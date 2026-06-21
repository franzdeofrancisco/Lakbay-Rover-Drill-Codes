// ================= PIN ASSIGNMENTS =================
// BTS7960 Motor Drivers (PWM Pins)
const int DRILL_RPWM = 2;  const int DRILL_LPWM = 3;
const int VAC_RPWM   = 4;  const int VAC_LPWM   = 5;
const int TELE_RPWM  = 6;  const int TELE_LPWM  = 7;
const int LIN_RPWM   = 8;  const int LIN_LPWM   = 9;

// Relays (Standard Digital I/O)
const int CLAMP_FWD_PIN = 22; const int CLAMP_REV_PIN = 23;
const int STOR_FWD_PIN  = 24; const int STOR_REV_PIN  = 25;

// ================= VARIABLES =================
const byte numChars = 64;
char receivedChars[numChars];
boolean newData = false;
unsigned long lastCommandTime = 0;

// Parsed Command States
int tele_dir = 0, lin_dir = 0;
int drill_state = 0, vac_state = 0;
int clamp_fwd = 0, clamp_rev = 0;
int storage_fwd = 0, storage_rev = 0;
int d_spd = 0, v_spd = 0, t_spd = 0, l_spd = 0;

void setup() {
  Serial.begin(115200);

  pinMode(DRILL_RPWM, OUTPUT); pinMode(DRILL_LPWM, OUTPUT);
  pinMode(VAC_RPWM, OUTPUT);   pinMode(VAC_LPWM, OUTPUT);
  pinMode(TELE_RPWM, OUTPUT);  pinMode(TELE_LPWM, OUTPUT);
  pinMode(LIN_RPWM, OUTPUT);   pinMode(LIN_LPWM, OUTPUT);

  pinMode(CLAMP_FWD_PIN, OUTPUT); pinMode(CLAMP_REV_PIN, OUTPUT);
  pinMode(STOR_FWD_PIN, OUTPUT);  pinMode(STOR_REV_PIN, OUTPUT);

  killAllSystems(); 
}

void loop() {
  receiveData();
  if (newData == true) {
    parseData();
    executeCommands();
    newData = false;
  }
  // PHYSICAL DEAD-MAN'S SWITCH (500ms timeout)
  if (millis() - lastCommandTime > 500) {
    killAllSystems();
  }
}

void receiveData() {
  static byte ndx = 0;
  char endMarker = '\n';
  char rc;
  while (Serial.available() > 0 && newData == false) {
    rc = Serial.read();
    if (rc != endMarker) {
      receivedChars[ndx] = rc;
      ndx++;
      if (ndx >= numChars) ndx = numChars - 1;
    } else {
      receivedChars[ndx] = '\0';
      ndx = 0;
      newData = true;
      lastCommandTime = millis();
    }
  }
}

void parseData() {
  char * strtokIndx; 
  strtokIndx = strtok(receivedChars, ",");
  if(strcmp(strtokIndx, "TX") != 0) return; 

  strtokIndx = strtok(NULL, ","); tele_dir = atoi(strtokIndx);
  strtokIndx = strtok(NULL, ","); lin_dir = atoi(strtokIndx);
  strtokIndx = strtok(NULL, ","); drill_state = atoi(strtokIndx);
  strtokIndx = strtok(NULL, ","); vac_state = atoi(strtokIndx);
  strtokIndx = strtok(NULL, ","); clamp_fwd = atoi(strtokIndx);
  strtokIndx = strtok(NULL, ","); clamp_rev = atoi(strtokIndx);
  strtokIndx = strtok(NULL, ","); storage_fwd = atoi(strtokIndx);
  strtokIndx = strtok(NULL, ","); storage_rev = atoi(strtokIndx);
  strtokIndx = strtok(NULL, ","); d_spd = atoi(strtokIndx);
  strtokIndx = strtok(NULL, ","); v_spd = atoi(strtokIndx);
  strtokIndx = strtok(NULL, ","); t_spd = atoi(strtokIndx);
  strtokIndx = strtok(NULL, ","); l_spd = atoi(strtokIndx);
}

void executeCommands() {
  // Telescopic
  if (tele_dir == 1) { analogWrite(TELE_RPWM, t_spd); analogWrite(TELE_LPWM, 0); } 
  else if (tele_dir == 2) { analogWrite(TELE_RPWM, 0); analogWrite(TELE_LPWM, t_spd); } 
  else { analogWrite(TELE_RPWM, 0); analogWrite(TELE_LPWM, 0); }

  // Linear
  if (lin_dir == 1) { analogWrite(LIN_RPWM, l_spd); analogWrite(LIN_LPWM, 0); } 
  else if (lin_dir == 2) { analogWrite(LIN_RPWM, 0); analogWrite(LIN_LPWM, l_spd); } 
  else { analogWrite(LIN_RPWM, 0); analogWrite(LIN_LPWM, 0); }

  // Drill & Vac
  if (drill_state == 1) { analogWrite(DRILL_RPWM, d_spd); analogWrite(DRILL_LPWM, 0); } 
  else { analogWrite(DRILL_RPWM, 0); analogWrite(DRILL_LPWM, 0); }
  if (vac_state == 1) { analogWrite(VAC_RPWM, v_spd); analogWrite(VAC_LPWM, 0); } 
  else { analogWrite(VAC_RPWM, 0); analogWrite(VAC_LPWM, 0); }

  // Relays (Active-LOW)
  digitalWrite(CLAMP_FWD_PIN, clamp_fwd == 1 ? LOW : HIGH);
  digitalWrite(CLAMP_REV_PIN, clamp_rev == 1 ? LOW : HIGH);
  digitalWrite(STOR_FWD_PIN, storage_fwd == 1 ? LOW : HIGH);
  digitalWrite(STOR_REV_PIN, storage_rev == 1 ? LOW : HIGH);
}

void killAllSystems() {
  analogWrite(DRILL_RPWM, 0); analogWrite(DRILL_LPWM, 0);
  analogWrite(VAC_RPWM, 0);   analogWrite(VAC_LPWM, 0);
  analogWrite(TELE_RPWM, 0);  analogWrite(TELE_LPWM, 0);
  analogWrite(LIN_RPWM, 0);   analogWrite(LIN_LPWM, 0);
  digitalWrite(CLAMP_FWD_PIN, HIGH); digitalWrite(CLAMP_REV_PIN, HIGH);
  digitalWrite(STOR_FWD_PIN, HIGH);  digitalWrite(STOR_REV_PIN, HIGH);
}
