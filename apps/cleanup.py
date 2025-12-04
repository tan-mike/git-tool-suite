"""
Git Branch Cleanup Application.
Queries and deletes stale branches based on age and prefix filters.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime
import threading
import os


try:
    from git import Repo, exc
except ImportError:
    pass  # Will show error in main app initialization

from config import Config


class BranchCleanerApp:
    def __init__(self, parent):
        """Initializes the Branch Cleanup UI inside the provided parent widget (a tab)."""
        self.parent = parent
        self.repo_path = tk.StringVar()
        self.prefs = Config.load_preferences()
        
        # Load preferences
        cleanup_prefs = self.prefs.get('cleanup', {})
        self.prefix = tk.StringVar(value=cleanup_prefs.get('default_prefix', 'feature/'))
        self.days = tk.IntVar(value=cleanup_prefs.get('default_days', 30))
        self.delete_scope = tk.StringVar(value=cleanup_prefs.get('delete_scope', 'both'))
        
        self.build_ui()
        self.repo = None
        self.branches_info = []
        self.log_message("Application ready. Please select a repository.")

    def build_ui(self):
        main_frame = ttk.Frame(self.parent, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        frm_top = ttk.Frame(main_frame)
        frm_top.pack(fill="x", pady=(0, 5))
        ttk.Label(frm_top, text="Repository Path:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm_top, textvariable=self.repo_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(frm_top, text="Browse", command=self.browse_repo).grid(row=0, column=2)
        ttk.Label(frm_top, text="Branch Prefix:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(frm_top, textvariable=self.prefix).grid(row=1, column=1, sticky="w")
        ttk.Label(frm_top, text="Older than (days):").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(frm_top, textvariable=self.days, width=10).grid(row=2, column=1, sticky="w")
        ttk.Button(frm_top, text="Query Branches", command=self.query_branches).grid(row=3, column=1, sticky="w", pady=10)

        self.tree = ttk.Treeview(main_frame, columns=("branch", "last_commit", "days_old"), show="headings", selectmode="extended")
        self.tree.heading("branch", text="Branch Name")
        self.tree.heading("last_commit", text="Last Commit Date")
        self.tree.heading("days_old", text="Days Old")
        self.tree.column("branch", width=350)
        self.tree.column("last_commit", width=200)
        self.tree.column("days_old", width=100, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=5)

        frm_actions = ttk.Frame(main_frame)
        frm_actions.pack(fill="x", pady=5)
        ttk.Label(frm_actions, text="Deletion Scope:").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(frm_actions, text="Both", variable=self.delete_scope, value="both").pack(side="left", padx=5)
        ttk.Radiobutton(frm_actions, text="Remote Only", variable=self.delete_scope, value="remote").pack(side="left", padx=5)
        ttk.Radiobutton(frm_actions, text="Local Only", variable=self.delete_scope, value="local").pack(side="left", padx=5)

        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding=10)
        log_frame.pack(fill="both", expand=True, pady=5)
        self.log_text = tk.Text(log_frame, height=8, state="disabled", wrap="word", font=("Courier New", 9))
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text["yscrollcommand"] = scrollbar.set
        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)
        
        frm_bottom = ttk.Frame(main_frame)
        frm_bottom.pack(fill="x", pady=5)
        self.progress = ttk.Progressbar(frm_bottom, orient="horizontal", mode="determinate", length=500)
        self.progress.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.btn_delete = ttk.Button(frm_bottom, text="Delete Selected", command=self.delete_selected)
        self.btn_delete.pack(side="right")

    def log_message(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.parent.after(0, self._log_to_widget, f"[{timestamp}] {message}")

    def _log_to_widget(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state="disabled")
        self.log_text.see(tk.END)

    def browse_repo(self):
        path = filedialog.askdirectory()
        if path:
            self.repo_path.set(path)
            self.log_message(f"Repo path set to: {path}")

    def query_branches(self):
        repo_path = self.repo_path.get().strip()
        prefix = self.prefix.get().strip()
        days_limit = self.days.get()
        
        if not repo_path or not os.path.isdir(repo_path):
            return messagebox.showerror("Error", "Select a valid Git repo path.")
        
        # Save preferences
        self.prefs['cleanup']['default_prefix'] = prefix
        self.prefs['cleanup']['default_days'] = days_limit
        Config.save_preferences(self.prefs)
        
        self.log_message(f"Querying branches with prefix='{prefix}', older than {days_limit} days.")
        try:
            self.repo = Repo(repo_path)
            self.log_message("Fetching from remote to update branch list...")
            self.repo.git.fetch("--all", "--prune")
            self.log_message("Fetch complete.")
        except Exception as e:
            self.log_message(f"Git Error: {e}")
            return messagebox.showerror("Git Error", f"Failed to access repo or fetch:\n{e}")

        self.tree.delete(*self.tree.get_children())
        self.branches_info.clear()
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Collect all candidates: name -> {'local': ref, 'remote': ref}
        candidates = {}

        # 1. Local branches
        for head in self.repo.heads:
            if head.name.startswith(prefix):
                if head.name not in candidates:
                    candidates[head.name] = {}
                candidates[head.name]['local'] = head

        # 2. Remote branches (origin)
        if 'origin' in self.repo.remotes:
            for ref in self.repo.remotes.origin.refs:
                # ref.name is typically "origin/feature/..."
                remote_name = ref.name
                if remote_name.startswith("origin/"):
                    short_name = remote_name[7:]  # strip "origin/"
                    if short_name.startswith(prefix):
                        if short_name not in candidates:
                            candidates[short_name] = {}
                        candidates[short_name]['remote'] = ref

        for name, refs in candidates.items():
            # Determine most recent commit date between local and remote
            timestamps = []
            if 'local' in refs:
                timestamps.append(refs['local'].commit.committed_date)
            if 'remote' in refs:
                timestamps.append(refs['remote'].commit.committed_date)
            
            if not timestamps:
                continue
            
            # Use the newest timestamp to avoid deleting a branch that was just updated on one side
            max_ts = max(timestamps)
            commit_date = datetime.datetime.fromtimestamp(max_ts, datetime.timezone.utc)
            age_days = (now - commit_date).days
            
            if age_days >= days_limit:
                self.branches_info.append((name, commit_date, age_days))
        
        self.branches_info.sort(key=lambda x: x[2], reverse=True)
        for name, c_date, a_days in self.branches_info:
            self.tree.insert("", "end", values=(name, c_date.strftime("%Y-%m-%d %H:%M"), a_days))
        
        self.log_message(f"Found {len(self.branches_info)} branches matching criteria.")
        if not self.branches_info:
            messagebox.showinfo("Result", "No branches matched your criteria.")

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return messagebox.showwarning("Warning", "No branches selected.")
        
        scope = self.delete_scope.get()
        scope_text = {"both": "local and remote", "remote": "remote only", "local": "local only"}.get(scope)
        
        if not messagebox.askyesno("Confirm", f"Delete {len(selected)} branches from {scope_text}?"):
            return self.log_message("Deletion cancelled by user.")

        # Save scope preference
        self.prefs['cleanup']['delete_scope'] = scope
        Config.save_preferences(self.prefs)

        self.log_message(f"Starting deletion of {len(selected)} branches ({scope_text})...")
        self.btn_delete.config(state="disabled")
        self.progress["value"] = 0
        self.progress["maximum"] = len(selected)
        threading.Thread(target=self._delete_branches_thread, args=(selected, scope), daemon=True).start()

    def _delete_branches_thread(self, selected, scope):
        success_count = 0
        total_count = len(selected)
        
        for idx, item in enumerate(selected, start=1):
            branch_name = self.tree.item(item, "values")[0]
            short_name = branch_name.replace("origin/", "")
            self.log_message(f"({idx}/{total_count}) Processing '{short_name}'...")
            branch_cleanup_success = False

            if scope in ["remote", "both"]:
                self.log_message(f"  -> Deleting remote 'origin/{short_name}'...")
                try:
                    self.repo.git.push("origin", "--delete", short_name)
                    branch_cleanup_success = True
                except exc.GitCommandError as e:
                    if "remote ref does not exist" in str(e):
                        self.log_message("     Remote branch already deleted.")
                        branch_cleanup_success = True
                    else:
                        self.log_message(f"     ERROR deleting remote: {e.stderr.strip()}")
            
            if scope in ["local", "both"]:
                self.log_message(f"  -> Deleting local '{short_name}'...")
                try:
                    self.repo.git.branch("-D", short_name)
                    branch_cleanup_success = True
                except exc.GitCommandError as e:
                    if "not found" in str(e):
                        self.log_message("     Local branch does not exist.")
                        branch_cleanup_success = True
                    else:
                        self.log_message(f"     ERROR deleting local: {e.stderr.strip()}")

            if branch_cleanup_success:
                success_count += 1
            self.parent.after(0, self.progress.config, {"value": idx})

        self.parent.after(0, self._finish_deletion, success_count)

    def _finish_deletion(self, success_count):
        self.log_message(f"Deletion finished. {success_count} branches cleaned up.")
        self.btn_delete.config(state="normal")
        messagebox.showinfo("Done", f"Cleaned up {success_count} branches.")
        self.query_branches()
