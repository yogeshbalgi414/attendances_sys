#include <Wire.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <time.h>

// OLED Setup
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// Buzzer
#define BUZZER_PIN 15

// RFID Setup
#define RST_PIN 16    // D0
#define SS_PIN 2      // D4
MFRC522 rfid(SS_PIN, RST_PIN);

// WiFi Credentials
const char* ssid = "NARZO 70 Pro 5G";
const char* password = "87654321";

// Flask Server
const char* serverUrl = "http://192.168.153.210:5000/api/scan";

// Flags
bool facultyScanned = false;
String lastFacultyID = "";

void setup() {
  pinMode(BUZZER_PIN, OUTPUT);
  Serial.begin(115200);

  Wire.begin(5, 4); // SDA = D1, SCL = D2

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED not found");
    while (1);
  }

  display.clearDisplay();
  display.setTextColor(WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("Connecting WiFi...");
  display.display();

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  configTime(19800, 0, "pool.ntp.org", "time.nist.gov"); // IST

  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("WiFi Connected");
  display.display();
  delay(2000);

  SPI.begin();
  rfid.PCD_Init();

  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("Scan Faculty Card...");
  display.display();
}

void loop() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    delay(300);
    return;
  }

  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    uid += String(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  Serial.println("Scanned UID: " + uid);

  String response = sendToServer(uid);

  display.clearDisplay();

  if (response.startsWith("FACULTY:")) {
    facultyScanned = true;
    lastFacultyID = uid;
    playSuccessTone();

    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("Faculty OK");

    display.setCursor(0, 15);
    display.println("ID: " + uid);

    display.setCursor(0, 30);
    display.println("Scan Student");

  } else if (response.startsWith("STUDENT:")) {
    if (facultyScanned) {
      playSuccessTone();
      display.setTextSize(1);
      display.setCursor(0, 0);
      display.println("Attendance Marked");

      display.setCursor(0, 15);
      display.println("Student:");

      display.setTextSize(2);
      display.setCursor(0, 35);
      display.println(response.substring(8));  // Student name or parent number
      display.setTextSize(1);
    } else {
      playErrorTone();
      display.setTextSize(2);
      display.setCursor(0, 20);
      display.println("No Faculty");
      display.setCursor(0, 45);
      display.println("Scanned!");
      display.setTextSize(1);
    }

  } else if (response == "NOCLASS") {
    playErrorTone();
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("No Class Scheduled");

  } else if (response == "UNKNOWN") {
    playErrorTone();
    display.setTextSize(2);
    display.setCursor(0, 20);
    display.println("Unknown");
    display.setCursor(0, 45);
    display.println("Card");
    display.setTextSize(1);

  } else if (response.startsWith("SESSION ENDED:")) {
    facultyScanned = false;
    lastFacultyID = "";
    playSuccessTone();

    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("Session Ended");

    display.setCursor(0, 15);
    display.println(response.substring(14));  // Faculty name

  } else if (response == "NO_TIMETABLE") {
    playErrorTone();
    display.setCursor(0, 0);
    display.println("No Class Today");

  } else if (response == "ALREADY_TAUGHT") {
    playErrorTone();
    display.setCursor(0, 0);
    display.println("Class Already Taken");

  } else if (response == "ALREADY_MARKED") {
    playErrorTone();
    display.setCursor(0, 0);
    display.println("Already Marked");

  } else {
    playErrorTone();
    display.setCursor(0, 0);
    display.println("Error Occurred");
  }

  display.display();
  delay(3000);

  display.clearDisplay();
  display.setCursor(0, 0);
  if (!facultyScanned) {
    display.println("Scan Faculty Card...");
  } else {
    display.println("Scan Student Card...");
  }
  display.display();

  rfid.PICC_HaltA();
}

String sendToServer(String uid) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    WiFiClient client;
    http.begin(client, serverUrl);
    http.addHeader("Content-Type", "application/x-www-form-urlencoded");

    String payload = "uid=" + uid + "&timestamp=" + getTimestamp();
    int httpCode = http.POST(payload);
    String response = http.getString();

    Serial.println("Server Response: " + response);
    http.end();
    return response;
  }
  return "ERROR";
}

String getTimestamp() {
  time_t now = time(nullptr);
  struct tm* p_tm = localtime(&now);
  char buffer[25];
  sprintf(buffer, "%04d-%02d-%02d %02d:%02d:%02d",
          p_tm->tm_year + 1900, p_tm->tm_mon + 1, p_tm->tm_mday,
          p_tm->tm_hour, p_tm->tm_min, p_tm->tm_sec);
  return String(buffer);
}

void playSuccessTone() {
  tone(BUZZER_PIN, 523, 150); // C5
  delay(200);
  tone(BUZZER_PIN, 659, 150); // E5
  delay(200);
  tone(BUZZER_PIN, 784, 150); // G5
  delay(200);
  noTone(BUZZER_PIN);
}


void playErrorTone() {
  tone(BUZZER_PIN, 784, 150); // G5
  delay(200);
  tone(BUZZER_PIN, 523, 150); // C5
  delay(200);
  tone(BUZZER_PIN, 400, 400); // low buzz
  delay(500);
  noTone(BUZZER_PIN);
}

