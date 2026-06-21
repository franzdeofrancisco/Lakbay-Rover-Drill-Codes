import sys
import serial
import time
import struct
import socket
import threading
import json

# ================= CONFIGURATION & LIMITS =================
DRIVER_PORT = "/dev/serial/by-id/usb-Arduino__www.arduino.cc__0042_55731323336351109192-if00"
SENSOR_PORT = "/dev/serial/by-id/usb-Arduino__www.arduino.cc__0042_857353136323519041A1-if00"

T_WARN = 55.0   
T_CRIT = 75.0   
I_WARN = 12.0   
I_CRIT = 18.0   
MAX_SPEED = 210
MIN_RECOVERY_SPEED = 90
HOST = '0.0.0.0'
PORT = 5050

# ================= GLOBAL STATE =================
class SystemState:
    def __init__(self):
        self.laptop_connected = False
        self.active_conn = None
        self.network_estop = True  
        self.thermal_trip = False
        
        self.inputs = {f"ls{i}": False for i in range(1, 9)}
        self.inputs.update({
            "bfull": False, "s1full": False, "estop": False,
            "drillCurrent": 0.0, "vacuumCurrent": 0.0, "teleCurrent": 0.0, "linCurrent": 0.0,
            "tempDrill": 0.0, "tempVac": 0.0, "tempCase": 0.0, "thermal_trip": False
        })
        
        self.manualMode = False
        self.startPB = False
        self.reset = False
        
        self.drill_ON = False; self.vacuum_ON = False
        self.tele_fwd = False; self.tele_rev = False
        self.lin_fwd = False; self.lin_rev = False
        self.clamp_fwd = False; self.clamp_rev = False
        self.storage_fwd = False; self.storage_rev = False

        self.M1 = self.M2 = self.M3 = self.M4 = self.M5 = self.M6 = self.M7 = self.M8 = self.M11 = self.M15 = False
        self.M100 = self.M101 = self.M102 = self.M103 = False

state = SystemState()

# ================= HARDWARE CONNECTIONS =================
try:
    sensor_serial = serial.Serial(SENSOR_PORT, 115200, timeout=0.1)
    print("SENSES: Sensor Mega (8573) Connected.")
except Exception as e:
    print(f"CRITICAL: Sensor Mega missing! {e}")
    exit(1)

try:
    driver_serial = serial.Serial(DRIVER_PORT, 115200, timeout=0.1)
    print("MUSCLE: Drill Driver Mega (5573) Connected.")
except Exception as e:
    print(f"CRITICAL: Driver Mega missing! {e}")
    exit(1)

time.sleep(2)

# ================= NETWORK BRIDGE =================
def udp_beacon():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            my_ip = s.getsockname()[0]
            s.close()
            udp_sock.sendto(f"DRILL_RIG_GATEWAY:{my_ip}".encode('utf-8'), ('<broadcast>', 5051))
        except: pass
        time.sleep(2)

def telemetry_broadcaster():
    while True:
        if state.laptop_connected and state.active_conn:
            try:
                payload_data = state.inputs.copy()
                payload_data.update({
                    "thermal_trip": state.thermal_trip, "manualMode": state.manualMode,
                    "drill_ON": state.drill_ON, "vacuum_ON": state.vacuum_ON,
                    "tele_fwd": state.tele_fwd, "tele_rev": state.tele_rev,
                    "lin_fwd": state.lin_fwd, "lin_rev": state.lin_rev,
                    "clamp_fwd": state.clamp_fwd, "clamp_rev": state.clamp_rev,
                    "storage_fwd": state.storage_fwd, "storage_rev": state.storage_rev
                })
                payload = json.dumps(payload_data) + "\n"
                state.active_conn.sendall(payload.encode('utf-8'))
            except: pass
        time.sleep(0.05) 

