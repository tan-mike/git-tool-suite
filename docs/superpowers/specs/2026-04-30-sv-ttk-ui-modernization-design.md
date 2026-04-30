# UI Modernization: sv_ttk Integration Design

## 1. Goal
Modernize the Git Tools Suite UI to look like a modern, sleek desktop application across all platforms using the `sv_ttk` (Sun Valley) library. This applies a Microsoft "Fluent Design" system to all existing Tkinter `ttk` widgets.

## 2. Approach & Architecture
We will use `sv_ttk` as a drop-in theme replacement for the standard Tkinter themes.
- **Dependency**: Add `sv-ttk` to `requirements.txt`.
- **Global Initialization**: Inside `main.py`, immediately after creating the root `tk.Tk()` window, we will invoke `sv_ttk.set_theme("dark")`. This cascades the styling rules to all child widgets automatically.

## 3. Component Adjustments
While `sv_ttk` is mostly a drop-in solution, it modifies default paddings, row heights, and standard fonts. We must review and patch the following specific areas:

### 3.1 Hardcoded Fonts & Colors
- **Log Texts**: Any hardcoded fonts (like `font=("Courier", 9)`) will be reviewed. If they clash with `sv_ttk`'s typography, they will be adjusted.
- **Grayscales**: Custom foreground colors like `foreground="gray"` (used in path previews) need to be tested for legibility in both dark and light modes.

### 3.2 Treeview Spacing
- `sv_ttk` alters `ttk.Treeview` default row heights. If the Branch Refresh or Worktree Manager trees look too compact or too padded, we will apply a custom `ttk.Style().configure("Treeview", rowheight=X)` override.

## 4. Theme Toggle Feature
To take full advantage of the library:
- **Location**: Add a "Toggle Theme" button inside the `SettingsApp` (`apps/settings.py`).
- **Action**: The button will trigger `sv_ttk.toggle_theme()`, allowing users to switch between Light and Dark modes without restarting the application.
- **State Persistence**: (Optional, future enhancement) We may save the active theme preference in `config.py` to persist across sessions.

## 5. Trade-offs
- **Non-Native macOS Styling**: The app will not use Apple HIG. It will look like a Fluent Windows app on macOS.
- **Padding Overrides**: We may need to tweak `padx`/`pady` in frames that relied on the very tight default Tkinter packing.
