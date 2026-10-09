// =============================================================================
// Smart Traffic Management System for Emergency Vehicles
// Target Board: ESP32 Dev Module (ESP32-WROOM-32)
// Logic Level: 3.3V
// Features: 
//   - 3-Way Traffic Light System (Road A, Road B, Road C)
//   - 9 LEDs total (3 Red, 3 Yellow, 3 Green) with 220 Ohm current-limiting resistors
//   - WiFi HTTP REST API Server for Python Vision / Laptop commands
//   - Non-blocking millis() state machine with realistic 2-second Yellow transition
//   - UART2 Serial output to Arduino Uno (Roadside LCD + Hospital Gate)
// =============================================================================

#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// -----------------------------------------------------------------------------
// WiFi Credentials (Replace with your local Wi-Fi or Hotspot credentials)
// -----------------------------------------------------------------------------
const char* WIFI_SSID = "peabuddy";
const char* WIFI_PASS = "12345678";

// -----------------------------------------------------------------------------
// I2C 16x2 LCD Display (Safe ESP32 GPIOs: SDA=4, SCL=5)
// -----------------------------------------------------------------------------
constexpr uint8_t PIN_I2C_SDA = 4;
constexpr uint8_t PIN_I2C_SCL = 5;
LiquidCrystal_I2C lcd(0x27, 16, 2); // Default address 0x27 (use 0x3F if 0x27 is blank)
bool lcdAvailable = false;

// -----------------------------------------------------------------------------
// Pin Configuration (Safe ESP32 GPIOs)
// -----------------------------------------------------------------------------
// Road A (e.g., Northbound)
constexpr uint8_t PIN_ROAD_A_RED    = 18;
constexpr uint8_t PIN_ROAD_A_YELLOW = 19;
constexpr uint8_t PIN_ROAD_A_GREEN  = 21;

// Road B (e.g., Eastbound)
constexpr uint8_t PIN_ROAD_B_RED    = 22;
constexpr uint8_t PIN_ROAD_B_YELLOW = 23;
constexpr uint8_t PIN_ROAD_B_GREEN  = 25;

// Road C (e.g., Westbound)
constexpr uint8_t PIN_ROAD_C_RED    = 26;
constexpr uint8_t PIN_ROAD_C_YELLOW = 27;
constexpr uint8_t PIN_ROAD_C_GREEN  = 32;

// UART2 TX Pin to Arduino Uno RX
constexpr uint8_t PIN_UART2_TX      = 17;
constexpr uint8_t PIN_UART2_RX      = 16; // Not strictly used if unidirectional

// -----------------------------------------------------------------------------
// Timing Constants (milliseconds)
// -----------------------------------------------------------------------------
constexpr unsigned long NORMAL_GREEN_DURATION  = 8000; // 8 seconds green in normal cycle
constexpr unsigned long YELLOW_DELAY_DURATION  = 2000; // 2 seconds yellow light (as required)
constexpr unsigned long EMERGENCY_HOLD_TIMEOUT = 5000; // Revert to normal if no heartbeat for 5s

// -----------------------------------------------------------------------------
// State Machine Definitions
// -----------------------------------------------------------------------------
enum RoadIndex {
  ROAD_A = 0,
  ROAD_B = 1,
  ROAD_C = 2,
  ROAD_NONE = -1
};

enum LightColor {
  LIGHT_RED,
  LIGHT_YELLOW,
  LIGHT_GREEN
};

enum SystemMode {
  MODE_NORMAL_GREEN,
  MODE_NORMAL_YELLOW,
  MODE_EMERGENCY_TRANSITION_YELLOW,
  MODE_EMERGENCY_GREEN
};

// Global State
SystemMode currentMode = MODE_NORMAL_GREEN;
RoadIndex currentGreenRoad = ROAD_A;
RoadIndex targetEmergencyRoad = ROAD_NONE;
unsigned long stateStartTime = 0;
unsigned long lastEmergencyHeartbeat = 0;

// Web Server on port 80
WebServer server(80);

