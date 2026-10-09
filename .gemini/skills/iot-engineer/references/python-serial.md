# Python <-> Microcontroller over USB Serial

## Contents
1. When to use serial
2. Setup and finding the port
3. Minimal read/write
4. Designing the line protocol (CSV, JSON, commands)
5. Robust reader class (reconnect, threading)
6. Parsing and validation
7. Logging to CSV / SQLite
8. Live plotting with matplotlib
9. Firmata (control without writing firmware)
10. Framing for binary data
11. Raspberry Pi notes
12. Troubleshooting

---

## 1. When to use serial

Use USB serial when the board is plugged into the computer: simplest, lowest latency, no network
configuration. For several devices, remote nodes, or dashboards use MQTT instead
(`python-network-mqtt-http-ble.md`).

Install: `pip install pyserial` (import name is `serial`; do NOT install the unrelated package named `serial`).

## 2. Setup and finding the port

| OS      | Port name examples                                              |
|---------|-----------------------------------------------------------------|
| Windows | `COM3`, `COM4` (Device Manager > Ports)                         |
| Linux   | `/dev/ttyUSB0` (CH340/CP210x), `/dev/ttyACM0` (Uno R3 16U2, native USB boards) |
| macOS   | `/dev/cu.usbserial-*`, `/dev/cu.usbmodem*` (use `cu.`, not `tty.`) |

Linux permissions: `sudo usermod -aG dialout $USER` then log out and back in.
Only one program can hold a port: close the Arduino Serial Monitor/Plotter before running Python.

Auto-detect:

```python
import serial.tools.list_ports

def list_ports():
    for p in serial.tools.list_ports.comports():
        print(p.device, "|", p.description, "|", p.hwid)

def find_port(hints=("Arduino", "CH340", "CP210", "USB Serial", "USB-SERIAL", "ESP32")):
    for p in serial.tools.list_ports.comports():
        text = f"{p.description} {p.manufacturer or ''}"
        if any(h.lower() in text.lower() for h in hints):
            return p.device
    return None
```

Command line check: `python -m serial.tools.list_ports`; interactive terminal:
`python -m serial.tools.miniterm COM3 115200`.

## 3. Minimal read/write

```python
import time
import serial

with serial.Serial("COM3", 115200, timeout=1) as ser:
    time.sleep(2)                       # Uno/Nano reset on open (DTR); wait for boot
    ser.reset_input_buffer()            # drop boot messages
    ser.write(b"PING\n")
    reply = ser.readline().decode("utf-8", errors="replace").strip()
    print(reply)
```

Key facts:
- `readline()` returns when it sees `\n` or when `timeout` expires (returns partial/empty bytes).
  Always check for empty results.
- Write `bytes`: `"text".encode()`. Terminate commands with `\n`.
- Baud rate must match `Serial.begin()` in firmware exactly.
- Uno/Nano reset when the port opens. ESP32 boards may also reset (DTR/RTS). To avoid resets set
  `ser.dtr = False` before opening via `serial.Serial()` + `ser.port = ...; ser.open()`, or
  just wait for boot.
- For ESP32 boot ROM messages at 74880 baud you will see garbage at start; normal.

## 4. Designing the line protocol

Rules that prevent most integration bugs:
1. One message per line, terminated by `\n`.
2. Same units and field order on both sides; document them in a comment at the top of both files.
3. Machine data separate from human debug (prefix debug lines with `#`).
4. Mark invalid values explicitly (`nan` or empty field), never `0`.
5. Acknowledge commands (`OK,...` / `ERR,...`) so Python can detect problems.

**CSV telemetry** (compact, easy to parse):

```
# millis,distance_cm,angle
12034,23.4,90
```

**JSON lines** (self-describing, flexible; costs more RAM/time on Uno):

```cpp
// ArduinoJson v7
#include <ArduinoJson.h>
JsonDocument doc;
doc["t"] = millis();
doc["d"] = distanceCm;
doc["a"] = angle;
serializeJson(doc, Serial);
Serial.println();
```
Python: `json.loads(line)`.

For a tiny Uno sketch hand-format JSON with `Serial.print` to save memory:

```cpp
Serial.print(F("{\"d\":")); Serial.print(d, 1);
Serial.print(F(",\"a\":")); Serial.print(angle);
Serial.println('}');
```

