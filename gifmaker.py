import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading

def disable_widgets():
    for child in root.winfo_children():
        child_state(child, 'disable')

def enable_widgets():
    for child in root.winfo_children():
        child_state(child, 'normal')

def child_state(widget, state):
    try:
        widget.configure(state=state)
    except:
        pass
    for child in widget.winfo_children():
        child_state(child, state)

def select_video():
    path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv")])
    if path:
        video_path.set(path)

def select_output():
    path = filedialog.asksaveasfilename(defaultextension=".gif", filetypes=[("GIF Files", "*.gif")])
    if path:
        output_path.set(path)

def create_gif():
    def process():
        disable_widgets()
        processing_label.config(text="Processing, please wait...")
        try:
            cmd = ["ffmpeg", "-y"]
            if start_time.get():
                cmd.extend(["-ss", start_time.get()])
            cmd.extend(["-i", video_path.get()])
            if duration.get():
                cmd.extend(["-t", duration.get()])
            cmd.append(output_path.get())
            subprocess.run(cmd, check=True)
            messagebox.showinfo("Success", "GIF created successfully")
        except subprocess.CalledProcessError:
            messagebox.showerror("Error", "An error occurred during GIF creation.")
        processing_label.config(text="")
        enable_widgets()

    if not video_path.get() or not output_path.get():
        messagebox.showerror("Error", "Please select input video and output GIF path.")
        return

    threading.Thread(target=process).start()

root = tk.Tk()
root.title("Video to GIF Creator")
root.geometry("400x350")

video_path = tk.StringVar()
output_path = tk.StringVar()
start_time = tk.StringVar()
duration = tk.StringVar()

tk.Label(root, text="Video to GIF Creator", font=("Helvetica", 16)).pack(pady=10)

tk.Button(root, text="Select Video", command=select_video).pack(pady=5)
tk.Entry(root, textvariable=video_path, width=50).pack(pady=5)

tk.Button(root, text="Select Output GIF", command=select_output).pack(pady=5)
tk.Entry(root, textvariable=output_path, width=50).pack(pady=5)

tk.Label(root, text="Start Time (e.g., 00:00:05)").pack(pady=2)
tk.Entry(root, textvariable=start_time, width=20).pack(pady=2)

tk.Label(root, text="Duration (seconds, e.g., 5)").pack(pady=2)
tk.Entry(root, textvariable=duration, width=20).pack(pady=2)

tk.Button(root, text="Create GIF", command=create_gif, bg="green", fg="white").pack(pady=10)

processing_label = tk.Label(root, text="", fg="blue")
processing_label.pack()

root.mainloop()
