
import unittest
import os
import shutil
import subprocess
from pathlib import Path
import tkinter as tk
from unittest.mock import MagicMock, patch

# Add project root to sys.path to allow importing from apps
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from apps.propagator import GitPropagatorApp

class TestPropagatorOrder(unittest.TestCase):
    """
    Test suite for verifying the chronological order of cherry-picking multiple commits.
    """

    def setUp(self):
        """Set up a temporary Git repository for testing."""
        self.repo_path = Path("./test_repo_propagator").resolve()
        if self.repo_path.exists():
            shutil.rmtree(self.repo_path)
        self.repo_path.mkdir()

        self.run_git_command("init", self.repo_path)
        self.run_git_command("config user.name 'Test User'", self.repo_path)
        self.run_git_command("config user.email 'test@example.com'", self.repo_path)

        # Initial commit on main
        (self.repo_path / "file.txt").write_text("initial")
        self.run_git_command("add .", self.repo_path)
        self.run_git_command("commit -m 'Initial commit'", self.repo_path)

        # Create a feature branch with multiple commits
        self.run_git_command("checkout -b feature", self.repo_path)

        (self.repo_path / "file.txt").write_text("change 1")
        self.run_git_command("commit -am 'Commit 1'", self.repo_path)
        self.commit1_hash = self.get_latest_commit_hash()

        (self.repo_path / "file.txt").write_text("change 2")
        self.run_git_command("commit -am 'Commit 2'", self.repo_path)
        self.commit2_hash = self.get_latest_commit_hash()

        (self.repo_path / "file.txt").write_text("change 3")
        self.run_git_command("commit -am 'Commit 3'", self.repo_path)
        self.commit3_hash = self.get_latest_commit_hash()

        # Commits from git log are newest to oldest
        self.chronological_commits = [self.commit1_hash, self.commit2_hash, self.commit3_hash]
        self.log_order_commits = [self.commit3_hash, self.commit2_hash, self.commit1_hash]

        # Create target branch
        self.run_git_command("checkout master", self.repo_path)
        self.run_git_command("checkout -b target", self.repo_path)

        # Set up a minimal Tkinter environment for the app
        self.root = tk.Tk()
        self.app = GitPropagatorApp(self.root)
        self.app.repo_path.set(str(self.repo_path))

    def tearDown(self):
        """Clean up the temporary repository and Tkinter window."""
        self.root.destroy()
        shutil.rmtree(self.repo_path)

    def run_git_command(self, command, cwd):
        """Helper to run a git command."""
        return subprocess.check_output(f"git {command}", shell=True, cwd=cwd, text=True).strip()

    def get_latest_commit_hash(self):
        """Helper to get the hash of the latest commit."""
        return self.run_git_command("rev-parse HEAD", self.repo_path)

    def get_commit_hashes_on_branch(self, branch):
        """Helper to get the list of commit hashes on a branch, from oldest to newest."""
        log = self.run_git_command(f"log {branch} --pretty=format:'%H' --reverse --not master", self.repo_path)
        return log.splitlines()

    @patch('tkinter.messagebox.showerror')
    @patch('tkinter.messagebox.askyesno', return_value=True)
    def test_multi_commit_cherry_pick_order(self, mock_askyesno, mock_showerror):
        """
        Verify that multiple individual commits are cherry-picked in chronological order.
        """
        # --- Simulate UI state ---
        # 1. Mock the commit listbox to return selected commit info
        self.app.commit_listbox = MagicMock()
        self.app.commit_listbox.curselection.return_value = (0, 1, 2) # User selects all three

        # The get method should return commits in the order they appear in the log (newest first)
        commit_info_list = [
            f"{self.commit3_hash}|Commit 3 (Test User)",
            f"{self.commit2_hash}|Commit 2 (Test User)",
            f"{self.commit1_hash}|Commit 1 (Test User)",
        ]
        self.app.commit_listbox.get.side_effect = lambda i: commit_info_list[i]

        # 2. Mock the target branch listbox
        self.app.target_branch_listbox = MagicMock()
        self.app.target_branch_listbox.curselection.return_value = (0,)
        self.app.target_branch_listbox.get.return_value = "target"

        # 3. Mock other UI variables
        self.app.combine_commits_var = MagicMock()
        self.app.combine_commits_var.get.return_value = False # Individual commits

        self.app.push_changes_var = MagicMock()
        self.app.push_changes_var.get.return_value = False # No push

        # --- Run the propagation logic ---
        self.app.propagate_commit()

        # --- Assert the result ---
        # Get the hashes of commits applied to the target branch
        applied_hashes = self.get_commit_hashes_on_branch('target')

        # The applied hashes should be in chronological order
        self.assertEqual(applied_hashes, self.chronological_commits,
                         "The commits were not applied in the correct chronological order.")

if __name__ == '__main__':
    unittest.main()
