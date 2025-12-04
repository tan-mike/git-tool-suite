# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-12-04

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

- Updated application title to "Git Productivity Tools Suite Ver: 1.0.0".
