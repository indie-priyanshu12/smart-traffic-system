# LCD Display Reference (HD44780 16x2 / 20x4, LiquidCrystal)

## Contents
1. What it is
2. Option A: parallel wiring with `LiquidCrystal` (Uno)
3. Option B: I2C backpack with `LiquidCrystal_I2C` (Uno and ESP32)
4. Finding the I2C address
5. API cheat sheet
6. Custom characters
7. Formatting, flicker-free updates, scrolling
8. ESP32-specific notes (3.3 V vs 5 V)
9. Menus and multi-screen UI pattern
10. Alternatives (OLED)
11. Troubleshooting

---

## 1. What it is

Character LCDs based on the HD44780 controller: 16 columns x 2 rows (1602), 20x4 (2004),
and others. Needs 5 V supply for logic and backlight on most modules. Displays ASCII plus
a small set of extra characters, and 8 user-defined characters.

Two ways to connect:
- **Parallel (4-bit mode)**: 6 signal pins + contrast pot + backlight. Library: `LiquidCrystal` (built into the Arduino IDE).
- **I2C backpack (PCF8574)**: 4 wires (VCC, GND, SDA, SCL). Library: `LiquidCrystal_I2C`.
  Strongly preferred: it saves pins and wiring errors.

## 2. Option A: parallel wiring (Uno)

16-pin LCD pinout and connections:

| LCD pin | Name | Connect to                                         |
|---------|------|----------------------------------------------------|
| 1       | VSS  | GND                                                |
| 2       | VDD  | 5 V                                                |
| 3       | V0   | Middle pin of 10 kΩ pot (ends to 5 V and GND) - contrast |
| 4       | RS   | Uno D12                                            |
| 5       | RW   | GND (write only)                                   |
| 6       | E    | Uno D11                                            |
| 7-10    | D0-D3| Not connected (4-bit mode)                         |
| 11      | D4   | Uno D5                                             |
| 12      | D5   | Uno D4                                             |
| 13      | D6   | Uno D3                                             |
| 14      | D7   | Uno D2                                             |
| 15      | A    | 5 V through 220 Ω (backlight anode)                |
| 16      | K    | GND (backlight cathode)                            |

```cpp
#include <LiquidCrystal.h>

// LiquidCrystal(rs, enable, d4, d5, d6, d7)
LiquidCrystal lcd(12, 11, 5, 4, 3, 2);

void setup() {
  lcd.begin(16, 2);              // columns, rows
  lcd.print("Hello, IoT!");
  lcd.setCursor(0, 1);           // column 0, row 1 (second line)
  lcd.print("Uptime: ");
}

void loop() {
  lcd.setCursor(8, 1);
  lcd.print(millis() / 1000);
  lcd.print("s   ");              // trailing spaces erase leftovers
}
```

Parallel mode uses 6 Uno pins: the D2/D3 interrupt pins are consumed here; if you also
need interrupts or lots of PWM, choose the I2C backpack instead.

Contrast: turn the pot until text appears. A row of solid boxes on line 1 and nothing
on line 2 means the LCD is powered but not initialized (or contrast is too high).

## 3. Option B: I2C backpack

The backpack is a PCF8574 (or PCF8574A) soldered to the LCD pins, with a contrast
trimmer and a jumper for the backlight.

Wiring (Uno):

| Backpack | Uno |
|----------|-----|
| GND      | GND |
| VCC      | 5 V |
| SDA      | A4  |
| SCL      | A5  |

Wiring (ESP32): GND -> GND, VCC -> **5 V (VIN)**, SDA -> GPIO 21, SCL -> GPIO 22 (see section 8).

Library: "LiquidCrystal I2C" (Frank de Brabander, `LiquidCrystal_I2C.h`) via Library Manager.
Some boards need the "hd44780" library by Bill Perry instead (it auto-detects address and
pin mapping): `#include <hd44780.h>` and `#include <hd44780ioClass/hd44780_I2Cexp.h>`.

```cpp
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);    // address, columns, rows

void setup() {
  // ESP32 with custom pins: Wire.begin(21, 22);
  lcd.init();                 // some library forks use lcd.begin() instead
  lcd.backlight();            // lcd.noBacklight() to turn off
  lcd.setCursor(0, 0);
  lcd.print("I2C LCD ready");
}

void loop() {
  lcd.setCursor(0, 1);
  lcd.print(millis() / 1000);
  lcd.print(" s      ");
}
```

