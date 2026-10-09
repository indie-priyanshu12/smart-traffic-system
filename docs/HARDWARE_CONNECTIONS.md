# Hardware Connections & Circuit Wiring Guide

This document contains the complete electrical pinout tables, schematics, power distribution recommendations, and wiring rules for the Smart Traffic System.

---

## 1. Bill of Materials (BOM)

### Primary Microcontrollers
| Item | Model | Voltage | Role |
| :--- | :--- | :--- | :--- |
| **Microcontroller 1** | ESP32 DevKit V1 (30 or 38 pins) | 5V USB in, **3.3V GPIO logic** | Wi-Fi REST Server & 9-LED Traffic Signal Driver |
| **Microcontroller 2** | Arduino Uno R3 (ATmega328P) | 5V USB in, **5V GPIO logic** | Roadside LCD, Hospital Ultrasonic Gate, Servo & Buzzer |

### Components & Peripherals
| Component | Quantity | Value / Specification | Role |
| :--- | :--- | :--- | :--- |
| **Red 5mm LEDs** | 3 | $V_f \approx 2.0\text{V}$, $I_f \approx 10\text{mA}$ | Stop signals for Roads A, B, C |
| **Yellow 5mm LEDs** | 3 | $V_f \approx 2.1\text{V}$, $I_f \approx 10\text{mA}$ | 2.0s Transition indicators for Roads A, B, C |
| **Green 5mm LEDs** | 3 | $V_f \approx 3.0\text{V}$, $I_f \approx 10\text{mA}$ | Go signals for Roads A, B, C |
| **Current Resistors** | 9 | 220Ω (or 330Ω), 1/4W | In series with each LED anode |
| **16x2 Character LCD** | 1 | HD44780 with PCF8574 I2C Backpack | Address `0x27` (or `0x3F`), 5V |
| **Ultrasonic Sensor** | 1 | HC-SR04 (4-pin) | Proximity trigger for hospital door |
| **Micro Servo Motor** | 1 | SG90 / MG90S (3-pin) | Hospital entrance barrier gate (0°–90°) |
| **Piezo Buzzer** | 1 | 5V Active or Passive Buzzer | Siren alerts & gate warnings |
| **Power Supply** | 1 | External 5V 1A DC adapter / Battery | Dedicated power for SG90 servo motor |
| **Decoupling Capacitor**| 1 | 100µF, 16V Electrolytic | Connected across servo power rails |
| **Breadboard & Wires** | — | Standard breadboard + Dupont jumpers | Male-to-Male and Male-to-Female |

---

## 2. ESP32 Traffic Light Controller Pinout (9 LEDs)

All LED cathodes connect to the ESP32 **GND** rail. Each anode connects via a **220Ω resistor** to the specified GPIO.

| Road Approach | Signal Color | Component Pin | ESP32 Pin | Logic Level | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Road A (North)** | **Red** | Anode (+) via 220Ω | **GPIO 18** | 3.3V Output | Safe general output |
| | **Yellow** | Anode (+) via 220Ω | **GPIO 19** | 3.3V Output | 2.0-second delay indicator |
| | **Green** | Anode (+) via 220Ω | **GPIO 21** | 3.3V Output | Safe general output |
| **Road B (East)** | **Red** | Anode (+) via 220Ω | **GPIO 22** | 3.3V Output | Safe general output |
| | **Yellow** | Anode (+) via 220Ω | **GPIO 23** | 3.3V Output | 2.0-second delay indicator |
| | **Green** | Anode (+) via 220Ω | **GPIO 25** | 3.3V Output | Safe general output |
| **Road C (West)** | **Red** | Anode (+) via 220Ω | **GPIO 26** | 3.3V Output | Safe general output |
| | **Yellow** | Anode (+) via 220Ω | **GPIO 27** | 3.3V Output | 2.0-second delay indicator |
| | **Green** | Anode (+) via 220Ω | **GPIO 32** | 3.3V Output | Safe general output |
| **All 9 LEDs** | **Cathode** | Flat edge (-) | **GND** | 0V Reference | Common Ground bus |
| **Inter-Board Link**| **UART2 TX** | Serial out | **GPIO 17** | 3.3V Output | Connects to Arduino Uno Pin D2 |
| **Common Ground** | **GND** | Reference Ground | **Uno GND** | 0V | **Required shared ground** |

> [!IMPORTANT]
> **GPIO Pin Selection Safety:**
> The selected pins avoid all strapping pins (GPIO 0, 2, 12, 15) and internal flash pins (GPIO 6–11). In addition, input-only pins (GPIO 34, 35, 36, 39) were strictly avoided for LED outputs.

---

## 3. Arduino Uno Roadside & Hospital Gate Pinout

