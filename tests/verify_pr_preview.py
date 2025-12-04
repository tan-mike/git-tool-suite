
import os
import shutil
import subprocess
import sys

def run_git(args, cwd):
    return subprocess.check_output(["git"] + args, cwd=cwd, text=True).strip()

def verify_pr_preview():
    base_path = os.path.abspath("pr_preview_test")
    if os.path.exists(base_path):
        shutil.rmtree(base_path)
    os.makedirs(base_path)
    
    # 1. Setup Repo
    print("Setting up test repo...")
    run_git(["init"], base_path)
    
    # Create main branch with initial commit
    with open(os.path.join(base_path, "README.md"), "w") as f:
        f.write("# Main\n")
    run_git(["add", "README.md"], base_path)
    run_git(["commit", "-m", "Initial commit"], base_path)
    
    # Create feature branch
    run_git(["checkout", "-b", "feature/test"], base_path)
    
    # Modify README
    with open(os.path.join(base_path, "README.md"), "a") as f:
        f.write("Feature change\n")
    run_git(["add", "README.md"], base_path)
    run_git(["commit", "-m", "Update README"], base_path)
    
    # Add new file
    with open(os.path.join(base_path, "new_file.py"), "w") as f:
        f.write("print('hello')\n")
    run_git(["add", "new_file.py"], base_path)
    run_git(["commit", "-m", "Add new file"], base_path)
    
    # 2. Simulate Logic in App
    source = "feature/test"
    target = "master" # git init creates master by default usually, or main. Let's check.
    branches = run_git(["branch"], base_path)
    if "main" in branches:
        target = "main"
        
    print(f"Testing diff between {target} and {source}...")
    
    # Test 1: Files Changed (git diff --stat)
    # Note: In app we try origin/target...source first, then target...source.
    # Here we only have local, so we test the fallback logic which is crucial.
    
    diff_cmd = ["diff", "--stat", f"{target}...{source}"]
    stat_output = run_git(diff_cmd, base_path)
    print("\n--- Diff Stat Output ---")
    print(stat_output)
    
    if "README.md" in stat_output and "new_file.py" in stat_output:
        print("SUCCESS: Files changed detected.")
    else:
        print("FAILURE: Files changed NOT detected.")
        sys.exit(1)

    # Test 2: Commits (git log)
    log_cmd = ["log", "--pretty=format:%h|%an|%s", f"{target}...{source}"]
    log_output = run_git(log_cmd, base_path)
    print("\n--- Log Output ---")
    print(log_output)
    
    commits = log_output.splitlines()
    if len(commits) == 2:
        print(f"SUCCESS: Found {len(commits)} commits (expected 2).")
        if "Update README" in commits[1] and "Add new file" in commits[0]:
             print("SUCCESS: Commit subjects match.")
        else:
             print("FAILURE: Commit subjects do not match expected order/content.")
             # Note: git log shows newest first.
             # "Add new file" is newest.
    else:
        print(f"FAILURE: Found {len(commits)} commits (expected 2).")
        sys.exit(1)

if __name__ == "__main__":
    try:
        verify_pr_preview()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if os.path.exists("pr_preview_test"):
            try:
                shutil.rmtree("pr_preview_test")
            except:
                pass
