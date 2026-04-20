"""
database.py

Set up SQLite database using the models from models.py.
Inlcudes SQLite connection setup, session management, and CRUD helper functions.

Usage in FastAPI endpoints:
    from database import get_session
    from sqlmodel import Session
 
    @app.post("/profile")
    def create_profile(profile: TasteProfileCreate, session: Session = Depends(get_session)):
        return db_create_profile(session, profile)
"""

from datetime import datetime
from typing import Generator, Optional
from sqlmodel import SQLModel, Session, create_engine, select
 
from models import (
    User, UserCreate,
    TasteProfile, TasteProfileCreate, TasteProfileUpdate,
    Recommendation, RecommendationCreate,
    RecommendedWine,
)

### Engine Setup

# The database lives in a single file at the project root.
# check_same_thread=False is required for FastAPI's async context.
DATABASE_URL = "sqlite:///./app.db"
 
engine = create_engine(
    DATABASE_URL,
    echo=False,            
    connect_args={"check_same_thread": False},
)
 
def create_tables_and_db() -> None:
    """
    Creates the tables and db based on the models created in models.py.
    """
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session per request.
    """
    with Session(engine) as session:
        yield session


### User CRUD

def db_create_user(session: Session, user_in: UserCreate) -> User:
    """Create a new user record and return it with its generated id."""
    user = User.model_validate(user_in)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
 
 
def db_get_user(session: Session, user_id: int) -> Optional[User]:
    """Return a user by id, or None if not found."""
    return session.get(User, user_id)
 
 
def db_get_all_users(session: Session) -> list[User]:
    """Return all users."""
    return session.exec(select(User)).all()

### Taste Profile CRUD


def db_create_profile( 
    session: Session, profile_in: TasteProfileCreate
) -> TasteProfile:
    """
    Create a taste profile for a user.
    Raises ValueError if a profile already exists for this user.
    """
    existing = db_get_profile_by_user(session, profile_in.user_id)
    if existing:
        raise ValueError(
            f"User {profile_in.user_id} already has a taste profile. "
            "Use PATCH /profile/{id} to update it."
        )
 
    profile = TasteProfile.model_validate(profile_in)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile
 
 
def db_get_profile(session: Session, profile_id: int) -> Optional[TasteProfile]:
    return session.get(TasteProfile, profile_id)
 
 
def db_get_profile_by_user(
    session: Session, user_id: int
) -> Optional[TasteProfile]:
    """Fetch the single taste profile belonging to a given user."""
    statement = select(TasteProfile).where(TasteProfile.user_id == user_id)
    return session.exec(statement).first()
 
 
def db_update_profile(
    session: Session,
    profile_id: int,
    updates: TasteProfileUpdate,
) -> Optional[TasteProfile]:
    """
    Partial update — only fields explicitly provided in `updates` are changed.
    Always refreshes updated_at.
    """
    profile = session.get(TasteProfile, profile_id)
    if not profile:
        return None
 
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
 
    profile.updated_at = datetime.utc()
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile
 
 
def db_delete_profile(session: Session, profile_id: int) -> bool:
    """Delete a profile by id. Returns True if deleted, False if not found."""
    profile = session.get(TasteProfile, profile_id)
    if not profile:
        return False
    session.delete(profile)
    session.commit()
    return True
 
### Recommendation CRUD

def db_create_recommendation(
    session: Session, rec_in: RecommendationCreate
) -> Recommendation:
    """Create an empty recommendation record (wines added separately)."""
    rec = Recommendation.model_validate(rec_in)
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec
 
 
def db_add_wine_to_recommendation(
    session: Session,
    recommendation_id: int,
    wine: RecommendedWine,
) -> RecommendedWine:
    """Attach a RecommendedWine to an existing Recommendation."""
    wine.recommendation_id = recommendation_id
    session.add(wine)
    session.commit()
    session.refresh(wine)
    return wine
 
 
def db_finalize_recommendation(
    session: Session,
    recommendation_id: int,
    llm_raw_response: str,
    rag_candidates_retrieved: int,
) -> Optional[Recommendation]:
    """
    After all wines are added, store the raw LLM response.
    """
    rec = session.get(Recommendation, recommendation_id)
    if not rec:
        return None
    rec.llm_raw_response = llm_raw_response
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec
 
 
def db_get_recommendation(
    session: Session, recommendation_id: int
) -> Optional[Recommendation]:
    return session.get(Recommendation, recommendation_id)
 
 
def db_get_recommendations_by_user(
    session: Session, user_id: int
) -> list[Recommendation]:
    """Return all recommendations for a user, newest first."""
    statement = (
        select(Recommendation)
        .where(Recommendation.user_id == user_id)
        .order_by(Recommendation.created_at.desc())
    )
    return session.exec(statement).all()
 
 
def db_get_wines_for_recommendation(
    session: Session, recommendation_id: int
) -> list[RecommendedWine]:
    """Return all wines for a given recommendation, ordered by rank."""
    statement = (
        select(RecommendedWine)
        .where(RecommendedWine.recommendation_id == recommendation_id)
        .order_by(RecommendedWine.rank)
    )
    return session.exec(statement).all()
 