| Peripheral | Peripheral Pin | Arduino Uno Pin | Logic Level | Connection Details |
| :--- | :--- | :--- | :--- | :--- |
| **16x2 LCD (I2C)** | **VCC** | **5V** | 5V Power | LCD backlight and PCF8574 chip power |
| | **GND** | **GND** | 0V Ground | Power return |
| | **SDA** | **A4** | 5V I2C Data | Hardware I2C SDA |
| | **SCL** | **A5** | 5V I2C Clock | Hardware I2C SCL |
| **HC-SR04 Sensor** | **VCC** | **5V** | 5V Power | Sensor power supply |
| | **GND** | **GND** | 0V Ground | Power return |
| | **Trig** | **D7** | 5V Output | 10 µs trigger pulse from Uno |
| | **Echo** | **D6** | 5V Input | 5V echo pulse into Uno |
| **SG90 Servo Motor**| **Signal (Orange)**| **D9** | 5V PWM | Timer1 PWM control signal (0° to 90°) |
| | **VCC (Red)** | **External 5V (+)**| 5V DC Supply | **Do not power from Uno 5V pin!** |
| | **GND (Brown)** | **Common GND** | 0V Ground | Join external supply GND with Uno GND |
| **Piezo Buzzer** | **Positive (+)** | **D8** | 5V Output | Siren tones & proximity beeps |
| | **Negative (-)** | **GND** | 0V Ground | Power return |
| **ESP32 Sync Link** | **RX Input** | **D2** | 3.3V Logic | SoftwareSerial RX (from ESP32 GPIO 17) |

---

## 4. Electrical Safety & Wiring Best Practices

### 4.1 SG90 Servo Power Isolation (Crucial)
An SG90 micro-servo motor draws a quiescent current of ~10–20 mA, but can spike to **500–650 mA during stall or initial movement**. 
- Attempting to power the servo directly from the Arduino Uno 5V regulator will cause a voltage brownout.
- This causes the Arduino to reboot continuously and corrupts characters on the 16x2 LCD.
- **Rule**: Connect the servo's Red (VCC) wire to an **external 5V supply** (or dedicated 4×AA battery pack). Connect the servo's Brown (GND) wire to both the external supply GND **and** the Arduino Uno GND. Add a **100µF capacitor** across the servo's VCC and GND.

### 4.2 ESP32 (3.3V) to Arduino Uno (5V) Logic Levels
- **ESP32 TX (GPIO 17) $\rightarrow$ Arduino Uno RX (Pin D2)**:
  - The ESP32 outputs a 3.3V high signal.
  - The ATmega328P datasheet specifies $V_{IH(\text{min})} = 0.6 \times V_{CC} = 0.6 \times 5.0\text{V} = 3.0\text{V}$.
  - Because 3.3V is above 3.0V, the Arduino reliably registers the signal as a clean digital HIGH without needing any level shifter.
- **ESP32 Inputs**: Never connect a 5V signal from the Arduino directly to an ESP32 GPIO pin, as ESP32 pins are **not 5V tolerant**. Since our architecture only sends commands unidirectionally from ESP32 to Uno, the ESP32 remains 100% safe.

---

## 5. Circuit Schematic (ASCII Diagram)

```
========================================================================================
                               ESP32 TRAFFIC CONTROLLER
========================================================================================
                           +------------------------+
                           |      ESP32 DevKit      |
                           |                        |
                           | GPIO 18 --[ 220R ]-----> [A-RED LED]----+
                           | GPIO 19 --[ 220R ]-----> [A-YEL LED]----+
                           | GPIO 21 --[ 220R ]-----> [A-GRN LED]----+
                           |                        |                |
                           | GPIO 22 --[ 220R ]-----> [B-RED LED]----+
                           | GPIO 23 --[ 220R ]-----> [B-YEL LED]----+
                           | GPIO 25 --[ 220R ]-----> [B-GRN LED]----+
                           |                        |                |
                           | GPIO 26 --[ 220R ]-----> [C-RED LED]----+
                           | GPIO 27 --[ 220R ]-----> [C-YEL LED]----+
                           | GPIO 32 --[ 220R ]-----> [C-GRN LED]----+
                           |                        |                |
                           | GND ------------------------------------+ (All LED Cathodes)
                           |                        |
                           | GPIO 17 (TX) ----------+
                           +------------------------+
                                                    | (3.3V Serial Stream)
                                                    v
========================================================================================
                             ARDUINO UNO ROADSIDE UNIT
========================================================================================
                           +------------------------+
                           |      Arduino Uno       |
                           |                        |
      (From ESP32 GPIO 17) | Pin D2 (SW RX) <-------+
                           |                        |
         [16x2 LCD SDA] <--| Pin A4 (SDA)           |
         [16x2 LCD SCL] <--| Pin A5 (SCL)           |
                           |                        |
      [HC-SR04 Trig D7] <--| Pin D7                 |
       [HC-SR04 Echo D6] ->| Pin D6                 |
                           |                        |
         [Piezo Buzzer] <--| Pin D8                 |
      [SG90 Servo PWM] <---| Pin D9                 |
                           |                        |
                           | GND -------------------+------------------+
                           +------------------------+                  |
                                                                       | (Common GND)
            [External 5V Power Supply]                                 |
                  (+) 5V ------------------> [SG90 Servo Red Wire]     |
                  (-) GND -----------------> [SG90 Servo Brown Wire] --+
```
