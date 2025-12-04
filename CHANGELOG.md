# Changelog

All notable changes to this project will be documented in this file.

## [3.2] - 2025-12-04

### Added

- **Update Check Feature**: Implemented automatic update checking via Settings tab.
  - Fetches latest version from public Gist.
  - Compares current version against latest release.
  - Opens release page in browser when update is available.
- **GitHub Actions Workflow**: Automated Gist updates for `version.json`.
  - Triggers on push to `master` branch when `version.json` changes.
  - Automatically synchronizes version info to public Gist.
- **Version Management**: Created `version.json` for centralized version tracking.

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
