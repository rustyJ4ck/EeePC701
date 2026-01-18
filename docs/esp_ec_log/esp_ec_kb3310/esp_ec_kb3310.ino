#include <SoftwareSerial.h>

// EC             ESP
// 31 RX YELLOW   D1 TX BROWN
// 30 TX WHITE    D5 RX WHITE

// EC: PIN 30 EC_TX  -> D5
// EC: PIN 31 EC_RX  -> D1
// Common ground!

// Avoid D3 (GPIO0), D4 (GPIO2), D8 (GPIO15)

// Define pins: RX, TX
// Connect KB3310 TX to D5 and KB3310 RX to D1

// RX_PIN (Input to D1 Mini): Connect to the EC's TX Pin (KB3310 Pin 30)
// TX_PIN (Output from D1 Mini): Connect to the EC's RX Pin (KB3310 Pin 31)
SoftwareSerial ecSerial(D5, D1);  // (RX_PIN, TX_PIN)

void setup() {
  // Debug port to PC
  Serial.begin(115200); 
  delay(500); 
  Serial.println("D1> Listening on D5 (RX) and D1 (TX)");
  // Interface to ENE KB3310
  ecSerial.begin(115200); // Verify your EC's default baud rate
  
  Serial.println("D1> Software Serial Initialized...");
}

void loop() {
  // Forward data from KB3310 to USB Serial Monitor
  if (ecSerial.available()) {
    Serial.write(ecSerial.read());
  }

  // Forward data from USB Serial Monitor to KB3310
  // if (Serial.available()) {
  //   ecSerial.write(Serial.read());
  // }
}
