# Requirements & Software Configuration Guide

This guide details the complete software prerequisites, environment installation, network configuration, and step-by-step testing instructions for running the Smart Traffic Preemption System.

---

## 1. System Requirements

### Hardware Requirements
- **Laptop / PC**: Windows 10/11, macOS, or Ubuntu Linux (equipped with a webcam or external USB camera).
- **ESP32 DevKit V1**: Micro-USB or Type-C cable for programming and power.
- **Arduino Uno R3**: Standard USB Type-A to Type-B cable.
- **Local Wi-Fi Network**: A 2.4 GHz Wi-Fi network (or smartphone Wi-Fi hotspot) that both the laptop and the ESP32 can connect to.

### Software Prerequisites
- **Arduino IDE**: Version 2.x (or 1.8.x legacy).
- **Python**: Version 3.9 through 3.14 (64-bit).
- **Git** (optional, for code management).

---

## 2. Arduino IDE Setup & Library Installation

### 2.1 ESP32 Board Package Setup
1. Open **Arduino IDE**.
2. Navigate to **File > Preferences**.
3. In **Additional boards manager URLs**, add:
   ```
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```
4. Click **OK**.
5. Go to **Tools > Board > Boards Manager...**, search for `esp32` by *Espressif Systems*, and click **Install**.

### 2.2 Installing Required Arduino Libraries
Go to **Sketch > Include Library > Manage Libraries...** and install the following:

| Library Name | Author | Purpose | Target Board |
| :--- | :--- | :--- | :--- |
| **`ArduinoJson`** | Benoit Blanchon | JSON serialization/deserialization for REST endpoints | ESP32 |
| **`LiquidCrystal_I2C`**| Frank de Brabander | I2C driver for 16x2 LCD display (PCF8574 backpack) | Arduino Uno |
| **`Servo`** | Arduino built-in | Controls the SG90 micro-servo boom barrier | Arduino Uno |

---

## 3. Python Environment & Dependency Installation

1. Open PowerShell or Command Prompt in the repository's `python_vision` directory:
   ```powershell
   cd c:\Users\utkar\Documents\WORKSPACE\smart-traffic-system\python_vision
   ```
2. Install the required Python packages:
   ```powershell
   python -m pip install -r requirements.txt
   ```
   *Dependencies installed include*:
   - `ultralytics`: YOLOv8 deep-learning vehicle detection engine.
   - `opencv-python`: Camera capture, zone rendering, and OpenCV HUD overlays.
   - `requests`: HTTP REST communication with the ESP32.
   - `pyserial`: Serial communication with the Arduino Uno.
   - `fastapi` & `uvicorn`: Web telemetry bridge.

---

## 4. Network & IP Configuration

