# HybridServerGUI.py
# Unified single Conda shell for both commands and server output

import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time
import queue
import socketio
# ---------------- CONFIG ----------------
CONDA_ENV = "cast"  # name of your environment
APP_DIR =  "AppData"
MAIN_FILE = "srvrauto.py"
PID_FILE = "server.pid"
  # your Flask-SocketIO URL
# ----------------------------------------

class HybridServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Screen rendrer Control")
        self.root.geometry("1000x600")
        self.root.configure(bg="#1e1e1e")
        self.socket_connected = False
        self.SOCKET_URL = None
        self.reconnect_attempts = 0

        self.root._name = "root_window"
        self.q = queue.Queue()

        # ======== Unified Conda Shell Frame ========
        shell_frame = ttk.LabelFrame(self.root, text="Conda Shell + Server Output", name="shell_frame")
        shell_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.shell_output = scrolledtext.ScrolledText(
            shell_frame, wrap=tk.WORD, height=25, bg="#000", fg="#0f0",
            font=("Consolas", 10), name="shell_output"
        )
        self.shell_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.shell_input = tk.Entry(
            shell_frame, bg="#222", fg="#fff", font=("Consolas", 10), name="shell_input"
        )
        self.shell_input.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.shell_input.bind("<Return>", self.run_shell_command)

        # ======== Toolbar ========
        toolbar = tk.Frame(self.root, bg="#1e1e1e", name="toolbar")
        toolbar.pack(fill=tk.X, pady=6)

        button_cfg = {"width": 14, "fg": "white", "relief": "flat", "font": ("Segoe UI", 9, "bold")}
        self.start_btn = tk.Button(toolbar, text="Start Server", bg="#4CAF50",
                                   command=self.start_server, name="start_button", **button_cfg)
        self.start_btn.grid(row=0, column=0, padx=6)
        self.stop_btn = tk.Button(toolbar, text="Stop Server", bg="#F44336",
                                  command=self.stop_server, name="stop_button", **button_cfg)
        self.stop_btn.grid(row=0, column=1, padx=6)
        self.restart_btn = tk.Button(toolbar, text="Restart Server", bg="#FF9800",
                                     command=self.restart_server, name="restart_button", **button_cfg)
        self.restart_btn.grid(row=0, column=2, padx=6)
        self.status_btn = tk.Button(toolbar, text="Check Status", bg="#2196F3",
                                    command=self.check_status, name="status_button", **button_cfg)
        self.status_btn.grid(row=0, column=3, padx=6)

        self.proc = None
        self.stop_event = threading.Event()

        # Start unified Conda shell
        self.init_conda_shell()

    def update_button_states(self,server_running):
        """Enable/disable control buttons based on server state."""
        if server_running:
            self.start_btn.config(state=tk.DISABLED, bg="#2E7D32")
            self.stop_btn.config(state=tk.NORMAL, bg="#F44336")
            self.restart_btn.config(state=tk.NORMAL, bg="#FF9800")
        else:
            self.start_btn.config(state=tk.NORMAL, bg="#4CAF50")
            self.stop_btn.config(state=tk.DISABLED, bg="#5C5C5C")
            self.restart_btn.config(state=tk.DISABLED, bg="#5C5C5C")

    
    
    # =========================================================
    # =============== Conda Shell + Server Output ==============
    # =========================================================
    def init_conda_shell(self):
        # Force UTF-8 encoding in the CMD session
        cmd = f'cmd.exe /U /k "chcp 65001 >nul && set PYTHONIOENCODING=utf-8 && conda activate {CONDA_ENV}"'
        self.shell_proc = subprocess.Popen(
            cmd, shell=True, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="ignore"
        )
        threading.Thread(target=self.stream_shell_output, daemon=True).start()
        self.log_code(f"[INFO] Conda environment '{CONDA_ENV}' initialized (UTF-8 mode).")
    
    def stream_shell_output(self):
        for line in self.shell_proc.stdout:
            self.shell_output.insert(tk.END, line)
            self.shell_output.see(tk.END)

    def run_shell_command(self, event=None, cmd=None):
        """Send command to Conda shell (from input or button)."""
        if not cmd:  # If called by Enter key
            cmd = self.shell_input.get().strip()
        if not cmd:
            return

        self.shell_output.insert(tk.END, f"> {cmd}\n", ("code",))
        self.shell_proc.stdin.write(cmd + "\n")
        self.shell_proc.stdin.flush()
        self.shell_input.delete(0, tk.END)
        self.log_code(f"Executed command: {cmd}")

        

    # =========================================================
    # ================= Server Controls =======================
    # =========================================================
    def start_server(self):
        self.log_code("[Button] Starting Server")
        app_path = os.path.join(APP_DIR, MAIN_FILE)
        self.run_shell_command(cmd=f"python {app_path}")
        self.update_button_states(True)

    def stop_server(self):
        self.log_code("[Button] Stop Server clicked")
        try:
            import requests
            resp = requests.post(f"{self.SOCKET_URL}/shutdown", timeout=2)
            if resp.status_code == 200:
                self.log_code("🛑 Casting server stopped successfully.")
            else:
                self.log_code(f"⚠️ Shutdown returned: {resp.status_code}")
        except requests.exceptions.ConnectionError:
            self.log_code("❌ Casting servernot reachable — may already be stopped.")
        except Exception as e:
            self.log_code(f"⚠️ Stop error: {e}")
        self.update_button_states(False)

    def restart_server(self):
        self.log_code("🔁 Restarting server...")
        try:
            self.stop_server()
            time.sleep(2)
            self.start_server()
            self.log_code("✅ Server restarted successfully.")
        except Exception as e:
            self.log_code(f"❌ Restart failed: {e}")

    def check_status(self):
        """Check socket connection status only."""
        self.log_code("[Button] Check Status clicked")
        if self.socket_connected:
            self.log_code("🟢 Socket connected — server is alive.")
        else:
            self.log_code("🔴 Socket disconnected — attempting reconnect...")
            self.handle_socket_disconnect()
    
    # def check_status(self): old/OLD
    #     self.log_code("[Button] Check Status clicked")
    #     self.run_shell_command(cmd="tasklist | find \"python\"")
    
    # =========================================================
    # ================= Stream Server Output ==================
    # =========================================================
    def safe_insert(self, tag, text):
        try:
            self.shell_output.insert(tk.END, text, (tag,))
        except UnicodeEncodeError:
            self.shell_output.insert(tk.END, text.encode('utf-8', 'replace').decode('utf-8'), (tag,))
    def stream_shell_output(self):
        for raw in self.shell_proc.stdout:
            line = raw.replace("\r", "")
            tag = "server"
            self.safe_insert(tag, f"[SERVER] {line}")
            self.shell_output.tag_config(tag, foreground="#00BFFF")
            self.shell_output.see(tk.END)
            # Detect Flask startup line dynamically
            if "wsgi starting up on http://" in line.lower():
                import re
                match = re.search(r"http://0\.0\.0\.0:(\d+)", line)
                if match:
                    port = match.group(1)
                    if not hasattr(self, "socket_monitor_started"):
                        self.socket_monitor_started = True
                        self.log_code(f"✅ Flask detected running on port {port}. Starting SocketIO monitor...")
                        self.root.after(1000, lambda: self.init_socket_monitor(port))


    # =========================================================
    # ================= Log Helpers ===========================
    # =========================================================
    def log_code(self, msg):
        self.shell_output.insert(tk.END, f"[CODE] {msg}\n", ("code",))
        self.shell_output.tag_config("code", foreground="#00FF00")
        self.shell_output.see(tk.END)


    def log_server(self, msg):
        self.shell_output.insert(tk.END, f"[SERVER] {msg}\n", ("server",))
        self.shell_output.tag_config("server", foreground="#00BFFF")
        self.shell_output.see(tk.END)

    # =========================================================
    # ================== SocketIO Monitor =====================
    # =========================================================
    def init_socket_monitor(self, port):
        
        self.SOCKET_URL= f"http://127.0.0.1:{port}"
        self.socket_connected = False
        self.sio = socketio.Client()

        @self.sio.event
        def connect():
            self.log_code("🟢 Socket connected to Casting server.")
            self.socket_connected = True
        @self.sio.event
        def disconnect():
            self.log_code("🔴 Socket disconnected.")
            self.socket_connected = False
            self.handle_socket_disconnect()

        @self.sio.event
        def connect_error(data):
            self.log_code(f"⚠️ Socket connection error: {data}")
            self.socket_connected = False
            self.handle_socket_disconnect()

        def connect_thread():
            for attempt in range(1, 6):
                try:
                    self.log_code(f"⌛ Attempting SocketIO connection ({attempt}/5)...")
                    self.sio.connect(self.SOCKET_URL, wait_timeout=5, transports=["websocket"])
                    self.sio.wait()
                    return
                except Exception as e:
                    self.log_code(f"⚠️ Attempt {attempt} failed: {e}")
                    time.sleep(3)
            self.log_code("❌ Could not connect to Flask-SocketIO after 5 attempts.")

        threading.Thread(target=connect_thread, daemon=True).start()
    def handle_socket_disconnect(self):
        """Try to reconnect or restart the Casting server."""
        self.reconnect_attempts += 1
        if self.reconnect_attempts <= 3:
            self.log_code(f"⚠️ Attempting socket reconnect ({self.reconnect_attempts}/3)...")
            try:
                self.sio.connect(self.SOCKET_URL, wait_timeout=5)
                return
            except Exception as e:
                self.log_code(f"❌ Reconnect failed: {e}")
        else:
            self.log_code("❌ Casting server socket unresponsive — restarting server.")
            self.restart_server()
            self.reconnect_attempts = 0


if __name__ == "__main__":
    try:
        import psutil
    except ImportError:
        messagebox.showerror("Missing Dependency", "Please install psutil: conda install psutil")
        exit(1)

    root = tk.Tk()
    app = HybridServerGUI(root)
    root.mainloop()