import os
import json
import subprocess
import platform
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

class MonorepoManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Electron Monorepo Manager (pnpm)")
        self.root.geometry("850x550")
        self.root.minsize(700, 450)

        self.root_dir = tk.StringVar()
        self.apps_data = {}  # Map app name -> {path, pkg_name, scripts}
        
        self.create_widgets()

    def create_widgets(self):
        # --- Top Frame: Root Directory Selection ---
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(top_frame, text="Monorepo Root:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.dir_entry = ttk.Entry(top_frame, textvariable=self.root_dir, width=65)
        self.dir_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        browse_btn = ttk.Button(top_frame, text="Browse...", command=self.browse_directory)
        browse_btn.pack(side=tk.LEFT, padx=5)

        load_btn = ttk.Button(top_frame, text="Load Apps", command=self.load_apps)
        load_btn.pack(side=tk.LEFT, padx=5)

        # --- Middle Frame: Two Columns (Apps & Scripts) ---
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left Column: Apps List
        left_frame = ttk.LabelFrame(main_frame, text="Apps (/apps)", padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.apps_listbox = tk.Listbox(left_frame, exportselection=False)
        self.apps_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.apps_listbox.bind("<<ListboxSelect>>", self.on_app_select)

        apps_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.apps_listbox.yview)
        apps_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.apps_listbox.configure(yscrollcommand=apps_scrollbar.set)

        # Right Column: Scripts List
        right_frame = ttk.LabelFrame(main_frame, text="Available Scripts (package.json)", padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.scripts_listbox = tk.Listbox(right_frame, exportselection=False)
        self.scripts_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scripts_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.scripts_listbox.yview)
        scripts_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.scripts_listbox.configure(yscrollcommand=scripts_scrollbar.set)

        # --- Bottom Frame: Controls & Shell Selector ---
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)

        # Shell Selector (Windows only primarily, but kept available)
        ttk.Label(bottom_frame, text="Shell:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.shell_var = tk.StringVar(value="powershell" if platform.system() == "Windows" else "default")
        shell_options = ["powershell", "cmd"] if platform.system() == "Windows" else ["default"]
        
        self.shell_combo = ttk.Combobox(bottom_frame, textvariable=self.shell_var, values=shell_options, state="readonly", width=12)
        self.shell_combo.pack(side=tk.LEFT, padx=5)

        # Run Script Button
        run_btn = ttk.Button(bottom_frame, text="Run Script in External Shell", command=self.run_script)
        run_btn.pack(side=tk.RIGHT, padx=5)

    def browse_directory(self):
        dir_path = filedialog.askdirectory(title="Select Monorepo Root Directory")
        if dir_path:
            self.root_dir.set(dir_path)
            self.load_apps()

    def load_apps(self):
        root_path = self.root_dir.get().strip()
        if not root_path or not os.path.isdir(root_path):
            messagebox.showerror("Error", "Please select a valid monorepo root directory.")
            return

        apps_path = Path(root_path) / "apps"
        if not apps_path.is_dir():
            messagebox.showwarning("Warning", "No 'apps' directory found inside the selected root path.")
            return

        self.apps_data.clear()
        self.apps_listbox.delete(0, tk.END)
        self.scripts_listbox.delete(0, tk.END)

        # Scan /apps directory for subdirectories containing a package.json
        try:
            for item in sorted(apps_path.iterdir()):
                if item.is_dir():
                    pkg_json_path = item / "package.json"
                    if pkg_json_path.exists():
                        try:
                            with open(pkg_json_path, "r", encoding="utf-8") as f:
                                pkg_data = json.load(f)
                                pkg_name = pkg_data.get("name", item.name)
                                scripts = pkg_data.get("scripts", {})
                                
                                self.apps_data[item.name] = {
                                    "path": item,
                                    "pkg_name": pkg_name,
                                    "scripts": scripts
                                }
                                self.apps_listbox.insert(tk.END, item.name)
                        except Exception as e:
                            print(f"Error parsing {pkg_json_path}: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load apps: {e}")

        if not self.apps_data:
            messagebox.showinfo("Info", "No valid apps with package.json found in /apps.")

    def on_app_select(self, event):
        selection = self.apps_listbox.curselection()
        if not selection:
            return
        
        app_name = self.apps_listbox.get(selection[0])
        self.scripts_listbox.delete(0, tk.END)

        app_info = self.apps_data.get(app_name)
        if app_info and app_info["scripts"]:
            for script_name in sorted(app_info["scripts"].keys()):
                self.scripts_listbox.insert(tk.END, script_name)

    def run_script(self):
        root_path = self.root_dir.get().strip()
        app_selection = self.apps_listbox.curselection()
        script_selection = self.scripts_listbox.curselection()

        if not app_selection:
            messagebox.showwarning("Warning", "Please select an app.")
            return
        if not script_selection:
            messagebox.showwarning("Warning", "Please select a script to run.")
            return

        app_name = self.apps_listbox.get(app_selection[0])
        script_name = self.scripts_listbox.get(script_selection[0])
        app_info = self.apps_data.get(app_name)
        
        pkg_name = app_info["pkg_name"]
        
        # Construct pnpm filter command
        pnpm_cmd = f"pnpm --filter {pkg_name} run {script_name}"

        system = platform.system()
        shell_choice = self.shell_var.get()

        try:
            if system == "Windows":
                if shell_choice == "cmd":
                    # Open new cmd window, change directory, and run command
                    full_cmd = f'start cmd.exe /k "cd /d "{root_path}" && {pnpm_cmd}"'
                    subprocess.Popen(full_cmd, shell=True)
                else:
                    # Open new powershell window, set location, and run command
                    full_cmd = f'start powershell -NoExit -Command "Set-Location \'{root_path}\'; {pnpm_cmd}"'
                    subprocess.Popen(full_cmd, shell=True)
            elif system == "Darwin":  # macOS
                apple_script = f'''
                tell application "Terminal"
                    activate
                    do script "cd '{root_path}' && {pnpm_cmd}"
                end tell
                '''
                subprocess.Popen(["osascript", "-e", apple_script])
            else:  # Linux
                # Tries common terminal emulators
                for term in ["gnome-terminal", "konsole", "xterm"]:
                    if subprocess.call(["which", term], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                        if term == "gnome-terminal":
                            subprocess.Popen([term, "--", "bash", "-c", f"cd '{root_path}' && {pnpm_cmd}; exec bash"])
                        elif term == "konsole":
                            subprocess.Popen([term, "-e", "bash", "-c", f"cd '{root_path}' && {pnpm_cmd}; exec bash"])
                        elif term == "xterm":
                            subprocess.Popen([term, "-e", f"cd '{root_path}' && {pnpm_cmd}; exec bash"])
                        break
                else:
                    messagebox.showerror("Error", "No supported Linux terminal emulator found (gnome-terminal, konsole, xterm).")
        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to start external shell: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MonorepoManagerApp(root)
    root.mainloop()