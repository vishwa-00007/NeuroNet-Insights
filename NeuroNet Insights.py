# Dependencies: pip install pandas matplotlib
import subprocess
import re
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import math
import tkinter as tk
from tkinter import ttk, messagebox
import random
import string
import hashlib
from datetime import datetime
import platform
import time
import itertools

# Simulated wireless adapter list for Aircrack-ng compatibility check
WIRELESS_ADAPTERS = [
    {"name": "wlan0", "monitor_mode": True},
    {"name": "wlan1", "monitor_mode": False},
    {"name": "wlan2", "monitor_mode": True}
]

# Expanded wordlist with common passwords, predictable patterns, and regionally specific phrases
WORDLIST = [
    "password", "123456", "123abc", "admin123", "letmein", "welcome",
    "wifi2023", "secret", "password123", "qwerty",
    "knicksfan2020", "newyorkknicks1234", "yankees2023", "bigapple", "nycrules",
    "Summer2023!", "P@ssw0rd", "john123", "brooklyn99", "nyjetsfan"
]

# Simulated network packet structure
class NetworkPacket:
    def __init__(self, ssid, mac, signal_strength, encryption, data, device_name):
        self.ssid = ssid
        self.mac = mac
        self.signal_strength = signal_strength
        self.encryption = encryption
        self.data = data
        self.device_name = device_name
        self.timestamp = datetime.now()

# Function to get all Wi-Fi adapters
def get_wifi_adapters():
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True, check=True)
        adapters = []
        for line in result.stdout.splitlines():
            match = re.search(r'Name\s+:\s*(.+)', line)
            if match and "Wi-Fi" in match.group(1):
                adapters.append(match.group(1))
        return adapters if adapters else ["Unknown Adapter"]
    except subprocess.SubprocessError as e:
        print(f"Error retrieving adapters: {e}")
        return []

# Function to scan Wi-Fi networks using netsh for a specific adapter
def scan_wifi(adapter):
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'networks', 'mode=bssid'], 
                               capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.SubprocessError as e:
        print(f"Error scanning Wi-Fi on {adapter}: {e}")
        return None

# Function to parse netsh output
def parse_wifi_data(output, adapter):
    networks = []
    current_ssid = None
    current_bssid = None
    current_encryption = None
    debug_log = []
    
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            if line.startswith("SSID"):
                match = re.search(r'SSID \d+ : (.+)', line)
                if match:
                    current_ssid = match.group(1)
                    current_bssid = None
                    current_encryption = None
                else:
                    debug_log.append(f"Unmatched SSID line: {line}")
            elif line.startswith("BSSID") and current_ssid:
                match = re.search(r'BSSID \d+\s*:\s*(.+)', line)
                if match:
                    current_bssid = match.group(1).strip()
                else:
                    debug_log.append(f"Unmatched BSSID line: {line}")
                    current_bssid = "Unknown"
            elif line.startswith("Authentication") and current_ssid:
                match = re.search(r'Authentication\s+:\s*(.+)', line)
                if match:
                    auth = match.group(1).strip()
                    current_encryption = auth if auth in ["WPA2-Personal", "WPA-Personal", "WEP", "Open"] else "Unknown"
                else:
                    debug_log.append(f"Unmatched Authentication line: {line}")
                    current_encryption = "Unknown"
            elif line.startswith("Signal") and current_ssid:
                match = re.search(r'Signal\s+:\s*(\d+)%', line)
                if match:
                    signal_percent = int(match.group(1))
                    rssi = -100 + (signal_percent * 0.7)
                    networks.append({
                        "Adapter": adapter,
                        "SSID": current_ssid,
                        "RSSI": rssi,
                        "Distance (m)": estimate_distance(rssi),
                        "MAC": current_bssid or "Unknown",
                        "Encryption": current_encryption or "Unknown",
                        "Device": current_ssid
                    })
                else:
                    debug_log.append(f"Unmatched Signal line: {line}")
        except Exception as e:
            debug_log.append(f"Error parsing line '{line}': {e}")
    
    if debug_log:
        print("Debug: Unmatched lines in parse_wifi_data:")
        for log in debug_log[:5]:
            print(log)
    
    return networks

