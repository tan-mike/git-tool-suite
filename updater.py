"""
Auto-updater script for GitToolSuite.
This script downloads the new version, replaces the old executable, and restarts the app.
"""

import sys
import time
import os
import subprocess
import shutil
from pathlib import Path

def main():
    if len(sys.argv) != 3:
        print("Usage: updater.py <current_exe_path> <downloaded_exe_path>")
        sys.exit(1)
    
    current_exe = Path(sys.argv[1])
    downloaded_exe = Path(sys.argv[2])
    
    print(f"Waiting for main application to close...")
    time.sleep(2)  # Give main app time to close
    
    # Ensure the current exe is not running
    max_retries = 10
    for i in range(max_retries):
        try:
            # Try to rename (will fail if file is locked)
            temp_backup = current_exe.with_suffix('.exe.old')
            if temp_backup.exists():
                temp_backup.unlink()
            current_exe.rename(temp_backup)
            break
        except PermissionError:
            if i < max_retries - 1:
                print(f"Waiting for executable to close... ({i+1}/{max_retries})")
                time.sleep(1)
            else:
                print("ERROR: Could not replace executable. Please close the application manually.")
                input("Press Enter to exit...")
                sys.exit(1)
    
    try:
        # Copy new version to current location
        shutil.copy2(downloaded_exe, current_exe)
        print(f"Successfully updated to new version!")
        
        # Clean up
        downloaded_exe.unlink()
        temp_backup.unlink()
        
        # Restart the application
        print("Restarting application...")
        time.sleep(1)
        subprocess.Popen([str(current_exe)], cwd=current_exe.parent)
        
    except Exception as e:
        print(f"ERROR during update: {e}")
        # Restore backup if something went wrong
        if temp_backup.exists():
            temp_backup.rename(current_exe)
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
