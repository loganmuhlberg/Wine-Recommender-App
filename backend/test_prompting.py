"""
test_prompts.py
---------------
Tests the full prompt -> Gemini -> parse pipeline.
Run from backend/: python test_prompts.py
 
Requires GEMINI_API_KEY in your .env file.
Makes 2 real API calls (1 initial + 1 refinement).
"""
 
import os, json
from dotenv import load_dotenv
load_dotenv()

from embeddings import get_recommended_wines
from prompting import (
    get_initial_recommendation,
    get_refinement_recommendation,
    RecommendationResponse,
)
 
# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------
 
MOCK_PROFILE = {
    "sweetness": "sweet",
    "body": "medium",
    "tannins": "low-medium",
    "acidity": "medium",
    "favorite_flavors": json.dumps(["vanilla", "orange", "strawberry", "dark cherry"]),
    "price_min": 10.0,
    "price_max": 70.0,
    "preferred_wine_types": json.dumps(["red", "white", "rose"]),
    "preferred_regions":[],
}
 
MOCK_CANDIDATES = get_recommended_wines(
    query = "Sweet, fruity wine that isn't too dry.",
    price_max = 50
)
 
 
def print_response(parsed: RecommendationResponse, candidates: list[dict]):
    print(f"\n  Sommelier note: {parsed.sommelier_note[:120]}...")
    for rec in parsed.recommendations:
        wine = candidates[rec.candidate_index - 1]
        print(f"\n  #{rec.candidate_index} {wine['title']}")
        print(f"  Rationale:  {rec.rationale[:120]}...")
        if rec.food_pairing:
            print(f"  Pairing:    {rec.food_pairing[:100]}...")
        if rec.serving_suggestion:
            print(f"  Serving:    {rec.serving_suggestion}")
 
 
def test_initial():
    print("=" * 60)
    print("Test 1: Initial recommendation")
    print("=" * 60)
 
    parsed, history = get_initial_recommendation(
        query="Sweet, fruity wine that isn't too dry.",
        candidates=MOCK_CANDIDATES,
        profile=MOCK_PROFILE,
        n_recommendations=3,
    )
 
    assert parsed is not None, "Response failed to parse"
    assert len(parsed.recommendations) == 3, \
        f"Expected 3 recommendations, got {len(parsed.recommendations)}"
    for rec in parsed.recommendations:
        assert 1 <= rec.candidate_index <= len(MOCK_CANDIDATES), \
            f"candidate_index {rec.candidate_index} out of range"
 
    print_response(parsed, MOCK_CANDIDATES)
    print("\n  ✓ Test 1 passed")
    return parsed, history
 
 
def test_refinement(history):
    print("\n" + "=" * 60)
    print("Test 2: Refinement request")
    print("=" * 60)
 
    feedback = ("These feel too tannic and heavy. Can you suggest something "
                "more elegant and approachable with more finesse than power?")
    print(f"\n  Feedback: \"{feedback}\"")
 
    parsed, updated_history = get_refinement_recommendation(
        feedback=feedback,
        new_candidates=MOCK_CANDIDATES,
        conversation_history=history,
        profile=MOCK_PROFILE,
        n_recommendations=3,
    )
 
    assert parsed is not None, "Refinement response failed to parse"
    assert len(parsed.recommendations) == 3
    print(f"\n  Conversation turns: {len(updated_history)}")
    print_response(parsed, MOCK_CANDIDATES)
    print("\n  ✓ Test 2 passed")
 
 
if __name__ == "__main__":
    print("Testing Gemini 2.5 Flash prompt pipeline...\n")
    parsed, history = test_initial()
    test_refinement(history)
    print("\n" + "=" * 60)
    print("  All tests passed ✓")
    print("=" * 60)