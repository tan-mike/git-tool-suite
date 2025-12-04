"""
Settings Application.
Allows configuration of API keys and checking for updates.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import webbrowser

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
            
            self.parent.after(0, lambda: self._show_update_result(latest_version, release_url))
        except Exception as e:
            error_msg = f"Failed to check for updates:\n{e}"
            self.parent.after(0, lambda: messagebox.showerror("Error", error_msg))
        finally:
            self.parent.after(0, lambda: self.check_btn.config(state=tk.NORMAL, text="Check for Updates"))

    def _show_update_result(self, latest_version, release_url):
        current = Config.APP_VERSION
        # Simple string comparison (works for simple versions like "3.1" vs "3.2")
        # For more complex semver, we might need packaging.version
        if latest_version > current:
            if messagebox.askyesno("Update Available", f"A new version ({latest_version}) is available!\n\nOpen download page?"):
                webbrowser.open(release_url)
        else:
            messagebox.showinfo("Up to Date", f"You are running the latest version ({current}).")
