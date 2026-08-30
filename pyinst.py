import os
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class PyInstallerGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("PyInstaller GUI Helper")
        # Wider and shorter window dimensions
        self.geometry("960x520")
        self.minsize(800, 480)

        self.script_path = tk.StringVar()
        self.icon_path = tk.StringVar()
        self.onefile_var = tk.BooleanVar(value=True)
        self.windowed_var = tk.BooleanVar(value=True)
        self.clean_var = tk.BooleanVar(value=True)
        self.use_conda_var = tk.BooleanVar(value=False)
        self.conda_env_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()

        self._create_widgets()
        self._populate_conda_envs()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Main Split: Left Column (Controls) and Right Column (Logs)
        content_paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        content_paned.pack(fill=tk.BOTH, expand=True)

        # --- LEFT COLUMN: Configuration Controls ---
        left_frame = ttk.Frame(content_paned)
        content_paned.add(left_frame, weight=1)

        # Section 1: File Selection
        files_frame = ttk.LabelFrame(left_frame, text=" File Selection ", padding="8")
        files_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(files_frame, text="Python Script (.py):").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(files_frame, textvariable=self.script_path, width=30).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(files_frame, text="Browse...", command=self._browse_script).grid(row=0, column=2, pady=2)

        ttk.Label(files_frame, text="Icon (.ico/.icns):").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(files_frame, textvariable=self.icon_path, width=30).grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(files_frame, text="Browse...", command=self._browse_icon).grid(row=1, column=2, pady=2)

        ttk.Label(files_frame, text="Output Directory:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(files_frame, textvariable=self.output_dir_var, width=30).grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(files_frame, text="Browse...", command=self._browse_output_dir).grid(row=2, column=2, pady=2)

        files_frame.columnconfigure(1, weight=1)

        # Section 2: PyInstaller Options
        opts_frame = ttk.LabelFrame(left_frame, text=" PyInstaller Options ", padding="8")
        opts_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Checkbutton(opts_frame, text="One File (--onefile)", variable=self.onefile_var).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Checkbutton(opts_frame, text="Windowed / No Console (--windowed)", variable=self.windowed_var).grid(row=0, column=1, sticky="w", padx=5, pady=2)
        ttk.Checkbutton(opts_frame, text="Clean Cache Before Build (--clean)", variable=self.clean_var).grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=2)

        # Section 3: Conda Environment Setup
        conda_frame = ttk.LabelFrame(left_frame, text=" Environment Options ", padding="8")
        conda_frame.pack(fill=tk.X, pady=(0, 8))

        self.conda_chk = ttk.Checkbutton(
            conda_frame, 
            text="Run inside Conda Env", 
            variable=self.use_conda_var,
            command=self._toggle_conda
        )
        self.conda_chk.grid(row=0, column=0, sticky="w", pady=2)

        ttk.Label(conda_frame, text="Env Name:").grid(row=0, column=1, padx=(10, 5), sticky="w")
        self.conda_combo = ttk.Combobox(conda_frame, textvariable=self.conda_env_var, state="disabled", width=15)
        self.conda_combo.grid(row=0, column=2, sticky="ew", pady=2)
        conda_frame.columnconfigure(2, weight=1)

        # Build Button at bottom of Left Column
        self.build_btn = ttk.Button(left_frame, text="Build Executable", command=self._start_build_thread)
        self.build_btn.pack(fill=tk.X, ipady=4, pady=(5, 0))

        # --- RIGHT COLUMN: Execution Logs ---
        right_frame = ttk.Frame(content_paned)
        content_paned.add(right_frame, weight=2)

        log_frame = ttk.LabelFrame(right_frame, text=" Output Log ", padding="8")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9), width=40)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

    # --- Helper Dialogs ---
    def _browse_script(self):
        filename = filedialog.askopenfilename(filetypes=[("Python Files", "*.py"), ("All Files", "*.*")])
        if filename:
            self.script_path.set(filename)
            if not self.output_dir_var.get():
                self.output_dir_var.set(os.path.dirname(filename))

    def _browse_icon(self):
        filename = filedialog.askopenfilename(filetypes=[("Icon Files", "*.ico *.icns"), ("All Files", "*.*")])
        if filename:
            self.icon_path.set(filename)

    def _browse_output_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_var.set(directory)

    def _toggle_conda(self):
        if self.use_conda_var.get():
            self.conda_combo.config(state="readonly")
        else:
            self.conda_combo.config(state="disabled")

    def _log(self, text):
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)

    # --- Conda Discovery ---
    def _populate_conda_envs(self):
        """Find installed conda environments by running `conda env list`."""
        if not shutil.which("conda"):
            self.conda_chk.config(state="disabled")
            return

        try:
            output = subprocess.check_output(["conda", "env", "list"], text=True)
            envs = []
            for line in output.splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 1:
                    envs.append(parts[0])
            
            if envs:
                self.conda_combo["values"] = envs
                self.conda_combo.current(0)
        except Exception:
            self.conda_chk.config(state="disabled")

    # --- Command Construction ---
    def _build_command(self):
        script = self.script_path.get().strip()
        if not script or not os.path.isfile(script):
            messagebox.showerror("Error", "Please select a valid .py source file.")
            return None

        pyinstaller_args = ["pyinstaller"]

        if self.onefile_var.get():
            pyinstaller_args.append("--onefile")
        else:
            pyinstaller_args.append("--onedir")

        if self.windowed_var.get():
            pyinstaller_args.append("--windowed")

        if self.clean_var.get():
            pyinstaller_args.append("--clean")

        icon = self.icon_path.get().strip()
        if icon:
            if os.path.isfile(icon):
                pyinstaller_args.extend(["--icon", icon])
            else:
                messagebox.showwarning("Warning", "Icon path given is invalid. Skipping icon flag.")

        out_dir = self.output_dir_var.get().strip()
        if out_dir:
            pyinstaller_args.extend(["--distpath", os.path.join(out_dir, "dist")])
            pyinstaller_args.extend(["--workpath", os.path.join(out_dir, "build")])

        pyinstaller_args.append(script)

        if self.use_conda_var.get():
            env_name = self.conda_env_var.get().strip()
            if not env_name:
                messagebox.showerror("Error", "Please select a Conda environment.")
                return None
            cmd = ["conda", "run", "-n", env_name, "--no-capture-output"] + pyinstaller_args
        else:
            cmd = pyinstaller_args

        return cmd

    # --- Build Execution ---
    def _start_build_thread(self):
        cmd = self._build_command()
        if not cmd:
            return

        self.build_btn.config(state="disabled")
        self.log_text.delete("1.0", tk.END)
        self._log(f"Running command:\n{' '.join(cmd)}\n\n" + "="*50 + "\n")

        threading.Thread(target=self._run_process, args=(cmd,), daemon=True).start()

    def _run_process(self, cmd):
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            for line in iter(process.stdout.readline, ""):
                self.after(0, self._log, line)

            process.stdout.close()
            return_code = process.wait()

            if return_code == 0:
                self.after(0, self._log, "\n>>> Build Completed Successfully! <<<\n")
            else:
                self.after(0, self._log, f"\n>>> Build Failed with return code {return_code} <<<\n")

        except Exception as e:
            self.after(0, self._log, f"\nError executing process: {str(e)}\n")

        finally:
            self.after(0, lambda: self.build_btn.config(state="normal"))


if __name__ == "__main__":
    app = PyInstallerGUI()
    app.mainloop()