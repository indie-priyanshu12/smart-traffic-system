"""
Zone Detector Module for 3-Road Intersection.
Handles road tracing, polygon overlays, point-in-polygon vehicle detection,
and road calibration.
"""

import json
import os
import cv2
import numpy as np
from config import DEFAULT_ZONES

class ZoneDetector:
    def __init__(self, zones_file="zones.json"):
        self.zones_file = zones_file
        self.normalized_zones = self.load_zones()

    def load_zones(self) -> dict:
        """Load calibrated zones from file or fall back to defaults."""
        if os.path.exists(self.zones_file):
            try:
                with open(self.zones_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ZONE] Error reading {self.zones_file}: {e}. Using defaults.")
        return DEFAULT_ZONES.copy()

    def save_zones(self):
        """Save current zones to JSON file."""
        with open(self.zones_file, "w") as f:
            json.dump(self.normalized_zones, f, indent=4)
        print(f"[ZONE] Saved calibrated road zones to {self.zones_file}")

    def get_pixel_polygons(self, width: int, height: int) -> dict:
        """Convert normalized (0.0 - 1.0) coordinates to absolute pixel arrays."""
        pixel_zones = {}
        for road_id, points in self.normalized_zones.items():
            pts = [[int(pt[0] * width), int(pt[1] * height)] for pt in points]
            pixel_zones[road_id] = np.array(pts, dtype=np.int32)
        return pixel_zones

    def find_road_for_point(self, point: tuple, width: int, height: int) -> str:
        """
        Determine which road polygon contains the given (x, y) point.
        Returns 'A', 'B', 'C', or None.
        """
        pixel_zones = self.get_pixel_polygons(width, height)
        for road_id, poly in pixel_zones.items():
            # pointPolygonTest returns >= 0 if inside or on contour
            dist = cv2.pointPolygonTest(poly, (float(point[0]), float(point[1])), False)
            if dist >= 0:
                return road_id
        return None

    def draw_zones(self, frame: np.ndarray, active_emergency_road: str = None, highlighted_road: str = None) -> np.ndarray:
        """
        Draw transparent overlays, traced road lines, and informative banners
        for all 3 roads.
        """
        h, w = frame.shape[:2]
        pixel_zones = self.get_pixel_polygons(w, h)
        overlay = frame.copy()

        road_colors = {
            "A": (66, 135, 245),   # Blue / Amber
            "B": (245, 135, 66),   # Orange
            "C": (180, 80, 240)    # Violet / Purple
        }

        road_names = {
            "A": "ROAD A (North)",
            "B": "ROAD B (East)",
            "C": "ROAD C (West)"
        }

        alpha = 0.25

        for road_id, poly in pixel_zones.items():
            is_emergency = (active_emergency_road == road_id)
            is_highlighted = (highlighted_road == road_id)

            if is_emergency:
                fill_color = (0, 0, 230)       # Vivid Red for emergency
                border_color = (0, 50, 255)
                thickness = 3
            elif is_highlighted:
                fill_color = (0, 220, 220)     # Yellow highlight
                border_color = (0, 255, 255)
                thickness = 2
            else:
                fill_color = road_colors.get(road_id, (100, 100, 100))
                border_color = fill_color
                thickness = 2

            # Draw semi-transparent filled polygon
            cv2.fillPoly(overlay, [poly], fill_color)

            # Draw solid polygon boundary lines
            cv2.polylines(frame, [poly], isClosed=True, color=border_color, thickness=thickness)

            # Compute centroid of polygon for label placement
            M = cv2.moments(poly)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = poly[0][0], poly[0][1]

            # Road Label Badge
            label_text = f"[{road_id}] {road_names.get(road_id, road_id)}"
            if is_emergency:
                label_text = f"!! PRIORITY: ROAD {road_id} !!"

            # Draw text shadow and label
            cv2.putText(frame, label_text, (cx - 70, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
            text_color = (255, 255, 255) if not is_emergency else (0, 255, 255)
            cv2.putText(frame, label_text, (cx - 70, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, text_color, 2, cv2.LINE_AA)

        # Blend semi-transparent overlay
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        return frame
