"""
Main Computer Vision & YOLO Traffic Management Pipeline.
Processes camera feed, traces 3-way road intersection zones, detects incoming
emergency vehicles, triggers realistic 2-second yellow transitions, and notifies
ESP32 (over Wi-Fi) and Arduino Uno (over Serial).
"""

import os
import sys
import time
import argparse
import cv2
import numpy as np

from config import (
    CAMERA_SOURCE, FRAME_WIDTH, FRAME_HEIGHT,
    YOLO_MODEL_PATH, CONFIDENCE_THRESHOLD, VEHICLE_CLASS_IDS,
    ESP32_IP
)
from zone_detector import ZoneDetector
from esp32_client import ESP32Client
from uno_serial import ArduinoSerial
from api_bridge import shared_state, start_api_server_background

# Attempt to load Ultralytics YOLO; provide lightweight fallback if not yet installed
try:
    from ultralytics import YOLO
    HAS_ULTRALYTICS = True
except ImportError:
    HAS_ULTRALYTICS = False
    print("[WARN] ultralytics not installed. Running in high-performance simulated detector mode.")

class SmartTrafficVisionSystem:
    def __init__(self, camera_source=CAMERA_SOURCE, esp32_ip=ESP32_IP):
        self.camera_source = camera_source
        self.zone_detector = ZoneDetector()
        self.esp32_client = ESP32Client(f"http://{esp32_ip}:80")
        self.uno_serial = ArduinoSerial()
        
        # State tracking
        self.active_emergency_road = None
        self.last_detection_time = 0
        self.emergency_hold_time = 4.0 # Hold green for 4s after vehicle leaves zone
        
        # 2-second Yellow transition state tracker
        self.in_yellow_transition = False
        self.yellow_transition_start = 0
        self.yellow_transition_duration = 2.0 # Exact 2-second yellow delay requirement
        self.pending_emergency_road = None
        self.normal_cycle_road = "A"
        self.normal_cycle_last_switch = time.time()
        self.normal_cycle_interval = 8.0 # 8s green per road in normal round robin

        # Simulated ambulance position for interactive testing
        self.simulated_ambulance_road = None
        self.simulated_pos = None

        # YOLO Model & Sensitivity Settings
        self.model_name = self.resolve_model_path(YOLO_MODEL_PATH)
        self.confidence_threshold = CONFIDENCE_THRESHOLD
        self.model = None
        if HAS_ULTRALYTICS:
            try:
                print(f"[YOLO] Loading model '{self.model_name}'...")
                self.model = YOLO(self.model_name)
                print(f"[YOLO] Model loaded successfully: {os.path.basename(self.model_name)} (Classes: {list(self.model.names.values())})")
            except Exception as e:
                print(f"[YOLO] Error loading model ({e}). Using mock detector fallback.")
                self.model = None

    def resolve_model_path(self, model_name: str) -> str:
        """Resolve model path whether run from root or python_vision directory."""
        if os.path.isabs(model_name) and os.path.exists(model_name):
            return model_name
        # Check inside python_vision directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt_path = os.path.join(script_dir, model_name)
        if os.path.exists(alt_path):
            return alt_path
        # Check current working directory
        if os.path.exists(model_name):
            return os.path.abspath(model_name)
        return model_name

    def initialize_video(self):
        """Open camera stream or video file; fallback to synthetic canvas if none available."""
        src = self.camera_source
        if isinstance(src, str) and src.isdigit():
            src = int(src)
        
        # On Windows, try DirectShow (cv2.CAP_DSHOW) first for fast, reliable hardware webcam initialization
        if isinstance(src, int) and sys.platform.startswith('win'):
            cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(src)
        else:
            cap = cv2.VideoCapture(src)

        if not cap.isOpened():
            print(f"[CAMERA] Notice: Camera {src} could not be opened. Using Synthetic 3-Way Intersection Feed.")
            return None
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[CAMERA] Successfully opened Camera {src} ({actual_w}x{actual_h})")
        return cap

    def generate_synthetic_intersection_frame(self, width=1280, height=720) -> np.ndarray:
        """
        Creates a clean, realistic top-down 3-way intersection video feed
        when a physical camera is not connected.
        """
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Background: Dark Asphalt Ground
        frame[:] = (32, 38, 42)

        # Draw 3 Roads (Asphalt Gray)
        road_color = (60, 65, 70)
        line_color = (220, 220, 220)

        # Road A (North approach, vertical)
        cv2.rectangle(frame, (int(width * 0.38), 0), (int(width * 0.62), int(height * 0.5)), road_color, -1)
        # Road B (East approach, horizontal right)
        cv2.rectangle(frame, (int(width * 0.5), int(height * 0.42)), (width, int(height * 0.72)), road_color, -1)
        # Road C (West approach, horizontal left)
        cv2.rectangle(frame, (0, int(height * 0.42)), (int(width * 0.5), int(height * 0.72)), road_color, -1)

        # Intersection Center Box
        cv2.rectangle(frame, (int(width * 0.38), int(height * 0.42)), (int(width * 0.62), int(height * 0.72)), (50, 55, 60), -1)

        # Dashed Center Lane Markings
        # Road A
        for y in range(20, int(height * 0.42), 40):
            cv2.line(frame, (int(width * 0.5), y), (int(width * 0.5), y + 20), (0, 215, 255), 2)
        # Road B
        for x in range(int(width * 0.62), width - 20, 40):
            cv2.line(frame, (x, int(height * 0.57)), (x + 20, int(height * 0.57)), (0, 215, 255), 2)
        # Road C
        for x in range(20, int(width * 0.38), 40):
            cv2.line(frame, (x, int(height * 0.57)), (x + 20, int(height * 0.57)), (0, 215, 255), 2)

        # Road Stop Lines (White)
        cv2.line(frame, (int(width * 0.38), int(height * 0.42)), (int(width * 0.62), int(height * 0.42)), line_color, 4) # Road A
        cv2.line(frame, (int(width * 0.62), int(height * 0.42)), (int(width * 0.62), int(height * 0.72)), line_color, 4) # Road B
        cv2.line(frame, (int(width * 0.38), int(height * 0.42)), (int(width * 0.38), int(height * 0.72)), line_color, 4) # Road C

        return frame

    def get_ui_buttons(self):
        """Define on-screen clickable buttons for threshold and model adjustments."""
        y1, y2 = 72, 106
        buttons = [
            {
                "id": "dec_thresh",
                "rect": (20, y1, 115, y2),
                "label": "[-] THRESH",
                "bg_color": (50, 60, 75),
                "text_color": (255, 255, 255)
            },
            {
                "id": "thresh_badge",
                "rect": (120, y1, 235, y2),
                "label": f"CONF: {self.confidence_threshold:.2f}",
                "bg_color": (30, 95, 45) if self.confidence_threshold <= 0.20 else (25, 30, 40),
                "text_color": (0, 255, 180)
            },
            {
                "id": "inc_thresh",
                "rect": (240, y1, 335, y2),
                "label": "[+] THRESH",
                "bg_color": (50, 60, 75),
                "text_color": (255, 255, 255)
            },
            {
                "id": "preset_high",
                "rect": (345, y1, 445, y2),
                "label": "HIGH (0.15)",
                "bg_color": (0, 140, 100) if abs(self.confidence_threshold - 0.15) < 0.02 else (35, 40, 50),
                "text_color": (255, 255, 255)
            },
            {
                "id": "preset_med",
                "rect": (450, y1, 545, y2),
                "label": "MED (0.22)",
                "bg_color": (0, 120, 160) if abs(self.confidence_threshold - 0.22) < 0.02 else (35, 40, 50),
                "text_color": (255, 255, 255)
            },
            {
                "id": "preset_strict",
                "rect": (550, y1, 650, y2),
                "label": "STRICT (0.35)",
                "bg_color": (160, 90, 20) if abs(self.confidence_threshold - 0.35) < 0.02 else (35, 40, 50),
                "text_color": (255, 255, 255)
            },
            {
                "id": "toggle_model",
                "rect": (660, y1, 785, y2),
                "label": f"MODEL: {os.path.basename(self.model_name).replace('.pt','').upper()}",
                "bg_color": (90, 40, 130),
                "text_color": (255, 255, 255)
            }
        ]
        return buttons

    def draw_ui_buttons(self, frame: np.ndarray):
        """Render on-screen interactive buttons and prompts for threshold and model controls."""
        buttons = self.get_ui_buttons()

        # Render background pill strip behind buttons
        cv2.rectangle(frame, (12, 68), (800, 110), (18, 22, 28), -1)
        cv2.rectangle(frame, (12, 68), (800, 110), (55, 65, 80), 1)

        for btn in buttons:
            x1, y1, x2, y2 = btn["rect"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), btn["bg_color"], -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (90, 105, 125), 1)
            (tw, th), _ = cv2.getTextSize(btn["label"], cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
            tx = x1 + (x2 - x1 - tw) // 2
            ty = y1 + (y2 - y1 + th) // 2
            cv2.putText(frame, btn["label"], (tx, ty),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, btn["text_color"], 1, cv2.LINE_AA)

        # On-screen visual prompt
        prompt_text = "<- CLICK BUTTONS TO ADJUST SENSITIVITY"
        cv2.putText(frame, prompt_text, (815, 94),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)

    def handle_mouse_click(self, event, x, y, flags, param):
        """Handle mouse clicks on on-screen button prompts."""
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        buttons = self.get_ui_buttons()

        for btn in buttons:
            x1, y1, x2, y2 = btn["rect"]
            if x1 <= x <= x2 and y1 <= y <= y2:
                btn_id = btn["id"]
                if btn_id == "dec_thresh":
                    self.confidence_threshold = max(0.05, round(self.confidence_threshold - 0.03, 2))
                    print(f"[UI] Decreased threshold to {self.confidence_threshold:.2f} (More Sensitive)")
                elif btn_id == "inc_thresh":
                    self.confidence_threshold = min(0.90, round(self.confidence_threshold + 0.03, 2))
                    print(f"[UI] Increased threshold to {self.confidence_threshold:.2f} (Stricter)")
                elif btn_id == "preset_high":
                    self.confidence_threshold = 0.15
                    print(f"[UI] Set threshold to HIGH Sensitivity (0.15)")
                elif btn_id == "preset_med":
                    self.confidence_threshold = 0.22
                    print(f"[UI] Set threshold to MED Sensitivity (0.22)")
                elif btn_id == "preset_strict":
                    self.confidence_threshold = 0.35
                    print(f"[UI] Set threshold to STRICT (0.35)")
                elif btn_id == "toggle_model":
                    self.toggle_model()
                break

    def toggle_model(self):
        """Cycle through available models: Custom Car Model -> YOLOv8s -> YOLOv8n."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        custom_candidate = os.path.join(script_dir, "custom_car_model.pt")
        models_cycle = []
        if os.path.exists(custom_candidate):
            models_cycle.append(custom_candidate)
        models_cycle.extend(["yolov8s.pt", "yolov8n.pt"])

        current_base = os.path.basename(self.model_name)
        base_list = [os.path.basename(m) for m in models_cycle]
        try:
            curr_idx = base_list.index(current_base)
            next_model = models_cycle[(curr_idx + 1) % len(models_cycle)]
        except ValueError:
            next_model = models_cycle[0]

        resolved = self.resolve_model_path(next_model)
        display_name = os.path.basename(resolved)
        print(f"\n[YOLO] Switching model from {current_base} -> {display_name}...")
        try:
            self.model = YOLO(resolved)
            self.model_name = resolved
            print(f"[YOLO] Successfully loaded {display_name}! (Classes: {list(self.model.names.values())})")
        except Exception as e:
            print(f"[YOLO] Could not switch to {display_name}: {e}")

    def run(self):
        """Main detection and traffic control loop."""
        # Start background FastAPI bridge for React Web Dashboard
        start_api_server_background()

        cap = self.initialize_video()
        window_name = "Smart Traffic AI - Emergency Vehicle Preemption"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 960, 540)
        cv2.setMouseCallback(window_name, self.handle_mouse_click)

        prev_time = time.time()
        print("\n==============================================================")
        print("  Smart Traffic AI - Computer Vision Pipeline Running")
        print("  Controls:")
        print("    [A] / [B] / [C] : Simulate Emergency Ambulance on Road A, B, or C")
        print("    [R]             : Reset to Normal Traffic Cycle")
        print("    [G]             : Toggle Hospital Entrance Gate (Open/Close)")
        print("    [Q]             : Quit Application")
        print("==============================================================\n")

        while True:
            current_time = time.time()
            fps = 1.0 / max(current_time - prev_time, 0.001)
            prev_time = current_time

            # Check manual overrides from Web Dashboard
            if "manual_override" in shared_state:
                req_road = shared_state.pop("manual_override")
                self.trigger_emergency_for_road(req_road)
            if "manual_reset" in shared_state:
                shared_state.pop("manual_reset")
                self.reset_to_normal()

            # Acquire Frame
            if cap:
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
            else:
                frame = self.generate_synthetic_intersection_frame()

            h, w = frame.shape[:2]

            # Detect Vehicles & Emergency Preemption
            detected_road = None
            detected_box = None
            detected_confidence = 0.0
            all_detected_vehicles = []
            top_other_detection = None

            # 1. Run YOLO if available
            if self.model:
                results = self.model(frame, verbose=False, conf=self.confidence_threshold)
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        cls_name = self.model.names.get(cls_id, f"Class {cls_id}").capitalize()

                        # Match vehicle: custom single-class model (class 0) or standard COCO vehicle classes
                        is_target_vehicle = (cls_id == 0) if (len(self.model.names) == 1) else (cls_id in VEHICLE_CLASS_IDS)
                        if is_target_vehicle:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            cx = int((x1 + x2) / 2)
                            cy = int((y1 + y2) / 2)

                            road = self.zone_detector.find_road_for_point((cx, cy), w, h)

                            veh_info = {
                                "box": (x1, y1, x2, y2),
                                "centroid": (cx, cy),
                                "cls_id": cls_id,
                                "cls_name": cls_name,
                                "conf": conf,
                                "road": road
                            }
                            all_detected_vehicles.append(veh_info)

                            # First vehicle inside an intersection road zone triggers road logic
                            if road and not detected_road:
                                detected_road = road
                                detected_box = (x1, y1, x2, y2, cx, cy)
                                detected_confidence = conf
                        else:
                            # Keep track of nearest other object to give visual feedback
                            if top_other_detection is None or conf > top_other_detection["conf"]:
                                top_other_detection = {"name": cls_name, "conf": conf}

            # 2. Simulated ambulance injection (keys 'A', 'B', 'C')
            if self.simulated_ambulance_road:
                detected_road = self.simulated_ambulance_road
                detected_confidence = 0.96
                # Place virtual ambulance inside the chosen road polygon
                sim_coords = {
                    "A": (int(w * 0.48), int(h * 0.25)),
                    "B": (int(w * 0.78), int(h * 0.58)),
                    "C": (int(w * 0.18), int(h * 0.58))
                }
                cx, cy = sim_coords.get(detected_road, (int(w * 0.5), int(h * 0.5)))
                bw, bh = 80, 50
                detected_box = (cx - bw//2, cy - bh//2, cx + bw//2, cy + bh//2, cx, cy)
                all_detected_vehicles.append({
                    "box": (cx - bw//2, cy - bh//2, cx + bw//2, cy + bh//2),
                    "centroid": (cx, cy),
                    "cls_id": 99,
                    "cls_name": "Ambulance (Sim)",
                    "conf": 0.96,
                    "road": detected_road
                })

            # Handle Emergency Traffic Signal Logic & 2-Second Yellow Transition
            self.handle_traffic_logic(detected_road, current_time)

            # Draw Traced Road Lines & Zones
            frame = self.zone_detector.draw_zones(
                frame,
                active_emergency_road=self.active_emergency_road,
                highlighted_road=self.pending_emergency_road
            )

            # Draw ALL Detected Vehicles (real-time vehicle testing on Camera)
            for veh in all_detected_vehicles:
                vx1, vy1, vx2, vy2 = veh["box"]
                vcx, vcy = veh["centroid"]
                v_road = veh["road"]
                v_name = veh["cls_name"]
                v_conf = veh["conf"]

                if v_road:
                    # Vehicle is in an intersection zone!
                    box_color = (0, 0, 255) if int(current_time * 4) % 2 == 0 else (0, 215, 255)
                    label_bg = (0, 0, 180)
                    label_text = f"{v_name} [Road {v_road}] {int(v_conf * 100)}%"
                else:
                    # Vehicle detected in camera field of view
                    box_color = (0, 255, 120)  # Bright neon green
                    label_bg = (20, 120, 50)
                    label_text = f"{v_name} {int(v_conf * 100)}%"

                # Bounding Box
                cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), box_color, 2)
                # Centroid Dot
                cv2.circle(frame, (vcx, vcy), 4, (0, 255, 255), -1)

                # Label Badge with background
                (lw, lh), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                badge_y1 = max(0, vy1 - lh - 8)
                cv2.rectangle(frame, (vx1, badge_y1), (vx1 + lw + 10, vy1), label_bg, -1)
                cv2.putText(frame, label_text, (vx1 + 5, vy1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

            # Draw HUD & Telemetry Overlays
            self.draw_hud(frame, fps, current_time, len(all_detected_vehicles), top_other_detection)

            # Draw On-Screen Clickable Buttons & Prompt
            self.draw_ui_buttons(frame)

            # Update shared state for React Web Dashboard
            self.sync_shared_state(fps, detected_road, detected_confidence, len(all_detected_vehicles))

            # Display Window
            cv2.imshow("Smart Traffic AI - Emergency Vehicle Preemption", frame)

            # Key handling
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            elif key == ord('['):
                # Decrease confidence threshold (more sensitive)
                self.confidence_threshold = max(0.05, round(self.confidence_threshold - 0.03, 2))
                print(f"[SENSITIVITY] Lowered threshold to {self.confidence_threshold:.2f} (More Sensitive)")
            elif key == ord(']'):
                # Increase confidence threshold (stricter)
                self.confidence_threshold = min(0.90, round(self.confidence_threshold + 0.03, 2))
                print(f"[SENSITIVITY] Raised threshold to {self.confidence_threshold:.2f} (Stricter)")
            elif key == ord('m') or key == ord('M'):
                self.toggle_model()
            elif key == ord('a') or key == ord('A'):
                self.trigger_simulation("A")
            elif key == ord('b') or key == ord('B'):
                self.trigger_simulation("B")
            elif key == ord('c') or key == ord('C'):
                self.trigger_simulation("C")
            elif key == ord('r') or key == ord('R'):
                self.reset_to_normal()
            elif key == ord('g') or key == ord('G'):
                # Toggle hospital gate
                shared_state["hospital_gate_open"] = not shared_state["hospital_gate_open"]
                if shared_state["hospital_gate_open"]:
                    self.uno_serial.send_gate_open()
                print(f"[GATE] Hospital Gate Toggled: {'OPEN' if shared_state['hospital_gate_open'] else 'CLOSED'}")

        # Cleanup
        if cap:
            cap.release()
        cv2.destroyAllWindows()
        self.uno_serial.close()

    def trigger_simulation(self, road: str):
        """Simulate an ambulance entering a specific road zone."""
        print(f"\n[SIM] Ambulance entered {road}! Initiating preemption protocol...")
        self.simulated_ambulance_road = road
        self.last_detection_time = time.time()
        self.trigger_emergency_for_road(road)

    def trigger_emergency_for_road(self, road: str):
        """Start the transition to make the target road GREEN with a 2-second Yellow delay."""
        current_green = self.active_emergency_road if self.active_emergency_road else self.normal_cycle_road
        
        if current_green == road and not self.in_yellow_transition:
            # Already green on this road! Just lock it in emergency mode
            self.active_emergency_road = road
            self.esp32_client.send_emergency(road)
            self.uno_serial.send_emergency(road)
            return

        # Start 2-second Yellow Light Delay on the currently green road
        print(f"[TRANSITION] Switching current Road {current_green} to YELLOW (2s delay before Road {road} turns GREEN)")
        self.in_yellow_transition = True
        self.yellow_transition_start = time.time()
        self.pending_emergency_road = road
        
        # Notify ESP32 to start 2-second yellow light
        self.esp32_client.send_emergency(road)
        self.uno_serial.send_emergency(road)

    def reset_to_normal(self):
        """Restore normal round-robin cycle."""
        print("[TRAFFIC] Resumed Normal Traffic Cycle.")
        self.simulated_ambulance_road = None
        self.active_emergency_road = None
        self.pending_emergency_road = None
        self.in_yellow_transition = False
        self.normal_cycle_last_switch = time.time()
        self.esp32_client.send_reset()
        self.uno_serial.send_normal()

    def handle_traffic_logic(self, detected_road: str, current_time: float):
        """Handles non-blocking state transitions: normal cycle, yellow delay, and emergency lock."""
        # 1. Active detection from camera
        if detected_road:
            self.last_detection_time = current_time
            if not self.active_emergency_road and not self.in_yellow_transition:
                self.trigger_emergency_for_road(detected_road)

        # 2. Check 2-Second Yellow Light Transition
        if self.in_yellow_transition:
            elapsed = current_time - self.yellow_transition_start
            if elapsed >= self.yellow_transition_duration:
                # 2 seconds have passed! Now turn target road GREEN!
                self.in_yellow_transition = False
                self.active_emergency_road = self.pending_emergency_road
                self.pending_emergency_road = None
                print(f"[TRAFFIC] *** PRIORITY OVERRIDE *** Road {self.active_emergency_road} is now GREEN!")
            return

        # 3. If in Emergency Mode, check if ambulance has cleared
        if self.active_emergency_road:
            if current_time - self.last_detection_time > self.emergency_hold_time:
                print(f"[TRAFFIC] Ambulance has cleared Road {self.active_emergency_road}. Transitioning back to normal cycle.")
                self.reset_to_normal()
            return

        # 4. Normal Round-Robin Traffic Cycle (A -> B -> C -> A) with 2-second yellow transitions
        normal_elapsed = current_time - self.normal_cycle_last_switch
        if normal_elapsed > self.normal_cycle_interval:
            # Advance to next road
            next_map = {"A": "B", "B": "C", "C": "A"}
            self.normal_cycle_road = next_map.get(self.normal_cycle_road, "A")
            self.normal_cycle_last_switch = current_time

    def get_current_lights(self) -> dict:
        """Calculate current Red/Yellow/Green state for all 3 roads."""
        lights = {"A": "RED", "B": "RED", "C": "RED"}
        
        if self.in_yellow_transition:
            # The previously green road is now Yellow
            curr_road = self.active_emergency_road if self.active_emergency_road else self.normal_cycle_road
            lights[curr_road] = "YELLOW"
        elif self.active_emergency_road:
            lights[self.active_emergency_road] = "GREEN"
        else:
            lights[self.normal_cycle_road] = "GREEN"
        return lights

    def draw_hud(self, frame: np.ndarray, fps: float, current_time: float, vehicle_count: int = 0, top_other: dict = None):
        """Draw an informative HUD displaying system telemetry."""
        h, w = frame.shape[:2]
        lights = self.get_current_lights()

        # Top Control Banner (Dark Glassmorphic strip)
        cv2.rectangle(frame, (0, 0), (w, 65), (20, 24, 30), -1)
        cv2.line(frame, (0, 65), (w, 65), (50, 60, 75), 2)

        # Title
        cv2.putText(frame, "SMART TRAFFIC AI - EMERGENCY PREEMPTION", (20, 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Subtitle / Mode or Detection Feedback
        if self.in_yellow_transition:
            remaining = max(0.0, self.yellow_transition_duration - (current_time - self.yellow_transition_start))
            mode_text = f"PHASE CHANGE: 2.0s YELLOW DELAY ({remaining:.1f}s) -> ROAD {self.pending_emergency_road}"
            mode_color = (0, 220, 255) # Yellow
        elif self.active_emergency_road:
            mode_text = f"EMERGENCY ACTIVE: PRIORITY GREEN FOR ROAD {self.active_emergency_road}"
            mode_color = (0, 50, 255) # Red/Orange
        elif vehicle_count > 0:
            mode_text = f"TRACKING: {vehicle_count} VEHICLE(S) IN VIEW"
            mode_color = (0, 255, 120) # Bright Green
        elif top_other:
            mode_text = f"SCANNING: Nearest object '{top_other['name']}' ({int(top_other['conf']*100)}%)"
            mode_color = (180, 200, 220) # Light slate
        else:
            mode_text = f"NORMAL CYCLE: ROAD {self.normal_cycle_road} GREEN"
            mode_color = (0, 255, 120) # Green

        cv2.putText(frame, mode_text, (20, 52),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, mode_color, 2, cv2.LINE_AA)

        # Right side: 3 Traffic Signal Badges
        start_x = w - 340
        for road in ["A", "B", "C"]:
            color_state = lights[road]
            badge_color = (0, 0, 220) if color_state == "RED" else (0, 215, 255) if color_state == "YELLOW" else (0, 220, 0)
            
            # Circle light indicator
            cv2.circle(frame, (start_x, 32), 14, (40, 45, 50), -1)
            cv2.circle(frame, (start_x, 32), 11, badge_color, -1)
            cv2.putText(frame, road, (start_x - 5, 37),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2, cv2.LINE_AA)

            start_x += 70

        # Model, Sensitivity, Camera, Vehicles & FPS badge
        short_model = os.path.basename(self.model_name).replace(".pt", "").upper()
        telemetry = f"{short_model} | Conf: {self.confidence_threshold:.2f} | Cam: {self.camera_source} | Veh: {vehicle_count} | FPS: {int(fps)}"
        cv2.putText(frame, telemetry, (w - 440, 52),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 220), 1, cv2.LINE_AA)

        # Bottom Instructions Strip
        cv2.rectangle(frame, (0, h - 30), (w, h), (15, 18, 22), -1)
        help_text = "[Keys] [ / ]: Sensitivity | M: Switch Model (s/n) | A/B/C: Sim Amb | R: Reset | Q: Quit"
        cv2.putText(frame, help_text, (20, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (170, 175, 185), 1, cv2.LINE_AA)

    def sync_shared_state(self, fps: float, detected_road: str, detected_confidence: float, vehicle_count: int = 0):
        """Update global dictionary for the FastAPI Web Bridge."""
        lights = self.get_current_lights()
        shared_state["system_mode"] = "TRANSITION_YELLOW" if self.in_yellow_transition else \
                                      "EMERGENCY" if self.active_emergency_road else "NORMAL"
        shared_state["active_road"] = self.active_emergency_road or self.normal_cycle_road
        shared_state["transition_target"] = self.pending_emergency_road
        shared_state["transition_remaining_sec"] = max(0.0, self.yellow_transition_duration - (time.time() - self.yellow_transition_start)) if self.in_yellow_transition else 0.0
        shared_state["lights"] = lights
        shared_state["emergency_vehicle_detected"] = bool(detected_road)
        shared_state["detected_road"] = detected_road
        shared_state["vehicle_confidence"] = detected_confidence
        shared_state["vehicle_count"] = vehicle_count
        shared_state["esp32_connected"] = self.esp32_client.is_connected
        shared_state["fps"] = round(fps, 1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Traffic Vision AI")
    parser.add_argument("--camera", default=CAMERA_SOURCE, help="Camera index or video file")
    parser.add_argument("--esp32", default=ESP32_IP, help="ESP32 IP address")
    parser.add_argument("--model", default=YOLO_MODEL_PATH, help="YOLO model path (yolov8s.pt, yolov8n.pt)")
    parser.add_argument("--conf", type=float, default=CONFIDENCE_THRESHOLD, help="Confidence threshold (e.g. 0.22)")
    args = parser.parse_args()

    system = SmartTrafficVisionSystem(camera_source=args.camera, esp32_ip=args.esp32)
    if args.model:
        system.model_name = args.model
    if args.conf:
        system.confidence_threshold = args.conf
    system.run()
