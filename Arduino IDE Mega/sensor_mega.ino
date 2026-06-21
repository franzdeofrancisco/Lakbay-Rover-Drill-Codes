#include <HX711.h>

// ================= PINS =================
const int LS_PINS[8] = {2, 3, 4, 5, 6, 7, 8, 9};
const int IR_ACT = 10, IR_SOUTH = 11, IR_EAST = 12, IR_WEST = 13;
const int ESTOP_PIN = A10;
const int LOADCELL_DOUT_PIN = A8, LOADCELL_SCK_PIN = A9;

// ================= DATA STRUCTURE =================
// MUST match Python: struct.Struct("<BBHHHHHHHH") -> 18 Bytes
struct __attribute__((packed)) SensorData {
  uint8_t ls_bits;
  uint8_t sys_bits;
  uint16_t servo_i;
  uint16_t drill_i;
  uint16_t vac_i;
  uint16_t tele_i;
  uint16_t lin_i;
  uint16_t t_drill;
  uint16_t t_vac;
  uint16_t t_case;
};

SensorData payload;
unsigned long lastSend = 0;

void setup() {
  Serial.begin(115200);
  
  // Set all digital inputs to PULLUP to kill floating ghosts
  for(int i=0; i<8; i++) pinMode(LS_PINS[i], INPUT_PULLUP);
  pinMode(IR_ACT, INPUT_PULLUP);
  pinMode(IR_SOUTH, INPUT_PULLUP);
  pinMode(IR_EAST, INPUT_PULLUP);
  pinMode(IR_WEST, INPUT_PULLUP);
  pinMode(ESTOP_PIN, INPUT_PULLUP);
}

void loop() {
  if (millis() - lastSend >= 20) { // 50Hz sample rate
    
    // Pack Limit Switches into a single byte
    payload.ls_bits = 0;
    for(int i=0; i<8; i++) {
      if(digitalRead(LS_PINS[i]) == LOW) payload.ls_bits |= (1 << i);
    }
    
    // Pack System Status (Bin Full, Storage Full, E-Stop)
    payload.sys_bits = 0;
    if(digitalRead(IR_ACT) == LOW) payload.sys_bits |= (1 << 0);
    if(digitalRead(IR_SOUTH) == LOW) payload.sys_bits |= (1 << 1);
    if(digitalRead(ESTOP_PIN) == LOW) payload.sys_bits |= (1 << 2);
    
    // Analog Reads
    payload.servo_i = analogRead(A0);
    payload.drill_i = analogRead(A1);
    payload.vac_i   = analogRead(A2);
    payload.tele_i  = analogRead(A3);
    payload.lin_i   = analogRead(A4);
    payload.t_drill = analogRead(A5);
    payload.t_vac   = analogRead(A6);
    payload.t_case  = analogRead(A7);
    
    // Blast binary packet to Raspberry Pi
    Serial.write((uint8_t*)&payload, sizeof(payload));
    lastSend = millis();
  }
}
