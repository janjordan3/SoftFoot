#define ROWS 14
#define COLS 16

// Updated to your ESP32-S3 safe pins
const int rowSelectPins[4] = {4, 5, 6, 7};
const int colSelectPins[4] = {15, 16, 17, 18};
const int adcPin = 10; 

// Die 14 Zeilenstreifen sind physisch an C2-C15 angeschlossen (nicht C0-C13) -
// dieser Offset sorgt dafür, dass der Code die richtigen Kanäle anspricht.
const int ROW_CHANNEL_OFFSET = 2;

// --- Timing ---
const int settleMicros = 50; 

void setMuxChannel(const int pins[4], int channel) {
  for (int i = 0; i < 4; i++) {
    digitalWrite(pins[i], (channel >> i) & 0x01);
  }
}

void setup() {
  Serial.begin(115200);

  for (int i = 0; i < 4; i++) {
    pinMode(rowSelectPins[i], OUTPUT);
    pinMode(colSelectPins[i], OUTPUT);
  }
  pinMode(adcPin, INPUT);

  analogReadResolution(12); // 0-4095
  analogSetAttenuation(ADC_11db); // Full 0-3.3V range for S3

  // kurze Pause, damit die serielle Verbindung steht, bevor Daten kommen
  delay(500);
}

void loop() {
  Serial.println("START");

  for (int row = 0; row < ROWS; row++) {
    setMuxChannel(rowSelectPins, row + ROW_CHANNEL_OFFSET);
    delayMicroseconds(settleMicros);

    String line = "";
    for (int col = 0; col < COLS; col++) {
      setMuxChannel(colSelectPins, col);
      delayMicroseconds(settleMicros);

      int value = analogRead(adcPin);
      line += String(value);
      if (col < COLS - 1) line += ",";
    }
    Serial.println(line);
  }

  Serial.println("END");
  delay(50); 
}
