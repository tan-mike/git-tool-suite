"""
Auto-updater script for GitToolSuite.
This script extracts the new version from ZIP, replaces the old executable, and restarts the app.
"""

import sys
import time
import os
import subprocess
import shutil
import zipfile
from pathlib import Path

def main():
    if len(sys.argv) != 3:
        print("Usage: updater.exe <current_exe_path> <downloaded_zip_path>")
        sys.exit(1)
    
    current_exe = Path(sys.argv[1])
    downloaded_zip = Path(sys.argv[2])
    app_dir = current_exe.parent
    
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
        print(f"Extracting update from {downloaded_zip.name}...")
        
        # We need to handle self-update (updater.exe)
        # We are currently running updater.exe. To update it, we must rename ourselves.
        current_updater = Path(sys.executable)
        updater_backup = None
        
        if current_updater.name.lower() == 'updater.exe':
            try:
                updater_backup = current_updater.with_suffix('.exe.old')
                if updater_backup.exists():
                    updater_backup.unlink()
                # Rename running executable to .old (Windows allows this)
                current_updater.rename(updater_backup)
            except Exception as e:
                print(f"Warning: Could not enable self-update: {e}")
        
        # Extract ZIP contents
        with zipfile.ZipFile(downloaded_zip, 'r') as zip_ref:
            zip_ref.extractall(app_dir)
            
        print(f"Successfully updated to new version!")
        
        # Clean up
        if downloaded_zip.exists():
            downloaded_zip.unlink()
        
        # Cleanup backups
        if temp_backup.exists():
            try:
                temp_backup.unlink()
            except:
                pass # Ignore if we can't delete backup yet
                
        if updater_backup and updater_backup.exists():
            try:
                # Schedule deletion on next reboot or just leave it
                # We can't delete it while our process (which originated from it) is technically still closing?
                # Actually, if we renamed running exe, we can't delete it while running.
                pass
            except:
                pass

        # Restart the application
        print("Restarting application...")
        time.sleep(1)
        
        # Hide console window on Windows
        creation_flags = 0
        if sys.platform == 'win32':
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        subprocess.Popen(
            [str(current_exe)], 
            cwd=app_dir,
            creationflags=creation_flags
        )
        
    except Exception as e:
        print(f"ERROR during update: {e}")
        # Restore backup if something went wrong
        if temp_backup.exists():
            if current_exe.exists():
                current_exe.unlink()
            temp_backup.rename(current_exe)
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
