"""
Shared UI utility functions and components.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk


def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    
    Args:
        relative_path (str): Relative path to resource
        
    Returns:
        str: Absolute path to resource
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class CenteredDialog(tk.Toplevel):
    """
    A base class for modal dialogs that are centered relative to their parent window.
    """
    def __init__(self, parent, title, width=600, height=500):
        super().__init__(parent)
        self.withdraw()  # Hide the window while we prepare it
        self.title(title)
        self.transient(parent)
        self.grab_set()
        
        # Ensure it's resizable by default
        self.resizable(True, True)
        
        # Get root window coordinates and dimensions
        root = parent.winfo_toplevel()
        root.update_idletasks() # Ensure dimensions are current
        
        root_width = root.winfo_width()
        root_height = root.winfo_height()
        root_x = root.winfo_x()
        root_y = root.winfo_y()
        
        # Calculate centered position
        x = root_x + (root_width // 2) - (width // 2)
        y = root_y + (root_height // 2) - (height // 2)
        
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Now that it's positioned, show it
        self.deiconify()
        
        # Close on Escape key
        self.bind("<Escape>", lambda e: self.destroy())
