"""
Commit Message Generator Application.
Allows users to stage files and generate commit messages using Gemini AI.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import os
import threading

from config import Config
from ai.gemini_client import GeminiClient

class CommitGeneratorApp:
    def __init__(self, parent):
        self.parent = parent
        self.repo_path = tk.StringVar()
        self.current_branch = tk.StringVar()
        self.gemini_client = GeminiClient()
        
        self.main_frame = ttk.Frame(self.parent, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.build_ui()
        
    def build_ui(self):
        # 1. Repository Selection
        repo_frame = ttk.LabelFrame(self.main_frame, text="1. Repository & Branch", padding="10")
        repo_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(repo_frame, textvariable=self.repo_path, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(repo_frame, text="Browse...", command=self.browse_repository).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(repo_frame, text="Branch:").pack(side=tk.LEFT)
        ttk.Label(repo_frame, textvariable=self.current_branch, font=("", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(repo_frame, text="Refresh", command=self.refresh_status).pack(side=tk.RIGHT)
        ttk.Button(repo_frame, text="New Branch...", command=self.create_branch_dialog).pack(side=tk.RIGHT, padx=5)

        # 2. Staging Area (PanedWindow)
        paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Left: Unstaged
        unstaged_frame = ttk.LabelFrame(paned, text="Unstaged Changes", padding="5")
        paned.add(unstaged_frame, weight=1)
        
        self.unstaged_list = tk.Listbox(unstaged_frame, selectmode=tk.EXTENDED, width=40)
        self.unstaged_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_unstaged = ttk.Scrollbar(unstaged_frame, orient="vertical", command=self.unstaged_list.yview)
        sb_unstaged.pack(side=tk.RIGHT, fill=tk.Y)
        self.unstaged_list.config(yscrollcommand=sb_unstaged.set)
        
        # Middle: Buttons
        btn_frame = ttk.Frame(paned, padding="5")
        paned.add(btn_frame, weight=0)
        
        ttk.Button(btn_frame, text="Stage >>", command=self.stage_selected).pack(pady=(50, 5))
        ttk.Button(btn_frame, text="<< Unstage", command=self.unstage_selected).pack(pady=5)
        ttk.Button(btn_frame, text="Stage All", command=self.stage_all).pack(pady=(20, 5))
        
        # Right: Staged
        staged_frame = ttk.LabelFrame(paned, text="Staged Changes (Will Commit)", padding="5")
        paned.add(staged_frame, weight=1)
        
        self.staged_list = tk.Listbox(staged_frame, selectmode=tk.EXTENDED, width=40)
        self.staged_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_staged = ttk.Scrollbar(staged_frame, orient="vertical", command=self.staged_list.yview)
        sb_staged.pack(side=tk.RIGHT, fill=tk.Y)
        self.staged_list.config(yscrollcommand=sb_staged.set)
        
        # 3. Commit Message
        msg_frame = ttk.LabelFrame(self.main_frame, text="3. Commit Message", padding="10")
        msg_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Toolbar
        toolbar = ttk.Frame(msg_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        self.generate_btn = ttk.Button(toolbar, text="✨ Generate Message", command=self.generate_message_threaded)
        self.generate_btn.pack(side=tk.LEFT)
        
        self.commit_btn = ttk.Button(toolbar, text="Commit", command=self.commit)
        self.commit_btn.pack(side=tk.RIGHT)
        
        ttk.Button(toolbar, text="Copy", command=self.copy_to_clipboard).pack(side=tk.RIGHT, padx=5)
        
        self.msg_text = scrolledtext.ScrolledText(msg_frame, height=8, wrap=tk.WORD)
        self.msg_text.pack(fill=tk.BOTH, expand=True)
        
        # Log
        self.log_label = ttk.Label(self.main_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.log_label.pack(fill=tk.X, pady=(5, 0))

    def log(self, msg):
        self.log_label.config(text=msg)
        self.parent.update_idletasks()

    def _run_git(self, args, check=True):
        if not self.repo_path.get():
            return ""
        try:
            # Hide console window on Windows
            import sys
            creation_flags = 0
            if sys.platform == 'win32':
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run(
                ["git"] + args, 
                cwd=self.repo_path.get(), 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='ignore',
                creationflags=creation_flags
            )
            if check and result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
            return result.stdout.strip()
        except Exception as e:
            self.log(f"Git Error: {e}")
            return ""

    def create_branch_dialog(self):
        if not self.repo_path.get():
            return messagebox.showwarning("Warning", "Please select a repository first.")
            
        dialog = tk.Toplevel(self.parent)
        dialog.title("Create New Branch")
        dialog.geometry("450x450")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # --- Branch Name Section ---
        name_frame = ttk.Frame(dialog)
        name_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(name_frame, text="New Branch Name:").pack(anchor=tk.W)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=name_var, width=45)
        name_entry.pack(fill=tk.X, expand=True)

        # AI Generation
        ai_frame = ttk.Frame(name_frame)
        ai_frame.pack(fill=tk.X, pady=(5,0))

        prefix_var = tk.StringVar(value="feature/")
        ttk.Label(ai_frame, text="Prefix:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Entry(ai_frame, textvariable=prefix_var, width=15).pack(side=tk.LEFT)

        self.ai_branch_btn = ttk.Button(ai_frame, text="✨ Generate with AI",
                                        command=lambda: self.generate_branch_name_threaded(name_var, prefix_var.get()))
        self.ai_branch_btn.pack(side=tk.RIGHT)
        
        # --- Source Section ---
        from_origin_var = tk.BooleanVar()
        origin_frame = ttk.LabelFrame(dialog, text="Source (Optional)", padding=10)
        origin_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Defined here for lambda closure
        combo = ttk.Combobox(origin_frame, state=tk.DISABLED, width=35)
        status_lbl = ttk.Label(origin_frame, text="", font=("", 8), foreground="gray")
        
        chk = ttk.Checkbutton(origin_frame, text="Checkout from Origin", variable=from_origin_var, 
                              command=lambda: self._toggle_origin_combo(combo, from_origin_var, status_lbl))
        chk.pack(anchor=tk.W)
        
        lbl = ttk.Label(origin_frame, text="Select Remote Branch:")
        lbl.pack(anchor=tk.W, pady=(5, 0))

        # Add a filter entry
        filter_var = tk.StringVar()
        filter_entry = ttk.Entry(origin_frame, textvariable=filter_var, width=35)
        filter_entry.pack(pady=5)
        filter_entry.bind("<KeyRelease>", lambda e: self._filter_remote_branches(combo, filter_var.get()))

        combo.pack(pady=5)
        status_lbl.pack()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Create", 
                   command=lambda: self._create_branch_action(dialog, name_var.get(), from_origin_var.get(), combo.get())).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT)

    def generate_branch_name_threaded(self, name_var, prefix):
        if not self.gemini_client.api_key:
            return messagebox.showerror("Error", "Gemini API Key not configured.")
        if self.staged_list.size() == 0:
            return messagebox.showwarning("Warning", "Stage files to generate a branch name.")

        self.ai_branch_btn.config(state=tk.DISABLED, text="Generating...")
        threading.Thread(target=self._generate_branch_name_worker, args=(name_var, prefix), daemon=True).start()

    def _generate_branch_name_worker(self, name_var, prefix):
        try:
            diff = self._run_git(["diff", "--cached"])
            if not diff:
                self.parent.after(0, lambda: messagebox.showinfo("Info", "No staged changes to analyze."))
                return

            branch_name = self.gemini_client.generate_branch_name(diff, prefix)
            self.parent.after(0, lambda: name_var.set(branch_name))
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Error", f"Failed to generate branch name:\n{e}"))
        finally:
            self.parent.after(0, lambda: self.ai_branch_btn.config(state=tk.NORMAL, text="✨ Generate with AI"))

    def _toggle_origin_combo(self, combo, var, status_lbl):
        if var.get():
            combo.config(state="readonly")
            status_lbl.config(text="Fetching origin branches...")
            self.parent.update_idletasks()
            threading.Thread(target=self._fetch_remote_branches_worker, args=(combo, status_lbl), daemon=True).start()
        else:
            combo.config(state=tk.DISABLED)
            status_lbl.config(text="")
            
    def _fetch_remote_branches_worker(self, combo, status_lbl):
        try:
            self._run_git(["fetch", "origin"])
            out = self._run_git(["branch", "-r"])
            branches = []
            for line in out.splitlines():
                line = line.strip()
                if "->" in line: continue
                if line.startswith("origin/"):
                    branches.append(line.replace("origin/", "", 1))
            
            self.all_remote_branches = sorted(branches)

            def update_ui():
                combo['values'] = self.all_remote_branches
                status_lbl.config(text=f"Found {len(self.all_remote_branches)} remote branches.")
                if self.all_remote_branches:
                    combo.current(0)
            self.parent.after(0, update_ui)
        except Exception as e:
            def show_err():
                status_lbl.config(text="Error fetching branches (Check network/remote)")
            self.parent.after(0, show_err)

    def _filter_remote_branches(self, combo, filter_text):
        if not hasattr(self, 'all_remote_branches'):
            return

        filtered_list = [b for b in self.all_remote_branches if filter_text.lower() in b.lower()]
        current_val = combo.get()
        combo['values'] = filtered_list
        if current_val in filtered_list:
            combo.set(current_val)
        elif filtered_list:
            combo.set(filtered_list[0])
        else:
            combo.set('')

    def _create_branch_action(self, dialog, name, from_origin, remote_branch):
        if not name:
            return messagebox.showerror("Error", "Branch name required.")
        if " " in name:
             return messagebox.showwarning("Warning", "Branch names cannot contain spaces.")
        
        args = ["checkout", "-b", name]
        if from_origin:
            if not remote_branch:
                return messagebox.showerror("Error", "Please select a remote branch.")
            args.append(f"origin/{remote_branch}")
            
        try:
            out = self._run_git(args)
            if "Switched to a new branch" in out or "Switched to branch" in out or not out: 
                # Git output varies, sometimes stderr has the message.
                # If _run_git didn't raise, it's mostly success.
                pass
            
            messagebox.showinfo("Success", f"Branch '{name}' created!\n\n{out}")
            dialog.destroy()
            self.refresh_status()
        except Exception as e:
            # Subprocess.CalledProcessError
            if hasattr(e, 'stderr') and e.stderr:
                 messagebox.showerror("Error", f"Failed to create branch:\n{e.stderr}")
            else:
                 messagebox.showerror("Error", f"Failed to create branch:\n{e}")

    def browse_repository(self):
        path = filedialog.askdirectory()
        if path and os.path.isdir(os.path.join(path, '.git')):
            self.repo_path.set(path)
            self.refresh_status()
        elif path:
            messagebox.showerror("Error", "Not a valid Git repository.")

    def refresh_status(self):
        if not self.repo_path.get():
            return
            
        # Get branch
        branch = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        self.current_branch.set(branch)
        
        # Get status
        status_out = self._run_git(["status", "--porcelain"])
        
        self.unstaged_list.delete(0, tk.END)
        self.staged_list.delete(0, tk.END)
        
        for line in status_out.splitlines():
            if not line: continue
            code = line[:2]
            path = line[3:]
            
            # X (index), Y (worktree)
            index_status = code[0]
            worktree_status = code[1]
            
            # If index has something (M, A, D, R, C), it's staged
            if index_status in "MADRC":
                self.staged_list.insert(tk.END, path)
            
            # If worktree has something (M, D, ?) or index is empty but worktree has something
            if worktree_status in "MD?" or (index_status == '?' and worktree_status == '?'):
                self.unstaged_list.insert(tk.END, path)
                
        self.log(f"Status refreshed for {branch}")

    def stage_selected(self):
        selection = self.unstaged_list.curselection()
        if not selection: return
        
        files = [self.unstaged_list.get(i) for i in selection]
        self._run_git(["add"] + files)
        self.refresh_status()

    def stage_all(self):
        self._run_git(["add", "."])
        self.refresh_status()

    def unstage_selected(self):
        selection = self.staged_list.curselection()
        if not selection: return
        
        files = [self.staged_list.get(i) for i in selection]
        self._run_git(["restore", "--staged"] + files)
        self.refresh_status()

    def generate_message_threaded(self):
        if not self.gemini_client.api_key:
            return messagebox.showerror("Error", "Gemini API Key not configured.")
        
        # Check if anything is staged
        if self.staged_list.size() == 0:
            return messagebox.showwarning("Warning", "Stage some files first!")
            
        self.generate_btn.config(state=tk.DISABLED, text="Generating...")
        threading.Thread(target=self._generate_worker, daemon=True).start()

    def _generate_worker(self):
        try:
            diff = self._run_git(["diff", "--cached"])
            if not diff:
                self.log("No diff found in staged changes.")
                return
                
            msg = self.gemini_client.generate_commit_message(diff)
            
            self.parent.after(0, self._update_msg_area, msg)
        except Exception as e:
            self.log(f"Error generating: {e}")
        finally:
            self.parent.after(0, lambda: self.generate_btn.config(state=tk.NORMAL, text="✨ Generate Message"))

    def _update_msg_area(self, msg):
        self.msg_text.delete("1.0", tk.END)
        self.msg_text.insert("1.0", msg)
        self.log("Message generated.")

    def copy_to_clipboard(self):
        text = self.msg_text.get("1.0", tk.END).strip()
        if text:
            self.parent.clipboard_clear()
            self.parent.clipboard_append(text)
            self.log("Copied to clipboard.")

    def commit(self):
        msg = self.msg_text.get("1.0", tk.END).strip()
        if not msg:
            return messagebox.showwarning("Warning", "Commit message is empty.")
            
        if messagebox.askyesno("Confirm", "Proceed with commit?"):
            out = self._run_git(["commit", "-m", msg])
            messagebox.showinfo("Result", out)
            self.msg_text.delete("1.0", tk.END)
            self.refresh_status()
