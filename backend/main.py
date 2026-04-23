"""
main.py

Acts as the main traffic controller for the wine recommender backend.
Contains all FastAPI call functions and HTTP endpoints.

Run with:
    uvicorn main:app --reload --port 8000
"""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional
 
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session
 
from database import (
    create_db_and_tables,
    db_add_wine_to_recommendation,
    db_create_profile,
    db_create_recommendation,
    db_create_user,
    db_finalize_recommendation,
    db_get_profile_by_user,
    db_get_recommendation,
    db_get_recommendations_by_user,
    db_get_wines_for_recommendation,
    db_get_user,
    db_update_profile,
    get_session,
    db_update_conversation_history
)
from embeddings import get_collection, get_model, get_recommended_wines
from models import (
    Recommendation,
    RecommendationCreate,
    RecommendedWine,
    TasteProfileCreate,
    TasteProfileRead,
    TasteProfileUpdate,
    UserCreate,
    UserRead,
    User,
)
from prompting import (
    RecommendationResponse,
    get_initial_recommendation,
    get_refinement_recommendation,
    parse_recommendation_response,
    _user_turn,
    _model_turn,
    serialize_history,
    deserialize_history
)
from search_enrichment import enrich_wines_batch, WineEnrichment

### JSON Response Pydantic Schemas

class RecommendRequest(BaseModel):
    user_id: int
    query_text: str
    # Sidebar filters
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    regions: Optional[list[str]] = None
    countries: Optional[list[str]] = None 
    varietals: Optional[list[str]] = None
 
class RefineRequest(BaseModel):
    user_id: int
    feedback: str
    previous_recommendation_id: int
    # Sidebar filters
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    regions: Optional[list[str]] = None
    countries: Optional[list[str]] = None 
    varietals: Optional[list[str]] = None
 
 
class WineResult(BaseModel):
    """Single wine card as returned to the frontend."""
    rank: int
    wine_name: str
    winery: Optional[str] = None
    varietal: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    points: Optional[int] = None
    price: Optional[float] = None
    description: Optional[str] = None
    rationale: str
    food_pairing: str = ""
    serving_suggestion: str = ""
    thumbnail: Optional[str] = None
    image_source: Optional[str] = None
    buy_link: Optional[str] = None
    buy_source: Optional[str] = None
 
 
class RecommendResponse(BaseModel):
    """Full recommendation response returned to the frontend."""
    recommendation_id: int
    user_id : int
    sommelier_note: str
    query_text: str
    wines: list[WineResult]

### Lifespan Setup

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when server starts
    create_db_and_tables() 
    get_model()               
    get_collection()          
    yield

### Create App Instance:

app = FastAPI(
    title="Wine Recommender API",
    description="Personalized wine recommendations powered by RAG and Gemini.",
    version="0.1.0",
    lifespan=lifespan,
)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

### User Endpoints

@app.post("/users", response_model = UserRead, tags = ["Users"])
def create_user(user : UserCreate, session : Session = Depends(get_session)):
    """
    Creates a user in the SQLite database based off request info. 
    Called on first visit to the website when filling out taste profile quiz.
    """
    user_c = db_create_user(session, user)
    return user_c

@app.get("/users", response_model = UserRead, tags = ["Users"])
def get_user(user_id : int, session : Session = Depends(get_session)):
    """Fetch a user by ID. Raises HTTP exception if user id given is not in database."""
    user = db_get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

### Taste Profile Endpoints

@app.post("/users{id}/profile", response_model = TasteProfileRead, tags = ["Profile"])
def create_profile(user_id : int, profile_in : TasteProfileCreate , session : Session = Depends(get_session)):
    """
    Creates a Taste Profile instance for a user when the quiz is completed.
    """
   # Ensure user exists
    user = db_get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Attach user_id from the URL
    profile_in.user_id = user_id
 
    try:
        profile = db_create_profile(session, profile_in)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
 
    return profile


