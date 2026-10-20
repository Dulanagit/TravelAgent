# 🗺️ TravelAgent — Agent Flow Diagram

This diagram reflects the actual LangGraph workflow defined in [`graph.py`](./graph.py).

---

## Agent Graph

```mermaid
flowchart TD
    START(["🚀 START"])

    subgraph Chatbot ["🤖 Chatbot Node (Information Gathering Agent)"]
        CB["chatbot_node\n─────────────────\nLLM: llm_with_tools\nGathers: destination, dates,\nbudget, companions,\nvibe, transport_mode\nOutputs READY when complete"]
    end

    subgraph Tools ["🔧 Tool Node (LangGraph ToolNode)"]
        T1["check_weather(city)\n→ Open-Meteo API"]
        T2["search_transport_options(mode)\n→ Mock data"]
    end

    subgraph Planner ["📅 Planner Node"]
        PN["planner_node\n─────────────────\nParses constraints from messages\nCalls: search_hotels()\nCalls: get_places_to_visit()\nCalls: get_sri_lanka_weather()\nUpdates: real_hotels, activities,\nweather_data, phase=planning"]
    end

    subgraph Evaluator ["⭐ Evaluator Agent Node"]
        EN["evaluator_agent_node\n─────────────────\nScores hotels via SCORING_WEIGHTS\nScores activities (rain penalty)\nTop 3 hotels selected\nLLM builds day-by-day itinerary JSON\nUpdates: top_hotels, itinerary,\nphase=review"]
    end

    subgraph HITL ["🧑 Human-in-the-Loop (HITL) Node"]
        HN["hitl_node\n─────────────────\nPresents itinerary for approval\n⚠️ Graph is INTERRUPTED here\n(interrupt_before=[hitl])\nWaits for user_approved flag"]
    end

    END(["🏁 END"])

    %% Entry
    START --> CB

    %% Chatbot routing (route_chatbot)
    CB -- "has tool_calls" --> Tools
    CB -- "AIMessage contains 'READY'" --> Planner
    CB -- "waiting for user input" --> END

    %% Tools loop back to chatbot
    Tools --> CB

    %% Linear pipeline
    Planner --> Evaluator
    Evaluator --> HITL

    %% HITL routing (route_hitl)
    HITL -- "user_approved = True" --> END
    HITL -- "user_approved = False\n(feedback injected into messages)" --> Planner
```

---

## Node Descriptions

| Node | Role | LLM Used |
|---|---|---|
| **chatbot** | Information Gathering Agent — collects all 6 travel constraints from the user via natural conversation | `llm_with_tools` (Groq, temp=0) |
| **tools** | LangGraph `ToolNode` — executes tool calls made by the chatbot | — |
| **planner** | Fetches real hotels (Booking.com/Google), activities (DuckDuckGo scrape), and weather data | — (API calls only) |
| **evaluator** | Scores & ranks hotels and activities; uses LLM to produce a structured day-by-day itinerary | `planner_llm` (Groq, temp=0.2) |
| **hitl** | Presents the plan to the user; graph is **interrupted** here until the user approves or rejects | — |

---

## Tools Available to Chatbot

| Tool | Description | Data Source |
|---|---|---|
| `check_weather(city)` | Fetches real-time weather for a Sri Lankan city | Open-Meteo API (geocoding + forecast) |
| `search_transport_options(mode)` | Returns transport options for `rent_car` or `public_transport` | Mock data |

---

## External API Integrations (called by Planner)

| Function | Purpose | Source |
|---|---|---|
| `search_hotels()` | Searches real hotels by city & dates | Booking.com via RapidAPI → fallback to Google Places API |
| `get_places_to_visit()` | Finds activities matching user vibe | DuckDuckGo search + BeautifulSoup scrape (TripAdvisor / Reddit) |
| `get_sri_lanka_weather()` | Weather data for scoring | Open-Meteo API |
| `get_current_news()` | Sri Lanka news context | DuckDuckGo News (available but not wired into graph currently) |

---

## State Shape ([`state.py`](./state.py))

```
TravelState
├── messages          – conversation history (add_messages reducer)
├── constraints       – TravelConstraints (destination, dates, budget, companions, vibe, transport_mode)
├── phase             – "gathering" | "planning" | "review" | "booking" | "end"
├── weather_checked / weather_approved_by_user
├── real_hotels       – raw hotel list from API
├── hotel_search_error
├── weather_data      – {temperature, is_raining, city}
├── news_context
├── activities        – scored activity list
├── top_hotels        – top 3 scored hotels
├── itinerary         – final day-by-day plan
├── user_approved     – HITL approval flag
└── booking_confirmation
```

---

## WebSocket API Flow ([`main.py`](./main.py))

```mermaid
sequenceDiagram
    participant UI as Browser (WebSocket)
    participant BE as FastAPI /ws/agent
    participant LG as LangGraph App

    UI->>BE: action=chat, message="..."
    BE->>LG: astream(HumanMessage)
    LG-->>BE: chatbot node update → chat_response
    LG-->>BE: tools node update → system_event
    LG-->>BE: planner node update → system_event
    LG-->>BE: evaluator node update → system_event
    Note over LG: Graph pauses at HITL
    BE-->>UI: node=hitl, state={itinerary, top_hotels, ...}

    alt User Approves
        UI->>BE: action=approve
        BE->>LG: update_state(user_approved=True) + resume
        LG-->>BE: END
        BE-->>UI: node=end, state={...}
    else User Rejects
        UI->>BE: action=reject, feedback="..."
        BE->>LG: update_state(user_approved=False) + feedback message
        LG-->>BE: re-runs planner → evaluator → hitl
        BE-->>UI: node=hitl, state={new itinerary...}
    end
```
