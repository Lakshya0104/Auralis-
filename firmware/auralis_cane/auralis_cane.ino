// AURALIS smart cane firmware (ESP32 DevKit, Arduino core 2.x/3.x)
//
// Reads two ultrasonic sensors (front + downward), streams distances to the
// phone over BLE, and drives a vibration motor. The cane keeps working on its
// own (local haptic fallback) when the phone is disconnected.
//
// BLE protocol (Nordic-UART style):
//   notify  "F:<cm>,D:<cm>,B:<0|1>"   every 100 ms   (front, down, button)
//   write   "V<n>"                    vibrate pattern n (1=caution 2=warning 3=urgent 4=confirm)

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#define SERVICE_UUID "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define RX_UUID      "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  // phone -> cane
#define TX_UUID      "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  // cane -> phone

// Pins (HC-SR04 echo is 5 V: use a 1k/2k divider to 3.3 V, or use JSN-SR04T/US-100 at 3.3 V)
const int FRONT_TRIG = 5,  FRONT_ECHO = 18;
const int DOWN_TRIG  = 19, DOWN_ECHO  = 21;
const int MOTOR_PIN  = 25;  // -> 1k -> NPN base (2N2222/BC547); motor on collector; 1N4007 flyback
const int BUZZER_PIN = 26;  // optional active buzzer
const int BUTTON_PIN = 27;  // to GND, internal pull-up

// Local fallback thresholds (cm)
const int FRONT_URGENT = 60, FRONT_WARN = 120;
const int DROP_DELTA   = 25;  // downward reading this much longer than baseline = step-down / pit

BLECharacteristic *txChar;
bool phoneConnected = false;
int  downBaseline = -1;
volatile int pendingPattern = 0;

class ServerCb : public BLEServerCallbacks {
  void onConnect(BLEServer *) override { phoneConnected = true; }
  void onDisconnect(BLEServer *s) override {
    phoneConnected = false;
    s->getAdvertising()->start();
  }
};

class RxCb : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    String v = c->getValue().c_str();
    if (v.length() >= 2 && v[0] == 'V') pendingPattern = v.substring(1).toInt();
  }
};

int readCm(int trig, int echo) {
  digitalWrite(trig, LOW);  delayMicroseconds(2);
  digitalWrite(trig, HIGH); delayMicroseconds(10);
  digitalWrite(trig, LOW);
  long us = pulseIn(echo, HIGH, 25000);  // ~4 m timeout
  return us == 0 ? 400 : (int)(us / 58);
}

void pulse(int n, int onMs, int offMs) {
  for (int i = 0; i < n; i++) {
    digitalWrite(MOTOR_PIN, HIGH); digitalWrite(BUZZER_PIN, HIGH);
    delay(onMs);
    digitalWrite(MOTOR_PIN, LOW);  digitalWrite(BUZZER_PIN, LOW);
    delay(offMs);
  }
}

void playPattern(int p) {
  switch (p) {
    case 1: pulse(1, 120, 0); break;    // caution
    case 2: pulse(2, 150, 100); break;  // warning
    case 3: pulse(4, 250, 80); break;   // urgent / stop
    case 4: pulse(1, 60, 0); break;     // confirmation
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(FRONT_TRIG, OUTPUT); pinMode(FRONT_ECHO, INPUT);
  pinMode(DOWN_TRIG, OUTPUT);  pinMode(DOWN_ECHO, INPUT);
  pinMode(MOTOR_PIN, OUTPUT);  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  BLEDevice::init("AURALIS-Cane");
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new ServerCb());
  BLEService *svc = server->createService(SERVICE_UUID);
  txChar = svc->createCharacteristic(TX_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  txChar->addDescriptor(new BLE2902());
  BLECharacteristic *rx = svc->createCharacteristic(
      RX_UUID, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  rx->setCallbacks(new RxCb());
  svc->start();
  BLEAdvertising *adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(SERVICE_UUID);
  adv->start();

  pulse(2, 80, 80);  // boot OK
}

void loop() {
  int front = readCm(FRONT_TRIG, FRONT_ECHO);
  delay(15);  // avoid cross-talk between sensors
  int down = readCm(DOWN_TRIG, DOWN_ECHO);
  bool button = digitalRead(BUTTON_PIN) == LOW;

  // Slowly learn the normal cane-to-ground distance while walking on flat ground
  if (downBaseline < 0) downBaseline = down;
  else if (abs(down - downBaseline) < DROP_DELTA) downBaseline = (downBaseline * 9 + down) / 10;
  bool drop = down - downBaseline > DROP_DELTA;

  if (phoneConnected) {
    char buf[40];
    snprintf(buf, sizeof(buf), "F:%d,D:%d,B:%d,G:%d", front, down, button ? 1 : 0, downBaseline);
    txChar->setValue((uint8_t *)buf, strlen(buf));
    txChar->notify();
    if (pendingPattern) { playPattern(pendingPattern); pendingPattern = 0; }
  } else {
    // Graceful fallback: cane alone still warns
    if (drop || front < FRONT_URGENT) playPattern(3);
    else if (front < FRONT_WARN) playPattern(1);
  }
  delay(85);
}
