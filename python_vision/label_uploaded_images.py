"""
Smart Labeling & Dataset Importer for Uploaded Car Images.
Processes photos placed in 'my_car_images/', automatically proposes or lets you draw
bounding boxes on a clean, responsive UI canvas, and generates the YOLO training dataset.
"""

import os
import sys
import glob
import random
import cv2
import numpy as np

# Base paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

UPLOAD_DIRS = [
    os.path.join(ROOT_DIR, "my_car_images"),
    os.path.join(SCRIPT_DIR, "my_car_images")
]

DATASET_DIR = os.path.join(SCRIPT_DIR, "dataset")
TRAIN_IMG_DIR = os.path.join(DATASET_DIR, "images", "train")
VAL_IMG_DIR = os.path.join(DATASET_DIR, "images", "val")
TRAIN_LBL_DIR = os.path.join(DATASET_DIR, "labels", "train")
VAL_LBL_DIR = os.path.join(DATASET_DIR, "labels", "val")

for d in [TRAIN_IMG_DIR, VAL_IMG_DIR, TRAIN_LBL_DIR, VAL_LBL_DIR]:
    os.makedirs(d, exist_ok=True)

# Attempt to load YOLO for auto-proposing bounding boxes
try:
    from ultralytics import YOLO
    model_path = os.path.join(SCRIPT_DIR, "yolov8s.pt")
    AUTO_YOLO = YOLO(model_path if os.path.exists(model_path) else "yolov8s.pt")
except Exception:
    AUTO_YOLO = None

