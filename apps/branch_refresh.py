"""
Git Branch Refresh Application.
Keeps local development branches synchronized with their remote tracking branches.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import datetime
import uuid

from config import Config
from utils.git_utils import run_git_command, get_branches, get_current_branch


class BranchRefreshApp:
    def __init__(self, parent):
        """Initializes the Branch Refresh UI inside the provided parent widget (a tab)."""
        self.parent = parent
        self.tracked_repos = {}  # Dict: {repo_path: [branch_names]}
        self.selected_repo = None
        
        self.build_ui()
        self.load_tracked_configuration()
    
    def build_ui(self):
        """Build the UI layout with multi-repo support."""
        # Main container with two columns
        main_container = ttk.Frame(self.parent, padding=10)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=2)
        main_container.rowconfigure(0, weight=1)
        
        # LEFT PANEL: Repository Management
        left_panel = ttk.LabelFrame(main_container, text="Tracked Repositories", padding=10)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Repository tree
        tree_frame = ttk.Frame(left_panel)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.repo_tree = ttk.Treeview(tree_frame, yscrollcommand=tree_scroll.set, selectmode="browse")
        self.repo_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.repo_tree.yview)
        
        self.repo_tree.heading("#0", text="Repository → Branches")
        self.repo_tree.bind("<<TreeviewSelect>>", self.on_repo_selected)
        
        # Repository management buttons
        repo_btn_frame = ttk.Frame(left_panel)
        repo_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(repo_btn_frame, text="Add Repository", command=self.add_repository).pack(side=tk.LEFT, padx=2)
        ttk.Button(repo_btn_frame, text="Remove Repository", command=self.remove_repository).pack(side=tk.LEFT, padx=2)
        
        # RIGHT PANEL: Branch Selection & Controls
        right_panel = ttk.Frame(main_container)
        right_panel.grid(row=0, column=1, sticky="nsew")
        
        # Branch selection section
        branch_frame = ttk.LabelFrame(right_panel, text="Branch Selection (select branches to track)", padding=10)
        branch_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Instructions
        ttk.Label(branch_frame, text="Select a repository on the left to configure tracked branches.", 
                  foreground="gray").pack(anchor=tk.W, pady=(0, 5))
        
        # Branch listbox with checkboxes (will be populated when repo selected)
        branch_list_frame = ttk.Frame(branch_frame)
        branch_list_frame.pack(fill=tk.BOTH, expand=True)
        
        branch_scroll = ttk.Scrollbar(branch_list_frame)
        branch_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.branch_listbox = tk.Listbox(branch_list_frame, yscrollcommand=branch_scroll.set, 
                                         selectmode=tk.MULTIPLE, height=10)
        self.branch_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        branch_scroll.config(command=self.branch_listbox.yview)
        
        # Save branches button
        ttk.Button(branch_frame, text="Save Tracked Branches", 
                   command=self.save_tracked_branches).pack(anchor=tk.E, pady=(5, 0))
        
        # Refresh controls section
        refresh_frame = ttk.LabelFrame(right_panel, text="Refresh Controls", padding=10)
        refresh_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_container = ttk.Frame(refresh_frame)
        btn_container.pack(fill=tk.X)
        
        ttk.Button(btn_container, text="Refresh All Tracked Branches", 
                   command=self.refresh_all_tracked).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_container, text="Refresh Selected Repository", 
                   command=self.refresh_selected_repo).pack(side=tk.LEFT, padx=5)
        
        # Future enhancement placeholder
        ttk.Label(refresh_frame, text="(Auto-refresh scheduling coming in future version)", 
                  foreground="gray", font=("", 8)).pack(anchor=tk.W, pady=(5, 0))
        
        # Log section
        log_frame = ttk.LabelFrame(right_panel, text="Operation Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def log_message(self, message):
        """Log a message to the log area."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def add_repository(self):
        """Add a new repository to track."""
        repo_path = filedialog.askdirectory(title="Select Git Repository")
        if not repo_path:
            return
        
        # Validate it's a git repository
        try:
            run_git_command("rev-parse --git-dir", repo_path)
        except Exception as e:
            messagebox.showerror("Invalid Repository", f"The selected directory is not a Git repository.\n\n{e}")
            return
        
        if repo_path in self.tracked_repos:
            messagebox.showinfo("Already Tracked", "This repository is already in the tracking list.")
            return
        
        # Add to tracked repos with empty branch list
        self.tracked_repos[repo_path] = []
        self.update_repo_tree()
        self.save_tracked_configuration()
        self.log_message(f"Added repository: {repo_path}")
    
    def remove_repository(self):
        """Remove selected repository from tracking."""
        selected = self.repo_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a repository to remove.")
            return
        
        item = selected[0]
        # Check if it's a repo (top-level item)
        parent = self.repo_tree.parent(item)
        if parent:  # It's a branch, get parent repo
            item = parent
        
        repo_path = self.repo_tree.item(item, "text")
        
        confirm = messagebox.askyesno("Confirm Removal", 
                                      f"Remove this repository from tracking?\n\n{repo_path}")
        if confirm:
            del self.tracked_repos[repo_path]
            self.update_repo_tree()
            self.save_tracked_configuration()
            self.log_message(f"Removed repository: {repo_path}")
            
            # Clear branch listbox
            self.branch_listbox.delete(0, tk.END)
            self.selected_repo = None
    
    def on_repo_selected(self, event=None):
        """Handle repository selection in tree."""
        selected = self.repo_tree.selection()
        if not selected:
            return
        
        item = selected[0]
        # Get repo path (might be branch item, so traverse to parent)
        parent = self.repo_tree.parent(item)
        if parent:  # It's a branch, get parent
            repo_path = self.repo_tree.item(parent, "text")
        else:
            repo_path = self.repo_tree.item(item, "text")
        
        self.selected_repo = repo_path
        self.load_branches_for_repo(repo_path)
    
    def load_branches_for_repo(self, repo_path):
        """Load branches with tracking for selected repository."""
        try:
            # Get branches with remote tracking
            from utils.git_utils import get_branches_with_tracking
            branches_with_tracking = get_branches_with_tracking(repo_path)
            
            # Clear and populate listbox
            self.branch_listbox.delete(0, tk.END)
            
            if not branches_with_tracking:
                self.branch_listbox.insert(tk.END, "(No branches with remote tracking found)")
                return
            
            # Get currently tracked branches for this repo
            tracked_branches = self.tracked_repos.get(repo_path, [])
            
            # Populate listbox
            for local_branch, remote_branch in branches_with_tracking:
                self.branch_listbox.insert(tk.END, f"{local_branch} → {remote_branch}")
                
                # Select if already tracked
                if local_branch in tracked_branches:
                    self.branch_listbox.selection_set(tk.END)
        
        except Exception as e:
            self.log_message(f"Error loading branches: {e}")
            messagebox.showerror("Error", f"Failed to load branches:\n\n{e}")
    
    def save_tracked_branches(self):
        """Save selected branches for the currently selected repository."""
        if not self.selected_repo:
            messagebox.showwarning("No Repository Selected", "Please select a repository first.")
            return
        
        # Get selected indices
        selected_indices = self.branch_listbox.curselection()
        
        # Extract branch names from selections
        tracked_branches = []
        for idx in selected_indices:
            item_text = self.branch_listbox.get(idx)
            if " → " in item_text:
                branch_name = item_text.split(" → ")[0]
                tracked_branches.append(branch_name)
        
        # Update tracked repos
        self.tracked_repos[self.selected_repo] = tracked_branches
        self.update_repo_tree()
        self.save_tracked_configuration()
        
        self.log_message(f"Saved {len(tracked_branches)} tracked branch(es) for {self.selected_repo}")
    
    def update_repo_tree(self):
        """Update the repository tree view."""
        # Clear existing items
        for item in self.repo_tree.get_children():
            self.repo_tree.delete(item)
        
        # Populate tree
        for repo_path, branches in self.tracked_repos.items():
            # Add repo as parent
            repo_item = self.repo_tree.insert("", tk.END, text=repo_path, open=True)
            
            # Add branches as children
            if branches:
                for branch in branches:
                    self.repo_tree.insert(repo_item, tk.END, text=f"  ↳ {branch}")
            else:
                self.repo_tree.insert(repo_item, tk.END, text="  (No branches tracked)", tags=("gray",))
        
        # Configure tag for gray text
        self.repo_tree.tag_configure("gray", foreground="gray")
    
    def load_tracked_configuration(self):
        """Load saved configuration from preferences."""
        prefs = Config.load_preferences()
        branch_refresh_prefs = prefs.get("branch_refresh", {})
        self.tracked_repos = branch_refresh_prefs.get("tracked_repos", {})
        self.update_repo_tree()
    
    def save_tracked_configuration(self):
        """Save current configuration to preferences."""
        prefs = Config.load_preferences()
        if "branch_refresh" not in prefs:
            prefs["branch_refresh"] = {}
        
        prefs["branch_refresh"]["tracked_repos"] = self.tracked_repos
        Config.save_preferences(prefs)
    
    def refresh_all_tracked(self):
        """Refresh all tracked branches across all repositories."""
        if not self.tracked_repos:
            messagebox.showinfo("No Tracked Branches", "No repositories or branches are being tracked.")
            return
        
        # Count total branches
        total_branches = sum(len(branches) for branches in self.tracked_repos.values())
        
        if total_branches == 0:
            messagebox.showinfo("No Tracked Branches", "No branches are being tracked in any repository.")
            return
        
        confirm = messagebox.askyesno(
            "Confirm Refresh All",
            f"This will refresh {total_branches} branch(es) across {len(self.tracked_repos)} repository(ies).\n\n"
            "This operation will:\n"
            "• Delete and recreate local branches from remote\n"
            "• Skip branches with uncommitted changes\n"
            "• Handle currently checked out branches safely\n\n"
            "Continue?"
        )
        
        if not confirm:
            return
        
        # Run in background thread
        threading.Thread(target=self._refresh_all_worker, daemon=True).start()
    
    def _refresh_all_worker(self):
        """Background worker to refresh all tracked branches."""
        self.log_message("=== Starting refresh of all tracked branches ===")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for repo_path, branches in self.tracked_repos.items():
            self.log_message(f"\nProcessing repository: {repo_path}")
            
            for branch in branches:
                result = self.refresh_branch(repo_path, branch)
                if result == "success":
                    success_count += 1
                elif result == "skipped":
                    skip_count += 1
                else:
                    error_count += 1
        
        self.log_message(f"\n=== Refresh Complete ===")
        self.log_message(f"Success: {success_count}, Skipped: {skip_count}, Errors: {error_count}")
    
    def refresh_selected_repo(self):
        """Refresh all tracked branches in the selected repository."""
        if not self.selected_repo:
            messagebox.showwarning("No Selection", "Please select a repository from the tree.")
            return
        
        branches = self.tracked_repos.get(self.selected_repo, [])
        
        if not branches:
            messagebox.showinfo("No Tracked Branches", "No branches are tracked for the selected repository.")
            return
        
        confirm = messagebox.askyesno(
            "Confirm Refresh",
            f"Refresh {len(branches)} branch(es) in:\n{self.selected_repo}\n\n"
            "This will delete and recreate local branches from remote.\n\n"
            "Continue?"
        )
        
        if not confirm:
            return
        
        # Run in background thread
        threading.Thread(target=self._refresh_repo_worker, args=(self.selected_repo, branches), daemon=True).start()
    
    def _refresh_repo_worker(self, repo_path, branches):
        """Background worker to refresh branches in one repository."""
        self.log_message(f"=== Refreshing repository: {repo_path} ===")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for branch in branches:
            result = self.refresh_branch(repo_path, branch)
            if result == "success":
                success_count += 1
            elif result == "skipped":
                skip_count += 1
            else:
                error_count += 1
        
        self.log_message(f"Repository refresh complete - Success: {success_count}, Skipped: {skip_count}, Errors: {error_count}")
    
    def refresh_branch(self, repo_path, branch):
        """
        Refresh a single branch by deleting and recreating from remote.
        Returns: "success", "skipped", or "error"
        """
        try:
            self.log_message(f"Refreshing branch: {branch}")
            
            # Check if branch has tracking remote
            from utils.git_utils import get_tracking_branch, has_uncommitted_changes
            tracking_branch = get_tracking_branch(repo_path, branch)
            
            if not tracking_branch:
                self.log_message(f"  ⚠ SKIPPED: No tracking branch found for '{branch}'")
                return "skipped"
            
            # Check for uncommitted changes in the entire repo
            if has_uncommitted_changes(repo_path):
                self.log_message(f"  ⚠ SKIPPED: Repository has uncommitted changes")
                return "skipped"
            
            # Check if this is the current branch
            current_branch = get_current_branch(repo_path)
            is_current = (current_branch == branch)
            
            temp_branch = None
            
            if is_current:
                # Create temporary branch and switch to it
                temp_branch = f"temp-refresh-{uuid.uuid4().hex[:8]}"
                self.log_message(f"  Creating temporary branch: {temp_branch}")
                run_git_command(f"checkout -b {temp_branch}", repo_path)
            
            # Delete local branch
            self.log_message(f"  Deleting local branch: {branch}")
            run_git_command(f"branch -D {branch}", repo_path)
            
            # Recreate from remote
            # Extract remote name and branch name from tracking branch (e.g., "origin/develop" -> "origin", "develop")
            remote_parts = tracking_branch.split("/", 1)
            if len(remote_parts) == 2:
                remote_name, remote_branch = remote_parts
            else:
                remote_name = "origin"
                remote_branch = tracking_branch
            
            self.log_message(f"  Recreating from: {tracking_branch}")
            run_git_command(f"checkout -b {branch} {tracking_branch}", repo_path)
            
            if is_current:
                # We're already on the refreshed branch, just delete temp
                self.log_message(f"  Deleting temporary branch: {temp_branch}")
                run_git_command(f"branch -D {temp_branch}", repo_path)
            
            self.log_message(f"  ✓ SUCCESS: Branch '{branch}' refreshed")
            return "success"
            
        except Exception as e:
            self.log_message(f"  ✗ ERROR: {str(e)}")
            
            # If we created a temp branch and failed, try to recover
            if temp_branch:
                try:
                    # Try to go back to original branch if it still exists
                    run_git_command(f"checkout {branch}", repo_path, check=False)
                    run_git_command(f"branch -D {temp_branch}", repo_path, check=False)
                except:
                    pass
            
            return "error"
