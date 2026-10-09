import os
import json
from typing import Literal
from dotenv import load_dotenv

# Load .env FIRST so GROQ_API_KEY is available before ChatGroq is instantiated
load_dotenv()

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_groq import ChatGroq
from state import TravelState, TravelConstraints
from api_integrations import (
    get_sri_lanka_weather,
    get_current_news,
    search_hotels,
    get_places_to_visit
)
from scoring_config import SCORING_WEIGHTS, SEARCH_CONSTRAINTS

# --- Tools ---

@tool
def check_weather(city: str) -> str:
    """Check the weather for a given city in Sri Lanka. Use this to warn users if it's raining."""
    weather = get_sri_lanka_weather(city)
    return json.dumps(weather)

@tool
def search_transport_options(transport_mode: str) -> str:
    """Searches for public transport or rental car options based on the user's preference."""
    # Simple mock for now
    if transport_mode == "rent_car":
        return "Found 3 rental car options: Malkey Rent-A-Car ($30/day), Casons Rent-A-Car ($35/day)."
    elif transport_mode == "public_transport":
        return "Trains are available from Colombo Fort. Express trains take 3 hours to Kandy, 2 hours to Galle."
    return "No specific transport info found."

tools = [check_weather, search_transport_options]
tool_node = ToolNode(tools)

# --- LLM Setup ---
llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
llm_with_tools = llm.bind_tools(tools)
planner_llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0.2)

# --- Nodes ---

def chatbot_node(state: TravelState) -> dict:
    """Information Gathering Agent"""
    messages = state.get("messages", [])
    
    # System prompt to guide the LLM
    sys_msg = SystemMessage(content='''You are an intelligent Travel Agent for Sri Lanka.
Your goal is to gather the following required constraints from the user before planning an itinerary:
1. Destination (City in Sri Lanka)
2. Start Date and End Date
3. Budget
4. Companions (e.g. solo, partner, family)
5. Vibe/Preferences (e.g. relaxing, adventure)
6. Transport Mode (e.g. rent_car, public_transport, own_vehicle)

If any of these are missing, ask the user naturally. 
IMPORTANT: Once you have the destination and dates, YOU MUST use the `check_weather` tool to check the weather. If it's raining, warn the user and ask if they want to proceed.
Once you have ALL constraints AND you have checked the weather, and the user is ready to proceed, output EXACTLY the word "READY" at the end of your message.''')
    
    response = llm_with_tools.invoke([sys_msg] + messages)
    
    return {"messages": [response]}

def parse_constraints(messages: list) -> TravelConstraints:
    """A helper to parse constraints from the conversation history using a structured output."""
    # We use a structured output LLM to extract constraints from the chat history
    structured_llm = llm.with_structured_output(TravelConstraints)
    sys_msg = SystemMessage(content="Extract the travel constraints from the conversation. If a constraint is not explicitly stated, leave it null/None.")
    constraints = structured_llm.invoke([sys_msg] + messages)
    return constraints

def planner_node(state: TravelState) -> dict:
    """Planner Agent: Uses constraints to build an itinerary."""
    constraints = state.get("constraints")
    # If constraints aren't properly populated yet, try parsing them from messages
    if not constraints or not constraints.destination:
        constraints = parse_constraints(state["messages"])
    
    print(f"\n[Planner Node] Drafting itinerary for {constraints.destination}...")
    
    # Fetch real hotels and activities
    city = constraints.destination or "Colombo"
    start_date = constraints.start_date or "2026-11-01"
    end_date = constraints.end_date or "2026-11-10"
    budget = constraints.budget or 1000.0
    vibe = constraints.vibe or "sightseeing"
    
    hotels = search_hotels(city, start_date, end_date, budget)
    activities = get_places_to_visit(city, vibe)
    weather = get_sri_lanka_weather(city)
    
    return {
        "constraints": constraints,
        "real_hotels": hotels,
        "activities": activities,
        "weather_data": weather,
        "phase": "planning"
    }