Compile error `'class LiquidCrystal_I2C' has no member named ...`: a different fork is
installed; check which methods exist (`init()` vs `begin()`), or install the one noted above.

## 4. Finding the I2C address

Common addresses: `0x27` (PCF8574) and `0x3F` (PCF8574A). Range can be 0x20-0x27 or 0x38-0x3F.
Solder jumpers A0/A1/A2 on the backpack change the address.

I2C scanner (works on Uno and ESP32):

```cpp
#include <Wire.h>

void setup() {
  Serial.begin(115200);
  Wire.begin();                       // ESP32 custom: Wire.begin(21, 22);
  Serial.println("Scanning...");
  int found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("Found device at 0x");
      Serial.println(addr, HEX);
      found++;
    }
  }
  if (!found) Serial.println("No I2C devices found - check wiring/pull-ups/power");
}
void loop() {}
```

## 5. API cheat sheet

| Method                              | Purpose                                          |
|-------------------------------------|--------------------------------------------------|
| `begin(cols, rows)` / `init()`      | Initialize                                       |
| `clear()`                           | Clear all, cursor to home (slow, causes flicker) |
| `home()`                            | Cursor to 0,0 without clearing                   |
| `setCursor(col, row)`               | Move cursor (0-based)                            |
| `print(x)` / `print(f, digits)`     | Print text/number                                |
| `write(byte)`                       | Write a raw character code (custom chars)        |
| `backlight()` / `noBacklight()`     | I2C backpack backlight                           |
| `display()` / `noDisplay()`         | Show/hide text without erasing                   |
| `cursor()` / `noCursor()`           | Underline cursor                                 |
| `blink()` / `noBlink()`             | Blinking block cursor                            |
| `scrollDisplayLeft()` / `Right()`   | Shift whole display                              |
| `autoscroll()` / `noAutoscroll()`   | Auto-shift on print                              |
| `createChar(slot, bytes)`           | Define custom char in slot 0-7                   |

Row addressing: 16x2 rows 0 and 1. 20x4 rows are interleaved internally, but
`setCursor(col,row)` handles it when you pass the correct size to the constructor.

## 6. Custom characters

Each character is 5 columns x 8 rows, stored as 8 bytes (low 5 bits used). Eight slots (0-7).

```cpp
byte heart[8] = {
  0b00000, 0b01010, 0b11111, 0b11111,
  0b01110, 0b00100, 0b00000, 0b00000
};
byte degree[8] = {
  0b00110, 0b01001, 0b01001, 0b00110,
  0b00000, 0b00000, 0b00000, 0b00000
};

void setup() {
  lcd.init(); lcd.backlight();
  lcd.createChar(0, heart);          // must be called after init
  lcd.createChar(1, degree);
  lcd.setCursor(0, 0);
  lcd.write(byte(0));                // use write(byte(n)), not print(0)
  lcd.print(" 23.5");
  lcd.write(byte(1));
  lcd.print("C");
}
```

Tip: bar-graph characters (1..5 filled columns) let you draw a horizontal gauge using
one character per cell with five levels each.

## 7. Formatting, flicker-free updates, scrolling

Avoid `lcd.clear()` in a loop: it is slow and flickers. Instead overwrite fixed fields
and pad with spaces.

Helper to print a padded line:

```cpp
void printLine(uint8_t row, const char *text, uint8_t cols = 16) {
  lcd.setCursor(0, row);
  uint8_t i = 0;
  for (; i < cols && text[i]; i++) lcd.print(text[i]);
  for (; i < cols; i++) lcd.print(' ');       // erase remainder
}
```

Floats on AVR (no `%f` in `snprintf`):

```cpp
char num[8], line[17];
dtostrf(distanceCm, 5, 1, num);                       // " 23.4"
snprintf(line, sizeof line, "Dist:%s cm", num);
printLine(0, line);
```

On ESP32 `snprintf(line, sizeof line, "Dist:%5.1f cm", distanceCm);` works directly.

Update only when the value changes (or every 200-500 ms): the display is slow, and
rapid rewriting can make text look smeared.

