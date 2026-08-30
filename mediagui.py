import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import os
import re
from pathlib import Path
import threading
import shutil


class MediaWebGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MediaGui v0.5")
        self.geometry("1100x600")

        style = ttk.Style()
        style.theme_use('clam')

        self.filepath_var = tk.StringVar()
        self.filename_var = tk.StringVar()
        self.workdir_var  = tk.StringVar()

        self.create_header()
        self.create_tabs()
        self.create_console()
        self.check_dependencies()

    # ------------------------------------------------------------------
    # Dependencies
    # ------------------------------------------------------------------
    def check_dependencies(self):
        missing = []
        if not shutil.which("ffmpeg"):
            missing.append("FFmpeg")
        if not shutil.which("magick"):
            missing.append("ImageMagick")
        if missing:
            self.log(f"WARNING: Not found in PATH: {', '.join(missing)}. Install them or operations will fail.")
        else:
            self.log("System Check: FFmpeg and ImageMagick found.")

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    def create_header(self):
        frame = ttk.LabelFrame(self, text="File Selection", padding=4)
        frame.pack(fill="x", padx=8, pady=(4, 2))

        ttk.Button(frame, text="Select File", command=self.browse_file).pack(side="left", padx=4)
        ttk.Label(frame, textvariable=self.filepath_var, relief="sunken", anchor="w").pack(
            side="left", fill="x", expand=True, padx=4)

    def browse_file(self):
        fpath = filedialog.askopenfilename()
        if fpath:
            fpath = os.path.normpath(fpath)
            self.filepath_var.set(fpath)
            p = Path(fpath)
            self.filename_var.set(p.name)
            self.workdir_var.set(str(p.parent))
            self.log(f"Selected: {fpath}")

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------
    def create_tabs(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=2)

        self.tab_ffmpeg = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ffmpeg, text="FFMPEG")
        self.setup_ffmpeg_tab()

        self.tab_magick = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_magick, text="Image Magick")
        self.setup_magick_tab()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def make_time_entry(self, parent):
        """Returns a small HH/MM/SS entry (caller is responsible for packing)."""
        e = ttk.Entry(parent, width=3)
        e.insert(0, "00")
        return e

    def pack_time_row(self, parent, label, prefix):
        """Pack a labelled H:M:S trio into *parent* (side=left).
        Returns (h_entry, m_entry, s_entry)."""
        ttk.Label(parent, text=label).pack(side="left", padx=(4, 1))
        h = self.make_time_entry(parent); h.pack(side="left")
        ttk.Label(parent, text=":").pack(side="left")
        m = self.make_time_entry(parent); m.pack(side="left")
        ttk.Label(parent, text=":").pack(side="left")
        s = self.make_time_entry(parent); s.pack(side="left")
        return h, m, s

    # ------------------------------------------------------------------
    # FFmpeg tab  –  compact 2-column grid of LabelFrames
    # ------------------------------------------------------------------
    def setup_ffmpeg_tab(self):
        outer = ttk.Frame(self.tab_ffmpeg, padding=6)
        outer.pack(fill="both", expand=True)

        # Left column
        left = ttk.Frame(outer)
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))

        # Right column
        right = ttk.Frame(outer)
        right.pack(side="left", fill="both", expand=True)

        # ── Convert ──────────────────────────────────────────────────
        f_conv = ttk.LabelFrame(left, text="Convert Container", padding=4)
        f_conv.pack(fill="x", pady=2)
        ttk.Label(f_conv, text="New ext:").pack(side="left")
        self.ff_ext = ttk.Entry(f_conv, width=6)
        self.ff_ext.pack(side="left", padx=4)
        ttk.Button(f_conv, text="Go", command=self.ffmpeg_convert).pack(side="left")

        # ── Reverse ───────────────────────────────────────────────────
        f_rev = ttk.LabelFrame(left, text="Reverse", padding=4)
        f_rev.pack(fill="x", pady=2)
        ttk.Button(f_rev, text="Reverse Video + Audio", command=self.ffmpeg_reverse).pack(fill="x")

        # ── Scale ─────────────────────────────────────────────────────
        f_scale = ttk.LabelFrame(left, text="📐 Scale", padding=4)
        f_scale.pack(fill="x", pady=2)

        self.scale_mode = tk.StringVar(value="res")
        modes = [("Res (w:h)", "res"), ("Height (-2:h)", "asrth"),
                 ("Width (w:-2)", "asrtw"), ("Factor (*n or /n)", "factor")]
        self.scale_mode_map = {m[0]: m[1] for m in modes}

        ttk.Combobox(f_scale, textvariable=self.scale_mode,
                     values=[m[0] for m in modes], state="readonly", width=16).pack(side="left", padx=(0,4))
        self.scale_val = ttk.Entry(f_scale, width=8)
        self.scale_val.insert(0, "w:h")
        self.scale_val.pack(side="left", padx=4)
        ttk.Button(f_scale, text="Scale", command=self.ffmpeg_scale).pack(side="left")

        # ── Speed ─────────────────────────────────────────────────────
        f_speed = ttk.LabelFrame(left, text="🕓 Speed", padding=4)
        f_speed.pack(fill="x", pady=2)
        ttk.Label(f_speed, text="Multiplier:").pack(side="left")
        self.speed_val = ttk.Entry(f_speed, width=6)
        self.speed_val.insert(0, "1.0")
        self.speed_val.pack(side="left", padx=4)
        ttk.Button(f_speed, text="Set Speed", command=self.ffmpeg_speed).pack(side="left")

        # ── Framerate ─────────────────────────────────────────────────
        f_fps = ttk.LabelFrame(left, text="🎞️ Framerate", padding=4)
        f_fps.pack(fill="x", pady=2)
        ttk.Label(f_fps, text="FPS:").pack(side="left")
        self.fps_val = ttk.Entry(f_fps, width=6)
        self.fps_val.insert(0, "24")
        self.fps_val.pack(side="left", padx=4)
        ttk.Button(f_fps, text="Change FPS", command=self.ffmpeg_framerate).pack(side="left")

        # ── Split / Cut ───────────────────────────────────────────────
        f_cut = ttk.LabelFrame(right, text="✂️ Split", padding=4)
        f_cut.pack(fill="x", pady=2)

        row_from = ttk.Frame(f_cut); row_from.pack(fill="x", pady=1)
        self.cut_f_h, self.cut_f_m, self.cut_f_s = self.pack_time_row(row_from, "From:", "f")

        row_to = ttk.Frame(f_cut); row_to.pack(fill="x", pady=1)
        self.cut_t_h, self.cut_t_m, self.cut_t_s = self.pack_time_row(row_to, "  To:", "t")

        ttk.Button(f_cut, text="Cut", command=self.ffmpeg_cut).pack(pady=3)

        # ── Screenshot ────────────────────────────────────────────────
        f_ss = ttk.LabelFrame(right, text="📷 Screenshot", padding=4)
        f_ss.pack(fill="x", pady=2)

        row_ss = ttk.Frame(f_ss); row_ss.pack(fill="x", pady=1)
        self.ss_h, self.ss_m, self.ss_s = self.pack_time_row(row_ss, "At:", "ss")
        ttk.Label(row_ss, text="Frames:").pack(side="left", padx=(10, 2))
        self.ss_frames = ttk.Entry(row_ss, width=3)
        self.ss_frames.insert(0, "1")
        self.ss_frames.pack(side="left")

        ttk.Button(f_ss, text="Capture", command=self.ffmpeg_screenshot).pack(pady=3)

    # ------------------------------------------------------------------
    # ImageMagick tab
    # ------------------------------------------------------------------
    def setup_magick_tab(self):
        container = ttk.Frame(self.tab_magick, padding=6)
        container.pack(fill="both", expand=True)

        # Quick buttons
        r1 = ttk.Frame(container)
        r1.pack(fill="x", pady=2)
        ttk.Button(r1, text="Check Version",    command=self.magick_version).pack(side="left", padx=4)
        ttk.Button(r1, text="Identify Metadata",command=self.magick_metadata).pack(side="left", padx=4)

        # Modification form
        f_mod = ttk.LabelFrame(container, text="Modify Image", padding=6)
        f_mod.pack(fill="x", pady=4)

        ttk.Label(f_mod, text="Convert to (ext):").grid(row=0, column=0, sticky="e", pady=3)
        self.mg_convert = ttk.Entry(f_mod)
        self.mg_convert.grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(f_mod, text="Resize (WxH or %):").grid(row=1, column=0, sticky="e", pady=3)
        self.mg_resize = ttk.Entry(f_mod)
        self.mg_resize.grid(row=1, column=1, sticky="w", padx=5)

        ttk.Label(f_mod, text="Presets:").grid(row=2, column=0, sticky="e", pady=3)
        self.mg_preset = ttk.Combobox(f_mod, values=["", "Transparency"], state="readonly")
        self.mg_preset.grid(row=2, column=1, sticky="w", padx=5)
        self.mg_preset.bind("<<ComboboxSelected>>", self.on_magick_preset)

        ttk.Label(f_mod, text="Extra commands:").grid(row=3, column=0, sticky="e", pady=3)
        self.mg_xcmd = ttk.Entry(f_mod, width=50)
        self.mg_xcmd.grid(row=3, column=1, sticky="w", padx=5)

        ttk.Button(f_mod, text="Run Magick", command=self.magick_run).grid(row=4, column=1, pady=6)

    # ------------------------------------------------------------------
    # Console
    # ------------------------------------------------------------------
    def create_console(self):
        frame = ttk.LabelFrame(self, text="Console Output", padding=4)
        frame.pack(fill="both", expand=True, padx=8, pady=(2, 4))

        self.console = scrolledtext.ScrolledText(
            frame, height=8, state="disabled",
            bg="#1e1e1e", fg="#00ff00", font=("Consolas", 9))
        self.console.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def log(self, msg):
        self.console.config(state="normal")
        self.console.insert("end", str(msg) + "\n")
        self.console.see("end")
        self.console.config(state="disabled")

    def run_cmd(self, cmd):
        def thread_task():
            try:
                self.log(f"Processing...")
                self.log(f"CMD: {cmd}")
                process = subprocess.Popen(
                    cmd, shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in iter(process.stdout.readline, ""):
                    self.log(line.strip())
                rc = process.wait()
                self.log("Done!" if rc == 0 else f"Finished with error code {rc}")
            except Exception as e:
                self.log(f"CRITICAL ERROR: {e}")

        threading.Thread(target=thread_task, daemon=True).start()

    def get_file_info(self):
        f = self.filepath_var.get()
        if not f:
            self.log("ERROR: No file selected.")
            messagebox.showwarning("Missing File", "Please select a file first.")
            return None, None, None
        if not os.path.exists(f):
            self.log(f"ERROR: File not found: {f}")
            messagebox.showerror("Error", "File does not exist.")
            return None, None, None
        p = Path(f)
        return str(p), str(p.with_suffix("")), p.suffix

    # ------------------------------------------------------------------
    # FFmpeg actions
    # ------------------------------------------------------------------
    def ffmpeg_convert(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return
        nwext = self.ff_ext.get().strip().lstrip(".")
        if not nwext:
            self.log("ERROR: Extension required"); return
        self.run_cmd(f'ffmpeg -y -i "{fname}" -map 0 -c copy "{fnwx}.{nwext}"')

    def ffmpeg_reverse(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return
        # Reverse both video and audio streams
        self.run_cmd(f'ffmpeg -y -i "{fname}" -vf reverse -af areverse "{fnwx}_reversed{ext}"')

    def ffmpeg_cut(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return
        try:
            start = f"{self.cut_f_h.get()}:{self.cut_f_m.get()}:{self.cut_f_s.get()}"
            end   = f"{self.cut_t_h.get()}:{self.cut_t_m.get()}:{self.cut_t_s.get()}"
            s_sfx = "".join([self.cut_f_h.get(), self.cut_f_m.get(), self.cut_f_s.get()])
            e_sfx = "".join([self.cut_t_h.get(), self.cut_t_m.get(), self.cut_t_s.get()])
            self.run_cmd(f'ffmpeg -y -ss {start} -to {end} -i "{fname}" -c copy "{fnwx}_{s_sfx}_{e_sfx}{ext}"')
        except Exception as e:
            self.log(f"Error preparing cut command: {e}")

    def ffmpeg_screenshot(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return
        time   = f"{self.ss_h.get()}:{self.ss_m.get()}:{self.ss_s.get()}"
        frames = self.ss_frames.get().strip() or "1"
        # Use pattern output when capturing multiple frames
        out = f'"{fnwx}_screen%04d.png"' if int(frames) > 1 else f'"{fnwx}_screen.png"'
        self.run_cmd(f'ffmpeg -y -ss {time} -i "{fname}" -frames:v {frames} {out}')

    def ffmpeg_scale(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return
        scmode = self.scale_mode_map.get(self.scale_mode.get(), "res")
        scvalue = self.scale_val.get()
        if scmode == "res":      fstr = f"scale={scvalue}"
        elif scmode == "factor": fstr = f"scale=iw{scvalue}:ih{scvalue}"
        elif scmode == "asrth":  fstr = f"scale=-2:{scvalue}"
        elif scmode == "asrtw":  fstr = f"scale={scvalue}:-2"
        else:                    fstr = f"scale={scvalue}"
        clean_val = re.sub(r'[/\*:]', '', scvalue)
        self.run_cmd(f'ffmpeg -y -i "{fname}" -vf "{fstr}" "{fnwx}_{clean_val}{ext}"')

    def ffmpeg_speed(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return
        try:
            mult = float(self.speed_val.get())
        except ValueError:
            self.log("ERROR: Speed multiplier must be a number"); return

        # setpts multiplier is inverse: 2x speed → PTS*0.5
        pts_mult = round(1.0 / mult, 6)

        # atempo only accepts 0.5–2.0; chain filters for values outside range
        def atempo_chain(factor):
            filters = []
            while factor > 2.0:
                filters.append("atempo=2.0"); factor /= 2.0
            while factor < 0.5:
                filters.append("atempo=0.5"); factor /= 0.5
            filters.append(f"atempo={factor:.6f}")
            return ",".join(filters)

        vf = f"setpts={pts_mult}*PTS"
        af = atempo_chain(mult)
        self.run_cmd(f'ffmpeg -y -i "{fname}" -vf "{vf}" -af "{af}" "{fnwx}_{mult}x{ext}"')

    def ffmpeg_framerate(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return
        fps = re.sub(r'[^0-9.]', '', self.fps_val.get()) or "24"
        self.run_cmd(f'ffmpeg -y -i "{fname}" -filter:v "fps={fps}" -c:a copy "{fnwx}_fps{fps}{ext}"')

    # ------------------------------------------------------------------
    # ImageMagick actions
    # ------------------------------------------------------------------
    def magick_version(self):
        self.run_cmd("magick -version")

    def on_magick_preset(self, event):
        if self.mg_preset.get() == "Transparency":
            self.mg_xcmd.delete(0, tk.END)
            self.mg_xcmd.insert(0, "-fuzz 20% -transparent white")

    def magick_metadata(self):
        fname = self.filepath_var.get()
        if not fname:
            self.log("Error: Select a file for metadata"); return
        self.run_cmd(f'magick identify -verbose "{fname}"')

    def magick_run(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return

        convert_to = self.mg_convert.get().strip()
        resize     = self.mg_resize.get().strip()
        xcmd       = self.mg_xcmd.get().strip()

        newext = f".{convert_to}" if convert_to else ext

        # ImageMagick v7: `magick [opts] input [ops] output`  (no sub-command needed)
        parts = ["magick", f'"{fname}"']
        if resize:
            parts.append(f"-resize {resize}")
        if xcmd:
            parts.append(xcmd)

        suffix = f"_{re.sub(r'[^a-zA-Z0-9]', '', resize)}" if resize else ""
        parts.append(f'"{fnwx}{suffix}{newext}"')

        self.run_cmd(" ".join(parts))


if __name__ == "__main__":
    app = MediaWebGui()
    app.mainloop()
