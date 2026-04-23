"""
prompting.py

Contains all prompt templates and prompting techniques for the wine recommendation LLM calls.
Built to be used by Google Gemini-2.5-Flash
"""

import os
import json
from typing import Optional
from pydantic import BaseModel, ValidationError


from google import genai
from google.genai import types

### Global Variables

_client: Optional[genai.Client] = None
 
def get_client() -> genai.Client:
    """Instantiate the GenAI client once and reuse it."""
    global _client
    # Requires GOOGLE_API_KEY set in environment.
    if _client is None:
        _client = genai.Client() 
    return _client


USE_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are a master sommelier with decades of experience making personalized wine recommendations\
to a wide variety of people. Your job is to select the best wines for a specific person given a\
specific list of candidates from a wine database.

Your selections must follow these rules:
- Base your rationale exclusively on the description and attributes shown for each candidate wine.\
Do NOT draw on outside knowledge of these wines, wineries, or vintages.
- Select only from the numbered list of candidate wines given. Never recommend a wine not in the candidate list.
- Tailor every recommendation to the user's stated taste profile and query. 
- Always return a valid JSON matching the structure given in the response schema. Do not give any\
introduction or explanation outside the JSON structure.
- If the candidates are a poor match for the user's request, say so honestly in the \
sommelier_note and recommend the closest available options anyway.
"""

RESPONSE_SCHEMA = """
{
  "sommelier_note": "A 2-3 sentence overview of your recommendation set and why these wines suit this person. Written in first person as a sommelier.",
  "recommendations": [
    {
      "candidate_index": 1,
      "rationale": "2-3 sentences explaining why this wine matches the user's taste profile specifically. Reference their stated preferences directly.",
      "food_pairing": "One sentence on why this wine works with the user's specific request or occasion, if mentioned.",
      "serving_suggestion": "Temperature and decanting recommendation if relevant, otherwise omit this field."
    }
  ]
}
"""

### Pydantic Output Schema

class WineRecommendation(BaseModel):
    candidate_index: int
    rationale: str
    food_pairing: str = ""
    serving_suggestion: str = ""
 
class RecommendationResponse(BaseModel):
    sommelier_note: str
    recommendations: list[WineRecommendation]


### Formatting Helper Functions

def _format_taste_profile(profile: dict) -> str:
    """
    Converts a user's taste profile dict into a readable block for the prompt.
    Only includes fields that are present. Expects all of the fields in the TasteProfile Class
    defined in models.py.
    """
    lines = []

    if profile.get("sweetness"):
        lines.append(f"Sweetness preference: {profile['sweetness']}")
    if profile.get("body"):
        lines.append(f"Body preference: {profile['body']}")
    if profile.get("tannins"):
        lines.append(f"Tannin preference: {profile['tannins']}")
    if profile.get("acidity"):
        lines.append(f"Acidity preference: {profile['acidity']}")
    
    # Handle case of singular flavor preference vs multiple
    flavors  = profile.get("flavors", [])
    if isinstance(flavors, str):
        try:
            flavors = json.loads(flavors)
        except json.JSONDecodeError:
            flavors = []
    if flavors:
        lines.append(f"Favorite flavor notes: {', '.join(flavors)}")
    
    # Handle Price Range Preference
    price_min = profile.get("price_min")
    price_max = profile.get("price_max")
    if price_min is not None and price_max is not None:
        lines.append(f"Price range: ${price_min:.0f}–${price_max:.0f}")
    elif price_max is not None:
        lines.append(f"Maximum price: ${price_max:.0f}")
    
    # Handle case of singular vs multiple wine type preferences
    wine_types = profile.get("preferred_wine_types", [])
    if isinstance(wine_types, str):
        try:
            wine_types = json.loads(wine_types)
        except json.JSONDecodeError:
            wine_types = []
    if wine_types:
        lines.append(f"Preferred wine types: {', '.join(wine_types)}")
    
    # Handle case of singular vs multiple wine region preferences
    regions = profile.get("preferred_regions", [])
    if isinstance(regions, str):
        try:
            regions = json.loads(regions)
        except json.JSONDecodeError:
            regions = []
    if regions:
        lines.append(f"Preferred regions: {', '.join(regions)}")

    if not lines:
        return "No taste profile provided — make general recommendations."

    return "\n".join(lines)


def _format_candidates(candidates : dict) -> str:
    """
    Formats the dictionary of wines retrieved through RAG into a string ready to be
    used in the prompt for the LLM. Expects the dictionary to be formatted like the output for
    get_recommended_wines() in embeddings.py.
    """

    blocks =[]

    # Builds location line from available fields
    for i, wine in enumerate(candidates, start=1):
        location_parts = [
            p for p in [
                wine.get("region_1"),
                wine.get("province"),
                wine.get("country"),
            ] if p and p.strip()
        ]
        location = ", ".join(location_parts) if location_parts else "Unknown region"
    
        # Format price and hide the -1.0 sentinel for unknown prices
        price = wine.get("price", -1.0)
        price_str = f"${price:.0f}" if price >= 0 else "Price unknown"

        # Points
        points = wine.get("points", 0)
        points_str = f"{points}pts" if points > 0 else "Unrated"
 
        # Build block for each wine
        block = (
            f"[{i}] {wine.get('title') or wine.get('winery') or 'Unknown Wine'}\n"
            f"    Variety: {wine.get('variety') or 'Unknown'}\n"
            f"    Region: {location}\n"
            f"    {points_str} | {price_str}\n"
            f"    Description: \"{wine.get('description', '').strip()}\""
        )

        blocks.append(block)
 
    return "\n\n".join(blocks)

def _schema_block() -> str:
    return json.dumps(RecommendationResponse.model_json_schema(), indent=2)


### Gemini Content Helpers

def _user_turn(text: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=text)])
 
def _model_turn(text: str) -> types.Content:
    return types.Content(role="model", parts=[types.Part(text=text)])
 
def _extract_text(response) -> str:
    """
    Extract only non-thought text parts from a Gemini response.
    Gemini 2.5 models return internal reasoning parts (thought=True)
    alongside the actual response which must be filtered out.
    """
    parts = []
    for candidate in response.candidates:
        for part in candidate.content.parts:
            if getattr(part, "thought", False):
                continue
            if part.text:
                parts.append(part.text)
    return "".join(parts).strip()

def serialize_history(history: list[types.Content]) -> str:
    """
    Converts list[types.Content] to a JSON string for storage in SQLite.
    Call this in main.py after get_initial_recommendation() to store history.
    """
    return json.dumps([
        {
            "role": turn.role,
            "parts": [{"text": part.text} for part in turn.parts]
        }
        for turn in history
    ])


def deserialize_history(history_json: str) -> list[types.Content]:
    """
    Reconstructs list[types.Content] from a stored JSON string.
    Call this in main.py before get_refinement_recommendation() to restore history.
    """
    raw = json.loads(history_json)
    return [
        types.Content(
            role=turn["role"],
            parts=[types.Part(text=p["text"]) for p in turn["parts"]]
        )
        for turn in raw
    ]


### Initial Recommendation Prompt

def get_initial_recommendation(
        query : str,
        candidates : list[dict],
        profile : Optional[dict] = None,
        n_recommendations : int = 3,
) -> tuple[Optional[RecommendationResponse], list[types.Content]]:
    """
    Builds the prompt for the LLM to use to recommend wines.
    Utilizes the predefined response schema.
    Additionally calls gemini and gets response.

    Fields:
    - Query: Raw User query used to retrieve candidates.
    - Candidates: List of dictionarys where each dictionary is a different candidate wine retrieved through RAG from ChromaDB
    - Profile : Optional Dictionary object for user taste profile pulled from sqlite if the user has one.
    - n_recommendations: number of recommendations to give back to the user. Default is 3.

    Returns a RecommendationResponse from the LLM, alongside the chat history.
    """
    profile_block = _format_taste_profile(profile or {})
    candidates_block = _format_candidates(candidates)

    user_message = f"""## Taste Profile
{profile_block}
 
