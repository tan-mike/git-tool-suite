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
        print("Usage: updater <current_exe_path> <downloaded_zip_path>")
        sys.exit(1)
    
    current_exe = Path(sys.argv[1])
    downloaded_zip = Path(sys.argv[2])

    # Resolve correct app directory.
    # If .app bundle, current_exe might be inside Contents/MacOS
    # We want the directory containing the .app bundle (or the exe if windows)
    if sys.platform == 'darwin' and '.app/Contents/MacOS' in str(current_exe):
         # Walk up until we find the .app folder
         temp_path = current_exe
         while temp_path.parent != temp_path:
             if temp_path.name.endswith('.app'):
                 current_exe = temp_path # We want to replace the whole .app
                 break
             temp_path = temp_path.parent

    app_dir = current_exe.parent
    
    print(f"Waiting for main application to close...")
    time.sleep(2)  # Give main app time to close
    
    # Platform-specific backup extension
    backup_suffix = '.exe.old' if sys.platform == 'win32' else '.old'

    # Ensure the current exe is not running
    # On Windows, we loop and rename. On POSIX, we can usually just rename/unlink even if running (but rename is safer).
    max_retries = 10
    temp_backup = current_exe.with_suffix(backup_suffix)

    for i in range(max_retries):
        try:
            # Try to rename (will fail if file is locked on Windows)
            if temp_backup.exists():
                if temp_backup.is_dir():
                    shutil.rmtree(temp_backup)
                else:
                    temp_backup.unlink()

            # Use os.replace for atomic replacement if possible (Python 3.3+)
            # But here we are moving the *current* exe to backup
            # shutil.move or os.rename
            os.rename(current_exe, temp_backup)
            break
        except PermissionError:
            if i < max_retries - 1:
                print(f"Waiting for executable to close... ({i+1}/{max_retries})")
                time.sleep(1)
            else:
                print("ERROR: Could not replace executable. Please close the application manually.")
                if sys.platform == 'win32':
                    input("Press Enter to exit...")
                sys.exit(1)
        except FileNotFoundError:
             # Already gone?
             break
        except OSError as e:
             print(f"OS Error during rename: {e}")
             if i < max_retries - 1:
                time.sleep(1)
             else:
                sys.exit(1)

    try:
        print(f"Extracting update from {downloaded_zip.name}...")
        
        # We need to handle self-update (updater itself)
        current_updater = Path(sys.executable)
        updater_backup = None
        
        # Check if we are running the updater and need to update it
        updater_name = 'updater.exe' if sys.platform == 'win32' else 'updater'

        if current_updater.name.lower() == updater_name.lower():
            try:
                updater_backup = current_updater.with_suffix(backup_suffix)
                if updater_backup.exists():
                    updater_backup.unlink()

                # Rename running executable to .old
                # Windows allows renaming running files, POSIX allows unlinking/renaming
                os.rename(current_updater, updater_backup)
            except Exception as e:
                print(f"Warning: Could not enable self-update: {e}")
        
        # Extract ZIP contents
        # On Mac, if it's a .app bundle, unzip preserves directory structure
        with zipfile.ZipFile(downloaded_zip, 'r') as zip_ref:
            # On Unix, we might need to preserve permissions (chmod +x)
            # zipfile.extractall doesn't always preserve permissions
            zip_ref.extractall(app_dir)
            
            # Restore permissions for executables on Unix
            if sys.platform != 'win32':
                for info in zip_ref.infolist():
                    extracted_path = app_dir / info.filename
                    # Check if it was executable (external_attr >> 16)
                    # 0o755 is rwxr-xr-x
                    # ZIP external_attr:
                    # Unix attributes are in the high order 16 bits
                    unix_mode = info.external_attr >> 16
                    if unix_mode:
                        os.chmod(extracted_path, unix_mode)

                    # Ensure the main executable is executable if detection fails
                    # If we extracted a .app, we need to chmod the binary inside
                    if current_exe.name.endswith('.app'):
                        # Try to find binary inside .app
                        # Convention: App.app/Contents/MacOS/App
                        app_name = current_exe.stem
                        binary_path = extracted_path
                        if binary_path.name == app_name and 'Contents/MacOS' in str(binary_path):
                             os.chmod(binary_path, 0o755)
                    elif extracted_path.name == current_exe.name:
                         os.chmod(extracted_path, 0o755)

        print(f"Successfully updated to new version!")
        
        # Clean up
        if downloaded_zip.exists():
            downloaded_zip.unlink()
        
        # Cleanup backups
        if temp_backup.exists():
            try:
                if temp_backup.is_dir():
                    shutil.rmtree(temp_backup)
                else:
                    temp_backup.unlink()
            except:
                pass
                
        if updater_backup and updater_backup.exists():
            try:
                # Can't easily delete running executable's file on Windows immediately
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
        
        # On Mac .app bundle, we might need to open using 'open' command or execute the binary inside
        # If current_exe points to the .app folder, we should use 'open'

        cmd = [str(current_exe)]

        if sys.platform == 'darwin' and str(current_exe).endswith('.app'):
            cmd = ['open', str(current_exe)]
            subprocess.Popen(cmd, cwd=app_dir)
        else:
            subprocess.Popen(
                cmd,
                cwd=app_dir,
                creationflags=creation_flags
            )
        
    except Exception as e:
        print(f"ERROR during update: {e}")
        # Restore backup if something went wrong
        if temp_backup.exists():
            if current_exe.exists():
                 # Should probably unlink partial new file first
                 try:
                    if current_exe.is_dir():
                        shutil.rmtree(current_exe)
                    else:
                        current_exe.unlink()
                 except: pass
            temp_backup.rename(current_exe)

            # Restore permissions
            if sys.platform != 'win32':
                 # If it was a file, chmod it. If dir (.app), we might need to find binary?
                 # Actually if we moved back the backup, permissions should be preserved unless .old lost them?
                 # os.rename preserves metadata usually.
                 pass

        if sys.platform == 'win32':
            input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