**Commands PC -> board**: `VERB[,arg1,arg2]\n`, e.g. `S,90`, `LED,1`, `GET`, `CFG,thr,25`.

Non-blocking command reader for firmware (works on Uno and ESP32):

```cpp
constexpr size_t BUF_LEN = 48;
char buf[BUF_LEN];
size_t idx = 0;

void pollSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      buf[idx] = '\0';
      if (idx > 0) handleCommand(buf);
      idx = 0;
    } else if (idx < BUF_LEN - 1) {
      buf[idx++] = c;
    } else {
      idx = 0;                      // overflow: drop the line
    }
  }
}
```

## 5. Robust reader class

Handles reconnect, parsing, and background reading with a thread and a queue.

```python
import queue, threading, time
from typing import Optional
import serial

class SerialDevice:
    def __init__(self, port: str, baud: int = 115200, boot_delay: float = 2.0):
        self.port, self.baud, self.boot_delay = port, baud, boot_delay
        self.ser: Optional[serial.Serial] = None
        self.rx: "queue.Queue[str]" = queue.Queue(maxsize=1000)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def connect(self) -> None:
        self.ser = serial.Serial(self.port, self.baud, timeout=0.5, write_timeout=1)
        time.sleep(self.boot_delay)
        self.ser.reset_input_buffer()

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self) -> None:
        while not self._stop.is_set():
            try:
                if self.ser is None or not self.ser.is_open:
                    self.connect()
                raw = self.ser.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if line and not line.startswith("#"):
                    try:
                        self.rx.put_nowait(line)
                    except queue.Full:
                        _ = self.rx.get_nowait()          # drop the oldest
                        self.rx.put_nowait(line)
            except (serial.SerialException, OSError):
                if self.ser:
                    try: self.ser.close()
                    except Exception: pass
                time.sleep(1.0)                            # wait, then reconnect

    def send(self, text: str) -> None:
        if self.ser and self.ser.is_open:
            self.ser.write((text.strip() + "\n").encode())

    def close(self) -> None:
        self._stop.set()
        if self._thread: self._thread.join(timeout=2)
        if self.ser and self.ser.is_open: self.ser.close()

if __name__ == "__main__":
    dev = SerialDevice("COM3")
    dev.connect(); dev.start()
    try:
        while True:
            try:
                print(dev.rx.get(timeout=1))
            except queue.Empty:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        dev.close()
```

Async alternative: `pyserial-asyncio` (or `serial_asyncio_fast`) for asyncio apps.

## 6. Parsing and validation

```python
import math
from dataclasses import dataclass
from typing import Optional

@dataclass
class Reading:
    t_ms: int
    distance_cm: Optional[float]
    angle: int

def parse_reading(line: str) -> Optional[Reading]:
    parts = line.split(",")
    if len(parts) != 3:
        return None
    try:
        t = int(parts[0])
        d = float(parts[1])
        a = int(parts[2])
    except ValueError:
        return None
    if math.isnan(d) or not (2.0 <= d <= 400.0):
        d = None
    return Reading(t, d, a)
```

Reject lines with the wrong field count, non-numeric values, or out-of-range values. Serial
data can arrive truncated at connect time; never assume every line is well-formed.

Timestamps: use the PC clock (`time.time()`/`datetime.now()`) when logging, since the
board's `millis()` resets on each boot.

## 7. Logging

CSV:

```python
import csv, time
from datetime import datetime

with open("log.csv", "a", newline="") as f:
    w = csv.writer(f)
    if f.tell() == 0:
        w.writerow(["timestamp", "distance_cm", "angle"])
    # inside the read loop:
    w.writerow([datetime.now().isoformat(timespec="milliseconds"), d, a])
    f.flush()
```

SQLite:

```python
import sqlite3
db = sqlite3.connect("sensors.db")
db.execute("CREATE TABLE IF NOT EXISTS readings(ts TEXT, distance_cm REAL, angle INTEGER)")
db.execute("INSERT INTO readings VALUES (?,?,?)", (datetime.now().isoformat(), d, a))
db.commit()
```

For time-series dashboards: InfluxDB + Grafana, or MQTT -> Node-RED -> storage (see
`python-network-mqtt-http-ble.md`).

## 8. Live plotting

