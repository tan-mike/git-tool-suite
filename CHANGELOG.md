# Changelog

All notable changes to this project will be documented in this file.

## [3.4] - 2025-12-10

### Added

- **Merge Commit Handling**: Full support for cherry-picking merge commits in Commit Propagator.
  - Automatic merge commit detection (commits with multiple parents).
  - Default filtering to hide merge commits (prevents accidental errors).
  - "Show merge commits" checkbox to toggle visibility with 🔀 indicator.
  - Parent selection dialog when cherry-picking merge commits.
  - Automatic `-m` flag insertion for correct merge commit propagation.
- **Fetch & Pull Operations**: Repository synchronization directly from Commit Propagator.
  - 🔄 Fetch button to update all remote branch references.
  - ⬇️ Pull button with branch selection dialog.
  - Pull any local branch without switching to it first.
  - Branch filter for quick branch lookup.
  - Auto-refresh of branch lists after fetch/pull.
- **Remote Branch Selection**: Select remote branches as source in Commit Propagator.
  - "Include remote branches (origin/\*)" checkbox.
  - Filter support for both local and remote branches.
  - View commits from any origin/\* branch for propagation.
- **Upstream Tracking**: All push operations now use `-u` flag.
  - Establishes proper tracking relationships.
  - Enables Git UIs to detect remote branches correctly.
  - Shows ahead/behind status in git status.
  - Applied to Propagator and Pull Request tools.
- **Responsive UI**: Window sizing adapts to screen dimensions.
  - Auto-detects screen resolution.
  - Accounts for Windows taskbar (60px).
  - Uses 90% width and 85% of usable height.
  - Maximum window size: 1400x900.
  - Minimum window size: 800x600.
  - Auto-centers window on screen.

### Changed

- Updated application version to 3.4.0.
- Improved window geometry calculation for better multi-monitor support.
- Enhanced branch loading to include both local and remote branches.

### Fixed

- Fixed issue where other Git UIs couldn't detect remote branches after push.
- Fixed window positioning to prevent taskbar overlap.
- Improved merge commit error handling with clear user guidance.

## [3.2] - 2025-12-04

### Added

- **Automatic Update System**: Full auto-update functionality for executable builds.
  - One-click download and installation of new versions.
  - Background download with progress indicator.
  - Automatic executable replacement via updater script.
  - Seamless restart after update completion.
- **Update Check Feature**: Implemented automatic update checking via Settings tab.
  - Fetches latest version from public Gist.
  - Compares current version against latest release.
  - Three-option update dialog: Auto-install, Manual download, or Skip.
- **GitHub Actions Workflow**: Automated Gist updates for `version.json`.
  - Triggers on push to `master` branch when `version.json` changes.
  - Automatically synchronizes version info to public Gist.
- **Version Management**: Created `version.json` for centralized version tracking.
  - Includes version number, release URL, and download URL.
- **Updater Script**: Helper script (`updater.py`) for safe executable replacement.

### Changed

- Updated `UPDATE_CHECK_URL` to use public Gist instead of raw GitHub URL.
- Improved API key configuration documentation in README.
- Updated application version to 3.2.

### Fixed

- Fixed `NameError` in Settings app when update check fails.
- Added `.gitignore` to exclude `__pycache__`, `.pyc` files, and `.env` files.

## [3.1] - 2025-12-04

### Added

- **Commit Tool**: A new tab for staging files and generating commit messages using Gemini AI.
  - Interactive staging area (stage/unstage selected files).
  - AI-powered commit message generation based on staged diffs.
- **Pull Request Enhancements**:
  - "Preview Changes" section with "Files Changed" and "Commits" tabs.
  - "View on GitHub" button to open the created PR in the browser.

### Fixed

- **Branch Cleanup**: Fixed an issue where local branches without remote tracking branches were not being listed. The tool now correctly identifies and lists both local and remote stale branches.

### Changed

- Updated application title to "Git Productivity Tools Suite Ver: 3.1".
