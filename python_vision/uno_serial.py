"""
Arduino Uno Serial Communication Module.
Transmits roadside display commands and emergency gate events over USB Serial.
"""

import time

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

class ArduinoSerial:
    def __init__(self, port: str = "COM3", baud_rate: int = 115200):
        self.port = port
        self.baud_rate = baud_rate
        self.ser = None
        self.is_connected = False
        self.connect()

    def connect(self) -> bool:
        """Attempt to connect to Arduino Uno over Serial."""
        if not HAS_SERIAL:
            return False
        now = time.time()
        if hasattr(self, "_last_attempt_time") and (now - self._last_attempt_time < 5.0):
            return False
        self._last_attempt_time = now
        try:
            # Check available ports
            available = [p.device for p in serial.tools.list_ports.comports()]
            if self.port not in available and available:
                # Auto-select first available port if configured port isn't found
                self.port = available[0]

            self.ser = serial.Serial(self.port, self.baud_rate, timeout=1.0)
            time.sleep(2.0) # Uno resets on DTR, wait for bootloader
            self.is_connected = True
            print(f"[UNO-SERIAL] Connected to Arduino Uno on {self.port} @ {self.baud_rate} baud")
            return True
        except Exception as e:
            self.is_connected = False
            # Silently tolerate if not plugged in
            return False

    def send_emergency(self, road: str):
        """Send emergency trigger to Uno."""
        if not self.is_connected and not self.connect():
            return
        try:
            cmd = f"EMERGENCY:{road}\n"
            self.ser.write(cmd.encode("utf-8"))
            self.ser.flush()
        except Exception:
            self.is_connected = False

    def send_normal(self):
        """Send normal cycle command to Uno."""
        if not self.is_connected and not self.connect():
            return
        try:
            cmd = "NORMAL\n"
            self.ser.write(cmd.encode("utf-8"))
            self.ser.flush()
        except Exception:
            self.is_connected = False

    def send_gate_open(self):
        """Manually trigger hospital gate open."""
        if not self.is_connected and not self.connect():
            return
        try:
            self.ser.write(b"GATE:OPEN\n")
            self.ser.flush()
        except Exception:
            self.is_connected = False

    def close(self):
        """Cleanly close serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.is_connected = False
