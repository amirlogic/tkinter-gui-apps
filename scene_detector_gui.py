import os
import sys
import subprocess
import threading
import glob
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk


class SceneDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FFmpeg Scene Change Detector")
        self.root.geometry("850x600")  # Fixed geometry specifier
        self.root.minsize(700, 500)

        # Variables
        self.video_path = tk.StringVar()
        self.threshold = tk.DoubleVar(value=0.3)  # FFmpeg select filter threshold (0.0 to 1.0)
        self.status_text = tk.StringVar(value="Select a video file to begin.")
        self.image_references = []  # Keep references to prevent garbage collection

        self._create_widgets()

    def _create_widgets(self):
        # --- Top Section: File Selection & Settings ---
        top_frame = ttk.LabelFrame(self.root, text="Video & Settings", padding=10)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        # Video File Selection
        ttk.Label(top_frame, text="Video File:").grid(row=0, column=0, sticky=tk.W, pady=2)
        entry_path = ttk.Entry(top_frame, textvariable=self.video_path, width=60)
        entry_path.grid(row=0, column=1, padx=5, pady=2, sticky=tk.EW)
        
        btn_browse = ttk.Button(top_frame, text="Browse...", command=self.browse_file)
        btn_browse.grid(row=0, column=2, padx=2, pady=2)

        # Threshold Control
        ttk.Label(top_frame, text="Detection Threshold (0.1 - 1.0):").grid(row=1, column=0, sticky=tk.W, pady=5)
        thresh_spin = ttk.Spinbox(
            top_frame, 
            from_=0.05, 
            to=1.0, 
            increment=0.05, 
            textvariable=self.threshold, 
            width=10
        )
        thresh_spin.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Action Button
        self.btn_process = ttk.Button(top_frame, text="Detect & Extract Scenes", command=self.start_processing_thread)
        self.btn_process.grid(row=1, column=2, padx=2, pady=5)

        top_frame.columnconfigure(1, weight=1)

        # --- Middle Section: Progress Bar & Status ---
        status_frame = ttk.Frame(self.root, padding=(10, 0))
        status_frame.pack(fill=tk.X, padx=10, pady=2)

        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=2)

        lbl_status = ttk.Label(status_frame, textvariable=self.status_text, foreground="gray30")
        lbl_status.pack(anchor=tk.W)

        # --- Bottom Section: Scrollable Image Gallery ---
        gallery_frame = ttk.LabelFrame(self.root, text="Detected Scene Screenshots", padding=10)
        gallery_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Canvas + Scrollbar setup for scrolling thumbnail grid
        self.canvas = tk.Canvas(gallery_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(gallery_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Canvas resize handler to wrap grid layout dynamically
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_canvas_configure(self, event):
        # Stretch inner frame width to fit canvas
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def browse_file(self):
        filetypes = (
            ("Video files", "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm"),
            ("All files", "*.*")
        )
        filepath = filedialog.askopenfilename(title="Select Video", filetypes=filetypes)
        if filepath:
            self.video_path.set(filepath)

    def start_processing_thread(self):
        video_file = self.video_path.get().strip()
        if not video_file or not os.path.isfile(video_file):
            messagebox.showwarning("Warning", "Please select a valid video file.")
            return

        # Run process in a separate thread so GUI remains responsive
        self.btn_process.config(state=tk.DISABLED)
        self.progress.start(10)
        self.status_text.set("Processing video scene detection... Please wait.")
        
        # Clear existing images from gallery
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.image_references.clear()

        threading.Thread(target=self.process_video, args=(video_file,), daemon=True).start()

    def process_video(self, video_file):
        try:
            video_dir, full_filename = os.path.split(video_file)
            video_name, _ = os.path.splitext(full_filename)

            # Target directory structure: <video_dir>/screenshots/<video_name>/
            output_dir = os.path.join(video_dir, "screenshots", video_name)
            os.makedirs(output_dir, exist_ok=True)

            output_pattern = os.path.join(output_dir, "scene_%04d.jpg")

            # FFmpeg Command for scene detection:
            # -select_frames: filter by scene change score above threshold
            # -vsync vfr: variable frame rate to output only selected frames
            thresh = self.threshold.get()
            cmd = [
                "ffmpeg",
                "-y",                             # Overwrite output files
                "-i", video_file,                 # Input file
                "-filter_complex", f"select='gt(scene,{thresh})',metadata=print",
                "-vsync", "vfr",
                output_pattern
            ]

            # Execute FFmpeg without opening command window (Windows hide console)
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                text=True
            )
            _, stderr = process.communicate()

            if process.returncode != 0:
                raise Exception(f"FFmpeg error:\n{stderr}")

            # Collect generated screenshot images
            images = sorted(glob.glob(os.path.join(output_dir, "scene_*.jpg")))

            # Update GUI back on main thread
            self.root.after(0, self.on_processing_complete, images, output_dir)

        except Exception as e:
            self.root.after(0, self.on_processing_error, str(e))

    def on_processing_complete(self, image_paths, output_dir):
        self.progress.stop()
        self.btn_process.config(state=tk.NORMAL)

        if not image_paths:
            self.status_text.set("Finished: No scene changes detected with current threshold.")
            messagebox.showinfo("Finished", "No scene changes detected. Try lowering the threshold.")
            return

        self.status_text.set(f"Done! Found {len(image_paths)} scenes. Saved to: {output_dir}")
        self.display_thumbnails(image_paths)

    def on_processing_error(self, error_msg):
        self.progress.stop()
        self.btn_process.config(state=tk.NORMAL)
        self.status_text.set("Error occurred during processing.")
        messagebox.showerror("Error", f"Failed to process video.\n\n{error_msg}")

    def display_thumbnails(self, image_paths):
        thumb_width = 160
        thumb_height = 90
        columns = 4

        for index, img_path in enumerate(image_paths):
            try:
                img = Image.open(img_path)
                img.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.image_references.append(photo)  # Save reference

                # Create frame for image + label
                item_frame = ttk.Frame(self.scrollable_frame, padding=5)
                row = index // columns
                col = index % columns
                item_frame.grid(row=row, column=col, padx=5, pady=5)

                lbl_img = ttk.Label(item_frame, image=photo)
                lbl_img.pack()

                file_name = os.path.basename(img_path)
                lbl_txt = ttk.Label(item_frame, text=file_name, font=("Arial", 8))
                lbl_txt.pack()

            except Exception as e:
                print(f"Error loading thumbnail {img_path}: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = SceneDetectorApp(root)
    root.mainloop()