# Arduino Uno Reference

## Contents
1. Hardware summary
2. Pin map and special functions
3. Digital I/O
4. Analog input and PWM output
5. Serial communication
6. Interrupts
7. Timers and timing
8. Memory management
9. EEPROM
10. Power
11. Toolchain and uploading
12. Starter sketches
13. Common errors

---

## 1. Hardware summary

| Item            | Value                                                         |
|-----------------|---------------------------------------------------------------|
| MCU             | ATmega328P (8-bit AVR), 16 MHz                                |
| Logic level     | 5 V                                                           |
| Flash           | 32 KB (about 0.5 KB used by bootloader)                       |
| SRAM            | 2 KB                                                          |
| EEPROM          | 1 KB (about 100,000 write cycles per cell)                    |
| Digital pins    | 14 (D0-D13)                                                   |
| PWM pins        | 6 (D3, D5, D6, D9, D10, D11)                                  |
| Analog inputs   | 6 (A0-A5), 10-bit ADC, default reference = 5 V                |
| USB chip        | ATmega16U2 (official) or CH340 (most clones)                  |
| Radio           | None (add ESP-01, HC-05, nRF24L01, etc.)                      |
| Supply          | USB 5 V, barrel jack 7-12 V (recommended), Vin pin 7-12 V     |
| 3.3 V pin       | Max about 50 mA                                               |
| Pin current     | 20 mA recommended, 40 mA absolute max; about 200 mA total     |

## 2. Pin map and special functions

| Pin        | Special function                                            |
|------------|-------------------------------------------------------------|
| D0 (RX)    | Hardware serial RX - shared with USB; keep free for uploads |
| D1 (TX)    | Hardware serial TX - shared with USB                        |
| D2, D3     | External interrupts INT0, INT1                              |
| D3,5,6,9,10,11 | PWM                                                     |
| D10-D13    | SPI: SS, MOSI, MISO, SCK                                    |
| D13        | Built-in LED (also SCK)                                     |
| A4, A5     | I2C SDA, SCL (also on dedicated header pins near AREF)      |
| A0-A5      | Can be used as digital pins 14-19                           |
| AREF       | External analog reference                                   |
| RESET      | Pull low to reset                                           |

Pin planning rules:
- Keep D0/D1 free if the sketch uses `Serial` (USB) or if uploading must work reliably.
- Put I2C devices on A4/A5; do not use those pins for other things.
- Keep D2/D3 for interrupts (e.g. a flow sensor, rotary encoder, ultrasonic echo timing).
- Count PWM needs early; there are only six PWM pins.

## 3. Digital I/O

```cpp
pinMode(pin, OUTPUT);          // drive
pinMode(pin, INPUT);           // high impedance (needs external pull-up/down)
pinMode(pin, INPUT_PULLUP);    // internal ~20-50 kΩ pull-up (button to GND)
digitalWrite(pin, HIGH);       // 5 V
int v = digitalRead(pin);
```

Button wiring (recommended): one leg to pin, other to GND, use `INPUT_PULLUP`. Pressed
reads `LOW`. This removes the need for an external resistor.

Do not leave an `INPUT` pin floating; it will read noise.

## 4. Analog input and PWM output

```cpp
int raw = analogRead(A0);              // 0-1023  -> 0-5 V by default
float volts = raw * (5.0 / 1023.0);
analogWrite(9, 128);                   // PWM, 0-255 (about 50% duty)
```

- PWM frequency: about 490 Hz on pins 3, 9, 10, 11; about 980 Hz on pins 5 and 6.
- `analogWrite` is PWM, not a true analog voltage. Filter it (RC) if you need a DC level.
- ADC takes about 100 µs per read; resolution about 4.9 mV/step at 5 V.
- Noisy readings: average 8-16 samples, add a 0.1 µF capacitor at the input, keep wires short.
- `analogReference(INTERNAL)` selects a 1.1 V reference for more resolution on small signals.
  Do not apply more than the reference voltage to the pin.
- Timer conflicts: the `Servo` library takes Timer1 and disables PWM on pins 9 and 10.
  `tone()` uses Timer2 and disables PWM on pins 3 and 11.

## 5. Serial communication

```cpp
void setup() {
  Serial.begin(115200);          // must match Serial Monitor and Python
}
void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');   // OK for short commands
    line.trim();
  }
  Serial.println(F("hello"));
}
```

- Opening the serial port from a PC (Serial Monitor or pyserial) toggles DTR and
  RESETS the Uno. Wait about 2 seconds before sending the first command.
- `Serial.print(x, 2)` prints a float with 2 decimals.
- `Serial.readStringUntil` blocks until timeout (default 1000 ms). Use
  `Serial.setTimeout(50)` or a non-blocking reader (see `firmware-patterns.md`).
- Only one hardware UART. Use `SoftwareSerial` (pins of choice, up to about 9600-57600 baud
  reliably) for a second device such as a GPS or Bluetooth module. It conflicts with
  some libraries that use the same timers.
- 115200 baud is reliable for USB; high rates over `SoftwareSerial` are not.

## 6. Interrupts

```cpp
volatile unsigned long pulses = 0;     // volatile: modified in ISR

void onPulse() {                       // ISR: keep it very short
  pulses++;                            // no delay(), no Serial.print here
}

void setup() {
  pinMode(2, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(2), onPulse, FALLING);
}

void loop() {
  noInterrupts();                      // copy multi-byte shared data atomically
  unsigned long p = pulses;
  interrupts();
  // use p
}
```

