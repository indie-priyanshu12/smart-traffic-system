// =============================================================================
// Smart Traffic Roadside Display & Hospital Entrance Gate Controller
// Target Board: Arduino Uno (ATmega328P, 5V Logic)
// Features:
//   - 16x2 LCD Display (I2C Backpack PCF8574 at 0x27 or 0x3F on A4/A5)
//   - HC-SR04 Ultrasonic Sensor (Trig D7, Echo D6) for Hospital Entrance
//   - SG90/MG90S Servo Motor (D9 PWM) for Hospital Automatic Door / Boom Barrier
//   - Piezo Buzzer (D8) for Emergency Siren & Gate Opening Alert
//   - SoftwareSerial (Pin 2 RX, Pin 3 TX) from ESP32 UART2 (GPIO 17 TX)
//   - Hardware USB Serial (115200) for PC/Laptop direct control & debugging
// =============================================================================

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>
#include <SoftwareSerial.h>

// -----------------------------------------------------------------------------
// Pin Definitions
// -----------------------------------------------------------------------------
constexpr uint8_t PIN_SW_RX       = 2;  // SoftwareSerial RX (Connects to ESP32 GPIO 17 TX)
constexpr uint8_t PIN_SW_TX       = 3;  // SoftwareSerial TX (Not used, or with voltage divider to ESP32 RX)
constexpr uint8_t PIN_US_ECHO     = 6;  // HC-SR04 Echo (5V logic on Uno is safe)
constexpr uint8_t PIN_US_TRIG     = 7;  // HC-SR04 Trig
constexpr uint8_t PIN_BUZZER      = 8;  // Active/Passive Buzzer (+)
constexpr uint8_t PIN_SERVO       = 9;  // SG90 Servo PWM signal

// -----------------------------------------------------------------------------
// Parameters & Thresholds
// -----------------------------------------------------------------------------
constexpr unsigned int  DISTANCE_THRESHOLD_CM = 15;   // Trigger gate when vehicle is closer than 15 cm
constexpr unsigned long GATE_HOLD_DURATION_MS = 5000; // Keep gate open for 5 seconds
constexpr unsigned long ULTRASONIC_INTERVAL   = 100;  // Read distance every 100ms
constexpr unsigned long LCD_UPDATE_INTERVAL   = 250;  // Refresh LCD display every 250ms

// -----------------------------------------------------------------------------
// Hardware Instances
// -----------------------------------------------------------------------------
// Note: If display is blank, change 0x27 to 0x3F or adjust contrast trimmer on back
LiquidCrystal_I2C lcd(0x27, 16, 2);
Servo gateServo;
SoftwareSerial espSerial(PIN_SW_RX, PIN_SW_TX);

// -----------------------------------------------------------------------------
// System State Variables
// -----------------------------------------------------------------------------
enum GateState {
  GATE_CLOSED,
  GATE_OPENING,
  GATE_OPEN,
  GATE_CLOSING
};

GateState currentGateState = GATE_CLOSED;
int currentServoAngle = 0; // 0 deg = closed, 90 deg = open

char activeEmergencyRoad = '-'; // 'A', 'B', 'C', or '-' (None)
bool isEmergency = false;

unsigned long lastUltrasonicRead = 0;
unsigned long lastLcdUpdate = 0;
unsigned long gateOpenedTime = 0;
unsigned long buzzerLastToggle = 0;
bool buzzerState = false;

long measuredDistanceCm = 999;
char serialBuffer[64];
uint8_t bufferIdx = 0;

// -----------------------------------------------------------------------------
// Ultrasonic Reading Helper (Safe with 30ms timeout)
// -----------------------------------------------------------------------------
long readUltrasonicDistance() {
  digitalWrite(PIN_US_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_US_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_US_TRIG, LOW);

  // pulseIn with 30000us timeout (~5m max range) prevents blocking
  unsigned long duration = pulseIn(PIN_US_ECHO, HIGH, 30000UL);
  if (duration == 0) {
    return 999; // Out of range or no echo
  }
  return duration * 0.0343 / 2.0;
}

// -----------------------------------------------------------------------------
// Command Parser (handles both ESP32 JSON / text and PC Serial)
// Format examples: "EMERGENCY:A", "NORMAL", "GATE:OPEN", "GATE:CLOSE"
// -----------------------------------------------------------------------------
void parseCommand(const char* cmd) {
  Serial.print(F("[CMD] Received: "));
  Serial.println(cmd);

  if (strstr(cmd, "EMERGENCY") != nullptr || strstr(cmd, "\"event\":\"EMERGENCY\"") != nullptr) {
    isEmergency = true;
    if (strstr(cmd, "road\":\"A\"") || strstr(cmd, ":A")) activeEmergencyRoad = 'A';
    else if (strstr(cmd, "road\":\"B\"") || strstr(cmd, ":B")) activeEmergencyRoad = 'B';
    else if (strstr(cmd, "road\":\"C\"") || strstr(cmd, ":C")) activeEmergencyRoad = 'C';
    else activeEmergencyRoad = 'A';

    // Alarm double-beep
    tone(PIN_BUZZER, 2400, 150);
  } 
  else if (strstr(cmd, "NORMAL") != nullptr || strstr(cmd, "\"event\":\"NORMAL\"") != nullptr) {
    isEmergency = false;
    activeEmergencyRoad = '-';
    noTone(PIN_BUZZER);
  }
  else if (strstr(cmd, "GATE:OPEN") != nullptr) {
    openGate();
  }
  else if (strstr(cmd, "GATE:CLOSE") != nullptr) {
    closeGate();
  }
}

