"""
SQLModel table definitions for creation in the user database.

Tables:
User - user account in the app
TasteProfile - Taste Preferences for each User (1-to-1)
Recommendation - Saved recommendations
RecommendedWine - specific wines within the recommendation
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
import json

class UserBase(SQLModel):
    display_name: Optional[int] = Field(default = None, max_length = 100)

class User(UserBase, table = True):
    """
    Single User account.
    User created when opening the app for the first time.
    """
    id : Optional[int] = Field(default = None, primary_key = True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    password : str

    #Relationships
    taste_profile: Optional["TasteProfile"] = Relationship(back_populates="user")
    recommendations: list["Recommendation"] = Relationship(back_populates="user")

class UserCreate(UserBase):
    """
    User creation schema
    """
    pass

class UserRead(UserBase):
    """
    User reading schema (to avoid password sharing)
    """
    id : int
    password: str
    created_at : datetime


### TASTE PROFILE

class TasteProfileBase(SQLModel):
    """
    Taste Profile for a specific user.
    Captures all their preferred preferences from a small quiz given on account creation.
    """

    # Main Preferences
    sweetness : str = Field(
        description = "Preferred Sweetness Level. One of Dry, Off-Dry, Sweet."
    )
    acidity : str = Field(
        description = "Preferred Acidity Level. One of Low, Medium-Low, Medium, Medium-High, or High."
    )
    tannins : str = Field(
        description = "Preferred Tannin Level. One of Low, Medium-Low, Medium, Medium-High, or High."
    )
    body : str = Field(
        description = "Preferred Body. One of Light, Medium, Full."
    )
    types : str = Field(
        description = "Preferred Types of Wine. Stored as array of one or many of Red, White, Sparkling, Dessert, or Fortified."
    )

    # Flavor and Aroma Notes
    flavors : str = Field(
        description = "Preferred Flavors in Wine. Stored as array of input flavors.",
        defualt = "[]"
    )
    aromas : str = Field(
        description = "Preferred Aromas in Wine. Stored as array of input flavors.",
        defualt = "[]"
    )

    # Region Preferences
    regions : str = Field(
        description = "Preferred Wine Regions. Stored as array of regions (e.g. ['Fruili', 'Bordeaux'])",
        default = "[]"
    )

    # Price Range
    price_min : float = Field(default = 0.0, ge = 0)
    price_max : float = Field(default = 50.0, ge = 0)

class TasteProfile(TasteProfileBase):
    id : Optional[int] = Field(default = None, primary_key = True)
    user_id : int = Field(foreign_key = "user.id", unique = True)
    created_at : datetime = Field(default_factory=datetime.utc)
    updated_at : datetime = Field(default_factory=datetime.utc)

    user: Optional[User] = Relationship(back_populates="taste_profile")

class TasteProfileCreate(TasteProfileBase):
    """
    Used to create an initial taste profile at time of user creation (taste quiz).
    """
    user_id : int

    def set_flavors(self, in_flavors : list[str]):
        self.flavors = json.dumps(in_flavors)
    def set_regions(self, in_regions : list[str]):
        self.regions = json.dumps(in_regions)
    def set_types(self, in_types : list[str]):
        self.types = json.dumps(in_types)


class TasteProfileUpdate(SQLModel):
    """
    Used to update an existing taste profile.
    """
    sweetness: Optional[str] = None
    body: Optional[str] = None
    tannins: Optional[str] = None
    acidity: Optional[str] = None
    flavors: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    types: Optional[str] = None
    regions: Optional[str] = None

class TasteProfileRead(TasteProfileBase):
    """
    Returned to frontend, deserialized JSON list fields.
    """
    id : int
    user_id : int
    created_at : datetime
    updated_at : datetime

    @property
    def flavor_list(self) -> list[str]:
        return json.loads(self.flavors)
    def region_list(self) -> list[str]:
        return json.loads(self.regions)
    def type_list(self) -> list[str]:
        return json.loads(self.types)
    

### Recommendations
class RecommendedWine(SQLModel, table = True):
    id : Optional[int] = Field(default = None, primary_key = True)
    recommendation_id : int = Field(foreign_key = "recommendation.id")
    rank : int = Field(default = 1)

    # Wine Characteristics
    wine_name : str
    winery : Optional[str]
    varietal : Optional[str]
    region : Optional[str]
    country : Optional[str]
    
    # Attributes from Base Dataset
    points : Optional[int] = Field(default = None, ge = 0, le = 100)
    price : Optional[float] = Field(default = None, ge = 0)
    description : Optional[float] = None

    # Rational from LLM
    rationale : Optional[str] = None

    # Vivino Display Data 
    vivino_price : Optional[str] = None
    vivino_thumb : Optional[str] = None
    vivino_link : Optional[str] = None
    vivino_rating : Optional[str] = None
    vivino_name : Optional[str] = None

    # Relationship
    recommendation: Optional["Recommendation"] = Relationship(back_populates="wines")

class Recommendation:
    """
    One recommendation, containing specific wines
    """
    id : Optional[int] = Field(default = None, primary_key = True)
    user_id : int = Field(foreign_key = "user.id")
    created_at : datetime = Field(default_factory=datetime.utc)

    # user input query
    query_text : Optional[str]

    # LLM response, mostly for debugging
    response_text : Optional[str] = None

    user: Optional[User] = Relationship(back_populates="recommendations")
    wines: list[RecommendedWine] = Relationship(back_populates="recommendation")

class RecommendationCreate(SQLModel):
    user_id: int
    query_text: str
 
 
class RecommendationRead(SQLModel):
    id: int
    user_id: int
    query_text: str
    created_at: datetime
    llm_raw_response: Optional[str]
    wines: list[RecommendedWine] = []



