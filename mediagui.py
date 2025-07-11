import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import webbrowser
import threading
import re

class MediaGuiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MediaGui")
        self.root.geometry("800x600")
        self.root.configure(bg="#f2f2f2")
        
        self.processing = False
        self.process = None
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main container
        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Home screen
        self.home_frame = ttk.Frame(self.main_frame)
        self.home_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(self.home_frame, text="MediaGui", font=("Arial", 24)).pack(pady=10)
        
        # Target selection
        ttk.Label(self.home_frame, text="Select Tool:").pack()
        self.target_var = tk.StringVar(value="ffmpeg")
        target_combo = ttk.Combobox(self.home_frame, textvariable=self.target_var, 
                                  values=["ffmpeg", "magick"], state="readonly")
        target_combo.pack(pady=5)
        
        # File selection
        self.file_var = tk.StringVar()
        file_frame = ttk.Frame(self.home_frame)
        file_frame.pack(pady=5, fill=tk.X)
        ttk.Entry(file_frame, textvariable=self.file_var, state="readonly").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))
        ttk.Button(file_frame, text="Browse", command=self.browse_file).pack(side=tk.RIGHT)
        
        # Action buttons
        action_frame = ttk.Frame(self.home_frame)
        action_frame.pack(pady=10)
        ttk.Button(action_frame, text="Process File", command=self.process_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="FFmpeg Version", command=lambda: self.show_version("ffmpeg")).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Magick Version", command=lambda: self.show_version("magick")).pack(side=tk.LEFT, padx=5)
        
        # Processing overlay (initially hidden)
        self.overlay = tk.Toplevel(self.root)
        self.overlay.withdraw()
        self.overlay.title("Processing")
        self.overlay.geometry("300x150")
        self.overlay.resizable(False, False)
        self.overlay.transient(self.root)
        ttk.Label(self.overlay, text="Processing...", font=("Arial", 14)).pack(pady=20)
        ttk.Button(self.overlay, text="Cancel", command=self.cancel_operation).pack(pady=10)
        self.center_overlay()
        
    def center_overlay(self):
        self.overlay.update_idletasks()
        width = self.overlay.winfo_width()
        height = self.overlay.winfo_height()
        x = (self.root.winfo_screenwidth() - width) // 2
        y = (self.root.winfo_screenheight() - height) // 2
        self.overlay.geometry(f"{width}x{height}+{x}+{y}")
        
    def browse_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.file_var.set(file_path)
            
    def show_processing(self):
        self.processing = True
        self.root.config(cursor="wait")
        for widget in self.root.winfo_children():
            self.set_widget_state(widget, "disabled")
        self.overlay.deiconify()
        
    def hide_processing(self):
        self.processing = False
        self.root.config(cursor="")
        for widget in self.root.winfo_children():
            self.set_widget_state(widget, "normal")
        self.overlay.withdraw()
        
    def set_widget_state(self, widget, state):
        try:
            widget.configure(state=state)
        except:
            pass
        for child in widget.winfo_children():
            self.set_widget_state(child, state)
            
    def cancel_operation(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.hide_processing()
        
    def run_command(self, cmd, output_widget=None):
        def thread_func():
            try:
                self.process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 
                                             stderr=subprocess.PIPE, text=True)
                stdout, stderr = self.process.communicate()
                
                self.root.after(0, self.hide_processing)
                
                if self.process.returncode != 0:
                    self.root.after(0, lambda: messagebox.showerror("Error", stderr or "Unknown error"))
                elif output_widget:
                    self.root.after(0, lambda: output_widget.insert(tk.END, stdout))
                else:
                    self.root.after(0, lambda: messagebox.showinfo("Success", "Operation completed successfully"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.root.after(0, self.hide_processing)
                
        self.show_processing()
        threading.Thread(target=thread_func, daemon=True).start()
        
    def show_version(self, tool):
        new_window = tk.Toplevel(self.root)
        new_window.title(f"{tool.capitalize()} Version")
        new_window.geometry("600x400")
        text_area = tk.Text(new_window, wrap=tk.WORD)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        cmd = "ffmpeg -version" if tool == "ffmpeg" else "magick -version"
        self.run_command(cmd, text_area)
        
    def process_file(self):
        if not self.file_var.get():
            messagebox.showerror("Error", "Please select a file")
            return
            
        self.file_window = tk.Toplevel(self.root)
        self.file_window.title("File Processing")
        self.file_window.geometry("800x600")
        
        if self.target_var.get() == "ffmpeg":
            self.create_ffmpeg_interface()
        else:
            self.create_magick_interface()
            
    def create_ffmpeg_interface(self):
        frame = ttk.Frame(self.file_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="FFmpeg", font=("Arial", 24)).pack(pady=10)
        ttk.Label(frame, text=f"File: {self.file_var.get()}").pack()
        
        # Convert
        convert_frame = ttk.LabelFrame(frame, text="Convert", padding=10)
        convert_frame.pack(pady=5, fill=tk.X)
        ttk.Label(convert_frame, text="Convert to:").pack(side=tk.LEFT)
        convert_ext = ttk.Entry(convert_frame, width=10)
        convert_ext.pack(side=tk.LEFT, padx=5)
        ttk.Button(convert_frame, text="Convert", 
                  command=lambda: self.ffmpeg_convert(convert_ext.get())).pack(side=tk.LEFT)
        
        # Reverse
        ttk.Button(frame, text="Reverse", 
                  command=self.ffmpeg_reverse).pack(pady=5, fill=tk.X)
        
        # Cut
        cut_frame = ttk.LabelFrame(frame, text="Split", padding=10)
        cut_frame.pack(pady=5, fill=tk.X)
        
        from_frame = ttk.Frame(cut_frame)
        from_frame.pack(fill=tk.X)
        ttk.Label(from_frame, text="From:").pack(side=tk.LEFT)
        fhrs = ttk.Entry(from_frame, width=3)
        fhrs.insert(0, "00")
        fhrs.pack(side=tk.LEFT)
        ttk.Label(from_frame, text=":").pack(side=tk.LEFT)
        fmin = ttk.Entry(from_frame, width=3)
        fmin.insert(0, "00")
        fmin.pack(side=tk.LEFT)
        ttk.Label(from_frame, text=":").pack(side=tk.LEFT)
        fsec = ttk.Entry(from_frame, width=3)
        fsec.insert(0, "00")
        fsec.pack(side=tk.LEFT)
        
        to_frame = ttk.Frame(cut_frame)
        to_frame.pack(fill=tk.X, pady=5)
        ttk.Label(to_frame, text="To:").pack(side=tk.LEFT)
        thrs = ttk.Entry(to_frame, width=3)
        thrs.insert(0, "00")
        thrs.pack(side=tk.LEFT)
        ttk.Label(to_frame, text=":").pack(side=tk.LEFT)
        tmin = ttk.Entry(to_frame, width=3)
        tmin.insert(0, "00")
        tmin.pack(side=tk.LEFT)
        ttk.Label(to_frame, text=":").pack(side=tk.LEFT)
        tsec = ttk.Entry(to_frame, width=3)
        tsec.insert(0, "00")
        tsec.pack(side=tk.LEFT)
        
        ttk.Button(cut_frame, text="Cut", 
                  command=lambda: self.ffmpeg_cut(fhrs.get(), fmin.get(), fsec.get(), 
                                               thrs.get(), tmin.get(), tsec.get())).pack(pady=5)
        
        # Screenshot
        screenshot_frame = ttk.LabelFrame(frame, text="Screenshot", padding=10)
        screenshot_frame.pack(pady=5, fill=tk.X)
        time_frame = ttk.Frame(screenshot_frame)
        time_frame.pack(fill=tk.X)
        ttk.Label(time_frame, text="Time:").pack(side=tk.LEFT)
        hrs = ttk.Entry(time_frame, width=3)
        hrs.insert(0, "00")
        hrs.pack(side=tk.LEFT)
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT)
        min = ttk.Entry(time_frame, width=3)
        min.insert(0, "00")
        min.pack(side=tk.LEFT)
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT)
        sec = ttk.Entry(time_frame, width=3)
        sec.insert(0, "00")
        sec.pack(side=tk.LEFT)
        ttk.Button(screenshot_frame, text="Take Screenshot", 
                  command=lambda: self.ffmpeg_screenshot(hrs.get(), min.get(), sec.get())).pack(pady=5)
        
        # Scale
        scale_frame = ttk.LabelFrame(frame, text="Change Scale", padding=10)
        scale_frame.pack(pady=5, fill=tk.X)
        ttk.Label(scale_frame, text="Mode:").pack(side=tk.LEFT)
        scale_mode = ttk.Combobox(scale_frame, 
                                values=["res", "asrth", "asrtw", "factor"], 
                                state="readonly")
        scale_mode.set("res")
        scale_mode.pack(side=tk.LEFT, padx=5)
        scale_value = ttk.Entry(scale_frame)
        scale_value.insert(0, "w:h")
        scale_value.pack(side=tk.LEFT, padx=5)
        ttk.Button(scale_frame, text="Scale", 
                  command=lambda: self.ffmpeg_scale(scale_mode.get(), scale_value.get())).pack(side=tk.LEFT)
        
        # Speed
        speed_frame = ttk.LabelFrame(frame, text="Speed", padding=10)
        speed_frame.pack(pady=5, fill=tk.X)
        ttk.Label(speed_frame, text="Multiplier:").pack(side=tk.LEFT)
        speed_mult = ttk.Entry(speed_frame, width=5)
        speed_mult.insert(0, "1")
        speed_mult.pack(side=tk.LEFT, padx=5)
        ttk.Button(speed_frame, text="Change Speed", 
                  command=lambda: self.ffmpeg_speed(speed_mult.get())).pack(side=tk.LEFT)
        
        ttk.Button(frame, text="Back to Home", command=self.file_window.destroy).pack(pady=10)
        
    def create_magick_interface(self):
        frame = ttk.Frame(self.file_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="ImageMagick", font=("Arial", 24)).pack(pady=10)
        ttk.Label(frame, text=f"File: {self.file_var.get()}").pack()
        
        # Image info
        info_frame = ttk.Frame(frame)
        info_frame.pack(fill=tk.BOTH, expand=True)
        info_text = tk.Text(info_frame, height=10)
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        ttk.Button(frame, text="Get Metadata", 
                  command=lambda: self.magick_metadata(info_text)).pack(pady=5)
        
        # Modify
        modify_frame = ttk.LabelFrame(frame, text="Modify", padding=10)
        modify_frame.pack(pady=5, fill=tk.X)
        
        ttk.Label(modify_frame, text="Convert to:").pack(side=tk.LEFT)
        convert_ext = ttk.Entry(modify_frame, width=10)
        convert_ext.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(modify_frame, text="Resize:").pack(side=tk.LEFT)
        resize_val = ttk.Entry(modify_frame, width=15)
        resize_val.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(modify_frame, text="Extra:").pack(side=tk.LEFT)
        extra_cmd = ttk.Entry(modify_frame)
        extra_cmd.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        extra_options = ttk.Combobox(modify_frame, 
                                  values=["", "transparency"], 
                                  state="readonly")
        extra_options.set("")
        extra_options.pack(side=tk.LEFT, padx=5)
        extra_options.bind("<<ComboboxSelected>>", 
                         lambda e: extra_cmd.insert(tk.END, 
                                                  "-fuzz 20% -transparent white" if extra_options.get() == "transparency" else ""))
        
        ttk.Button(modify_frame, text="Modify", 
                  command=lambda: self.magick_modify(convert_ext.get(), resize_val.get(), extra_cmd.get())).pack(side=tk.LEFT)
        
        ttk.Button(frame, text="Back to Home", command=self.file_window.destroy).pack(pady=10)
        
    def ffmpeg_convert(self, new_ext):
        if not new_ext:
            messagebox.showerror("Error", "Please enter a new extension")
            return
        fname = self.file_var.get()
        fnwx = os.path.splitext(fname)[0]
        cmd = f'ffmpeg -i "{fname}" -map 0 -c copy "{fnwx}.{new_ext}"'
        self.run_command(cmd)
        
    def ffmpeg_reverse(self):
        fname = self.file_var.get()
        fnwx = os.path.splitext(fname)[0]
        ext = os.path.splitext(fname)[1]
        cmd = f'ffmpeg -i "{fname}" -vf reverse "{fnwx}_reversed{ext}"'
        self.run_command(cmd)
        
    def ffmpeg_cut(self, fhrs, fmin, fsec, thrs, tmin, tsec):
        if not all([fhrs, fmin, fsec, thrs, tmin, tsec]):
            messagebox.showerror("Error", "Please fill all time fields")
            return
        fname = self.file_var.get()
        fnwx = os.path.splitext(fname)[0]
        cmd = (f'ffmpeg -ss {fhrs}:{fmin}:{fsec} -to {thrs}:{tmin}:{tsec} '
              f'-i "{fname}" -c copy "{fnwx}_{fhrs}{fmin}{fsec}_{thrs}{tmin}{tsec}.avi"')
        self.run_command(cmd)
        
    def ffmpeg_screenshot(self, hrs, min, sec):
        if not all([hrs, min, sec]):
            messagebox.showerror("Error", "Please fill all time fields")
            return
        fname = self.file_var.get()
        fnwx = os.path.splitext(fname)[0]
        cmd = f'ffmpeg -ss {hrs}:{min}:{sec} -i "{fname}" -frames:v 1 "{fnwx}.png"'
        self.run_command(cmd)
        
    def ffmpeg_scale(self, mode, value):
        if not value:
            messagebox.showerror("Error", "Please enter a scale value")
            return
        fname = self.file_var.get()
        fnwx = os.path.splitext(fname)[0]
        ext = os.path.splitext(fname)[1]
        if mode == "res":
            fstr = f"scale={value}"
        elif mode == "factor":
            fstr = f"scale=iw{value}:ih{value}"
        elif mode == "asrth":
            fstr = f"scale=-2:{value}"
        elif mode == "asrtw":
            fstr = f"scale={value}:-2"
        else:
            messagebox.showerror("Error", "Invalid scale mode")
            return
        sanitized_value = re.sub(r'[/\*:]', '', value)
        cmd = f'ffmpeg -i "{fname}" -vf "{fstr}" "{fnwx}_{sanitized_value}{ext}"'
        self.run_command(cmd)
        
    def ffmpeg_speed(self, multiplier):
        if not multiplier:
            messagebox.showerror("Error", "Please enter a multiplier")
            return
        fname = self.file_var.get()
        fnwx = os.path.splitext(fname)[0]
        ext = os.path.splitext(fname)[1]
        cmd = f'ffmpeg -i "{fname}" -filter:v "setpts={multiplier}*PTS" -an "{fnwx}_{multiplier}{ext}"'
        self.run_command(cmd)
        
    def magick_metadata(self, text_widget):
        cmd = f'magick identify -verbose "{self.file_var.get()}"'
        self.run_command(cmd, text_widget)
        
    def magick_modify(self, convert, resize, xcmd):
        fname = self.file_var.get()
        fnwx = os.path.splitext(fname)[0]
        ext = os.path.splitext(fname)[1]
        newext = f".{convert}" if convert else ext
        suffix = f"_{resize}" if resize else ""
        cmd = "magick "
        if convert:
            cmd += "convert "
        cmd += f'"{fname}" '
        if resize:
            cmd += f'-resize {resize} '
        if xcmd:
            cmd += f'{xcmd} '
        cmd += f'"{fnwx}{suffix}{newext}"'
        self.run_command(cmd)

if __name__ == "__main__":
    root = tk.Tk()
    app = MediaGuiApp(root)
    root.mainloop()
