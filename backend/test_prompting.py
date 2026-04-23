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
 
from prompting import (
    get_initial_recommendation,
    get_refinement_recommendation,
    RecommendationResponse,
)
 
# ---------------------------------------------------------------------------
# Mock data
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
 
MOCK_CANDIDATES = [
    {
        "title": "Chateau Leoville-Barton 2015",
        "winery": "Chateau Leoville-Barton",
        "variety": "Cabernet Sauvignon Blend",
        "country": "France", "province": "Bordeaux", "region_1": "Saint-Julien",
        "points": 95, "price": 55.0,
        "description": "Rich and structured with dark fruit, cedar, and firm tannins. "
                       "Notes of tobacco and leather emerge after decanting. Long finish.",
    },
    {
        "title": "Caymus Vineyards 2016 Cabernet Sauvignon",
        "winery": "Caymus Vineyards",
        "variety": "Cabernet Sauvignon",
        "country": "US", "province": "California", "region_1": "Napa Valley",
        "points": 92, "price": 65.0,
        "description": "Bold and plush with blackberry, vanilla, and toasted oak. "
                       "Full-bodied with velvety tannins and a long, warm finish.",
    },
    {
        "title": "Ridge 2017 Monte Bello",
        "winery": "Ridge Vineyards",
        "variety": "Cabernet Sauvignon",
        "country": "US", "province": "California", "region_1": "Santa Cruz Mountains",
        "points": 96, "price": 68.0,
        "description": "Elegant and precise with cassis, dried herbs, and minerality. "
                       "Firm fine-grained tannins with excellent aging potential.",
    },
    {
        "title": "Penfolds Bin 389 Cabernet Shiraz 2018",
        "winery": "Penfolds",
        "variety": "Cabernet Sauvignon-Shiraz",
        "country": "Australia", "province": "South Australia", "region_1": "Multi-regional blend",
        "points": 91, "price": 40.0,
        "description": "Rich blackcurrant and dark chocolate with hints of mocha. "
                       "Full-bodied with grippy tannins and good concentration.",
    },
    {
        "title": "Stag's Leap Wine Cellars 2017 CASK 23",
        "winery": "Stag's Leap Wine Cellars",
        "variety": "Cabernet Sauvignon",
        "country": "US", "province": "California", "region_1": "Stags Leap District",
        "points": 97, "price": 69.0,
        "description": "Dark cherry, violets, and graphite. Silky tannins, "
                       "impeccable balance, and a very long finish.",
    },
]
 
 
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
        query="I want something bold to pair with a ribeye steak tonight",
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