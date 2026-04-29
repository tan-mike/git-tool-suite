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

    def add_repository(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Select Git Repository")
        if not path:
            return
            
        try:
            # Validate it's a git repo
            run_git_command("rev-parse --git-dir", path)
            
            if path in self.profiles:
                messagebox.showinfo("Info", "Repository already tracked.")
                return
                
            # Add to profiles with empty setup
            self.profiles[path] = {
                "copy_files": [],
                "install_commands": [],
                "post_commands": []
            }
            self.save_configuration()
            self.update_repo_tree()
            self.log_message(f"Added repository: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Invalid Git repository:\n{e}")

    def remove_repository(self):
        selected = self.repo_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Select a repository to remove.")
            return
            
        item = selected[0]
        # If a worktree is selected, get its parent (the repo)
        parent = self.repo_tree.parent(item)
        repo_item = parent if parent else item
        repo_path = self.repo_tree.item(repo_item, "text")
        
        if messagebox.askyesno("Confirm", f"Stop tracking repository?\n\n{repo_path}"):
            if repo_path in self.profiles:
                del self.profiles[repo_path]
                self.save_configuration()
                self.update_repo_tree()
                self.log_message(f"Removed repository: {repo_path}")
                if self.selected_repo == repo_path:
                    self.selected_repo = None
                    self.branch_combo.set("")
                    self.branch_combo['values'] = []

    def update_repo_tree(self):
        # Clear tree
        for item in self.repo_tree.get_children():
            self.repo_tree.delete(item)
            
        prefs = Config.load_preferences()
        self.profiles = prefs.get("worktree", {}).get("profiles", {})
        
        for repo_path in self.profiles.keys():
            try:
                repo_node = self.repo_tree.insert("", tk.END, text=repo_path, open=True)
                worktrees = list_worktrees(repo_path)
                
                for wt in worktrees:
                    # Skip the main worktree (it's the repo_path itself)
                    if Path(wt['path']).resolve() == Path(repo_path).resolve():
                        continue
                    
                    display_text = f"{wt['branch']} → {wt['path']}"
                    self.repo_tree.insert(repo_node, tk.END, text=display_text)
            except Exception as e:
                self.repo_tree.insert("", tk.END, text=f"Error loading {repo_path}: {e}")

    def on_tree_select(self, event):
        selected = self.repo_tree.selection()
        if not selected:
            return
            
        item = selected[0]
        parent = self.repo_tree.parent(item)
        
        # Determine repo path
        if parent: # Worktree selected
            repo_path = self.repo_tree.item(parent, "text")
        else: # Repo selected
            repo_path = self.repo_tree.item(item, "text")
            
        if repo_path != self.selected_repo:
            self.selected_repo = repo_path
            self._load_branches_for_repo(repo_path)
            # load_profile_for_repo will be implemented in Task 7
            if hasattr(self, 'load_profile_for_repo'):
                self.load_profile_for_repo(repo_path)
        
        self._update_path_preview()

    def _load_branches_for_repo(self, repo_path):
        try:
            local_branches = get_branches(repo_path)
            
            # Also get remote branches
            remote_output = run_git_command("branch -r", repo_path)
            remote_branches = []
            for line in remote_output.splitlines():
                branch = line.strip()
                if " -> " in branch: continue # Skip HEAD -> ...
                # strip origin/
                if "/" in branch:
                    branch = branch.split("/", 1)[1]
                remote_branches.append(branch)
            
            all_branches = sorted(list(set(local_branches + remote_branches)))
            self.branch_combo['values'] = all_branches
            
            current = run_git_command("rev-parse --abbrev-ref HEAD", repo_path)
            self.branch_combo.set(current)
        except Exception as e:
            self.log_message(f"Error loading branches: {e}")

    def _update_path_preview(self):
        if not self.selected_repo:
            self.path_preview_label.config(text="Path: Select a repo...")
            return
            
        branch = self.branch_combo.get().strip()
        if not branch:
            self.path_preview_label.config(text="Path: Select a branch...")
            return
            
        repo_name = Path(self.selected_repo).name
        base = Path(self.base_path).expanduser()
        worktree_path = base / repo_name / branch.replace("/", "-")
        self.path_preview_label.config(text=f"Path: {worktree_path}")

    def _get_selected_worktree_path(self):
        """Get the filesystem path of the currently selected worktree."""
        selected = self.repo_tree.selection()
        if not selected:
            return None
        item = selected[0]
        if not self.repo_tree.parent(item):
            return None  # It's a repo, not a worktree
        text = self.repo_tree.item(item, "text")
        if " → " in text:
            return text.split(" → ")[-1].strip()
        return None

    def prune_selected(self):
        if not self.selected_repo:
            return
        try:
            prune_worktrees(self.selected_repo)
            self.log_message(f"Pruned worktrees for {self.selected_repo}")
            self.update_repo_tree()
        except Exception as e:
            self.log_message(f"Prune failed: {e}")

    # --- Placeholders for remaining actions ---
    def remove_selected_worktree(self): pass
    def open_in_file_manager(self): pass
    def open_in_editor(self): pass
    def create_worktree(self): pass