Scrolling text longer than 16 chars: print a moving 16-character window of the
string, advancing by one character every 300 ms (non-blocking with `millis()`),
rather than using `scrollDisplayLeft()` (which shifts the whole 40-column memory).

Show values with units and fixed widths so the layout does not jump:
`"T:%2d.%dC H:%2d%%"`.

## 8. ESP32-specific notes (3.3 V vs 5 V)

- The LCD logic and backlight need about 5 V. Power the backpack from the ESP32 **VIN/5V** pin (USB 5 V).
- Most PCF8574 backpacks have 4.7 kΩ-10 kΩ pull-ups on SDA/SCL to the backpack's VCC. With
  VCC = 5 V, that puts 5 V on the ESP32's SDA/SCL lines through the pull-ups. In practice it
  often works but exceeds ESP32 ratings. Safer options:
  1. Use a bidirectional I2C level shifter between the ESP32 and the backpack, or
  2. Remove/desolder the backpack pull-up resistors and use 3.3 V pull-ups on the ESP32 side, or
  3. Power the backpack from 3.3 V (display will be dim/low contrast but often readable; PCF8574 is happy at 3.3 V).
- Use an OLED (SSD1306, 3.3 V native) if level shifting is unwanted.
- Initialize `Wire.begin(21, 22)` explicitly if using non-default pins.

## 9. Menus and multi-screen UI pattern

For simple UIs: one function per screen, a `currentScreen` variable, a button to cycle.

```cpp
enum Screen { SCREEN_DISTANCE, SCREEN_SERVO, SCREEN_STATUS, SCREEN_COUNT };
Screen current = SCREEN_DISTANCE;
unsigned long lastDraw = 0;

void drawScreen() {
  switch (current) {
    case SCREEN_DISTANCE: /* printLine(0, ...); printLine(1, ...); */ break;
    case SCREEN_SERVO:    break;
    case SCREEN_STATUS:   break;
    default: break;
  }
}

void loop() {
  // on button press: current = (Screen)((current + 1) % SCREEN_COUNT); lcd.clear();
  if (millis() - lastDraw >= 250) { lastDraw = millis(); drawScreen(); }
}
```

Call `lcd.clear()` only when switching screens, not every refresh.

## 10. Alternatives

- **SSD1306 OLED 128x64 (I2C, 0x3C/0x3D)**: 3.3 V-friendly, graphics and fonts, libraries
  `Adafruit_SSD1306` + `Adafruit_GFX` or `U8g2`. Better for ESP32.
- **TFT/ST7735/ILI9341 (SPI)**: color graphics, `TFT_eSPI` (ESP32) or Adafruit libs.
- **7-segment (TM1637)**: numbers only, 2 pins.

## 11. Troubleshooting

| Symptom                                           | Cause and fix                                                          |
|---------------------------------------------------|------------------------------------------------------------------------|
| Backlight on, blank screen or full-blocks on top row | Contrast pot (backpack trimmer or V0 pot) not adjusted; init not run |
| Nothing at all, backlight off                      | No power, backlight jumper removed, `backlight()` not called          |
| I2C scanner finds nothing                          | Wrong SDA/SCL, no common ground, bad solder joints, cable too long    |
| Scanner shows `0x3F`, code uses `0x27`             | Update the address in the constructor                                 |
| Garbled or random characters                       | Bad wiring (parallel mode), loose breadboard, noisy supply, wrong rows/cols in constructor |
| Text only on every other character / double spaced | Wrong column count in constructor (e.g. 20x4 declared as 16x2)        |
| LCD blanks when a servo/motor moves                | Power sag: separate servo supply, 470-1000 µF cap, common ground      |
| Old text remains after update                      | Pad with spaces (`"12   "`) or use `printLine()`                      |
| Custom char shows as a strange symbol              | `createChar` before `init`, or used `print(0)` instead of `write(byte(0))` |
| Display flickers                                   | Calling `clear()` repeatedly; update only on change                    |
| Compile error: `LiquidCrystal_I2C.h` not found     | Install library via Library Manager; check the exact name              |
| ESP32: display works but ESP32 acts unstable        | 5 V pull-ups on I2C lines; use level shifter or 3.3 V pull-ups        |
