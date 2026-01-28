#!/usr/bin/env python3
"""
TallyPi - ATEM to Smartview Tally Bridge
Uses the simple Videohub protocol on port 9990
"""

import socket
import threading
import time
import logging
import re

# Configuration
ATEM_IP = "10.253.20.229"
ATEM_PORT = 9990
SMARTVIEW_IP = "10.253.20.211"
SMARTVIEW_PORT = 9992

# Map ATEM inputs to Smartview monitors
# Format: atem_input: (monitor_index, green_only)
# green_only=True means only show green, never red
INPUT_TO_MONITOR = {
    1: (0, False),  # Camera 1 -> Monitor A, red+green
    2: (1, False),  # Camera 2 -> Monitor B, red+green
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("TallyPi")


class SmartviewClient:
    def __init__(self, ip, port=9992):
        self.ip = ip
        self.port = port
        self.sock = None
        self.lock = threading.Lock()
    
    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.ip, self.port))
            self.sock.recv(4096)
            log.info("Smartview connected")
            return True
        except Exception as e:
            log.error(f"Smartview connection failed: {e}")
            return False
    
    def set_border(self, monitor_index, color):
        if not self.sock:
            if not self.connect():
                return
        
        monitor = chr(ord('A') + monitor_index)
        cmd = f"MONITOR {monitor}:\nBorder: {color}\n\n"
        
        with self.lock:
            try:
                self.sock.sendall(cmd.encode())
                log.info(f"Monitor {monitor} -> {color}")
            except Exception as e:
                log.error(f"Smartview send failed: {e}")
                self.sock = None


class TallyBridge:
    def __init__(self):
        self.smartview = SmartviewClient(SMARTVIEW_IP, SMARTVIEW_PORT)
        self.program_input = None
        self.preview_input = None
        self.sock = None
        self.monitor_state = {0: "None", 1: "None"}  # Track current state
    
    def connect_atem(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(30)
            self.sock.connect((ATEM_IP, ATEM_PORT))
            log.info("ATEM connected (Videohub protocol)")
            return True
        except Exception as e:
            log.error(f"ATEM connection failed: {e}")
            return False
    
    def update_tally(self):
        """Update Smartview borders based on current program/preview"""
        new_state = {0: "None", 1: "None"}
        
        # Check each mapped input
        for atem_input, (monitor_idx, green_only) in INPUT_TO_MONITOR.items():
            if atem_input == self.program_input:
                if green_only:
                    # Green only cameras show green even on program
                    if new_state[monitor_idx] == "None":
                        new_state[monitor_idx] = "Green"
                else:
                    # Normal cameras show red on program
                    new_state[monitor_idx] = "Red"
            elif atem_input == self.preview_input:
                # Preview always shows green (if not already red)
                if new_state[monitor_idx] != "Red":
                    new_state[monitor_idx] = "Green"
        
        # Apply changes
        for monitor_idx in [0, 1]:
            if new_state[monitor_idx] != self.monitor_state[monitor_idx]:
                self.smartview.set_border(monitor_idx, new_state[monitor_idx])
                self.monitor_state[monitor_idx] = new_state[monitor_idx]
    
    def parse_routing(self, data):
        lines = data.strip().split('\n')
        changed = False
        
        for line in lines:
            match = re.match(r'^(\d+)\s+(\d+)$', line.strip())
            if match:
                output = int(match.group(1))
                input_idx = int(match.group(2))
                
                if output == 2:  # Program output
                    if self.program_input != input_idx:
                        self.program_input = input_idx
                        log.info(f"Program -> Input {input_idx}")
                        changed = True
                elif output == 3:  # Preview output
                    if self.preview_input != input_idx:
                        self.preview_input = input_idx
                        log.info(f"Preview -> Input {input_idx}")
                        changed = True
        
        return changed
    
    def run(self):
        log.info("TallyPi starting...")
        log.info(f"ATEM: {ATEM_IP}:{ATEM_PORT}")
        log.info(f"Smartview: {SMARTVIEW_IP}:{SMARTVIEW_PORT}")
        log.info(f"Cam 1->MonA (R+G), Cam 2->MonB (R+G), Cam 3->MonA (G), Cam 4->MonB (G)")
        
        self.smartview.connect()
        
        while True:
            if not self.sock:
                if not self.connect_atem():
                    time.sleep(5)
                    continue
            
            try:
                data = self.sock.recv(4096).decode('utf-8', errors='ignore')
                if not data:
                    log.warning("ATEM disconnected")
                    self.sock = None
                    continue
                
                if "VIDEO OUTPUT ROUTING:" in data:
                    sections = data.split("VIDEO OUTPUT ROUTING:")
                    for section in sections[1:]:
                        routing_data = section.split('\n\n')[0]
                        if self.parse_routing(routing_data):
                            self.update_tally()
                            
            except socket.timeout:
                pass
            except Exception as e:
                log.error(f"Error: {e}")
                self.sock = None
                time.sleep(1)


if __name__ == "__main__":
    bridge = TallyBridge()
    bridge.run()
