import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import os
import re
import threading

class SceneDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FFmpeg Scene Detection")
        self.root.geometry("800x600")
        
        self.video_path = tk.StringVar()
        self.threshold = tk.DoubleVar(value=0.3)
        self.is_processing = False
        
        self.create_widgets()
        
    def create_widgets(self):
        # File selection frame
        file_frame = ttk.LabelFrame(self.root, text="Video File", padding=10)
        file_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Entry(file_frame, textvariable=self.video_path, width=60).pack(side="left", padx=5)
        ttk.Button(file_frame, text="Browse", command=self.browse_file).pack(side="left")
        
        # Settings frame
        settings_frame = ttk.LabelFrame(self.root, text="Settings", padding=10)
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(settings_frame, text="Scene Threshold (0.0-1.0):").pack(side="left", padx=5)
        threshold_spinbox = ttk.Spinbox(
            settings_frame, 
            from_=0.0, 
            to=1.0, 
            increment=0.05,
            textvariable=self.threshold,
            width=10
        )
        threshold_spinbox.pack(side="left", padx=5)
        ttk.Label(settings_frame, text="(Higher = fewer scenes)").pack(side="left", padx=5)
        
        # Control buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        self.detect_btn = ttk.Button(button_frame, text="Detect Scenes", command=self.detect_scenes)
        self.detect_btn.pack(side="left", padx=5)
        
        self.export_btn = ttk.Button(button_frame, text="Export List", command=self.export_list, state="disabled")
        self.export_btn.pack(side="left", padx=5)
        
        ttk.Button(button_frame, text="Clear", command=self.clear_results).pack(side="left", padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.root, mode='indeterminate')
        self.progress.pack(fill="x", padx=10, pady=5)
        
        # Results frame
        results_frame = ttk.LabelFrame(self.root, text="Detected Scenes", padding=10)
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, height=20)
        self.results_text.pack(fill="both", expand=True)
        
        # Status bar
        self.status = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status, relief=tk.SUNKEN)
        status_bar.pack(fill="x", side="bottom")
        
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mkv *.mov *.flv *.wmv"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.video_path.set(filename)
            
    def format_timestamp(self, seconds):
        """Convert seconds to HH:MM:SS.mmm format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def detect_scenes(self):
        if not self.video_path.get():
            messagebox.showwarning("No File", "Please select a video file first.")
            return
            
        if not os.path.exists(self.video_path.get()):
            messagebox.showerror("Error", "Selected file does not exist.")
            return
            
        if self.is_processing:
            messagebox.showinfo("Processing", "Scene detection is already in progress.")
            return
            
        # Run detection in separate thread
        thread = threading.Thread(target=self.run_detection)
        thread.daemon = True
        thread.start()
        
    def run_detection(self):
        self.is_processing = True
        self.detect_btn.config(state="disabled")
        self.export_btn.config(state="disabled")
        self.progress.start()
        self.status.set("Detecting scenes...")
        self.results_text.delete(1.0, tk.END)
        
        try:
            # FFmpeg command for scene detection
            cmd = [
                'ffmpeg',
                '-i', self.video_path.get(),
                '-filter:v', f"select='gt(scene,{self.threshold.get()})',showinfo",
                '-f', 'null',
                '-'
            ]
            
            # Run FFmpeg
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            _, stderr = process.communicate()
            
            # Parse output for scene changes
            scenes = []
            # Look for lines with showinfo output
            lines = stderr.split('\n')
            
            for line in lines:
                # Match pts_time in showinfo output
                if 'pts_time:' in line and 'showinfo' in line:
                    # Extract timestamp
                    pts_match = re.search(r'pts_time:([\d.]+)', line)
                    if pts_match:
                        timestamp = float(pts_match.group(1))
                        # Try to find scene score if available
                        score_match = re.search(r'scene:([\d.]+)', line)
                        score = float(score_match.group(1)) if score_match else 0.0
                        scenes.append((timestamp, score))
            
            # Display results
            if scenes:
                self.results_text.insert(tk.END, f"Found {len(scenes)} scene changes:\n\n")
                self.results_text.insert(tk.END, f"{'Scene #':<10}{'Timestamp':<20}{'Time':<15}{'Score':<10}\n")
                self.results_text.insert(tk.END, "-" * 60 + "\n")
                
                for i, (timestamp, score) in enumerate(scenes, 1):
                    time_str = self.format_timestamp(timestamp)
                    self.results_text.insert(
                        tk.END, 
                        f"{i:<10}{timestamp:<20.3f}{time_str:<15}{score:<10.3f}\n"
                    )
                
                self.export_btn.config(state="normal")
                self.status.set(f"Complete: {len(scenes)} scenes detected")
            else:
                self.results_text.insert(tk.END, "No scene changes detected. Try lowering the threshold.")
                self.status.set("No scenes detected")
                
        except FileNotFoundError:
            messagebox.showerror("Error", "FFmpeg not found. Please install FFmpeg and add it to your PATH.")
            self.status.set("Error: FFmpeg not found")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            self.status.set("Error occurred")
        finally:
            self.is_processing = False
            self.detect_btn.config(state="normal")
            self.progress.stop()
            
    def export_list(self):
        content = self.results_text.get(1.0, tk.END)
        if not content.strip():
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Scene list exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")
                
    def clear_results(self):
        self.results_text.delete(1.0, tk.END)
        self.export_btn.config(state="disabled")
        self.status.set("Ready")

if __name__ == "__main__":
    root = tk.Tk()
    app = SceneDetectorApp(root)
    root.mainloop()