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
        self.title("MediaGui v0.4")
        self.geometry("850x750")
        
        # Styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Variables
        self.filepath_var = tk.StringVar()
        self.filename_var = tk.StringVar()
        self.workdir_var = tk.StringVar()

        # Main Layout
        self.create_header()
        self.create_tabs()
        self.create_console()
        
        # Check dependencies on launch
        self.check_dependencies()

    def check_dependencies(self):
        """Checks if ffmpeg and magick are in PATH"""
        missing = []
        if not shutil.which("ffmpeg"):
            missing.append("FFmpeg")
        if not shutil.which("magick"):
            missing.append("ImageMagick")
        
        if missing:
            self.log(f"WARNING: The following tools were not found in PATH: {', '.join(missing)}")
            self.log("Please install them or operations will fail.")
        else:
            self.log("System Check: FFmpeg and ImageMagick found.")

    def create_header(self):
        frame = ttk.LabelFrame(self, text="File Selection", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        # File Chooser
        btn_browse = ttk.Button(frame, text="Select File", command=self.browse_file)
        btn_browse.pack(side="left", padx=5)

        lbl_file = ttk.Label(frame, textvariable=self.filepath_var, relief="sunken", anchor="w")
        lbl_file.pack(side="left", fill="x", expand=True, padx=5)

    def browse_file(self):
        fpath = filedialog.askopenfilename()
        if fpath:
            # Normalize path for Windows consistency
            fpath = os.path.normpath(fpath)
            self.filepath_var.set(fpath)
            p = Path(fpath)
            self.filename_var.set(p.name)
            self.workdir_var.set(p.parent)
            self.log(f"Selected: {fpath}")

    def create_tabs(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # FFmpeg Tab
        self.tab_ffmpeg = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ffmpeg, text="FFMPEG")
        self.setup_ffmpeg_tab()

        # Magick Tab
        self.tab_magick = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_magick, text="Image Magick")
        self.setup_magick_tab()

    def create_time_entry(self, parent):
        """Creates and PACKS a small entry box for time inputs"""
        e = ttk.Entry(parent, width=3)
        e.insert(0, "00")
        # FIXED: Added pack here so they actually show up
        e.pack(side="left", padx=2) 
        return e

    def setup_ffmpeg_tab(self):
        container = ttk.Frame(self.tab_ffmpeg, padding=10)
        container.pack(fill="both", expand=True)

        # Row 1: Convert & Reverse
        r1 = ttk.Frame(container)
        r1.pack(fill="x", pady=5)
        
        # Convert
        f_conv = ttk.LabelFrame(r1, text="Convert Container", padding=5)
        f_conv.pack(side="left", fill="both", expand=True, padx=5)
        ttk.Label(f_conv, text="New Ext:").pack(side="left")
        self.ff_ext = ttk.Entry(f_conv, width=5)
        self.ff_ext.pack(side="left", padx=5)
        ttk.Button(f_conv, text="Go", command=self.ffmpeg_convert).pack(side="left")

        # Reverse
        f_rev = ttk.LabelFrame(r1, text="Reverse", padding=5)
        f_rev.pack(side="left", fill="both", expand=True, padx=5)
        ttk.Button(f_rev, text="Reverse Video", command=self.ffmpeg_reverse).pack(fill="x")

        # Row 2: Split
        r2 = ttk.LabelFrame(container, text="✂️ Split", padding=5)
        r2.pack(fill="x", pady=5, padx=5)
        
        f_split_inputs = ttk.Frame(r2)
        f_split_inputs.pack()
        
        ttk.Label(f_split_inputs, text="From:").pack(side="left")
        self.cut_f_h = self.create_time_entry(f_split_inputs)
        ttk.Label(f_split_inputs, text=":").pack(side="left")
        self.cut_f_m = self.create_time_entry(f_split_inputs)
        ttk.Label(f_split_inputs, text=":").pack(side="left")
        self.cut_f_s = self.create_time_entry(f_split_inputs)

        ttk.Label(f_split_inputs, text="  To:").pack(side="left", padx=(20, 0))
        self.cut_t_h = self.create_time_entry(f_split_inputs)
        ttk.Label(f_split_inputs, text=":").pack(side="left")
        self.cut_t_m = self.create_time_entry(f_split_inputs)
        ttk.Label(f_split_inputs, text=":").pack(side="left")
        self.cut_t_s = self.create_time_entry(f_split_inputs)

        ttk.Button(r2, text="Cut", command=self.ffmpeg_cut).pack(pady=5)

        # Row 3: Screenshot
        r3 = ttk.LabelFrame(container, text="📷 Screenshot", padding=5)
        r3.pack(fill="x", pady=5, padx=5)
        
        f_ss = ttk.Frame(r3)
        f_ss.pack()
        
        ttk.Label(f_ss, text="At Time:").pack(side="left")
        self.ss_h = self.create_time_entry(f_ss)
        ttk.Label(f_ss, text=":").pack(side="left")
        self.ss_m = self.create_time_entry(f_ss)
        ttk.Label(f_ss, text=":").pack(side="left")
        self.ss_s = self.create_time_entry(f_ss)
        
        ttk.Label(f_ss, text="# Frames:").pack(side="left", padx=(10,5))
        self.ss_frames = ttk.Entry(f_ss, width=3)
        self.ss_frames.insert(0, "1")
        self.ss_frames.pack(side="left")
        
        ttk.Button(r3, text="Capture", command=self.ffmpeg_screenshot).pack(pady=5)

        # Row 4: Scale & Speed
        r4 = ttk.Frame(container)
        r4.pack(fill="x", pady=5)

        # Scale
        f_scale = ttk.LabelFrame(r4, text="📐 Change Scale", padding=5)
        f_scale.pack(side="left", fill="both", expand=True, padx=5)
        
        self.scale_mode = tk.StringVar(value="res")
        modes = [("Res (w:h)", "res"), ("Height (-2:h)", "asrth"), ("Width (w:-2)", "asrtw"), ("Factor (*n or /n)", "factor")]
        
        cb = ttk.Combobox(f_scale, textvariable=self.scale_mode, values=[m[0] for m in modes], state="readonly", width=15)
        cb.pack(pady=2)
        # Map nice names back to codes
        self.scale_mode_map = {m[0]: m[1] for m in modes}
        
        self.scale_val = ttk.Entry(f_scale, width=10)
        self.scale_val.insert(0, "w:h")
        self.scale_val.pack(pady=2)
        ttk.Button(f_scale, text="Scale", command=self.ffmpeg_scale).pack(pady=2)

        # Speed
        f_speed = ttk.LabelFrame(r4, text="🕓 Speed", padding=5)
        f_speed.pack(side="left", fill="both", expand=True, padx=5)
        
        ttk.Label(f_speed, text="Multiplier:").pack()
        self.speed_val = ttk.Entry(f_speed, width=5)
        self.speed_val.insert(0, "1")
        self.speed_val.pack(pady=2)
        ttk.Button(f_speed, text="Set Speed", command=self.ffmpeg_speed).pack(pady=2)

        # Row 5: Framerate
        r5 = ttk.LabelFrame(container, text="🎞️ Framerate", padding=5)
        r5.pack(fill="x", pady=5, padx=5)
        
        f_fps = ttk.Frame(r5)
        f_fps.pack()
        ttk.Label(f_fps, text="FPS:").pack(side="left")
        self.fps_val = ttk.Entry(f_fps, width=5)
        self.fps_val.insert(0, "24")
        self.fps_val.pack(side="left", padx=5)
        ttk.Button(r5, text="Change FPS", command=self.ffmpeg_framerate).pack(pady=2)

    def setup_magick_tab(self):
        container = ttk.Frame(self.tab_magick, padding=10)
        container.pack(fill="both", expand=True)

        # Buttons
        r1 = ttk.Frame(container)
        r1.pack(fill="x", pady=5)
        ttk.Button(r1, text="Check Version", command=self.magick_version).pack(side="left", padx=5)
        ttk.Button(r1, text="Identify Metadata", command=self.magick_metadata).pack(side="left", padx=5)

        # Modification Form
        f_mod = ttk.LabelFrame(container, text="Modify Image", padding=10)
        f_mod.pack(fill="x", pady=10)

        # Convert
        ttk.Label(f_mod, text="Convert to (ext):").grid(row=0, column=0, sticky="e", pady=5)
        self.mg_convert = ttk.Entry(f_mod)
        self.mg_convert.grid(row=0, column=1, sticky="w", padx=5)

        # Resize
        ttk.Label(f_mod, text="Resize (WxH or %):").grid(row=1, column=0, sticky="e", pady=5)
        self.mg_resize = ttk.Entry(f_mod)
        self.mg_resize.grid(row=1, column=1, sticky="w", padx=5)

        # Preset cmds
        ttk.Label(f_mod, text="Presets:").grid(row=2, column=0, sticky="e", pady=5)
        self.mg_preset = ttk.Combobox(f_mod, values=["", "Transparency"], state="readonly")
        self.mg_preset.grid(row=2, column=1, sticky="w", padx=5)
        self.mg_preset.bind("<<ComboboxSelected>>", self.on_magick_preset)

        # Extra Cmds
        ttk.Label(f_mod, text="Extra commands:").grid(row=3, column=0, sticky="e", pady=5)
        self.mg_xcmd = ttk.Entry(f_mod, width=50)
        self.mg_xcmd.grid(row=3, column=1, sticky="w", padx=5)

        # Submit
        ttk.Button(f_mod, text="Run Magick", command=self.magick_run).grid(row=4, column=1, pady=10)

    def create_console(self):
        frame = ttk.LabelFrame(self, text="Console Output", padding=5)
        frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.console = scrolledtext.ScrolledText(frame, height=10, state="disabled", bg="#1e1e1e", fg="#00ff00", font=("Consolas", 9))
        self.console.pack(fill="both", expand=True)

    # --- Helpers ---
    def log(self, msg):
        self.console.config(state="normal")
        self.console.insert("end", str(msg) + "\n")
        self.console.see("end")
        self.console.config(state="disabled")

    def run_cmd(self, cmd):
        """Runs command in a thread"""
        def thread_task():
            try:
                # Log usage immediately inside thread to confirm it started
                self.log(f"Processing...")
                self.log(f"CMD: {cmd}")
                
                # subprocess.PIPE can buffer. text=True handles decoding.
                process = subprocess.Popen(
                    cmd, 
                    shell=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True
                )
                
                # Read line by line
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        self.log(line.strip())
                        
                rc = process.poll()
                if rc == 0:
                    self.log("Done!")
                else:
                    self.log(f"Finished with error code {rc}")
                    
            except Exception as e:
                self.log(f"CRITICAL ERROR: {e}")

        # Start the thread
        t = threading.Thread(target=thread_task, daemon=True)
        t.start()

    def get_file_info(self):
        f = self.filepath_var.get()
        if not f:
            self.log("ERROR: No file selected. Please select a file first.")
            messagebox.showwarning("Missing File", "Please select a file first.")
            return None, None, None
            
        if not os.path.exists(f):
            self.log(f"ERROR: File not found: {f}")
            messagebox.showerror("Error", "File does not exist.")
            return None, None, None
            
        path_obj = Path(f)
        return str(path_obj), str(path_obj.with_suffix('')), path_obj.suffix

    # --- FFMPEG Actions ---

    def ffmpeg_convert(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return
        
        nwext = self.ff_ext.get()
        if not nwext:
            self.log("ERROR: Extension required")
            return

        cmd = f'ffmpeg -y -i "{fname}" -map 0 -c copy "{fnwx}.{nwext}"'
        self.run_cmd(cmd)

    def ffmpeg_reverse(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return
        cmd = f'ffmpeg -y -i "{fname}" -vf reverse "{fnwx}_reversed{ext}"'
        self.run_cmd(cmd)

    def ffmpeg_cut(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return
        
        try:
            start = f"{self.cut_f_h.get()}:{self.cut_f_m.get()}:{self.cut_f_s.get()}"
            end = f"{self.cut_t_h.get()}:{self.cut_t_m.get()}:{self.cut_t_s.get()}"
            
            s_suffix = "".join([self.cut_f_h.get(), self.cut_f_m.get(), self.cut_f_s.get()])
            e_suffix = "".join([self.cut_t_h.get(), self.cut_t_m.get(), self.cut_t_s.get()])
            
            cmd = f'ffmpeg -y -ss {start} -to {end} -i "{fname}" -c copy "{fnwx}_{s_suffix}_{e_suffix}{ext}"'
            self.run_cmd(cmd)
        except Exception as e:
            self.log(f"Error preparing cut command: {e}")

    def ffmpeg_screenshot(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return

        time = f"{self.ss_h.get()}:{self.ss_m.get()}:{self.ss_s.get()}"
        frames = self.ss_frames.get()
        
        cmd = f'ffmpeg -y -ss {time} -i "{fname}" -frames:v {frames} "{fnwx}_screen.png"'
        self.run_cmd(cmd)

    def ffmpeg_scale(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return

        raw_mode = self.scale_mode.get() 
        scmode = self.scale_mode_map.get(raw_mode, "res")
        scvalue = self.scale_val.get()

        fstr = ""
        if scmode == "res":
            fstr = f"scale={scvalue}"
        elif scmode == "factor":
            fstr = f"scale=iw{scvalue}:ih{scvalue}"
        elif scmode == "asrth":
            fstr = f"scale=-2:{scvalue}"
        elif scmode == "asrtw":
            fstr = f"scale={scvalue}:-2"

        clean_val = re.sub(r'[/\*:]', '', scvalue)
        cmd = f'ffmpeg -y -i "{fname}" -vf "{fstr}" "{fnwx}_{clean_val}{ext}"'
        self.run_cmd(cmd)

    def ffmpeg_speed(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return
        
        multiplier = self.speed_val.get()
        cmd = f'ffmpeg -y -i "{fname}" -filter:v "setpts={multiplier}*PTS" -an "{fnwx}_{multiplier}{ext}"'
        self.run_cmd(cmd)

    def ffmpeg_framerate(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return
        
        fps = self.fps_val.get()
        fps = re.sub(r'[^0-9.]', '', fps)
        if not fps: fps = "24"

        cmd = f'ffmpeg -y -i "{fname}" -filter:v "fps={fps}" -c:a copy "{fnwx}_fps{fps}{ext}"'
        self.run_cmd(cmd)

    # --- MAGICK Actions ---

    def magick_version(self):
        self.run_cmd("magick -version")

    def on_magick_preset(self, event):
        val = self.mg_preset.get()
        if val == "Transparency":
            self.mg_xcmd.delete(0, tk.END)
            self.mg_xcmd.insert(0, "-fuzz 20% -transparent white")

    def magick_metadata(self):
        fname = self.filepath_var.get()
        if not fname: 
            self.log("Error: Select a file for metadata")
            return
        self.run_cmd(f'magick identify -verbose "{fname}"')

    def magick_run(self):
        fname, fnwx, ext = self.get_file_info()
        if not fname: return
        
        convert_to = self.mg_convert.get().strip()
        resize = self.mg_resize.get().strip()
        xcmd = self.mg_xcmd.get().strip()

        newext = ext
        cmd_start = "magick "
        
        if convert_to:
            cmd_start += "convert "
            newext = f".{convert_to}"
        
        cmd_mid = f'"{fname}" '
        
        suffix = ""
        if resize:
            cmd_mid += f"-resize {resize} "
            suffix = f"_{resize}"
        
        cmd_mid += f"{xcmd} "
        
        outfile = f'"{fnwx}{suffix}{newext}"'
        
        full_cmd = cmd_start + cmd_mid + outfile
        self.run_cmd(full_cmd)

if __name__ == "__main__":
    app = MediaWebGui()
    app.mainloop()