// -----------------------------------------------------------------------------
// Function Prototypes
// -----------------------------------------------------------------------------
void setRoadLights(RoadIndex road, LightColor color);
void updateTrafficLights(LightColor stateA, LightColor stateB, LightColor stateC);
void handleRoot();
void handleStatus();
void handleEmergency();
void handleReset();
void handleNotFound();
const char* roadIndexToString(RoadIndex r);

// -----------------------------------------------------------------------------
// Helper: Convert Road Index to String
// -----------------------------------------------------------------------------
const char* roadIndexToString(RoadIndex r) {
  switch (r) {
    case ROAD_A: return "A";
    case ROAD_B: return "B";
    case ROAD_C: return "C";
    default:     return "NONE";
  }
}

// -----------------------------------------------------------------------------
// Apply LED states for all 3 roads
// -----------------------------------------------------------------------------
void setLightOutputs(LightColor colA, LightColor colB, LightColor colC) {
  // Road A
  digitalWrite(PIN_ROAD_A_RED,    colA == LIGHT_RED    ? HIGH : LOW);
  digitalWrite(PIN_ROAD_A_YELLOW, colA == LIGHT_YELLOW ? HIGH : LOW);
  digitalWrite(PIN_ROAD_A_GREEN,  colA == LIGHT_GREEN  ? HIGH : LOW);

  // Road B
  digitalWrite(PIN_ROAD_B_RED,    colB == LIGHT_RED    ? HIGH : LOW);
  digitalWrite(PIN_ROAD_B_YELLOW, colB == LIGHT_YELLOW ? HIGH : LOW);
  digitalWrite(PIN_ROAD_B_GREEN,  colB == LIGHT_GREEN  ? HIGH : LOW);

  // Road C
  digitalWrite(PIN_ROAD_C_RED,    colC == LIGHT_RED    ? HIGH : LOW);
  digitalWrite(PIN_ROAD_C_YELLOW, colC == LIGHT_YELLOW ? HIGH : LOW);
  digitalWrite(PIN_ROAD_C_GREEN,  colC == LIGHT_GREEN  ? HIGH : LOW);
}

// -----------------------------------------------------------------------------
// I2C 16x2 LCD Display Helper Functions
// -----------------------------------------------------------------------------
void initLcd() {
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  Wire.beginTransmission(0x27);
  if (Wire.endTransmission() == 0) {
    lcd = LiquidCrystal_I2C(0x27, 16, 2);
    lcdAvailable = true;
    Serial.println("[LCD] Detected 16x2 LCD at I2C address 0x27");
  } else {
    Wire.beginTransmission(0x3F);
    if (Wire.endTransmission() == 0) {
      lcd = LiquidCrystal_I2C(0x3F, 16, 2);
      lcdAvailable = true;
      Serial.println("[LCD] Detected 16x2 LCD at I2C address 0x3F");
    } else {
      Serial.println("[LCD] Warning: No I2C LCD detected at 0x27 or 0x3F (Check wiring)");
    }
  }

  if (lcdAvailable) {
    lcd.init();
    lcd.backlight();
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("SMART TRAFFIC");
    lcd.setCursor(0, 1);
    lcd.print("CONTROLLER BOOT");
  }
}

void updateLcd(const char* line1, const char* line2) {
  if (!lcdAvailable) return;
  lcd.setCursor(0, 0);
  lcd.print("                ");
  lcd.setCursor(0, 0);
  lcd.print(line1);

  lcd.setCursor(0, 1);
  lcd.print("                ");
  lcd.setCursor(0, 1);
  lcd.print(line2);
}

// -----------------------------------------------------------------------------
// Send Serial Notification to Arduino Uno (Roadside Unit)
// -----------------------------------------------------------------------------
void notifyArduino(const char* eventType, RoadIndex road) {
  // Serial2 transmits to Arduino Uno SoftwareSerial pin
  Serial2.printf("{\"event\":\"%s\",\"road\":\"%s\"}\n", eventType, roadIndexToString(road));
  Serial.printf("[UNO-SYNC] Sent: event=%s, road=%s\n", eventType, roadIndexToString(road));
}

