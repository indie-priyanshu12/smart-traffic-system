# Servo Motor Reference

## Contents
1. How hobby servos work
2. Common models and electrical needs
3. Wiring and power (the part that most often goes wrong)
4. Arduino Uno: `Servo` library
5. ESP32: `ESP32Servo` library
6. Smooth and non-blocking motion
7. Continuous-rotation servos
8. Many servos: PCA9685
9. Control from Python
10. Calibration, limits, jitter
11. Troubleshooting

---

## 1. How hobby servos work

A hobby servo contains a DC motor, gearbox, potentiometer (position feedback) and a
control board. You send a repeating pulse about every 20 ms (50 Hz). The pulse **width**
sets the target angle:

| Pulse width | Typical position |
|-------------|------------------|
| about 500-1000 µs | 0 degrees (minimum) |
| about 1500 µs     | 90 degrees (center) |
| about 2000-2500 µs| 180 degrees (maximum) |

Exact end points vary by model. The default `Servo` library range is 544-2400 µs.
The servo holds position actively and draws current to resist load.

Wire colors: brown or black = GND; red = V+ (4.8-6 V); orange, yellow, or white = signal.

## 2. Common models

| Model         | Type                | Voltage | Torque (approx.) | Current (approx.)                     |
|---------------|---------------------|---------|------------------|---------------------------------------|
| SG90 / MG90S  | Micro, plastic/metal gears | 4.8-6 V | 1.8 kg·cm (SG90) | idle about 10 mA, moving 100-250 mA, stall can exceed 500 mA |
| MG995 / MG996R| Standard, metal gears | 4.8-7.2 V | 9-11 kg·cm   | moving 300-500 mA, stall about 1-2.5 A |
| DS3218 etc.   | High-torque standard | 4.8-6.8 V (check) | 20 kg·cm | up to several amps at stall          |

Use datasheet values when known; the numbers above are indicative. Size the supply for
**stall current x number of servos** (or at least for realistic peak load). Servos draw
short, sharp current spikes when starting or when blocked.

Signal level: 3.3 V signals from an ESP32 normally drive 5 V-powered servos fine (most
servos accept a logic high above about 2.5 V). If a particular servo misbehaves, add a
level shifter or a 74HCT-series buffer.

## 3. Wiring and power

Rules:
1. Power servos from a dedicated 5-6 V supply (battery pack, regulated adapter, or BEC).
2. Connect the supply ground to the microcontroller ground (common ground). Without this the signal has no reference and the servo jitters or ignores commands.
3. Add a 470-1000 µF electrolytic capacitor across the servo supply near the servo(s) to absorb current spikes. Add a 0.1 µF ceramic too.
4. Signal wire goes to a GPIO through an optional 220-470 Ω series resistor (protection).
5. Never power the microcontroller from the servo supply through its 5 V pin AND via USB at the same time unless the board is designed for it (backfeed risk).

Wiring - Uno with one SG90 under light load (testing only):

| Servo  | Uno           |
|--------|---------------|
| Brown  | GND           |
| Red    | 5 V           |
| Orange | D9            |

Wiring - Uno/ESP32 with an external supply (recommended):

| Servo  | Connect to                                    |
|--------|-----------------------------------------------|
| Brown  | External supply GND AND board GND (common)    |
| Red    | External supply +5 V (4.8-6 V)                |
| Orange | Board GPIO (Uno D9, ESP32 GPIO 18, etc.)      |

```
 5 V supply (+) ------------------------- servo red
 5 V supply (-) ----+---------------------- servo brown
                    +---- board GND
 board GPIO ------[220R]------------------- servo orange
 (470-1000 uF capacitor across supply + and -, close to the servo)
```

Symptoms of bad power: the board resets when the servo moves, the LCD flickers or goes
blank, the servo buzzes/jitters/twitches, or the servo gets hot.

## 4. Arduino Uno: `Servo` library (built in)

```cpp
#include <Servo.h>

constexpr uint8_t SERVO_PIN = 9;
Servo servo;

void setup() {
  servo.attach(SERVO_PIN, 500, 2400);   // pin, min µs, max µs (optional args)
  servo.write(90);                       // center
}

void loop() {
  for (int a = 0; a <= 180; a += 1) { servo.write(a); delay(15); }
  for (int a = 180; a >= 0; a -= 1) { servo.write(a); delay(15); }
}
```

Key calls: `attach(pin[, min, max])`, `write(angle)`, `writeMicroseconds(us)`,
`read()` (last commanded angle, not measured), `attached()`, `detach()`.

Uno notes:
- The `Servo` library uses Timer1 -> disables `analogWrite` on pins 9 and 10 regardless
  of which pin the servo is on.
- It can drive up to 12 servos on an Uno, but power becomes the limit.
- Pins: any digital pin works.

## 5. ESP32: `ESP32Servo` library

The stock `Servo` library is not designed for ESP32. Install "ESP32Servo" (Kevin Harrington / John K. Bennett) from Library Manager.

```cpp
#include <ESP32Servo.h>

constexpr int SERVO_PIN = 18;
Servo servo;

void setup() {
  ESP32PWM::allocateTimer(0);           // optional but recommended when using several
  servo.setPeriodHertz(50);             // standard 50 Hz
  servo.attach(SERVO_PIN, 500, 2400);   // µs range
  servo.write(90);
}

void loop() {
  for (int a = 0; a <= 180; a++) { servo.write(a); delay(10); }
  for (int a = 180; a >= 0; a--) { servo.write(a); delay(10); }
}
```

