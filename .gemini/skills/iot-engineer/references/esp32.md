# ESP32 Reference

## Contents
1. Hardware summary and variants
2. Setup in Arduino IDE / PlatformIO
3. GPIO rules (what is safe to use)
4. Digital, ADC, DAC, PWM (LEDC)
5. Wi-Fi station mode with reconnect
6. Web server
7. Bluetooth / BLE
8. FreeRTOS tasks and dual core
9. Persistent storage (NVS, SPIFFS/LittleFS)
10. Deep sleep and power
11. OTA updates
12. Interrupts and touch
13. Troubleshooting

---

## 1. Hardware summary and variants

Classic ESP32 (ESP32-WROOM-32 DevKit):

| Item          | Value                                                       |
|---------------|-------------------------------------------------------------|
| CPU           | Xtensa LX6 dual-core, up to 240 MHz                         |
| Logic level   | 3.3 V (pins are NOT 5 V tolerant)                           |
| RAM           | about 520 KB SRAM                                           |
| Flash         | 4 MB typical (external SPI flash)                           |
| Radio         | Wi-Fi 802.11 b/g/n (2.4 GHz), Bluetooth Classic + BLE       |
| ADC           | 2 units, 12-bit (0-4095), 18 channels total                 |
| DAC           | 2 channels, 8-bit (GPIO 25, 26)                             |
| Other         | Touch sensing, hall sensor (old), RMT, I2S, CAN (TWAI), 2x I2C, 3x SPI, 3x UART |
| Supply        | USB 5 V (regulated to 3.3 V), or 3.3 V pin; Wi-Fi peaks at about 250-500 mA |

Variants (check the exact board's pinout before assigning pins):

| Chip      | Notes                                                                    |
|-----------|--------------------------------------------------------------------------|
| ESP32-S3  | Dual-core, Wi-Fi + BLE 5, native USB, more GPIO, AI instructions         |
| ESP32-S2  | Single-core, Wi-Fi only, native USB, no Bluetooth                        |
| ESP32-C3  | Single-core RISC-V, Wi-Fi + BLE 5, cheap, few pins                       |
| ESP32-C6  | RISC-V, Wi-Fi 6, BLE 5, Thread/Zigbee                                    |

## 2. Setup

Arduino IDE:
1. File > Preferences > Additional Boards Manager URLs, add:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
2. Boards Manager > install "esp32 by Espressif Systems".
3. Tools > Board > "ESP32 Dev Module" (or the exact board, e.g. "ESP32S3 Dev Module").
4. Select the port. Upload speed 921600 normally; use 115200 if uploads fail.

USB-serial chips: CP2102 or CH340 (drivers may be needed). S2/S3/C3/C6 boards often
have native USB (enable "USB CDC On Boot" if `Serial` output is missing).

PlatformIO:

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
lib_deps =
    knolleary/PubSubClient
    bblanchon/ArduinoJson
```

Core version note: Arduino-ESP32 core 3.x (based on ESP-IDF 5) changed some APIs
(notably LEDC PWM). Tell the user which core their code targets and give both forms
when it matters (see section 4).

## 3. GPIO rules

| GPIO               | Rule                                                                    |
|--------------------|-------------------------------------------------------------------------|
| 6-11               | Connected to the SPI flash. NEVER use.                                  |
| 34, 35, 36 (VP), 39 (VN) | Input-only. No output, no internal pull-up/down.                  |
| 0                  | Strapping: LOW at boot enters flash mode. Used by the BOOT button.      |
| 2                  | Strapping; on-board LED on many boards. Keep floating/low at boot.      |
| 12 (MTDI)          | Strapping: HIGH at boot selects 1.8 V flash -> boot failure on some modules. Avoid pull-ups. |
| 15 (MTDO)          | Strapping: affects boot log. Usually OK as output.                      |
| 5                  | Strapping (timing of SDIO); generally usable.                           |
| 1, 3               | UART0 TX/RX (USB console). Avoid unless Serial is unused.               |
| 25, 26             | DAC capable.                                                            |
| ADC2 pins (0,2,4,12-15,25-27) | `analogRead` does not work while Wi-Fi is on. Use ADC1.      |
| ADC1 pins (32-39)  | Safe with Wi-Fi.                                                        |

Safe general-purpose picks on a classic ESP32 DevKit:
4, 13, 14, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33
(plus 34/35/36/39 for input only).

Default buses: I2C SDA 21 / SCL 22; SPI (VSPI) MOSI 23 / MISO 19 / SCK 18 / SS 5;
UART2 RX 16 / TX 17. On ESP32 almost any GPIO can be remapped for I2C, SPI, UART, and PWM:

```cpp
Wire.begin(SDA_PIN, SCL_PIN);          // custom I2C pins
Serial2.begin(9600, SERIAL_8N1, 16, 17);   // RX=16, TX=17
```

Logic level: every GPIO is 3.3 V. For 5 V signals use a divider (e.g. 1 kΩ top / 2 kΩ
bottom) or a bidirectional level shifter. Details in `electronics-power-wiring.md`.

## 4. Digital, ADC, DAC, PWM

Digital: same API as Arduino (`pinMode`, `digitalWrite`, `digitalRead`, `INPUT_PULLUP`).

ADC:

```cpp
int raw = analogRead(34);                   // 0-4095
uint32_t mv = analogReadMilliVolts(34);     // calibrated millivolts (preferred)
analogSetPinAttenuation(34, ADC_11db);      // about 0-3.1 V usable range
```

- The ESP32 ADC is non-linear near the ends and noisy; average 16 samples and use
  `analogReadMilliVolts()` for better accuracy. Inputs above about 3.1 V saturate; never exceed 3.3 V.
- Use ADC1 pins if Wi-Fi is on.

DAC (classic ESP32/S2): `dacWrite(25, 128);` gives about 1.65 V (8-bit).

PWM (LEDC) - core 3.x:

```cpp
const int PIN = 4, FREQ = 5000, RES = 8;    // 8-bit: duty 0-255
void setup() { ledcAttach(PIN, FREQ, RES); }
void loop()  { ledcWrite(PIN, 128); }
```

PWM (LEDC) - core 2.x:

```cpp
const int PIN = 4, CH = 0, FREQ = 5000, RES = 8;
void setup() { ledcSetup(CH, FREQ, RES); ledcAttachPin(PIN, CH); }
void loop()  { ledcWrite(CH, 128); }
```

`analogWrite()` also exists in core 3.x. For servos, use the `ESP32Servo` library
(see `servo-motor.md`), which handles the 50 Hz timing.

## 5. Wi-Fi station mode with reconnect

`secrets.h` (never commit; add to `.gitignore`):

```cpp
#pragma once
#define WIFI_SSID "your-ssid"
#define WIFI_PASS "your-password"
```

```cpp
#include <WiFi.h>
#include "secrets.h"

void connectWiFi(uint32_t timeoutMs = 15000) {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < timeoutMs) {
    delay(250);
    Serial.print('.');
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nIP: %s  RSSI: %d dBm\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
  } else {
    Serial.println("\nWi-Fi failed; will retry");
  }
}