// -----------------------------------------------------------------------------
// REST API Handlers
// -----------------------------------------------------------------------------
void setupCors() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
}

void handleRoot() {
  setupCors();
  String html = "<!DOCTYPE html><html><head><title>ESP32 Traffic Signal</title></head>";
  html += "<body style='font-family:sans-serif;background:#121826;color:#eee;padding:2rem;'>";
  html += "<h1>Smart Traffic Controller - ESP32</h1>";
  html += "<p>Mode: <b>" + String(currentMode == MODE_EMERGENCY_GREEN ? "EMERGENCY OVERRIDE" : "NORMAL") + "</b></p>";
  html += "<p>Active Green Road: <b>Road " + String(roadIndexToString(currentGreenRoad)) + "</b></p>";
  html += "<p>API Endpoints: <code>/api/status</code>, <code>/api/emergency?road=A|B|C</code>, <code>/api/reset</code></p>";
  html += "</body></html>";
  server.send(200, "text/html", html);
}

void handleStatus() {
  setupCors();
  StaticJsonDocument<256> doc;
  
  doc["mode"] = (currentMode == MODE_EMERGENCY_GREEN) ? "EMERGENCY" :
                (currentMode == MODE_EMERGENCY_TRANSITION_YELLOW) ? "TRANSITION_YELLOW" : "NORMAL";
  doc["active_road"] = roadIndexToString(currentGreenRoad);
  doc["target_road"] = roadIndexToString(targetEmergencyRoad);
  doc["elapsed_ms"]  = millis() - stateStartTime;

  // Current light colors
  if (currentMode == MODE_NORMAL_GREEN || currentMode == MODE_EMERGENCY_GREEN) {
    doc["roadA"] = (currentGreenRoad == ROAD_A) ? "GREEN" : "RED";
    doc["roadB"] = (currentGreenRoad == ROAD_B) ? "GREEN" : "RED";
    doc["roadC"] = (currentGreenRoad == ROAD_C) ? "GREEN" : "RED";
  } else {
    // In yellow transition
    doc["roadA"] = (currentGreenRoad == ROAD_A) ? "YELLOW" : "RED";
    doc["roadB"] = (currentGreenRoad == ROAD_B) ? "YELLOW" : "RED";
    doc["roadC"] = (currentGreenRoad == ROAD_C) ? "YELLOW" : "RED";
  }

  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

void handleEmergency() {
  setupCors();
  if (!server.hasArg("road")) {
    server.send(400, "application/json", "{\"error\":\"Missing 'road' query parameter (A, B, or C)\"}");
    return;
  }

  String roadParam = server.arg("road");
  roadParam.toUpperCase();
  RoadIndex reqRoad = ROAD_NONE;

  if (roadParam == "A" || roadParam == "1") reqRoad = ROAD_A;
  else if (roadParam == "B" || roadParam == "2") reqRoad = ROAD_B;
  else if (roadParam == "C" || roadParam == "3") reqRoad = ROAD_C;
  else {
    server.send(400, "application/json", "{\"error\":\"Invalid road. Use A, B, or C\"}");
    return;
  }

  lastEmergencyHeartbeat = millis();

  // If already emergency green on this road, just refresh heartbeat
  if (currentMode == MODE_EMERGENCY_GREEN && currentGreenRoad == reqRoad) {
    server.send(200, "application/json", "{\"status\":\"Emergency active maintained\",\"road\":\"" + roadParam + "\"}");
    return;
  }

  // If already green on this road in normal mode, immediately upgrade to emergency lock
  if (currentMode == MODE_NORMAL_GREEN && currentGreenRoad == reqRoad) {
    currentMode = MODE_EMERGENCY_GREEN;
    stateStartTime = millis();
    notifyArduino("EMERGENCY", currentGreenRoad);
    char buf[17];
    snprintf(buf, sizeof(buf), "PRIORITY ROAD %s", roadParam.c_str());
    updateLcd("EMERGENCY LOCKED", buf);
    server.send(200, "application/json", "{\"status\":\"Immediate emergency green granted\",\"road\":\"" + roadParam + "\"}");
    return;
  }

  // Need transition: currently another road is green!
  // Trigger realistic 2-second Yellow transition for the currently green road
  targetEmergencyRoad = reqRoad;
  currentMode = MODE_EMERGENCY_TRANSITION_YELLOW;
  stateStartTime = millis();

  // Turn current green road to Yellow, others remain Red
  if (currentGreenRoad == ROAD_A) setLightOutputs(LIGHT_YELLOW, LIGHT_RED, LIGHT_RED);
  else if (currentGreenRoad == ROAD_B) setLightOutputs(LIGHT_RED, LIGHT_YELLOW, LIGHT_RED);
  else if (currentGreenRoad == ROAD_C) setLightOutputs(LIGHT_RED, LIGHT_RED, LIGHT_YELLOW);

  char buf[17];
  snprintf(buf, sizeof(buf), "RD %s -> RD %s (2s)", roadIndexToString(currentGreenRoad), roadParam.c_str());
  updateLcd("EMERGENCY ALERT!", buf);

  notifyArduino("TRANSITION", targetEmergencyRoad);
  Serial.printf("[TRAFFIC] Emergency transition initiated: Road %s -> 2s Yellow, then Road %s GREEN\n",
                roadIndexToString(currentGreenRoad), roadIndexToString(targetEmergencyRoad));

  server.send(200, "application/json", "{\"status\":\"Yellow transition started (2s)\",\"target\":\"" + roadParam + "\"}");
}

void handleReset() {
  setupCors();
  targetEmergencyRoad = ROAD_NONE;
  currentMode = MODE_NORMAL_GREEN;
  stateStartTime = millis();
  
  if (currentGreenRoad == ROAD_A) setLightOutputs(LIGHT_GREEN, LIGHT_RED, LIGHT_RED);
  else if (currentGreenRoad == ROAD_B) setLightOutputs(LIGHT_RED, LIGHT_GREEN, LIGHT_RED);
  else if (currentGreenRoad == ROAD_C) setLightOutputs(LIGHT_RED, LIGHT_RED, LIGHT_GREEN);

  char buf[17];
  snprintf(buf, sizeof(buf), "ROAD %s: GREEN", roadIndexToString(currentGreenRoad));
  updateLcd("TRAFFIC: NORMAL", buf);

  notifyArduino("NORMAL", currentGreenRoad);
  server.send(200, "application/json", "{\"status\":\"Reset to normal cycle\"}");
}

void handleNotFound() {
  setupCors();
  if (server.method() == HTTP_OPTIONS) {
    server.send(204);
    return;
  }
  server.send(404, "text/plain", "Not found");
}

// -----------------------------------------------------------------------------
// Setup
// -----------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, PIN_UART2_RX, PIN_UART2_TX);
  delay(100);

  Serial.println("\n=========================================");
  Serial.println("  Smart Traffic System - ESP32 Controller");
  Serial.println("=========================================");

  // Initialize GPIO Pins
  pinMode(PIN_ROAD_A_RED, OUTPUT);
  pinMode(PIN_ROAD_A_YELLOW, OUTPUT);
  pinMode(PIN_ROAD_A_GREEN, OUTPUT);

  pinMode(PIN_ROAD_B_RED, OUTPUT);
  pinMode(PIN_ROAD_B_YELLOW, OUTPUT);
  pinMode(PIN_ROAD_B_GREEN, OUTPUT);

  pinMode(PIN_ROAD_C_RED, OUTPUT);
  pinMode(PIN_ROAD_C_YELLOW, OUTPUT);
  pinMode(PIN_ROAD_C_GREEN, OUTPUT);

  // Initialize 16x2 I2C LCD on GPIO 4 (SDA) and GPIO 5 (SCL)
  initLcd();

  // Self-test LED sequence (150ms per color)
  setLightOutputs(LIGHT_RED, LIGHT_RED, LIGHT_RED);
  delay(300);
  setLightOutputs(LIGHT_YELLOW, LIGHT_YELLOW, LIGHT_YELLOW);
  delay(300);
  setLightOutputs(LIGHT_GREEN, LIGHT_GREEN, LIGHT_GREEN);
  delay(300);

  // Initial State: Road A Green, others Red
  currentGreenRoad = ROAD_A;
  currentMode = MODE_NORMAL_GREEN;
  stateStartTime = millis();
  setLightOutputs(LIGHT_GREEN, LIGHT_RED, LIGHT_RED);

  // Connect to Wi-Fi
  Serial.printf("[WIFI] Connecting to %s", WIFI_SSID);
  updateLcd("WIFI CONNECTING", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long wifiStart = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - wifiStart < 15000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WIFI] Connected successfully!");
    Serial.print("[WIFI] ESP32 IP Address: ");
    Serial.println(WiFi.localIP());

    char ipBuf[17];
    snprintf(ipBuf, sizeof(ipBuf), "%s", WiFi.localIP().toString().c_str());
    updateLcd("WIFI CONNECTED!", ipBuf);
    delay(1500);
  } else {
    Serial.println("\n[WIFI] WARNING: Could not connect to Wi-Fi. Operating in Standalone mode.");
    Serial.println("[WIFI] Setting up Access Point 'ESP32-Traffic-System'...");
    WiFi.softAP("ESP32-Traffic-System", "emergency123");
    Serial.print("[WIFI] AP IP: ");
    Serial.println(WiFi.softAPIP());
    updateLcd("AP:ESP32-Traffic", "IP:192.168.4.1");
    delay(1500);
  }

  // Display initial normal road
  updateLcd("TRAFFIC: NORMAL", "ROAD A: GREEN");

  // Configure REST API Routes
  server.on("/", HTTP_GET, handleRoot);
  server.on("/api/status", HTTP_GET, handleStatus);
  server.on("/api/emergency", HTTP_POST, handleEmergency);
  server.on("/api/emergency", HTTP_GET, handleEmergency); // Support GET for quick browser testing
  server.on("/api/reset", HTTP_POST, handleReset);
  server.on("/api/reset", HTTP_GET, handleReset);
  server.onNotFound(handleNotFound);

  server.begin();
  Serial.println("[HTTP] REST API Server started.");
  notifyArduino("NORMAL", currentGreenRoad);
}

