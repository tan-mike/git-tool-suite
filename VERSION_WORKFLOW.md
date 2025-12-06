# Version Management Workflow

All version information is centralized in `config.py` (`Config.APP_VERSION`).

---

## Prerequisites

Before releasing, ensure you have:

1. **GitHub CLI** installed and authenticated:

   ```bash
   winget install GitHub.cli
   gh auth login
   ```

2. **PyInstaller** installed:
   ```bash
   pip install pyinstaller
   ```

---

## Quick Release (Automated)

### 1. Update version in config.py

```python
# In config.py
APP_VERSION = "3.3.0"  # Change this
```

### 2. Run the automated release pipeline

```bash
python generate_version.py --release
```

This single command will:

- ✓ Check prerequisites (gh, pyinstaller, git)
- ✓ Verify git working directory is clean
- ✓ Confirm version not already released
- ✓ Generate version.json
- ✓ Build GitToolSuite.exe with PyInstaller
- ✓ Copy updater.py to dist/
- ✓ Create git tag `v3.3.0`
- ✓ Push tag to GitHub
- ✓ Create GitHub release
- ✓ Upload GitToolSuite.exe and updater.py to release

**That's it!** The entire release is automated.

---

## Other Commands

### Build Only (No Release)

```bash
python generate_version.py --build
```

Builds the application without creating a release. Useful for testing builds.

### Generate version.json Only

```bash
python generate_version.py
```

Just generates/updates `version.json` without building or releasing.

---

## Manual Release Steps (Advanced)

If you prefer manual control or automation fails:

### 1. Update version

```python
# config.py
APP_VERSION = "3.3.0"
```

### 2. Generate version.json

```bash
python generate_version.py
```

### 3. Build application

```bash
pyinstaller GitToolSuite.spec --clean
cp updater.py dist/
```

### 4. Create and push tag

```bash
git tag -a v3.3.0 -m "Release v3.3.0"
git push origin v3.3.0
```

### 5. Create GitHub release

```bash
gh release create v3.3.0 \
  dist/GitToolSuite.exe \
  dist/updater.py \
  --title "Git Tool Suite v3.3.0" \
  --notes "Release version 3.3.0" \
  --repo tan-mike/git-tool-suite
```

---

## Safety Features

The automated release includes:

- **Prerequisite checks** - Verifies required tools installed
- **Git status check** - Warns about uncommitted changes
- **Version check** - Prevents releasing duplicate versions
- **Confirmation prompt** - Requires typing "yes" to proceed
- **Step-by-step output** - Shows progress of each step
- **Error handling** - Graceful failures with helpful messages

---

## What happens after release?

1. **GitHub Actions** (if configured) will update the public gist with new version.json
2. **Auto-update feature** in the app will detect the new version
3. **Users** will be prompted to download and install the update

---

## Troubleshooting

### "gh: command not found"

Install GitHub CLI: `winget install GitHub.cli`
Then authenticate: `gh auth login`

### "pyinstaller: command not found"

Install PyInstaller: `pip install pyinstaller`

### Build fails

- Check `GitToolSuite.spec` exists
- Ensure all dependencies in `requirements.txt` are installed
- Try running `pyinstaller GitToolSuite.spec --clean` manually

### Release creation fails

- Verify you have push access to the repo
- Check GitHub CLI authentication: `gh auth status`
- Ensure the tag doesn't already exist: `git tag -l`