void setup() { Serial.begin(115200); connectWiFi(); }

void loop() {
  connectWiFi();      // cheap when already connected
  // ... non-blocking work
}
```

Notes:
- ESP32 supports 2.4 GHz only. A 5 GHz-only SSID will never connect.
- Use `WiFi.mode(WIFI_STA)` explicitly to avoid the default AP+STA behavior.
- For provisioning without hardcoded credentials, use the `WiFiManager` library
  (captive portal) or BLE provisioning.
- HTTPS: `WiFiClientSecure` with `client.setCACert(rootCA)` (preferred) or
  `client.setInsecure()` for quick tests only (no certificate validation).
- Time: `configTime(0, 0, "pool.ntp.org");` then `getLocalTime(&tm)`.

## 6. Web server

```cpp
#include <WiFi.h>
#include <WebServer.h>
WebServer server(80);

void handleRoot()  { server.send(200, "text/plain", "ESP32 online"); }
void handleData()  {
  char json[64];
  snprintf(json, sizeof json, "{\"uptime_s\":%lu}", millis() / 1000);
  server.send(200, "application/json", json);
}
void setup() {
  // ... connectWiFi();
  server.on("/", handleRoot);
  server.on("/api/data", HTTP_GET, handleData);
  server.begin();
}
void loop() { server.handleClient(); }     // keep loop() non-blocking
```

For async serving or WebSockets, use `ESPAsyncWebServer` (community library) or the
newer `ESP32 WebServer` features; for REST + JSON + Python clients see
`python-network-mqtt-http-ble.md`.

## 7. Bluetooth / BLE

- Classic ESP32 supports Bluetooth Classic (`BluetoothSerial`, SPP) and BLE.
  S2 has no Bluetooth; S3/C3/C6 have BLE only.
- BLE concepts: a peripheral advertises; a GATT server exposes Services containing
  Characteristics (read/write/notify). Use 128-bit UUIDs for custom services.
- Use the `NimBLE-Arduino` library for lower RAM use than the stock BLE library.
- BLE and Wi-Fi share one radio; running both reduces throughput and can cause
  instability. Prefer one at a time for low-power nodes.
- Python side: `bleak` (see `python-network-mqtt-http-ble.md`).

## 8. FreeRTOS tasks and dual core

Arduino `loop()` runs as a task on core 1. Create extra tasks for slow or blocking jobs:

```cpp
void sensorTask(void *param) {
  for (;;) {
    // read sensor
    vTaskDelay(pdMS_TO_TICKS(100));      // yield; never busy-wait
  }
}
void setup() {
  xTaskCreatePinnedToCore(sensorTask, "sensor", 4096, nullptr, 1, nullptr, 0);
}
```

Pass data between tasks with queues (`xQueueCreate`, `xQueueSend`, `xQueueReceive`)
or protect shared variables with a mutex/critical section. Wi-Fi and BLE stacks run on
core 0 by default. Feed the watchdog: long loops without `vTaskDelay`/`delay` can trigger
a task watchdog reset.

## 9. Persistent storage

Preferences (NVS key-value, survives reboot and re-flash of the sketch):

```cpp
#include <Preferences.h>
Preferences prefs;
prefs.begin("cfg", false);                 // namespace, read-write
int th = prefs.getInt("threshold", 30);    // default 30
prefs.putInt("threshold", 25);
prefs.end();
```

Files: use LittleFS (`#include <LittleFS.h>`; `LittleFS.begin(true)`). SPIFFS is deprecated.
Upload data folders with the IDE plugin or PlatformIO `uploadfs`.
For data that must survive deep sleep only (not power loss): `RTC_DATA_ATTR int bootCount;`

