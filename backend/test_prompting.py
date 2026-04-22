"""
test_prompts.py
---------------
Tests the full prompt → Gemini → parse pipeline.
Run from backend/: python test_prompts.py

Requires GOOGLE_API_KEY in your .env file.
Makes 2 real API calls (1 initial + 1 refinement).
"""

import os
import json
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from google import genai
from backend.embeddings import get_recommended_wines
from backend.prompting import (
    SYSTEM_PROMPT,
    build_recommendation_prompt,
    build_refinement_prompt,
    parse_recommendation_response,
    start_conversation,
)

CLIENT = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
USE_MODEL  = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Fake data — representative of what embeddings.py + SQLite would provide
# ---------------------------------------------------------------------------

MOCK_PROFILE = {
    "sweetness": "dry",
    "body": "full",
    "tannins": "high",
    "acidity": "medium",
    "favorite_flavors": json.dumps(["dark cherry", "oak", "tobacco", "leather"]),
    "price_min": 20.0,
    "price_max": 70.0,
    "preferred_wine_types": json.dumps(["red"]),
    "preferred_regions": json.dumps(["Bordeaux", "Napa Valley"]),
    "additional_notes": "Prefers Old World structure when possible.",
}

MOCK_RESULTS = get_recommended_wines("I want something bold to pair with a ribeye steak tonight")
for i, wine in enumerate(MOCK_RESULTS):
    print(f"  #{i+1} {wine['title'] or wine['winery']}"
          f" ({wine['variety']})"
          f" ${wine['price']:.0f} | {wine['points']}pts"
          f" | similarity: {wine['similarity']}")
    print(f"       {wine['description'][:100]}...")
    print()

def call_google(messages: str, system = SYSTEM_PROMPT) -> str:
    """Fire a Google API call and return the raw text response."""
    response = CLIENT.models.generate_content(
        model=USE_MODEL,
        contents=messages,
        config = {"system_instruction" : SYSTEM_PROMPT}
    )
    return response.text


def test_initial_recommendation():
    print("=" * 60)
    print("Test 1: Initial recommendation")
    print("=" * 60)

    messages = build_recommendation_prompt(
        query="I want something bold to pair with a ribeye steak tonight",
        candidates=MOCK_CANDIDATES,
        profile=MOCK_PROFILE,
        n_recommendations=3,
    )

    print(f"\nSending {len(MOCK_CANDIDATES)} candidates to Google...")
    raw = call_google(messages)

    print("\nRaw Gemini response:")
    print(raw)

    parsed = parse_recommendation_response(raw)
    assert parsed is not None, "Response failed to parse as JSON"
    assert parsed.recommendations, "Missing recommendations"
    assert parsed.sommelier_note, "Missing sommelier_note"
    assert len(parsed.recommendations) == 3, \
    f"Expected 3 recommendations, got {len(parsed.recommendations)}"

    print(f"\nSommelier note: {parsed.sommelier_note[:100]}...")
    for rec in parsed.recommendations:
        wine = MOCK_CANDIDATES[rec.candidate_index - 1]
        print(f"\n  #{rec.candidate_index} {wine['title']}")
        print(f"  Rationale: {rec.rationale[:120]}...")
        if rec.food_pairing:
            print(f"  Pairing: {rec.food_pairing[:100]}...")
        if rec.serving_suggestion:
            print(f"  Serving: {rec.serving_suggestion}")
    return messages, raw


def test_refinement(initial_messages: list[dict], initial_response: str):
    print("=" * 60)
    print("Test 2: Refinement request")
    print("=" * 60)

    history = start_conversation(initial_messages, initial_response)

    # Simulate user wanting something different
    feedback = "These feel too tannic and heavy. " \
               "Can you suggest something a bit more elegant and approachable, " \
               "maybe with more finesse than power?"

    # In real usage, new_candidates would come from a fresh ChromaDB query
    # using the feedback. For this test we reuse the same candidates.
    messages = build_refinement_prompt(
        feedback=feedback,
        new_candidates=MOCK_CANDIDATES,
        conversation_history=history,
        profile=MOCK_PROFILE,
        n_recommendations=3,
    )

    print(f"\nConversation history length: {len(messages)} messages")
    print(f"Feedback: \"{feedback}\"")
    print("\nSending refinement to Gemini...")

    raw = call_google(messages)

    print("\nRaw Gemini response:")
    print(raw)

    parsed = parse_recommendation_response(raw)
    assert parsed is not None, "Refinement response failed to parse as JSON"
    assert parsed.recommendations, "Missing recommendations"
    assert len(parsed.recommendations) == 3

    print("\nRefined recommendations:")
    for rec in parsed.recommendations:
        wine = MOCK_CANDIDATES[rec.candidate_index - 1]
        print(f"\n  #{rec.candidate_index} {wine['title']}")
        print(f"  Rationale: {rec.rationale[:120]}...")

    print("\n✓ Test 2 passed\n")


print("Testing prompt pipeline...\n")

initial_messages, initial_response = test_initial_recommendation()
test_refinement(initial_messages, initial_response)

print("=" * 60)
print("  All prompt tests passed ✓")
print("=" * 60)