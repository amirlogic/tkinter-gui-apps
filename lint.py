import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class PylintGUIApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Pylint GUI Dashboard")
        self.geometry("800x650")
        self.minsize(650, 500)

        # Threading queue for safe GUI updates
        self.output_queue = queue.Queue()

        # Layout configuration
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Variables
        self.target_path_var = tk.StringVar()
        self.extra_args_var = tk.StringVar()

        # Checkbox variables
        self.opt_reports = tk.BooleanVar(value=False)
        self.opt_score = tk.BooleanVar(value=True)
        self.opt_errors_only = tk.BooleanVar(value=False)
        self.opt_verbose = tk.BooleanVar(value=False)

        # Disable specific categories
        self.dis_convention = tk.BooleanVar(value=False)
        self.dis_refactor = tk.BooleanVar(value=False)
        self.dis_warning = tk.BooleanVar(value=False)

        self._build_ui()
        # Start checking queue for thread messages
        self.after(100, self._process_queue)

    def _build_ui(self):
        # 1. Target Selection Frame
        file_frame = ttk.LabelFrame(self, text=" Target Selection ", padding=10)
        file_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        file_frame.columnconfigure(0, weight=1)

        target_entry = ttk.Entry(file_frame, textvariable=self.target_path_var)
        target_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        ttk.Button(
            file_frame, text="Browse File", command=self._browse_file
        ).grid(row=0, column=1, padx=2)
        ttk.Button(
            file_frame, text="Browse Folder", command=self._browse_dir
        ).grid(row=0, column=2, padx=2)

        # 2. Options Frame
        options_frame = ttk.LabelFrame(self, text=" Pylint Options ", padding=10)
        options_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        ttk.Checkbutton(
            options_frame, text="Show Score (--score)", variable=self.opt_score
        ).grid(row=0, column=0, sticky="w", padx=10, pady=2)
        ttk.Checkbutton(
            options_frame,
            text="Full Report (--reports=y)",
            variable=self.opt_reports,
        ).grid(row=1, column=0, sticky="w", padx=10, pady=2)
        ttk.Checkbutton(
            options_frame,
            text="Errors Only (--errors-only)",
            variable=self.opt_errors_only,
        ).grid(row=2, column=0, sticky="w", padx=10, pady=2)
        ttk.Checkbutton(
            options_frame, text="Verbose (--verbose)", variable=self.opt_verbose
        ).grid(row=3, column=0, sticky="w", padx=10, pady=2)

        sep = ttk.Separator(options_frame, orient="vertical")
        sep.grid(row=0, column=1, rowspan=4, sticky="ns", padx=15)

        ttk.Label(options_frame, text="Disable Categories:").grid(
            row=0, column=2, sticky="w", padx=10
        )
        ttk.Checkbutton(
            options_frame, text="Convention (C)", variable=self.dis_convention
        ).grid(row=1, column=2, sticky="w", padx=10, pady=2)
        ttk.Checkbutton(
            options_frame, text="Refactor (R)", variable=self.dis_refactor
        ).grid(row=2, column=2, sticky="w", padx=10, pady=2)
        ttk.Checkbutton(
            options_frame, text="Warning (W)", variable=self.dis_warning
        ).grid(row=3, column=2, sticky="w", padx=10, pady=2)

        extra_frame = ttk.Frame(options_frame)
        extra_frame.grid(
            row=4, column=0, columnspan=3, sticky="ew", pady=(10, 0)
        )
        extra_frame.columnconfigure(1, weight=1)

        ttk.Label(extra_frame, text="Extra Flags:").grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        ttk.Entry(extra_frame, textvariable=self.extra_args_var).grid(
            row=0, column=1, sticky="ew"
        )

        # 3. Output & Controls Frame
        output_frame = ttk.LabelFrame(self, text=" Output Results ", padding=10)
        output_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output_text = tk.Text(
            output_frame, wrap="word", font=("Consolas", 10)
        )
        self.output_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            output_frame, orient="vertical", command=self.output_text.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.output_text.config(yscrollcommand=scrollbar.set)

        btn_bar = ttk.Frame(self, padding=5)
        btn_bar.grid(row=3, column=0, sticky="ew", padx=10)

        self.btn_run = ttk.Button(
            btn_bar, text="Run Pylint", command=self._start_pylint_thread
        )
        self.btn_run.pack(side="right", padx=5)

        ttk.Button(
            btn_bar, text="Clear Output", command=self._clear_output
        ).pack(side="right", padx=5)

    def _browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select Python File",
            filetypes=[("Python Files", "*.py"), ("All Files", "*.*")],
        )
        if filename:
            self.target_path_var.set(filename)

    def _browse_dir(self):
        directory = filedialog.askdirectory(title="Select Folder")
        if directory:
            self.target_path_var.set(directory)

    def _clear_output(self):
        self.output_text.delete("1.0", tk.END)

    def _build_pylint_command(self):
        target = self.target_path_var.get().strip()
        if not target:
            return None

        cmd = [sys.executable, "-m", "pylint"]
        cmd.append(f"--score={'y' if self.opt_score.get() else 'n'}")
        cmd.append(f"--reports={'y' if self.opt_reports.get() else 'n'}")

        if self.opt_errors_only.get():
            cmd.append("--errors-only")
        if self.opt_verbose.get():
            cmd.append("--verbose")

        disabled_list = []
        if self.dis_convention.get():
            disabled_list.append("C")
        if self.dis_refactor.get():
            disabled_list.append("R")
        if self.dis_warning.get():
            disabled_list.append("W")

        if disabled_list:
            cmd.append(f"--disable={','.join(disabled_list)}")

        extra_args = self.extra_args_var.get().strip()
        if extra_args:
            cmd.extend(extra_args.split())

        cmd.append(target)
        return cmd

    def _start_pylint_thread(self):
        target = self.target_path_var.get().strip()
        if not target:
            messagebox.showwarning(
                "Missing Input",
                "Please select a file or directory to lint first.",
            )
            return

        cmd = self._build_pylint_command()

        self._clear_output()
        self.output_text.insert(
            tk.END, f"Running Command:\n{' '.join(cmd)}\n"
        )
        self.output_text.insert(
            tk.END, "=" * 60 + "\n[ Running... Please wait ]\n\n"
        )

        # Disable button while running
        self.btn_run.config(state="disabled")

        # Run subprocess in a separate thread
        threading.Thread(
            target=self._run_pylint_worker, args=(cmd,), daemon=True
        ).start()

    def _run_pylint_worker(self, cmd):
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            for line in process.stdout:
                self.output_queue.put(("OUTPUT", line))

            process.wait()
            self.output_queue.put(
                ("DONE", f"\n[ Finished with exit code {process.returncode} ]\n")
            )

        except Exception as e:
            self.output_queue.put(
                ("ERROR", f"Failed to execute Pylint: {str(e)}\n")
            )

    def _process_queue(self):
        """Poll the queue periodically to safely update Tkinter widgets from main thread."""
        try:
            while True:
                msg_type, content = self.output_queue.get_nowait()
                if msg_type in ("OUTPUT", "ERROR", "DONE"):
                    self.output_text.insert(tk.END, content)
                    self.output_text.see(tk.END)

                if msg_type in ("DONE", "ERROR"):
                    self.btn_run.config(state="normal")
        except queue.Empty:
            pass

        self.after(100, self._process_queue)


if __name__ == "__main__":
    app = PylintGUIApp()
    app.mainloop()