def evaluator_agent_node(state: TravelState) -> dict:
    """Evaluator Agent: Score hotels and activities"""
    print(f"\n[Evaluator Node] Scoring based on config and real-world data...")
    hotels = state.get("real_hotels", [])
    activities = state.get("activities", [])
    budget = state.get("constraints").budget if state.get("constraints") else 1000
    weather = state.get("weather_data", {})
    
    hotel_weights = SCORING_WEIGHTS["hotel"]
    scored_hotels = []
    for h in hotels:
        est_cost = h.get("price_per_night", 50) * 5 # Approx nights
        score = h.get("rating", 3) * hotel_weights["rating_weight"]
        if est_cost > budget:
            overage = est_cost - budget
            score -= (overage * hotel_weights["budget_penalty_per_dollar"])
        h["score"] = score
        scored_hotels.append(h)
        
    scored_hotels.sort(key=lambda x: x["score"], reverse=True)
    top_2_hotels = scored_hotels[:2]
    
    weather_weights = SCORING_WEIGHTS["weather"]
    scored_activities = []
    for a in activities:
        score = 100
        if weather.get("is_raining") and a.get("type", "") == "Sightseeing":
            score += weather_weights["rain_penalty"]
        a["score"] = score
        scored_activities.append(a)
    
    scored_activities.sort(key=lambda x: x["score"], reverse=True)
    
    itinerary = []
    if top_2_hotels:
        itinerary.append({"day": "Whole Trip", "type": "Accommodation", "details": top_2_hotels[0]})
    
    max_activities = SEARCH_CONSTRAINTS["max_activities_per_day"]
    for i, a in enumerate(scored_activities[:max_activities]):
        itinerary.append({"day": f"Day {i+1}", "type": "Activity", "details": a})
        
    return {
        "top_hotels": top_2_hotels,
        "itinerary": itinerary,
        "phase": "review"
    }

def hitl_node(state: TravelState) -> dict:
    """Human-in-the-Loop Checkpoint"""
    print(f"\n[HITL Node] Presenting proposed itinerary for approval...")
    return state

def booking_node(state: TravelState) -> dict:
    """Booking Node: Finalize"""
    import uuid
    print(f"\n[Booking Node] Finalizing bookings...")
    return {
        "booking_confirmation": f"CONFIRMATION-{uuid.uuid4().hex[:8].upper()}",
        "phase": "booking"
    }

# --- Routing ---

def route_chatbot(state: TravelState) -> Literal["tools", "planner", "__end__"]:
    """Route from chatbot to either tools, planner, or interrupt for user."""
    messages = state["messages"]
    last_message = messages[-1]
    
    if last_message.tool_calls:
        return "tools"
    
    if isinstance(last_message, AIMessage) and "READY" in str(last_message.content):
        return "planner"
    
    # Otherwise, we wait for the user to reply
    return "__end__"

def route_hitl(state: TravelState) -> Literal["booking", "planner"]:
    """User Decision on Itinerary"""
    if state.get("user_approved", True):
        return "booking"
    return "planner"

# --- Workflow Initialization ---
workflow = StateGraph(TravelState)

workflow.add_node("chatbot", chatbot_node)
workflow.add_node("tools", tool_node)
workflow.add_node("planner", planner_node)
workflow.add_node("evaluator", evaluator_agent_node)
workflow.add_node("hitl", hitl_node)
workflow.add_node("booking", booking_node)

workflow.set_entry_point("chatbot")

workflow.add_conditional_edges("chatbot", route_chatbot)
workflow.add_edge("tools", "chatbot")
workflow.add_edge("planner", "evaluator")
workflow.add_edge("evaluator", "hitl")
workflow.add_conditional_edges("hitl", route_hitl)
workflow.add_edge("booking", END)

from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
app = workflow.compile(
    checkpointer=memory,
    interrupt_before=["hitl"]
)
