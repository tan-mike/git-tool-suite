"""
Git Tools Suite - Main Application Entry Point
Version 3.0 (Modular Edition)
"""

# CRITICAL: Windows taskbar icon fix - Set App User Model ID BEFORE any imports
# This MUST be set before tkinter is imported for Windows to display the custom icon
import sys
if sys.platform == 'win32':
    try:
        import ctypes
        # Set a unique App User Model ID for Windows taskbar icon
        myappid = 'tan.mike.gittoolssuite.v3'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        print("App User Model ID set successfully")  # Debug message
    except Exception as e:
        print(f"Could not set App User Model ID: {e}")

# Now import everything else
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import datetime

# Import our modular components
from apps.propagator import GitPropagatorApp
from apps.cleanup import BranchCleanerApp
from apps.pull_request import PullRequestApp
from apps.commit_generator import CommitGeneratorApp
from apps.branch_refresh import BranchRefreshApp
from apps.settings import SettingsApp
from ai.gemini_client import GeminiClient
from config import Config
from utils.versioning import is_newer_version


class GitToolsSuiteApp:
    def __init__(self, root):
        self.root = root
        if Config.is_limited_edition():
            title = f"Git Productivity Tools Suite Ver: {Config.APP_VERSION} (Limited Edition)"
        else:
            title = f"Git Productivity Tools Suite Ver: {Config.APP_VERSION}"
        self.root.title(title)
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Account for taskbar/dock
        if sys.platform == 'win32':
             taskbar_height = 60
        elif sys.platform == 'darwin':
             # Mac has top menu bar (~22px) and Dock (variable).
             # winfo_screenheight is usually full screen including dock/menu.
             # Reasonable buffer
             taskbar_height = 100
        else:
             taskbar_height = 60

        usable_height = screen_height - taskbar_height
        
        # Calculate window size - 90% width, 85% of usable height
        window_width = min(int(screen_width * 0.9), 1400)
        window_height = min(int(usable_height * 0.85), 900)
        
        # Calculate position to center window (account for taskbar)
        position_x = (screen_width - window_width) // 2
        position_y = (usable_height - window_height) // 2
        
        # Set geometry and minimum size
        self.root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        self.root.minsize(800, 600)  # Minimum usable size
        
        # Set window icon
        self._set_window_icon()

        self.joke_result = None
        self.gemini_client = GeminiClient() if Config.get_api_key() else None

        # Bottom frame with joke button (Pack this FIRST to ensure visibility)
        bottom_frame = ttk.Frame(root, padding=(10, 5, 10, 10))
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.joke_button = ttk.Button(bottom_frame, text="Tell me a joke", command=self.tell_joke_threaded)
        self.joke_button.pack(side=tk.RIGHT, padx=5)

        # Create tabs
        self.notebook = ttk.Notebook(root)
        
        tab_propagator = ttk.Frame(self.notebook)
        tab_cleanup = ttk.Frame(self.notebook)
        tab_pr_creator = ttk.Frame(self.notebook)
        tab_commit = ttk.Frame(self.notebook)
        tab_branch_refresh = ttk.Frame(self.notebook)
        tab_settings = ttk.Frame(self.notebook)
        
        self.notebook.add(tab_propagator, text='Commit Propagator')
        self.notebook.add(tab_cleanup, text='Branch Cleanup')
        self.notebook.add(tab_pr_creator, text='Create Pull Request')
        self.notebook.add(tab_commit, text='Commit Tool')
        self.notebook.add(tab_branch_refresh, text='Branch Refresh')
        self.notebook.add(tab_settings, text='Settings')
        self.notebook.pack(expand=True, fill="both", pady=(0, 5))

        # Initialize app instances
        self.propagator_app = GitPropagatorApp(tab_propagator)
        self.cleanup_app = BranchCleanerApp(tab_cleanup)
        self.pr_app = PullRequestApp(tab_pr_creator)
        self.commit_app = CommitGeneratorApp(tab_commit)
        self.branch_refresh_app = BranchRefreshApp(tab_branch_refresh)
        self.settings_app = SettingsApp(tab_settings)

        self.tab_apps = [self.propagator_app, self.cleanup_app, self.pr_app, self.commit_app, self.branch_refresh_app, self.settings_app]

        if not self.gemini_client:
            self.joke_button.config(state=tk.DISABLED)
            ttk.Label(bottom_frame, text="Gemini features disabled (API key not configured)").pack(side=tk.LEFT)

        self.check_for_birthday_threaded()
        
        # Auto-check for updates once on launch
        self.check_for_updates_on_launch()
    
    def _set_window_icon(self):
        """Set window icon for both development and frozen executable modes."""
        import os
        import sys
        
        icon_paths = []
        
        # For frozen executable (PyInstaller)
        if getattr(sys, 'frozen', False):
            # Icon embedded in executable via PyInstaller
            base_path = sys._MEIPASS
            icon_paths.append(os.path.join(base_path, 'assets', 'git_tools_suite.ico'))
        else:
            # For development mode
            icon_paths.append(os.path.join('assets', 'git_tools_suite.ico'))
            icon_paths.append('git_tools_suite.ico')  # Fallback
        
        # Try each path
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    self.root.iconbitmap(icon_path)
                    return
                except Exception as e:
                    # On Mac/Linux iconbitmap sometimes fails with ICO files.
                    # Just ignore and use default system icon if so.
                    print(f"Could not set icon from {icon_path}: {e}")
        
        # If no icon found, silently continue with default icon
        print("No custom icon found, using default")

    def tell_joke_threaded(self):
        """Entry point for joke generation."""
        self.joke_button.config(state=tk.DISABLED)
        self.joke_result = None

        loading_popup = tk.Toplevel(self.root)
        loading_popup.transient(self.root)
        loading_popup.overrideredirect(True)
        
        loading_label = ttk.Label(loading_popup, text="  Thinking of a joke...  ", padding=20, font=("Helvetica", 12))
        loading_label.pack()
        
        loading_popup.update_idletasks()
        
        popup_width = loading_label.winfo_width()
        popup_height = loading_label.winfo_height()
        main_win_x, main_win_y = self.root.winfo_x(), self.root.winfo_y()
        main_win_width, main_win_height = self.root.winfo_width(), self.root.winfo_height()
        position_x = main_win_x + (main_win_width // 2) - (popup_width // 2)
        position_y = main_win_y + (main_win_height // 2) - (popup_height // 2)
        loading_popup.geometry(f"{popup_width}x{popup_height}+{position_x}+{position_y}")

        self.root.after(50, self._start_joke_worker_and_poller, loading_popup)

    def _start_joke_worker_and_poller(self, loading_popup):
        loading_popup.grab_set()
        threading.Thread(target=self._tell_joke_worker, daemon=True).start()
        self.check_for_joke_result(loading_popup)

    def _tell_joke_worker(self):
        """Background thread for generating a joke."""
        self.log_to_active_tab("Requesting a joke from the AI...")
        self.joke_result = self.gemini_client.get_joke()

    def check_for_joke_result(self, loading_popup):
        """Polls for joke result."""
        if self.joke_result is not None:
            loading_popup.destroy()
            if "Error:" not in self.joke_result:
                self.show_centered_popup("Here's a Joke!", self.joke_result)
            self.joke_button.config(state=tk.NORMAL)
        else:
            self.root.after(100, self.check_for_joke_result, loading_popup)

    def log_to_active_tab(self, message):
        try:
            current_tab_index = self.notebook.index(self.notebook.select())
            active_app = self.tab_apps[current_tab_index]
            if hasattr(active_app, 'log_message'):
                active_app.log_message(message)
            elif hasattr(active_app, 'log'):
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                active_app.log(f"[{timestamp}] {message}")
        except Exception as e:
            print(f"Failed to log to active tab: {e}")

    def show_centered_popup(self, title, message):
        """Shows a popup with typewriter effect."""
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.resizable(False, False)
        popup.grab_set()

        popup_width, popup_height = 450, 250
        self.root.update_idletasks()
        main_x, main_y = self.root.winfo_x(), self.root.winfo_y()
        main_w, main_h = self.root.winfo_width(), self.root.winfo_height()
        
        x = main_x + (main_w // 2) - (popup_width // 2)
        y = main_y + (main_h // 2) - (popup_height // 2)
        popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

        frame = ttk.Frame(popup, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        text_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Segoe UI", 10))
        text_area.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        ok_button = ttk.Button(frame, text="OK", command=popup.destroy)
        ok_button.pack()
        
        def insert_text_safely(i=0):
            if not text_area.winfo_exists(): 
                return
            if i < len(message):
                text_area.insert(tk.END, message[i])
                text_area.see(tk.END)
                text_area.after(10, insert_text_safely, i + 1)
            else:
                text_area.config(state=tk.DISABLED)

        insert_text_safely()
        popup.focus_force()
        popup.wait_window()

    def check_for_birthday_threaded(self):
        today = datetime.date.today()
        # Only show birthday greeting if Limited Edition is active
        if Config.is_limited_edition() and self.gemini_client and today.month == 12 and today.day == 12:
            threading.Thread(target=self._birthday_worker, daemon=True).start()

    def _birthday_worker(self):
        self.log_to_active_tab("Ahh..It's that special day...")
        message = self.gemini_client.get_birthday_message("Yie Thin")
        if "Error:" not in message:
            self.root.after(0, self.show_centered_popup, "A Special Message for Yie Thin!", message)
    
    def check_for_updates_on_launch(self):
        """Check for updates silently on app launch (once per session)."""
        import sys
        # Only check if running as executable
        if getattr(sys, 'frozen', False):
            threading.Thread(target=self._update_check_worker, daemon=True).start()
    
    def _update_check_worker(self):
        """Background worker to check for updates."""
        import requests
        try:
            response = requests.get(Config.UPDATE_CHECK_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            latest_version = data.get('version')
            release_url = data.get('release_url', "https://github.com/tan-mike/git-tool-suite/releases")
            
            # Simple version comparison
            if is_newer_version(latest_version, Config.APP_VERSION):
                # Show notification in main thread
                self.root.after(0, lambda: self._show_update_notification(latest_version, release_url))
        except Exception:
            # Silently fail - don't interrupt user experience
            pass
    
    def _show_update_notification(self, latest_version, release_url):
        """Show a non-intrusive update notification."""
        from tkinter import messagebox
        import webbrowser
        
        response = messagebox.askyesno(
            "Update Available",
            f"A new version ({latest_version}) is available!\n\n"
            f"Current version: {Config.APP_VERSION}\n\n"
            "Would you like to update now?\n\n"
            "(You can also check for updates manually in the Settings tab)",
            icon='info'
        )
        
        if response:
            # Switch to settings tab and trigger update check
            self.notebook.select(4)  # Settings tab is index 4
            # Let the SettingsApp handle the automatic update flow
            self.settings_app.check_for_updates()


def cleanup_old_versions():
    """Delete old versions of the executable."""
    import sys
    from pathlib import Path
    
    try:
        # Get directory of current executable or script
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent
            
        # Find all files ending in .old
        # Clean both .exe.old and .old files
        patterns = ["*.exe.old", "*.old"]
        for pattern in patterns:
            for old_file in base_path.glob(pattern):
                try:
                    old_file.unlink()
                    print(f"Cleaned up old version: {old_file.name}")
                except Exception as e:
                    # Retries will happen next launch
                    print(f"Could not delete {old_file.name}: {e}")
                
    except Exception as e:
        print(f"Error during cleanup: {e}")


def main():
    """Main entry point."""
    import tkinter as tk
    from tkinter import messagebox
    
    # Run cleanup first thing
    cleanup_old_versions()
    
    # Check for GitPython dependency
    try:
        from git import Repo, exc
    except ImportError:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Dependency Missing",
            "The 'gitpython' library is required for the Branch Cleanup tab.\n\n"
            "Please install it by running:\n'pip install gitpython'"
        )
        root.destroy()
        return
    
    root = tk.Tk()
    app = GitToolsSuiteApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
