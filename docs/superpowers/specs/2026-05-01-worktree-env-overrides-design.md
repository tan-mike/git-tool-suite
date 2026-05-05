# Worktree Env Overrides Design

## Goal
Provide an automated way to override specific environment variables in `.env` files when creating a new git worktree. This enables dynamic adjustments (e.g., unique database names, different ports) for parallel worktrees without requiring manual edits or post-setup shell scripts.

## Proposed Changes

### 1. Configuration Model
The `Config` store (which manages `worktree` profiles per repository) will be expanded to include an `"env_overrides": []` list for each repository's profile.
- Entries are strings in the format `KEY=VALUE`.
- Dynamic variable substitution will be supported, specifically `${branch}` which resolves to the target branch name.

### 2. UI Updates (`apps/worktree.py`)
- Add a 4th listbox titled "Env Overrides" to the `Setup Profile` panel, adjacent to "Files to Copy", "Install Cmds", and "Post-Setup Cmds".
- Include standard `+`, `-`, `↑`, `↓` controls.
- When `+` is clicked, prompt the user to input the override (e.g., `APP_PORT=8001`). Basic validation ensures the input contains an `=` sign.

### 3. Core Logic (`apps/worktree.py`)
- In `_create_worktree_worker`, after the file copy step (where `.env` is typically duplicated into the new worktree), the script will check if `.env` exists in the target worktree.
- If `env_overrides` has entries:
  - Read the `.env` file line by line.
  - For each override, parse the `KEY` and `VALUE`. Substitute `${branch}` in the `VALUE`.
  - Scan the file content for `KEY=`. 
    - If found, replace the line with `KEY=VALUE`.
    - If not found, append `KEY=VALUE` to the end of the file.
  - Write the modifications back to `.env`.

## Verification Plan
- Add a repository to the Worktree Manager.
- Add `.env` to "Files to Copy".
- Add `TEST_KEY=test_${branch}` to "Env Overrides".
- Create a worktree.
- Verify the copied `.env` contains the substituted value and that existing keys are properly overwritten.
