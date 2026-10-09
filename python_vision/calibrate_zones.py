"""
Interactive Road Zone Calibration Utility.
Allows users to click 4 points for each of the 3 roads directly on the camera feed
and save them to 'zones.json'.
"""

import cv2
import json
import numpy as np
from config import CAMERA_SOURCE, FRAME_WIDTH, FRAME_HEIGHT

current_road_idx = 0
roads = ["A", "B", "C"]
road_names = {"A": "Road A (North)", "B": "Road B (East)", "C": "Road C (West)"}
collected_points = {"A": [], "B": [], "C": []}
current_pts = []

def mouse_callback(event, x, y, flags, param):
    global current_pts, current_road_idx
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(current_pts) < 4:
            current_pts.append((x, y))
            print(f"[CALIBRATE] Road {roads[current_road_idx]} - Added Point {len(current_pts)}/4: ({x}, {y})")
            if len(current_pts) == 4:
                # Save normalized points
                w, h = param["size"]
                norm_pts = [[round(px / w, 4), round(py / h, 4)] for px, py in current_pts]
                collected_points[roads[current_road_idx]] = norm_pts
                print(f"[CALIBRATE] Road {roads[current_road_idx]} completed!")

def main():
    global current_road_idx, current_pts

    cap = cv2.VideoCapture(int(CAMERA_SOURCE) if str(CAMERA_SOURCE).isdigit() else CAMERA_SOURCE)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or FRAME_WIDTH
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or FRAME_HEIGHT

    cv2.namedWindow("Calibrate Road Zones")
    cv2.setMouseCallback("Calibrate Road Zones", mouse_callback, {"size": (w, h)})

    print("\n--- ROAD ZONE CALIBRATION ---")
    print("Click 4 corners for each road polygon.")
    print("Press [SPACE] or [ENTER] to advance to next road.")
    print("Press [S] to save and exit.")
    print("Press [R] to clear current road points.")
    print("Press [ESC] to cancel.")

    while True:
        ret, frame = cap.read()
        if not ret:
            # Generate blank canvas if no camera
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:] = (30, 30, 30)

        # Draw already saved roads
        for r_id, pts in collected_points.items():
            if len(pts) == 4:
                pixel_pts = np.array([[int(p[0] * w), int(p[1] * h)] for p in pts], dtype=np.int32)
                cv2.polylines(frame, [pixel_pts], True, (0, 255, 0), 2)
                cv2.putText(frame, f"Road {r_id} (OK)", (pixel_pts[0][0], pixel_pts[0][1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Draw current points being clicked
        for pt in current_pts:
            cv2.circle(frame, pt, 6, (0, 255, 255), -1)
        if len(current_pts) > 1:
            for i in range(len(current_pts) - 1):
                cv2.line(frame, current_pts[i], current_pts[i + 1], (0, 255, 255), 2)

        # Instruction HUD
        active_road = roads[current_road_idx]
        cv2.rectangle(frame, (0, 0), (w, 50), (20, 20, 20), -1)
        msg = f"CALIBRATING: {road_names[active_road]} | Points: {len(current_pts)}/4 | [SPACE]: Next Road | [S]: Save"
        cv2.putText(frame, msg, (15, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        cv2.imshow("Calibrate Road Zones", frame)
        key = cv2.waitKey(20) & 0xFF

        if key == 27: # ESC
            break
        elif key == ord('r') or key == ord('R'):
            current_pts = []
            collected_points[active_road] = []
            print(f"[CALIBRATE] Cleared points for {active_road}")
        elif key in [32, 13]: # SPACE or ENTER
            if len(current_pts) == 4:
                if current_road_idx < 2:
                    current_road_idx += 1
                    current_pts = []
                    print(f"\nNow Calibrating {road_names[roads[current_road_idx]]}...")
                else:
                    print("\nAll 3 roads calibrated! Press [S] to save to zones.json.")
        elif key == ord('s') or key == ord('S'):
            # Save
            with open("zones.json", "w") as f:
                json.dump(collected_points, f, indent=4)
            print("[CALIBRATE] Successfully saved zones.json!")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
