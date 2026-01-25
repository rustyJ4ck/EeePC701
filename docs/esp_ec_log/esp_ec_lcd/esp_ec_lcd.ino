/**
Wiring Instructions:

ESP8266 D1 Mini to LCD (I2C):
D1 (GPIO5) → SCL (LCD)
D2 (GPIO4) → SDA (LCD)
5V → VCC (LCD)
GND → GND (LCD)

ESP8266 D1 Mini to EC (KB3310):
D5 (GPIO14) → RX (Receive from EC TX)
D1 (GPIO5) → TX (Transmit to EC RX - optional)

GND → GND (EC)

Power:

Connect 5V and GND from USB or external power

Required Libraries:
SoftwareSerial (built-in)
Wire (built-in for I2C)
LiquidCrystal_I2C (install via Arduino Library Manager)

Installation:

Open Arduino IDE
Install "LiquidCrystal I2C" library by Frank de Brabander
Select Board: "LOLIN(WEMOS) D1 R2 & mini" or "NodeMCU 1.0"
Set CPU Frequency: 160MHz
Set Upload Speed: 921600 (for faster uploads)
Upload the sketch

Features:

Display Format:
Line 1: CPU NN°C |oooooooooooooo| (40-70°C range)
Line 2: FAN NN% |oooooooooooooo| (0-100% range)

Custom Characters:
8-level vertical bars for visual gauge
Degree symbol (°)

Data Parsing:
Parses temperature from various EC formats
Parses fan PWM percentage
Filters temperatures to 40-80°C range

Update Rate:

LCD updates every 1 second
Real-time EC data parsing

Notes:

The LCD I2C address might be 0x27 or 0x3F - adjust in line 10
For a more visually appealing gauge, use updateDisplayWithCustomBars() instead of updateDisplay()
The sketch outputs debug info to Serial Monitor (115200 baud)
Custom bar characters provide 8 levels of fill for each character position



// D6 SDA ORANGE
// D7 SCL YELLOW
#define CUSTOM_SDA_PIN D6
#define CUSTOM_SCL_PIN D7

...

  // custom pin
  Wire.begin(CUSTOM_SDA_PIN, CUSTOM_SCL_PIN);
  //Wire.setClock(100000);  // 100 kHz
  Wire.setClock(50000); // if shimmering

*/

#include <SoftwareSerial.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <ESP8266WiFi.h>

// ====== PIN CONFIGURATION ======
#define RX_PIN D5  // Receive from EC
#define TX_PIN D1  // Transmit to EC

// Custom I2C Pins for LCD
#define LCD_SDA D6  // GPIO4
#define LCD_SCL D7  // GPIO12

// LCD configuration
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Serial interface to EC
SoftwareSerial ecSerial(RX_PIN, TX_PIN);

// Variables for data
// int cpuTemp = 0;
// int fanPWM = 0;
unsigned long lastUpdate = 0;
const unsigned long updateInterval = 2000;

String currentParam = ""; // Stores the parameter found on the PREVIOUS line
int cpuTemp = 0;
int fanMode = 0;
int fanRPM = 0;

// Custom degree symbol
byte degreeSymbol[8] = {
  B01100,
  B10010,
  B10010,
  B01100,
  B00000,
  B00000,
  B00000,
  B00000
};

// Parse hex to int
//int hexToInt(String hexStr) {
//  return (int)strtol(hexStr.c_str(), NULL, 16);
//}

// Create temperature gauge with solid blocks
String createTempGauge(int temp) {
  String gauge = "";
  int gaugeChars = 13;
  int minTemp = 40;
  int maxTemp = 80;
  
  int filled = 0;
  if (temp <= minTemp) {
    filled = 0;
  } else if (temp >= maxTemp) {
    filled = gaugeChars;
  } else {
    filled = map(temp, minTemp, maxTemp, 0, gaugeChars);
  }
  
  for (int i = 0; i < gaugeChars; i++) {
    if (i < filled) {
      gauge += char(0xFF);  // Solid block character (█)
    } else {
      gauge += ' ';  // Single character
    }
  }
  
  return gauge;
}

// Create fan gauge with solid blocks
String createFanGauge(int pwm) {
  String gauge = "";
  int gaugeChars = 13;
  
  int filled = map(pwm, 40, 90, 0, gaugeChars);
  filled = constrain(filled, 0, gaugeChars);
  
  for (int i = 0; i < gaugeChars; i++) {
    if (i < filled) {
      gauge += char(0xFF);  // Solid block character (█)
    } else {
      gauge += ' ';  // Single character
    }
  }
  
  return gauge;
}

