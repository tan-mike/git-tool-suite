import tkinter as tk
from tkinter import ttk, scrolledtext
import os
import re
from utils.ui_utils import CenteredDialog

class UserGuideDialog(CenteredDialog):
    def __init__(self, parent):
        super().__init__(parent, "User Guide", width=900, height=700)
        
        self.sections = {
            "Introduction": self._load_readme_section("Introduction") or "Welcome to Git Tools Suite.",
            "Commit Propagator": self._load_readme_section("1. Commit Propagator"),
            "Branch Cleanup": self._load_readme_section("2. Branch Cleanup"),
            "Pull Request Creator": self._load_readme_section("3. Pull Request Creator"),
            "Commit Tool": self._load_readme_section("4. Commit Tool"),
            "Branch Refresh": self._load_readme_section("5. Branch Refresh"),
            "Worktree Manager": self._load_worktree_guide(),
            "AI Features": self._load_readme_section("7. AI Features"),
            "Keyboard Shortcuts": "• Enter: Confirm/OK in dialogs\n• Escape: Cancel/Close dialogs\n• Ctrl+F: Filter branches (in Propagator)"
        }
        
        self.build_ui()
        
    def _load_readme_content(self):
        try:
            with open("README.md", "r", encoding="utf-8") as f:
                return f.read()
        except:
            return ""

    def _load_readme_section(self, section_title):
        content = self._load_readme_content()
        if not content:
            return ""
        
        # Simple extraction logic: find section and read until next major section
        # This is a heuristic and might need adjustment based on README structure
        pattern = f"### {re.escape(section_title)}.*?(?=\\n### |\\n## |$)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(0).strip()
        return ""

    def _load_worktree_guide(self):
        try:
            with open("docs/GUIDE_WORKTREE.md", "r", encoding="utf-8") as f:
                return f.read()
        except:
            return "Worktree Manager guide not found."

    def build_ui(self):
        # Main layout: Sidebar and Content
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Sidebar
        sidebar_frame = ttk.Frame(paned)
        paned.add(sidebar_frame, weight=1)
        
        ttk.Label(sidebar_frame, text="Table of Contents", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        self.toc_list = tk.Listbox(sidebar_frame, font=("", 10), background="#2b2b2b" if self._is_dark_mode() else "#ffffff", foreground="white" if self._is_dark_mode() else "black")
        self.toc_list.pack(fill=tk.BOTH, expand=True)
        
        for section in self.sections.keys():
            self.toc_list.insert(tk.END, section)
        
        self.toc_list.bind("<<ListboxSelect>>", self._on_section_select)
        
        # Content Area
        content_frame = ttk.Frame(paned)
        paned.add(content_frame, weight=4)
        
        self.text_area = scrolledtext.ScrolledText(content_frame, wrap=tk.WORD, font=("", 11), padx=20, pady=20)
        self.text_area.pack(fill=tk.BOTH, expand=True)
        
        # Define tags for rich text
        self.text_area.tag_configure("h1", font=("", 16, "bold"), spacing1=10, spacing3=10)
        self.text_area.tag_configure("h2", font=("", 14, "bold"), spacing1=8, spacing3=8)
        self.text_area.tag_configure("h3", font=("", 12, "bold"), spacing1=5, spacing3=5)
        self.text_area.tag_configure("bold", font=("", 11, "bold"))
        self.text_area.tag_configure("code", font=("Courier", 10), background="#3c3f41" if self._is_dark_mode() else "#f0f0f0")
        self.text_area.tag_configure("bullet", lmargin1=20, lmargin2=35)
        
        # Select first section by default
        self.toc_list.selection_set(0)
        self._on_section_select(None)

    def _is_dark_mode(self):
        try:
            import sv_ttk
            return sv_ttk.get_theme() == "dark"
        except:
            return True

    def _on_section_select(self, event):
        selection = self.toc_list.curselection()
        if not selection:
            return
        
        section_name = self.toc_list.get(selection[0])
        content = self.sections.get(section_name, "")
        
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete("1.0", tk.END)
        
        # Simple Markdown-ish parser
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# "):
                self.text_area.insert(tk.END, line[2:] + "\n", "h1")
            elif line.startswith("## "):
                self.text_area.insert(tk.END, line[3:] + "\n", "h2")
            elif line.startswith("### "):
                self.text_area.insert(tk.END, line[4:] + "\n", "h3")
            elif line.startswith("- ") or line.startswith("* "):
                self.text_area.insert(tk.END, "• " + line[2:] + "\n", "bullet")
            else:
                # Handle inline bold and code
                self._insert_styled_text(line + "\n")
        
        self.text_area.config(state=tk.DISABLED)

    def _insert_styled_text(self, text):
        # Very basic bold/code parsing
        parts = re.split(r"(\*\*.*?\*\*|`.*?`)", text)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                self.text_area.insert(tk.END, part[2:-2], "bold")
            elif part.startswith("`") and part.endswith("`"):
                self.text_area.insert(tk.END, part[1:-1], "code")
            else:
                self.text_area.insert(tk.END, part)
