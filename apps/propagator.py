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

from config import Config


class GitPropagatorApp:
    def __init__(self, parent):
        """Initializes the Commit Propagator UI inside the provided parent widget (a tab)."""
        self.parent = parent
        self.repo_path = tk.StringVar()
        self.original_branch = ""
        self.all_branches = []
        self.prefs = Config.load_preferences()
        
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
        browse_button.pack(side=tk.LEFT)

        # 2. Source Branch Selection
        source_branch_frame = ttk.LabelFrame(main_frame, text="2. Select Source Branch", padding="10")
        source_branch_frame.pack(fill=tk.X, pady=5)
        
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
        process = subprocess.run(command_parts, cwd=self.repo_path.get(), capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if process.stdout: 
            self.log(process.stdout.strip())
        if process.stderr: 
            self.log(f"ERROR: {process.stderr.strip()}")
        if check: 
            process.check_returncode()
        return process.stdout.strip()

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
            
            # Save to preferences
            self.prefs['last_repo_path'] = path
            Config.save_preferences(self.prefs)
        elif path:
            messagebox.showerror("Error", "The selected folder is not a valid Git repository.")
    
    def filter_target_branches(self, event=None):
        """Filters the target branch listbox based on user input."""
        filter_term = self.target_branch_filter_var.get().lower()
        self.target_branch_listbox.delete(0, tk.END)
        for branch in self.all_branches:
            if filter_term in branch.lower():
                self.target_branch_listbox.insert(tk.END, branch)

    def update_all_branch_lists(self):
        try:
            branch_output = self.run_git_command("branch")
            branches = sorted([b.strip().replace("* ", "") for b in branch_output.splitlines()])
            self.all_branches = branches
            self.source_branch_combo['values'] = branches
            
            if branches:
                current_branch = self.run_git_command("rev-parse --abbrev-ref HEAD")
                if current_branch in branches: 
                    self.source_branch_combo.set(current_branch)
                else: 
                    self.source_branch_combo.current(0)
                self.load_commits(self.source_branch_combo.get())

            # Populate target list using the filter function
            self.target_branch_filter_var.set("")
            self.filter_target_branches()
        except (subprocess.CalledProcessError, ValueError) as e:
            messagebox.showerror("Git Error", f"Failed to load branch data:\n{e}")

    def on_source_branch_selected(self, event=None):
        selected_branch = self.source_branch_combo.get()
        if selected_branch: 
            self.load_commits(selected_branch)

    def load_commits(self, branch_name):
        self.commit_listbox.delete(0, tk.END)
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
            log_output = self.run_git_command(f"log {branch_name} --pretty=format:'%h|%s (%an)' -n {max_commits}")
            for line in log_output.splitlines(): 
                self.commit_listbox.insert(tk.END, line)
        except (subprocess.CalledProcessError, ValueError) as e:
            messagebox.showerror("Git Error", f"Failed to load commits for {branch_name}:\n{e}")

    def refresh_commits(self):
        self.on_source_branch_selected()

    def create_new_branch_popup(self):
        popup = tk.Toplevel(self.parent)
        popup.title("Create New Branch")
        popup.transient(self.parent)
        popup.grab_set()
        popup_width, popup_height = 400, 150
        main_win = self.parent.winfo_toplevel()
        position_x = main_win.winfo_x() + (main_win.winfo_width() // 2) - (popup_width // 2)
        position_y = main_win.winfo_y() + (main_win.winfo_height() // 2) - (popup_height // 2)
        popup.geometry(f"{popup_width}x{popup_height}+{position_x}+{position_y}")

        frame = ttk.Frame(popup, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Base Branch:").grid(row=0, column=0, sticky="w", pady=2)
        base_branch_combo = ttk.Combobox(frame, values=self.source_branch_combo['values'], state="readonly")
        base_branch_combo.set(self.source_branch_combo.get())
        base_branch_combo.grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Label(frame, text="New Branch Name:").grid(row=1, column=0, sticky="w", pady=2)
        new_branch_entry = ttk.Entry(frame)
        new_branch_entry.grid(row=1, column=1, sticky="ew", pady=2)
        new_branch_entry.focus_set()
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        create_btn = ttk.Button(button_frame, text="Create", command=lambda: self.handle_create_branch(popup, base_branch_combo, new_branch_entry))
        create_btn.pack(side=tk.LEFT, padx=5)
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=popup.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        frame.columnconfigure(1, weight=1)

    def handle_create_branch(self, popup, base_combo, new_name_entry):
        base_branch, new_branch_name = base_combo.get(), new_name_entry.get().strip()
        if not base_branch or not new_branch_name:
            messagebox.showwarning("Input Error", "Both fields are required.", parent=popup)
            return
        if new_branch_name in self.source_branch_combo['values']:
            messagebox.showerror("Error", f"Branch '{new_branch_name}' already exists.", parent=popup)
            return
        try:
            self.log(f"\n--- Creating new branch '{new_branch_name}' from '{base_branch}' ---")
            self.run_git_command(f"checkout -b {new_branch_name} {base_branch}")
            messagebox.showinfo("Success", f"Branch '{new_branch_name}' created.", parent=popup)
            popup.destroy()
            self.update_all_branch_lists()
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Git Error", f"Failed to create branch:\n{e}", parent=popup)

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
            commit_hash = self.commit_listbox.get(selected_indices[0]).split('|')[0]
            if not messagebox.askyesno("Confirm Action", f"Cherry-pick commit '{commit_hash}' onto:\n\n- {', '.join(target_branches)}\n\nProceed?"):
                return self.log("Operation cancelled.")
            
            self.propagate_button.config(state=tk.DISABLED)
            try:
                self.original_branch = self.run_git_command("rev-parse --abbrev-ref HEAD")
                for branch in target_branches:
                    self.log(f"\n--- Processing branch: {branch} ---")
                    try:
                        self.run_git_command(f"checkout {branch}")
                        self.run_git_command(f"cherry-pick {commit_hash}")
                        if self.push_changes_var.get():
                            self.log(f"Pushing changes for {branch} to origin...")
                            self.run_git_command(f"push origin {branch}")
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
                commits = [self.commit_listbox.get(i).split('|')[0] for i in selected_indices]
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
                                self.run_git_command(f"cherry-pick {commit_hash}")
                            if self.push_changes_var.get():
                                self.log(f"Pushing changes for {branch} to origin...")
                                self.run_git_command(f"push origin {branch}")
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
            commits = [self.commit_listbox.get(i).split('|')[0] for i in indices]
            commits_reversed = list(reversed(commits))  # Oldest first
            
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
                self.run_git_command(f"cherry-pick {commit}")
            
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
                        self.run_git_command(f"push origin {branch}")
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
