# Git Tools Suite v3.6

A comprehensive desktop application for Git productivity, featuring commit propagation, branch cleanup, pull request creation, AI-powered commit generation, and automated worktree management.

## Features

### 1. Commit Propagator

- Cherry-pick commits across multiple branches
- **NEW v3.4:** Handle merge commits with parent selection
- **NEW v3.4:** 🔄 Fetch and ⬇️ Pull buttons for repository updates
- **NEW v3.4:** Select remote branches (origin/\*) as source
- **NEW v3.4:** Pull any branch without switching to it
- Combine multiple commits into one before propagating
- Filter target branches with real-time search
- Create new branches on-the-fly
- Optional automatic push to remote (with upstream tracking)

### 2. Branch Cleanup

- Query stale branches by age and prefix
- Bulk deletion of local/remote branches
- **IMPROVED:** Detects both local and remote stale branches
- Progress tracking and detailed logging

### 3. Pull Request Creator

- Create GitHub PRs from the desktop
- Branch filtering for easy selection
- Auto-fill PR details from commit messages
- **IMPROVED v3.4:** Push with upstream tracking enabled
- Preview changed files and commits before creating PR
- Open created PR directly in GitHub

### 4. Commit Tool

- Interactive staging area for files
- Generate conventional commit messages using Gemini AI
- Analyze diffs of staged changes
- Create branches with AI-generated names

### 5. Branch Refresh (NEW v3.5)

- Keep local development branches in sync with remote tracking branches
- Multi-repository support - track branches across multiple repos
- **Safety-first approach:**
  - Skips branches with uncommitted changes
  - Handles currently checked-out branches automatically
  - Only refreshes branches with valid remote tracking
- Manual refresh options:
  - Refresh all tracked branches across all repos
  - Refresh selected repository only
- Configuration persistence across sessions
- **Optimized performance** - instant loading even with 100+ branches
- Detailed operation logging

### 6. Worktree Manager (NEW v3.6)

- Manage parallel Git worktrees with automated environment setup.
- **Environment Automation**: Setup profiles for copying files (like `.env`) and running install commands (`npm install`, etc.).
- Integrated Editor support: Launch your IDE directly from the tool.
- Hierarchical view of repositories and active worktrees.
- Cross-platform support (Mac, Linux, Windows).

### 7. AI Features (Optional)

- Commit message generation
- PR title/description generation
- Branch name generation
- Joke generator powered by Google Gemini
- Birthday messages (December 12th)

### 8. Automatic Updates

- Check for updates from Settings tab
- **One-click auto-update** for executable builds
- Downloads and installs updates automatically
- Seamless restart after update
- Manual download option available

### 9. Responsive UI (NEW v3.4)

- **Auto-adapting window size** based on screen resolution
- Taskbar-aware positioning (Windows)
- Supports multiple monitor setups
- Minimum size: 800x600, Maximum: 1400x900

## Installation

### For Users (Executable)

Download and run the standalone executable - no installation required!

### For Developers

1. **Clone or extract the project**

2. **Install dependencies:**

   Run the setup script to create a virtual environment and install dependencies:
   
   ```bash
   ./setup_venv.sh
   ```
   
   Or manually:
   
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment (Optional, for AI features):**
   Create a `.env` file in the root directory:

   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

4. **Run the application:**
   ```bash
   source .venv/bin/activate
   python main.py
   ```

## Requirements

- Python 3.8+
- Git (command-line)
- GitHub CLI (`gh`) - for Pull Request feature
- GitPython library
- Requests library

## Project Structure

```
GitToolSuite_v3/
├── main.py                 # Application entry point
├── config.py               # Configuration and API key management
├── apps/                   # Application modules
│   ├── propagator.py      # Commit Propagator
│   ├── cleanup.py         # Branch Cleanup
│   ├── pull_request.py    # PR Creator
│   ├── commit_generator.py # Commit Tool
│   ├── branch_refresh.py  # Branch Refresh
│   └── settings.py        # Settings
├── utils/                  # Shared utilities
│   ├── git_utils.py       # Git operations
│   └── ui_utils.py        # UI helpers
├── ai/                     # AI integration
│   └── gemini_client.py   # Gemini API client
├── build_helpers/          # Build scripts
│   └── obfuscate_key.py   # API key obfuscation
└── tests/                  # Unit tests
```

## Building Executable

For developers who want to create a standalone executable:

1. **Set API key (optional, for AI features):**
   Set `GEMINI_API_KEY` in your environment variables OR ensure it is present in your `.env` file.

   ```bash
   # Option A: Environment Variable (Linux/Mac)
   export GEMINI_API_KEY="your_api_key_here"

   # Option B: Environment Variable (Windows PowerShell)
   $env:GEMINI_API_KEY="your_api_key_here"
   ```

2. **Obfuscate and inject key:**

   ```bash
   python build_helpers/obfuscate_key.py
   ```

3. **Build with PyInstaller:**

   ```bash
   # With icon (recommended)
   pyinstaller --onefile --windowed --icon=assets/app_icon.ico --name GitToolSuite main.py

   # Or use the automated build script
   python generate_version.py --build
   ```

   **Note:** If using a custom .spec file, add the icon parameter:

   ```python
   # In GitToolSuite.spec
   exe = EXE(
       # ... other parameters ...
       icon='assets/app_icon.ico',
   )
   ```

4. **Distribute:**
   - Executable will be in `dist/GitToolSuite.exe`
   - No configuration needed by end users!

## Configuration

User preferences are automatically saved to `~/.git-tool-suite/preferences.json`:

- Last used repository path
- Propagator settings (max commits, auto-push)
- Cleanup defaults (prefix, days, scope)
- PR creator defaults
- Branch refresh tracked repositories

## New in Version 3.5.0

- **Branch Refresh** - Automated synchronization of local branches with remote tracking branches
- **Multi-Repository Tracking** - Manage branches across multiple repos simultaneously
- **Safety Checks** - Uncommitted changes detection and current branch handling
- **Performance Optimization** - 11x-101x faster branch loading using batch git commands

## New in Version 3.4

- **Merge Commit Support** - Detect, filter, and cherry-pick merge commits with parent selection
- **Fetch & Pull** - Synchronize repositories directly from Commit Propagator
- **Remote Branches** - Select origin/\* branches as source for propagation
- **Upstream Tracking** - All pushes establish proper tracking relationships
- **Responsive UI** - Auto-sizing window with taskbar awareness

## New in Version 3.2

- **Automatic Updates** - One-click download and install updates from Settings tab
- **Update Checking** - Automatic version checking against GitHub releases
- **GitHub Actions** - Automated Gist synchronization for version information
- **Improved Documentation** - Better API key setup and configuration guides

## New in Version 3.1

- **Commit Tool** - Stage files and generate AI commit messages
- **Enhanced PR Creator** - Preview files/commits and open in browser
- **Improved Branch Cleanup** - Better detection of local stale branches
- **Bug Fixes** - Various stability improvements

## New in Version 3.0

- **Modular architecture** - Clean separation of concerns
- **Multi-commit combination** - Squash commits before cherry-picking
- **Bundled API key** - No user configuration needed for AI features
- **Persistent preferences** - Settings saved across sessions
- **Enhanced security** - Improved API key obfuscation

## License

This project is for personal/educational use.