### 4.1 Configuring ESP32 Wi-Fi Credentials
1. Open [`firmware/esp32_traffic_controller/esp32_traffic_controller.ino`](file:///c:/Users/utkar/Documents/WORKSPACE/smart-traffic-system/firmware/esp32_traffic_controller/esp32_traffic_controller.ino) in Arduino IDE.
2. Edit lines 16–17 with your local Wi-Fi SSID and Password:
   ```cpp
   const char* WIFI_SSID = "Your_WiFi_Network";
   const char* WIFI_PASS = "Your_WiFi_Password";
   ```
3. Connect your ESP32 via USB, select **Tools > Board > ESP32 Dev Module**, choose the correct COM port, and click **Upload**.
4. Open the **Serial Monitor** at **115200 baud**.
5. Once connected, the ESP32 will print its assigned IP address:
   ```
   [WIFI] Connected successfully!
   [WIFI] ESP32 IP Address: 192.168.1.105
   ```

> [!NOTE]
> If no Wi-Fi network is available, the ESP32 automatically creates a fallback Access Point named `ESP32-Traffic-System` (password: `emergency123`) with static IP `192.168.4.1`.

### 4.2 Flashing Arduino Uno
1. Open [`firmware/arduino_hospital_gate/arduino_hospital_gate.ino`](file:///c:/Users/utkar/Documents/WORKSPACE/smart-traffic-system/firmware/arduino_hospital_gate/arduino_hospital_gate.ino) in Arduino IDE.
2. Select **Tools > Board > Arduino Uno**, choose its COM port, and click **Upload**.
3. Verify on boot that the 16x2 LCD displays `SMART TRAFFIC - GATE SYSTEM OK`.

---

## 5. Camera Road Tracing & Calibration

The system identifies which road an ambulance is approaching by checking if the vehicle enters defined polygon boundaries for **Road A (North)**, **Road B (East)**, or **Road C (West)**.

### 5.1 Interactive Calibration Utility
If your camera is mounted at a unique angle or positioned over a physical model track:
1. Run the calibration script:
   ```powershell
   python calibrate_zones.py
   ```
2. A window opens with your live camera stream:
   - Click the 4 corners of **Road A** in order (clockwise or counter-clockwise).
   - Press `[SPACE]` to move to **Road B**, and click its 4 corners.
   - Press `[SPACE]` to move to **Road C**, and click its 4 corners.
   - Press `[S]` to save the geometry to `zones.json`.
3. The main vision pipeline will automatically load this custom configuration on launch.

---

## 6. Execution & Operation

Launch the vision system by pointing it to your ESP32's IP address:

```powershell
python main_vision.py --esp32 192.168.1.105 --camera 0
```

*(If you don't specify an IP, it defaults to `192.168.1.100` or operates in local simulation mode).*

### Interactive Hotkeys for Demonstrations & Testing
The OpenCV window includes active hotkeys to test all scenarios without requiring physical vehicle models in front of the lens:

| Key | Action | Description |
| :---: | :--- | :--- |
| **`[A]`** | **Simulate Ambulance on Road A** | Triggers 2s Yellow transition on active road, then grants Road A Green |
| **`[B]`** | **Simulate Ambulance on Road B** | Triggers 2s Yellow transition on active road, then grants Road B Green |
| **`[C]`** | **Simulate Ambulance on Road C** | Triggers 2s Yellow transition on active road, then grants Road C Green |
| **`[R]`** | **Reset to Normal** | Clears emergency override and resumes 8s normal round-robin cycle |
| **`[G]`** | **Toggle Hospital Gate** | Manually opens/closes the hospital servo gate barrier |
| **`[Q]`** | **Quit** | Closes camera feed and releases all ports |

---

## 7. Troubleshooting & FAQs

### 1. 16x2 LCD is blank or shows white boxes
- **Cause**: Contrast trimmer needs adjustment, or incorrect I2C address.
- **Fix**: Use a small screwdriver to turn the potentiometer potentiometer on the back of the I2C backpack until the text appears sharp. If still blank, verify whether the address is `0x27` or `0x3F` using an I2C scanner sketch.

### 2. Arduino resets or LCD flickers when the servo moves
- **Cause**: Servo drawing transient current surges from the Arduino 5V pin.
- **Fix**: Never power the servo motor from the Arduino board. Use a dedicated external 5V supply, tie the supply's negative terminal to the Arduino GND, and add a 100µF capacitor across the servo power wires.

### 3. Python script shows `requests.exceptions.ConnectTimeout`
- **Cause**: Laptop and ESP32 are not on the same subnet, or Wi-Fi isolation is enabled on the router.
- **Fix**: Ensure the laptop is on the same 2.4 GHz Wi-Fi network. Open a web browser on the laptop and test navigating to `http://<ESP32_IP>/api/status`. If it loads JSON, the network link is functional.

### 4. Upload fails on ESP32 (`A fatal error occurred: Failed to connect`)
- **Fix**: Press and hold the **BOOT** button on the ESP32 board when the Arduino IDE displays `Connecting........_____`, then release it once flashing starts.
