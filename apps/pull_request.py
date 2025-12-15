"""
Pull Request Creator Application.
Creates GitHub pull requests using the gh CLI.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import webbrowser
import subprocess
import os
import shutil
import sys

from config import Config
from ai.gemini_client import GeminiClient


class PullRequestApp:
    def __init__(self, parent):
        self.parent = parent
        self.repo_path = tk.StringVar()
        self.all_branches = []
        self.source_filter_var = tk.StringVar()
        self.target_filter_var = tk.StringVar()
        self.prefs = Config.load_preferences()
        self.gemini_client = GeminiClient()

        self.main_frame = ttk.Frame(self.parent, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.build_ui()
        self._check_gh_cli()

    def _check_gh_cli(self):
        # 0. Check for custom path in preferences
        custom_gh = self.prefs.get('gh_path', '').strip()
        if custom_gh and os.path.exists(custom_gh):
            # If it's a file (e.g. /path/to/gh), get directory
            if os.path.isfile(custom_gh):
                gh_dir = os.path.dirname(custom_gh)
            else:
                gh_dir = custom_gh
            
            # Prepend to PATH
            os.environ["PATH"] = gh_dir + os.pathsep + os.environ["PATH"]
            print(f"DEBUG: Using custom gh path: {gh_dir}")

        # On macOS, GUI apps often don't inherit the shell PATH, so we manually check common locations
        if sys.platform == 'darwin' and not shutil.which("gh"):
            common_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
            for p in common_paths:
                gh_path = os.path.join(p, "gh")
                if os.path.exists(gh_path):
                    # Found it! Add to PATH for this process so subprocess can find it
                    os.environ["PATH"] += os.pathsep + p
                    print(f"DEBUG: Found gh at {gh_path}, added to PATH")
                    break

        if not shutil.which("gh"):
            for widget in self.main_frame.winfo_children():
                widget.destroy()
            
            error_msg = ("GitHub CLI ('gh') not found.\n\n"
                         "This tool is required to create pull requests.\n"
                         "Please install it from 'https://cli.github.com/'\n"
                         "and ensure it is in your system's PATH.")
            
            error_label = ttk.Label(self.main_frame, text=error_msg, justify=tk.CENTER, font=("", 12))
            error_label.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
            return False
        return True

    def build_ui(self):
        # 1. Repository Selection
        repo_frame = ttk.LabelFrame(self.main_frame, text="1. Select Git Repository", padding="10")
        repo_frame.pack(fill=tk.X, pady=5)
        ttk.Entry(repo_frame, textvariable=self.repo_path, width=70).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(repo_frame, text="Browse...", command=self.browse_repository).pack(side=tk.LEFT)

        # 2. Branch Selection
        branch_frame = ttk.LabelFrame(self.main_frame, text="2. Select Branches", padding="10")
        branch_frame.pack(fill=tk.X, pady=5)
        branch_frame.columnconfigure(1, weight=1)

        # Controls row
        controls_frame = ttk.Frame(branch_frame)
        controls_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        refresh_button = ttk.Button(controls_frame, text="Refresh Branch List", command=self._load_branches)
        refresh_button.pack(side=tk.RIGHT)

        # Source Branch
        ttk.Label(branch_frame, text="Filter Source:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        source_filter_entry = ttk.Entry(branch_frame, textvariable=self.source_filter_var)
        source_filter_entry.grid(row=1, column=1, sticky="ew", pady=2)
        source_filter_entry.bind("<KeyRelease>", lambda e: self._filter_branches('source'))
        ttk.Label(branch_frame, text="Source Branch:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.source_branch_combo = ttk.Combobox(branch_frame, state="readonly")
        self.source_branch_combo.grid(row=2, column=1, sticky="ew", pady=(2, 10))
        self.source_branch_combo.bind("<<ComboboxSelected>>", self._on_source_branch_selected)

        # Target Branch
        ttk.Label(branch_frame, text="Filter Target:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        target_filter_entry = ttk.Entry(branch_frame, textvariable=self.target_filter_var)
        target_filter_entry.grid(row=3, column=1, sticky="ew", pady=2)
        target_filter_entry.bind("<KeyRelease>", lambda e: self._filter_branches('target'))
        ttk.Label(branch_frame, text="Target Branch:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.target_branch_combo = ttk.Combobox(branch_frame, state="readonly")
        self.target_branch_combo.grid(row=4, column=1, sticky="ew", pady=2)
        self.target_branch_combo.bind("<<ComboboxSelected>>", self._on_target_branch_selected)

        # 3. PR Details
        details_frame = ttk.LabelFrame(self.main_frame, text="3. Pull Request Details", padding="10")
        details_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        details_frame.columnconfigure(1, weight=1)

        # Title row with AI button
        title_row = ttk.Frame(details_frame)
        title_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=2)
        title_row.columnconfigure(1, weight=1)
        
        ttk.Label(title_row, text="Title:").pack(side=tk.LEFT, padx=(0, 5))
        self.title_entry = ttk.Entry(title_row)
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.ai_button = ttk.Button(title_row, text="✨ Generate with AI", command=self._generate_with_ai)
        self.ai_button.pack(side=tk.LEFT)
        
        ttk.Label(details_frame, text="Description:").grid(row=1, column=0, sticky="nw", pady=2, padx=5)
        self.description_text = scrolledtext.ScrolledText(details_frame, height=5, wrap=tk.WORD)
        self.description_text.grid(row=1, column=1, sticky="nsew", pady=2)
        details_frame.rowconfigure(1, weight=1)

        # 4. Preview Tabs (Files & Commits)
        preview_frame = ttk.LabelFrame(self.main_frame, text="4. Preview Changes", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.preview_notebook = ttk.Notebook(preview_frame)
        self.preview_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Files Tab
        self.files_tree = ttk.Treeview(self.preview_notebook, columns=("file", "stats"), show="headings")
        self.files_tree.heading("file", text="File Path")
        self.files_tree.heading("stats", text="Changes")
        self.files_tree.column("file", width=400)
        self.files_tree.column("stats", width=150)
        self.preview_notebook.add(self.files_tree, text="Files Changed")
        
        # Commits Tab
        self.commits_tree = ttk.Treeview(self.preview_notebook, columns=("hash", "author", "date", "subject"), show="headings")
        self.commits_tree.heading("hash", text="Hash")
        self.commits_tree.heading("author", text="Author")
        self.commits_tree.heading("date", text="Date")
        self.commits_tree.heading("subject", text="Subject")
        self.commits_tree.column("hash", width=80)
        self.commits_tree.column("author", width=150)
        self.commits_tree.column("date", width=150)
        self.commits_tree.column("subject", width=400)
        self.preview_notebook.add(self.commits_tree, text="Commits")

        # 5. Action Buttons
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.view_gh_button = ttk.Button(button_frame, text="View on GitHub", command=self._open_github_link, state=tk.DISABLED)
        self.view_gh_button.pack(side=tk.RIGHT, padx=5)
        
        self.create_pr_button = ttk.Button(button_frame, text="Create Pull Request", command=self.create_pull_request, state=tk.DISABLED)
        self.create_pr_button.pack(side=tk.RIGHT)
        
        # Log Output
        self.log_text = scrolledtext.ScrolledText(self.main_frame, height=5, state="disabled", wrap="word", bg="black", fg="white")
        self.log_text.pack(fill=tk.X, pady=5)

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.parent.update_idletasks()

    def _run_command(self, command_parts, check=True):
        if not self.repo_path.get():
            raise ValueError("Repository path not set.")
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

    def browse_repository(self):
        path = filedialog.askdirectory(title="Select a Git repository folder")
        if path and os.path.isdir(os.path.join(path, '.git')):
            self.repo_path.set(path)
            self.log(f"Repository selected: {path}")
            self._load_branches()
            self.create_pr_button.config(state=tk.NORMAL)
        elif path:
            messagebox.showerror("Error", "The selected folder is not a valid Git repository.")

    def _filter_branches(self, combo_type):
        """Filters the branch list for the specified combobox."""
        if combo_type == 'source':
            filter_term = self.source_filter_var.get().lower()
            combo = self.source_branch_combo
            current_val = combo.get()
        else:  # 'target'
            filter_term = self.target_filter_var.get().lower()
            combo = self.target_branch_combo
            current_val = combo.get()

        filtered_list = [b for b in self.all_branches if filter_term in b.lower()]
        combo['values'] = filtered_list

        if current_val in filtered_list:
            combo.set(current_val)
        elif filtered_list:
            combo.set('')
        else:
            combo.set('')

    def _load_branches(self):
        try:
            self.log("\n--- Loading branches ---")
            branch_output = self._run_command(["git", "branch", "-a"])
            branches = []
            current_branch = ""
            
            for line in branch_output.splitlines():
                clean_branch = line.strip().replace("* ", "")
                if "->" in clean_branch:
                    continue  # Skip symbolic refs
                if line.startswith("*"):
                    current_branch = clean_branch
                if clean_branch.startswith("remotes/origin/"):
                    clean_branch = clean_branch.replace("remotes/origin/", "")
                if clean_branch not in branches:
                    branches.append(clean_branch)
            
            self.all_branches = sorted(branches)
            
            # Reset filters and populate comboboxes
            self.source_filter_var.set("")
            self.target_filter_var.set("")
            self._filter_branches('source')
            self._filter_branches('target')
            
            if current_branch in self.source_branch_combo['values']:
                self.source_branch_combo.set(current_branch)
            
            # Set default target
            default_target = self.prefs.get('pr_creator', {}).get('default_target', 'main')
            for default in [default_target, "main", "master", "develop"]:
                if default in self.target_branch_combo['values']:
                    self.target_branch_combo.set(default)
                    break
            
            self._on_source_branch_selected()
        except (subprocess.CalledProcessError, ValueError) as e:
            messagebox.showerror("Git Error", f"Failed to load branch data:\n{e}")

    def _update_preview(self):
        """Updates the files and commits preview tabs."""
        source = self.source_branch_combo.get()
        target = self.target_branch_combo.get()
        
        if not source or not target or source == target:
            return

        # Clear existing items
        self.files_tree.delete(*self.files_tree.get_children())
        self.commits_tree.delete(*self.commits_tree.get_children())
        
        try:
            # 1. Get Files Changed (git diff --stat)
            # Use origin/ prefix if available, else local
            base_ref = f"origin/{target}" if f"origin/{target}" in self.all_branches or True else target # Simplified logic, usually origin exists
            head_ref = source # Local source
            
            # Check if origin/target exists, if not try local target
            # Actually, let's just try generic logic:
            # If we are pushing source to origin, we compare source against origin/target usually.
            
            # Let's try to find the merge base or just use dot-dot-dot
            # git diff --stat origin/target...source
            
            diff_cmd = ["git", "diff", "--stat", f"origin/{target}...{source}"]
            stat_output = self._run_command(diff_cmd, check=False)
            
            if not stat_output.strip():
                 # Try local target
                 diff_cmd = ["git", "diff", "--stat", f"{target}...{source}"]
                 stat_output = self._run_command(diff_cmd, check=False)

            for line in stat_output.splitlines():
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) == 2:
                        fpath = parts[0].strip()
                        stats = parts[1].strip()
                        self.files_tree.insert("", "end", values=(fpath, stats))

            # 2. Get Commits (git log)
            log_cmd = ["git", "log", "--pretty=format:%h|%an|%ai|%s", f"origin/{target}..{source}"]
            log_output = self._run_command(log_cmd, check=False)
            
            if not log_output.strip():
                log_cmd = ["git", "log", "--pretty=format:%h|%an|%ai|%s", f"{target}..{source}"]
                log_output = self._run_command(log_cmd, check=False)

            for line in log_output.splitlines():
                parts = line.split("|")
                if len(parts) >= 4:
                    h = parts[0]
                    auth = parts[1]
                    date = parts[2]
                    subj = "|".join(parts[3:])
                    self.commits_tree.insert("", "end", values=(h, auth, date, subj))
                    
        except Exception as e:
            self.log(f"Error updating preview: {e}")

    def _open_github_link(self):
        """Opens the PR link in browser."""
        if hasattr(self, 'pr_url') and self.pr_url:
            webbrowser.open(self.pr_url)

    def _generate_with_ai(self):
        """Generate PR title and description using AI based on git diff."""
        source = self.source_branch_combo.get()
        target = self.target_branch_combo.get()
        
        if not source or not target:
            messagebox.showwarning("Missing Branches", "Please select both source and target branches first.")
            return
        
        if source == target:
            messagebox.showwarning("Invalid Branches", "Source and target branches cannot be the same.")
            return
        
        # Check if API key is configured
        if not self.gemini_client.api_key:
            messagebox.showerror(
                "API Key Not Configured",
                "Gemini API key is not configured.\n\n"
                "For development: Add GEMINI_API_KEY to .env file\n"
                "For production: Run build_helpers/obfuscate_key.py before building"
            )
            return
        
        # Disable button and show loading state
        original_text = self.ai_button.config('text')[-1]
        self.ai_button.config(text="⏳ Generating...", state=tk.DISABLED)
        self.parent.update_idletasks()
        
        try:
            self.log(f"\n--- Generating PR content with AI ---")
            self.log(f"Analyzing diff between '{target}' and '{source}'...")
            
            # Get the diff between target and source
            diff_output = self._run_command([
                "git", "diff", 
                f"origin/{target}...{source}"
            ], check=False)
            
            if not diff_output.strip():
                # Try without origin/ prefix
                diff_output = self._run_command([
                    "git", "diff", 
                    f"{target}...{source}"
                ], check=False)
            
            self.log(f"Diff size: {len(diff_output)} characters")
            
            # Call Gemini API
            self.log("Calling Gemini API...")
            result = self.gemini_client.generate_pr_content(diff_output, source, target)
            
            if result:
                # Populate fields
                self.title_entry.delete(0, tk.END)
                self.title_entry.insert(0, result['title'])
                
                self.description_text.delete("1.0", tk.END)
                self.description_text.insert("1.0", result['description'])
                
                self.log("✅ PR content generated successfully!")
                messagebox.showinfo("Success", "PR title and description generated with AI!")
            else:
                self.log("❌ Failed to generate PR content")
                messagebox.showerror("AI Error", "Failed to generate PR content. Check the log for details.")
                
        except subprocess.CalledProcessError as e:
            self.log(f"❌ Git error: {e}")
            messagebox.showerror("Git Error", f"Failed to get diff:\n{e}")
        except Exception as e:
            self.log(f"❌ Unexpected error: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")
        finally:
            # Re-enable button
            self.ai_button.config(text=original_text, state=tk.NORMAL)

    def _on_source_branch_selected(self, event=None):
        branch = self.source_branch_combo.get()
        if not branch:
            return
        try:
            self.log(f"\nFetching last commit info for '{branch}'...")
            title = self._run_command(["git", "log", branch, "-1", "--pretty=%s"])
            body = self._run_command(["git", "log", branch, "-1", "--pretty=%b"])
            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, title)
            self.description_text.config(state=tk.NORMAL)
            self.description_text.delete("1.0", tk.END)
            self.description_text.insert("1.0", body)
            self.log("Auto-filled title and description.")
        except (subprocess.CalledProcessError, ValueError) as e:
            self.log(f"Could not fetch commit info for '{branch}': {e}")
        
        self._update_preview()
    
    def _on_target_branch_selected(self, event=None):
        self._update_preview()
    
    def create_pull_request(self):
        source = self.source_branch_combo.get()
        target = self.target_branch_combo.get()
        title = self.title_entry.get().strip()
        body = self.description_text.get("1.0", tk.END).strip()
        
        if not all([source, target, title]):
            return messagebox.showwarning("Input Missing", "Source, target, and title are required.")
        if source == target:
            return messagebox.showwarning("Invalid Branches", "Source and target branches cannot be the same.")
        if not messagebox.askyesno("Confirm", f"Create PR?\n\nFrom: {source}\nInto: {target}\nTitle: {title}"):
            return self.log("PR creation cancelled.")
        
        self.log("\n--- Creating Pull Request ---")
        try:
            self.log(f"Pushing '{source}' to origin...")
            self._run_command(["git", "push", "-u", "origin", source])
            command = ["gh", "pr", "create", "--base", target, "--head", source, "--title", title, "--body", body]
            result = self._run_command(command)
            self.log("✅ Pull Request created successfully!")
            
            # Extract URL
            self.pr_url = result.splitlines()[-1]
            if "https://github.com" in self.pr_url:
                self.view_gh_button.config(state=tk.NORMAL)
            
            messagebox.showinfo("Success", f"Pull Request created!\n\n{self.pr_url}")
        except subprocess.CalledProcessError:
            self.log("🛑 FAILED to create Pull Request. Check the error log above.")
            messagebox.showerror("GitHub CLI Error", "Failed to create the Pull Request. See the log for details.")