def tcp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"Gateway LIVE on Port {PORT}. Waiting for Command Center...")

    while True:
        conn, addr = server.accept()
        print(f"Laptop Connected from {addr[0]}!")
        state.active_conn = conn
        state.laptop_connected = True
        state.network_estop = False 

        while True:
            try:
                data = conn.recv(1024).decode('utf-8')
                if not data: break 
                
                for char in data:
                    if char == 'M': state.manualMode = not state.manualMode
                    elif char == 'S': state.startPB = True
                    elif char == 'R': state.reset = True; state.thermal_trip = False
                    elif char == 'E': state.network_estop = not state.network_estop
                    elif char == 'H': pass 
                    
                    if state.manualMode:
                        if char == '0': state.drill_ON = not state.drill_ON
                        elif char == '1': state.vacuum_ON = not state.vacuum_ON
                        elif char == '2': state.tele_fwd = not state.tele_fwd; state.tele_rev = False
                        elif char == '3': state.tele_rev = not state.tele_rev; state.tele_fwd = False
                        elif char == '4': state.lin_fwd = not state.lin_fwd; state.lin_rev = False
                        elif char == '5': state.lin_rev = not state.lin_rev; state.lin_fwd = False
                        elif char == '6': state.clamp_fwd = not state.clamp_fwd; state.clamp_rev = False
                        elif char == '7': state.clamp_rev = not state.clamp_rev; state.clamp_fwd = False
                        elif char == '8': state.storage_fwd = not state.storage_fwd; state.storage_rev = False
                        elif char == '9': state.storage_rev = not state.storage_rev; state.storage_fwd = False
            except: break
        
        print("Laptop Disconnected. ENGAGING DEAD-MAN'S SWITCH.")
        conn.close()
        state.active_conn = None
        state.laptop_connected = False
        state.network_estop = True

threading.Thread(target=udp_beacon, daemon=True).start()
threading.Thread(target=telemetry_broadcaster, daemon=True).start()
threading.Thread(target=tcp_server, daemon=True).start()

# ================= LADDER LOGIC & SAFETY =================
def calculate_fallback_speed(current_val, temp_val):
    if current_val >= I_CRIT or temp_val >= T_CRIT: return -1 
    current_factor = (current_val - I_WARN) / (I_CRIT - I_WARN) if current_val > I_WARN else 0.0
    temp_factor = (temp_val - T_WARN) / (T_CRIT - T_WARN) if temp_val > T_WARN else 0.0
    worst_factor = max(current_factor, temp_factor)
    return max(MIN_RECOVERY_SPEED, MAX_SPEED - int(worst_factor * (MAX_SPEED - MIN_RECOVERY_SPEED)))

packet_struct = struct.Struct("<BBHHHHHHHH")
raw_to_amps = lambda adc: round((adc * (5.0 / 1023.0)) * 10.0, 2)

