"""
Generate version.json, build application, and create GitHub releases.
Automates the entire release pipeline.
"""

import json
import sys
import shutil
import subprocess
import argparse
import zipfile
from pathlib import Path
from config import Config


def generate_version_json():
    """Generate version.json with data from Config."""
    version_data = {
        "version": Config.APP_VERSION,
        "release_url": "https://github.com/tan-mike/git-tool-suite/releases",
        # Updated to point to the ZIP file
        "download_url": f"https://github.com/tan-mike/git-tool-suite/releases/download/v{Config.APP_VERSION}/GitToolSuite-v{Config.APP_VERSION}.zip"
    }
    
    # Write to version.json
    version_file = Path(__file__).parent / "version.json"
    with open(version_file, 'w') as f:
        json.dump(version_data, f, indent=2)
    
    print(f"✓ Generated version.json for version {Config.APP_VERSION}")
    print(f"  Release URL: {version_data['release_url']}")
    print(f"  Download URL: {version_data['download_url']}")
    
    return version_data


def check_prerequisites():
    """Check that required tools are installed."""
    print("\n=== Checking Prerequisites ===")
    
    tools = {
        'pyinstaller': 'PyInstaller (for building)',
        'gh': 'GitHub CLI (for releases)',
        'git': 'Git (for tagging)'
    }
    
    missing = []
    for tool, description in tools.items():
        if not shutil.which(tool):
            print(f"✗ {description} - NOT FOUND")
            missing.append(tool)
        else:
            print(f"✓ {description}")
    
    if missing:
        print(f"\n❌ Missing required tools: {', '.join(missing)}")
        print("\nInstallation instructions:")
        if 'gh' in missing:
            print("  GitHub CLI: winget install GitHub.cli")
            print("  Then run: gh auth login")
        if 'pyinstaller' in missing:
            print("  PyInstaller: pip install pyinstaller")
        return False
    
    print("✓ All prerequisites met")
    return True


def check_git_status():
    """Verify git working directory is clean."""
    print("\n=== Checking Git Status ===")
    
    try:
        # Check for uncommitted changes
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout.strip():
            print("⚠ Warning: You have uncommitted changes:")
            print(result.stdout)
            response = input("\nContinue anyway? (y/N): ")
            if response.lower() != 'y':
                print("❌ Aborted")
                return False
        else:
            print("✓ Working directory clean")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error: {e}")
        return False


