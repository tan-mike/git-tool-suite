"""
Worktree Manager Application.
Allows managing parallel Git worktrees with automatic environment setup.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import datetime
import os
import sys
import shlex
from pathlib import Path

from config import Config
from utils.git_utils import (
    run_git_command,
    list_worktrees,
    add_worktree,
    remove_worktree,
    prune_worktrees,
    get_branches
)

class WorktreeManagerApp:
    def __init__(self, parent):
        self.parent = parent
        self.selected_repo = None
        self.load_configuration()
        
        self.main_frame = ttk.Frame(self.parent, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.build_ui()
        self.update_repo_tree()

    def load_configuration(self):
        prefs = Config.load_preferences()
        wt_prefs = prefs.get("worktree", {})
        self.base_path = wt_prefs.get("base_path", "~/worktrees")
        self.editor_command = wt_prefs.get("editor_command", "")
        self.profiles = wt_prefs.get("profiles", {})
        self.tracked_repos = list(self.profiles.keys())

    def save_configuration(self):
        prefs = Config.load_preferences()
        prefs["worktree"] = {
            "base_path": self.base_path,
            "editor_command": self.editor_command,
            "profiles": self.profiles,
        }
        Config.save_preferences(prefs)

    def build_ui(self):
        # Configure grid
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        # --- Left Panel: Tracked Repositories ---
        left_panel = ttk.Frame(self.main_frame)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ttk.Label(left_panel, text="Tracked Repositories", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        # TreeView
        self.repo_tree = ttk.Treeview(left_panel, selectmode="browse", show="tree")
        self.repo_tree.pack(fill=tk.BOTH, expand=True)
        self.repo_tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        # Repo Buttons
        repo_btn_frame = ttk.Frame(left_panel)
        repo_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(repo_btn_frame, text="Add Repo", command=self.add_repository).pack(side=tk.LEFT, padx=2)
        ttk.Button(repo_btn_frame, text="Remove Repo", command=self.remove_repository).pack(side=tk.LEFT, padx=2)
        
        # Worktree Actions
        wt_action_frame = ttk.Frame(left_panel)
        wt_action_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(wt_action_frame, text="Remove WT", command=self.remove_selected_worktree).pack(side=tk.LEFT, padx=2)
        ttk.Button(wt_action_frame, text="Open Folder", command=self.open_in_file_manager).pack(side=tk.LEFT, padx=2)
        ttk.Button(wt_action_frame, text="Open Editor", command=self.open_in_editor).pack(side=tk.LEFT, padx=2)
        ttk.Button(wt_action_frame, text="Prune", command=self.prune_selected).pack(side=tk.LEFT, padx=2)

        # --- Right Panel: Create & Profile ---
        right_panel = ttk.Frame(self.main_frame)
        right_panel.grid(row=0, column=1, sticky="nsew")

        # 1. Create Worktree Section
        create_frame = ttk.LabelFrame(right_panel, text="Create Worktree", padding="10")
        create_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(create_frame, text="Branch:").grid(row=0, column=0, sticky=tk.W)
        self.branch_combo = ttk.Combobox(create_frame)
        self.branch_combo.grid(row=0, column=1, sticky="ew", padx=5)
        create_frame.columnconfigure(1, weight=1)
        
        self.create_new_branch_var = tk.BooleanVar()
        ttk.Checkbutton(create_frame, text="Create new branch", variable=self.create_new_branch_var).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        self.path_preview_label = ttk.Label(create_frame, text="Path: Select a repo...", font=("", 8, "italic"), foreground="gray")
        self.path_preview_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Button(create_frame, text="Create Worktree", command=self.create_worktree).grid(row=3, column=1, sticky=tk.E)

        # 2. Setup Profile Section (Placeholder for Task 7)
        profile_frame = ttk.LabelFrame(right_panel, text="Setup Profile", padding="10")
        profile_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        ttk.Label(profile_frame, text="Environment setup options will appear here...").pack()

        # 3. Log Section
        log_frame = ttk.LabelFrame(right_panel, text="Operation Log", padding="10")
        log_frame.pack(fill=tk.X)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state=tk.DISABLED, font=("Courier", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log_message(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    # --- Placeholders for subsequent tasks ---
    def add_repository(self): pass
    def remove_repository(self): pass
    def update_repo_tree(self): pass
    def on_tree_select(self, event): pass
    def remove_selected_worktree(self): pass
    def open_in_file_manager(self): pass
    def open_in_editor(self): pass
    def prune_selected(self): pass
    def create_worktree(self): pass
