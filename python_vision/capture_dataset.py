"""
Interactive Dataset Collector & Auto-Labeler for Custom Car / Vehicle Model.
Allows you to point your camera at your specific toy car or model,
rotate it at different angles, and automatically capture labeled YOLO training data.
"""

import os
import sys
import time
import random
import cv2
import numpy as np

from config import CAMERA_SOURCE, FRAME_WIDTH, FRAME_HEIGHT

# Output directories for YOLOv8 training
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
TRAIN_IMG_DIR = os.path.join(DATASET_DIR, "images", "train")
VAL_IMG_DIR = os.path.join(DATASET_DIR, "images", "val")
TRAIN_LBL_DIR = os.path.join(DATASET_DIR, "labels", "train")
VAL_LBL_DIR = os.path.join(DATASET_DIR, "labels", "val")

for d in [TRAIN_IMG_DIR, VAL_IMG_DIR, TRAIN_LBL_DIR, VAL_LBL_DIR]:
    os.makedirs(d, exist_ok=True)

class DatasetCollector:
    def __init__(self, camera_source=CAMERA_SOURCE):
        self.camera_source = int(camera_source) if str(camera_source).isdigit() else camera_source
        self.cap = None
        self.count = len(os.listdir(TRAIN_IMG_DIR)) + len(os.listdir(VAL_IMG_DIR))
        
        # Guide box coordinates (center default: 380x250 box)
        self.box_w = 380
        self.box_h = 250
        self.cx = FRAME_WIDTH // 2
        self.cy = FRAME_HEIGHT // 2
        
        self.dragging = False
        self.continuous_mode = False
        self.last_snap_time = 0
        self.snap_interval = 0.35 # seconds between shots in continuous mode

    def open_camera(self):
        src = self.camera_source
        if isinstance(src, int) and sys.platform.startswith("win"):
            self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(src)
        else:
            self.cap = cv2.VideoCapture(src)

        if not self.cap.isOpened():
            print(f"[ERROR] Could not open camera {src}.")
            return False
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        print(f"[CAMERA] Opened camera {src} for dataset collection.")
        return True

    def mouse_callback(self, event, x, y, flags, param):
        """Allow clicking and dragging to position the guide box over the car."""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.dragging = True
            self.cx = x
            self.cy = y
        elif event == cv2.EVENT_MOUSEMOVE and self.dragging:
            self.cx = x
            self.cy = y
        elif event == cv2.EVENT_LBUTTONUP:
            self.dragging = False

    def save_sample(self, raw_frame):
        """Save clean frame and normalized YOLO annotation file."""
        h, w = raw_frame.shape[:2]
        
        # Calculate bounding box bounds
        x1 = max(0, self.cx - self.box_w // 2)
        y1 = max(0, self.cy - self.box_h // 2)
        x2 = min(w, self.cx + self.box_w // 2)
        y2 = min(h, self.cy + self.box_h // 2)

        # Normalized coordinates for YOLO (class 0: car/ambulance)
        norm_cx = ((x1 + x2) / 2.0) / w
        norm_cy = ((y1 + y2) / 2.0) / h
        norm_w = (x2 - x1) / w
        norm_h = (y2 - y1) / h

        # 80% train, 20% validation split
        is_val = random.random() < 0.20
        target_img_dir = VAL_IMG_DIR if is_val else TRAIN_IMG_DIR
        target_lbl_dir = VAL_LBL_DIR if is_val else TRAIN_LBL_DIR

        self.count += 1
        base_name = f"car_{int(time.time()*1000)}_{self.count:04d}"
        img_path = os.path.join(target_img_dir, f"{base_name}.jpg")
        lbl_path = os.path.join(target_lbl_dir, f"{base_name}.txt")

        # Save clean original image
        cv2.imwrite(img_path, raw_frame)

        # Write YOLO label: <class_id> <cx> <cy> <w> <h>
        with open(lbl_path, "w") as f:
            f.write(f"0 {norm_cx:.6f} {norm_cy:.6f} {norm_w:.6f} {norm_h:.6f}\n")

        print(f"[SAVED] Sample #{self.count:03d} -> {'VAL' if is_val else 'TRAIN'}")

    def run(self):
        if not self.open_camera():
            return

        window_name = "Custom Car Dataset Collector - Align Car in Green Box"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 960, 540)
        cv2.setMouseCallback(window_name, self.mouse_callback)

        print("\n==============================================================")
        print("   Custom Car Dataset Collector & Auto-Labeler")
        print("==============================================================")
        print("  1. Place your car inside the GREEN bounding box.")
        print("  2. Click anywhere on screen to reposition the box.")
        print("  3. Press [SPACE] to snap a sample.")
        print("  4. Press [C] to toggle CONTINUOUS SNAP (slowly rotate your car).")
        print("  5. Use [+] / [-] keys to resize the box.")
        print("  6. Press [Q] when finished (Aim for 40-60 samples).")
        print("==============================================================\n")

        while True:
            ret, self_frame = self.cap.read()
            if not ret:
                break

            h, w = self_frame.shape[:2]
            raw_frame = self_frame.copy()
            frame = self_frame.copy()
            current_time = time.time()

            # Continuous snapshot trigger
            if self.continuous_mode and (current_time - self.last_snap_time >= self.snap_interval):
                self.save_sample(raw_frame)
                self.last_snap_time = current_time

            # Compute box corners
            x1 = max(0, self.cx - self.box_w // 2)
            y1 = max(0, self.cy - self.box_h // 2)
            x2 = min(w, self.cx + self.box_w // 2)
            y2 = min(h, self.cy + self.box_h // 2)

            # Draw Guide Bounding Box (Flashing Red when recording)
            box_color = (0, 0, 255) if (self.continuous_mode and int(current_time * 5) % 2 == 0) else (0, 255, 120)
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            
            # Crosshair center mark
            cv2.circle(frame, (self.cx, self.cy), 5, (0, 255, 255), -1)
            cv2.line(frame, (self.cx - 15, self.cy), (self.cx + 15, self.cy), (0, 255, 255), 1)
            cv2.line(frame, (self.cx, self.cy - 15), (self.cx, self.cy + 15), (0, 255, 255), 1)

            # Top Telemetry Header
            cv2.rectangle(frame, (0, 0), (w, 65), (20, 24, 30), -1)
            cv2.line(frame, (0, 65), (w, 65), (50, 60, 75), 2)
            cv2.putText(frame, "CUSTOM CAR DATASET COLLECTOR", (20, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

            mode_str = "CONTINUOUS RECORDING (Rotate your car)" if self.continuous_mode else "MANUAL SNAP (Press SPACE)"
            mode_color = (0, 80, 255) if self.continuous_mode else (0, 255, 120)
            cv2.putText(frame, mode_str, (20, 52),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, mode_color, 2, cv2.LINE_AA)

            # Samples count badge & recommendation
            count_text = f"Samples: {self.count} / 50"
            rec_text = "Ready to train!" if self.count >= 30 else f"Need {30 - self.count} more"
            cv2.putText(frame, count_text, (w - 300, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, rec_text, (w - 300, 52),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 120) if self.count >= 30 else (180, 180, 180), 1, cv2.LINE_AA)

            # Bottom instructions bar
            cv2.rectangle(frame, (0, h - 35), (w, h), (15, 18, 22), -1)
            help_str = "[SPACE] Snap 1 Photo | [C] Continuous Auto-Snap | [+][-] Resize Box | [Q] Done & Exit"
            cv2.putText(frame, help_str, (20, h - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 190, 200), 1, cv2.LINE_AA)

            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            elif key == ord(' '):
                self.save_sample(raw_frame)
            elif key == ord('c') or key == ord('C'):
                self.continuous_mode = not self.continuous_mode
                print(f"[MODE] Continuous capture: {'ON' if self.continuous_mode else 'OFF'}")
            elif key == ord('+') or key == ord('='):
                self.box_w = min(w - 20, self.box_w + 20)
                self.box_h = min(h - 20, self.box_h + 15)
            elif key == ord('-') or key == ord('_'):
                self.box_w = max(80, self.box_w - 20)
                self.box_h = max(60, self.box_h - 15)

        self.cap.release()
        cv2.destroyAllWindows()

        print("\n==============================================================")
        print(f"  Dataset Collection Finished! Total samples: {self.count}")
        print("  Images saved to: python_vision/dataset/images/")
        print("  Labels saved to: python_vision/dataset/labels/")
        print("  Next Step: Run 'python train_custom.py' to train your model!")
        print("==============================================================\n")

if __name__ == "__main__":
    collector = DatasetCollector()
    collector.run()
