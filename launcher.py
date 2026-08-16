"""
Word Format Batch Editor - GUI Launcher
System tray application for managing the server.
"""

import os
import sys
import subprocess
import threading
import webbrowser
import time
from pathlib import Path

# Try to import pystray, fall back to tkinter-only if not available
try:
    import pystray
    from pystray import MenuItem as item
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

import tkinter as tk
from tkinter import ttk, messagebox


def _enable_dpi_awareness():
    """Enable per-monitor DPI awareness on Windows so the GUI scales on HiDPI screens."""
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


class ServerManager:
    """Manages the FastAPI server process."""
    
    def __init__(self):
        self.process = None
        self.running = False
        self.base_dir = Path(__file__).parent
        
    def find_python(self):
        """Find the Python executable."""
        for cmd in [sys.executable, 'python', 'python3', 'py']:
            try:
                result = subprocess.run(
                    [cmd, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return cmd
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return sys.executable
    
    def start(self):
        """Start the server."""
        if self.running:
            return True
        try:
            import socket
            with socket.create_connection(("127.0.0.1", 8000), timeout=0.5):
                return True
        except OSError:
            pass
        python_cmd = self.find_python()
        
        # Start uvicorn
        cmd = [
            python_cmd, '-m', 'uvicorn',
            'backend.main:app',
            '--host', '0.0.0.0',
            '--port', '8000'
        ]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=str(self.base_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            self.running = True
            
            # Wait for server to start
            time.sleep(2)
            
            if self.process.poll() is not None:
                self.running = False
                return False
            
            return True
        except Exception as e:
            print(f"Failed to start server: {e}")
            return False
    
    def stop(self):
        """Stop the server."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None
            self.running = False
    
    def is_running(self):
        """Check if server is running."""
        if self.process:
            return self.process.poll() is None
        return False


class App:
    """Main GUI application."""
    
    def __init__(self):
        _enable_dpi_awareness()
        self.server = ServerManager()
        self.root = tk.Tk()
        self.root.title("Word Format Batch Editor")

        # Scale base window (400x300) by DPI factor on HiDPI screens
        try:
            dpi_scale = self.root.winfo_fpixels('1i') / 96.0
            if dpi_scale < 1.0:
                dpi_scale = 1.0
            win_w = int(400 * dpi_scale)
            win_h = int(300 * dpi_scale)
        except Exception:
            dpi_scale = 1.0
            win_w, win_h = 400, 300

        self.dpi_scale = dpi_scale
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.resizable(False, False)
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - win_w) // 2
        y = (self.root.winfo_screenheight() - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        
        self.setup_ui()
        self.setup_tray()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Update status periodically
        self.update_status()
    
    def setup_ui(self):
        """Setup the GUI."""
        s = self.dpi_scale  # font size multiplier for HiDPI screens

        # Main frame
        main_frame = ttk.Frame(self.root, padding=int(20 * s))
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Word Format Batch Editor",
            font=("Helvetica", int(16 * s), "bold")
        )
        title_label.pack(pady=(0, int(20 * s)))
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Server Status", padding=int(10 * s))
        status_frame.pack(fill=tk.X, pady=(0, int(20 * s)))
        
        self.status_label = ttk.Label(
            status_frame,
            text="● Stopped",
            font=("Helvetica", int(12 * s)),
            foreground="red"
        )
        self.status_label.pack()
        
        self.url_label = ttk.Label(
            status_frame,
            text="http://localhost:8000",
            font=("Helvetica", int(10 * s)),
            foreground="gray"
        )
        self.url_label.pack(pady=(int(5 * s), 0))
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, int(10 * s)))
        
        self.start_btn = ttk.Button(
            btn_frame,
            text="Start Server",
            command=self.start_server
        )
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, int(5 * s)))
        
        self.stop_btn = ttk.Button(
            btn_frame,
            text="Stop Server",
            command=self.stop_server,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(int(5 * s), 0))
        
        # Open browser button
        self.open_btn = ttk.Button(
            main_frame,
            text="Open in Browser",
            command=self.open_browser,
            state=tk.DISABLED
        )
        self.open_btn.pack(fill=tk.X, pady=(0, int(10 * s)))
        
        # Minimize to tray button
        if HAS_TRAY:
            self.tray_btn = ttk.Button(
                main_frame,
                text="Minimize to Tray",
                command=self.minimize_to_tray
            )
            self.tray_btn.pack(fill=tk.X)
        
        # Version info
        version_label = ttk.Label(
            main_frame,
            text="v1.0.0",
            font=("Helvetica", int(8 * s)),
            foreground="gray"
        )
        version_label.pack(side=tk.BOTTOM, pady=(int(10 * s), 0))
    
    def setup_tray(self):
        """Setup system tray icon."""
        if not HAS_TRAY or not HAS_PIL:
            self.tray_icon = None
            return
        
        # Create tray icon image
        image = self.create_tray_icon()
        
        # Create menu
        menu = pystray.Menu(
            item('Show', self.show_window),
            item('Start Server', self.start_server_tray),
            item('Stop Server', self.stop_server_tray),
            pystray.Menu.SEPARATOR,
            item('Open Browser', self.open_browser),
            pystray.Menu.SEPARATOR,
            item('Quit', self.quit_app)
        )
        
        self.tray_icon = pystray.Icon(
            "word_format_editor",
            image,
            "Word Format Batch Editor",
            menu
        )
    
    def create_tray_icon(self):
        """Create a simple tray icon."""
        if not HAS_PIL:
            return None
        
        # Create a 64x64 icon
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='#4a90d9')
        draw = ImageDraw.Draw(image)
        
        # Draw a simple "W" letter
        draw.text((15, 10), "W", fill='white')
        
        return image
    
    def start_server(self):
        """Start the server."""
        self.status_label.config(text="● Starting...", foreground="orange")
        self.root.update()
        
        # Start in background thread
        def _start():
            success = self.server.start()
            self.root.after(0, lambda: self._on_start_complete(success))
        
        threading.Thread(target=_start, daemon=True).start()
    
    def _on_start_complete(self, success):
        """Called when server start completes."""
        if success:
            self.status_label.config(text="● Running", foreground="green")
            self.url_label.config(foreground="blue")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.open_btn.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="● Failed to Start", foreground="red")
            messagebox.showerror("Error", "Failed to start server. Check if port 8000 is available.")
    
    def stop_server(self):
        """Stop the server."""
        self.server.stop()
        self.status_label.config(text="● Stopped", foreground="red")
        self.url_label.config(foreground="gray")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.open_btn.config(state=tk.DISABLED)
    
    def open_browser(self):
        """Open browser to the server URL."""
        webbrowser.open("http://localhost:8000")
    
    def minimize_to_tray(self):
        """Minimize window to system tray."""
        if self.tray_icon:
            self.root.withdraw()
            # Run tray icon in background thread
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def show_window(self, icon=None, item=None):
        """Show the main window."""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.deiconify()
        self.root.lift()
    
    def start_server_tray(self, icon=None, item=None):
        """Start server from tray menu."""
        self.start_server()
    
    def stop_server_tray(self, icon=None, item=None):
        """Stop server from tray menu."""
        self.stop_server()
    
    def quit_app(self, icon=None, item=None):
        """Quit the application completely."""
        # Stop server first
        self.server.stop()
        
        # Stop tray icon
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
        
        # Force kill any remaining server processes on port 8000
        try:
            import subprocess
            if sys.platform == 'win32':
                # Kill processes on port 8000
                subprocess.run(
                    ['cmd', '/c', 'for /f "tokens=5" %a in (\'netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"\') do taskkill /f /pid %a'],
                    capture_output=True,
                    timeout=5
                )
            else:
                subprocess.run(['fuser', '-k', '8000/tcp'], capture_output=True, timeout=5)
        except:
            pass
        
        # Destroy root window
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
        
        # Force exit
        os._exit(0)
    
    def on_close(self):
        """Handle window close button."""
        if HAS_TRAY and self.tray_icon:
            # Minimize to tray instead of closing
            self.minimize_to_tray()
        else:
            # No tray - ask to quit
            self.quit_app()
    
    def update_status(self):
        """Update server status periodically."""
        if self.server.running and not self.server.is_running():
            self.status_label.config(text="● Stopped", foreground="red")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.open_btn.config(state=tk.DISABLED)
            self.server.running = False
        
        self.root.after(1000, self.update_status)
    
    def run(self):
        """Run the application."""
        # Auto-start server if launched with --auto-start
        if '--auto-start' in sys.argv or '-a' in sys.argv:
            self.root.after(100, self.start_server)
        
        self.root.mainloop()


def main():
    """Main entry point."""
    # Check dependencies
    missing = []
    if not HAS_TRAY:
        missing.append("pystray")
    if not HAS_PIL:
        missing.append("Pillow")
    
    if missing:
        print(f"Optional dependencies not installed: {', '.join(missing)}")
        print("For system tray support, install: pip install pystray Pillow")
        print("Running in window-only mode...\n")
    
    app = App()
    app.run()


if __name__ == "__main__":
    main()