```python
import collections, time
import matplotlib.pyplot as plt

xs = collections.deque(maxlen=200)
ys = collections.deque(maxlen=200)
plt.ion()
fig, ax = plt.subplots()
(line,) = ax.plot([], [])
ax.set_xlabel("time (s)"); ax.set_ylabel("distance (cm)"); ax.set_ylim(0, 200)
t0 = time.time()

# inside the read loop, after a valid reading d:
xs.append(time.time() - t0); ys.append(d)
line.set_data(xs, ys)
ax.set_xlim(max(0, xs[0]), xs[-1] + 1)
plt.pause(0.001)
```

Alternatives: `pyqtgraph` (fast), `dash`/`streamlit` (web dashboards), `pandas` for analysis.
Polar radar plot for the servo + ultrasonic scanner: `project-examples.md`.

## 9. Firmata (control without writing firmware)

Firmata is a protocol that lets Python read/write pins directly.

1. Arduino IDE: File > Examples > Firmata > **StandardFirmata** > upload to the Uno.
2. Install `pip install pyfirmata2` (maintained fork of `pyfirmata`).

```python
from pyfirmata2 import Arduino, util
import time

board = Arduino(Arduino.AUTODETECT)       # or "COM3"
board.samplingOn(100)                     # sampling interval ms

led = board.get_pin("d:13:o")             # digital pin 13 output
pot = board.get_pin("a:0:i")              # analog 0 input
servo = board.get_pin("d:9:s")            # servo on pin 9

def on_pot(value):                        # value in 0.0-1.0, or None
    if value is not None:
        servo.write(int(value * 180))
pot.register_callback(on_pot)
pot.enable_reporting()

for _ in range(10):
    led.write(1); time.sleep(0.5)
    led.write(0); time.sleep(0.5)
board.exit()
```

Pin spec: `"<d|a>:<pin>:<i|o|p|s>"` (input, output, PWM, servo).

Trade-offs: quick prototypes and teaching, but no on-board logic (loop latency depends on the
PC), limited to what Firmata supports, and libraries such as LCD I2C or ultrasonic timing are
not directly available (use custom firmware for those). Firmata does not suit ESP32 over Wi-Fi.

## 10. Binary framing (advanced)

For high-rate or compact data use fixed structs with a header and checksum:

Firmware:
```cpp
struct __attribute__((packed)) Packet {
  uint8_t  header = 0xAA;
  uint16_t distance_mm;
  uint8_t  angle;
  uint8_t  crc;
};
```
Python: `struct.unpack("<BHBB", data)`; verify the header and checksum, resynchronize by
scanning for `0xAA`. Text lines are easier to debug; use binary only when needed.

## 11. Raspberry Pi notes

- Pi with USB-connected Arduino/ESP32: same pyserial code (`/dev/ttyACM0`/`/dev/ttyUSB0`).
- Pi hardware UART: `/dev/serial0`; enable UART in `raspi-config`; 3.3 V logic (do not connect 5 V TX directly).
- The Pi can run the MQTT broker (Mosquitto) as the central hub for ESP32 nodes.

## 12. Troubleshooting

| Symptom                                           | Cause and fix                                                      |
|---------------------------------------------------|--------------------------------------------------------------------|
| `PermissionError(13)` / `could not open port`     | Port in use by Serial Monitor/another script; Linux `dialout` group |
| `FileNotFoundError` for COM port                  | Wrong port name; unplug/replug and list ports                      |
| First lines are garbage or missing                | Board reset on open; `sleep(2)` + `reset_input_buffer()`           |
| Garbage characters all the time                   | Baud mismatch                                                      |
| `UnicodeDecodeError`                              | Decode with `errors="replace"` / `"ignore"`                        |
| Script hangs on `readline()`                      | No `timeout` set; board not sending; wrong port                    |
| Data arrives in bursts / delayed                  | Firmware blocking with `delay()`; board buffer full; slow plotting in the read thread |
| Python gets old data after being idle             | Input buffer holds stale lines; `reset_input_buffer()` before reading |
| Works in Arduino Serial Monitor but not in Python | Python needs `\n`-terminated commands and the correct line ending expectations |
| Random resets when Python opens the port          | DTR reset behavior; use a capacitor on RESET (Uno) or `dtr=False` |
