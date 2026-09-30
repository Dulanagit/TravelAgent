from langgraph.graph import StateGraph, END
from state import TravelState, TravelConstraints
import uuid

def extract_node(state: TravelState) -> TravelState:
    """Extraction Node: Parse constraints into strict JSON (mocked)"""
    constraints = state.get("constraints")
    if not constraints:
        constraints = TravelConstraints()
    
    missing = []
    if not constraints.destination:
        if "paris" in state.get("query", "").lower():
            constraints.destination = "Paris"
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
        constraints.destination = "Paris"
    if "start_date" in missing:
        constraints.start_date = "2024-05-01"
    if "end_date" in missing:
        constraints.end_date = "2024-05-10"
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

def api_execution_node(state: TravelState) -> TravelState:
    """API Execution Node: Fetch mock hotel data"""
    mock_hotels = [
        {"name": "Le Meurice", "price_per_night": 500, "rating": 4.8},
        {"name": "Ritz Paris", "price_per_night": 800, "rating": 4.9},
        {"name": "Ibis Styles", "price_per_night": 100, "rating": 4.0},
        {"name": "Novotel", "price_per_night": 150, "rating": 4.2}
    ]
    return {**state, "mock_hotels": mock_hotels}

def evaluator_agent_node(state: TravelState) -> TravelState:
    """Evaluator Agent: Score hotels and filter to Top 2"""
    hotels = state.get("mock_hotels", [])
    budget = state.get("constraints").budget if state.get("constraints") else 1000
    
    scored_hotels = []
    for h in hotels:
        # Simple evaluation logic: score = rating - cost penalty
        est_cost = h["price_per_night"] * 9 # Assuming 9 nights stay
        score = h["rating"] * 10
        if est_cost > budget:
            score -= 20 # Penalty for exceeding budget
        h["score"] = score
        scored_hotels.append(h)
        
    scored_hotels.sort(key=lambda x: x["score"], reverse=True)
    top_2 = scored_hotels[:2]
    
    return {**state, "top_hotels": top_2}

def hitl_node(state: TravelState) -> TravelState:
    """Human-in-the-Loop Checkpoint"""
    print(f"\n[HITL Node] Checkpoint. Top hotels presented to user:")
    for h in state.get('top_hotels', []):
        print(f"  - {h['name']} (${h['price_per_night']}/night, Score: {h['score']})")
    
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
        "yes": "api",
        "no": "ask"
    }
)
workflow.add_edge("ask", "extract")
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
