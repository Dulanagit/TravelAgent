import json
import uuid
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from graph import app as langgraph_app
from state import TravelConstraints
from langchain_core.messages import AIMessage, HumanMessage

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

def sanitize_state(state: dict) -> dict:
    clean_state = {}
    for k, v in state.items():
        if k == "messages":
            continue # Don't send entire message history to UI
        if hasattr(v, 'model_dump'):
            clean_state[k] = v.model_dump()
        elif hasattr(v, 'dict'):
            clean_state[k] = v.dict()
        else:
            clean_state[k] = v
    return clean_state

@app.websocket("/ws/agent")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        while True:
            data = await websocket.receive_text()
            request_data = json.loads(data)
            action = request_data.get("action")
            
            input_dict = None
            
            if action == "chat":
                msg_content = request_data.get("message", "")
                if msg_content:
                    input_dict = {"messages": [HumanMessage(content=msg_content)]}
                    
            elif action == "approve":
                langgraph_app.update_state(config, {"user_approved": True})
                input_dict = None # Resume with None
                
            elif action == "reject":
                feedback = request_data.get("feedback", "Rejected")
                langgraph_app.update_state(config, {"user_approved": False, "messages": [HumanMessage(content=f"Itinerary Feedback: {feedback}")]})
                input_dict = None
            
            # Stream the graph
            async for output in langgraph_app.astream(input_dict, config=config, stream_mode="updates"):
                for node_name, state_update in output.items():
                    if node_name == "chatbot":
                        if "messages" in state_update and state_update["messages"]:
                            last_msg = state_update["messages"][-1]
                            if isinstance(last_msg, AIMessage) and last_msg.content:
                                content = last_msg.content.replace("READY", "").strip()
                                if content:
                                    await websocket.send_json({
                                        "node": "chat_response",
                                        "message": content
                                    })
                    elif node_name == "tools":
                        await websocket.send_json({
                            "node": "system_event",
                            "message": "Agent is searching for information..."
                        })
                    elif node_name == "planner":
                        await websocket.send_json({
                            "node": "system_event",
                            "message": "Drafting your custom itinerary..."
                        })
                    elif node_name == "evaluator":
                        await websocket.send_json({
                            "node": "system_event",
                            "message": "Evaluating options..."
                        })
                    elif node_name == "booking":
                        await websocket.send_json({
                            "node": "system_event",
                            "message": "Finalizing bookings!"
                        })
                        
            # After streaming finishes for the current step, check if we are paused at HITL
            snapshot = langgraph_app.get_state(config)
            if snapshot.next and "hitl" in snapshot.next:
                clean_state = sanitize_state(snapshot.values)
                await websocket.send_json({
                    "node": "hitl",
                    "state": clean_state
                })
            elif not snapshot.next and "booking_confirmation" in snapshot.values:
                # Finished
                clean_state = sanitize_state(snapshot.values)
                await websocket.send_json({
                    "node": "end",
                    "state": clean_state
                })
                
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        error_msg = str(e)
        print(f"Error: {error_msg}")
        traceback.print_exc()
        try:
            # Send error to UI as a chat message instead of disconnecting
            await websocket.send_json({
                "node": "chat_response",
                "message": f"⚠️ Agent error: {error_msg}"
            })
        except Exception:
            await websocket.close()

@app.get("/health")
def health_check():
    return {"status": "ok"}
