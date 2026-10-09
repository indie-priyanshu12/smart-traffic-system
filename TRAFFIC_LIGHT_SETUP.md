# Stripped-Down Traffic Light Testing Guide

This guide covers the minimal hardware wiring, breadboard layout, and testing procedure for running the **3-Way Traffic Light System** with the YOLO computer vision pipeline using only:
- **1× ESP32 DevKit** (powered via USB)
- **9× 5mm LEDs** (3 Red, 3 Yellow, 3 Green)
- **9× 220Ω Resistors** (Red-Red-Brown-Gold)
- **1× 16x2 Character LCD** (with I2C Backpack)
- **1× 63-Row Breadboard** + Jumper wires

---

## 1. Bill of Materials & Specifications

| Component | Quantity | Value / Specs | Polarity / Notes |
| :--- | :--- | :--- | :--- |
| **ESP32 DevKit V1** | 1 | 30 or 38 pins, 3.3V logic | Powered via standard 5V Micro-USB / USB-C cable |
| **Red LEDs** | 3 | $V_f \approx 2.0\text{V}$, $10\text{mA}$ | Long leg = Anode (+), Short leg / flat rim = Cathode (-) |
| **Yellow LEDs** | 3 | $V_f \approx 2.1\text{V}$, $10\text{mA}$ | Long leg = Anode (+), Short leg / flat rim = Cathode (-) |
| **Green LEDs** | 3 | $V_f \approx 3.0\text{V}$, $10\text{mA}$ | Long leg = Anode (+), Short leg / flat rim = Cathode (-) |
| **Current Resistors** | 9 | 220Ω (or 330Ω), 1/4W | Red-Red-Brown-Gold bands (non-polar) |
| **16x2 LCD Display** | 1 | HD44780 with PCF8574 I2C module | 4 pins: GND, VCC, SDA, SCL |
| **Breadboard** | 1 | Standard 63-row dual-rail | Full-size prototyping breadboard |
| **Jumper Wires** | ~20 | Male-to-Male & Female-to-Male | Dupont jumper wires |

---

## 2. Complete Pinout Table

### A. 9 Traffic LEDs (Roads A, B, C)
All LED **Cathodes (-)** connect to the common breadboard **GND rail `(-)`**.  
Each LED **Anode (+)** connects in series through a **220Ω resistor** to the specified ESP32 GPIO:

| Road Approach | Signal Color | Component Pin | ESP32 GPIO | Logic Level | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Road A (North)** | 🔴 **Red** | Anode (+) via 220Ω | **GPIO 18** | 3.3V Output | Safe output pin |
| | 🟡 **Yellow** | Anode (+) via 220Ω | **GPIO 19** | 3.3V Output | 2.0s Transition indicator |
| | 🟢 **Green** | Anode (+) via 220Ω | **GPIO 21** | 3.3V Output | Safe output pin |
| **Road B (East)** | 🔴 **Red** | Anode (+) via 220Ω | **GPIO 22** | 3.3V Output | Safe output pin |
| | 🟡 **Yellow** | Anode (+) via 220Ω | **GPIO 23** | 3.3V Output | 2.0s Transition indicator |
| | 🟢 **Green** | Anode (+) via 220Ω | **GPIO 25** | 3.3V Output | Safe output pin |
| **Road C (West)** | 🔴 **Red** | Anode (+) via 220Ω | **GPIO 26** | 3.3V Output | Safe output pin |
| | 🟡 **Yellow** | Anode (+) via 220Ω | **GPIO 27** | 3.3V Output | 2.0s Transition indicator |
| | 🟢 **Green** | Anode (+) via 220Ω | **GPIO 32** | 3.3V Output | Safe output pin |
| **All 9 LEDs** | **Cathodes (-)** | Short leg / Flat rim | **GND Rail** | 0V Reference | Common Ground bus |

---

### B. 16x2 Character LCD (I2C Backpack)

Connect the 4-pin female header on the I2C backpack using Female-to-Male jumper wires:

| LCD Module Pin | ESP32 Pin / Rail | Purpose & Notes |
| :--- | :--- | :--- |
| **GND** | **ESP32 GND** *(or Blue `-` Rail)* | Ground reference |
| **VCC** | **ESP32 VIN** *(or 5V pin)* | **Must connect to 5V (VIN)** — 3.3V produces faint characters |
| **SDA** | **GPIO 4** *(or GPIO 16)* | I2C Data line *(GPIO 21 is occupied by Road A Green)* |
| **SCL** | **GPIO 5** *(or GPIO 17)* | I2C Clock line *(GPIO 22 is occupied by Road B Red)* |

> [!TIP]
> **Contrast Potentiometer**: If the LCD powers on with only blank blocks or solid white squares, rotate the small brass potentiometer on the back of the I2C backpack with a small screwdriver until characters appear sharp.

---

## 3. 63-Row Breadboard Layout Plan

This layout keeps all 3 traffic clusters separated cleanly down the breadboard:

```
Row  1 - 18 : ESP32 DevKit mounted across center divider (USB facing top edge)
Row 19 - 21 : [Buffer gap]

Row 22 - 32 : [ROAD A - NORTH TRAFFIC LIGHT]
   • Row 23 : Road A RED    (Anode + 220Ω to GPIO 18, Cathode to Blue - Rail)
   • Row 27 : Road A YELLOW (Anode + 220Ω to GPIO 19, Cathode to Blue - Rail)
   • Row 31 : Road A GREEN  (Anode + 220Ω to GPIO 21, Cathode to Blue - Rail)

Row 33 - 35 : [Buffer gap]

Row 36 - 46 : [ROAD B - EAST TRAFFIC LIGHT]
   • Row 37 : Road B RED    (Anode + 220Ω to GPIO 22, Cathode to Blue - Rail)
   • Row 41 : Road B YELLOW (Anode + 220Ω to GPIO 23, Cathode to Blue - Rail)
   • Row 45 : Road B GREEN  (Anode + 220Ω to GPIO 25, Cathode to Blue - Rail)

Row 47 - 49 : [Buffer gap]

Row 50 - 60 : [ROAD C - WEST TRAFFIC LIGHT]
   • Row 51 : Road C RED    (Anode + 220Ω to GPIO 26, Cathode to Blue - Rail)
   • Row 55 : Road C YELLOW (Anode + 220Ω to GPIO 27, Cathode to Blue - Rail)
   • Row 59 : Road C GREEN  (Anode + 220Ω to GPIO 32, Cathode to Blue - Rail)

Power Bus Connections:
   • Connect ESP32 GND to the Breadboard Blue (-) Ground rail.
   • Connect ESP32 VIN to the Breadboard Red (+) Power rail (feeds 5V to LCD VCC).
```

---

## 4. Circuit Schematic (ASCII)

```
                          ESP32 DevKit (Powered via USB)
                      +-----------------------------------+
                      |                                   |
                      |  VIN (5V) ------------------------+-------------> [16x2 LCD VCC]
                      |  GND -----------------------------+--[GND Rail]-> [16x2 LCD GND]
                      |                                   |          |
                      |  GPIO 4 (SDA) --------------------+----------> [16x2 LCD SDA]
                      |  GPIO 5 (SCL) --------------------+----------> [16x2 LCD SCL]
                      |                                   |
(Road A North)        |  GPIO 18 ----[ 220Ω ]---> [RED A] |
                      |  GPIO 19 ----[ 220Ω ]---> [YEL A] |
                      |  GPIO 21 ----[ 220Ω ]---> [GRN A] |
                      |                                   |
(Road B East)         |  GPIO 22 ----[ 220Ω ]---> [RED B] |
                      |  GPIO 23 ----[ 220Ω ]---> [YEL B] |
                      |  GPIO 25 ----[ 220Ω ]---> [GRN B] |
                      |                                   |
(Road C West)         |  GPIO 26 ----[ 220Ω ]---> [RED C] |
                      |  GPIO 27 ----[ 220Ω ]---> [YEL C] |
                      |  GPIO 32 ----[ 220Ω ]---> [GRN C] |
                      +-----------------------------------+
                                                              |
                                           All 9 LED Cathodes |
                                           connected to GND --+
```

---

## 5. Firmware Upload & Configuration

1. Open `firmware/esp32_traffic_controller/esp32_traffic_controller.ino` in the Arduino IDE.
2. Ensure you have installed the **ESP32 Board Package** and the **ArduinoJson** library.
3. Update your Wi-Fi credentials in lines 20–21:
   ```cpp
   const char* WIFI_SSID = "YOUR_WIFI_SSID";
   const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";
   ```
4. Select board **ESP32 Dev Module**, choose the correct COM port, and click **Upload**.
5. Open the Serial Monitor at **115200 baud** and record the assigned IP address:
   ```text
   [WIFI] Connected! IP Address: 192.168.1.50
   [HTTP] Web server active on port 80
   ```

---

## 6. Testing with the YOLO Python Vision Pipeline

1. **Install Python dependencies** (if not already done):
   ```bash
   cd python_vision
   pip install -r requirements.txt
   ```

2. **Launch the main vision pipeline**:
   Pass your ESP32 IP address and webcam index:
   ```bash
   python main_vision.py --esp32 192.168.1.50 --camera 0
   ```
   *(Note: The Python vision script will automatically tolerate the absence of the Arduino Uno gate peripheral and will communicate directly with the ESP32 over Wi-Fi).*

3. **Verify Signal Behavior**:
   - **Normal Round-Robin Cycle**:
     - Road A: Green (8.0s) $\rightarrow$ Yellow (2.0s) $\rightarrow$ Red
     - Road B: Green (8.0s) $\rightarrow$ Yellow (2.0s) $\rightarrow$ Red
     - Road C: Green (8.0s) $\rightarrow$ Yellow (2.0s) $\rightarrow$ Red
   - **Emergency Preemption Test**:
     - Click the OpenCV camera preview window.
     - Press key **`A`**, **`B`**, or **`C`** on your keyboard to simulate an ambulance approaching on that road.
     - Observe the currently active road switch to **Yellow for exactly 2.0 seconds** (safety clearance delay), followed by the requested emergency road turning **Green**.
     - Press **`N`** to release the emergency lock and return to normal round-robin scheduling.