# Function to calculate distance from RSSI using FSPL
def estimate_distance(rssi, freq_mhz=2400):
    tx_power = 20
    constant = -27.55
    fspl = tx_power - rssi
    distance = 10 ** ((fspl - 20 * math.log10(freq_mhz) - constant) / 20)
    return round(distance, 2)

# Function to load characters for brute-force attack
def load_characters():
    return [
        "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", 
"p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", 
"Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
        "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+", "-", "=", "{", "}", "[", "]", "|", "\\", ":", ";", "\"", "'", "<", ">", ",", ".", "?", "/", "~", "`",
        "¡", "¢", "£", "¤", "¥", "¦", "§", "¨", "©", "ª", "«", "¬", "®", "¯", "°", "±", "²", "³", "´", "µ", "¶", "·", "¸", "¹", "º", "»", "¼", "½", "¾", "¿",
        " "
    ]

# Aircrack-ng Simulation Functions
def simulate_packet_capture(app, ssid, mac, encryption, device, num_packets=5, output_widget=None, callback=None):
    def capture_step(i=0, captured_packets=[]):
        if i >= num_packets:
            if output_widget:
                output_widget.insert(tk.END, "[*] Packet Capture Complete.\n")
                output_widget.see(tk.END)
            if callback:
                callback(captured_packets)
            return
        
        signal_strength = random.randint(-90, -30)
        data = {"frame_type": random.choice(["Beacon", "Data", "Probe"]), "size": random.randint(50, 1500)}
        packet = NetworkPacket(ssid, mac, signal_strength, encryption, data, device)
        captured_packets.append(packet)
        
        output = f"[+] Captured Packet {i+1}: SSID={packet.ssid}, MAC={packet.mac}, "
        output += f"Signal={packet.signal_strength}dBm, Encryption={packet.encryption}, "
        output += f"Device={packet.device_name}\n"
        
        if output_widget:
            output_widget.insert(tk.END, output)
            output_widget.see(tk.END)
        
        app.root.after(500, capture_step, i+1, captured_packets)
    
    if output_widget:
        output_widget.insert(tk.END, "\n[*] Simulating Packet Capture in Monitor Mode...\n")
        output_widget.insert(tk.END, "[*] Monitor Mode: Adapter listens to all wireless traffic without connecting.\n")
        output_widget.see(tk.END)
    
    capture_step()

