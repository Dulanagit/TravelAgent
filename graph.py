from langgraph.graph import StateGraph, END
from state import TravelState, TravelConstraints
import uuid
from api_integrations import (
    get_sri_lanka_weather,
    get_current_news,
    search_hotels,
    get_places_to_visit
)
from scoring_config import SCORING_WEIGHTS, SEARCH_CONSTRAINTS

def extract_node(state: TravelState) -> TravelState:
    """Extraction Node: Parse constraints into strict JSON"""
    constraints = state.get("constraints")
    if not constraints:
        constraints = TravelConstraints()
    
    missing = []
    
    # Enforce Sri Lanka constraint
    country_limit = SEARCH_CONSTRAINTS.get("country_limit", "Sri Lanka")
    
    if not constraints.destination:
        if "colombo" in state.get("query", "").lower():
            constraints.destination = "Colombo"
        elif "kandy" in state.get("query", "").lower():
            constraints.destination = "Kandy"
        else:
            missing.append("destination")
    
    if not constraints.start_date:
        missing.append("start_date")
    if not constraints.end_date:
        missing.append("end_date")
    if not constraints.budget:
        missing.append("budget")
        
    return {
        **state,
        "constraints": constraints,
        "is_complete": len(missing) == 0,
        "missing_fields": missing
    }

def ask_node(state: TravelState) -> TravelState:
    """Pause: Ask user for missing dates/budget"""
    constraints = state.get("constraints", TravelConstraints())
    missing = state.get("missing_fields", [])
    
    print(f"\n[Ask Node] Requesting missing info from user: {missing}")
    
    # Mock user input filling missing fields
    if "destination" in missing:
        constraints.destination = "Colombo"
    if "start_date" in missing:
        constraints.start_date = "2026-11-01"
    if "end_date" in missing:
        constraints.end_date = "2026-11-10"
    if "budget" in missing:
        constraints.budget = 2000.0
        
    return {
        **state,
        "constraints": constraints,
    }

def check_constraints(state: TravelState) -> str:
    """Are constraints complete?"""
    if state.get("is_complete"):
        return "yes"
    return "no"

def environmental_awareness_node(state: TravelState) -> TravelState:
    """Fetches real-time weather and news."""
    print(f"\n[Environmental Node] Fetching real-time weather and news for Sri Lanka...")
    city = state["constraints"].destination
    weather = get_sri_lanka_weather(city)
    news = get_current_news("Sri Lanka political economic situation")
    
    return {
        **state,
        "weather_data": weather,
        "news_context": news
    }

def api_execution_node(state: TravelState) -> TravelState:
    """API Execution Node: Fetch real hotels and activities"""
    print(f"\n[API Node] Fetching real hotels and activities...")
    city = state["constraints"].destination
    start_date = state["constraints"].start_date
    end_date = state["constraints"].end_date
    budget = state["constraints"].budget
    
    hotels = search_hotels(city, start_date, end_date, budget)
    activities = get_places_to_visit(city, "sightseeing food")
    
    return {
        **state, 
        "real_hotels": hotels,
        "activities": activities
    }

def evaluator_agent_node(state: TravelState) -> TravelState:
    """Evaluator Agent: Score hotels and activities using config"""
    print(f"\n[Evaluator Node] Scoring based on config and real-world data...")
    hotels = state.get("real_hotels", [])
    activities = state.get("activities", [])
    budget = state.get("constraints").budget if state.get("constraints") else 1000
    weather = state.get("weather_data", {})
    
    # Evaluate Hotels
    hotel_weights = SCORING_WEIGHTS["hotel"]
    scored_hotels = []
    for h in hotels:
        # Simple evaluation logic using config
        est_cost = h["price_per_night"] * 9 # Mock stay length
        score = h["rating"] * hotel_weights["rating_weight"]
        if est_cost > budget:
            overage = est_cost - budget
            score -= (overage * hotel_weights["budget_penalty_per_dollar"])
        h["score"] = score
        scored_hotels.append(h)
        
    scored_hotels.sort(key=lambda x: x["score"], reverse=True)
    top_2_hotels = scored_hotels[:2]
    
    # Evaluate Activities (apply weather penalty)
    weather_weights = SCORING_WEIGHTS["weather"]
    scored_activities = []
    for a in activities:
        score = 100 # Base score
        if weather.get("is_raining") and a.get("type") == "Sightseeing":
            score += weather_weights["rain_penalty"]
            print(f"  -> Applying rain penalty to {a['name']}")
        a["score"] = score
        scored_activities.append(a)
    
    scored_activities.sort(key=lambda x: x["score"], reverse=True)
    
    # Build Itinerary
    itinerary = []
    if top_2_hotels:
        itinerary.append({"day": "1-9", "type": "Accommodation", "details": top_2_hotels[0]})
    
    max_activities = SEARCH_CONSTRAINTS["max_activities_per_day"]
    for i, a in enumerate(scored_activities[:max_activities]):
        itinerary.append({"day": "1", "type": "Activity", "details": a})
        
    return {
        **state, 
        "top_hotels": top_2_hotels,
        "itinerary": itinerary
    }

def hitl_node(state: TravelState) -> TravelState:
    """Human-in-the-Loop Checkpoint"""
    print(f"\n[HITL Node] Checkpoint. Proposed Itinerary:")
    for item in state.get('itinerary', []):
        if item["type"] == "Accommodation":
            h = item["details"]
            print(f"  - STAY: {h['name']} (${h['price_per_night']}/night, Score: {h.get('score')})")
        else:
            a = item["details"]
            print(f"  - DO:   {a['name']} (Score: {a.get('score')})")
            
    print("\nWeather Alert:")
    weather = state.get("weather_data", {})
    print(f"  - Temp: {weather.get('temperature')}C, Raining: {weather.get('is_raining')}")
    
    # Note: user_approved is set in initial state for simulation
    return state

def check_approval(state: TravelState) -> str:
    """User Decision"""
    if state.get("user_approved", True):
        return "approve"
    return "reject"

def booking_node(state: TravelState) -> TravelState:
    """Booking Node: Execute mock POST request"""
    return {
        **state,
        "booking_confirmation": f"CONFIRMATION-{uuid.uuid4().hex[:8].upper()}"
    }

# Workflow Initialization
workflow = StateGraph(TravelState)

# Add nodes
workflow.add_node("extract", extract_node)
workflow.add_node("ask", ask_node)
workflow.add_node("env_awareness", environmental_awareness_node)
workflow.add_node("api", api_execution_node)
workflow.add_node("evaluator", evaluator_agent_node)
workflow.add_node("hitl", hitl_node)
workflow.add_node("booking", booking_node)

# Entry point
workflow.set_entry_point("extract")

# Edges & Routing
workflow.add_conditional_edges(
    "extract",
    check_constraints,
    {
        "yes": "env_awareness",
        "no": "ask"
    }
)
workflow.add_edge("ask", "extract")
workflow.add_edge("env_awareness", "api")
workflow.add_edge("api", "evaluator")
workflow.add_edge("evaluator", "hitl")

workflow.add_conditional_edges(
    "hitl",
    check_approval,
    {
        "approve": "booking",
        "reject": "extract"
    }
)
workflow.add_edge("booking", END)

# Compile graph
app = workflow.compile()