void setup() {
  // ====== DISABLE WIFI ======
  WiFi.mode(WIFI_OFF);
  WiFi.forceSleepBegin();
  delay(1);
  system_update_cpu_freq(80);
  
  // Debug port to PC
  Serial.begin(115200);
  delay(500);
  Serial.println("EEE PC 701 CPU/FAN");
  Serial.println("EC Monitor");
  
  // Interface to ENE KB3310 EC
  ecSerial.begin(115200);
  
  // ====== INITIALIZE LCD ======
  Wire.begin(LCD_SDA, LCD_SCL);
  Wire.setClock(50000);
  
  lcd.init();
  lcd.setBacklight(96);
  lcd.createChar(0, degreeSymbol);
  
  // Display startup
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("EC Val+Param");
  lcd.setCursor(0, 1);
  lcd.print("WiFi: OFF");
  
  delay(1000);
  lcd.clear();
  updateDisplay();
}

void loop() {
  // Parse incoming data from EC
  static String buffer = "";
  
  while (ecSerial.available()) {
    char c = ecSerial.read();
    
    // Echo to serial monitor for debugging
    Serial.write(c);
    
    // End of line
    if (c == '\n' || c == '\r') {
      if (buffer.length() > 0) {
        parseLine(buffer);
        buffer = "";
      }
    } else {
      buffer += c;
    }
  }
  
  // Update LCD display periodically
  if (millis() - lastUpdate >= updateInterval) {
    updateDisplay();
    lastUpdate = millis();
  }
  
  delay(10);
}

// Essential hex-to-int helper for 3C, 3D, etc.
int hexToInt(String hexStr) {
  return (int) strtol(hexStr.c_str(), NULL, 16);
}

void parseLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  // 1. Split the line at the first comma
  // Example: "03,3C,T(A0,S0)TTTCPUTmp" 
  // valuePart = "03,3C,T(A0,S0)TTT"
  // headerPart = "CPUTmp" (identified by endsWith)
  
  int firstComma = line.indexOf(',');
  String valuePart = (firstComma > 0) ? line.substring(0, line.lastIndexOf(',', line.length() - 8)) : "";

  // 2. PARSE THE DATA FIRST (using the stored currentParam)
  // We use the data at the start of the current line
  if (currentParam == "CPUTmp") {
    parseCpuTempValue(line); 
  } else if (currentParam == "CFan") {
    parseFanValue(line);
  }

  // 3. SET THE NEW PARAMETER (for the next line)
  if (line.endsWith("CPUTmp")) {
    currentParam = "CPUTmp";
  } else if (line.endsWith("CFan idx,PWM")) {
    currentParam = "CFan";
  } else {
    currentParam = ""; // Reset if line doesn't end with a known header
  }
}

void parseCpuTempValue(String data) {
  // Get first hex before comma
  int comma = data.indexOf(',');
  String hex = (comma > 0) ? data.substring(0, comma) : data;
  cpuTemp = hexToInt(hex);
  
  Serial.print("CPU Temp Updated: ");
  Serial.println(cpuTemp);
}

void parseFanValue(String data) {
  // Get first and second hex
  int firstComma = data.indexOf(',');
  if (firstComma == -1) return;
  int secondComma = data.indexOf(',', firstComma + 1);
  
  String modeHex = data.substring(0, firstComma);
  String rpmHex = (secondComma > 0) ? data.substring(firstComma + 1, secondComma) : data.substring(firstComma + 1);
  
  fanMode = hexToInt(modeHex);
  fanRPM  = hexToInt(rpmHex);

  Serial.print("Fan Updated - Mode: ");
  Serial.print(fanMode);
  Serial.print(" PWM: ");
  Serial.println(fanRPM);
}



void updateDisplay() {
  // Update without clearing to reduce flicker
  
  // Line 1: CPU Temperature
  lcd.setCursor(0, 0);
  lcd.print("CPU");
  lcd.setCursor(3, 0);
  
  if (cpuTemp > 0) {
    if (cpuTemp < 10) {
      lcd.print(" ");
      lcd.print(cpuTemp);
    } else {
      lcd.print(cpuTemp);
    }
    
    lcd.write(0);  // Degree symbol
    
    // Print gauge
    lcd.setCursor(6, 0);
    String tempGauge = createTempGauge(cpuTemp);
    lcd.print(tempGauge);
  } else {
    lcd.print("---");
    lcd.setCursor(6, 0);
    lcd.print("             ");
  }
  
  // Line 2: Fan PWM
  lcd.setCursor(0, 1);
  lcd.print("FAN");
  lcd.setCursor(3, 1);
  
  if (fanRPM >= 0) {
    if (fanRPM < 10) {
      lcd.print(" ");
      lcd.print(fanRPM);
    } else {
      lcd.print(fanRPM);
    }
    
    lcd.print("%");
    
    // Print gauge
    lcd.setCursor(6, 1);
    String fanGauge = createFanGauge(fanRPM);
    lcd.print(fanGauge);
  } else {
    lcd.print("---%");
    lcd.setCursor(6, 1);
    lcd.print("             ");
  }
}