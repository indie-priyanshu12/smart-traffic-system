# Project Description: IoT Smart Traffic Management System for Emergency Vehicles

## 1. Executive Summary

Urban traffic congestion frequently impedes emergency response vehicles—such as ambulances and fire engines—leading to life-threatening transit delays. Conventional traffic lights operate on static timers or basic vehicle-actuated loops that cannot distinguish between general commuters and emergency vehicles. 

This project implements an **IoT-driven Smart Traffic Preemption System** for a 3-way intersection (Roads A, B, and C). By integrating **Computer Vision (YOLO)** with dual microcontrollers (**ESP32** and **Arduino Uno**), the system automatically detects approaching ambulances, identifies their entry lane, initiates a realistic **2.0-second Yellow light transition** to clear conflicting traffic safely, locks the emergency route to Green, and alerts roadside LCD units while actuating an automated hospital gate barrier.

---

## 2. System Architecture & Working Principle

```
+-----------------------------------------------------------------------------------+
|                            OVERHEAD CAMERA MODULE                                 |
+-----------------------------------------------------------------------------------+
                                          |
                                   (Video Stream)
                                          v
+-----------------------------------------------------------------------------------+
|                        LAPTOP / EDGE AI PROCESSOR                                 |
|  - Ultralytics YOLOv8 Vehicle & Ambulance Detection                               |
|  - Traced Road Boundary Polygons (Road A North, Road B East, Road C West)        |
|  - Centroid Point-in-Polygon Classification                                       |
|  - Triggers 2-Second Safety Yellow Countdown                                      |
+-----------------------------------------------------------------------------------+
                                          |
                               (Wi-Fi HTTP REST API)
                                          v
+-----------------------------------------------------------------------------------+
|                   ESP32 TRAFFIC SIGNAL CONTROLLER (3.3V)                          |
|  - Manages 9 LEDs (3 Red, 3 Yellow, 3 Green) across Roads A, B, and C             |
|  - Executes non-blocking millis() state machine                                    |
|  - Implements 2.0s Yellow Clearance Delay before granting Green                   |
|  - Maintains Emergency Priority lock until vehicle clears                         |
+-----------------------------------------------------------------------------------+
                                          |
                           (Hardware UART Serial Link)
                                          v
+-----------------------------------------------------------------------------------+
|                    ARDUINO UNO ROADSIDE & HOSPITAL GATE (5V)                      |
|  - 16x2 I2C LCD Display: Shows incoming lane ("EMERGENCY! RD:B")                  |
|  - HC-SR04 Ultrasonic Sensor: Detects ambulance arrival at hospital (< 15 cm)     |
|  - SG90 Servo Motor: Opens entrance boom barrier (0° -> 90°) for 5 seconds        |
|  - Piezo Buzzer: Emits audio siren and gate opening alerts                        |
+-----------------------------------------------------------------------------------+
```

---

## 3. Intersection Geometry & Approach Layout

The system monitors a **3-way junction** categorized into three distinct approach corridors:

| Road ID | Geographical Approach | Description & Default Zone |
| :--- | :--- | :--- |
| **Road A** | **North Approach** | Top-down vertical corridor feeding south into the junction. |
| **Road B** | **East Approach** | Right-side horizontal corridor feeding west into the junction. |
| **Road C** | **West Approach** | Left-side horizontal corridor feeding east into the junction. |

Virtual polygon boundaries are mapped across the camera feed using normalized $(x, y)$ coordinates. When an ambulance bounding box is detected, its centroid $(c_x, c_y)$ is checked against each road polygon using OpenCV's `pointPolygonTest`.

---

## 4. Signal Timing & 2-Second Yellow Light Transition Logic

A critical engineering requirement of real-world traffic engineering is preventing T-bone collisions when priority signals change. Abruptly switching a signal from Red to Green while cross-traffic is in motion causes severe hazards.

### Phase 1: Normal Round-Robin Operation (No Emergency)
- Sequence: **Road A $\rightarrow$ Road B $\rightarrow$ Road C $\rightarrow$ Road A**.
- **Green Duration**: 8.0 seconds per road.
- **Yellow Clearance Duration**: Exactly 2.0 seconds between road phase hand-offs.
- All non-active roads remain Red.

### Phase 2: Emergency Vehicle Inbound (Preemption Triggered)
When an emergency vehicle is detected approaching on **Road X** (e.g., Road B) while **Road Y** (e.g., Road A) is currently green:
1. **Yellow Safety Interlock (2.0s Delay)**:
   - Road Y is immediately switched from Green to **Yellow for exactly 2000 milliseconds**.
   - Road X and Road Z remain Red.
   - This 2-second clearance window permits vehicles already past the stop bar on Road Y to clear the intersection box safely.
2. **Priority Green Grant**:
   - Exactly at $t = 2.0\text{ s}$, Road Y switches to **Red**.
   - Road X switches to **Green**.
   - All other roads are locked in **Red**.
3. **Emergency Lock & Clearance Window**:
   - Road X remains locked in Green for the entire duration the ambulance is in the detection zone.
   - Once the ambulance leaves the zone, a 4.0-second clearance heartbeat ensures the vehicle has fully navigated through the junction.
4. **Safe Return to Normal Cycle**:
   - Road X receives a 2.0-second Yellow transition, after which normal round-robin scheduling resumes smoothly.

---

## 5. Hospital Entrance Automation & Roadside Unit

In addition to traffic signal preemption, the system connects to an intelligent hospital gateway unit driven by an **Arduino Uno**:
- **16x2 Roadside LCD**:
  - Displays real-time status visible to drivers and traffic officers:
    - Normal: `TRAFFIC: NORMAL` / `GATE: CLS >1m`
    - Emergency: `EMERGENCY! RD:B` / `GATE: OPEN 12cm`
- **Ultrasonic Vehicle Proximity (HC-SR04)**:
  - Mounted at the emergency bay entrance door.
  - Senses when the approaching ambulance reaches within **15 cm** (scalable for scale models or real distances).
- **Automated Entrance Barrier (SG90 Servo)**:
  - Actuates from 0° (horizontal barrier / closed door) to 90° (vertical / open door).
  - Automatically holds open for 5.0 seconds while the vehicle enters, then closes smoothly.
- **Audible Siren (Piezo Buzzer)**:
  - Emits double-beep pulses when an emergency road override is declared.
  - Emits warning frequency pulses while the hospital gate barrier is in motion.