Pins: use output-capable GPIOs (not 34/35/36/39). Avoid strapping pins. Powering: external
5 V supply + common ground (the ESP32's USB 5 V can sag and trigger brownouts).

## 6. Smooth and non-blocking motion

`delay()`-based sweeps freeze everything else (sensor reads, serial commands, LCD updates).
Use `millis()`:

```cpp
#include <Servo.h>
Servo servo;
int target = 90, current = 90;
unsigned long lastStep = 0;
constexpr unsigned long STEP_MS = 15;     // lower = faster
constexpr int STEP_DEG = 1;

void moveTo(int deg) { target = constrain(deg, 0, 180); }

void updateServo() {
  if (millis() - lastStep < STEP_MS || current == target) return;
  lastStep = millis();
  current += (target > current) ? STEP_DEG : -STEP_DEG;
  servo.write(current);
}

void setup() { servo.attach(9); servo.write(current); }
void loop()  { updateServo(); /* other work... */ }
```

Easing (accelerate/decelerate): vary the step size using a smoothing factor, e.g.
`current += (target - current) * 0.1f;` (keep a float position).

Speed estimate: an SG90 turns about 60 degrees in 0.1-0.12 s at 4.8-6 V (no load). Moving
faster than the servo can follow gives no benefit.

## 7. Continuous-rotation servos

These servos give speed and direction rather than angle: about 1500 µs = stop, below =
one direction, above = the other direction; distance from 1500 sets speed.

```cpp
servo.writeMicroseconds(1500);   // stop (trim the screw on the servo if it creeps)
servo.writeMicroseconds(1700);   // forward
servo.writeMicroseconds(1300);   // reverse
```

`write(90)` stops, `write(0)` and `write(180)` are full speed each way.
No position feedback: they cannot be told "go to 45 degrees".

## 8. Many servos: PCA9685 (16 channels, I2C)

Use when you need more than a few servos or want to offload timing:
- Library: "Adafruit PWM Servo Driver Library".
- I2C address default `0x40`; chain with address jumpers.
- Power: V+ terminal takes servo power (5-6 V external), VCC takes logic power (3.3-5 V). Common ground.
- Frequency 50 Hz; pulse values are 12-bit counts out of 4096 per period.

```cpp
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
Adafruit_PWMServoDriver pwm(0x40);

constexpr uint16_t SERVOMIN = 150;   // about 0.7 ms at 50 Hz (calibrate)
constexpr uint16_t SERVOMAX = 600;   // about 2.9 ms (calibrate)

uint16_t angleToTicks(int a) { return map(a, 0, 180, SERVOMIN, SERVOMAX); }

void setup() {
  pwm.begin();
  pwm.setPWMFreq(50);
  pwm.setPWM(0, 0, angleToTicks(90));    // channel 0 to 90 degrees
}
void loop() {}
```

Alternative: `pwm.writeMicroseconds(channel, us)` (available in newer library versions).

## 9. Control from Python

Define a simple line protocol, e.g. `S,<angle>\n` to set the servo:

Arduino side (excerpt):

```cpp
// reads "S,90\n"
void handleCommand(char *line) {
  if (line[0] == 'S' && line[1] == ',') {
    int angle = atoi(line + 2);
    moveTo(angle);                      // from the non-blocking code above
    Serial.print(F("OK,")); Serial.println(constrain(angle, 0, 180));
  } else {
    Serial.println(F("ERR,unknown"));
  }
}
```

Python side:

```python
import serial, time
with serial.Serial("COM3", 115200, timeout=1) as ser:   # "/dev/ttyUSB0" on Linux
    time.sleep(2)                       # Uno resets when the port opens
    for angle in (0, 90, 180, 90):
        ser.write(f"S,{angle}\n".encode())
        print(ser.readline().decode().strip())
        time.sleep(1)
```

Full serial command parser and Python helpers: `python-serial.md`.
Or use Firmata (`pyfirmata2`) to set servo pins from Python without custom firmware.

## 10. Calibration, limits, jitter

- Find real end points: command 1000 µs and 2000 µs, then widen gradually. Stop when the
  servo hits its mechanical stop and hums - do not hold it there (stall current heats and
  strips gears). Set software limits with `constrain()`.
- Attach only when needed and `detach()` when idle if you do not need holding torque:
  removes jitter and saves power. (Position can drift under load when detached.)
- Jitter causes: noisy supply, no common ground, long thin signal wires, PWM timer conflicts
  from other libraries, and `analogWrite` on shared timers.
- Always `write()` an initial angle immediately after `attach()` to avoid a violent jump
  to a random position on power-up.
- Mount horns at 90 degrees (center) so the working range sits in the middle.

## 11. Troubleshooting

| Symptom                                    | Cause and fix                                                      |
|--------------------------------------------|--------------------------------------------------------------------|
| Servo twitches or buzzes without moving    | Underpowered, no common ground, or commanded beyond mechanical limit |
| Board resets when servo starts             | Brownout: separate supply, bulk capacitor                          |
| Servo does nothing                         | Wrong signal pin, no 5 V on red, `attach()` missing, ground not shared |
| Moves only to extremes                     | Wrong min/max µs or code uses microseconds in `write()`             |
| Gets hot, whines when holding              | Stalled against a stop or heavy load; reduce range/load, use a stronger servo |
| Jitters at rest                            | Noisy supply, add capacitors; `detach()` when idle                  |
| ESP32 compile error with `Servo.h`         | Use `ESP32Servo.h`                                                  |
| LCD garbage when servo moves               | Electrical noise/sag: separate supplies, ferrite or cap, shorter wires |
| `analogWrite` on pin 9/10 stops working (Uno) | Servo library uses Timer1; use another PWM pin (3, 5, 6, 11)     |
