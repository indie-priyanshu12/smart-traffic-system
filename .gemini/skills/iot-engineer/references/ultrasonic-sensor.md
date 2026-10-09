# Ultrasonic Sensor Reference (HC-SR04 and relatives)

## Contents
1. How it works
2. Variants and specs
3. Wiring (Uno and ESP32)
4. Basic code (Uno and ESP32)
5. Reliable readings: timeouts, filtering, temperature compensation
6. Non-blocking measurement
7. NewPing library
8. Using it with a servo (scanner) and LCD
9. Limits and physics
10. Python integration
11. Troubleshooting

---

## 1. How it works

The module has a transmitter and a receiver (the two "eyes"). To measure:

1. Send a 10 µs HIGH pulse to **Trig**.
2. The module emits eight 40 kHz ultrasonic bursts.
3. **Echo** goes HIGH when the burst is sent and LOW when the echo returns.
4. The HIGH duration = round-trip time. Distance = time x speed of sound / 2.

Speed of sound in air at 20 C is about 343 m/s = 0.0343 cm/µs.

```
distance_cm = duration_us * 0.0343 / 2      (about duration_us / 58.3)
distance_in = duration_us / 148
```

## 2. Variants and specs

| Module          | Supply | Logic (Echo)   | Range (approx.)  | Notes                                         |
|-----------------|--------|----------------|------------------|-----------------------------------------------|
| HC-SR04         | 5 V    | 5 V            | 2-400 cm         | Most common; about 15 mA; about 15 degree cone |
| HC-SR04P / RCWL-1601 | 3-5.5 V | 3.3 V-friendly | 2-400 cm   | Safe for ESP32 when powered at 3.3 V (check module) |
| JSN-SR04T       | 5 V    | 5 V            | about 25-450 cm  | Waterproof probe; larger blind zone           |
| US-100          | 2.4-5.5 V | matches supply | 2-450 cm      | UART mode and built-in temperature compensation |
| A02YYUW         | 3.3-5 V| UART           | 3-450 cm         | Waterproof, UART output                       |

Measurement cycle: wait at least 50-60 ms between pings so echoes from the previous burst die out.

## 3. Wiring

HC-SR04 pins: VCC, Trig, Echo, GND.

**Arduino Uno (5 V logic, direct connection):**

| HC-SR04 | Uno       |
|---------|-----------|
| VCC     | 5 V       |
| Trig    | D7        |
| Echo    | D8        |
| GND     | GND       |

(Any digital pins work. D2/D3 if you want interrupt-based timing.)

**ESP32 (3.3 V logic): Echo is a 5 V signal - protect the GPIO.**

Option 1 - voltage divider on Echo (cheap and works):

```
HC-SR04 Echo ---[1 kΩ]---+---[2 kΩ]--- GND
                         |
                         +--- ESP32 GPIO (e.g. GPIO 26)
```
Output = 5 V x 2/(1+2) = 3.33 V.

Option 2 - bidirectional level shifter module (BSS138 type).
Option 3 - use a 3.3 V-tolerant module (HC-SR04P, RCWL-1601 at 3.3 V, US-100).

| HC-SR04 | ESP32                                  |
|---------|----------------------------------------|
| VCC     | 5 V (VIN)                              |
| Trig    | GPIO 25 (3.3 V output is enough to trigger) |
| Echo    | GPIO 26 through the divider            |
| GND     | GND                                    |

Trig accepts the ESP32's 3.3 V HIGH in nearly all modules. Echo must be divided.

## 4. Basic code

Uno:

```cpp
constexpr uint8_t PIN_TRIG = 7;
constexpr uint8_t PIN_ECHO = 8;
constexpr unsigned long ECHO_TIMEOUT_US = 30000UL;   // about 5 m round trip max

void setup() {
  Serial.begin(115200);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  digitalWrite(PIN_TRIG, LOW);
}

// Returns distance in cm, or NAN if no echo
float readDistanceCm() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);

  unsigned long us = pulseIn(PIN_ECHO, HIGH, ECHO_TIMEOUT_US);
  if (us == 0) return NAN;                 // timeout: nothing in range or bad wiring
  return us * 0.0343f / 2.0f;
}

void loop() {
  float cm = readDistanceCm();
  if (isnan(cm)) Serial.println(F("out of range"));
  else { Serial.print(cm, 1); Serial.println(F(" cm")); }
  delay(60);
}
```

ESP32: same code works (use pins 25/26). Use `Serial.printf("%.1f cm\n", cm);` if desired.
`pulseIn` works on ESP32; its timeout is in µs as well.

Always pass a timeout to `pulseIn`. Without it a missing echo blocks for about 1 s.

## 5. Reliable readings

**Reject invalid values**: treat timeout (`NAN`) and out-of-spec values (below 2 cm or above 400 cm) as invalid.

**Median filter** (best single fix for spikes):

```cpp
float readMedianCm(uint8_t n = 5) {
  float v[9];
  if (n > 9) n = 9;
  uint8_t count = 0;
  for (uint8_t i = 0; i < n; i++) {
    float d = readDistanceCm();
    if (!isnan(d)) v[count++] = d;
    delay(60);
  }
  if (count == 0) return NAN;
  // insertion sort
  for (uint8_t i = 1; i < count; i++) {
    float key = v[i]; int j = i - 1;
    while (j >= 0 && v[j] > key) { v[j + 1] = v[j]; j--; }
    v[j + 1] = key;
  }
  return v[count / 2];
}
```

This blocks about n x 60 ms. For a responsive system use the non-blocking approach below.

**Exponential moving average** (smoothing a stream):

```cpp
float ema = NAN;
float smooth(float x, float alpha = 0.3f) {
  if (isnan(x)) return ema;                 // keep last value
  ema = isnan(ema) ? x : alpha * x + (1 - alpha) * ema;
  return ema;
}
```