print("Starting Main PLC Loop...")
while True:
    try:
        if sensor_serial.in_waiting >= packet_struct.size:
            data = sensor_serial.read(packet_struct.size)
            unpacked = packet_struct.unpack(data)
            
            ls = unpacked[0]; sys_stat = unpacked[1]
            for i in range(8): state.inputs[f"ls{i+1}"] = bool(ls & (1 << i))
                
            state.inputs["bfull"] = bool(sys_stat & (1 << 0))
            state.inputs["s1full"] = bool(sys_stat & (1 << 1))
            state.inputs["estop"] = bool(sys_stat & (1 << 2))
            
            state.inputs["servoCurrent"] = raw_to_amps(unpacked[2])
            state.inputs["drillCurrent"] = raw_to_amps(unpacked[3])
            state.inputs["vacuumCurrent"] = raw_to_amps(unpacked[4])
            state.inputs["teleCurrent"] = raw_to_amps(unpacked[5])
            state.inputs["linCurrent"] = raw_to_amps(unpacked[6])
            
            state.inputs["tempDrill"] = float(unpacked[7])
            state.inputs["tempVac"] = float(unpacked[8])
            state.inputs["tempCase"] = float(unpacked[9])
            
            if sensor_serial.in_waiting > 150: sensor_serial.flushInput()
    except: pass

    # NOTE: Set speeds to MAX_SPEED here to bypass float-pin limits during bench testing
    d_spd = calculate_fallback_speed(state.inputs["drillCurrent"], state.inputs["tempDrill"])
    v_spd = calculate_fallback_speed(state.inputs["vacuumCurrent"], state.inputs["tempVac"])
    t_spd = calculate_fallback_speed(state.inputs["teleCurrent"], state.inputs["tempCase"])
    l_spd = calculate_fallback_speed(state.inputs["linCurrent"], state.inputs["tempCase"])

    if -1 in [d_spd, v_spd, t_spd, l_spd]: state.thermal_trip = True
    master_estop = state.inputs["estop"] or state.network_estop or state.thermal_trip

    if not state.manualMode:
        state.M100 = state.startPB and not state.M7
        state.M101 = master_estop
        state.M103 = (state.reset or state.M103) and not state.M8
        state.M8 = state.inputs["ls8"] and state.inputs["ls5"] and state.inputs["ls3"] and state.inputs["ls1"]
        state.M102 = (state.M100 or state.M102) and not state.M103 and not state.M6 and not state.M101
        
        if state.M102:
            state.M1 = (state.M100 or state.M1) and not state.M3 and not state.inputs["ls2"]
            state.tele_fwd = state.M1 and not state.M101
            state.M2 = (state.M1 or state.M2) and not state.M5
            state.M3 = state.inputs["ls2"] and not state.inputs["ls4"] and not state.M6
            state.M4 = (state.M3 or state.M4) and not state.inputs["ls4"]
            state.lin_fwd = state.M4 and not state.M101
            state.M11 = (state.M4 or state.M11) and not state.M5
            state.vacuum_ON = state.M11 and not state.M101
        else:
            state.lin_fwd = state.tele_fwd = state.vacuum_ON = False
            state.M1 = state.M2 = state.M3 = state.M4 = state.M11 = False

        state.M15 = (state.M102 or state.M15) and not state.M101 and not state.inputs["ls1"]
        state.drill_ON = state.M15
        state.M5 = (state.inputs["bfull"] or state.M5) and not state.M7 and not state.inputs["ls6"]
        state.storage_fwd = state.M5 and not state.M101
        state.clamp_fwd = (state.M2 or state.M6) and not state.inputs["ls8"] and not state.M101
        state.clamp_rev = state.inputs["ls6"] and not state.M6 and not state.inputs["ls7"] and not state.M101
        state.M7 = state.inputs["s1full"]
        state.M6 = (state.M7 or state.M103 or (state.M6 and not state.inputs["ls1"])) and not state.M101
        
        if state.M6:
            state.storage_rev = not state.inputs["ls5"] and state.inputs["ls8"]
            state.lin_rev = state.inputs["ls5"] and not state.inputs["ls3"]
            state.tele_rev = state.inputs["ls3"] and not state.inputs["ls1"]
        else: state.storage_rev = state.lin_rev = state.tele_rev = False
        state.startPB = False; state.reset = False
    else:
        if state.tele_fwd and state.inputs["ls2"]: state.tele_fwd = False
        if state.tele_rev and state.inputs["ls1"]: state.tele_rev = False
        if state.lin_fwd and state.inputs["ls4"]:  state.lin_fwd = False
        if state.lin_rev and state.inputs["ls3"]:  state.lin_rev = False
        if state.clamp_fwd and state.inputs["ls8"]: state.clamp_fwd = False
        if state.clamp_rev and state.inputs["ls7"]: state.clamp_rev = False
        if state.storage_fwd and state.inputs["ls6"]: state.storage_fwd = False
        if state.storage_rev and state.inputs["ls5"]: state.storage_rev = False
        
        if master_estop:
            state.drill_ON = state.vacuum_ON = state.tele_fwd = state.tele_rev = False
            state.lin_fwd = state.lin_rev = state.clamp_fwd = state.clamp_rev = state.storage_fwd = state.storage_rev = False

    tele_dir = 1 if state.tele_fwd else (2 if state.tele_rev else 0)
    lin_dir = 1 if state.lin_fwd else (2 if state.lin_rev else 0)
    final_d_spd = max(0, d_spd) if state.drill_ON else 0
    final_v_spd = max(0, v_spd) if state.vacuum_ON else 0
    final_t_spd = max(0, t_spd) if tele_dir > 0 else 0
    final_l_spd = max(0, l_spd) if lin_dir > 0 else 0

    cmd_str = (f"TX,{tele_dir},{lin_dir},{1 if state.drill_ON else 0},{1 if state.vacuum_ON else 0},"
               f"{1 if state.clamp_fwd else 0},{1 if state.clamp_rev else 0},"
               f"{1 if state.storage_fwd else 0},{1 if state.storage_rev else 0},"
               f"{final_d_spd},{final_v_spd},{final_t_spd},{final_l_spd}\n")
    try: driver_serial.write(cmd_str.encode())
    except: pass
    time.sleep(0.03)