def simulate_cracking(app, target_hash, encryption_type, output_widget=None, callback=None, online_mode=True):
    def dictionary_attack(i=0, start_time=None, brute_force=False, length=1, current_attempt=0):
        if start_time is None:
            start_time = time.time()
        
        # Try wordlist first
        if not brute_force:
            if i >= len(WORDLIST):
                output = f"[-] Wordlist Attack Failed after {i} attempts in {time.time() - start_time:.2f} seconds.\n"
                output += "[*] Starting brute-force attack...\n"
                if output_widget:
                    output_widget.insert(tk.END, output)
                    output_widget.see(tk.END)
                # Switch to brute-force
                dictionary_attack(0, start_time, brute_force=True, length=1, current_attempt=i)
                return
            
            word = WORDLIST[i]
            guess_hash = hashlib.md5(word.encode()).hexdigest()
            output = f"[*] Attempt {i+1}/{len(WORDLIST)}: Trying '{word}' (Hash: {guess_hash})\n"
            
            if guess_hash == target_hash:
                elapsed_time = time.time() - start_time
                output += f"[+] Success! Password found: '{word}' in {elapsed_time:.2f} seconds.\n"
                if output_widget:
                    output_widget.insert(tk.END, output)
                    output_widget.see(tk.END)
                if callback:
                    callback(word)
                return
            
            if output_widget:
                output_widget.insert(tk.END, output)
                output_widget.see(tk.END)
            
            delay = 200 if online_mode else 50
            app.root.after(delay, dictionary_attack, i+1, start_time, False)
            return
        
        # Brute-force attack
        characters = load_characters()[:10]  # Limit to first 10 characters for demo
        max_length = 3
        
        if length > max_length:
            elapsed_time = time.time() - start_time
            output = f"[-] Brute-force Attack Failed after {current_attempt} attempts in {elapsed_time:.2f} seconds.\n"
            if output_widget:
                output_widget.insert(tk.END, output)
                output_widget.see(tk.END)
            if callback:
                callback(None)
            return
        
        for combination in itertools.product(characters, repeat=length):
            current_attempt += 1
            password = ''.join(combination)
            guess_hash = hashlib.md5(password.encode()).hexdigest()
            
            if current_attempt % 100 == 0:
                output = f"[*] Brute-force Attempt {current_attempt}: Trying '{password}' (Hash: {guess_hash})\n"
                if output_widget:
                    output_widget.insert(tk.END, output)
                    output_widget.see(tk.END)
            
            if guess_hash == target_hash:
                elapsed_time = time.time() - start_time
                output = f"[+] Success! Password found: '{password}' in {elapsed_time:.2f} seconds.\n"
                if output_widget:
                    output_widget.insert(tk.END, output)
                    output_widget.see(tk.END)
                if callback:
                    callback(password)
                return
            
            if current_attempt % 100 == 0:
                app.root.update()
        
        app.root.after(50, dictionary_attack, 0, start_time, True, length + 1, current_attempt)
    
    if output_widget:
        mode = "Online" if online_mode else "Offline"
        output_widget.insert(tk.END, f"\n[*] Simulating {encryption_type} {mode} Dictionary Attack...\n")
        if online_mode:
            output_widget.insert(tk.END, "[*] Unlimited attempts with slower delay to simulate network latency.\n")
        else:
            output_widget.insert(tk.END, "[*] Offline mode: Unlimited attempts (assuming access to password hash).\n")
            output_widget.insert(tk.END, "[*] Using wordlist with common passwords, regional phrases, and leaked password patterns.\n")
        output_widget.see(tk.END)
    
    if encryption_type in ["WPA", "WPA2", "WPA2-Personal", "WPA-Personal"]:
        dictionary_attack()
    else:
        output = f"[-] {encryption_type} not supported for dictionary attack. Use WEP for brute-force instead.\n"
        if output_widget:
            output_widget.insert(tk.END, output)
            output_widget.see(tk.END)
        if callback:
            callback(None)

def simulate_packet_injection(app, target_mac, output_widget=None, callback=None):
    def injection_step(i=0, max_injections=3):
        if i >= max_injections:
            output = "[*] Injection Complete. AP may respond with additional packets.\n"
            if output_widget:
                output_widget.insert(tk.END, output)
                output_widget.see(tk.END)
            if callback:
                callback()
            return
        
        packet = {
            "type": "ARP",
            "target_mac": target_mac,
            "source_mac": ":".join(["".join(random.choices(string.hexdigits.lower(), k=2)) for _ in range(6)]),
            "data": f"Crafted ARP Packet #{i+1}"
        }
        output = f"[+] Injecting Packet: {packet}\n"
        
        if output_widget:
            output_widget.insert(tk.END, output)
            output_widget.see(tk.END)
        
        app.root.after(500, injection_step, i+1, max_injections)
    
    if output_widget:
        output_widget.insert(tk.END, f"\n[*] Simulating Packet Injection to MAC: {target_mac}\n")
        output_widget.insert(tk.END, "[*] Goal: Inject malformed/repeated packets to provoke AP responses.\n")
        output_widget.see(tk.END)
    
    injection_step()

def simulate_deauth_attack(app, target_mac, ap_mac, output_widget=None, callback=None):
    def deauth_step(i=0, max_deauths=3):
        if i >= max_deauths:
            output = "[*] Deauth Attack Complete. Client likely disconnected.\n"
            if output_widget:
                output_widget.insert(tk.END, output)
                output_widget.see(tk.END)
            if callback:
                callback()
            return
        
        output = f"[+] Sending Deauth Packet {i+1} to {target_mac} from {ap_mac}\n"
        if output_widget:
            output_widget.insert(tk.END, output)
            output_widget.see(tk.END)
        
        app.root.after(300, deauth_step, i+1, max_deauths)
    
    if output_widget:
        output_widget.insert(tk.END, "\n[*] Simulating Deauthentication Attack...\n")
        output_widget.insert(tk.END, f"[*] Target Client: {target_mac}, AP: {ap_mac}\n")
        output_widget.insert(tk.END, "[*] Goal: Force client to disconnect and re-authenticate to capture handshake.\n")
        output_widget.see(tk.END)
    
    deauth_step()

