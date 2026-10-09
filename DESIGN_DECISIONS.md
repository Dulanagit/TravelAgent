# AI Travel Agent: Design Decisions & Architecture

This document tracks the technical decisions made while building this conversational travel agent.

## Architecture Pattern: Conversational Agent with LangGraph

We have moved from a rigid, static DAG (where extraction and API calls happen in a fixed sequence) to a dynamic, LLM-powered **Conversational Agentic Workflow**.

### Core Flow & Graph Nodes

```mermaid
graph TD
    START((Start)) --> CHATBOT[Information Gathering Agent]
    
    CHATBOT --> |Requires Weather/Transport Info| TOOLS[Execute Tools]
    TOOLS --> CHATBOT
    
    CHATBOT --> |Needs User Input| USER_INPUT((Wait for User Reply))
    USER_INPUT --> CHATBOT
    
    CHATBOT --> |All Constraints Met| PLANNER[Planner Agent]
    
    PLANNER --> EVALUATOR[Evaluator Agent]
    EVALUATOR --> HITL((Human-in-the-Loop))
    
    HITL --> |User Requests Changes| PLANNER
    HITL --> |User Approves| BOOKING[Booking Agent]
    BOOKING --> END((End))
```

### Agent Roles

1. **Information Gathering Agent (Chatbot)**
   - **Role**: Converses with the user to dynamically fill out required constraints (Destination, Dates, Budget, Companions, Vibe, Transport).
   - **Capabilities**: Uses tools (`check_weather`, `search_transport_options`) to gather contextual information. For example, if the user mentions Colombo, it automatically checks the weather. If it's raining, it warns the user before proceeding to planning.
   - **LLM**: Powered by Groq (`llama3-70b-8192`) using `bind_tools`.

2. **Planner Agent**
   - **Role**: Once the chatbot determines all constraints are filled and the user is ready, the Planner Agent kicks in. It fetches real hotels (via RapidAPI) and activities (via DuckDuckGo) based on the user's constraints.
   - **Error Handling**: If the RapidAPI hotel search fails (e.g., API key missing, destination not found, no hotels match), it no longer falls back to mock data. Instead, it captures the error in `hotel_search_error` state variable.
   
3. **Evaluator Agent**
   - **Role**: Scores the drafted itinerary based on predefined rules (e.g., budget penalties, rain penalties for sightseeing). It includes the hotel search error (if any) in its output state.

4. **Human-in-the-Loop (HITL) Checkpoint**
   - **Role**: Pauses the execution. If a hotel search error occurred, it explicitly shows a warning (⚠️ Hotel Search Failed) in the UI so the user knows they need to search for accommodations themselves.

## State Management (`state.py`)
We use LangGraph's `add_messages` reducer to maintain a persistent chat history across the websocket connection. The `MemorySaver` checkpointer ensures that when the graph pauses at the HITL node, it perfectly resumes upon receiving the user's decision.

## UI/UX (WebSocket)
The frontend (`static/index.html`) is a chat interface that streams AI responses. When the `hitl` node is reached, the chat input is hidden, and an interactive itinerary review box is displayed. 