## User Request
"{query}"
 
## Candidate Wines ({len(candidates)} options)
{candidates_block}
 
## Your Task
Select the {n_recommendations} best wines for this person from the candidates above.
 
Respond with valid JSON matching this schema exactly:
{RESPONSE_SCHEMA}
 
Important:
- candidate_index must match the [number] in the candidate list above, and be between 1 and {len(candidates)}.
- The serving_suggestion field is optional. Omit it if not relevant to the query.
- Your rationale must directly reference the user's stated preferences, \
not generic wine descriptions."""
 
    history = [_user_turn(user_message)]
 
    response = get_client().models.generate_content(
        model=USE_MODEL,
        contents=history,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
        ),
    )
 
    raw    = _extract_text(response)
    parsed = parse_recommendation_response(raw)
    history.append(_model_turn(raw))
 
    return parsed, history

### Refinement Prompting

def get_refinement_recommendation(
    feedback : str,
    new_candidates : list[dict],
    conversation_history : list[types.Content],
    profile : Optional[dict] = None,
    n_recommendations : int = 3,
) -> tuple[Optional[RecommendationResponse], list[types.Content]]:
    """
    Builds the system prompt for a refinement call on a previous recommendation. Includes full
    conversation history so the LLM client understands what it recommended previously and why the user
    is asking for something different.

    Fields:
    - Feedback: Raw User feedback in response to the previous recommendation.
    - New_Candidates: New candidates from chromadb based on a combination of the previous query and new feedback.
    - Conversation_History: A list of dictionaries, where each is a recommendation from previously in the chat.
    follows the output [{"role": "User", "content" : ...}] schema.
    - Profile : Optional Dictionary object for user taste profile pulled from sqlite if the user has one.
    - n_recommendations: number of recommendations to give back to the user. Default is 3.

    Returns the full conversation history + new refined message as a RecommendationResponse
    """
    profile_block = _format_taste_profile(profile or {})
    candidates_block = _format_candidates(new_candidates)
 
    refinement_message = f"""## Taste Profile
{profile_block}
 
## Refinement Request
"{feedback}"
 
## New Candidate Wines ({len(new_candidates)} options)
These are fresh candidates retrieved based on your feedback. \
You may see some overlap with previous candidates.
{candidates_block}
 
## Your Task
Taking your previous recommendations and the user's feedback into account, \
select {n_recommendations} new wines from the candidates above.
 
Rules for refinement:
- Avoid recommending wines you already suggested unless they directly address \
the feedback.
- Explicitly acknowledge what you are changing and why in your sommelier_note.
- If the feedback is vague, interpret it generously and explain your interpretation.
 
Respond with valid JSON matching this schema exactly, No markdown. No explanation. No extra text.
{RESPONSE_SCHEMA}"""
 
    # Append the new refinement message to the existing conversation history
    # Convert prior conversation into plain text

    updated_history = conversation_history + [_user_turn(refinement_message)]
 
    response = get_client().models.generate_content(
        model=USE_MODEL,
        contents=updated_history,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
        ),
    )
 
    raw    = _extract_text(response)
    parsed = parse_recommendation_response(raw)
    updated_history.append(_model_turn(raw))
 
    return parsed, updated_history


### Response Parser

def parse_recommendation_response(raw: str) -> Optional[RecommendationResponse]:
    print(f"[debug] First 50 chars repr: {repr(raw[:50])}")
    print(f"[debug] Starts with backtick: {raw.strip().startswith('`')}")
    text = raw.strip()
    
    # Strip markdown fences — handle ```json, ```JSON, ``` etc.
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (the fence opener) and last line (the fence closer)
        inner_lines = []
        for line in lines[1:]:
            if line.strip() == "```":
                break
            inner_lines.append(line)
        text = "\n".join(inner_lines).strip()
    print(f"[debug] text after fence strip (first 80): {repr(text[:80])}")
    print(f"[debug] text after fence strip (last 80): {repr(text[-80:])}")  
    
    try:
        return RecommendationResponse.model_validate_json(text)
    except (ValidationError, json.JSONDecodeError) as e:
        print(f"[debug] Full error: {e}")
        print(f"[debug] Full stripped text:\n{text}")
        return None


