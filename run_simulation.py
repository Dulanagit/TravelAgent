from graph import app
from state import TravelConstraints
import json

def print_state(step_name: str, state: dict):
    print(f"\n{'='*50}")
    print(f"STATE AFTER: {step_name}")
    print(f"{'='*50}")
    
    # We serialize to JSON for clean formatting, filtering out non-serializable objects if any
    # Pydantic models need to be dumped to dict
    clean_state = {}
    for k, v in state.items():
        if hasattr(v, 'dict'):
            clean_state[k] = v.dict()
        else:
            clean_state[k] = v
            
    print(json.dumps(clean_state, indent=2))
    print("\n")

def run_simulation():
    print("Starting Travel Agent Simulation...\n")
    
    # Mock user query that only has partial information
    # Missing start_date, end_date, and budget
    initial_state = {
        "query": "I want to go to Colombo.",
        "constraints": TravelConstraints(destination=None, start_date=None, end_date=None, budget=None),
        "is_complete": False,
        "missing_fields": [],
        "real_hotels": [],
        "weather_data": {},
        "news_context": "",
        "activities": [],
        "top_hotels": [],
        "itinerary": [],
        "user_approved": True,  # Mocking that the user will approve the hotels in HITL
        "booking_confirmation": None
    }
    
    print_state("INITIAL INPUT", initial_state)
    
    # Use LangGraph's stream to see the state after each node executes
    for output in app.stream(initial_state):
        # output is a dict where the key is the node name and the value is the state returned by that node
        for node_name, state in output.items():
            print_state(f"NODE: {node_name.upper()}", state)
            
if __name__ == "__main__":
    run_simulation()