// -----------------------------------------------------------------------------
// Non-Blocking State Machine in loop()
// -----------------------------------------------------------------------------
void loop() {
  server.handleClient();
  unsigned long now = millis();

  switch (currentMode) {
    // -------------------------------------------------------------------------
    // 1. Normal Mode: Active Road is Green
    // -------------------------------------------------------------------------
    case MODE_NORMAL_GREEN:
      if (now - stateStartTime >= NORMAL_GREEN_DURATION) {
        // Time to transition this road to Yellow for 2 seconds
        currentMode = MODE_NORMAL_YELLOW;
        stateStartTime = now;

        if (currentGreenRoad == ROAD_A) setLightOutputs(LIGHT_YELLOW, LIGHT_RED, LIGHT_RED);
        else if (currentGreenRoad == ROAD_B) setLightOutputs(LIGHT_RED, LIGHT_YELLOW, LIGHT_RED);
        else if (currentGreenRoad == ROAD_C) setLightOutputs(LIGHT_RED, LIGHT_RED, LIGHT_YELLOW);

        char buf[17];
        snprintf(buf, sizeof(buf), "ROAD %s: 2s YEL", roadIndexToString(currentGreenRoad));
        updateLcd("TRAFFIC: NORMAL", buf);

        Serial.printf("[TRAFFIC] Road %s -> 2s Yellow before next phase\n", roadIndexToString(currentGreenRoad));
      }
      break;

    // -------------------------------------------------------------------------
    // 2. Normal Mode: Active Road is Yellow (2-second delay)
    // -------------------------------------------------------------------------
    case MODE_NORMAL_YELLOW:
      if (now - stateStartTime >= YELLOW_DELAY_DURATION) {
        // Move to the next road in round-robin: A -> B -> C -> A
        if (currentGreenRoad == ROAD_A) currentGreenRoad = ROAD_B;
        else if (currentGreenRoad == ROAD_B) currentGreenRoad = ROAD_C;
        else currentGreenRoad = ROAD_A;

        currentMode = MODE_NORMAL_GREEN;
        stateStartTime = now;

        if (currentGreenRoad == ROAD_A) setLightOutputs(LIGHT_GREEN, LIGHT_RED, LIGHT_RED);
        else if (currentGreenRoad == ROAD_B) setLightOutputs(LIGHT_RED, LIGHT_GREEN, LIGHT_RED);
        else if (currentGreenRoad == ROAD_C) setLightOutputs(LIGHT_RED, LIGHT_RED, LIGHT_GREEN);

        char buf[17];
        snprintf(buf, sizeof(buf), "ROAD %s: GREEN", roadIndexToString(currentGreenRoad));
        updateLcd("TRAFFIC: NORMAL", buf);

        Serial.printf("[TRAFFIC] Road %s is now GREEN\n", roadIndexToString(currentGreenRoad));
        notifyArduino("NORMAL", currentGreenRoad);
      }
      break;

    // -------------------------------------------------------------------------
    // 3. Emergency Preemption: 2-second Yellow transition on old road
    // -------------------------------------------------------------------------
    case MODE_EMERGENCY_TRANSITION_YELLOW:
      if (now - stateStartTime >= YELLOW_DELAY_DURATION) {
        // 2-second yellow delay has completed!
        // Make the Target Emergency Road GREEN, all others RED!
        currentGreenRoad = targetEmergencyRoad;
        currentMode = MODE_EMERGENCY_GREEN;
        stateStartTime = now;

        if (currentGreenRoad == ROAD_A) setLightOutputs(LIGHT_GREEN, LIGHT_RED, LIGHT_RED);
        else if (currentGreenRoad == ROAD_B) setLightOutputs(LIGHT_RED, LIGHT_GREEN, LIGHT_RED);
        else if (currentGreenRoad == ROAD_C) setLightOutputs(LIGHT_RED, LIGHT_RED, LIGHT_GREEN);

        char buf[17];
        snprintf(buf, sizeof(buf), "PRIORITY ROAD %s", roadIndexToString(currentGreenRoad));
        updateLcd("EMERGENCY LOCKED", buf);

        Serial.printf("[TRAFFIC] *** PRIORITY OVERRIDE *** Road %s is now GREEN!\n", roadIndexToString(currentGreenRoad));
        notifyArduino("EMERGENCY", currentGreenRoad);
      }
      break;

    // -------------------------------------------------------------------------
    // 4. Emergency Mode: Ambulance Road locked in Green
    // -------------------------------------------------------------------------
    case MODE_EMERGENCY_GREEN:
      // Heartbeat check: If python vision hasn't detected the ambulance for EMERGENCY_HOLD_TIMEOUT,
      // it means the ambulance has cleared the intersection. Revert safely with 2s yellow.
      if (now - lastEmergencyHeartbeat >= EMERGENCY_HOLD_TIMEOUT) {
        Serial.println("[TRAFFIC] Emergency heartbeat timed out. Ambulance cleared. Resuming normal cycle...");
        targetEmergencyRoad = ROAD_NONE;
        
        // Give 2s yellow to the emergency road before moving forward
        currentMode = MODE_NORMAL_YELLOW;
        stateStartTime = now;

        if (currentGreenRoad == ROAD_A) setLightOutputs(LIGHT_YELLOW, LIGHT_RED, LIGHT_RED);
        else if (currentGreenRoad == ROAD_B) setLightOutputs(LIGHT_RED, LIGHT_YELLOW, LIGHT_RED);
        else if (currentGreenRoad == ROAD_C) setLightOutputs(LIGHT_RED, LIGHT_RED, LIGHT_YELLOW);

        char buf[17];
        snprintf(buf, sizeof(buf), "ROAD %s: 2s YEL", roadIndexToString(currentGreenRoad));
        updateLcd("AMBULANCE PASSED", buf);

        notifyArduino("NORMAL", currentGreenRoad);
      }
      break;
  }
}
