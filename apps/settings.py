"""
Settings Application.
Allows configuration of API keys and checking for updates.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import webbrowser
import shutil
import tempfile

from config import Config

class SettingsApp:
    def __init__(self, parent):
        self.parent = parent
        self.prefs = Config.load_preferences()
        self.api_key_var = tk.StringVar(value=self.prefs.get('api_key', ''))
        
        self.main_frame = ttk.Frame(self.parent, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.build_ui()
        
    def build_ui(self):
        # Title
        ttk.Label(self.main_frame, text="Settings", font=("", 16, "bold")).pack(anchor=tk.W, pady=(0, 20))
        
        # 1. API Key Setup (Conditional)
        if not Config.IS_LIMITED_BUILD:
            api_frame = ttk.LabelFrame(self.main_frame, text="Gemini API Configuration", padding="15")
            api_frame.pack(fill=tk.X, pady=(0, 20))
            
            ttk.Label(api_frame, text="API Key:").pack(anchor=tk.W)
            
            entry_frame = ttk.Frame(api_frame)
            entry_frame.pack(fill=tk.X, pady=5)
            
            self.key_entry = ttk.Entry(entry_frame, textvariable=self.api_key_var, show="*", width=50)
            self.key_entry.pack(side=tk.LEFT, padx=(0, 10))
            
            ttk.Button(entry_frame, text="Save", command=self.save_api_key).pack(side=tk.LEFT, padx=5)
            ttk.Button(entry_frame, text="Clear", command=self.clear_api_key).pack(side=tk.LEFT)
            
            ttk.Label(api_frame, text="Note: Provide your own Gemini API key, to use AI features.", font=("", 8, "italic")).pack(anchor=tk.W, pady=(5, 0))
        
        # 2. Update Checker
        update_frame = ttk.LabelFrame(self.main_frame, text="Software Update", padding="15")
        update_frame.pack(fill=tk.X, pady=(0, 20))
        
        version_frame = ttk.Frame(update_frame)
        version_frame.pack(fill=tk.X)
        
        ttk.Label(version_frame, text=f"Current Version: {Config.APP_VERSION}", font=("", 10)).pack(side=tk.LEFT)
        
        self.check_btn = ttk.Button(version_frame, text="Check for Updates", command=self.check_for_updates)
        self.check_btn.pack(side=tk.RIGHT)
        
        # 3. About
        about_frame = ttk.LabelFrame(self.main_frame, text="About", padding="15")
        about_frame.pack(fill=tk.X)
        
        ttk.Label(about_frame, text="Git Productivity Tools Suite").pack(anchor=tk.W)

    def save_api_key(self):
        key = self.api_key_var.get().strip()
        if not key:
            return messagebox.showwarning("Warning", "API Key cannot be empty.")
            
        self.prefs['api_key'] = key
        Config.save_preferences(self.prefs)
        messagebox.showinfo("Success", "API Key saved successfully.\nPlease restart the application for changes to take effect.")

    def clear_api_key(self):
        if messagebox.askyesno("Confirm", "Clear stored API Key?"):
            self.api_key_var.set("")
            if 'api_key' in self.prefs:
                del self.prefs['api_key']
                Config.save_preferences(self.prefs)
            messagebox.showinfo("Success", "API Key cleared.")

    def check_for_updates(self):
        self.check_btn.config(state=tk.DISABLED, text="Checking...")
        threading.Thread(target=self._update_worker, daemon=True).start()


    def _update_worker(self):
        try:
            response = requests.get(Config.UPDATE_CHECK_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            latest_version = data.get('version')
            release_url = data.get('release_url', "https://github.com/tan-mike/git-tool-suite/releases")
            download_url = data.get('download_url')
            
            self.parent.after(0, lambda: self._show_update_result(latest_version, release_url, download_url))
        except Exception as e:
            error_msg = f"Failed to check for updates:\n{e}"
            self.parent.after(0, lambda: messagebox.showerror("Error", error_msg))
        finally:
            self.parent.after(0, lambda: self.check_btn.config(state=tk.NORMAL, text="Check for Updates"))

    def _show_update_result(self, latest_version, release_url, download_url):
        current = Config.APP_VERSION
        # Simple string comparison (works for simple versions like "3.1" vs "3.2")
        # For more complex semver, we might need packaging.version
        if latest_version > current:
            # Check if running as executable
            import sys
            is_executable = getattr(sys, 'frozen', False)
            
            if is_executable and download_url:
                # Offer automatic update
                response = messagebox.askyesnocancel(
                    "Update Available",
                    f"A new version ({latest_version}) is available!\n\n"
                    "Do you want to download and install it automatically?\n\n"
                    "Yes - Download and install now\n"
                    "No - Open download page manually\n"
                    "Cancel - Skip this update"
                )
                
                if response is True:  # Yes - Auto update
                    self._download_and_install_update(download_url)
                elif response is False:  # No - Manual download
                    webbrowser.open(release_url)
            else:
                # Running from source or no download_url - just open browser
                if messagebox.askyesno("Update Available", f"A new version ({latest_version}) is available!\n\nOpen download page?"):
                    webbrowser.open(release_url)
        else:
            messagebox.showinfo("Up to Date", f"You are running the latest version ({current}).")
    
    def _download_and_install_update(self, download_url):
        """Download and install the update automatically with progress tracking."""
        import sys
        from pathlib import Path
        import tempfile
        import subprocess
        import time
        
        try:
            # Show progress window
            progress_window = tk.Toplevel(self.parent)
            progress_window.title("Downloading Update")
            progress_window.geometry("450x120")
            progress_window.transient(self.parent)
            progress_window.grab_set()
            
            # Status label
            status_label = ttk.Label(progress_window, text="Initializing download...", font=("", 9))
            status_label.pack(pady=(15, 5))
            
            # Determinate progress bar
            progress_bar = ttk.Progressbar(progress_window, mode='determinate', length=400)
            progress_bar.pack(padx=20, pady=5)
            
            # Speed label
            speed_label = ttk.Label(progress_window, text="", font=("", 8))
            speed_label.pack(pady=(5, 15))
            
            # Download in thread with retry logic
            def download():
                max_retries = 3
                chunk_size = 32 * 1024 * 1024  # 32 MB chunks for maximum speed
                update_interval = 5 * 1024 * 1024  # Update UI every 5 MB downloaded
                
                for attempt in range(max_retries):
                    session = None
                    try:
                        # Update status
                        self.parent.after(0, status_label.config, {'text': f'Connecting... (Attempt {attempt + 1}/{max_retries})'})
                        
                        # Use session for connection pooling and better performance
                        session = requests.Session()
                        session.headers.update({
                            'User-Agent': 'GitToolSuite-Updater',
                            'Accept-Encoding': 'gzip, deflate'
                        })
                        
                        self.parent.after(0, speed_label.config, {'text': f'Requesting {download_url}...'})
                        response = session.get(download_url, stream=True, timeout=30)
                        response.raise_for_status()
                        
                        # Update status immediately after successful connection
                        self.parent.after(0, status_label.config, {'text': 'Download starting...'})
                        
                        # Get total file size
                        total_size = int(response.headers.get('content-length', 0))
                        
                        if total_size > 0:
                            self.parent.after(0, progress_bar.config, {'maximum': total_size})
                            self.parent.after(0, status_label.config, {'text': f'Downloading ({total_size/(1024*1024):.1f} MB)...'})
                            self.parent.after(0, speed_label.config, {'text': 'Initializing...'})
                        else:
                            # No content-length header - use indeterminate mode
                            self.parent.after(0, progress_bar.config, {'mode': 'indeterminate'})
                            self.parent.after(0, progress_bar, 'start')
                            self.parent.after(0, status_label.config, {'text': 'Downloading...'})
                            self.parent.after(0, speed_label.config, {'text': 'Size unknown, downloading...'})
                        
                        # Save to temp file with progress tracking
                        temp_exe = Path(tempfile.gettempdir()) / "GitToolSuite_update.exe"
                        downloaded = 0
                        last_ui_update = 0
                        start_time = time.time()
                        
                        # Use larger buffer for file writes
                        with open(temp_exe, 'wb', buffering=chunk_size) as f:
                            for chunk in response.iter_content(chunk_size=chunk_size):
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    
                                    # Only update UI every update_interval bytes to reduce overhead
                                    if downloaded - last_ui_update >= update_interval or downloaded >= total_size:
                                        last_ui_update = downloaded
                                        
                                        # Calculate speed and progress
                                        elapsed = time.time() - start_time
                                        if elapsed > 0:
                                            speed = downloaded / elapsed / (1024 * 1024)  # MB/s
                                            
                                            if total_size > 0:
                                                percent = (downloaded / total_size) * 100
                                                remaining = (total_size - downloaded) / (downloaded / elapsed) if downloaded > 0 else 0
                                                
                                                status_text = f"Downloaded {downloaded/(1024*1024):.1f} MB / {total_size/(1024*1024):.1f} MB ({percent:.0f}%)"
                                                speed_text = f"{speed:.1f} MB/s - ~{remaining:.0f}s remaining"
                                            else:
                                                status_text = f"Downloaded {downloaded/(1024*1024):.1f} MB"
                                                speed_text = f"{speed:.1f} MB/s"
                                            
                                            # Update UI
                                            self.parent.after(0, progress_bar.config, {'value': downloaded})
                                            self.parent.after(0, status_label.config, {'text': status_text})
                                            self.parent.after(0, speed_label.config, {'text': speed_text})
                        
                        # Close session
                        if session:
                            session.close()
                        
                        # Download successful
                        self.parent.after(0, status_label.config, {'text': 'Download complete!'})
                        self.parent.after(0, speed_label.config, {'text': 'Preparing to update...'})
                        
                        # Close progress window
                        self.parent.after(0, progress_window.destroy)
                        
                        # Launch updater
                        current_exe = Path(sys.executable)
                        
                        # Embed updater script - extract to temp at runtime
                        # This allows single-file distribution
                        updater_code = '''"""
