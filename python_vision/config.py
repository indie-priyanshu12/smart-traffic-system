"""
Configuration settings for Python YOLO Smart Traffic Vision System.
Includes ESP32 network settings, camera options, and default 3-road zone polygons.
"""

import os

# -----------------------------------------------------------------------------
# ESP32 & Arduino Network / Hardware Settings
# -----------------------------------------------------------------------------
# Replace with the actual IP address assigned to your ESP32 on your Wi-Fi network
ESP32_IP = os.getenv("ESP32_IP", "192.168.1.100")
ESP32_PORT = int(os.getenv("ESP32_PORT", 80))
ESP32_BASE_URL = f"http://{ESP32_IP}:{ESP32_PORT}"

# Arduino Uno Serial port (Optional direct USB link)
ARDUINO_COM_PORT = os.getenv("ARDUINO_PORT", "COM3")
ARDUINO_BAUD_RATE = 115200

# -----------------------------------------------------------------------------
# Camera / Video Feed Settings
# -----------------------------------------------------------------------------
# 0 = default webcam, 1 = external USB camera, or path to a sample MP4 video
CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "0")
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# -----------------------------------------------------------------------------
# YOLO Model Configuration
# -----------------------------------------------------------------------------
# Auto-detects custom trained car model if present, otherwise uses yolov8s.pt
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CUSTOM_MODEL_PATH = os.path.join(SCRIPT_DIR, "custom_car_model.pt")
DEFAULT_MODEL = CUSTOM_MODEL_PATH if os.path.exists(CUSTOM_MODEL_PATH) else "yolov8s.pt"
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", DEFAULT_MODEL)
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.22"))

# In standard COCO dataset:
# Class 1 = bicycle, 2 = car, 3 = motorcycle, 5 = bus, 7 = truck
VEHICLE_CLASS_IDS = [1, 2, 3, 5, 7] 

# -----------------------------------------------------------------------------
# Default 3-Way Road Zones (Normalized Coordinates [0.0 - 1.0])
# -----------------------------------------------------------------------------
# Road A = North Approach (Top of screen)
# Road B = East Approach (Right side)
# Road C = West Approach (Left side)
DEFAULT_ZONES = {
    "A": [
        [0.35, 0.05],
        [0.65, 0.05],
        [0.60, 0.45],
        [0.40, 0.45]
    ],
    "B": [
        [0.65, 0.45],
        [0.98, 0.50],
        [0.98, 0.90],
        [0.60, 0.70]
    ],
    "C": [
        [0.02, 0.50],
        [0.35, 0.45],
        [0.40, 0.70],
        [0.02, 0.90]
    ]
}

# -----------------------------------------------------------------------------
# Local Web Bridge API
# -----------------------------------------------------------------------------
API_BRIDGE_HOST = "0.0.0.0"
API_BRIDGE_PORT = 8000
