"""
FastAPI Server Bridge.
Exposes REST and SSE/WebSocket endpoints so the React Web Dashboard
can monitor traffic signals, road zones, ambulance alerts, and trigger overrides.
"""

import threading
import time
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Smart Traffic Vision & IoT Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared global state
shared_state = {
    "system_mode": "NORMAL",             # NORMAL | TRANSITION_YELLOW | EMERGENCY
    "active_road": "A",                  # Road currently green (A, B, C)
    "transition_target": None,           # Road transitioning to
    "transition_remaining_sec": 0.0,     # 2s countdown
    "lights": {
        "A": "GREEN",
        "B": "RED",
        "C": "RED"
    },
    "emergency_vehicle_detected": False,
    "detected_road": None,
    "vehicle_confidence": 0.0,
    "esp32_connected": False,
    "esp32_ip": "192.168.1.100",
    "uno_connected": False,
    "hospital_gate_open": False,
    "ultrasonic_distance_cm": 95,
    "fps": 30.0,
    "total_emergencies_cleared": 0,
    "active_booking": None
}

class BookingRequest(BaseModel):
    patient_name: str
    contact: str
    pickup_road: str
    destination_hospital: str
    severity: str

@app.get("/api/state")
def get_state():
    return shared_state

@app.post("/api/emergency/trigger")
def trigger_emergency(road: str):
    road = road.upper()
    if road in ["A", "B", "C"]:
        shared_state["manual_override"] = road
        return {"status": "success", "road": road}
    return {"status": "error", "message": "Invalid road"}

@app.post("/api/emergency/reset")
def reset_emergency():
    shared_state["manual_reset"] = True
    return {"status": "success"}

@app.post("/api/gate/toggle")
def toggle_gate(open_gate: bool):
    shared_state["hospital_gate_open"] = open_gate
    return {"status": "success", "gate_open": open_gate}

@app.post("/api/booking/create")
def create_booking(booking: BookingRequest):
    booking_data = booking.dict()
    booking_data["id"] = f"AMB-{int(time.time())}"
    booking_data["status"] = "DISPATCHED"
    booking_data["timestamp"] = time.strftime("%H:%M:%S")
    shared_state["active_booking"] = booking_data
    return {"status": "success", "booking": booking_data}

@app.post("/api/booking/update_status")
def update_booking_status(status: str):
    if shared_state["active_booking"]:
        shared_state["active_booking"]["status"] = status
        return {"status": "success", "booking": shared_state["active_booking"]}
    return {"status": "error", "message": "No active booking"}

def run_api_server(host="0.0.0.0", port=8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="warning")

def start_api_server_background():
    server_thread = threading.Thread(target=run_api_server, daemon=True)
    server_thread.start()
    print("[API-BRIDGE] FastAPI Server started at http://localhost:8000")
    return server_thread
