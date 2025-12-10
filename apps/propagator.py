"""
Git Commit Propagator Application.
Allows cherry-picking commits across multiple branches with support for combining commits.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import os
import shlex
import uuid
import threading

from config import Config
from ai.gemini_client import GeminiClient


class GitPropagatorApp:
    def __init__(self, parent):
        """Initializes the Commit Propagator UI inside the provided parent widget (a tab)."""
        self.parent = parent
        self.repo_path = tk.StringVar()
        self.original_branch = ""
        self.all_branches = []
        self.all_remote_branches = []
        self.prefs = Config.load_preferences()
        self.gemini_client = GeminiClient()
        # Store commit data with merge status: {hash: {"display": "...", "is_merge": bool, "parents": []}}
        self.commit_data = {}
        
        # Load saved repo path if available
        if self.prefs.get('last_repo_path'):
            self.repo_path.set(self.prefs['last_repo_path'])

        # --- UI Layout ---
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Repository Selection
        repo_frame = ttk.LabelFrame(main_frame, text="1. Select Git Repository", padding="10")
        repo_frame.pack(fill=tk.X, pady=5)
        
        repo_entry = ttk.Entry(repo_frame, textvariable=self.repo_path, width=70)
        repo_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        browse_button = ttk.Button(repo_frame, text="Browse...", command=self.browse_repository)
        browse_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Fetch and Pull buttons
        self.fetch_button = ttk.Button(repo_frame, text="🔄 Fetch", command=self.fetch_repository_threaded, state=tk.DISABLED)
        self.fetch_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.pull_button = ttk.Button(repo_frame, text="⬇️ Pull", command=self.pull_current_branch_threaded, state=tk.DISABLED)
        self.pull_button.pack(side=tk.LEFT)

        # 2. Source Branch Selection
        source_branch_frame = ttk.LabelFrame(main_frame, text="2. Select Source Branch", padding="10")
        source_branch_frame.pack(fill=tk.X, pady=5)
        
        # Checkbox to toggle remote branches
        source_controls = ttk.Frame(source_branch_frame)
        source_controls.pack(fill=tk.X, pady=(0, 5))
        
        self.show_remote_branches_var = tk.BooleanVar(value=False)
        remote_checkbox = ttk.Checkbutton(
            source_controls,
            text="Include remote branches (origin/*)",
            variable=self.show_remote_branches_var,
            command=self.update_source_branch_list
        )
        remote_checkbox.pack(side=tk.LEFT)
        
        # Filter for source branches
        ttk.Label(source_controls, text="Filter:").pack(side=tk.LEFT, padx=(20, 5))
        self.source_branch_filter_var = tk.StringVar()
        source_filter_entry = ttk.Entry(source_controls, textvariable=self.source_branch_filter_var, width=20)
        source_filter_entry.pack(side=tk.LEFT)
        source_filter_entry.bind("<KeyRelease>", lambda e: self.update_source_branch_list())
        
        self.source_branch_combo = ttk.Combobox(source_branch_frame, state="readonly")
        self.source_branch_combo.pack(fill=tk.X, expand=True)
        self.source_branch_combo.bind("<<ComboboxSelected>>", self.on_source_branch_selected)

        # 3 & 4. Selections Frame
        selection_frame = ttk.Frame(main_frame)
        selection_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        selection_frame.columnconfigure(0, weight=1)
        selection_frame.columnconfigure(1, weight=1)
        selection_frame.rowconfigure(0, weight=1)

        # 3. Commit Selection
        commit_frame = ttk.LabelFrame(selection_frame, text="3. Select Commit(s) to Propagate (Ctrl+Click for multiple)", padding="10")
        commit_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        commit_actions_frame = ttk.Frame(commit_frame)
        commit_actions_frame.pack(fill=tk.X, pady=(0, 5))

        # Max Commits Entry
        max_commits_default = self.prefs.get('propagator', {}).get('max_commits', 50)
        self.max_commits_var = tk.StringVar(value=str(max_commits_default))
        ttk.Label(commit_actions_frame, text="Max Commits:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(commit_actions_frame, textvariable=self.max_commits_var, width=5).pack(side=tk.LEFT)

        self.refresh_commits_button = ttk.Button(commit_actions_frame, text="Refresh", command=self.refresh_commits, state=tk.DISABLED)
        self.refresh_commits_button.pack(side=tk.RIGHT)
        
        # UPDATED: Changed selectmode to EXTENDED for multi-select
        self.commit_listbox = tk.Listbox(commit_frame, selectmode=tk.EXTENDED, exportselection=False, font=("Courier", 10))
        self.commit_listbox.pack(fill=tk.BOTH, expand=True)
        
        # 4. Target Branch Selection
        branch_frame = ttk.LabelFrame(selection_frame, text="4. Select Target Branches (Ctrl+Click)", padding="10")
        branch_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Target Branch Filter
        filter_frame = ttk.Frame(branch_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.target_branch_filter_var = tk.StringVar()
        filter_entry = ttk.Entry(filter_frame, textvariable=self.target_branch_filter_var)
        filter_entry.pack(fill=tk.X, expand=True)
        filter_entry.bind("<KeyRelease>", self.filter_target_branches)

        self.create_branch_button = ttk.Button(branch_frame, text="Create New Branch...", command=self.create_new_branch_popup, state=tk.DISABLED)
        self.create_branch_button.pack(fill=tk.X, pady=(0, 5))
        self.target_branch_listbox = tk.Listbox(branch_frame, selectmode=tk.EXTENDED, exportselection=False)
        self.target_branch_listbox.pack(fill=tk.BOTH, expand=True)

        # 5. Action Frame
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=5)
        
        # NEW: Combine commits checkbox
        self.combine_commits_var = tk.BooleanVar(value=False)
        combine_checkbox = ttk.Checkbutton(
            action_frame, 
            text="Combine selected commits into one", 
            variable=self.combine_commits_var
        )
        combine_checkbox.pack(side=tk.LEFT, padx=(0, 10))
        
        # NEW: Show merge commits checkbox
        self.show_merge_commits_var = tk.BooleanVar(value=False)
        merge_checkbox = ttk.Checkbutton(
            action_frame,
            text="Show merge commits",
            variable=self.show_merge_commits_var,
            command=self.refresh_commits
        )
        merge_checkbox.pack(side=tk.LEFT, padx=(0, 10))
        
        auto_push_default = self.prefs.get('propagator', {}).get('auto_push', False)
        self.push_changes_var = tk.BooleanVar(value=auto_push_default)
        push_checkbox = ttk.Checkbutton(action_frame, text="Push changes to 'origin' after success", variable=self.push_changes_var)
        push_checkbox.pack(side=tk.LEFT)
        
        self.propagate_button = ttk.Button(action_frame, text="Propagate Commit(s)", command=self.propagate_commit, state=tk.DISABLED)
        self.propagate_button.pack(side=tk.RIGHT)

        # 6. Log Output
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, state=tk.DISABLED, bg="black", fg="white")
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Auto-load if repo path was restored
        if self.repo_path.get() and os.path.isdir(os.path.join(self.repo_path.get(), '.git')):
            self.update_all_branch_lists()
            self.propagate_button.config(state=tk.NORMAL)
            self.create_branch_button.config(state=tk.NORMAL)
            self.refresh_commits_button.config(state=tk.NORMAL)
            self.fetch_button.config(state=tk.NORMAL)
            self.pull_button.config(state=tk.NORMAL)

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.parent.update_idletasks()

    def run_git_command(self, command, check=True):
        if not self.repo_path.get(): 
            raise ValueError("Repository path not set.")
        command_parts = ["git"] + shlex.split(command)
        self.log(f"> {' '.join(command_parts)}")
        
        # Hide console window on Windows
        import sys
        creation_flags = 0
        if sys.platform == 'win32':
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        process = subprocess.run(
            command_parts, 
            cwd=self.repo_path.get(), 
            capture_output=True, 
            text=True, 
            encoding='utf-8', 
            errors='ignore',
            creationflags=creation_flags
        )
        if process.stdout: 
            self.log(process.stdout.strip())
        if process.stderr: 
            self.log(f"ERROR: {process.stderr.strip()}")
        if check: 
            process.check_returncode()
        return process.stdout.strip()
    
    def is_merge_commit(self, commit_hash):
        """Check if a commit is a merge commit (has multiple parents)."""
        try:
            # Get parent commit hashes
            parents_output = self.run_git_command(f"rev-list --parents -n 1 {commit_hash}")
            # Output format: <commit_hash> <parent1> [<parent2> ...]
            # Split and check if there are more than 2 items (hash + more than 1 parent)
            parts = parents_output.split()
            return len(parts) > 2  # merge commit has 2+ parents
        except subprocess.CalledProcessError:
            return False
    
    def get_commit_parents(self, commit_hash):
        """Get the parent commit hashes for a commit."""
        try:
            parents_output = self.run_git_command(f"log --pretty=%P -n 1 {commit_hash}")
            return parents_output.split() if parents_output else []
        except subprocess.CalledProcessError:
            return []

    def browse_repository(self):
        path = filedialog.askdirectory(title="Select a Git repository folder")
        if path and os.path.isdir(os.path.join(path, '.git')):
            self.repo_path.set(path)
            self.log(f"Repository selected: {path}")
            self.commit_listbox.delete(0, tk.END)
            self.update_all_branch_lists()
            self.propagate_button.config(state=tk.NORMAL)
            self.create_branch_button.config(state=tk.NORMAL)
            self.refresh_commits_button.config(state=tk.NORMAL)
            self.fetch_button.config(state=tk.NORMAL)
            self.pull_button.config(state=tk.NORMAL)
            
            # Save to preferences
            self.prefs['last_repo_path'] = path
            Config.save_preferences(self.prefs)
        elif path:
            messagebox.showerror("Error", "The selected folder is not a valid Git repository.")
    
    def fetch_repository_threaded(self):
        """Fetch all branches from origin in a background thread."""
        if not self.repo_path.get():
            return messagebox.showwarning("Warning", "Please select a repository first.")
        
        self.fetch_button.config(state=tk.DISABLED, text="Fetching...")
        self.log("\n--- Fetching from origin ---")
        threading.Thread(target=self._fetch_worker, daemon=True).start()
    
    def _fetch_worker(self):
        """Worker thread for git fetch operation."""
        try:
            self.run_git_command("fetch origin")
            self.log("✅ Fetch completed successfully.")
            # Refresh branch lists after fetch
            self.parent.after(0, self.update_all_branch_lists)
        except subprocess.CalledProcessError as e:
            self.log(f"🛑 Fetch failed: {e}")
            self.parent.after(0, lambda: messagebox.showerror("Fetch Failed", f"Failed to fetch from origin:\n{e}"))
        finally:
            self.parent.after(0, lambda: self.fetch_button.config(state=tk.NORMAL, text="🔄 Fetch"))
    
    def pull_current_branch_threaded(self):
        """Show dialog to select which branch to pull from origin."""
        if not self.repo_path.get():
            return messagebox.showwarning("Warning", "Please select a repository first.")
        
        # Show branch selection dialog
        self.show_pull_branch_dialog()
    
    def show_pull_branch_dialog(self):
        """Show dialog for selecting which branch to pull."""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Pull Branch")
        dialog.geometry("450x350")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Select branch to pull from origin:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 10))
        
        # Filter entry
        filter_var = tk.StringVar()
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        filter_entry = ttk.Entry(filter_frame, textvariable=filter_var)
        filter_entry.pack(fill=tk.X, expand=True)
        
        # Branch listbox
        listbox_frame = ttk.Frame(main_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        branch_listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, exportselection=False)
        branch_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=branch_listbox.yview)
        
        # Get current branch
        try:
            current_branch = self.run_git_command("rev-parse --abbrev-ref HEAD")
        except subprocess.CalledProcessError:
            current_branch = None
        
        # Populate branches
        all_branches = []
        try:
            branch_output = self.run_git_command("branch")
            for b in branch_output.splitlines():
                branch_name = b.strip().replace("* ", "")
                all_branches.append(branch_name)
                if branch_name == current_branch:
                    branch_listbox.insert(tk.END, f"{branch_name} (current)")
                else:
                    branch_listbox.insert(tk.END, branch_name)
            
            # Select current branch by default
            if current_branch and current_branch in all_branches:
                idx = all_branches.index(current_branch)
                branch_listbox.selection_set(idx)
                branch_listbox.see(idx)
        except subprocess.CalledProcessError:
            pass
        
        def filter_branches(event=None):
            filter_text = filter_var.get().lower()
            branch_listbox.delete(0, tk.END)
            for branch in all_branches:
                if filter_text in branch.lower():
                    if branch == current_branch:
                        branch_listbox.insert(tk.END, f"{branch} (current)")
                    else:
                        branch_listbox.insert(tk.END, branch)
        
        filter_entry.bind("<KeyRelease>", filter_branches)
        
        def on_pull():
            selection = branch_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a branch to pull.")
                return
            
            selected_text = branch_listbox.get(selection[0])
            # Remove " (current)" suffix if present
            branch_name = selected_text.replace(" (current)", "")
            
            dialog.destroy()
            
            # Confirm and execute pull
            if messagebox.askyesno("Confirm Pull", 
                                   f"Pull latest changes for branch '{branch_name}' from origin?\n\n"
                                   f"This will update the local branch '{branch_name}'."):
                self.pull_button.config(state=tk.DISABLED, text="Pulling...")
                self.log(f"\n--- Pulling branch '{branch_name}' from origin ---")
                threading.Thread(target=self._pull_worker, args=(branch_name,), daemon=True).start()
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        ttk.Button(button_frame, text="Pull", command=on_pull).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
        
        # Double-click to pull
        branch_listbox.bind("<Double-Button-1>", lambda e: on_pull())
    
    def _pull_worker(self, branch_name):
        """Worker thread for git pull operation."""
        try:
            self.run_git_command(f"pull origin {branch_name}")
            self.log(f"✅ Successfully pulled '{branch_name}' from origin.")
            # Refresh commits after pull
            self.parent.after(0, lambda: self.load_commits(branch_name))
        except subprocess.CalledProcessError as e:
            self.log(f"🛑 Pull failed: {e}")
            self.parent.after(0, lambda: messagebox.showerror("Pull Failed", f"Failed to pull branch '{branch_name}':\n{e}\n\nYou may have local changes or conflicts."))
        finally:
            self.parent.after(0, lambda: self.pull_button.config(state=tk.NORMAL, text="⬇️ Pull"))
    
    def filter_target_branches(self, event=None):
        """Filters the target branch listbox based on user input."""
        filter_term = self.target_branch_filter_var.get().lower()
        self.target_branch_listbox.delete(0, tk.END)
        for branch in self.all_branches:
            if filter_term in branch.lower():
                self.target_branch_listbox.insert(tk.END, branch)

    def update_all_branch_lists(self):
        try:
            # Load local branches
            branch_output = self.run_git_command("branch")
            local_branches = sorted([b.strip().replace("* ", "") for b in branch_output.splitlines()])
            self.all_branches = local_branches
            
            # Load remote branches
            remote_output = self.run_git_command("branch -r")
            remote_branches = []
            for b in remote_output.splitlines():
                branch = b.strip()
                if "->" not in branch and branch.startswith("origin/"):
                    remote_branches.append(branch)
            self.all_remote_branches = sorted(remote_branches)
            
            # Update source branch list
            self.update_source_branch_list()
            
            if local_branches:
                current_branch = self.run_git_command("rev-parse --abbrev-ref HEAD")
                if current_branch in self.source_branch_combo['values']: 
                    self.source_branch_combo.set(current_branch)
                elif self.source_branch_combo['values']:
                    self.source_branch_combo.current(0)
                self.load_commits(self.source_branch_combo.get())

            # Populate target list using the filter function
            self.target_branch_filter_var.set("")
            self.filter_target_branches()
        except (subprocess.CalledProcessError, ValueError) as e:
            messagebox.showerror("Git Error", f"Failed to load branch data:\n{e}")
    
    def update_source_branch_list(self):
        """Updates source branch combobox based on filter and remote checkbox."""
        show_remote = self.show_remote_branches_var.get()
        filter_text = self.source_branch_filter_var.get().lower()
        
        # Combine local and remote branches if checkbox is enabled
        available_branches = self.all_branches.copy()
        if show_remote:
            available_branches.extend(self.all_remote_branches)
        
        # Apply filter
        filtered_branches = [b for b in available_branches if filter_text in b.lower()]
        
        # Store current selection
        current_value = self.source_branch_combo.get()
        
        # Update combobox
        self.source_branch_combo['values'] = filtered_branches
        
        # Restore selection if still valid
        if current_value in filtered_branches:
            self.source_branch_combo.set(current_value)
        elif filtered_branches:
            self.source_branch_combo.set(filtered_branches[0])

    def on_source_branch_selected(self, event=None):
        selected_branch = self.source_branch_combo.get()
        if selected_branch: 
            self.load_commits(selected_branch)

    def load_commits(self, branch_name):
        self.commit_listbox.delete(0, tk.END)
        self.commit_data.clear()
        try:
            max_commits = 50
            try:
                user_val = int(self.max_commits_var.get())
                if user_val > 0:
                    max_commits = user_val
            except (ValueError, TypeError):
                self.log("Warning: Invalid 'Max Commits' value. Using default of 50.")
                self.max_commits_var.set("50")

            self.log(f"\nLoading last {max_commits} commits for branch '{branch_name}'...")
            # Include parent info in log format
            log_output = self.run_git_command(f"log {branch_name} --pretty=format:'%h|%P|%s (%an)' -n {max_commits}")
            
            show_merge = self.show_merge_commits_var.get()
            
            for line in log_output.splitlines():
                if '|' not in line:
                    continue
                
                parts = line.split('|', 2)  # Split into hash, parents, message
                if len(parts) < 3:
                    continue
                    
                commit_hash = parts[0]
                parents_str = parts[1]
                message = parts[2]
                
                # Check if merge commit (2+ parents)
                parents = parents_str.split() if parents_str else []
                is_merge = len(parents) > 1
                
                # Store commit data
                display_text = f"{commit_hash}|{message}"
                if is_merge:
                    display_text = f"🔀 {display_text}"  # Add merge indicator
                
                self.commit_data[commit_hash] = {
                    "display": display_text,
                    "is_merge": is_merge,
                    "parents": parents,
                    "message": message
                }
                
                # Add to listbox based on filter
                if show_merge or not is_merge:
                    self.commit_listbox.insert(tk.END, display_text)
        except (subprocess.CalledProcessError, ValueError) as e:
            messagebox.showerror("Git Error", f"Failed to load commits for {branch_name}:\n{e}")

    def refresh_commits(self):
        self.on_source_branch_selected()

    def create_new_branch_popup(self):
        if not self.repo_path.get():
            return messagebox.showwarning("Warning", "Please select a repository first.")
        
        dialog = tk.Toplevel(self.parent)
        dialog.title("Create New Branch")
        dialog.geometry("450x450")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # --- Branch Name Section ---
        name_frame = ttk.Frame(dialog)
        name_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(name_frame, text="New Branch Name:").pack(anchor=tk.W)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=name_var, width=45)
        name_entry.pack(fill=tk.X, expand=True)

        # AI Generation
        ai_frame = ttk.Frame(name_frame)
        ai_frame.pack(fill=tk.X, pady=(5,0))

        prefix_var = tk.StringVar(value="feature/")
        ttk.Label(ai_frame, text="Prefix:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Entry(ai_frame, textvariable=prefix_var, width=15).pack(side=tk.LEFT)

        self.ai_branch_btn = ttk.Button(ai_frame, text="✨ Generate with AI",
                                        command=lambda: self.generate_branch_name_threaded(name_var, prefix_var.get()))
        self.ai_branch_btn.pack(side=tk.RIGHT)
        
        # --- Source Section ---
        from_origin_var = tk.BooleanVar()
        origin_frame = ttk.LabelFrame(dialog, text="Source (Optional)", padding=10)
        origin_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Defined here for lambda closure
        combo = ttk.Combobox(origin_frame, state=tk.DISABLED, width=35)
        status_lbl = ttk.Label(origin_frame, text="", font=("", 8), foreground="gray")
        
        chk = ttk.Checkbutton(origin_frame, text="Checkout from Origin", variable=from_origin_var, 
                              command=lambda: self._toggle_origin_combo(combo, from_origin_var, status_lbl))
        chk.pack(anchor=tk.W)
        
        lbl = ttk.Label(origin_frame, text="Select Remote Branch:")
        lbl.pack(anchor=tk.W, pady=(5, 0))

        # Add a filter entry
        filter_var = tk.StringVar()
        filter_entry = ttk.Entry(origin_frame, textvariable=filter_var, width=35)
        filter_entry.pack(pady=5)
        filter_entry.bind("<KeyRelease>", lambda e: self._filter_remote_branches(combo, filter_var.get()))

        combo.pack(pady=5)
        status_lbl.pack()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Create", 
                   command=lambda: self._create_branch_action(dialog, name_var.get(), from_origin_var.get(), combo.get())).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT)

    def generate_branch_name_threaded(self, name_var, prefix):
        if not self.gemini_client.api_key:
            return messagebox.showerror("Error", "Gemini API Key not configured.")
        
        # Check if there are any staged changes
        try:
            diff_output = self.run_git_command("diff --cached")
            if not diff_output:
                return messagebox.showwarning("Warning", "No staged changes to generate a branch name from. Please stage files first.")
        except subprocess.CalledProcessError:
            return messagebox.showwarning("Warning", "Could not check repository status.")

        self.ai_branch_btn.config(state=tk.DISABLED, text="Generating...")
        threading.Thread(target=self._generate_branch_name_worker, args=(name_var, prefix), daemon=True).start()

    def _generate_branch_name_worker(self, name_var, prefix):
        try:
            # Only consider staged changes
            diff = self.run_git_command("diff --cached")
            
            if not diff:
                self.parent.after(0, lambda: messagebox.showinfo("Info", "No staged changes to analyze."))
                return

            branch_name = self.gemini_client.generate_branch_name(diff, prefix)
            self.parent.after(0, lambda: name_var.set(branch_name))
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Error", f"Failed to generate branch name:\n{e}"))
        finally:
            self.parent.after(0, lambda: self.ai_branch_btn.config(state=tk.NORMAL, text="✨ Generate with AI"))

    def _toggle_origin_combo(self, combo, var, status_lbl):
        if var.get():
            combo.config(state="readonly")
            status_lbl.config(text="Fetching origin branches...")
            self.parent.update_idletasks()
            threading.Thread(target=self._fetch_remote_branches_worker, args=(combo, status_lbl), daemon=True).start()
        else:
            combo.config(state=tk.DISABLED)
            status_lbl.config(text="")

    def _fetch_remote_branches_worker(self, combo, status_lbl):
        try:
            self.run_git_command("fetch origin")
            out = self.run_git_command("branch -r")
            branches = []
            for line in out.splitlines():
                line = line.strip()
                if "->" in line: continue
                if line.startswith("origin/"):
                    branches.append(line.replace("origin/", "", 1))
            
            self.all_remote_branches = sorted(branches)

            def update_ui():
                combo['values'] = self.all_remote_branches
                status_lbl.config(text=f"Found {len(self.all_remote_branches)} remote branches.")
                if self.all_remote_branches:
                    combo.current(0)
            self.parent.after(0, update_ui)
        except Exception as e:
            def show_err():
                status_lbl.config(text="Error fetching branches (Check network/remote)")
            self.parent.after(0, show_err)

    def _filter_remote_branches(self, combo, filter_text):
        if not hasattr(self, 'all_remote_branches'):
            return

        filtered_list = [b for b in self.all_remote_branches if filter_text.lower() in b.lower()]
        current_val = combo.get()
        combo['values'] = filtered_list
        if current_val in filtered_list:
            combo.set(current_val)
        elif filtered_list:
            combo.set(filtered_list[0])
        else:
            combo.set('')

    def prompt_merge_parent_selection(self, commit_hash):
        """Prompt user to select which parent to use for cherry-picking a merge commit."""
        parents = self.get_commit_parents(commit_hash)
        if len(parents) < 2:
            return None
        
        dialog = tk.Toplevel(self.parent)
        dialog.title("Select Merge Parent")
        dialog.geometry("500x300")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text=f"Commit {commit_hash} is a merge commit.", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(main_frame, text="Select which parent to follow for cherry-pick:", font=("Arial", 9)).pack(anchor="w", pady=(0, 10))
        
        parent_var = tk.IntVar(value=1)
        
        for idx, parent in enumerate(parents, 1):
            # Get parent commit subject
            try:
                parent_subject = self.run_git_command(f"log --oneline -n 1 {parent}")
            except subprocess.CalledProcessError:
                parent_subject = f"{parent} (unable to fetch details)"
            
            label_text = f"Parent {idx}: {parent_subject}"
            if idx == 1:
                label_text += " (usually target/main branch)"
            elif idx == 2:
                label_text += " (usually feature branch)"
            
            ttk.Radiobutton(main_frame, text=label_text, variable=parent_var, value=idx).pack(anchor="w", pady=5)
        
        result = {'selection': None}
        
        def on_ok():
            result['selection'] = parent_var.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT)
        
        dialog.wait_window()
        return result['selection']
    
    def _create_branch_action(self, dialog, name, from_origin, remote_branch):
        if not name:
            return messagebox.showerror("Error", "Branch name required.")
        if " " in name:
             return messagebox.showwarning("Warning", "Branch names cannot contain spaces.")
        
        args = ["checkout", "-b", name]
        if from_origin:
            if not remote_branch:
                return messagebox.showerror("Error", "Please select a remote branch.")
            args.append(f"origin/{remote_branch}")
            
        try:
            # Build command string for run_git_command
            cmd = " ".join(args)
            out = self.run_git_command(cmd)
            if "Switched to a new branch" in out or "Switched to branch" in out or not out: 
                # Git output varies, sometimes stderr has the message.
                # If run_git_command didn't raise, it's mostly success.
                pass
            
            messagebox.showinfo("Success", f"Branch '{name}' created!\n\n{out}")
            dialog.destroy()
            self.update_all_branch_lists()
        except Exception as e:
            # Subprocess.CalledProcessError
            if hasattr(e, 'stderr') and e.stderr:
                 messagebox.showerror("Error", f"Failed to create branch:\n{e.stderr}")
            else:
                 messagebox.showerror("Error", f"Failed to create branch:\n{e}")

    def propagate_commit(self):
        """Main propagation logic supporting both single and multiple commit selection."""
        selected_indices = self.commit_listbox.curselection()
        if not selected_indices: 
            return messagebox.showwarning("Warning", "Please select at least one commit.")

        selected_branch_indices = self.target_branch_listbox.curselection()
        if not selected_branch_indices: 
            return messagebox.showwarning("Warning", "Please select target branches.")
        target_branches = [self.target_branch_listbox.get(i) for i in selected_branch_indices]

        # Single commit - existing logic
        if len(selected_indices) == 1:
            commit_display = self.commit_listbox.get(selected_indices[0])
            # Remove merge indicator if present
            commit_hash = commit_display.replace('🔀 ', '').split('|')[0]
            
            # Check if it's a merge commit and prompt for parent
            merge_parent = None
            if self.commit_data.get(commit_hash, {}).get('is_merge', False):
                merge_parent = self.prompt_merge_parent_selection(commit_hash)
                if merge_parent is None:
                    return self.log("Operation cancelled - no parent selected.")
            
            if not messagebox.askyesno("Confirm Action", f"Cherry-pick commit '{commit_hash}' onto:\n\n- {', '.join(target_branches)}\n\nProceed?"):
                return self.log("Operation cancelled.")
            
            self.propagate_button.config(state=tk.DISABLED)
            try:
                self.original_branch = self.run_git_command("rev-parse --abbrev-ref HEAD")
                for branch in target_branches:
                    self.log(f"\n--- Processing branch: {branch} ---")
                    try:
                        self.run_git_command(f"checkout {branch}")
                        # Add -m option if it's a merge commit
                        cherry_pick_cmd = f"cherry-pick {commit_hash}"
                        if merge_parent:
                            cherry_pick_cmd = f"cherry-pick -m {merge_parent} {commit_hash}"
                        self.run_git_command(cherry_pick_cmd)
                        if self.push_changes_var.get():
                            self.log(f"Pushing changes for {branch} to origin...")
                            self.run_git_command(f"push -u origin {branch}")
                        self.log(f"✅ Successfully propagated to {branch}")
                    except subprocess.CalledProcessError:
                        self.log(f"🛑 FAILED on {branch}. A merge conflict likely occurred.")
                        messagebox.showerror("Cherry-Pick Failed", f"Failed on '{branch}'. Please resolve conflict.")
                        return
            finally:
                if self.original_branch:
                    self.log(f"\n--- Returning to original branch: {self.original_branch} ---")
                    try: 
                        self.run_git_command(f"checkout {self.original_branch}")
                    except subprocess.CalledProcessError: 
                        self.log("WARNING: Could not return to original branch.")
                self.propagate_button.config(state=tk.NORMAL)
                self.log("\n--- Propagation process finished. ---")
        
        # Multiple commits
        else:
            if self.combine_commits_var.get():
                # Combine and propagate
                combined_message = self.prompt_combined_commit_message(selected_indices)
                if not combined_message:
                    return  # User cancelled
                
                self.combine_and_propagate(selected_indices, combined_message, target_branches)
            else:
                # Propagate each commit individually
                commits = [self.commit_listbox.get(i).replace('🔀 ', '').split('|')[0] for i in selected_indices]
                # REVERSE the list to process oldest-to-newest, which is the correct chronological order for cherry-picking
                commits.reverse()
                
                # Check for merge commits and prompt for parents
                merge_parents = {}  # {commit_hash: parent_index}
                for commit_hash in commits:
                    if self.commit_data.get(commit_hash, {}).get('is_merge', False):
                        parent = self.prompt_merge_parent_selection(commit_hash)
                        if parent is None:
                            return self.log("Operation cancelled - no parent selected for merge commit.")
                        merge_parents[commit_hash] = parent
                if not messagebox.askyesno("Confirm Action", f"Cherry-pick {len(commits)} commits individually onto:\n\n- {', '.join(target_branches)}\n\nProceed?"):
                    return self.log("Operation cancelled.")
                
                self.propagate_button.config(state=tk.DISABLED)
                try:
                    self.original_branch = self.run_git_command("rev-parse --abbrev-ref HEAD")
                    for branch in target_branches:
                        self.log(f"\n--- Processing branch: {branch} ---")
                        try:
                            self.run_git_command(f"checkout {branch}")
                            for commit_hash in commits:
                                self.log(f"Cherry-picking {commit_hash}...")
                                # Add -m option if it's a merge commit
                                cherry_pick_cmd = f"cherry-pick {commit_hash}"
                                if commit_hash in merge_parents:
                                    cherry_pick_cmd = f"cherry-pick -m {merge_parents[commit_hash]} {commit_hash}"
                                self.run_git_command(cherry_pick_cmd)
                            if self.push_changes_var.get():
                                self.log(f"Pushing changes for {branch} to origin...")
                                self.run_git_command(f"push -u origin {branch}")
                            self.log(f"✅ Successfully propagated all commits to {branch}")
                        except subprocess.CalledProcessError:
                            self.log(f"🛑 FAILED on {branch}. A merge conflict likely occurred.")
                            messagebox.showerror("Cherry-Pick Failed", f"Failed on '{branch}'. Please resolve conflict.")
                            return
                finally:
                    if self.original_branch:
                        self.log(f"\n--- Returning to original branch: {self.original_branch} ---")
                        try: 
                            self.run_git_command(f"checkout {self.original_branch}")
                        except subprocess.CalledProcessError: 
                            self.log("WARNING: Could not return to original branch.")
                    self.propagate_button.config(state=tk.NORMAL)
                    self.log("\n--- Propagation process finished. ---")

    def prompt_combined_commit_message(self, indices):
        """
        Shows dialog for editing the combined commit message.
        Returns: message string or None if cancelled
        """
        popup = tk.Toplevel(self.parent)
        popup.title("Combined Commit Message")
        popup.transient(self.parent)
        popup.grab_set()
        popup_width, popup_height = 600, 400
        main_win = self.parent.winfo_toplevel()
        position_x = main_win.winfo_x() + (main_win.winfo_width() // 2) - (popup_width // 2)
        position_y = main_win.winfo_y() + (main_win.winfo_height() // 2) - (popup_height // 2)
        popup.geometry(f"{popup_width}x{popup_height}+{position_x}+{position_y}")

        frame = ttk.Frame(popup, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Show selected commits (read-only)
        ttk.Label(frame, text="Combining these commits:").pack(anchor="w", pady=(0, 5))
        commits_list = tk.Listbox(frame, height=5)
        commits_list.pack(fill=tk.X, pady=(0, 10))
        for idx in indices:
            commit_info = self.commit_listbox.get(idx)
            commits_list.insert(tk.END, commit_info)
        
        # Editable commit message
        ttk.Label(frame, text="Edit the combined commit message:").pack(anchor="w", pady=(0, 5))
        
        # Build suggested message from all commit messages
        suggested_messages = []
        for idx in indices:
            commit_line = self.commit_listbox.get(idx)
            # Extract message part (between | and (author))
            if '|' in commit_line:
                msg_part = commit_line.split('|')[1]
                if '(' in msg_part:
                    msg_part = msg_part[:msg_part.rfind('(')].strip()
                suggested_messages.append(msg_part)
        
        suggested = "\n\n".join(suggested_messages)
        
        message_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=10)
        message_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        message_text.insert("1.0", suggested)
        message_text.focus_set()
        
        result = {'message': None}
        
        def on_ok():
            result['message'] = message_text.get("1.0", tk.END).strip()
            popup.destroy()
        
        def on_cancel():
            popup.destroy()
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X)
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT)
        
        popup.wait_window()
        return result['message']

    def combine_and_propagate(self, indices, message, targets):
        """
        Combines multiple commits into one and propagates to target branches.
        
        1. Create temp branch from first commit's parent
        2. Cherry-pick all selected commits
        3. Squash using git reset --soft
        4. Create new commit with custom message
        5. Cherry-pick the combined commit to targets
        6. Clean up temp branch
        """
        temp_branch = f"temp-combine-{uuid.uuid4().hex[:8]}"
        
        try:
            self.log(f"\n--- Combining {len(indices)} commits ---")
            self.propagate_button.config(state=tk.DISABLED)
            
            # Get commit hashes (need to reverse to get chronological order)
            commits = [self.commit_listbox.get(i).replace('🔀 ', '').split('|')[0] for i in indices]
            commits_reversed = list(reversed(commits))  # Oldest first
            
            # Check for merge commits and prompt for parents
            merge_parents = {}  # {commit_hash: parent_index}
            for commit_hash in commits_reversed:
                if self.commit_data.get(commit_hash, {}).get('is_merge', False):
                    parent = self.prompt_merge_parent_selection(commit_hash)
                    if parent is None:
                        self.log("Operation cancelled - no parent selected for merge commit.")
                        return
                    merge_parents[commit_hash] = parent
            
            self.log(f"Commits to combine (oldest first): {', '.join(commits_reversed)}")
            
            # Save original branch
            self.original_branch = self.run_git_command("rev-parse --abbrev-ref HEAD")
            
            # Find the parent of the first (oldest) commit
            base_commit = self.run_git_command(f"rev-parse {commits_reversed[0]}^")
            self.log(f"Base commit: {base_commit}")
            
            # Create temporary branch from base
            self.run_git_command(f"checkout -b {temp_branch} {base_commit}")
            self.log(f"Created temporary branch: {temp_branch}")
            
            # Cherry-pick all commits
            for commit in commits_reversed:
                self.log(f"Cherry-picking {commit}...")
                # Add -m option if it's a merge commit
                cherry_pick_cmd = f"cherry-pick {commit}"
                if commit in merge_parents:
                    cherry_pick_cmd = f"cherry-pick -m {merge_parents[commit]} {commit}"
                self.run_git_command(cherry_pick_cmd)
            
            # Squash: reset soft to base, then commit with new message
            self.log("Squashing commits...")
            self.run_git_command(f"reset --soft {base_commit}")
            self.run_git_command(f"commit -m {shlex.quote(message)}")
            
            # Get the new combined commit hash
            combined_hash = self.run_git_command("rev-parse HEAD")
            self.log(f"✅ Created combined commit: {combined_hash}")
            
            # Now cherry-pick this combined commit to all target branches
            for branch in targets:
                self.log(f"\n--- Applying combined commit to branch: {branch} ---")
                try:
                    self.run_git_command(f"checkout {branch}")
                    self.run_git_command(f"cherry-pick {combined_hash}")
                    if self.push_changes_var.get():
                        self.log(f"Pushing changes for {branch} to origin...")
                        self.run_git_command(f"push -u origin {branch}")
                    self.log(f"✅ Successfully propagated to {branch}")
                except subprocess.CalledProcessError:
                    self.log(f"🛑 FAILED on {branch}. A merge conflict likely occurred.")
                    messagebox.showerror("Cherry-Pick Failed", f"Failed on '{branch}'. Please resolve conflict.")
                    return
            
            self.log("\n--- Combined commit propagation successful! ---")
            
        except subprocess.CalledProcessError as e:
            self.log(f"🛑 ERROR during combine operation: {e}")
            messagebox.showerror("Combine Failed", "Failed to combine commits. Check the log for details.")
        finally:
            # Cleanup: delete temp branch and return to original
            try:
                if self.original_branch:
                    self.run_git_command(f"checkout {self.original_branch}")
                self.run_git_command(f"branch -D {temp_branch}")
                self.log(f"Cleaned up temporary branch: {temp_branch}")
            except subprocess.CalledProcessError:
                self.log(f"WARNING: Could not clean up temp branch or return to original branch.")
            
            self.propagate_button.config(state=tk.NORMAL)
            self.log("\n--- Propagation process finished. ---")
