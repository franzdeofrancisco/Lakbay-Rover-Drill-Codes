# Lakbay-Rover-Drill-Codes
# ERC 2026 Dual Reciprocating Drill: Master SCADA & PLC Engine 

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![C++](https://img.shields.io/badge/C++-Arduino-00979D.svg)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-brightgreen)
![Status](https://img.shields.io/badge/Status-Field%20Ready-success)

A robust, 3-tier hardware and software architecture designed to control a heavy-duty Dual Reciprocating Drill mechanism inspired by wood wasp ovipositors for the ERC 2026 competition. 

This system transforms a Raspberry Pi into a headless, high-speed industrial PLC that bridges a wireless Windows command center with dual Arduino Mega hardware controllers. It features automated network discovery, real-time thermal rollback math, and multi-layered safety interlocks.

---

## 🏗️ System Architecture

The rig operates on a strict Master/Slave hierarchy separated into three distinct tiers to ensure high reliability and processing efficiency:

1. **Tier 1: Command Center HMI (Windows Laptop)**
   * Built with `PyQt6`, this UI acts as the operator dashboard.
   * Auto-discovers the drill rig on the local Wi-Fi via UDP beacons.
   * Parses live JSON telemetry at 20Hz for real-time monitoring and visual indicators.
   * Receives an integrated OpenCV video stream for remote operation.

2. **Tier 2: The Logic Engine (Raspberry Pi)**
   * Runs `drill_master_plc.py` as a headless Python PLC loop (30Hz).
   * Executes continuous ladder logic, physical interlocks, and dynamic fallback speed calculations.
   * Maintains a persistent TCP socket with the HMI, serving as a hardware Dead-Man's Switch.
   * Communicates with physical controllers via hardcoded USB IDs to prevent port-swapping.

3. **Tier 3: Hardware I/O (Dual Arduino Megas)**
   * **The Muscle (Driver Mega - ID 5573):** Parses high-speed 12-variable command strings to execute precise PWM controls across 4x BTS7960 motor drivers and 4x digital relays.
   * **The Senses (Sensor Mega - ID 8573):** Compresses data from limit switches, load cells (HX711), analog thermistors, and current sensors into a dense 18-byte binary packet for instantaneous transmission to the Pi.

---

## 🛡️ Safety Protocols

When drilling into dense substrates like Sibul clay, hardware preservation is critical. This software stack includes three non-negotiable safety layers:

* **Dynamic Thermal Rollback:** The Pi actively monitors current and temperature across all actuators. If limits (`T_WARN = 55.0°C`, `I_WARN = 12.0A`) are exceeded, the Pi linearly throttles PWM speeds. If critical limits (`T_CRIT = 75.0°C`, `I_CRIT = 18.0A`) are hit, the system triggers an automatic latching thermal trip.
* **TCP Dead-Man's Switch:** A 500ms heartbeat pulses over the Wi-Fi. If the command center loses connection, the Pi automatically engages `network_estop` and freezes all motors.
* **Hardware E-Stop Interlock:** The physical E-Stop cuts logic power to the motor drivers and signals an interrupt to the software stack simultaneously.

---

## ⚙️ Pinout & Hardware Map

### Sensor Mega (Data Acquisition)
| Component | Pins | Type |
| :--- | :--- | :--- |
| **Limit Switches 1-8** | `D2` to `D9` | Digital (`INPUT_PULLUP`) |
| **IR Sensors (ACT, S, E, W)** | `D10` to `D13` | Digital (`INPUT_PULLUP`) |
| **Motor Current Sensors** | `A0` to `A4` | Analog |
| **Temperature Sensors** | `A5` to `A7` | Analog |
| **Load Cell (HX711)** | `A8` (DT), `A9` (SCK)| Analog/Digital |
| **Hardware E-Stop** | `A10` | Digital (`INPUT_PULLUP`) |

### Driver Mega (Actuation)
| Component | Pins | Type |
| :--- | :--- | :--- |
| **Drill Motor (BTS7960)** | `D2` (RPWM), `D3` (LPWM) | PWM Output |
| **Vacuum Motor (BTS7960)** | `D4` (RPWM), `D5` (LPWM) | PWM Output |
| **Tele Motor (BTS7960)** | `D6` (RPWM), `D7` (LPWM) | PWM Output |
| **Linear Motor (BTS7960)** | `D8` (RPWM), `D9` (LPWM) | PWM Output |
| **Clamp Relays** | `D22` (FWD), `D23` (REV) | Digital Output |
| **Storage Relays** | `D24` (FWD), `D25` (REV) | Digital Output |

*(Note: The `EN` pins on all BTS7960 drivers are tied directly to the 5V logic bus via a Master Ignition Relay).*

---

## 🚀 Installation & Setup

### 1. Arduino Firmware
1. Open the Arduino IDE.
2. Install the **HX711 Arduino Library by Bogdan Necula**.
3. Flash `sensor_mega.ino` to the data acquisition board.
4. Flash `driver_mega.ino` to the motor control board.

### 2. Raspberry Pi Gateway
1. Connect both Arduino Megas to the Pi via USB.
2. Ensure the hardware IDs in the Python script match your physical boards by running `ls /dev/serial/by-id/`.
3. Install dependencies:
   ```bash
   pip install pyserial