**Hysteresis for thresholds**: trigger at 20 cm, release at 25 cm to stop flapping.

**Temperature compensation**:

```
speed_m_per_s = 331.3 + 0.606 * temperatureC
distance_cm   = duration_us * (speed_m_per_s / 10000.0) / 2
```

At 0 C vs 30 C the speed differs by about 5%, i.e. about 5 cm error at 100 cm. Use a DHT22/DS18B20/BME280 if accuracy matters.

## 6. Non-blocking measurement

Use `millis()` to space pings and avoid long blocking:

```cpp
unsigned long lastPing = 0;
constexpr unsigned long PING_INTERVAL_MS = 60;
float lastCm = NAN;

void updateDistance() {
  if (millis() - lastPing < PING_INTERVAL_MS) return;
  lastPing = millis();
  float d = readDistanceCm();               // blocks at most ~30 ms (timeout)
  if (!isnan(d)) lastCm = smooth(d);
}
```

For fully non-blocking timing, use an interrupt on Echo (CHANGE) that records
`micros()` at rising and falling edges (on Uno, Echo on D2 or D3; on ESP32, any GPIO,
with `IRAM_ATTR`). Compute the duration from the stored timestamps in `loop()`.

## 7. NewPing library

Library Manager: "NewPing" by Tim Eckel. Handles timing, median, and ping timers.

```cpp
#include <NewPing.h>
constexpr uint8_t TRIG = 7, ECHO = 8;
constexpr unsigned int MAX_CM = 200;
NewPing sonar(TRIG, ECHO, MAX_CM);

void loop() {
  delay(50);
  unsigned int cm = sonar.ping_cm();        // 0 = no echo/out of range
  unsigned int cmMedian = sonar.convert_cm(sonar.ping_median(5));
}
```

Note: NewPing returns `0` for no echo - treat it as invalid, not as "0 cm".
NewPing works on Uno; on ESP32 prefer own code or check library compatibility (ESP32 support exists in recent releases; timer-based `ping_timer` features may not).

## 8. Using it with a servo (scanner) and LCD

Mount the sensor on a servo to sweep and map distances (radar-style). Key points:
- Move the servo, wait for it to settle (about 15-20 ms per few degrees), then ping.
- Use steps of 5-10 degrees: the beam is about 15 degrees wide.
- Servo on Uno pin 9, ultrasonic on pins 7/8 (avoid PWM-timer conflicts).
- Supply the servo externally with common ground (`servo-motor.md`).
- Display angle and distance on the LCD with padded fields (`lcd-display.md`).
- Complete working example with Python polar plot: `project-examples.md`.

## 9. Limits and physics

- **Blind zone**: below about 2 cm (HC-SR04) the echo is unusable; about 20-25 cm for JSN-SR04T.
- **Angle**: about 15 degree cone. Targets off-axis or small thin objects (poles, wires) may be missed.
- **Surface**: hard, flat, perpendicular surfaces reflect well; angled surfaces deflect the echo away; soft materials (fabric, foam, fur) absorb it.
- **Noise**: other ultrasonic sensors firing at the same time cause false readings. Fire sensors in sequence, not simultaneously.
- **Wind, rain, temperature gradients, vibration** reduce accuracy. Mount the sensor rigidly.
- **Accuracy**: about 3 mm theoretical; expect 1-3 cm in practice.
- **Voltage dips** (from servos/motors on the same 5 V) cause erratic readings.
- **Outdoors/liquids**: use a waterproof probe (JSN-SR04T) and mind its minimum distance.

## 10. Python integration

Firmware prints one CSV record per measurement:

```cpp
Serial.print(millis());
Serial.print(',');
if (isnan(cm)) Serial.println("nan"); else Serial.println(cm, 1);
```

Python reader with validation:

```python
import math, time
import serial

PORT, BAUD = "COM3", 115200               # "/dev/ttyUSB0" or "/dev/ttyACM0" on Linux

def parse(line: str):
    try:
        t_ms, d = line.strip().split(",")
        d = float(d)
        return int(t_ms), (None if math.isnan(d) else d)
    except ValueError:
        return None                       # ignore malformed lines (startup noise, debug text)

with serial.Serial(PORT, BAUD, timeout=1) as ser:
    time.sleep(2)                         # Uno resets on open
    ser.reset_input_buffer()
    while True:
        raw = ser.readline().decode("utf-8", errors="ignore")
        rec = parse(raw)
        if rec and rec[1] is not None:
            print(f"{rec[0]} ms  {rec[1]:.1f} cm")
```

For MQTT publishing from an ESP32, see `python-network-mqtt-http-ble.md`.
For live plotting, logging to CSV/SQLite, and the radar plot, see `python-serial.md` and `project-examples.md`.

## 11. Troubleshooting

| Symptom                                 | Cause and fix                                                          |
|-----------------------------------------|------------------------------------------------------------------------|
| Always 0 / timeout                      | Trig/Echo swapped, no 5 V on VCC, no common ground, object too close/far |
| Random large spikes                     | No median filter, noisy 5 V (servo on same rail), multiple sensors firing at once |
| Readings stuck at one value             | Echo pin wired to an input that is not reading, or sketch never re-triggers |
| Sketch freezes                          | `pulseIn` without timeout, sensor disconnected                         |
| ESP32 resets/ bad readings              | 5 V on Echo without divider; weak 5 V supply                           |
| Values drift with weather/temperature   | Apply temperature compensation                                         |
| Wrong distance by constant factor       | Forgot `/2` for round trip, or wrong constant (0.0343 cm/µs)           |
| Misses thin or angled objects           | Narrow target outside beam, sound deflected; re-aim or use multiple sensors |