class ImageLabeler:
    def __init__(self, auto_mode=False):
        # Canvas dimensions: fixed, compact, fits any laptop screen comfortably
        self.canvas_w = 840
        self.canvas_h = 540

        # Viewport dimensions where the car image is centered and letterboxed
        self.view_x = 20
        self.view_y = 62
        self.view_w = 800
        self.view_h = 400

        # Current image state
        self.current_box = None  # (rx1, ry1, rx2, ry2) in raw image coordinates
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.disp_w = 0
        self.disp_h = 0
        self.raw_w = 1
        self.raw_h = 1

        # Mouse interaction
        self.drawing = False
        self.start_pt = None  # in raw image coordinates
        self.saved_count = 0
        self.auto_accept_all = auto_mode
        self.action_requested = None

        # Interactive UI buttons at bottom
        y1, y2 = 475, 522
        self.buttons = [
            {
                "id": "accept",
                "rect": (20, y1, 185, y2),
                "label": "[SPACE] Accept Box",
                "bg_color": (30, 140, 50),
                "hover_color": (40, 180, 65),
                "text_color": (255, 255, 255)
            },
            {
                "id": "auto_all",
                "rect": (195, y1, 380, y2),
                "label": "[A] Auto-Accept All",
                "bg_color": (25, 120, 140),
                "hover_color": (35, 155, 180),
                "text_color": (255, 255, 255)
            },
            {
                "id": "skip",
                "rect": (390, y1, 495, y2),
                "label": "[S] Skip Image",
                "bg_color": (45, 52, 65),
                "hover_color": (65, 75, 90),
                "text_color": (220, 220, 220)
            },
            {
                "id": "quit",
                "rect": (505, y1, 665, y2),
                "label": "[Q] Finish & Train",
                "bg_color": (30, 60, 160),
                "hover_color": (40, 80, 200),
                "text_color": (255, 255, 255)
            },
            {
                "id": "info",
                "rect": (675, y1, 820, y2),
                "label": "Drag to Redraw",
                "bg_color": (20, 26, 35),
                "hover_color": (20, 26, 35),
                "text_color": (0, 255, 200)
            }
        ]

    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks for UI buttons and drawing boxes on the centered image."""
        if event == cv2.EVENT_LBUTTONDOWN:
            # 1. Check if a button was clicked
            for btn in self.buttons:
                bx1, by1, bx2, by2 = btn["rect"]
                if bx1 <= x <= bx2 and by1 <= y <= by2:
                    if btn["id"] in ["accept", "auto_all", "skip", "quit"]:
                        self.action_requested = btn["id"]
                        return

            # 2. Check if clicked inside the centered image area
            if (self.offset_x <= x <= self.offset_x + self.disp_w and
                self.offset_y <= y <= self.offset_y + self.disp_h):
                self.drawing = True
                rx = int((x - self.offset_x) / self.scale)
                ry = int((y - self.offset_y) / self.scale)
                rx = max(0, min(self.raw_w, rx))
                ry = max(0, min(self.raw_h, ry))
                self.start_pt = (rx, ry)
                self.current_box = (rx, ry, rx, ry)

        elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
            rx = int((x - self.offset_x) / self.scale)
            ry = int((y - self.offset_y) / self.scale)
            rx = max(0, min(self.raw_w, rx))
            ry = max(0, min(self.raw_h, ry))
            x1 = min(self.start_pt[0], rx)
            y1 = min(self.start_pt[1], ry)
            x2 = max(self.start_pt[0], rx)
            y2 = max(self.start_pt[1], ry)
            self.current_box = (x1, y1, x2, y2)

        elif event == cv2.EVENT_LBUTTONUP and self.drawing:
            self.drawing = False
            rx = int((x - self.offset_x) / self.scale)
            ry = int((y - self.offset_y) / self.scale)
            rx = max(0, min(self.raw_w, rx))
            ry = max(0, min(self.raw_h, ry))
            x1 = min(self.start_pt[0], rx)
            y1 = min(self.start_pt[1], ry)
            x2 = max(self.start_pt[0], rx)
            y2 = max(self.start_pt[1], ry)
            if (x2 - x1) > 10 and (y2 - y1) > 10:
                self.current_box = (x1, y1, x2, y2)

    def propose_box(self, img):
        """Use pre-trained YOLO to guess where the vehicle is, or fallback to center."""
        h, w = img.shape[:2]
        if AUTO_YOLO:
            try:
                results = AUTO_YOLO(img, verbose=False, conf=0.15)
                best_box = None
                best_conf = 0.0
                for r in results:
                    for b in r.boxes:
                        conf = float(b.conf[0])
                        cls_id = int(b.cls[0])
                        # Prioritize vehicle classes: 1:bicycle, 2:car, 3:motorcycle, 5:bus, 7:truck
                        is_veh = cls_id in [1, 2, 3, 5, 7]
                        if is_veh and conf > best_conf:
                            bx1, by1, bx2, by2 = map(int, b.xyxy[0])
                            best_box = (max(0, bx1), max(0, by1), min(w, bx2), min(h, by2))
                            best_conf = conf
                        elif best_box is None and conf > 0.20:
                            bx1, by1, bx2, by2 = map(int, b.xyxy[0])
                            best_box = (max(0, bx1), max(0, by1), min(w, bx2), min(h, by2))
                            best_conf = conf
                if best_box:
                    return best_box
            except Exception:
                pass

        # Fallback: Center box covering ~75% of image
        margin_x = int(w * 0.12)
        margin_y = int(h * 0.12)
        return (margin_x, margin_y, w - margin_x, h - margin_y)

    def save_sample(self, raw_img, box):
        """Save image and YOLO normalized label."""
        h, w = raw_img.shape[:2]
        x1, y1, x2, y2 = box

        norm_cx = ((x1 + x2) / 2.0) / w
        norm_cy = ((y1 + y2) / 2.0) / h
        norm_w = (x2 - x1) / w
        norm_h = (y2 - y1) / h

        # 80% train, 20% validation split
        is_val = random.random() < 0.20
        target_img_dir = VAL_IMG_DIR if is_val else TRAIN_IMG_DIR
        target_lbl_dir = VAL_LBL_DIR if is_val else TRAIN_LBL_DIR

        self.saved_count += 1
        base_name = f"custom_car_{self.saved_count:04d}"
        img_out = os.path.join(target_img_dir, f"{base_name}.jpg")
        lbl_out = os.path.join(target_lbl_dir, f"{base_name}.txt")

        cv2.imwrite(img_out, raw_img)
        with open(lbl_out, "w") as f:
            f.write(f"0 {norm_cx:.6f} {norm_cy:.6f} {norm_w:.6f} {norm_h:.6f}\n")

    def run(self):
        # Gather all uploaded images
        image_files = []
        for upload_dir in UPLOAD_DIRS:
            if os.path.exists(upload_dir):
                for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp"]:
                    image_files.extend(glob.glob(os.path.join(upload_dir, ext)))
                    image_files.extend(glob.glob(os.path.join(upload_dir, ext.upper())))

        image_files = sorted(list(set(image_files)))

        if not image_files:
            print("\n==============================================================")
            print("  [NOTICE] No images found in upload folder!")
            print("  Please paste your car photos into:")
            print(f"    {UPLOAD_DIRS[0]}")
            print("  Then run this script again!")
            print("==============================================================\n")
            return

        print("\n==============================================================")
        print(f"  Found {len(image_files)} uploaded images to label & import!")
        print("  Controls:")
        print("    [SPACE] / Click [Accept Box]     : Accept box and save")
        print("    [A] / Click [Auto-Accept All]    : Auto-accept all remaining images")
        print("    [CLICK & DRAG] on car image      : Redraw bounding box")
        print("    [S] / Click [Skip]               : Skip image")
        print("    [Q] / Click [Finish & Train]     : Finish and train custom model")
        print("==============================================================\n")

        window_name = "Car Image Labeler & Importer"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, self.canvas_w, self.canvas_h)
        cv2.setMouseCallback(window_name, self.mouse_callback)

        for idx, img_path in enumerate(image_files, 1):
            raw_img = cv2.imread(img_path)
            if raw_img is None:
                continue

            self.raw_h, self.raw_w = raw_img.shape[:2]
            self.current_box = self.propose_box(raw_img)

            # Compute letterbox scaling to fit neatly inside the viewport
            scale = min(self.view_w / self.raw_w, self.view_h / self.raw_h)
            disp_w = int(self.raw_w * scale)
            disp_h = int(self.raw_h * scale)

            self.scale = scale
            self.disp_w = disp_w
            self.disp_h = disp_h
            self.offset_x = self.view_x + (self.view_w - disp_w) // 2
            self.offset_y = self.view_y + (self.view_h - disp_h) // 2

            # High quality resize of the original image for the viewport
            disp_img = cv2.resize(raw_img, (disp_w, disp_h), interpolation=cv2.INTER_LINEAR)

            # Fast auto-accept mode
            if self.auto_accept_all:
                self.save_sample(raw_img, self.current_box)
                print(f"[AUTO-SAVED] ({idx}/{len(image_files)}) {os.path.basename(img_path)}")
                continue

            self.action_requested = None

            while True:
                # 1. Create fresh dark canvas
                canvas = np.zeros((self.canvas_h, self.canvas_w, 3), dtype=np.uint8)
                canvas[:] = (20, 24, 30)  # Dark sleek slate

                # 2. Top Header Bar
                cv2.rectangle(canvas, (0, 0), (self.canvas_w, 54), (14, 17, 22), -1)
                cv2.line(canvas, (0, 54), (self.canvas_w, 54), (45, 52, 65), 1)

                cv2.putText(canvas, "CUSTOM CAR DATASET LABELER", (20, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.56, (255, 255, 255), 2, cv2.LINE_AA)

                file_display = os.path.basename(img_path)
                if len(file_display) > 35:
                    file_display = file_display[:32] + "..."
                cv2.putText(canvas, f"Image {idx} of {len(image_files)}: {file_display} ({self.raw_w}x{self.raw_h})",
                            (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (170, 190, 210), 1, cv2.LINE_AA)

                # Counter badge on right
                count_str = f"Imported: {self.saved_count}"
                cv2.rectangle(canvas, (self.canvas_w - 150, 12), (self.canvas_w - 20, 42), (28, 35, 46), -1)
                cv2.rectangle(canvas, (self.canvas_w - 150, 12), (self.canvas_w - 20, 42), (0, 220, 160), 1)
                cv2.putText(canvas, count_str, (self.canvas_w - 138, 32),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 200), 1, cv2.LINE_AA)

                # 3. Viewport Background & Frame
                cv2.rectangle(canvas, (self.view_x - 1, self.view_y - 1),
                              (self.view_x + self.view_w + 1, self.view_y + self.view_h + 1),
                              (40, 48, 60), 1)
                cv2.rectangle(canvas, (self.view_x, self.view_y),
                              (self.view_x + self.view_w, self.view_y + self.view_h),
                              (10, 12, 16), -1)

                # 4. Insert Centered Image (Crisp, true aspect ratio, untouched)
                canvas[self.offset_y : self.offset_y + disp_h, self.offset_x : self.offset_x + disp_w] = disp_img

                # 5. Draw Bounding Box on Canvas
                if self.current_box:
                    bx1 = self.offset_x + int(self.current_box[0] * self.scale)
                    by1 = self.offset_y + int(self.current_box[1] * self.scale)
                    bx2 = self.offset_x + int(self.current_box[2] * self.scale)
                    by2 = self.offset_y + int(self.current_box[3] * self.scale)

                    # Neon green bounding box
                    cv2.rectangle(canvas, (bx1, by1), (bx2, by2), (0, 255, 120), 2)

                    # Corner brackets for premium visual indicator
                    corner_len = min(15, (bx2 - bx1)//4, (by2 - by1)//4)
                    if corner_len > 4:
                        cv2.line(canvas, (bx1, by1), (bx1 + corner_len, by1), (255, 255, 255), 3)
                        cv2.line(canvas, (bx1, by1), (bx1, by1 + corner_len), (255, 255, 255), 3)
                        cv2.line(canvas, (bx2, by1), (bx2 - corner_len, by1), (255, 255, 255), 3)
                        cv2.line(canvas, (bx2, by1), (bx2, by1 + corner_len), (255, 255, 255), 3)
                        cv2.line(canvas, (bx1, by2), (bx1 + corner_len, by2), (255, 255, 255), 3)
                        cv2.line(canvas, (bx1, by2), (bx1, by2 - corner_len), (255, 255, 255), 3)
                        cv2.line(canvas, (bx2, by2), (bx2 - corner_len, by2), (255, 255, 255), 3)
                        cv2.line(canvas, (bx2, by2), (bx2, by2 - corner_len), (255, 255, 255), 3)

                    # Tag label
                    tag_text = "Car / Ambulance [Class 0]"
                    (tw, th), _ = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
                    badge_y = max(self.view_y + 2, by1 - th - 6)
                    cv2.rectangle(canvas, (bx1, badge_y), (bx1 + tw + 10, badge_y + th + 6), (0, 150, 70), -1)
                    cv2.putText(canvas, tag_text, (bx1 + 5, badge_y + th + 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA)

                # 6. Bottom Interactive Buttons
                for btn in self.buttons:
                    x1, y1, x2, y2 = btn["rect"]
                    cv2.rectangle(canvas, (x1, y1), (x2, y2), btn["bg_color"], -1)
                    cv2.rectangle(canvas, (x1, y1), (x2, y2), (70, 85, 105), 1)

                    (tw, th), _ = cv2.getTextSize(btn["label"], cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
                    tx = x1 + (x2 - x1 - tw) // 2
                    ty = y1 + (y2 - y1 + th) // 2
                    cv2.putText(canvas, btn["label"], (tx, ty),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.40, btn["text_color"], 1, cv2.LINE_AA)

                cv2.imshow(window_name, canvas)

                key = cv2.waitKey(20) & 0xFF

                # Process keyboard keys OR mouse button clicks
                if key in [ord(' '), 13] or self.action_requested == "accept":
                    self.save_sample(raw_img, self.current_box)
                    print(f"[SAVED] ({idx}/{len(image_files)}) {os.path.basename(img_path)}")
                    break
                elif key in [ord('a'), ord('A')] or self.action_requested == "auto_all":
                    self.auto_accept_all = True
                    self.save_sample(raw_img, self.current_box)
                    print(f"[AUTO-ACCEPT ON] ({idx}/{len(image_files)}) {os.path.basename(img_path)}")
                    break
                elif key in [ord('s'), ord('S')] or self.action_requested == "skip":
                    print(f"[SKIPPED] {os.path.basename(img_path)}")
                    break
                elif key in [ord('q'), ord('Q'), 27] or self.action_requested == "quit":
                    print("[EXIT] Labeling stopped by user.")
                    cv2.destroyAllWindows()
                    self.finish_and_prompt_train()
                    return

        cv2.destroyAllWindows()
        self.finish_and_prompt_train()

    def finish_and_prompt_train(self):
        print("\n==============================================================")
        print(f"  Import Completed! Total labeled samples in dataset: {self.saved_count}")
        print("  Location: python_vision/dataset/images/ (train/val)")
        print("==============================================================")
        print("  Starting custom model training on NVIDIA GPU now...")
        print("==============================================================\n")

        # Automatically launch training
        import subprocess
        try:
            train_script = os.path.join(SCRIPT_DIR, "train_custom.py")
            subprocess.run([sys.executable, train_script], check=True)
        except Exception as e:
            print(f"[NOTE] Please run: py -3.12 {os.path.join(SCRIPT_DIR, 'train_custom.py')}")

if __name__ == "__main__":
    auto = "--auto" in sys.argv
    labeler = ImageLabeler(auto_mode=auto)
    labeler.run()
