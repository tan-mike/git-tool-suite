
import os
import shutil
import subprocess
import sys

def run_git(args, cwd):
    return subprocess.check_output(["git"] + args, cwd=cwd, text=True).strip()

def verify_commit_tool():
    base_path = os.path.abspath("commit_tool_test")
    if os.path.exists(base_path):
        shutil.rmtree(base_path)
    os.makedirs(base_path)
    
    # 1. Setup Repo
    print("Setting up test repo...")
    run_git(["init"], base_path)
    
    # Create file
    with open(os.path.join(base_path, "test.txt"), "w") as f:
        f.write("Initial content\n")
    run_git(["add", "test.txt"], base_path)
    run_git(["commit", "-m", "Initial commit"], base_path)
    
    # Modify file
    with open(os.path.join(base_path, "test.txt"), "a") as f:
        f.write("New content\n")
        
    # Create new file
    with open(os.path.join(base_path, "new.txt"), "w") as f:
        f.write("New file content\n")
        
    # 2. Verify Status Parsing (Simulate App Logic)
    status_out = run_git(["status", "--porcelain"], base_path)
    print("\n--- Status Output ---")
    print(status_out)
    
    # Expected: M test.txt, ?? new.txt
    if "M test.txt" in status_out and "?? new.txt" in status_out:
        print("SUCCESS: Status detected correctly.")
    else:
        print("FAILURE: Status detection failed.")
        sys.exit(1)
        
    # 3. Verify Staging (Simulate 'Stage Selected')
    print("\nStaging 'test.txt'...")
    run_git(["add", "test.txt"], base_path)
    
    status_out = run_git(["status", "--porcelain"], base_path)
    print("--- Status Output After Stage ---")
    print(status_out)
    
    if "M  test.txt" in status_out: # Note: M at start means index
        print("SUCCESS: File staged correctly.")
    else:
        print("FAILURE: File staging failed.")
        sys.exit(1)
        
    # 4. Verify Diff for AI (Simulate 'Generate Message')
    diff_out = run_git(["diff", "--cached"], base_path)
    print("\n--- Cached Diff Output ---")
    print(diff_out)
    
    if "New content" in diff_out:
        print("SUCCESS: Cached diff contains changes.")
    else:
        print("FAILURE: Cached diff missing changes.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        verify_commit_tool()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if os.path.exists("commit_tool_test"):
            try:
                shutil.rmtree("commit_tool_test")
            except:
                pass
