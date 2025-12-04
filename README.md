# Git Tools Suite v3.1

A comprehensive desktop application for Git productivity, featuring commit propagation, branch cleanup, pull request creation, and AI-powered commit generation.

## Features

### 1. Commit Propagator

- Cherry-pick commits across multiple branches
- **NEW:** Combine multiple commits into one before propagating
- Filter target branches with real-time search
- Create new branches on-the-fly
- Optional automatic push to remote

### 2. Branch Cleanup

- Query stale branches by age and prefix
- Bulk deletion of local/remote branches
- **IMPROVED:** Detects both local and remote stale branches
- Progress tracking and detailed logging

### 3. Pull Request Creator

- Create GitHub PRs from the desktop
- Branch filtering for easy selection
- Auto-fill PR details from commit messages
- **NEW:** Preview changed files and commits before creating PR
- **NEW:** Open created PR directly in GitHub

### 4. Commit Tool (NEW)

- Interactive staging area for files
- Generate conventional commit messages using Gemini AI
- Analyze diffs of staged changes

### 5. AI Features (Optional)

- Commit message generation
- PR title/description generation
- Joke generator powered by Google Gemini
- Birthday messages (December 12th)

## Installation

### For Users (Executable)

Download and run the standalone executable - no installation required!

### For Developers

1. **Clone or extract the project**

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment (Optional, for AI features):**
   Create a `.env` file in the root directory:

   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

4. **Run the application:**
   ```bash
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
│   └── commit_generator.py # Commit Tool
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
   pyinstaller --onefile --windowed --name GitToolSuite main.py
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