Auto-updater script for GitToolSuite.
This script downloads the new version, replaces the old executable, and restarts the app.
"""

import sys
import time
import os
import subprocess
import shutil
from pathlib import Path

def main():
    if len(sys.argv) != 3:
        print("Usage: updater.py <current_exe_path> <downloaded_exe_path>")
        sys.exit(1)
    
    current_exe = Path(sys.argv[1])
    downloaded_exe = Path(sys.argv[2])
    
    print(f"Waiting for main application to close...")
    time.sleep(2)  # Give main app time to close
    
    # Ensure the current exe is not running
    max_retries = 10
    for i in range(max_retries):
        try:
            # Try to rename (will fail if file is locked)
            temp_backup = current_exe.with_suffix('.exe.old')
            if temp_backup.exists():
                temp_backup.unlink()
            current_exe.rename(temp_backup)
            break
        except PermissionError:
            if i < max_retries - 1:
                print(f"Waiting for executable to close... ({i+1}/{max_retries})")
                time.sleep(1)
            else:
                print("ERROR: Could not replace executable. Please close the application manually.")
                input("Press Enter to exit...")
                sys.exit(1)
    
    try:
        # Copy new version to current location
        shutil.copy2(downloaded_exe, current_exe)
        print(f"Successfully updated to new version!")
        
        # Clean up
        downloaded_exe.unlink()
        temp_backup.unlink()
        
        # Restart the application
        print("Restarting application...")
        time.sleep(1)
        
        # Hide console window on Windows
        creation_flags = 0
        if sys.platform == 'win32':
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        subprocess.Popen(
            [str(current_exe)], 
            cwd=current_exe.parent,
            creationflags=creation_flags
        )
        
    except Exception as e:
        print(f"ERROR during update: {e}")
        # Restore backup if something went wrong
        if temp_backup.exists():
            temp_backup.rename(current_exe)
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
                        
                        # Write updater to temp file
                        updater_script = Path(tempfile.gettempdir()) / "GitToolSuite_updater.py"
                        with open(updater_script, 'w') as f:
                            f.write(updater_code)
                        
                        # Find Python interpreter
                        python_exe = shutil.which('python') or shutil.which('python3')
                        if not python_exe:
                            # Try common Python installation paths
                            for py_path in [
                                Path(r'C:\Python313\python.exe'),
                                Path(r'C:\Python312\python.exe'),
                                Path(r'C:\Python311\python.exe'),
                                Path(r'C:\Python310\python.exe'),
                            ]:
                                if py_path.exists():
                                    python_exe = str(py_path)
                                    break
                        
                        if not python_exe:
                            error_msg = "Could not find Python interpreter to complete update.\n\n"
                            error_msg += "Python interpreter not found in PATH\n"
                            error_msg += "\nPlease manually replace the executable with the downloaded file."
                            self.parent.after(0, lambda: messagebox.showerror("Update Error", error_msg))
                            return
                        
                        # Start updater process
                        subprocess.Popen(
                            [python_exe, str(updater_script), str(current_exe), str(temp_exe)],
                            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                        )
                        
                        # Show message and exit
                        self.parent.after(0, lambda: messagebox.showinfo(
                            "Update Ready",
                            "Update downloaded successfully!\n\nThe application will now close and update."
                        ))
                        self.parent.after(100, lambda: self.parent.quit())
                        
                        # Success - exit retry loop
                        break
                        
                    except requests.RequestException as e:
                        # Close session on error
                        if session:
                            try:
                                session.close()
                            except:
                                pass
                        
                        if attempt < max_retries - 1:
                            # Retry
                            error_msg = str(e)[:100]
                            self.parent.after(0, status_label.config, {'text': f'Download failed, retrying...'})
                            self.parent.after(0, speed_label.config, {'text': f'Error: {error_msg}'})
                            time.sleep(2)
                        else:
                            # All retries exhausted
                            self.parent.after(0, progress_window.destroy)
                            error_msg = f"Failed to download update after {max_retries} attempts:\n{e}"
                            self.parent.after(0, lambda: messagebox.showerror("Download Error", error_msg))
                    
                    except Exception as e:
                        # Close session on error
                        if session:
                            try:
                                session.close()
                            except:
                                pass
                        
                        # Unexpected error
                        self.parent.after(0, progress_window.destroy)
                        error_msg = f"Unexpected error during download:\n{type(e).__name__}: {e}"
                        self.parent.after(0, lambda: messagebox.showerror("Download Error", error_msg))
                        break
            
            threading.Thread(target=download, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Update Error", f"Failed to start update:\n{e}")