def check_adapters(output_widget=None):
    output = "\n[*] Simulating Wireless Adapter Compatibility Check...\n"
    output += "[*] Checking for monitor mode support...\n"
    
    compatible_adapters = []
    for adapter in WIRELESS_ADAPTERS:
        status = "Supported" if adapter["monitor_mode"] else "Not Supported"
        output += f"[*] Adapter {adapter['name']}: Monitor Mode {status}\n"
        if adapter["monitor_mode"]:
            compatible_adapters.append(adapter)
    
    if output_widget:
        output_widget.insert(tk.END, output)
        output_widget.see(tk.END)
    return compatible_adapters

def simulate_real_time_monitoring(app, ssid, mac, encryption, device, duration=5, output_widget=None, callback=None):
    def monitoring_step(start_time, elapsed=0):
        if elapsed >= duration:
            output = "[*] Monitoring Stopped.\n"
            if output_widget:
                output_widget.insert(tk.END, output)
                output_widget.see(tk.END)
            if callback:
                callback()
            return
        
        signal_strength = random.randint(-90, -30)
        output = f"[+] {datetime.now()}: SSID={ssid}, MAC={mac}, Signal={signal_strength}dBm, "
        output += f"Encryption={encryption}, Device={device}\n"
        
        if output_widget:
            output_widget.insert(tk.END, output)
            output_widget.see(tk.END)
        
        elapsed = time.time() - start_time
        app.root.after(500, monitoring_step, start_time, elapsed)
    
    if output_widget:
        output_widget.insert(tk.END, "\n[*] Simulating Real-Time Network Monitoring...\n")
        output_widget.insert(tk.END, "[*] Displaying live packet traffic (SSIDs, signal, encryption)...\n")
        output_widget.see(tk.END)
    
    monitoring_step(time.time())

def print_attacks_summary(output_widget=None):
    output = "\n[*] Common Aircrack-ng Attacks Summary\n"
    output += "=====================================\n"
    output += "# ARP Replay Attack (WEP)\n"
    output += "- Captures and replays ARP packets to generate new IVs.\n"
    output += "- Speeds up WEP cracking by increasing data traffic.\n"
    output += "\n# Deauthentication Attack (WPA Handshake)\n"
    output += "- Sends deauth packets to force client reconnection.\n"
    output += "- Captures WPA 4-way handshake for cracking.\n"
    output += "\n# Dictionary Attacks (WPA/WPA2)\n"
    output += "- Tests passwords from a wordlist, followed by brute-force if needed.\n"
    output += "- Online: Unlimited attempts with slower delay; Offline: Faster attempts with hash access.\n"
    
    if output_widget:
        output_widget.insert(tk.END, output)
        output_widget.see(tk.END)