Modes: `RISING`, `FALLING`, `CHANGE`, `LOW`. Pin-change interrupts on other pins need a
library (e.g. `PinChangeInterrupt` / `EnableInterrupt`).

Rules: ISRs must be short; use `volatile`; no `delay()`; `millis()` does not advance
inside an ISR; protect multi-byte reads with `noInterrupts()/interrupts()`.

## 7. Timers and timing

| Timer  | Bits | Used by                                          |
|--------|------|--------------------------------------------------|
| Timer0 | 8    | `millis()`, `micros()`, `delay()`, PWM on 5, 6   |
| Timer1 | 16   | `Servo` library, PWM on 9, 10; `TimerOne` lib    |
| Timer2 | 8    | `tone()`, PWM on 3, 11                           |

- `millis()` overflows after about 49.7 days; always compare with subtraction
  (`now - last >= interval`), which stays correct across overflow.
- `delayMicroseconds()` is accurate for 3 µs and up; `delay()` blocks everything.
- `micros()` resolution is 4 µs on 16 MHz AVR.

## 8. Memory management (2 KB SRAM)

- Constant strings live in SRAM unless wrapped: `Serial.println(F("text"));`
- Large constant tables: `const int table[] PROGMEM = {...};` read with `pgm_read_word`.
- Avoid `String` in long-running sketches (fragmentation). Prefer `char buf[32]` and `snprintf`.
- No `snprintf` with `%f` on AVR by default; use `dtostrf(value, width, decimals, buf)`.
- Check free RAM when behavior is odd (random resets, garbled text): large arrays, many
  strings, and deep recursion are typical causes. The IDE reports static usage after compile.

```cpp
char buf[8];
dtostrf(distanceCm, 5, 1, buf);   // " 23.4"
```

## 9. EEPROM

```cpp
#include <EEPROM.h>
struct Config { uint16_t thresholdCm; uint8_t mode; };
Config cfg;
EEPROM.get(0, cfg);               // read
EEPROM.put(0, cfg);               // write only if changed (put does this check)
```

Limit writes (about 100k per cell). Never write in a fast loop; write on change, and
rate-limit. Validate stored data (e.g. a magic byte) because a fresh chip reads 0xFF.

## 10. Power

- USB: up to about 500 mA for the board and everything attached.
- Barrel jack 7-12 V feeds the on-board regulator (heat above 9-12 V with loads).
- Powering the 5 V pin directly with a regulated 5 V supply bypasses the regulator
  and the protection diode - fine if the supply is clean and correct, dangerous if not.
- Servos, motors, relays, long LED strips: external supply, common ground
  (see `electronics-power-wiring.md`).
- Brown-outs show up as random resets; add bulk capacitance near loads.

## 11. Toolchain and uploading

- Arduino IDE 2.x: Tools > Board > Arduino Uno; Tools > Port > the COM/tty port.
- Clone boards with CH340: install the CH340 driver on Windows/macOS if no port appears.
- Linux: add the user to `dialout` (`sudo usermod -aG dialout $USER`, then re-login).
- PlatformIO (VS Code): `board = uno`, `framework = arduino`, `monitor_speed = 115200`.
- CLI: `arduino-cli compile --fqbn arduino:avr:uno Sketch` and
  `arduino-cli upload -p /dev/ttyUSB0 --fqbn arduino:avr:uno Sketch`.
- Disconnect anything wired to D0/D1 during upload.

## 12. Starter sketches

Blink without `delay()`:

```cpp
constexpr uint8_t LED_PIN = LED_BUILTIN;
unsigned long lastToggle = 0;
bool ledState = false;

void setup() { pinMode(LED_PIN, OUTPUT); }

void loop() {
  if (millis() - lastToggle >= 500) {
    lastToggle = millis();
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState);
  }
}
```

Button toggles LED (with debounce):

```cpp
constexpr uint8_t BTN = 2, LED = 8;
bool ledOn = false, lastStable = HIGH, lastRead = HIGH;
unsigned long lastChange = 0;

void setup() { pinMode(BTN, INPUT_PULLUP); pinMode(LED, OUTPUT); }

void loop() {
  bool r = digitalRead(BTN);
  if (r != lastRead) { lastChange = millis(); lastRead = r; }
  if (millis() - lastChange > 30 && r != lastStable) {
    lastStable = r;
    if (r == LOW) { ledOn = !ledOn; digitalWrite(LED, ledOn); }
  }
}
```

Potentiometer to PWM LED:

```cpp
void setup() { pinMode(9, OUTPUT); }
void loop() { analogWrite(9, analogRead(A0) / 4); }   // 0-1023 -> 0-255
```

## 13. Common errors

| Symptom / message                                      | Likely cause and fix                                          |
|--------------------------------------------------------|---------------------------------------------------------------|
| `avrdude: stk500_getsync(): not in sync: resp=0x00`    | Wrong port/board, no driver, wires on D0/D1, bad cable        |
| `avrdude: ser_open(): can't open device`               | Port busy (Serial Monitor/Python open) or no permission       |
| Sketch uploads but nothing happens                     | Wrong pin numbers, missing `pinMode`, power problem           |
| Random resets when a motor/servo moves                 | Supply sag; separate supply plus capacitor                    |
| Garbage characters in Serial Monitor                   | Baud mismatch                                                 |
| `Low memory available, stability problems may occur`   | SRAM near full: `F()`, drop `String`, shrink buffers          |
| `analogWrite` has no effect on a pin                   | Pin lacks PWM, or Servo/tone took the timer                   |
| Readings jump on A-pins                                | Floating input, no reference, or noisy supply: average, cap   |
