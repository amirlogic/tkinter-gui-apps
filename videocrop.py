import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import threading
import re

class VideoCropperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FFmpeg Video Cropper")
        self.root.geometry("600x680")

        # State Variables
        self.source_file = tk.StringVar()
        self.source_w = tk.IntVar(value=1920)
        self.source_h = tk.IntVar(value=1080)
        self.target_w = tk.IntVar(value=1080)
        self.target_h = tk.IntVar(value=1920)
        self.crop_x = tk.IntVar(value=0)
        self.crop_y = tk.IntVar(value=0)

        self._init_ui()

    def _init_ui(self):
        # 1. File Selection
        frame_file = ttk.LabelFrame(self.root, text="1. Select Video", padding=10)
        frame_file.pack(fill="x", padx=10, pady=5)
        ttk.Entry(frame_file, textvariable=self.source_file, state="readonly").pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(frame_file, text="Browse...", command=self.load_video).pack(side="right")

        # 2. Dimension Inputs
        frame_dims = ttk.Frame(self.root, padding=10)
        frame_dims.pack(fill="x")

        f_src = ttk.LabelFrame(frame_dims, text="Source Size (Auto-detected)", padding=10)
        f_src.pack(side="left", fill="both", expand=True, padx=5)
        ttk.Label(f_src, text="W:").grid(row=0, column=0)
        ttk.Entry(f_src, textvariable=self.source_w, width=8).grid(row=0, column=1)
        ttk.Label(f_src, text="H:").grid(row=1, column=0)
        ttk.Entry(f_src, textvariable=self.source_h, width=8).grid(row=1, column=1)

        f_tar = ttk.LabelFrame(frame_dims, text="Target Size", padding=10)
        f_tar.pack(side="left", fill="both", expand=True, padx=5)
        ttk.Label(f_tar, text="W:").grid(row=0, column=0)
        ttk.Entry(f_tar, textvariable=self.target_w, width=8).grid(row=0, column=1)
        ttk.Label(f_tar, text="H:").grid(row=1, column=0)
        ttk.Entry(f_tar, textvariable=self.target_h, width=8).grid(row=1, column=1)
        
        ttk.Button(frame_dims, text="Set Sliders", command=self.update_slider_limits).pack(side="right", padx=5)

        # 3. Sliders
        frame_pos = ttk.LabelFrame(self.root, text="Crop Position", padding=10)
        frame_pos.pack(fill="x", padx=10, pady=5)
        self.slider_x = tk.Scale(frame_pos, from_=0, to=100, orient="horizontal", label="X Offset", variable=self.crop_x, command=self.on_slider_change)
        self.slider_x.pack(fill="x")
        self.slider_y = tk.Scale(frame_pos, from_=0, to=100, orient="horizontal", label="Y Offset", variable=self.crop_y, command=self.on_slider_change)
        self.slider_y.pack(fill="x")
        ttk.Button(frame_pos, text="Center Crop", command=self.center_crop).pack(pady=5)

        # 4. Command Preview
        self.txt_command = tk.Text(self.root, height=4, wrap="word", font=("Consolas", 9))
        self.txt_command.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 5. Render Button
        self.btn_run = ttk.Button(self.root, text="Render Video", command=self.validate_and_run, state="disabled")
        self.btn_run.pack(pady=10)
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status_var, relief="sunken").pack(side="bottom", fill="x")

    def load_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi")])
        if path:
            self.source_file.set(path)
            self.get_dims_via_ffmpeg(path)
            self.btn_run.config(state="normal")
            self.center_crop()

    def get_dims_via_ffmpeg(self, path):
        try:
            cmd = f'ffmpeg -i "{path}"'
            process = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            _, stderr = process.communicate()
            match = re.search(r'Video:.* (\d{3,5})x(\d{3,5})', stderr)
            if match:
                self.source_w.set(int(match.group(1)))
                self.source_h.set(int(match.group(2)))
                self.update_slider_limits()
        except: pass

    def update_slider_limits(self):
        try:
            sw, sh = self.source_w.get(), self.source_h.get()
            tw, th = self.target_w.get(), self.target_h.get()
            self.slider_x.config(to=max(0, sw - tw))
            self.slider_y.config(to=max(0, sh - th))
            self.generate_command()
        except: pass

    def on_slider_change(self, e): self.generate_command()

    def center_crop(self):
        try:
            self.crop_x.set(max(0, (self.source_w.get() - self.target_w.get()) // 2))
            self.crop_y.set(max(0, (self.source_h.get() - self.target_h.get()) // 2))
            self.update_slider_limits()
        except: pass

    def get_unique_filename(self, base_path):
        """Checks if file exists and appends an incrementing number if it does."""
        if not os.path.exists(base_path):
            return base_path
        
        folder, filename = os.path.split(base_path)
        name, ext = os.path.splitext(filename)
        
        counter = 1
        new_path = os.path.join(folder, f"{name}_{counter}{ext}")
        while os.path.exists(new_path):
            counter += 1
            new_path = os.path.join(folder, f"{name}_{counter}{ext}")
        return new_path

    def generate_command(self):
        if not self.source_file.get(): return None, None
        
        input_path = self.source_file.get()
        # Initial suggested path
        suggested_out = os.path.splitext(input_path)[0] + "_cropped" + os.path.splitext(input_path)[1]
        
        # Determine actual path based on existing files
        final_out = self.get_unique_filename(suggested_out)
        
        cmd = f'ffmpeg -i "{input_path}" -vf "crop={self.target_w.get()}:{self.target_h.get()}:{self.crop_x.get()}:{self.crop_y.get()}" -c:a copy "{final_out}"'
        
        self.txt_command.delete("1.0", tk.END)
        self.txt_command.insert(tk.END, cmd)
        return cmd, final_out

    def validate_and_run(self):
        sw, sh = self.source_w.get(), self.source_h.get()
        tw, th = self.target_w.get(), self.target_h.get()
        cx, cy = self.crop_x.get(), self.crop_y.get()

        if tw > sw or th > sh or (cx + tw) > sw or (cy + th) > sh:
            messagebox.showerror("Error", "Crop area exceeds source dimensions.")
            return
        self.run_ffmpeg()

    def run_ffmpeg(self):
        cmd_str, output_path = self.generate_command()
        self.btn_run.config(state="disabled")
        self.status_var.set(f"Rendering: {os.path.basename(output_path)}...")
        
        def process():
            try:
                subprocess.run(cmd_str, shell=True, check=True)
                self.root.after(0, lambda: messagebox.showinfo("Success", f"File saved as:\n{output_path}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"FFmpeg failed: {e}"))
            finally:
                self.root.after(0, lambda: [self.btn_run.config(state="normal"), self.status_var.set("Ready")])

        threading.Thread(target=process, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    VideoCropperApp(root)
    root.mainloop()