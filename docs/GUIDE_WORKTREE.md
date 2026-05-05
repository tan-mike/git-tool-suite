# Worktree Manager Advanced Guide

The Worktree Manager is designed to solve the "context switching" problem by allowing you to work on multiple branches in parallel without the overhead of manually setting up your environment every time.

## 1. Tracking a Repository
Before you can manage worktrees, you must add a repository to the manager:
1. Go to the **Worktree Manager** tab.
2. Click **+ Add Repository**.
3. Select the folder containing your Git repository.

## 2. Setup Profiles (Automated Environment)
This is the most powerful feature. A **Profile** defines what should happen automatically when a new worktree is created.

### Files to Copy
Commonly used for non-git-tracked files like `.env` or specialized configuration.
- **Example**: Add `.env.local` to the list. When you create a worktree, the tool will copy `.env.local` from your main repository to the new worktree directory.

### Env Overrides
Inject or update environment variables in your `.env` file automatically.
- **Variable Interpolation**: You can use `${branch}` in the value.
- **Example**: `APP_URL=http://${branch}.local.test`
- If your branch is `feature/login`, the tool will automatically set `APP_URL=http://feature-login.local.test` in the worktree's `.env` file.

### Install Commands
Commands that must run to prepare the environment.
- **Example**: `npm install` or `composer install`.
- These run sequentially within the new worktree directory.

### Post-Setup Commands
Final hooks for framework-specific setup.
- **Example**: `php artisan key:generate` or `npm run build:dev`.

## 3. Creating a Worktree
1. Select a repository in the tree view.
2. Click **+ Create Worktree**.
3. Select the branch you want to work on.
4. **The Setup Sequence**:
   - `git worktree add` is executed.
   - Files are copied based on your profile.
   - Env Overrides are applied to the `.env` file.
   - Install commands are executed.
   - Post-setup commands are executed.

## 4. Integrated Editor Support
Once a worktree is created, you can right-click it (or select it and use the buttons) to:
- **Open in Editor**: Launches your configured IDE (VS Code, Cursor, etc.) directly at the worktree root.
- **Open Folder**: Opens the worktree in your system file explorer.

## 5. Cleaning Up
When you're done with a task:
1. Select the worktree.
2. Click **Remove Worktree**.
3. The tool will run `git worktree remove` and cleanup the directory.