# Tkinter GUI class with SaaS-style network analytics dashboard theme
class WiFiScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Network Analytics Dashboard")
        self.root.configure(bg="#2c3e50")  # Blue-gray background
        self.directions = [0, 45, 90, 135, 180, 225, 270, 315]
        self.current_direction_index = 0
        self.all_networks = []
        self.adapters = get_wifi_adapters()
        self.selected_network = None
        self.last_update_time = 0  # For throttling radar updates
        
        # Sidebar menu
        self.sidebar = tk.Frame(root, bg="#34495e", width=200)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        
        # Sidebar menu items
        menu_items = ["Applications", "Users", "Categories", "Domains"]
        for item in menu_items:
            btn = tk.Button(self.sidebar, text=item, bg="#34495e", fg="#ecf0f1", 
                           font=("Arial", 12), bd=0, anchor="w", 
                           command=lambda x=item: self.switch_tab(x))
            btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Main content area
        self.main_frame = tk.Frame(root, bg="#2c3e50")
        self.main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Top bar
        self.top_frame = tk.Frame(self.main_frame, bg="#34495e")
        self.top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.status_label = tk.Label(self.top_frame, text=f"Adapters: {', '.join(self.adapters) or 'None'} | Click 'Scan' to start at 0°", 
                                    font=("Arial", 12), fg="#ecf0f1", bg="#34495e")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.scan_button = tk.Button(self.top_frame, text="Scan", 
                                    bg="#3498db", fg="#ecf0f1", font=("Arial", 12, "bold"),
                                    bd=0, command=self.scan_and_update)
        self.scan_button.pack(side=tk.RIGHT, padx=5)
        
        self.attack_button = tk.Button(self.top_frame, text="Run Simulation", 
                                     bg="#3498db", fg="#ecf0f1", font=("Arial", 12, "bold"),
                                     bd=0, command=self.run_aircrack_simulation, state="disabled")
        self.attack_button.pack(side=tk.RIGHT, padx=5)
        
        # Content panels
        self.content_frame = tk.Frame(self.main_frame, bg="#2c3e50")
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.left_panel = tk.Frame(self.content_frame, bg="#2c3e50")
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.right_panel = tk.Frame(self.content_frame, bg="#2c3e50")
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Radar-style canvas with concentric circles and sweep
        self.radar_canvas = tk.Canvas(self.left_panel, width=300, height=300, bg="#2c3e50", highlightthickness=0)
        self.radar_canvas.pack(pady=10)
        self.root.after(100, self.draw_radar)  # Delay initial draw
        
        # Stats panel
        self.stats_frame = tk.Frame(self.left_panel, bg="#34495e")
        self.stats_frame.pack(fill=tk.X, pady=10)
        
        # Real-time stats
        self.gps_label = tk.Label(self.stats_frame, text="Location: 40.7128°N, 74.0060°W", font=("Arial", 10), fg="#ecf0f1", bg="#34495e")
        self.gps_label.pack(anchor="w", padx=5)
        self.packet_rate_label = tk.Label(self.stats_frame, text="Packet Rate: 0.0 pkt/s", font=("Arial", 10), fg="#ecf0f1", bg="#34495e")
        self.packet_rate_label.pack(anchor="w", padx=5)
        self.cog_label = tk.Label(self.stats_frame, text="COG: 0°", font=("Arial", 10), fg="#ecf0f1", bg="#34495e")
        self.cog_label.pack(anchor="w", padx=5)
        self.hdg_label = tk.Label(self.stats_frame, text="HDG: 0°", font=("Arial", 10), fg="#ecf0f1", bg="#34495e")
        self.hdg_label.pack(anchor="w", padx=5)
        self.time_label = tk.Label(self.stats_frame, text=f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                                 font=("Arial", 10), fg="#ecf0f1", bg="#34495e")
        self.time_label.pack(anchor="w", padx=5)
        
        # Network table
        self.tree = ttk.Treeview(self.right_panel, columns=("Adapter", "SSID", "RSSI", "Distance", "Direction", "MAC", "Encryption", "Device"), 
                                show="headings", style="Custom.Treeview")
        self.tree.heading("Adapter", text="Adapter")
        self.tree.heading("SSID", text="SSID")
        self.tree.heading("RSSI", text="RSSI (dBm)")
        self.tree.heading("Distance", text="Distance (m)")
        self.tree.heading("Direction", text="Direction (°)")
        self.tree.heading("MAC", text="MAC")
        self.tree.heading("Encryption", text="Encryption")
        self.tree.heading("Device", text="Device")
        
        self.tree.column("Adapter", width=100)
        self.tree.column("SSID", width=120)
        self.tree.column("RSSI", width=80)
        self.tree.column("Distance", width=100)
        self.tree.column("Direction", width=100)
        self.tree.column("MAC", width=120)
        self.tree.column("Encryption", width=100)
        self.tree.column("Device", width=120)
        
        scrollbar = ttk.Scrollbar(self.right_panel, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<<TreeviewSelect>>', self.on_network_select)
        
        # Bottom panels for charts and output
        self.bottom_frame = tk.Frame(self.main_frame, bg="#2c3e50")
        self.bottom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.bottom_left = tk.Frame(self.bottom_frame, bg="#34495e")
        self.bottom_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.bottom_right = tk.Frame(self.bottom_frame, bg="#34495e")
        self.bottom_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Donut chart for signal strength
        self.fig, self.ax = plt.subplots(figsize=(6, 6))
        self.fig.patch.set_facecolor('#2c3e50')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.bottom_left)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.output_text = tk.Text(self.bottom_right, height=10, wrap=tk.WORD, bg="#34495e", fg="#ecf0f1", 
                                 font=("Arial", 10), bd=0)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        output_scrollbar = ttk.Scrollbar(self.bottom_right, orient="vertical", command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=output_scrollbar.set)
        output_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Custom style for Treeview
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Custom.Treeview", background="#34495e", foreground="#ecf0f1", 
                       fieldbackground="#34495e", font=("Arial", 10))
        style.configure("Custom.Treeview.Heading", background="#2c3e50", foreground="#ecf0f1", 
                       font=("Arial", 10, "bold"))
        style.map("Custom.Treeview", background=[('selected', '#3498db')], foreground=[('selected', '#ecf0f1')])
        
        # Bind resize event
        self.root.bind("<Configure>", self.on_resize)
        
        if not self.adapters or self.adapters == ["Unknown Adapter"]:
            self.scan_button.config(state="disabled")
            self.status_label.config(text="No Wi-Fi adapters detected. Please enable Wi-Fi or connect a compatible adapter.")

    def on_resize(self, event):
        if time.time() - self.last_update_time > 0.1:  # Throttle updates
            self.draw_radar()
            self.update_plot()
            self.last_update_time = time.time()

    def switch_tab(self, tab_name):
        self.status_label.config(text=f"Viewing {tab_name} | Adapters: {', '.join(self.adapters)}")

    def draw_radar(self):
        self.radar_canvas.delete("all")
        width = max(self.radar_canvas.winfo_width(), 100)
        height = max(self.radar_canvas.winfo_height(), 100)
        center_x, center_y = width // 2, height // 2
        max_radius = min(width, height) * 0.4
        
        # Draw concentric circles
        for i in range(1, 5):
            radius = max_radius * (i / 4)
            self.radar_canvas.create_oval(center_x - radius, center_y - radius,
                                        center_x + radius, center_y + radius,
                                        outline="#ecf0f1", width=1)
        
        # Draw grid lines
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x = center_x + max_radius * math.sin(rad)
            y = center_y - max_radius * math.cos(rad)
            self.radar_canvas.create_line(center_x, center_y, x, y, fill="#ecf0f1", dash=(2, 2))
        
        # Draw compass directions
        cardinals = ["N", "E", "S", "W"]
        for i, direction in enumerate(cardinals):
            angle = math.radians(i * 90)
            x = center_x + max_radius * 1.1 * math.sin(angle)
            y = center_y - max_radius * 1.1 * math.cos(angle)
            self.radar_canvas.create_text(x, y, text=direction, font=("Arial", 12, "bold"), fill="#ecf0f1")
        
        # Draw rotating sweep
        current_angle = math.radians(self.directions[self.current_direction_index])
        sweep_len = max_radius
        end_x = center_x + sweep_len * math.sin(current_angle)
        end_y = center_y - sweep_len * math.cos(current_angle)
        self.radar_canvas.create_line(center_x, center_y, end_x, end_y,
                                    fill="#3498db", width=5, stipple="gray50")
        
        # Draw signal blips (limit to 50)
        for network in self.all_networks[:50]:
            rssi = network["RSSI"]
            direction = math.radians(network["Direction"])
            norm_strength = min(max((rssi + 30) / 70, 0), 1)
            radius = max_radius * (1 - norm_strength)
            x = center_x + radius * math.sin(direction)
            y = center_y - radius * math.cos(direction)
            color = random.choice(["#e74c3c", "#3498db", "#f1c40f", "#9b59b6"])  # Red, Blue, Yellow, Purple
            self.radar_canvas.create_oval(x-5, y-5, x+5, y+5, fill=color)
        
        self.radar_canvas.create_text(center_x, center_y + max_radius * 1.2,
                                    text=f"{self.directions[self.current_direction_index]}°",
                                    font=("Arial", 14, "bold"), fill="#ecf0f1")

    def update_gps_view(self):
        # Update stats with simulated packet rate
        self.time_label.config(text=f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.cog_label.config(text=f"COG: {self.directions[self.current_direction_index]}°")
        self.hdg_label.config(text=f"HDG: {self.directions[self.current_direction_index]}°")
        packet_rate = random.uniform(10.0, 50.0)  # Simulate packet rate
        self.packet_rate_label.config(text=f"Packet Rate: {packet_rate:.1f} pkt/s")

    def scan_and_update(self):
        if not self.adapters or self.adapters == ["Unknown Adapter"]:
            messagebox.showwarning("No Adapters", "No valid Wi-Fi adapters detected. Please enable Wi-Fi or connect a compatible adapter.")
            return
        
        direction = self.directions[self.current_direction_index]
        self.status_label.config(text=f"Adapters: {', '.join(self.adapters)} | Scanning at {direction}°...")
        self.root.update()
        
        any_networks = False
        for adapter in self.adapters:
            output = scan_wifi(adapter)
            if output:
                networks = parse_wifi_data(output, adapter)
                if networks:
                    any_networks = True
                for network in networks:
                    network['Direction'] = direction
                    self.all_networks.append(network)
            else:
                messagebox.showwarning("Scan Failed", f"Failed to scan Wi-Fi networks on adapter {adapter}. Please ensure Wi-Fi is enabled and you have sufficient permissions.")
        
        if not any_networks and not self.all_networks:
            self.status_label.config(text=f"Adapters: {', '.join(self.adapters)} | No networks found at {direction}°")
        
        self.tree.delete(*self.tree.get_children())
        for network in self.all_networks:
            self.tree.insert("", "end", values=(
                network["Adapter"],
                network["SSID"],
                network["RSSI"],
                network["Distance (m)"],
                network["Direction"],
                network["MAC"],
                network["Encryption"],
                network["Device"]
            ))
        
        self.draw_radar()
        self.update_gps_view()
        self.update_plot()
        
        self.current_direction_index += 1
        if self.current_direction_index < len(self.directions):
            self.status_label.config(text=f"Adapters: {', '.join(self.adapters)} | Rotate to {self.directions[self.current_direction_index]}° and click 'Scan'")
        else:
            self.status_label.config(text=f"Adapters: {', '.join(self.adapters)} | Scanning complete!")
            self.scan_button.config(state="disabled")
            self.attack_button.config(state="normal")

    def update_plot(self):
        self.ax.clear()
        df = pd.DataFrame(self.all_networks)
        try:
            # Validate DataFrame
            if not df.empty and all(col in df.columns for col in ['SSID', 'RSSI']):
                # Ensure RSSI is numeric and within valid range (-100 to -30 dBm)
                df['RSSI'] = pd.to_numeric(df['RSSI'], errors='coerce')
                df = df.dropna(subset=['SSID', 'RSSI'])
                df = df[(df['RSSI'] >= -100) & (df['RSSI'] <= -30)]
                
                if not df.empty:
                    top_ssids = df.groupby('SSID')['RSSI'].mean().nlargest(5)
                    if not top_ssids.empty:
                        colors = ['#e74c3c', '#3498db', '#f1c40f', '#9b59b6', '#2ecc71']
                        def autopct_format(pct):
                            return f'{pct:.1f}%' if pct > 0 else ''
                        wedges, _, autotexts = self.ax.pie(
                            top_ssids, 
                            labels=top_ssids.index, 
                            colors=colors, 
                            startangle=90, 
                            counterclock=False, 
                            autopct=autopct_format,
                            textprops={'color': '#ecf0f1'}
                        )
                        self.ax.set_title("Top Networks by Signal Strength", color="#ecf0f1")
                        centre_circle = plt.Circle((0, 0), 0.70, fc='#2c3e50')
                        self.ax.add_patch(centre_circle)
                        for autotext in autotexts:
                            autotext.set_color('#ecf0f1')
                    else:
                        self.ax.text(0.5, 0.5, 'No Valid Networks', 
                                    horizontalalignment='center', 
                                    verticalalignment='center', 
                                    color='#ecf0f1', fontsize=12)
                else:
                    self.ax.text(0.5, 0.5, 'No Valid Data', 
                                horizontalalignment='center', 
                                verticalalignment='center', 
                                color='#ecf0f1', fontsize=12)
            else:
                self.ax.text(0.5, 0.5, 'No Data Available', 
                            horizontalalignment='center', 
                            verticalalignment='center', 
                            color='#ecf0f1', fontsize=12)
        except Exception as e:
            print(f"Error updating plot: {e}")
            self.ax.text(0.5, 0.5, 'Plot Error', 
                        horizontalalignment='center', 
                        verticalalignment='center', 
                        color='#ecf0f1', fontsize=12)
        self.ax.set_facecolor('#34495e')
        self.fig.set_facecolor('#2c3e50')
        self.canvas.draw()

    def on_network_select(self, event):
        selected_items = self.tree.selection()
        if selected_items:
            try:
                item = self.tree.item(selected_items[0])
                if item['values']:
                    self.selected_network = item['values']
                    self.attack_button.config(state="normal")
            except Exception as e:
                print(f"Error selecting network: {e}")
                self.selected_network = None
                self.attack_button.config(state="disabled")

    def run_aircrack_simulation(self):
        if not self.selected_network:
            messagebox.showwarning("No Network Selected", "Please select a network from the table to run the simulation.")
            return
        
        self.output_text.delete(1.0, tk.END)
        ssid = self.selected_network[1]
        mac = self.selected_network[5] if self.selected_network[5] != "Unknown" else "00:11:22:33:44:55"
        encryption = self.selected_network[6] if self.selected_network[6] != "Unknown" else random.choice(["WEP", "WPA", "WPA2"])
        device = self.selected_network[7]
        adapter = self.selected_network[0]
        
        self.output_text.insert(tk.END, f"[*] Targeting Device: {device} (SSID: {ssid}, MAC: {mac})\n")
        self.output_text.see(tk.END)
        
        # Capture and display netsh output
        netsh_output = scan_wifi(adapter)
        if netsh_output:
            self.output_text.insert(tk.END, "\n[*] Captured 'netsh wlan show networks mode=bssid' Output:\n")
            self.output_text.insert(tk.END, netsh_output[:500] + ("...\n" if len(netsh_output) > 500 else "\n"))
            self.output_text.see(tk.END)
        else:
            self.output_text.insert(tk.END, "\n[-] Failed to capture 'netsh wlan show networks mode=bssid' output.\n")
            self.output_text.see(tk.END)
        
        def step1():
            compatible_adapters = check_adapters(self.output_text)
            if not compatible_adapters:
                self.output_text.insert(tk.END, "[-] No adapters support monitor mode. Simulation stopped.\n")
                self.output_text.see(tk.END)
                return
            step2()
        
        def step2():
            def packet_callback(packets):
                step3()
            simulate_packet_capture(self, ssid, mac, encryption, device, output_widget=self.output_text, callback=packet_callback)
        
        def step3():
            def crack_callback(password):
                if password:
                    self.output_text.insert(tk.END, f"[+] Cracked Password for {device} (SSID: {ssid}): {password}\n")
                else:
                    self.output_text.insert(tk.END, f"[-] Failed to crack password for {device} (SSID: {ssid})\n")
                self.output_text.see(tk.END)
                step4()
            target_hash = hashlib.md5("wifi2023".encode()).hexdigest()
            self.output_text.insert(tk.END, "\n[*] Running Dictionary Attack...\n")
            simulate_cracking(self, target_hash, encryption, self.output_text, crack_callback, online_mode=True)
        
        def step4():
            def injection_callback():
                step5()
            simulate_packet_injection(self, mac, self.output_text, injection_callback)
        
        def step5():
            def deauth_callback():
                step6()
            ap_mac = "AA:BB:CC:DD:EE:FF"
            simulate_deauth_attack(self, mac, ap_mac, self.output_text, deauth_callback)
        
        def step6():
            def monitoring_callback():
                step7()
            simulate_real_time_monitoring(self, ssid, mac, encryption, device, output_widget=self.output_text, callback=monitoring_callback)
        
        def step7():
            print_attacks_summary(self.output_text)
        
        step1()

def main():
    if platform.system() != "Windows":
        tk.Tk().withdraw()
        messagebox.showerror("Platform Error", "This application requires Windows due to 'netsh' dependency. Please run on a Windows system with Wi-Fi enabled and sufficient permissions.")
        return
    
    root = tk.Tk()
    root.geometry("1200x900")
    app = WiFiScannerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()