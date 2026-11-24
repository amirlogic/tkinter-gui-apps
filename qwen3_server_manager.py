import json
import os
import platform
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import threading
import urllib.request
import zipfile
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk


MIN_ORT_VERSION = (1, 32, 0)
MIN_ORT_VERSION_STR = ".".join(map(str, MIN_ORT_VERSION))
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SERVER_READY_RE = re.compile(r"\bListening on https?://\S+", re.IGNORECASE)


class Qwen3ServerManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rust Qwen3 API Server Manager")
        self.geometry("920x720")
        self.minsize(820, 620)

        self.is_windows = platform.system() == "Windows"
        self.server_process = None
        self.build_process = None

        # State variables
        self.repo_dir = tk.StringVar(value=self._detect_initial_repo_dir())
        self.binary_name = tk.StringVar(value="rust-qwen3-api-server")
        self.ort_status_var = tk.StringVar(value="Not checked")
        self.ort_path_var = tk.StringVar(value="")
        self.ort_target_version = tk.StringVar(value=MIN_ORT_VERSION_STR)
        self.build_status_var = tk.StringVar(value="Not checked")
        self.exe_path_var = tk.StringVar(value="")
        self.cargo_features_var = tk.StringVar(value="")
        self.model_dir_var = tk.StringVar(value="model")
        self.server_args_var = tk.StringVar(value="")
        self.shell_choice = tk.StringVar(value="cmd" if self.is_windows else "sh")
        self.server_status_var = tk.StringVar(value="Stopped")

        self.readme_ort_notes = ""

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Initial scan
        self.after(150, self.refresh_all)

    def _detect_initial_repo_dir(self) -> str:
        cwd = Path.cwd()
        if (cwd / "Cargo.toml").exists():
            return str(cwd)
        script_dir = Path(__file__).resolve().parent
        if (script_dir / "Cargo.toml").exists():
            return str(script_dir)
        return str(cwd)

    # -------------------------------------------------------------------------
    # UI Construction
    # -------------------------------------------------------------------------
    def _build_ui(self):
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

        main_frame = ttk.Frame(self, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Repository Selection
        repo_frame = ttk.LabelFrame(main_frame, text="Repository Configuration", padding=10)
        repo_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(repo_frame, text="Repo Folder:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        ttk.Entry(repo_frame, textvariable=self.repo_dir).grid(row=0, column=1, sticky=tk.EW, padx=(0, 6))
        ttk.Button(repo_frame, text="Browse...", command=self._browse_repo).grid(row=0, column=2, padx=(0, 4))
        ttk.Button(repo_frame, text="Scan / Refresh", command=self.refresh_all).grid(row=0, column=3, padx=(0, 4))
        ttk.Button(repo_frame, text="View README ORT Info", command=self._show_readme_modal).grid(row=0, column=4)
        repo_frame.columnconfigure(1, weight=1)

        # 2. ONNX Runtime Section
        ort_frame = ttk.LabelFrame(main_frame, text="ONNX Runtime (ORT) Dependency", padding=10)
        ort_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(ort_frame, text="Status:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        self.ort_status_lbl = ttk.Label(ort_frame, textvariable=self.ort_status_var, font=("Segoe UI", 9, "bold"))
        self.ort_status_lbl.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(ort_frame, text="Target Version:").grid(row=0, column=2, sticky=tk.E, padx=(12, 4))
        ttk.Entry(ort_frame, textvariable=self.ort_target_version, width=12).grid(row=0, column=3, sticky=tk.W, padx=(0, 8))

        self.btn_install_ort = ttk.Button(
            ort_frame, text="Download & Install ORT", command=self._start_ort_install
        )
        self.btn_install_ort.grid(row=0, column=4, sticky=tk.E)

        ttk.Label(ort_frame, text="ORT Library Path:").grid(row=1, column=0, sticky=tk.W, pady=(6, 0), padx=(0, 6))
        ttk.Entry(ort_frame, textvariable=self.ort_path_var).grid(
            row=1, column=1, columnspan=3, sticky=tk.EW, pady=(6, 0), padx=(0, 8)
        )
        ttk.Button(ort_frame, text="Select Library...", command=self._browse_ort_lib).grid(
            row=1, column=4, sticky=tk.E, pady=(6, 0)
        )

        self.ort_progress = ttk.Progressbar(ort_frame, mode="determinate")
        self.ort_progress.grid(row=2, column=0, columnspan=5, sticky=tk.EW, pady=(8, 0))
        ort_frame.columnconfigure(1, weight=1)

        # 3. Build Status & Compilation Section
        build_frame = ttk.LabelFrame(main_frame, text="Rust Server Executable & Build", padding=10)
        build_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(build_frame, text="Binary Status:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        self.build_status_lbl = ttk.Label(build_frame, textvariable=self.build_status_var, font=("Segoe UI", 9, "bold"))
        self.build_status_lbl.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(build_frame, text="Cargo Features:").grid(row=0, column=2, sticky=tk.E, padx=(12, 4))
        ttk.Entry(build_frame, textvariable=self.cargo_features_var, width=22).grid(
            row=0, column=3, sticky=tk.W, padx=(0, 8)
        )

        self.btn_build = ttk.Button(
            build_frame, text="Build Release (cargo build --release)", command=self._start_cargo_build
        )
        self.btn_build.grid(row=0, column=4, sticky=tk.E)

        ttk.Label(build_frame, text="Executable Path:").grid(row=1, column=0, sticky=tk.W, pady=(6, 0), padx=(0, 6))
        ttk.Entry(build_frame, textvariable=self.exe_path_var, state="readonly").grid(
            row=1, column=1, columnspan=4, sticky=tk.EW, pady=(6, 0)
        )
        build_frame.columnconfigure(1, weight=1)

        # 4. Server Launch & Process Control
        srv_frame = ttk.LabelFrame(main_frame, text="Server Execution & Shell Controls", padding=10)
        srv_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(srv_frame, text="Model Directory:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        ttk.Entry(srv_frame, textvariable=self.model_dir_var).grid(
            row=0, column=1, columnspan=4, sticky=tk.EW, padx=(0, 8)
        )
        ttk.Button(srv_frame, text="Browse...", command=self._browse_model_dir).grid(
            row=0, column=5, sticky=tk.E
        )

        ttk.Label(srv_frame, text="CLI Arguments:").grid(row=1, column=0, sticky=tk.W, padx=(0, 6), pady=(6, 0))
        ttk.Entry(srv_frame, textvariable=self.server_args_var).grid(
            row=1, column=1, columnspan=3, sticky=tk.EW, padx=(0, 8), pady=(6, 0)
        )
        ttk.Label(srv_frame, text="State:").grid(row=1, column=4, sticky=tk.E, padx=(0, 4), pady=(6, 0))
        self.srv_status_lbl = ttk.Label(srv_frame, textvariable=self.server_status_var, font=("Segoe UI", 9, "bold"))
        self.srv_status_lbl.grid(row=1, column=5, sticky=tk.W, pady=(6, 0))

        btn_bar = ttk.Frame(srv_frame)
        btn_bar.grid(row=2, column=0, columnspan=6, sticky=tk.EW, pady=(10, 0))

        self.btn_start_inapp = ttk.Button(btn_bar, text="▶ Start Server (In-App)", command=self._start_server_inapp)
        self.btn_start_inapp.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_stop_inapp = ttk.Button(
            btn_bar, text="■ Stop Server", command=self._stop_server_inapp, state=tk.DISABLED
        )
        self.btn_stop_inapp.pack(side=tk.LEFT, padx=(0, 16))

        ttk.Separator(btn_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 16))

        self.btn_launch_ext = ttk.Button(
            btn_bar, text="↗ Launch in External Shell", command=self._launch_external_shell
        )
        self.btn_launch_ext.pack(side=tk.LEFT, padx=(0, 8))

        if self.is_windows:
            ttk.Radiobutton(btn_bar, text="CMD", variable=self.shell_choice, value="cmd").pack(side=tk.LEFT, padx=(0, 6))
            ttk.Radiobutton(btn_bar, text="PowerShell", variable=self.shell_choice, value="powershell").pack(
                side=tk.LEFT
            )
        else:
            ttk.Label(btn_bar, text=f"({platform.system()} Terminal)").pack(side=tk.LEFT)

        srv_frame.columnconfigure(1, weight=1)

        # 5. Console Output
        log_frame = ttk.LabelFrame(main_frame, text="Console Output & Logs", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(log_toolbar, text="Clear Logs", command=self._clear_logs).pack(side=tk.RIGHT)

        self.log_box = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Consolas" if self.is_windows else "Monospace", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#ffffff",
            state=tk.DISABLED,
        )
        self.log_box.pack(fill=tk.BOTH, expand=True)

    # -------------------------------------------------------------------------
    # Logging & Helpers
    # -------------------------------------------------------------------------
    def log(self, msg: str):
        def _append():
            self.log_box.configure(state=tk.NORMAL)
            self.log_box.insert(tk.END, msg + "\n")
            self.log_box.see(tk.END)
            self.log_box.configure(state=tk.DISABLED)

        self.after(0, _append)

    def _clear_logs(self):
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state=tk.DISABLED)

    def _browse_repo(self):
        selected = filedialog.askdirectory(initialdir=self.repo_dir.get(), title="Select rust-qwen3-api-server folder")
        if selected:
            self.repo_dir.set(selected)
            self.refresh_all()

    def _browse_model_dir(self):
        current_dir = Path(self.model_dir_var.get().strip())
        if not current_dir.is_absolute():
            current_dir = Path(self.repo_dir.get()) / current_dir
        initial_dir = current_dir if current_dir.is_dir() else self.repo_dir.get()
        selected = filedialog.askdirectory(initialdir=initial_dir, title="Select model directory")
        if selected:
            self.model_dir_var.set(selected)

    def _browse_ort_lib(self):
        if self.is_windows:
            filetypes = [("ONNX Runtime DLL", "onnxruntime.dll"), ("All DLLs", "*.dll"), ("All files", "*.*")]
        elif platform.system() == "Darwin":
            filetypes = [("ONNX Runtime Dylib", "libonnxruntime*.dylib"), ("All files", "*.*")]
        else:
            filetypes = [("ONNX Runtime Shared Lib", "libonnxruntime*.so*"), ("All files", "*.*")]

        selected = filedialog.askopenfilename(initialdir=self.repo_dir.get(), title="Select ONNX Runtime Library", filetypes=filetypes)
        if selected:
            self.ort_path_var.set(selected)
            self.check_onnxruntime()

    def _show_readme_modal(self):
        win = tk.Toplevel(self)
        win.title("README.md — ONNX Runtime Instructions")
        win.geometry("680x440")
        txt = scrolledtext.ScrolledText(win, wrap=tk.WORD, font=("Consolas" if self.is_windows else "Monospace", 9))
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        txt.insert(tk.END, self.readme_ort_notes or "No README.md found in the selected repository directory.")
        txt.configure(state=tk.DISABLED)

    # -------------------------------------------------------------------------
    # Repository, README, ORT & Build Detection
    # -------------------------------------------------------------------------
    def refresh_all(self):
        repo = Path(self.repo_dir.get())
        if not repo.exists():
            self.log(f"[WARN] Directory does not exist: {repo}")
            return

        self._parse_cargo_toml(repo)
        self._parse_readme(repo)
        self.check_onnxruntime()
        self.check_executable_built()

    def _parse_cargo_toml(self, repo: Path):
        cargo_file = repo / "Cargo.toml"
        if not cargo_file.exists():
            self.log("[WARN] Cargo.toml not found in selected directory.")
            return
        try:
            content = cargo_file.read_text(encoding="utf-8", errors="ignore")
            # Match package name under [package]
            pkg_match = re.search(r'\[package\][\s\S]*?name\s*=\s*"([^"]+)"', content)
            if pkg_match:
                self.binary_name.set(pkg_match.group(1))
                self.log(f"[INFO] Detected Cargo package binary: {self.binary_name.get()}")
        except Exception as exc:
            self.log(f"[ERROR] Failed to parse Cargo.toml: {exc}")

    def _parse_readme(self, repo: Path):
        readme_file = None
        for candidate in ("README.md", "readme.md", "Readme.md"):
            if (repo / candidate).exists():
                readme_file = repo / candidate
                break

        if not readme_file:
            self.readme_ort_notes = "README.md not found in repository."
            return

        try:
            text = readme_file.read_text(encoding="utf-8", errors="ignore")
            # Extract lines/sections mentioning onnx or ort
            lines = text.splitlines()
            relevant = []
            capture = False
            for line in lines:
                if line.startswith("#"):
                    capture = bool(re.search(r"onnx|ort|install|setup|prerequisite|require", line, re.I))
                if capture or re.search(r"onnx|ort_dylib|1\.\d+\.\d+", line, re.I):
                    relevant.append(line)

            self.readme_ort_notes = "\n".join(relevant).strip() or text[:3000]

            # Look for an ONNX Runtime version, including releases newer than 1.29.
            ver_match = re.search(r"onnxruntime[^\d]{0,25}(1\.\d+\.\d+)", text, re.I)
            if not ver_match:
                ver_match = re.search(r"\bv?(1\.\d+\.\d+)\b", text)
            if ver_match:
                detected_ver = ver_match.group(1)
                if tuple(map(int, detected_ver.split("."))) >= MIN_ORT_VERSION:
                    self.ort_target_version.set(detected_ver)
                    self.log(f"[INFO] README specifies ONNX Runtime v{detected_ver}")
                else:
                    self.log(
                        f"[WARN] README specifies ONNX Runtime v{detected_ver}, below the "
                        f"minimum v{MIN_ORT_VERSION_STR}; keeping v{MIN_ORT_VERSION_STR}."
                    )
        except Exception as exc:
            self.log(f"[ERROR] Could not read README.md: {exc}")

    def _get_ort_lib_filename(self) -> str:
        sys_name = platform.system()
        if sys_name == "Windows":
            return "onnxruntime.dll"
        elif sys_name == "Darwin":
            return "libonnxruntime.dylib"
        return "libonnxruntime.so"

    def check_onnxruntime(self):
        repo = Path(self.repo_dir.get())
        lib_name = self._get_ort_lib_filename()
        candidates = []

        # 1. Explicit user path
        if self.ort_path_var.get().strip():
            candidates.append(Path(self.ort_path_var.get().strip()))

        # 2. ORT_DYLIB_PATH environment variable
        env_ort = os.environ.get("ORT_DYLIB_PATH")
        if env_ort:
            p = Path(env_ort)
            candidates.append(p / lib_name if p.is_dir() else p)

        # 3. Local repo folders (onnxruntime/, target/release/, root)
        for sub in [
            repo / lib_name,
            repo / "onnxruntime" / "lib" / lib_name,
            repo / "onnxruntime" / lib_name,
            repo / "lib" / lib_name,
            repo / "target" / "release" / lib_name,
            repo / "target" / "debug" / lib_name,
        ]:
            candidates.append(sub)

        # Also search inside any extracted onnxruntime-* subfolder in repo
        if repo.exists():
            for child in repo.glob("onnxruntime*"):
                if child.is_dir():
                    candidates.append(child / "lib" / lib_name)
                    candidates.append(child / lib_name)

        # 4. User-level ONNX Runtime archive (the documented install location)
        user_ort_dir = Path.home() / "onnxruntime"
        candidates.extend(
            [
                user_ort_dir / lib_name,
                user_ort_dir / "lib" / lib_name,
            ]
        )
        if user_ort_dir.is_dir():
            for child in user_ort_dir.glob("onnxruntime*"):
                if child.is_dir():
                    candidates.append(child / "lib" / lib_name)
                    candidates.append(child / lib_name)

        # 5. System PATH
        which_hit = shutil.which(lib_name)
        if which_hit:
            candidates.append(Path(which_hit))

        found_lib = None
        for cand in candidates:
            if cand.exists() and cand.is_file():
                found_lib = cand.resolve()
                break

        if found_lib:
            self.ort_path_var.set(str(found_lib))
            version = self._detect_ort_version(found_lib)
            ver_str = f"v{version}" if version else "version unknown"
            self.ort_status_var.set(f"Installed ({ver_str})")
            self.ort_status_lbl.configure(foreground="#1b7e3c")
            self.log(f"[OK] ONNX Runtime found ({ver_str}): {found_lib}")
        else:
            self.ort_status_var.set("Not Found (Install Required)")
            self.ort_status_lbl.configure(foreground="#c9302c")
            self.log("[WARN] ONNX Runtime library not found locally or in ORT_DYLIB_PATH.")

    def _detect_ort_version(self, lib_path: Path) -> str | None:
        # Check VERSION_NUMBER file in parent or grandparent directory (standard in ORT archives)
        for parent in [lib_path.parent, lib_path.parent.parent]:
            ver_file = parent / "VERSION_NUMBER"
            if ver_file.exists():
                try:
                    return ver_file.read_text(encoding="utf-8").strip()
                except Exception:
                    pass

        # Fallback: extract version string from parent folder name (e.g., onnxruntime-win-x64-1.20.1)
        m = re.search(r"onnxruntime-[a-z0-9-]+-(1\.\d+\.\d+)", str(lib_path), re.I)
        if m:
            return m.group(1)

        # Fallback: scan binary strings for OrtGetApiBase / version tag
        try:
            data = lib_path.read_bytes()
            m_bin = re.search(rb"1\.(?:1[5-9]|2\d)\.\d+", data)
            if m_bin:
                return m_bin.group(0).decode("ascii", errors="ignore")
        except Exception:
            pass
        return None

    def check_executable_built(self):
        repo = Path(self.repo_dir.get())
        bin_name = self.binary_name.get()
        ext = ".exe" if self.is_windows else ""

        release_exe = repo / "target" / "release" / f"{bin_name}{ext}"
        debug_exe = repo / "target" / "debug" / f"{bin_name}{ext}"

        if release_exe.exists():
            self.exe_path_var.set(str(release_exe))
            self.build_status_var.set("Built (Release)")
            self.build_status_lbl.configure(foreground="#1b7e3c")
            self._set_run_buttons_state(True)
            self.log(f"[OK] Release executable ready: {release_exe}")
        elif debug_exe.exists():
            self.exe_path_var.set(str(debug_exe))
            self.build_status_var.set("Built (Debug)")
            self.build_status_lbl.configure(foreground="#2b6cb0")
            self._set_run_buttons_state(True)
            self.log(f"[OK] Debug executable ready: {debug_exe}")
        else:
            self.exe_path_var.set("")
            self.build_status_var.set("Not Built")
            self.build_status_lbl.configure(foreground="#c9302c")
            self._set_run_buttons_state(False)
            self.log("[WARN] Server binary not found. Click 'Build Release' to compile.")

    def _set_run_buttons_state(self, ready: bool):
        state = tk.NORMAL if ready else tk.DISABLED
        if self.server_process is None:
            self.btn_start_inapp.configure(state=state)
        self.btn_launch_ext.configure(state=state)

    # -------------------------------------------------------------------------
    # ONNX Runtime Download & Install
    # -------------------------------------------------------------------------
    def _get_ort_download_info(self, version: str) -> tuple[str, str]:
        sys_name = platform.system()
        arch = platform.machine().lower()

        if sys_name == "Windows":
            arch_tag = "arm64" if "arm" in arch else "x64"
            filename = f"onnxruntime-win-{arch_tag}-{version}.zip"
        elif sys_name == "Darwin":
            arch_tag = "arm64" if ("arm" in arch or "aarch64" in arch) else "x86_64"
            filename = f"onnxruntime-osx-{arch_tag}-{version}.tgz"
        else:
            arch_tag = "aarch64" if ("arm" in arch or "aarch64" in arch) else "x64"
            filename = f"onnxruntime-linux-{arch_tag}-{version}.tgz"

        url = f"https://github.com/microsoft/onnxruntime/releases/download/v{version}/{filename}"
        return url, filename

    def _start_ort_install(self):
        version = self.ort_target_version.get().strip().lstrip("v")
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            messagebox.showerror(
                "Invalid Version", f"Please enter a valid semantic version (e.g., {MIN_ORT_VERSION_STR})."
            )
            return

        if tuple(map(int, version.split("."))) < MIN_ORT_VERSION:
            messagebox.showerror(
                "Version Below Minimum",
                f"ONNX Runtime v{MIN_ORT_VERSION_STR} or newer is required.",
            )
            return

        self.btn_install_ort.configure(state=tk.DISABLED)
        self.ort_progress["value"] = 0
        threading.Thread(target=self._install_ort_worker, args=(version,), daemon=True).start()

    def _install_ort_worker(self, version: str):
        repo = Path(self.repo_dir.get())
        install_dir = repo / "onnxruntime"
        install_dir.mkdir(parents=True, exist_ok=True)

        url, filename = self._get_ort_download_info(version)
        archive_path = install_dir / filename

        self.log(f"[ORT] Downloading ONNX Runtime v{version} from:\n      {url}")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 65536
                with open(archive_path, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = (downloaded / total_size) * 100
                            self.after(0, lambda p=pct: self.ort_progress.configure(value=p))

            self.log(f"[ORT] Download complete ({archive_path.name}). Extracting...")

            if filename.endswith(".zip"):
                with zipfile.ZipFile(archive_path, "r") as zf:
                    zf.extractall(install_dir)
            else:
                with tarfile.open(archive_path, "r:gz") as tf:
                    tf.extractall(install_dir)

            # Locate extracted library and copy/link to clean location
            lib_name = self._get_ort_lib_filename()
            extracted_libs = list(install_dir.rglob(lib_name))
            if extracted_libs:
                target_lib = extracted_libs[0].resolve()
                self.after(0, lambda p=str(target_lib): self.ort_path_var.set(p))
                self.log(f"[ORT] Successfully installed to: {target_lib}")
            else:
                self.log("[WARN] Archive extracted, but library file was not automatically located.")

            archive_path.unlink(missing_ok=True)
            self.after(0, self.check_onnxruntime)

        except Exception as exc:
            self.log(f"[ERROR] ONNX Runtime installation failed: {exc}")
            self.after(
                0,
                lambda: messagebox.showerror(
                    "ORT Download Failed",
                    f"Could not download ONNX Runtime v{version}.\n\nError: {exc}\n\n"
                    "Verify the version number in README.md or check your internet connection.",
                ),
            )
        finally:
            self.after(0, lambda: self.btn_install_ort.configure(state=tk.NORMAL))

    # -------------------------------------------------------------------------
    # Cargo Build Execution
    # -------------------------------------------------------------------------
    def _build_env(self) -> dict:
        env = os.environ.copy()
        ort_lib = self.ort_path_var.get().strip()
        if ort_lib and Path(ort_lib).exists():
            env["ORT_DYLIB_PATH"] = ort_lib
            lib_dir = str(Path(ort_lib).parent)
            if self.is_windows:
                env["PATH"] = f"{lib_dir};{env.get('PATH', '')}"
            else:
                env["LD_LIBRARY_PATH"] = f"{lib_dir}:{env.get('LD_LIBRARY_PATH', '')}"
                env["DYLD_LIBRARY_PATH"] = f"{lib_dir}:{env.get('DYLD_LIBRARY_PATH', '')}"
        return env

    def _start_cargo_build(self):
        if not shutil.which("cargo"):
            messagebox.showerror("Cargo Not Found", "Rust 'cargo' toolchain was not found in your system PATH.")
            return

        repo = Path(self.repo_dir.get())
        if not (repo / "Cargo.toml").exists():
            messagebox.showerror("Invalid Repository", "No Cargo.toml found in the selected repository folder.")
            return

        self.btn_build.configure(state=tk.DISABLED)
        self.build_status_var.set("Building...")
        self.build_status_lbl.configure(foreground="#d97706")

        cmd = ["cargo", "build", "--release"]
        features = self.cargo_features_var.get().strip()
        if features:
            cmd.extend(["--features", features])

        self.log(f"\n[BUILD] Running: {' '.join(cmd)}")
        threading.Thread(target=self._cargo_build_worker, args=(cmd, repo), daemon=True).start()

    def _cargo_build_worker(self, cmd: list[str], cwd: Path):
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if self.is_windows else 0
            self.build_process = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                env=self._build_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )

            assert self.build_process.stdout is not None
            for line in self.build_process.stdout:
                self.log(line.rstrip())

            rc = self.build_process.wait()
            if rc == 0:
                self.log("[BUILD] Compilation succeeded!")
            else:
                self.log(f"[BUILD] Compilation failed with exit code {rc}.")
        except Exception as exc:
            self.log(f"[ERROR] Build process error: {exc}")
        finally:
            self.build_process = None
            self.after(0, lambda: self.btn_build.configure(state=tk.NORMAL))
            self.after(0, self.check_executable_built)

    # -------------------------------------------------------------------------
    # Server Launch (In-App & External Shell)
    # -------------------------------------------------------------------------
    def _prepare_server_cmd(self) -> tuple[list[str], Path] | None:
        exe_str = self.exe_path_var.get().strip()
        if not exe_str or not Path(exe_str).exists():
            messagebox.showwarning("Executable Missing", "Please build the server executable first.")
            return None

        repo = Path(self.repo_dir.get())
        cmd = [exe_str]
        model_dir = self.model_dir_var.get().strip()
        if not model_dir:
            messagebox.showwarning("Model Directory Missing", "Please select a model directory.")
            return None
        cmd.extend(["--model-dir", model_dir])

        extra_args = self.server_args_var.get().strip()
        if extra_args:
            cmd.extend(extra_args.split())
        return cmd, repo

    def _start_server_inapp(self):
        if self.server_process is not None:
            return

        prepared = self._prepare_server_cmd()
        if not prepared:
            return
        cmd, cwd = prepared

        self.log(f"\n[SERVER] Starting in-app: {' '.join(cmd)}")
        if self.ort_path_var.get():
            self.log(f"[SERVER] ORT_DYLIB_PATH={self.ort_path_var.get()}")

        try:
            creationflags = subprocess.CREATE_NO_WINDOW if self.is_windows else 0
            self.server_process = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                env=self._build_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
            self.server_status_var.set(f"Starting (PID {self.server_process.pid})")
            self.srv_status_lbl.configure(foreground="#b7791f")
            self.btn_start_inapp.configure(state=tk.DISABLED)
            self.btn_stop_inapp.configure(state=tk.NORMAL)

            threading.Thread(target=self._read_server_output, daemon=True).start()
        except Exception as exc:
            self.server_process = None
            self.log(f"[ERROR] Failed to start server: {exc}")

    def _read_server_output(self):
        proc = self.server_process
        if not proc or not proc.stdout:
            return
        try:
            ready_reported = False
            for line in proc.stdout:
                clean_line = ANSI_ESCAPE_RE.sub("", line).rstrip()
                self.log(clean_line)
                if not ready_reported and SERVER_READY_RE.search(clean_line):
                    ready_reported = True
                    self.after(0, self._mark_server_running, proc.pid)
            rc = proc.wait()
            self.log(f"[SERVER] Process exited with code {rc}.")
        except Exception as exc:
            self.log(f"[SERVER] Output stream ended: {exc}")
        finally:
            self.server_process = None
            self.after(0, self._reset_server_ui_stopped)

    def _mark_server_running(self, pid: int):
        if self.server_process is None or self.server_process.pid != pid:
            return
        self.server_status_var.set(f"Running (PID {pid})")
        self.srv_status_lbl.configure(foreground="#1b7e3c")

    def _reset_server_ui_stopped(self):
        self.server_status_var.set("Stopped")
        self.srv_status_lbl.configure(foreground="#c9302c")
        self.btn_stop_inapp.configure(state=tk.DISABLED)
        if self.exe_path_var.get() and Path(self.exe_path_var.get()).exists():
            self.btn_start_inapp.configure(state=tk.NORMAL)

    def _stop_server_inapp(self):
        if not self.server_process:
            return
        pid = self.server_process.pid
        self.log(f"[SERVER] Stopping server (PID {pid})...")
        try:
            if self.is_windows:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                self.server_process.send_signal(signal.SIGTERM)
                self.server_process.wait(timeout=5)
        except Exception:
            try:
                self.server_process.kill()
            except Exception:
                pass
        finally:
            self.server_process = None
            self._reset_server_ui_stopped()

    def _launch_external_shell(self):
        prepared = self._prepare_server_cmd()
        if not prepared:
            return
        cmd, cwd = prepared
        env = self._build_env()
        ort_lib = self.ort_path_var.get().strip()
        full_run = subprocess.list2cmdline(cmd) if self.is_windows else shlex.join(cmd)

        if self.is_windows:
            shell = self.shell_choice.get()
            if shell == "powershell":
                ps_commands = []
                if ort_lib:
                    ps_commands.append(f'$env:ORT_DYLIB_PATH = "{ort_lib}"')
                    ps_commands.append(f'$env:PATH = "{Path(ort_lib).parent};" + $env:PATH')
                ps_commands.append(f"& {full_run}")
                ps_script = "; ".join(ps_commands)
                subprocess.Popen(
                    ["powershell.exe", "-NoExit", "-Command", ps_script],
                    cwd=str(cwd),
                    env=env,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                self.log("[SERVER] Launched in external PowerShell window.")
            else:
                cmd_parts = []
                if ort_lib:
                    cmd_parts.append(f'set "ORT_DYLIB_PATH={ort_lib}"')
                    cmd_parts.append(f'set "PATH={Path(ort_lib).parent};%PATH%"')
                cmd_parts.append(full_run)
                cmd_line = " && ".join(cmd_parts)
                subprocess.Popen(
                    ["cmd.exe", "/k", cmd_line],
                    cwd=str(cwd),
                    env=env,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                self.log("[SERVER] Launched in external CMD window.")
        elif platform.system() == "Darwin":
            shell_command = (
                f"cd {shlex.quote(str(cwd))} && "
                f"ORT_DYLIB_PATH={shlex.quote(ort_lib)} {full_run}"
            )
            applescript_command = shell_command.replace("\\", "\\\\").replace('"', '\\"')
            script = f'tell application "Terminal" to do script "{applescript_command}"'
            subprocess.Popen(["osascript", "-e", script])
            self.log("[SERVER] Launched in macOS Terminal.")
        else:
            for term in ("x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal", "xterm"):
                if shutil.which(term):
                    bash_cmd = (
                        f"cd {shlex.quote(str(cwd))} && "
                        f"ORT_DYLIB_PATH={shlex.quote(ort_lib)} {full_run}; exec bash"
                    )
                    if term == "gnome-terminal":
                        subprocess.Popen([term, "--", "bash", "-c", bash_cmd], env=env)
                    else:
                        subprocess.Popen([term, "-e", f"bash -c {shlex.quote(bash_cmd)}"], env=env)
                    self.log(f"[SERVER] Launched in external terminal ({term}).")
                    return
            messagebox.showerror("No Terminal Found", "Could not detect a supported Linux terminal emulator.")

    def _on_close(self):
        if self.server_process is not None:
            if messagebox.askyesno("Server Running", "The server is still running in-app. Stop it and exit?"):
                self._stop_server_inapp()
            else:
                return
        self.destroy()


if __name__ == "__main__":
    app = Qwen3ServerManager()
    app.mainloop()