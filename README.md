# IoT-Based Smart Traffic Management System for Emergency Vehicles

An intelligent 3-way traffic management system engineered for emergency vehicles (ambulances, fire engines) featuring:
- **Computer Vision (YOLO)**: Detects incoming ambulances and classifies approach roads using camera line tracing.
- **Realistic Traffic Timing**: Implements an automatic **2.0-second Yellow light transition** before switching any road to Green.
- **ESP32 Wi-Fi Node**: Controls 9 traffic LEDs (Roads A, B, C: Red, Yellow, Green) and hosts a REST API for over-the-air signal preemption.
- **Arduino Uno Peripheral Unit**: Drives a 16x2 I2C LCD roadside display, HC-SR04 ultrasonic distance sensor, SG90 servo-actuated hospital entrance boom barrier, and alert buzzer.
- **Saved Web Dashboard**: Complete React.js dashboard archived in `web_dashboard/` for future deployment.

---

## 📚 Essential Documentation

The complete project documentation is organized into three consolidated guides:

| Document | Purpose & Contents |
| :--- | :--- |
| 📖 [**`PROJECT_DESCRIPTION.md`**](docs/PROJECT_DESCRIPTION.md) | Full system description, objectives, 3-way intersection geometry, signal timing logic (2-second yellow delay), and inter-device communication workflows. |
| 🔌 [**`HARDWARE_CONNECTIONS.md`**](docs/HARDWARE_CONNECTIONS.md) | Complete Bill of Materials (BOM), pinout tables for ESP32 and Arduino Uno, 3.3V vs 5V logic compatibility, servo power isolation, and ASCII schematics. |
| 🚥 [**`TRAFFIC_LIGHT_SETUP.md`**](TRAFFIC_LIGHT_SETUP.md) | Stripped-down testing guide for ESP32 + 9 LEDs + 16x2 LCD on breadboard with YOLO testing. |
| ⚙️ [**`REQUIREMENTS_AND_CONFIGURATION.md`**](docs/REQUIREMENTS_AND_CONFIGURATION.md) | Hardware & software prerequisites, Arduino IDE library installations, Python environment setup, Wi-Fi IP configuration, camera road calibration, and testing guide. |

---

## 📁 Repository Structure

```
smart-traffic-system/
├── README.md                                 # Master overview and navigation
├── docs/                                     # Essential project documentation
│   ├── PROJECT_DESCRIPTION.md               # Architecture, working principle & signal timing
│   ├── HARDWARE_CONNECTIONS.md              # Wiring tables, pinouts, power & schematics
│   └── REQUIREMENTS_AND_CONFIGURATION.md    # Software setup, Wi-Fi config, calibration & tests
├── firmware/
│   ├── esp32_traffic_controller/
│   │   ├── esp32_traffic_controller.ino     # ESP32 9-LED traffic light controller with REST API
│   │   └── secrets.h.example                # Wi-Fi credentials template
│   └── arduino_hospital_gate/
│       └── arduino_hospital_gate.ino        # 16x2 LCD, Ultrasonic sensor, Servo & Buzzer
├── python_vision/
│   ├── requirements.txt                     # Dependencies (ultralytics, opencv, requests, etc.)
│   ├── config.py                            # IP address, camera index, zone coordinates
│   ├── zone_detector.py                     # Road line tracing & point-in-polygon checks
│   ├── calibrate_zones.py                   # Interactive click-to-calibrate road boundary tool
│   ├── esp32_client.py                      # Wi-Fi HTTP client for ESP32
│   ├── uno_serial.py                        # Serial interface to Arduino Uno
│   ├── api_bridge.py                        # Telemetry API bridge
│   └── main_vision.py                       # Main YOLO vision detection & preemption engine
└── web_dashboard/                           # React.js web dashboard (saved for future use)
    ├── package.json
    ├── src/
    └── index.html
```

---

## ⚡ Quick Start Summary

1. **Wire the Hardware**:
   - Follow the pin connection tables in [`docs/HARDWARE_CONNECTIONS.md`](docs/HARDWARE_CONNECTIONS.md).
   - ESP32 controls 9 LEDs on GPIOs 18, 19, 21 (Road A), 22, 23, 25 (Road B), 26, 27, 32 (Road C).
   - Arduino Uno connects to 16x2 LCD (A4/A5), HC-SR04 (D7/D6), SG90 Servo (D9), and Buzzer (D8).
2. **Flash the Microcontrollers**:
   - Upload [`firmware/esp32_traffic_controller/esp32_traffic_controller.ino`](firmware/esp32_traffic_controller/esp32_traffic_controller.ino) to the ESP32.
   - Upload [`firmware/arduino_hospital_gate/arduino_hospital_gate.ino`](firmware/arduino_hospital_gate/arduino_hospital_gate.ino) to the Arduino Uno.
3. **Run the Python Vision Pipeline**:
   ```bash
   cd python_vision
   pip install -r requirements.txt
   python main_vision.py --esp32 <ESP32_IP> --camera 0
   ```
4. **Test the System**:
   - In the OpenCV camera window, press `[A]`, `[B]`, or `[C]` to simulate an ambulance on that road.
   - Observe the active road transition to **Yellow for 2.0 seconds**, followed by the requested road turning **Green**.
   - Check the 16x2 LCD updating to `EMERGENCY! RD:X`.
   - Bring an object within 15 cm of the ultrasonic sensor to open the hospital servo boom barrier.
