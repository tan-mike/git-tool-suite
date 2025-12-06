"""
Shared Git utility functions used across multiple apps.
"""

import subprocess
import shlex
import sys


def run_git_command(command, repo_path, check=True):
    """
    Execute a git command in the specified repository.
    
    Args:
        command (str): Git command without 'git' prefix (e.g., "branch -a")
        repo_path (str): Path to the Git repository
        check (bool): Whether to raise exception on non-zero exit code
        
    Returns:
        str: stdout from the command
        
    Raises:
        subprocess.CalledProcessError: If command fails and check=True
    """
    if not repo_path:
        raise ValueError("Repository path not set.")
    
    command_parts = ["git"] + shlex.split(command)
    
    # Hide console window when running as frozen executable on Windows
    creation_flags = 0
    if sys.platform == 'win32':
        creation_flags = subprocess.CREATE_NO_WINDOW
    
    process = subprocess.run(
        command_parts,
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore',
        creationflags=creation_flags
    )
    
    if check:
        process.check_returncode()
    
    return process.stdout.strip()


def get_branches(repo_path):
    """
    Get list of all local branches in the repository.
    
    Args:
        repo_path (str): Path to the Git repository
        
    Returns:
        list[str]: Sorted list of branch names
    """
    branch_output = run_git_command("branch", repo_path)
    branches = sorted([
        b.strip().replace("* ", "") 
        for b in branch_output.splitlines()
    ])
    return branches


def get_current_branch(repo_path):
    """
    Get the name of the currently checked out branch.
    
    Args:
        repo_path (str): Path to the Git repository
        
    Returns:
        str: Current branch name
    """
    return run_git_command("rev-parse --abbrev-ref HEAD", repo_path)


def get_commit_info(repo_path, branch, max_commits=50):
    """
    Get commit history for a branch.
    
    Args:
        repo_path (str): Path to the Git repository
        branch (str): Branch name
        max_commits (int): Maximum number of commits to retrieve
        
    Returns:
        list[str]: List of commit info strings in format "hash|message (author)"
    """
    log_output = run_git_command(
        f"log {branch} --pretty=format:'%h|%s (%an)' -n {max_commits}",
        repo_path
    )
    return log_output.splitlines()