def check_version_not_released(version):
    """Check if version tag already exists."""
    print(f"\n=== Checking if v{version} already released ===")
    
    try:
        # Check local tags
        result = subprocess.run(
            ['git', 'tag', '-l', f'v{version}'],
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout.strip():
            print(f"❌ Tag v{version} already exists locally")
            return False
        
        # Check remote tags
        result = subprocess.run(
            ['git', 'ls-remote', '--tags', 'origin', f'refs/tags/v{version}'],
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout.strip():
            print(f"❌ Tag v{version} already exists on remote")
            return False
        
        print(f"✓ Version v{version} not yet released")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"⚠ Warning: Could not check remote tags: {e}")
        return True  # Continue anyway


def build_application():
    """Build the application using PyInstaller."""
    print("\n=== Building Application ===")
    
    # Clean previous builds
    print("Cleaning previous builds...")
    shutil.rmtree('dist', ignore_errors=True)
    shutil.rmtree('build', ignore_errors=True)
    
    # Check if spec file exists
    spec_file = Path('GitToolSuite.spec')
    if not spec_file.exists():
        print("❌ GitToolSuite.spec not found")
        return None, None
    
    # Run PyInstaller for main app
    print("Running PyInstaller for GitToolSuite...")
    try:
        # Hide console window on Windows
        creation_flags = 0
        if sys.platform == 'win32':
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(
            ['pyinstaller', 'GitToolSuite.spec', '--clean'],
            check=True,
            capture_output=True,
            text=True,
            creationflags=creation_flags
        )
        # print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        print(e.stderr)
        return None, None
    
    # Verify main output
    exe_path = Path('dist/GitToolSuite.exe')
    if not exe_path.exists():
        print("❌ Build failed - executable not found at dist/GitToolSuite.exe")
        return None, None
    
    file_size = exe_path.stat().st_size / (1024 * 1024)  # MB
    print(f"✓ Main application built: {exe_path} ({file_size:.2f} MB)")

    # Build updater
    updater_path = build_updater()
    
    return exe_path, updater_path


def build_updater():
    """Build updater.exe using PyInstaller."""
    print("\nBuilding updater executable...")
    
    spec_file = Path('updater.spec')
    if not spec_file.exists():
        print("⚠ updater.spec not found, skipping updater build")
        return None
        
    try:
        # Hide console window on Windows
        creation_flags = 0
        if sys.platform == 'win32':
            creation_flags = subprocess.CREATE_NO_WINDOW
            
        result = subprocess.run(
            ['pyinstaller', 'updater.spec', '--clean'],
            check=True,
            capture_output=True,
            text=True,
            creationflags=creation_flags
        )
        
        updater_path = Path('dist/updater.exe')
        if updater_path.exists():
            size_mb = updater_path.stat().st_size / (1024 * 1024)
            print(f"✓ Updater built: {updater_path} ({size_mb:.2f} MB)")
            return updater_path
        else:
            print("❌ Updater build failed - exe not found")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Updater build failed: {e}")
        return None


def create_release_bundle(version, exe_path, updater_path):
    """Package both executables into a single ZIP."""
    bundle_name = f"GitToolSuite-v{version}.zip"
    bundle_path = Path("dist") / bundle_name
    
    print(f"\nCreating release bundle: {bundle_name}")
    
    with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add main app
        zf.write(exe_path, exe_path.name)
        
        # Add updater if exists
        if updater_path and updater_path.exists():
            zf.write(updater_path, updater_path.name)
        
        # Add README
        readme = f"""Git Tool Suite v{version}
=====================================

QUICK START
-----------
1. Extract all files to a folder
2. Run GitToolSuite.exe
3. No installation or Python required!

FILES
-----
- GitToolSuite.exe - Main application
- updater.exe - Auto-updater (used automatically)

REQUIREMENTS
------------
- Windows 10 or later
- No additional software needed

MORE INFO
---------
GitHub: https://github.com/tan-mike/git-tool-suite
"""
        zf.writestr('README.txt', readme)
    
    size_mb = bundle_path.stat().st_size / (1024 * 1024)
    print(f"✓ Bundle created: {bundle_path} ({size_mb:.2f} MB)")
    return bundle_path


def create_git_tag(version):
    """Create and push a git tag for the version."""
    print(f"\n=== Creating Git Tag v{version} ===")
    
    tag_name = f"v{version}"
    
    try:
        # Create tag
        print(f"Creating tag {tag_name}...")
        subprocess.run(
            ['git', 'tag', '-a', tag_name, '-m', f'Release {tag_name}'],
            check=True
        )
        print(f"✓ Tag {tag_name} created locally")
        
        # Push tag
        print(f"Pushing tag to origin...")
        subprocess.run(
            ['git', 'push', 'origin', tag_name],
            check=True
        )
        print(f"✓ Tag {tag_name} pushed to origin")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create/push tag: {e}")
        return False


def create_github_release(version, bundle_path, release_notes=None):
    """Create a GitHub release using gh CLI."""
    print(f"\n=== Creating GitHub Release v{version} ===")
    
    tag_name = f"v{version}"
    
    # Prepare release notes
    if not release_notes:
        release_notes = f"""# Git Tool Suite v{version}

## Download
- [GitToolSuite-v{version}.zip]({Config.UPDATE_CHECK_URL.replace('/raw/', '/download/')}/v{version}/GitToolSuite-v{version}.zip)

## What's New
See [CHANGELOG.md](https://github.com/tan-mike/git-tool-suite/blob/main/CHANGELOG.md) for details.

## Installation
1. Download the ZIP file
2. Extract all contents to a folder
3. Run `GitToolSuite.exe`

No installation required!
"""
    
    try:
        # Create release with gh CLI
        print(f"Creating release {tag_name} with bundle...")
        
        cmd = [
            'gh', 'release', 'create', tag_name,
            str(bundle_path),
            '--title', f'Git Tool Suite v{version}',
            '--notes', release_notes,
            '--repo', 'tan-mike/git-tool-suite'
        ]
        
        subprocess.run(cmd, check=True)
        
        print(f"✓ Release v{version} created successfully!")
        print(f"  View: https://github.com/tan-mike/git-tool-suite/releases/tag/{tag_name}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create GitHub release: {e}")
        return False


def run_build_only():
    """Run build without creating a release."""
    print("\n" + "="*60)
    print(f"  BUILD ONLY - Version {Config.APP_VERSION}")
    print("="*60)
    
    if not check_prerequisites():
        return 1
    
    exe_path, updater_path = build_application()
    if not exe_path:
        return 1
    
    # Also create the bundle for testing
    bundle_path = create_release_bundle(Config.APP_VERSION, exe_path, updater_path)
    
    print("\n✅ Build completed successfully!")
    print(f"   Bundle: {bundle_path}")
    return 0


def run_full_release():
    """Run the full release pipeline."""
    version = Config.APP_VERSION
    
    print("\n" + "="*60)
    print(f"  RELEASE PIPELINE - Version {version}")
    print("="*60)
    
    # Step 1: Prerequisites
    if not check_prerequisites():
        return 1
    
    # Step 2: Git status check
    if not check_git_status():
        return 1
    
    # Step 3: Check version not already released
    if not check_version_not_released(version):
        return 1
    
    # Confirmation
    print(f"\n{'='*60}")
    print(f"  READY TO RELEASE v{version}")
    print(f"{'='*60}")
    print("\nThis will:")
    print(f"  1. Generate version.json")
    print(f"  2. Build GitToolSuite.exe AND updater.exe")
    print(f"  3. Create ZIP bundle")
    print(f"  4. Create git tag v{version}")
    print(f"  5. Push tag to GitHub")
    print(f"  6. Create GitHub release with ZIP bundle")
    
    response = input(f"\nProceed with release v{version}? (yes/N): ")
    if response.lower() != 'yes':
        print("❌ Release cancelled")
        return 1
    
    # Step 4: Generate version.json
    version_data = generate_version_json()
    
    # Step 5: Build everything
    exe_path, updater_path = build_application()
    if not exe_path:
        return 1
    
    # Step 6: Create Bundle
    bundle_path = create_release_bundle(version, exe_path, updater_path)
    
    # Step 7: Create tag
    if not create_git_tag(version):
        print("\n⚠ Warning: Tag creation failed, but build succeeded")
        return 1
    
    # Step 8: Create GitHub release
    if not create_github_release(version, bundle_path):
        print("\n⚠ Warning: GitHub release creation failed")
        return 1
    
    # Success!
    print("\n" + "="*60)
    print("  ✅ RELEASE COMPLETE!")
    print("="*60)
    print(f"\n  Version: {version}")
    print(f"  Bundle: {bundle_path}")
    print(f"  Release: https://github.com/tan-mike/git-tool-suite/releases/tag/v{version}")
    print(f"\n  Next steps:")
    print(f"    1. Update CHANGELOG.md with release notes")
    print(f"    2. Let GitHub Actions update the version gist")
    print(f"    3. Test the auto-update feature")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Generate version.json and optionally build/release the application'
    )
    parser.add_argument(
        '--build',
        action='store_true',
        help='Build the application with PyInstaller'
    )
    parser.add_argument(
        '--release',
        action='store_true',
        help='Run the full release pipeline (build + tag + GitHub release)'
    )
    
    args = parser.parse_args()
    
    if args.release:
        return run_full_release()
    elif args.build:
        return run_build_only()
    else:
        # Default: just generate version.json
        generate_version_json()
        return 0


if __name__ == "__main__":
    sys.exit(main())
