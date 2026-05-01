"""
Worktree Manager Application.
Allows managing parallel Git worktrees with automatic environment setup.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
import threading
import shutil
import datetime
import os
import sys
import shlex
import subprocess
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
        self.branch_combo.bind("<<ComboboxSelected>>", lambda e: self._update_path_preview())
        self.branch_combo.bind("<KeyRelease>", lambda e: self._update_path_preview())
        create_frame.columnconfigure(1, weight=1)
        
        self.create_new_branch_var = tk.BooleanVar()
        ttk.Checkbutton(create_frame, text="Create new branch", variable=self.create_new_branch_var).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        self.path_preview_label = ttk.Label(create_frame, text="Path: Select a repo...", font=("", 9, "italic"))
        self.path_preview_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Button(create_frame, text="Create Worktree", command=self.create_worktree).grid(row=3, column=1, sticky=tk.E)

        # 2. Setup Profile Section
        profile_frame = ttk.LabelFrame(right_panel, text="Setup Profile", padding="10")
        profile_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Base Path & Editor
        settings_frame = ttk.Frame(profile_frame)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(settings_frame, text="Worktree Base Path:").grid(row=0, column=0, sticky=tk.W)
        self.base_path_var = tk.StringVar(value=self.base_path)
        ttk.Entry(settings_frame, textvariable=self.base_path_var).grid(row=0, column=1, sticky="ew", padx=5)
        
        ttk.Label(settings_frame, text="Editor Command:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.editor_var = tk.StringVar(value=self.editor_command)
        ttk.Entry(settings_frame, textvariable=self.editor_var).grid(row=1, column=1, sticky="ew", padx=5)
        settings_frame.columnconfigure(1, weight=1)

        # Lists for Profile
        list_container = ttk.Frame(profile_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        list_container.columnconfigure((0, 1, 2), weight=1)
        list_container.rowconfigure(1, weight=1)

        def create_list_section(parent, column, title, listbox_attr):
            ttk.Label(parent, text=title).grid(row=0, column=column, sticky=tk.W)
            frame = ttk.Frame(parent)
            frame.grid(row=1, column=column, sticky="nsew", padx=2)
            
            lb = tk.Listbox(frame, height=6)
            lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            setattr(self, listbox_attr, lb)
            
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(side=tk.RIGHT, fill=tk.Y)
            ttk.Button(btn_frame, text="+", width=2, command=lambda: self._add_list_item(lb, f"Add {title}", "Value:")).pack()
            ttk.Button(btn_frame, text="-", width=2, command=lambda: self._remove_list_item(lb)).pack()
            ttk.Button(btn_frame, text="↑", width=2, command=lambda: self._move_list_item(lb, -1)).pack()
            ttk.Button(btn_frame, text="↓", width=2, command=lambda: self._move_list_item(lb, 1)).pack()

        create_list_section(list_container, 0, "Files to Copy", "copy_files_lb")
        create_list_section(list_container, 1, "Install Cmds", "install_cmds_lb")
        create_list_section(list_container, 2, "Post-Setup Cmds", "post_cmds_lb")

        ttk.Button(profile_frame, text="Save Profile & Settings", command=self.save_profile).pack(anchor=tk.E, pady=(10, 0))

        # 3. Log Section
        log_frame = ttk.LabelFrame(right_panel, text="Operation Log", padding="10")
        log_frame.pack(fill=tk.X)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log_message(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def add_repository(self):
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

    def create_worktree(self):
        if not self.selected_repo:
            messagebox.showwarning("No Repository", "Select a repository first.")
            return
        
        branch = self.branch_combo.get().strip()
        if not branch:
            messagebox.showwarning("No Branch", "Enter or select a branch name.")
            return
        
        create_new = self.create_new_branch_var.get()
        
        # Compute worktree path
        repo_name = Path(self.selected_repo).name
        base = Path(self.base_path).expanduser()
        worktree_path = base / repo_name / branch.replace("/", "-")
        
        if worktree_path.exists():
            messagebox.showerror("Path Exists", f"Worktree path already exists:\n{worktree_path}")
            return
        
        threading.Thread(
            target=self._create_worktree_worker,
            args=(self.selected_repo, str(worktree_path), branch, create_new),
            daemon=True
        ).start()

    def _create_worktree_worker(self, repo_path, worktree_path, branch, create_new):
        self.log_message(f"=== Creating worktree: {branch} ===")
        
        # Step 1: git worktree add
        try:
            self.log_message(f"Creating worktree at: {worktree_path}")
            add_worktree(repo_path, worktree_path, branch, create_branch=create_new)
            self.log_message("  ✓ Worktree created")
        except Exception as e:
            self.log_message(f"  ✗ Failed to create worktree: {e}")
            return
        
        # Step 2: Copy files
        profile = self.profiles.get(repo_path, {})
        for rel_path in profile.get("copy_files", []):
            src = Path(repo_path) / rel_path
            dst = Path(worktree_path) / rel_path
            try:
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(src), str(dst))
                    self.log_message(f"  ✓ Copied: {rel_path}")
                else:
                    self.log_message(f"  ⚠ Source file not found: {rel_path}")
            except Exception as e:
                self.log_message(f"  ✗ Failed to copy {rel_path}: {e}")
        
        # Step 3: Run install commands
        for cmd in profile.get("install_commands", []):
            self._run_setup_command(cmd, worktree_path)
        
        # Step 4: Run post-setup commands
        for cmd in profile.get("post_commands", []):
            self._run_setup_command(cmd, worktree_path)
        
        # Step 5: Open in editor
        editor = self.editor_command
        if editor:
            try:
                import shlex
                # Use shell=True to support aliases and commands with arguments (like "code -n")
                if sys.platform == 'win32':
                    cmd = f'{editor} "{worktree_path}"'
                else:
                    cmd = f'{editor} {shlex.quote(str(worktree_path))}'
                
                subprocess.Popen(cmd, shell=True)
                self.log_message(f"  ✓ Opened in: {editor}")
            except Exception as e:
                self.log_message(f"  ✗ Failed to open editor: {e}")
        
        # Refresh tree
        self.parent.after(0, self.update_repo_tree)
        self.log_message("=== Worktree creation complete ===")

    def _run_setup_command(self, cmd, cwd):
        """Run a setup command cross-platform."""
        import shlex
        self.log_message(f"  Running: {cmd}")
        try:
            creation_flags = 0
            if sys.platform == 'win32':
                creation_flags = subprocess.CREATE_NO_WINDOW
                # Windows: use shell=True for commands like "npm install"
                process = subprocess.run(
                    cmd, cwd=cwd, shell=True,
                    capture_output=True, text=True, timeout=300,
                    creationflags=creation_flags
                )
            else:
                # Mac/Linux: split command properly
                process = subprocess.run(
                    shlex.split(cmd), cwd=cwd,
                    capture_output=True, text=True, timeout=300
                )
            
            if process.returncode == 0:
                self.log_message(f"    ✓ Success")
            else:
                self.log_message(f"    ✗ Exit code {process.returncode}")
                if process.stderr:
                    for line in process.stderr.strip().splitlines()[:3]:
                        self.log_message(f"      {line}")
        except subprocess.TimeoutExpired:
            self.log_message(f"    ✗ Timed out after 300s")
        except Exception as e:
            self.log_message(f"    ✗ Error: {e}")

    def remove_selected_worktree(self):
        path = self._get_selected_worktree_path()
        if not path:
            messagebox.showwarning("No Selection", "Select a worktree to remove.")
            return
            
        # Get parent repo path
        selected = self.repo_tree.selection()[0]
        parent = self.repo_tree.parent(selected)
        repo_path = self.repo_tree.item(parent, "text")
        
        if messagebox.askyesno("Confirm", f"Remove worktree?\n\n{path}"):
            try:
                remove_worktree(repo_path, path)
                self.log_message(f"✓ Removed worktree: {path}")
                self.update_repo_tree()
            except Exception as e:
                if messagebox.askyesno("Force Remove?", f"Normal removal failed:\n{e}\n\nForce remove?"):
                    try:
                        remove_worktree(repo_path, path, force=True)
                        self.log_message(f"✓ Force removed: {path}")
                        self.update_repo_tree()
                    except Exception as e2:
                        self.log_message(f"✗ Force remove failed: {e2}")

    def open_in_file_manager(self):
        path = self._get_selected_worktree_path()
        if not path:
            return
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.log_message(f"✗ Failed to open file manager: {e}")

    def open_in_editor(self):
        path = self._get_selected_worktree_path()
        if not path:
            return
            
        editor = self.editor_command
        if not editor:
            messagebox.showinfo("No Editor", "Set an editor command in the Setup Profile first.")
            return
            
        try:
            import shlex
            if sys.platform == 'win32':
                cmd = f'{editor} "{path}"'
            else:
                cmd = f'{editor} {shlex.quote(str(path))}'
                
            subprocess.Popen(cmd, shell=True)
            self.log_message(f"✓ Opened in editor: {path}")
        except Exception as e:
            self.log_message(f"✗ Failed to open editor: {e}")

    # --- Profile Helpers ---
    def _add_list_item(self, listbox, prompt_title, prompt_text):
        value = simpledialog.askstring(prompt_title, prompt_text, parent=self.parent)
        if value and value.strip():
            listbox.insert(tk.END, value.strip())

    def _remove_list_item(self, listbox):
        selected = listbox.curselection()
        if selected:
            listbox.delete(selected[0])

    def _move_list_item(self, listbox, direction):
        selected = listbox.curselection()
        if not selected:
            return
        idx = selected[0]
        new_idx = idx + direction
        if 0 <= new_idx < listbox.size():
            item = listbox.get(idx)
            listbox.delete(idx)
            listbox.insert(new_idx, item)
            listbox.selection_set(new_idx)

    def save_profile(self):
        # Global settings
        self.base_path = self.base_path_var.get().strip()
        self.editor_command = self.editor_var.get().strip()
        
        # Repo specific profile
        if self.selected_repo:
            profile = {
                "copy_files": list(self.copy_files_lb.get(0, tk.END)),
                "install_commands": list(self.install_cmds_lb.get(0, tk.END)),
                "post_commands": list(self.post_cmds_lb.get(0, tk.END)),
            }
            self.profiles[self.selected_repo] = profile
            
        self.save_configuration()
        self.log_message("✓ Settings and profile saved.")

    def load_profile_for_repo(self, repo_path):
        profile = self.profiles.get(repo_path, {})
        # Clear and populate each listbox
        for listbox, key in [
            (self.copy_files_lb, "copy_files"),
            (self.install_cmds_lb, "install_commands"),
            (self.post_cmds_lb, "post_commands"),
        ]:
            listbox.delete(0, tk.END)
            for item in profile.get(key, []):
                listbox.insert(tk.END, item)