@app.get("/users{id}/profile", response_model = TasteProfileRead, tags = ["Profile"])
def get_user_profile(user_id : int, session : Session = Depends(get_session)):
    """
    Fetches a taste profile associated with a given user id.
    Used to pre-fill the quiz form with their answers when the user returns.
    """
    profile = db_get_profile_by_user(session, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Taste Profile not found")
    return profile

@app.patch("/users{id}/profile", response_model = UserRead, tags = ["Profile"])
def update_user_profile(user_id : int, updates : TasteProfileUpdate, session : Session = Depends(get_session)):
    """
    Updates a user profile given a specific user id.
    Only fields included in the request body are changed.
    """
    profile = db_get_profile_by_user(session, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found for this user")
 
    updated = db_update_profile(session, profile.id, updates)
    return updated

### Recommendation Endpoints

def _build_wine_results(
        picks : RecommendationResponse,
        candidates : list[dict],
        enrichments : list[WineEnrichment]
) -> list[WineResult]:
    """
    Combine the picks from the LLM, the candidate wines from ChromaDB, and the search enrichments
    from Brave API searching into one WineResult class for each wine.
    """
    results = []
    for rank, (rec, enrichment) in enumerate(
        zip(picks.recommendations, enrichments), start=1
    ):
        # candidate_index is 1-based
        wine = candidates[rec.candidate_index - 1]
 
        results.append(WineResult(
            rank=rank,
            wine_name=wine.get("title") or wine.get("winery") or "Unknown",
            winery=wine.get("winery"),
            varietal=wine.get("variety"),
            region=wine.get("region_1"),
            country=wine.get("country"),
            points=wine.get("points") or None,
            price=wine.get("price") if wine.get("price", -1) >= 0 else None,
            description=wine.get("description"),
            rationale=rec.rationale,
            food_pairing=rec.food_pairing,
            serving_suggestion=rec.serving_suggestion,
            thumbnail=enrichment.thumbnail_url,
            image_source=enrichment.image_source,
            buy_link=enrichment.buy_url,
            buy_source=enrichment.buy_source,
        ))
    return results
 
def _save_recommendation(
    session : Session,
    user_id : int,
    query_text : str,
    results : list[WineResult],
    raw_llm_response : str,
    n_candidates : int
) -> Recommendation:
    """
    Persist the full recommendation session to SQLite.
    Returns saved recommendation record.
    """
    # Create parent recommendation
    rec = db_create_recommendation(session, RecommendationCreate(user_id=user_id, query_text=query_text))

    # Save each recommended wine
    for wine in results:
        db_add_wine_to_recommendation(
            session,
            rec.id,
            RecommendedWine(
                recommendation_id=rec.id,
                rank=wine.rank,
                wine_name=wine.wine_name,
                winery=wine.winery,
                varietal=wine.varietal,
                region=wine.region,
                country=wine.country,
                points=wine.points,
                price=wine.price,
                description=wine.description,
                rationale=wine.rationale,
                thumbnail=wine.thumbnail,
                buylink=wine.buy_link,
            ),
        )

    # Store LLM metadata for debugging
    db_finalize_recommendation(
        session,
        rec.id,
        llm_raw_response=raw_llm_response,
        rag_candidates_retrieved=n_candidates,
    )
 
    return rec

@app.post("/recommend", response_model = RecommendResponse, tags = ["Recommendations"])
def recommend(
    request : RecommendRequest,
    session : Session = Depends(get_session)
) -> RecommendResponse:
    """
    Core Recommendation endpoint.
    1. Loads user profile from sqlite
    2. Queries chromadb based on the request query
    3. Sends candidates to LLM to pick and create recommendation
    4. Sends picks to Brave Search API to enrich with buy link and thumbnail
    5. Formats into Recommendation object
    6. Save to SQLite and return
    """
    # 1. Load taste profile (optional — works without one)
    profile = db_get_profile_by_user(session, request.user_id)
    profile_dict = profile.model_dump() if profile else {}

    # 2. Build ChromaDB filters from profile and request candidates
    query = request.query_text
    price_min = request.price_min if request.price_min else None
    price_max = request.price_max if request.price_max else None
    regions = request.regions if request.regions else None
    countries = request.countries if request.countries else None
    varietals = request.varietals if request.varietals else None

    candidates = get_recommended_wines(query, price_min, price_max, regions, countries, varietals)

    if not candidates:
        raise HTTPException(
            status_code=503,
            detail="No matching wines found. Try broadening your search or adjusting filters.",
        )

    #3. Send candidates to LLM for recommendation
    parsed, history = get_initial_recommendation(query, candidates, profile_dict)
    conversation_history = serialize_history(history)

    if not parsed:
        raise HTTPException(
            status_code=502,
            detail="The recommendation model returned an unexpected response. Please try again.",
        )
    
    #4. Enrich results with Brave Search for buy link and thumbnail
    picked_wines = [candidates[r.candidate_index - 1] for r in parsed.recommendations]
    enrichments  = asyncio.run(enrich_wines_batch([
        {
            "wine_name": w.get("title", ""),
            "winery":    w.get("winery", ""),
            "region":    w.get("region_1", ""),
            "country":   w.get("country", ""),
        }
        for w in picked_wines
    ]))

    #5. Format into Recommendation object
    wine_results = _build_wine_results(parsed, candidates, enrichments)

    #6. Return recommendation and save to SQLite
    rec = _save_recommendation(
        session=session,
        user_id=request.user_id,
        query_text=request.query_text,
        results=wine_results,
        raw_llm_response=json.dumps(parsed.model_dump()),
        n_candidates=len(candidates),
    )

    db_update_conversation_history(session, rec.id, conversation_history)

    return RecommendResponse(
        recommendation_id=rec.id,
        user_id=request.user_id,
        sommelier_note=parsed.sommelier_note,
        query_text=request.query_text,
        wines=wine_results,
    )

@app.post("/recommend/{recommendation_id}/refine", response_model = RecommendResponse, tags = ["Recommendations"])
def refine(
    recommendation_id : int,
    request : RefineRequest,
    session : Session = Depends(get_session)
) -> RecommendResponse:
    """
    Call the LLM to refine the response from a previous recommendation.
    Recalls the entire recommendation process with the new user feedback.
    """
    #check if previous recommendation is found
    previous = db_get_recommendation(session, recommendation_id)
    if not previous:
        raise HTTPException(status_code=404, detail="Recommendation not found")
 
    #check if recommendation belongs to user
    if previous.user_id != request.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Load taste profile
    profile = db_get_profile_by_user(session, request.user_id)
    profile_dict = profile.model_dump() if profile else {}
 
    # Build updated query from original + feedback
    updated_query = f"{previous.query_text}. {request.feedback}"
 
    # Build new filters and get candidates
    price_min = request.price_min if request.price_min else None
    price_max = request.price_max if request.price_max else None
    regions = request.regions if request.regions else None
    countries = request.countries if request.countries else None
    varietals = request.varietals if request.varietals else None

    new_candidates = get_recommended_wines(updated_query, price_min, price_max, regions, countries, varietals)

    if not new_candidates:
        raise HTTPException(
            status_code=503,
            detail="No matching wines found for your refinement. Try different feedback.",
        )
    
    #Reconstruct
    conversation_history = deserialize_history(previous.conversation_history)

 
    # Ask Gemini to refine
    parsed, history = get_refinement_recommendation(
        feedback=request.feedback,
        new_candidates=new_candidates,
        conversation_history=conversation_history,
        profile=profile_dict,
        n_recommendations=3,
    )

    new_history = serialize_history(history)
 
    if not parsed:
        raise HTTPException(
            status_code=502,
            detail="The recommendation model returned an unexpected response. Please try again.",
        )
    
    # Enrich and build results
    picked_wines = [new_candidates[r.candidate_index - 1] for r in parsed.recommendations]
    enrichments  = asyncio.run(enrich_wines_batch([
        {
            "wine_name": w.get("title", ""),
            "winery":    w.get("winery", ""),
            "region":    w.get("region_1", ""),
            "country":   w.get("country", ""),
        }
        for w in picked_wines
    ]))
 
    wine_results = _build_wine_results(parsed, new_candidates, enrichments)
 
    # Save the refined recommendation as a new record
    rec = _save_recommendation(
        session=session,
        user_id=request.user_id,
        query_text=updated_query,
        results=wine_results,
        raw_llm_response=json.dumps(parsed.model_dump()),
        n_candidates=len(new_candidates),
    )

    db_update_conversation_history(session, rec.id, new_history)
 
    return RecommendResponse(
        recommendation_id=rec.id,
        user_id = request.user_id,
        sommelier_note=parsed.sommelier_note,
        query_text=request.feedback,
        wines=wine_results,
    )

@app.get("/recommend/{recommendation_id}", response_model=RecommendResponse, tags=["Recommendations"])
def get_recommendation(
    recommendation_id: int,
    session: Session = Depends(get_session),
):
    """
    Fetch a previously saved recommendation by id.
    Used by the frontend to display results after a page reload or navigation.
    """
    rec = db_get_recommendation(session, recommendation_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
 
    wines_db = db_get_wines_for_recommendation(session, recommendation_id)
 
    # Reconstruct sommelier_note from stored LLM response if available
    sommelier_note = ""
    if rec.llm_raw_response:
        try:
            stored = json.loads(rec.llm_raw_response)
            sommelier_note = stored.get("sommelier_note", "")
        except json.JSONDecodeError:
            pass

    wine_results = [
        WineResult(
            rank=w.rank,
            wine_name=w.wine_name,
            winery=w.winery,
            varietal=w.varietal,
            region=w.region,
            country=w.country,
            points=w.points,
            price=w.price,
            description=w.description,
            rationale=w.rationale or "",
            thumbnail=w.thumbnail,
            buy_link=w.buylink,
        )
        for w in wines_db
    ]
 
    return RecommendResponse(
        recommendation_id=rec.id,
        user_id=rec.user_id,
        sommelier_note=sommelier_note,
        query_text=rec.query_text,
        wines=wine_results,
    )

@app.get("/users/{user_id}/recommendations", response_model=list[RecommendResponse], tags=["Recommendations"])
def get_user_recommendations(
    user_id: int,
    session: Session = Depends(get_session),
):
    """
    Fetch all past recommendations for a user, newest first.
    Used to show recommendation history in the frontend.
    """
    user = db_get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
 
    recs = db_get_recommendations_by_user(session, user_id)
    responses = []
 
    for rec in recs:
        wines_db = db_get_wines_for_recommendation(session, rec.id)
        sommelier_note = ""
        if rec.llm_raw_response:
            try:
                stored = json.loads(rec.llm_raw_response)
                sommelier_note = stored.get("sommelier_note", "")
            except json.JSONDecodeError:
                pass
 
        wine_results = [
            WineResult(
                rank=w.rank,
                wine_name=w.wine_name,
                winery=w.winery,
                varietal=w.varietal,
                region=w.region,
                country=w.country,
                points=w.points,
                price=w.price,
                description=w.description,
                rationale=w.rationale or "",
                thumbnail=w.thumbnail,
                buy_link=w.buylink,
            )
            for w in wines_db
        ]
 
        responses.append(RecommendResponse(
            recommendation_id=rec.id,
            user_id=user_id,
            sommelier_note=sommelier_note,
            query_text=rec.query_text,
            wines=wine_results,
        ))
 
    return responses
    


### Health Check 
@app.get("/health", tags=["System"])
def health():
    """
    Simple health check. Returns 200 if the server is running.
    The frontend can call this to verify the backend is reachable before
    making real requests.
    """
    return {"status": "ok"}
    








    





