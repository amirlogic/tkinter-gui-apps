import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import threading
from datetime import datetime

class VideoChunkRemover:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Chunk Remover")
        self.root.geometry("800x600")
        
        self.video_file = ""
        self.chunks_to_remove = []
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Video file selection
        ttk.Label(main_frame, text="Video File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.video_path_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.video_path_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_video).grid(row=0, column=2, padx=5)
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Chunk removal section
        ttk.Label(main_frame, text="Remove Chunks:", font=('TkDefaultFont', 10, 'bold')).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # Add chunk frame
        chunk_frame = ttk.Frame(main_frame)
        chunk_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        chunk_frame.columnconfigure(1, weight=1)
        chunk_frame.columnconfigure(3, weight=1)
        
        ttk.Label(chunk_frame, text="Start Time:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.start_time_var = tk.StringVar(value="00:00:00")
        ttk.Entry(chunk_frame, textvariable=self.start_time_var, width=15).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(chunk_frame, text="End Time:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.end_time_var = tk.StringVar(value="00:00:00")
        ttk.Entry(chunk_frame, textvariable=self.end_time_var, width=15).grid(row=0, column=3, sticky=tk.W, padx=5)
        
        ttk.Button(chunk_frame, text="Add Chunk", command=self.add_chunk).grid(row=0, column=4, padx=5)
        
        # Time format help
        ttk.Label(chunk_frame, text="Format: HH:MM:SS or MM:SS", font=('TkDefaultFont', 8)).grid(row=1, column=0, columnspan=5, sticky=tk.W, pady=2)
        
        # Chunks list
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Treeview for chunks
        self.chunks_tree = ttk.Treeview(list_frame, columns=('Start', 'End'), show='headings', height=8)
        self.chunks_tree.heading('Start', text='Start Time')
        self.chunks_tree.heading('End', text='End Time')
        self.chunks_tree.column('Start', width=100)
        self.chunks_tree.column('End', width=100)
        self.chunks_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.chunks_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.chunks_tree.configure(yscrollcommand=scrollbar.set)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        ttk.Button(buttons_frame, text="Remove Selected", command=self.remove_selected_chunk).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Clear All", command=self.clear_all_chunks).pack(side=tk.LEFT, padx=5)
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Process button
        self.process_btn = ttk.Button(main_frame, text="Process Video", command=self.process_video)
        self.process_btn.grid(row=7, column=0, columnspan=3, pady=10)
        
        # Progress bar
        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.progress_var).grid(row=8, column=0, columnspan=3, pady=5)
        
        # Configure grid weights for resizing
        main_frame.rowconfigure(4, weight=1)
        
    def browse_video(self):
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.video_file = file_path
            self.video_path_var.set(file_path)
            
    def validate_time_format(self, time_str):
        """Validate and convert time format to HH:MM:SS"""
        time_str = time_str.strip()
        if not time_str:
            return None
            
        # Handle MM:SS format
        if len(time_str.split(':')) == 2:
            try:
                minutes, seconds = time_str.split(':')
                minutes = int(minutes)
                seconds = float(seconds)
                return f"00:{minutes:02d}:{seconds:06.3f}"
            except ValueError:
                return None
        
        # Handle HH:MM:SS format
        elif len(time_str.split(':')) == 3:
            try:
                hours, minutes, seconds = time_str.split(':')
                hours = int(hours)
                minutes = int(minutes)
                seconds = float(seconds)
                return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"
            except ValueError:
                return None
        
        return None
        
    def time_to_seconds(self, time_str):
        """Convert HH:MM:SS to seconds"""
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
        
    def add_chunk(self):
        start_time = self.validate_time_format(self.start_time_var.get())
        end_time = self.validate_time_format(self.end_time_var.get())
        
        if not start_time or not end_time:
            messagebox.showerror("Invalid Time", "Please enter valid time in HH:MM:SS or MM:SS format")
            return
            
        start_seconds = self.time_to_seconds(start_time)
        end_seconds = self.time_to_seconds(end_time)
        
        if start_seconds >= end_seconds:
            messagebox.showerror("Invalid Range", "Start time must be before end time")
            return
            
        # Check for overlapping chunks
        for chunk in self.chunks_to_remove:
            chunk_start = self.time_to_seconds(chunk['start'])
            chunk_end = self.time_to_seconds(chunk['end'])
            
            if (start_seconds < chunk_end and end_seconds > chunk_start):
                messagebox.showerror("Overlapping Chunks", "This chunk overlaps with an existing chunk")
                return
        
        chunk = {'start': start_time, 'end': end_time}
        self.chunks_to_remove.append(chunk)
        
        # Add to treeview
        self.chunks_tree.insert('', 'end', values=(start_time, end_time))
        
        # Clear input fields
        self.start_time_var.set("00:00:00")
        self.end_time_var.set("00:00:00")
        
    def remove_selected_chunk(self):
        selection = self.chunks_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a chunk to remove")
            return
            
        for item in selection:
            index = self.chunks_tree.index(item)
            self.chunks_tree.delete(item)
            del self.chunks_to_remove[index]
            
    def clear_all_chunks(self):
        self.chunks_tree.delete(*self.chunks_tree.get_children())
        self.chunks_to_remove.clear()
        
    def process_video(self):
        if not self.video_file:
            messagebox.showerror("No Video", "Please select a video file")
            return
            
        if not self.chunks_to_remove:
            messagebox.showerror("No Chunks", "Please add at least one chunk to remove")
            return
            
        # Ask for output file
        output_file = filedialog.asksaveasfilename(
            title="Save Processed Video As",
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        
        if not output_file:
            return
            
        # Start processing in a separate thread
        self.process_btn.config(state='disabled')
        self.progress_var.set("Processing...")
        
        thread = threading.Thread(target=self.process_video_thread, args=(output_file,))
        thread.daemon = True
        thread.start()
        
    def process_video_thread(self, output_file):
        try:
            # Sort chunks by start time
            sorted_chunks = sorted(self.chunks_to_remove, key=lambda x: self.time_to_seconds(x['start']))
            
            # Create filter_complex string for FFmpeg
            filter_parts = []
            current_time = 0
            segment_index = 0
            
            for chunk in sorted_chunks:
                start_seconds = self.time_to_seconds(chunk['start'])
                end_seconds = self.time_to_seconds(chunk['end'])
                
                # Add segment before this chunk
                if current_time < start_seconds:
                    filter_parts.append(f"[0:v]trim=start={current_time}:end={start_seconds},setpts=PTS-STARTPTS[v{segment_index}];")
                    filter_parts.append(f"[0:a]atrim=start={current_time}:end={start_seconds},asetpts=PTS-STARTPTS[a{segment_index}];")
                    segment_index += 1
                
                current_time = end_seconds
            
            # Add final segment after last chunk
            filter_parts.append(f"[0:v]trim=start={current_time},setpts=PTS-STARTPTS[v{segment_index}];")
            filter_parts.append(f"[0:a]atrim=start={current_time},asetpts=PTS-STARTPTS[a{segment_index}];")
            
            # Create concatenation filter
            video_inputs = "".join([f"[v{i}]" for i in range(segment_index + 1)])
            audio_inputs = "".join([f"[a{i}]" for i in range(segment_index + 1)])
            concat_filter = f"{video_inputs}concat=n={segment_index + 1}:v=1:a=0[outv];{audio_inputs}concat=n={segment_index + 1}:v=0:a=1[outa]"
            
            filter_complex = "".join(filter_parts) + concat_filter
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-i', self.video_file,
                '-filter_complex', filter_complex,
                '-map', '[outv]',
                '-map', '[outa]',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-y',  # Overwrite output file
                output_file
            ]
            
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.root.after(0, lambda: self.process_complete(True, "Video processed successfully!"))
            else:
                self.root.after(0, lambda: self.process_complete(False, f"FFmpeg error: {result.stderr}"))
                
        except Exception as e:
            self.root.after(0, lambda: self.process_complete(False, f"Error: {str(e)}"))
            
    def process_complete(self, success, message):
        self.process_btn.config(state='normal')
        
        if success:
            self.progress_var.set("Processing complete!")
            messagebox.showinfo("Success", message)
        else:
            self.progress_var.set("Processing failed!")
            messagebox.showerror("Error", message)

def main():
    root = tk.Tk()
    app = VideoChunkRemover(root)
    root.mainloop()

if __name__ == "__main__":
    main()
