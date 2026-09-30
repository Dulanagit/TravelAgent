# Travel Agent - Agentic Workflow Diagram

graph TD
    START((Start)) --> EXTRACT[Extraction Node: Parse constraints into strict JSON]
    EXTRACT --> CHECK{Are constraints complete?}
    CHECK -- No --> ASK[Pause: Ask user for missing dates/budget]
    ASK --> EXTRACT
    CHECK -- Yes --> API[API Execution Node: Fetch mock hotel data]
    API --> EVAL[Evaluator Agent: Score hotels and filter to Top 2]
    EVAL --> HITL((Human-in-the-Loop Checkpoint))
    HITL --> APPROVAL{User Decision}
    APPROVAL -- Reject/Modify --> EXTRACT
    APPROVAL -- Approve --> BOOK[Booking Node: Execute mock POST request]
    BOOK --> END((End: Itinerary Confirmed))
