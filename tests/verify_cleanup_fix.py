
import os
import shutil
import datetime
from git import Repo, Actor
import sys

# Mocking the App class structure to test the logic
class MockBranchCleanerApp:
    def __init__(self, repo_path):
        self.repo = Repo(repo_path)
        self.branches_info = []

    def query_branches(self, prefix, days_limit):
        self.branches_info.clear()
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Copied logic from the fix
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
                remote_name = ref.name
                if remote_name.startswith("origin/"):
                    short_name = remote_name[7:]
                    if short_name.startswith(prefix):
                        if short_name not in candidates:
                            candidates[short_name] = {}
                        candidates[short_name]['remote'] = ref

        for name, refs in candidates.items():
            timestamps = []
            if 'local' in refs:
                timestamps.append(refs['local'].commit.committed_date)
            if 'remote' in refs:
                timestamps.append(refs['remote'].commit.committed_date)
            
            if not timestamps:
                continue
            
            max_ts = max(timestamps)
            commit_date = datetime.datetime.fromtimestamp(max_ts, datetime.timezone.utc)
            age_days = (now - commit_date).days
            
            if age_days >= days_limit:
                self.branches_info.append((name, commit_date, age_days))

def create_dummy_repo(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    repo = Repo.init(path)
    return repo

def verify_fix():
    base_path = os.path.abspath("verify_repo_test")
    remote_path = os.path.join(base_path, "remote")
    local_path = os.path.join(base_path, "local")

    # Create remote
    remote_repo = create_dummy_repo(remote_path)
    index = remote_repo.index
    index.commit("Initial commit")
    
    # Create a branch on remote
    remote_repo.create_head("feature/remote-only")
    
    # Clone to local
    if os.path.exists(local_path):
        shutil.rmtree(local_path)
    local_repo = Repo.clone_from(remote_path, local_path)
    
    # Create a local branch that is NOT on remote
    local_repo.create_head("feature/local-only")
    
    # Create a branch that exists on both (simulated by checking out remote branch)
    local_repo.create_head("feature/both", "origin/feature/remote-only") # Actually let's name it 'both'
    # Wait, to have it on remote, I need to push it or create it on remote first.
    # Let's create 'feature/both' on remote first.
    remote_repo.create_head("feature/both")
    
    # Fetch in local to see it
    local_repo.remotes.origin.fetch()
    
    # Now create local tracking branch for 'feature/both'
    local_repo.create_head("feature/both", "origin/feature/both")

    # Set commit dates to be OLD (e.g. 60 days ago) so they are picked up
    # We can't easily change commit date without rewriting history, but we can set days_limit to -1 or 0.
    # If we set days_limit to 0, any branch created just now (age 0 days) might be borderline.
    # Let's use days_limit = -1 to ensure everything is "older".
    
    app = MockBranchCleanerApp(local_path)
    app.query_branches("feature/", -1)
    
    print(f"Found {len(app.branches_info)} branches.")
    found_names = [b[0] for b in app.branches_info]
    print(f"Branches: {found_names}")
    
    expected = {"feature/local-only", "feature/remote-only", "feature/both"}
    
    # Note: 'feature/remote-only' exists on remote. Local has 'origin/feature/remote-only'.
    # Local does NOT have 'feature/remote-only' head.
    # My code should find it via remote refs.
    
    missing = expected - set(found_names)
    unexpected = set(found_names) - expected
    
    if not missing and not unexpected:
        print("SUCCESS: All expected branches found.")
    else:
        print(f"FAILURE: Missing: {missing}, Unexpected: {unexpected}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        verify_fix()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if os.path.exists("verify_repo_test"):
            try:
                shutil.rmtree("verify_repo_test")
            except:
                pass
