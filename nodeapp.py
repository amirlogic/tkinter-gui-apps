import os
import json
import subprocess
import threading
import sys
import platform
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class NodeManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Node App Task Manager")
        self.root.geometry("650x570")
        self.root.minsize(550, 450)

        self.current_dir = ""
        self.package_manager = "npm"
        self.scripts = {}
        self.active_process = None  # Reference to track the current running process

        self.create_widgets()

    def create_widgets(self):
        # Top Frame - Directory Selector
        dir_frame = ttk.LabelFrame(self.root, text="Repository Directory", padding=10)
        dir_frame.pack(fill="x", padx=10, pady=5)

        self.dir_entry = ttk.Entry(dir_frame)
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_browse = ttk.Button(dir_frame, text="Browse...", command=self.browse_directory)
        btn_browse.pack(side="right")

        # Info Frame - Manager & Shell
        info_frame = ttk.Frame(self.root, padding=(10, 5))
        info_frame.pack(fill="x", padx=10)

        # Detected Package Manager Indicator
        self.pm_label = ttk.Label(info_frame, text="Package Manager: Undetected", font=("Segoe UI", 9, "bold"))
        self.pm_label.pack(side="left")

        # Windows Shell Selector
        if platform.system() == "Windows":
            shell_frame = ttk.Frame(info_frame)
            shell_frame.pack(side="right")
            
            ttk.Label(shell_frame, text="Shell: ").pack(side="left")
            self.shell_var = tk.StringVar(value="powershell")
            shell_combo = ttk.Combobox(
                shell_frame, 
                textvariable=self.shell_var, 
                values=["powershell", "cmd"], 
                state="readonly", 
                width=12
            )
            shell_combo.pack(side="right")
        else:
            self.shell_var = None

        # Main Content Frame
        main_frame = ttk.LabelFrame(self.root, text="Scripts & Actions", padding=10)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Action bar (Install, Run, Stop buttons)
        actions_frame = ttk.Frame(main_frame)
        actions_frame.pack(fill="x", pady=(0, 5))

        self.btn_install = ttk.Button(
            actions_frame, 
            text="Install Dependencies", 
            command=self.run_install, 
            state="disabled"
        )
        self.btn_install.pack(side="left", padx=(0, 5))

        self.btn_run = ttk.Button(
            actions_frame, 
            text="Run Selected Script", 
            command=self.run_script, 
            state="disabled"
        )
        self.btn_run.pack(side="left", padx=(0, 5))

        self.btn_stop = ttk.Button(
            actions_frame, 
            text="Stop Execution", 
            command=self.stop_command, 
            state="disabled"
        )
        self.btn_stop.pack(side="left")

        # Listbox for package.json scripts
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill="both", expand=True, pady=5)

        self.script_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.script_listbox.yview)
        self.script_listbox.config(yscrollcommand=scrollbar.set)

        self.script_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Output Terminal Frame
        output_frame = ttk.LabelFrame(self.root, text="Console Output", padding=10)
        output_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.output_text = tk.Text(output_frame, height=8, wrap="word", bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9))
        output_scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        self.output_text.config(yscrollcommand=output_scrollbar.set)

        self.output_text.pack(side="left", fill="both", expand=True)
        output_scrollbar.pack(side="right", fill="y")

    def browse_directory(self):
        selected_dir = filedialog.askdirectory()
        if selected_dir:
            self.current_dir = selected_dir
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, selected_dir)
            self.load_repository_info()

    def detect_package_manager(self):
        """Detects package manager based on lockfiles, defaulting to npm."""
        pnpm_lock = os.path.exists(os.path.join(self.current_dir, "pnpm-lock.yaml"))
        yarn_lock = os.path.exists(os.path.join(self.current_dir, "yarn.lock"))
        bun_lock = os.path.exists(os.path.join(self.current_dir, "bun.lockb")) or os.path.exists(os.path.join(self.current_dir, "bun.lock"))
        
        if pnpm_lock:
            return "pnpm"
        elif yarn_lock:
            return "yarn"
        elif bun_lock:
            return "bun"
        return "npm"

    def load_repository_info(self):
        self.script_listbox.delete(0, tk.END)
        self.output_text.delete("1.0", tk.END)
        self.scripts = {}

        pkg_path = os.path.join(self.current_dir, "package.json")
        if not os.path.exists(pkg_path):
            messagebox.showerror("Error", "No package.json found in the selected folder.")
            self.pm_label.config(text="Package Manager: N/A")
            self.btn_install.config(state="disabled")
            self.btn_run.config(state="disabled")
            self.btn_stop.config(state="disabled")
            return

        # 1. Detect Package Manager
        self.package_manager = self.detect_package_manager()
        self.pm_label.config(text=f"Package Manager: {self.package_manager}")

        # 2. Parse package.json scripts
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.scripts = data.get("scripts", {})
                for script_name, cmd in self.scripts.items():
                    self.script_listbox.insert(tk.END, f"{script_name}  -->  {cmd}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse package.json:\n{str(e)}")
            return

        # Enable/Disable Install Button based on node_modules presence
        node_modules_path = os.path.join(self.current_dir, "node_modules")
        if not os.path.exists(node_modules_path):
            self.btn_install.config(state="normal")
            self.log_output("Notice: 'node_modules' directory is missing. Click 'Install Dependencies' to set up.\n")
        else:
            self.btn_install.config(state="normal")

        if self.scripts:
            self.btn_run.config(state="normal")

    def run_install(self):
        cmd = f"{self.package_manager} install"
        self.execute_command(cmd)

    def run_script(self):
        selection = self.script_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a script to run.")
            return

        script_key = list(self.scripts.keys())[selection[0]]
        
        # Build command depending on the package manager
        if self.package_manager in ["npm", "pnpm"]:
            cmd = f"{self.package_manager} run {script_key}"
        else:
            cmd = f"{self.package_manager} {script_key}"

        self.execute_command(cmd)

    def stop_command(self):
        if self.active_process and self.active_process.poll() is None:
            self.log_output("\n> Stopping process...\n")
            try:
                if platform.system() == "Windows":
                    # Kills process tree (/T) forcefully (/F) by PID on Windows
                    subprocess.run(
                        f"taskkill /F /T /PID {self.active_process.pid}",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                else:
                    self.active_process.terminate()
            except Exception as e:
                self.log_output(f"\nFailed to terminate process: {str(e)}\n")

    def set_running_state(self, is_running):
        """Toggles button states during process execution."""
        if is_running:
            self.btn_run.config(state="disabled")
            self.btn_install.config(state="disabled")
            self.btn_stop.config(state="normal")
        else:
            self.btn_run.config(state="normal" if self.scripts else "disabled")
            self.btn_install.config(state="normal")
            self.btn_stop.config(state="disabled")

    def execute_command(self, full_cmd):
        self.output_text.delete("1.0", tk.END)
        self.log_output(f"> Executing: {full_cmd}\n\n")

        # Format execution string based on OS and user-selected Windows shell
        if platform.system() == "Windows":
            selected_shell = self.shell_var.get() if self.shell_var else "powershell"
            if selected_shell == "powershell":
                args = f'powershell.exe -Command "{full_cmd}"'
            else:
                args = f'cmd.exe /c "{full_cmd}"'
        else:
            args = full_cmd

        self.set_running_state(is_running=True)

        def worker():
            try:
                self.active_process = subprocess.Popen(
                    args,
                    cwd=self.current_dir,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                for line in iter(self.active_process.stdout.readline, ''):
                    self.root.after(0, self.log_output, line)

                self.active_process.stdout.close()
                self.active_process.wait()
                
                exit_code = self.active_process.returncode
                self.root.after(0, self.log_output, f"\n[Process exited with code {exit_code}]\n")
            except Exception as e:
                self.root.after(0, self.log_output, f"\nExecution failed: {str(e)}\n")
            finally:
                self.active_process = None
                self.root.after(0, self.set_running_state, False)

        threading.Thread(target=worker, daemon=True).start()

    def log_output(self, text):
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = NodeManagerApp(root)
    root.mainloop()