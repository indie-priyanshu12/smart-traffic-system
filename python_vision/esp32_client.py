"""
ESP32 WiFi REST Client.
Sends emergency vehicle signals and status queries to the ESP32 over WiFi asynchronously.
"""

import time
import threading
import requests
from config import ESP32_BASE_URL, ESP32_IP

class ESP32Client:
    def __init__(self, base_url: str = ESP32_BASE_URL):
        self.base_url = base_url
        self.is_connected = False
        self.mock_mode = False
        self.last_attempt_time = 0
        self.retry_interval = 8.0 # Throttle reconnection attempts when offline
        self.mock_status = {
            "mode": "NORMAL",
            "active_road": "A",
            "roadA": "GREEN",
            "roadB": "RED",
            "roadC": "RED"
        }

    def set_ip(self, ip_address: str):
        """Update ESP32 IP address dynamically."""
        self.base_url = f"http://{ip_address}:80"
        print(f"[ESP32] Updated target IP to: {self.base_url}")

    def _async_post(self, url: str):
        """Send HTTP POST in a background thread so the video pipeline never drops FPS."""
        def worker():
            try:
                resp = requests.post(url, timeout=0.8)
                self.is_connected = (resp.status_code == 200)
            except Exception as e:
                self.is_connected = False
                if not self.mock_mode:
                    print(f"[ESP32-CLIENT] Note: ESP32 offline at {self.base_url}. Using local simulation.")
                    self.mock_mode = True
        threading.Thread(target=worker, daemon=True).start()

    def check_connection(self) -> bool:
        """Check connection periodically in background."""
        now = time.time()
        if now - self.last_attempt_time < self.retry_interval:
            return self.is_connected
        self.last_attempt_time = now
        def worker():
            try:
                resp = requests.get(f"{self.base_url}/api/status", timeout=0.8)
                self.is_connected = (resp.status_code == 200)
                if self.is_connected and self.mock_mode:
                    print(f"[ESP32] Hardware connected at {self.base_url}!")
                    self.mock_mode = False
            except Exception:
                self.is_connected = False
        threading.Thread(target=worker, daemon=True).start()
        return self.is_connected

    def send_emergency(self, road: str) -> dict:
        """
        Notify ESP32 that an emergency vehicle has been detected in a road zone.
        Updates state immediately and sends non-blocking network signal.
        """
        road = road.upper()
        self.mock_status["mode"] = "EMERGENCY"
        self.mock_status["active_road"] = road
        self.mock_status["roadA"] = "GREEN" if road == "A" else "RED"
        self.mock_status["roadB"] = "GREEN" if road == "B" else "RED"
        self.mock_status["roadC"] = "GREEN" if road == "C" else "RED"

        url = f"{self.base_url}/api/emergency?road={road}"
        self._async_post(url)
        return {"status": "dispatched", "road": road}

    def send_reset(self) -> dict:
        """Reset ESP32 traffic light to normal round-robin cycle."""
        self.mock_status["mode"] = "NORMAL"
        url = f"{self.base_url}/api/reset"
        self._async_post(url)
        return {"status": "dispatched"}

    def get_status(self) -> dict:
        """Fetch current light states."""
        return self.mock_status
