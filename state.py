from typing import List, Optional, Dict, Any, TypedDict, Annotated, Literal
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage

class TravelConstraints(BaseModel):
    destination: Optional[str] = Field(default=None, description="The intended destination of the trip")
    start_date: Optional[str] = Field(default=None, description="The start date of the trip (e.g., YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="The end date of the trip (e.g., YYYY-MM-DD)")
    budget: Optional[float] = Field(default=None, description="The maximum budget for the trip")
    companions: Optional[str] = Field(default=None, description="Who they are traveling with (e.g., solo, partner, family)")
    vibe: Optional[str] = Field(default=None, description="The preferred vibe or type of plan (e.g., relaxing, adventure, historical)")
    transport_mode: Optional[str] = Field(default=None, description="Preferred transport mode (e.g., rent_car, public_transport, own_vehicle)")

class Hotel(BaseModel):
    name: str
    price_per_night: float
    rating: float
    score: Optional[float] = None

class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    constraints: TravelConstraints
    phase: Literal["gathering", "planning", "review", "booking", "end"]
    weather_checked: bool
    weather_approved_by_user: bool
    
    # Existing fields required by the planner and evaluator
    query: str # Can keep it just in case, though messages replaces it
    real_hotels: List[Dict[str, Any]]
    hotel_search_error: Optional[str]
    weather_data: Dict[str, Any]
    news_context: str
    activities: List[Dict[str, Any]]
    top_hotels: List[Dict[str, Any]]
    itinerary: List[Dict[str, Any]]
    user_approved: bool
    booking_confirmation: Optional[str]
