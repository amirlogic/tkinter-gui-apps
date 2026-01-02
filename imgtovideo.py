import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import shutil
import os
import threading

class VideoMakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image to Video with Zoom (FFmpeg)")
        self.root.geometry("500x450")
        self.root.resizable(False, False)

        # Variables
        self.image_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.duration = tk.StringVar(value="5")
        self.effect = tk.StringVar(value="Zoom In")
        self.resolution = tk.StringVar(value="1280x720")
        
        # Check for FFmpeg
        if not shutil.which("ffmpeg"):
            messagebox.showerror("Error", "FFmpeg is not found on your system.\nPlease install FFmpeg and add it to your PATH.")
            self.root.destroy()
            return

        self._create_widgets()

    def _create_widgets(self):
        # Main Frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Image Selection
        ttk.Label(main_frame, text="1. Select Image:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        img_frame = ttk.Frame(main_frame)
        img_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        
        self.entry_img = ttk.Entry(img_frame, textvariable=self.image_path, width=50)
        self.entry_img.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        btn_browse_img = ttk.Button(img_frame, text="Browse", command=self.browse_image)
        btn_browse_img.pack(side=tk.RIGHT)

        # 2. Settings
        ttk.Label(main_frame, text="2. Settings:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 5))

        settings_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        settings_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 15))

        # Duration
        ttk.Label(settings_frame, text="Duration (seconds):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(settings_frame, textvariable=self.duration, width=10).grid(row=0, column=1, sticky="w", padx=5, pady=5)

        # Effect
        ttk.Label(settings_frame, text="Zoom Effect:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        effects = ["Zoom In", "Zoom Out", "No Zoom"]
        ttk.OptionMenu(settings_frame, self.effect, self.effect.get(), *effects).grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Resolution
        ttk.Label(settings_frame, text="Output Resolution:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        resolutions = ["1920x1080", "1280x720", "720x480", "1080x1080"]
        ttk.Combobox(settings_frame, textvariable=self.resolution, values=resolutions, state="readonly", width=15).grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # 3. Output Selection
        ttk.Label(main_frame, text="3. Save Video As:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="w", pady=(0, 5))
        
        out_frame = ttk.Frame(main_frame)
        out_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 20))
        
        self.entry_out = ttk.Entry(out_frame, textvariable=self.output_path, width=50)
        self.entry_out.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        btn_browse_out = ttk.Button(out_frame, text="Save As...", command=self.save_as)
        btn_browse_out.pack(side=tk.RIGHT)

        # 4. Action
        self.btn_run = ttk.Button(main_frame, text="Generate Video", command=self.start_generation_thread)
        self.btn_run.grid(row=6, column=0, columnspan=3, sticky="ew", ipady=10)

        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def browse_image(self):
        filename = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if filename:
            self.image_path.set(filename)

    def save_as(self):
        filename = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
        if filename:
            self.output_path.set(filename)

    def start_generation_thread(self):
        # Run ffmpeg in a separate thread to keep UI responsive
        if not self.image_path.get() or not self.output_path.get():
            messagebox.showwarning("Missing Info", "Please select an input image and output location.")
            return
        
        self.btn_run.config(state=tk.DISABLED)
        self.status_var.set("Processing... Please wait.")
        
        thread = threading.Thread(target=self.generate_video)
        thread.start()

    def generate_video(self):
        try:
            img = self.image_path.get()
            out = self.output_path.get()
            dur = float(self.duration.get())
            effect = self.effect.get()
            res = self.resolution.get()
            
            # FPS Calculation (standard 25 fps)
            fps = 25
            total_frames = int(dur * fps)
            
            # --- FFmpeg Filter Logic ---
            # d (duration) in zoompan must be set high enough to cover the whole video
            # s (size) sets the resolution
            # x, y determine the "center" of the zoom
            
            zoom_expr = ""
            if effect == "Zoom In":
                # Start at 1.0, increase by 0.002 per frame (tunable)
                # Formula: min(zoom + step, max_zoom)
                # We normalize it so it zooms roughly 1.5x over the duration
                step = 0.5 / total_frames # To gain 0.5 zoom over total duration
                zoom_expr = f"z='min(zoom+{step:.6f},1.5)':d={total_frames*2}:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2'"
            
            elif effect == "Zoom Out":
                # Start at 1.5, decrease
                # Formula: If frame 1, set 1.5. Else, decrease.
                step = 0.5 / total_frames
                zoom_expr = f"z='if(eq(on,1),1.5,max(zoom-{step:.6f},1.0))':d={total_frames*2}:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2'"
            
            else: # No Zoom
                zoom_expr = f"z=1:d={total_frames*2}"

            # We use scale=8000:-1 before zoompan to "upscale" the input image momentarily.
            # This prevents pixelation when zooming in on smaller images.
            # Then we scale back down to target resolution (s=...) inside zoompan.
            
            vf_string = f"scale=8000:-1,zoompan={zoom_expr}:s={res}:fps={fps}"

            # Construct command
            # -y: Overwrite output
            # -loop 1: Loop the image
            # -t: Duration
            # -pix_fmt yuv420p: Ensure compatibility with all players
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", img,
                "-vf", vf_string,
                "-t", str(dur),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                out
            ]

            # Run FFmpeg
            # Using subprocess.PIPE to suppress console popups on Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                startupinfo=startupinfo
            )

            if process.returncode == 0:
                self.root.after(0, lambda: self.finish_success(out))
            else:
                err_msg = process.stderr.decode('utf-8')
                self.root.after(0, lambda: self.finish_error(err_msg))

        except Exception as e:
            self.root.after(0, lambda: self.finish_error(str(e)))

    def finish_success(self, filename):
        self.status_var.set(f"Done! Saved to {os.path.basename(filename)}")
        self.btn_run.config(state=tk.NORMAL)
        messagebox.showinfo("Success", "Video created successfully!")

    def finish_error(self, error_msg):
        self.status_var.set("Error occurred.")
        self.btn_run.config(state=tk.NORMAL)
        print(error_msg) # Print to console for debugging
        messagebox.showerror("Error", "Failed to create video.\nCheck console or inputs.")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoMakerApp(root)
    root.mainloop()