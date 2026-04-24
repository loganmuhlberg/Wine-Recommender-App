"""
api.py

acts as a wrapper for all api calls from the streamlit frontend.
"""

from typing import Optional
import requests
import json
from pathlib import Path
import streamlit as st

### configuration

API_BASE = "http://localhost:8000"
 
DEFAULT_TIMEOUT = 15
 
LLM_TIMEOUT = 60

### Internal Helper Functions

def _get(endpoint: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Fire a GET request and return the parsed JSON or an error dict."""
    url = f"{API_BASE}{endpoint}"
    print(f"[api debug] GET {url}")
    try:
        response = requests.get(f"{API_BASE}{endpoint}", timeout=timeout)
        print(f"[api debug] status: {response.status_code}")
        print(f"[api debug] raw response: {response.text[:200]}")
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", f"HTTP {response.status_code}")}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend. The server may not be running."}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. The server may be overloaded."}
    except Exception as e:
        return {"error": str(e)}
 
 
def _post(endpoint: str, body: dict, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Fire a POST request and return the parsed JSON or an error dict."""
    print(f"[api debug] POST {API_BASE}{endpoint}")  # add this
    print(f"[api debug] body: {body}")

    try:
        response = requests.post(
            f"{API_BASE}{endpoint}",
            json=body,
            timeout=timeout,
        )
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", f"HTTP {response.status_code}")}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend. The server may not be running."}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Please try again."}
    except Exception as e:
        return {"error": str(e)}
 
 
def _patch(endpoint: str, body: dict, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Fire a PATCH request and return the parsed JSON or an error dict."""
    try:
        response = requests.patch(
            f"{API_BASE}{endpoint}",
            json=body,
            timeout=timeout,
        )
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", f"HTTP {response.status_code}")}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend. The server may not be running."}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Please try again."}
    except Exception as e:
        return {"error": str(e)}
 
 
### System Health Check

def health_check() -> bool:
    """
    Returns True if the backend is reachable, False otherwise.
    Call this on app startup to give a clear error if the server isn't running.
    """
    result = _get("/health")
    return "error" not in result
 
### Users

def create_user(display_name: str) -> dict:
    """
    Create a new user account.
    Returns the created user dict including their generated id.
 
    Response keys: id, display_name, created_at
    """
    return _post("/users", {"display_name": display_name})
 
 
def get_user(user_id: int) -> dict:
    """
    Fetch a user by id.
    Used to verify a stored user_id is still valid on return visits.
 
    Returns {"error": ...} with a 404 message if the user doesn't exist.
    """
    result = _get(f"/users/{user_id}")
    return result

 
### Taste Profile

def get_profile(user_id: int) -> dict:
    """
    Fetch the taste profile for a user.
    Returns {"error": ...} with a 404 message if no profile exists yet.
    use this to decide whether to show the quiz or the edit view.
 
    Response keys: 
    id, user_id, sweetness, body, tannins, acidity,
    flavors, aromas, types, regions, price_min, price_max, created_at, updated_at
    """
    return _get(f"/users/{user_id}/profile")
 
 
def create_profile(
    user_id: int,
    sweetness: str,
    body: str,
    tannins: str,
    acidity: str,
    flavors: list[str],
    countries: list[str],
    types: list[str],
    regions: list[str],
    price_min: float,
    price_max: float,
) -> dict:
    """
    Submit a taste profile for a user (first time quiz completion).
    Each user can only have one profile.
    use update_profile() to change it.
 
    flavor, aroma, type, and region lists are serialised to JSON strings
    here so the Streamlit page doesn't need to know about that detail.
    """
    import json
    return _post(f"/users/{user_id}/profile", {
        "user_id":   user_id,
        "sweetness": sweetness,
        "body":      body,
        "tannins":   tannins,
        "acidity":   acidity,
        "flavors":   json.dumps(flavors),
        "countries":    json.dumps(countries),
        "types":     json.dumps(types),
        "regions":   json.dumps(regions),
        "price_min": price_min,
        "price_max": price_max,
    })
 
 
def update_profile(user_id: int, updates: dict) -> dict:
    """
    Partially update a taste profile.
    Only pass the fields you want to change — omitted fields are unchanged.
 
    Note: list fields (flavors, aromas, types, regions) must be passed as
    JSON strings if included:
        update_profile(1, {"flavors": json.dumps(["cherry", "oak"])})
    """
    return _patch(f"/users/{user_id}/profile", updates)

@st.cache_data
def load_filter_options() -> dict:
    """
    Load filter options from the pre-extracted JSON file.
    Cached by Streamlit so it only reads from disk once per session.
    """
    path = Path(__file__).parent / "filter_options.json"
    if not path.exists():
        return {"countries": [], "regions": [], "varietals": []}
    with open(path) as f:
        return json.load(f)

### Recommendations

def get_recommendation(
    user_id: int,
    query_text: str,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    regions: Optional[list[str]] = None,
    countries: Optional[list[str]] = None,
    varietals: Optional[list[str]] = None,
) -> dict:
    """
    Run the full recommendation pipeline and return 3 wine recommendations.
 
    This call takes 15-30 seconds on average.
 
    Sidebar filter arguments are all optional. Pass only those the user
    has explicitly set.
 
    Response keys: recommendation_id, user_id, sommelier_note, query_text, wines

    Each wine has: rank, wine_name, winery, variety, region, country,
    points, price, description, rationale, food_pairing, serving_suggestion, 
    thumbnail, image_source, buy_link, buy_source
    """
    body = {
        "user_id":    user_id,
        "query_text": query_text,
    }
    if price_min is not None:
        body["price_min"] = price_min
    if price_max is not None:
        body["price_max"] = price_max
    if regions:
        body["regions"] = regions
    if countries:
        body["countries"] = countries
    if varietals:
        body["varietals"] = varietals
 
    return _post("/recommend", body, timeout=LLM_TIMEOUT)
 
 
def refine_recommendation(
    user_id: int,
    recommendation_id: int,
    feedback: str,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    regions: Optional[list[str]] = None,
    countries: Optional[list[str]] = None,
    varietals: Optional[list[str]] = None,
) -> dict:
    """
    Refine a previous recommendation based on user feedback.
    Passes the full conversation history so the LLM understands
    what it previously recommended.
 
    This call also takes 15-30 seconds on average.
 
    Response shape is identical to get_recommendation().
    """
    body = {
        "user_id":                   user_id,
        "feedback":                  feedback,
        "previous_recommendation_id": recommendation_id,
    }
    if price_min is not None:
        body["price_min"] = price_min
    if price_max is not None:
        body["price_max"] = price_max
    if regions:
        body["regions"] = regions
    if countries:
        body["countries"] = countries
    if varietals:
        body["varietals"] = varietals
 
    return _post(f"/recommend/{recommendation_id}/refine", body, timeout=LLM_TIMEOUT) 
 
 
def fetch_recommendation(recommendation_id: int) -> dict:
    """
    Fetch a previously saved recommendation by id.
    Used by the history page to display past recommendations.
 
    Response shape is identical to get_recommendation().
    """
    return _get(f"/recommend/{recommendation_id}")
 
 
def get_user_recommendations(user_id: int) -> list[dict]:
    """
    Fetch all past recommendations for a user, newest first.
    Returns a list of recommendation dicts.
    Returns an empty list if the user has no recommendations or on error.
    """
    result = _get(f"/users/{user_id}/recommendations")
    if isinstance(result, list):
        return result
    return []
 
