
import os
import shutil
from git import Repo, Actor
import time

def create_dummy_repo(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    repo = Repo.init(path)
    return repo

def debug_refs():
    base_path = os.path.abspath("debug_repo_test")
    remote_path = os.path.join(base_path, "remote")
    local_path = os.path.join(base_path, "local")

    # Create remote
    remote_repo = create_dummy_repo(remote_path)
    index = remote_repo.index
    index.commit("Initial commit")
    
    # Create a branch on remote
    remote_repo.create_head("feature/old-remote")
    
    # Clone to local
    if os.path.exists(local_path):
        shutil.rmtree(local_path)
    local_repo = Repo.clone_from(remote_path, local_path)
    
    # Create a local branch that is NOT on remote
    local_repo.create_head("feature/local-only")
    
    # Create a local branch that IS on remote (already fetched as origin/feature/old-remote)
    # Checkout it to make it a local head too
    local_repo.create_head("feature/old-remote", "origin/feature/old-remote")

    print("--- Refs in Local Repo ---")
    for ref in local_repo.refs:
        print(f"Ref: {ref.name}, Type: {type(ref)}")

    print("\n--- Heads (Local Branches) ---")
    for head in local_repo.heads:
        print(f"Head: {head.name}")

    print("\n--- Remotes ---")
    for remote in local_repo.remotes:
        print(f"Remote: {remote.name}")
        for ref in remote.refs:
             print(f"  Remote Ref: {ref.name}")

if __name__ == "__main__":
    try:
        debug_refs()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        if os.path.exists("debug_repo_test"):
            try:
                shutil.rmtree("debug_repo_test")
            except:
                pass
