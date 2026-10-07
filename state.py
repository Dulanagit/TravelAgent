from typing import List, Optional, Dict, Any, TypedDict
from pydantic import BaseModel, Field

class TravelConstraints(BaseModel):
    destination: Optional[str] = Field(default=None, description="The intended destination of the trip")
    start_date: Optional[str] = Field(default=None, description="The start date of the trip (e.g., YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="The end date of the trip (e.g., YYYY-MM-DD)")
    budget: Optional[float] = Field(default=None, description="The maximum budget for the trip")

class Hotel(BaseModel):
    name: str
    price_per_night: float
    rating: float
    score: Optional[float] = None

class TravelState(TypedDict):
    query: str
    constraints: TravelConstraints
    is_complete: bool
    missing_fields: List[str]
    real_hotels: List[Dict[str, Any]]
    weather_data: Dict[str, Any]
    news_context: str
    activities: List[Dict[str, Any]]
    top_hotels: List[Dict[str, Any]]
    itinerary: List[Dict[str, Any]]
    user_approved: bool
    booking_confirmation: Optional[str]