## 10. Deep sleep and power

```cpp
RTC_DATA_ATTR int bootCount = 0;

void setup() {
  Serial.begin(115200);
  bootCount++;
  // read sensor, send data...
  esp_sleep_enable_timer_wakeup(60ULL * 1000000ULL);   // 60 s in microseconds
  esp_deep_sleep_start();                              // never returns; wakes into setup()
}
void loop() {}
```

- Wake sources: timer, external GPIO (`esp_sleep_enable_ext0_wakeup` for RTC GPIOs),
  touch, ULP.
- Deep-sleep current is about 10 µA on the chip, but dev boards waste mA on USB chip and LED;
  for battery projects use a bare module/low-quiescent board.
- Wi-Fi connect time dominates energy: keep connection fast (static IP, saved channel/BSSID).
- Brownout: `Brownout detector was triggered` means the supply sagged during a Wi-Fi
  burst. Use a better cable/supply and a 100-470 µF capacitor near the module.
- Light sleep keeps RAM and wakes faster; deep sleep restarts the program.

## 11. OTA updates

```cpp
#include <ArduinoOTA.h>
void setup() {
  // connectWiFi();
  ArduinoOTA.setHostname("esp32-node1");
  ArduinoOTA.setPassword("change-me");
  ArduinoOTA.begin();
}
void loop() { ArduinoOTA.handle(); }
```

Pick a partition scheme with OTA ("Default 4MB with spiffs" includes two app slots).
Always set a password. A failed OTA can be recovered over USB.

## 12. Interrupts and touch

```cpp
volatile uint32_t count = 0;
void IRAM_ATTR isr() { count++; }          // IRAM_ATTR required for ISRs on ESP32
void setup() {
  pinMode(27, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(27), isr, FALLING);
}
```

Any GPIO that supports input can be an interrupt source. Keep ISRs tiny; use
`portENTER_CRITICAL_ISR` or atomic types for shared multi-word data.
Touch pins (T0-T9 on GPIO 4, 0, 2, 15, 13, 12, 14, 27, 33, 32): `touchRead(T0)` returns
lower values when touched.

## 13. Troubleshooting

| Symptom / message                                                | Cause and fix                                                      |
|------------------------------------------------------------------|--------------------------------------------------------------------|
| `Failed to connect to ESP32: Wrong boot mode detected` / `Timed out waiting for packet header` | Hold BOOT while "Connecting..." appears; check cable/driver; lower upload speed; disconnect GPIO 0/2/12 circuitry |
| `Brownout detector was triggered`                                 | Weak USB port or cable; add capacitor; separate servo supply       |
| `Guru Meditation Error: Core 1 panic'ed (LoadProhibited)`        | Null pointer / bad memory access; decode the backtrace; check arrays and objects |
| Boot loop with `rst:0x10 (RTCWDT_RTC_RESET)` or flash errors     | Used GPIO 6-11, or strapping pin held wrong at boot                |
| `analogRead` returns 0 or constant while Wi-Fi is on             | Pin is on ADC2; move to ADC1 (GPIO 32-39)                          |
| Wi-Fi never connects                                             | 5 GHz network, wrong password, weak signal, hidden SSID, router MAC filter |
| Random resets under Wi-Fi load                                   | Power supply; watchdog from blocking code                          |
| Nothing printed on S3/C3 native USB                              | Enable "USB CDC On Boot"; open the correct port                    |
| I2C device not found                                             | Wrong SDA/SCL pins, missing pull-ups, device powered at wrong voltage |
| Servo jitters on ESP32                                           | Use `ESP32Servo`, separate 5 V supply, common ground               |
