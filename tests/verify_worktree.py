import os
import shutil
import tempfile
import unittest
from pathlib import Path

from utils.git_utils import (
    run_git_command, 
    list_worktrees, 
    add_worktree, 
    remove_worktree, 
    prune_worktrees,
    get_branches
)

class TestWorktreeUtils(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.repo_path = self.test_dir / "main_repo"
        self.repo_path.mkdir()
        
        # Init repo
        run_git_command("init", str(self.repo_path))
        (self.repo_path / "README.md").write_text("Main Repo")
        run_git_command("add README.md", str(self.repo_path))
        run_git_command("commit -m 'Initial commit'", str(self.repo_path))
        run_git_command("branch develop", str(self.repo_path))

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_worktree_lifecycle(self):
        # 1. Add worktree with spaces in path
        worktree_path = self.test_dir / "worktree with spaces"
        branch = "develop"
        
        print(f"Adding worktree at: {worktree_path}")
        add_worktree(str(self.repo_path), str(worktree_path), branch)
        
        # 2. List worktrees
        wt_list = list_worktrees(str(self.repo_path))
        print(f"Worktrees: {wt_list}")
        
        # Verify
        paths = [Path(w['path']).resolve() for w in wt_list]
        self.assertIn(worktree_path.resolve(), paths)
        
        # Check branch
        target_wt = next(w for w in wt_list if Path(w['path']).resolve() == worktree_path.resolve())
        self.assertEqual(target_wt['branch'], "develop")
        
        # 3. Remove worktree
        print(f"Removing worktree: {worktree_path}")
        remove_worktree(str(self.repo_path), str(worktree_path))
        
        # Verify removal
        wt_list_after = list_worktrees(str(self.repo_path))
        paths_after = [Path(w['path']).resolve() for w in wt_list_after]
        self.assertNotIn(worktree_path.resolve(), paths_after)
        
        # 4. Prune
        prune_worktrees(str(self.repo_path))
        print("Prune complete")

    def test_add_worktree_new_branch(self):
        worktree_path = self.test_dir / "new_branch_wt"
        branch = "feature-xyz"
        
        print(f"Adding worktree with new branch: {branch}")
        add_worktree(str(self.repo_path), str(worktree_path), branch, create_branch=True)
        
        wt_list = list_worktrees(str(self.repo_path))
        target_wt = next(w for w in wt_list if Path(w['path']).resolve() == worktree_path.resolve())
        self.assertEqual(target_wt['branch'], branch)
        
        branches = get_branches(str(self.repo_path))
        self.assertIn(branch, branches)

if __name__ == "__main__":
    unittest.main()