// -----------------------------------------------------------------------------
// Servo Gate Control
// -----------------------------------------------------------------------------
void openGate() {
  if (currentGateState != GATE_OPEN && currentGateState != GATE_OPENING) {
    Serial.println(F("[GATE] Opening Hospital Entrance Barrier..."));
    currentGateState = GATE_OPEN;
    currentServoAngle = 90;
    gateServo.write(currentServoAngle);
    gateOpenedTime = millis();
    tone(PIN_BUZZER, 1800, 200); // Beep confirmation
  }
}

void closeGate() {
  if (currentGateState != GATE_CLOSED) {
    Serial.println(F("[GATE] Closing Hospital Entrance Barrier..."));
    currentGateState = GATE_CLOSED;
    currentServoAngle = 0;
    gateServo.write(currentServoAngle);
    noTone(PIN_BUZZER);
  }
}

// -----------------------------------------------------------------------------
// LCD Display Update (Clean, formatted 16x2 output)
// -----------------------------------------------------------------------------
void updateLcd() {
  lcd.setCursor(0, 0);
  if (isEmergency) {
    lcd.print(F("EMERGENCY! RD:"));
    lcd.print(activeEmergencyRoad);
    lcd.print(F(" "));
  } else {
    lcd.print(F("TRAFFIC: NORMAL "));
  }

  lcd.setCursor(0, 1);
  if (currentGateState == GATE_OPEN) {
    lcd.print(F("GATE: OPEN "));
  } else {
    lcd.print(F("GATE: CLS "));
  }

  if (measuredDistanceCm < 100) {
    lcd.print(measuredDistanceCm);
    lcd.print(F("cm  "));
  } else {
    lcd.print(F(">1m  "));
  }
}

// -----------------------------------------------------------------------------
// Setup
// -----------------------------------------------------------------------------
void setup() {
  // Initialize Serial Ports
  Serial.begin(115200);
  espSerial.begin(9600);

  Serial.println(F("\n=============================================="));
  Serial.println(F("  Smart Traffic Roadside & Hospital Gate Unit"));
  Serial.println(F("=============================================="));

  // Initialize Pins
  pinMode(PIN_US_TRIG, OUTPUT);
  pinMode(PIN_US_ECHO, INPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);

  // Initialize Servo
  gateServo.attach(PIN_SERVO);
  gateServo.write(0); // Start closed

  // Initialize LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(F("SMART TRAFFIC"));
  lcd.setCursor(0, 1);
  lcd.print(F("HOSPITAL GATE OK"));
  delay(1200);
  lcd.clear();

  // Test beep
  tone(PIN_BUZZER, 2000, 100);
  Serial.println(F("[SYSTEM] Roadside Unit Ready."));
}

// -----------------------------------------------------------------------------
// Main Loop
// -----------------------------------------------------------------------------
void loop() {
  unsigned long now = millis();

  // 1. Process Hardware USB Serial input from Laptop
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (bufferIdx > 0) {
        serialBuffer[bufferIdx] = '\0';
        parseCommand(serialBuffer);
        bufferIdx = 0;
      }
    } else if (bufferIdx < sizeof(serialBuffer) - 1) {
      serialBuffer[bufferIdx++] = c;
    }
  }

  // 2. Process SoftwareSerial input from ESP32
  while (espSerial.available() > 0) {
    char c = espSerial.read();
    if (c == '\n' || c == '\r') {
      if (bufferIdx > 0) {
        serialBuffer[bufferIdx] = '\0';
        parseCommand(serialBuffer);
        bufferIdx = 0;
      }
    } else if (bufferIdx < sizeof(serialBuffer) - 1) {
      serialBuffer[bufferIdx++] = c;
    }
  }

  // 3. Periodic Ultrasonic Distance Sensor Reading
  if (now - lastUltrasonicRead >= ULTRASONIC_INTERVAL) {
    lastUltrasonicRead = now;
    measuredDistanceCm = readUltrasonicDistance();

    // Check if vehicle is detected at hospital gate
    if (measuredDistanceCm <= DISTANCE_THRESHOLD_CM && measuredDistanceCm > 0) {
      openGate();
      gateOpenedTime = now; // Reset hold countdown while vehicle is present
    }
  }

  // 4. Automatic Gate Timeout Handling
  if (currentGateState == GATE_OPEN) {
    // Pulsing buzzer warning while gate is open
    if (now - buzzerLastToggle >= 200) {
      buzzerLastToggle = now;
      buzzerState = !buzzerState;
      if (buzzerState) tone(PIN_BUZZER, 1200);
      else noTone(PIN_BUZZER);
    }

    // Auto-close gate after vehicle has cleared and timeout elapsed
    if (now - gateOpenedTime >= GATE_HOLD_DURATION_MS) {
      if (measuredDistanceCm > DISTANCE_THRESHOLD_CM) {
        closeGate();
      } else {
        // Vehicle still blocking sensor, hold open longer
        gateOpenedTime = now;
      }
    }
  }

  // 5. Periodic LCD Display Refresh
  if (now - lastLcdUpdate >= LCD_UPDATE_INTERVAL) {
    lastLcdUpdate = now;
    updateLcd();
  }
}
