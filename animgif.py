import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image


class GifMakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image to GIF Converter")
        self.root.geometry("550x550")
        self.root.resizable(True, True)

        self.image_paths = []

        self._build_ui()

    def _build_ui(self):
        # Top Frame - Buttons for File Management
        file_frame = ttk.LabelFrame(self.root, text=" 1. Manage Images ", padding=10)
        file_frame.pack(fill="x", padx=10, pady=5)

        btn_add = ttk.Button(file_frame, text="Add Images", command=self.add_images)
        btn_add.pack(side="left", padx=5)

        btn_remove = ttk.Button(file_frame, text="Remove Selected", command=self.remove_selected)
        btn_remove.pack(side="left", padx=5)

        btn_clear = ttk.Button(file_frame, text="Clear All", command=self.clear_all)
        btn_clear.pack(side="left", padx=5)

        # Listbox Frame - Display and Reorder Images
        list_frame = ttk.LabelFrame(self.root, text=" Image Order ", padding=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, yscrollcommand=scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        # Move Up/Down Buttons
        reorder_frame = ttk.Frame(list_frame)
        reorder_frame.pack(side="right", fill="y", padx=(5, 0))

        btn_up = ttk.Button(reorder_frame, text="▲ Move Up", command=self.move_up)
        btn_up.pack(pady=5)

        btn_down = ttk.Button(reorder_frame, text="▼ Move Down", command=self.move_down)
        btn_down.pack(pady=5)

        # Timing Settings Frame
        timing_frame = ttk.LabelFrame(self.root, text=" 2. Timing Options ", padding=10)
        timing_frame.pack(fill="x", padx=10, pady=5)

        self.mode_var = tk.StringVar(value="duration")

        # Duration Mode
        rb_duration = ttk.Radiobutton(
            timing_frame,
            text="Duration per frame (ms):",
            value="duration",
            variable=self.mode_var,
            command=self.toggle_mode
        )
        rb_duration.grid(row=0, column=0, sticky="w", pady=2)

        self.entry_duration = ttk.Entry(timing_frame, width=10)
        self.entry_duration.insert(0, "500")
        self.entry_duration.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        # FPS / Frequency Mode
        rb_fps = ttk.Radiobutton(
            timing_frame,
            text="Frame Rate (FPS / Hz):",
            value="fps",
            variable=self.mode_var,
            command=self.toggle_mode
        )
        rb_fps.grid(row=1, column=0, sticky="w", pady=2)

        self.entry_fps = ttk.Entry(timing_frame, width=10, state="disabled")
        self.entry_fps.insert(0, "2")
        self.entry_fps.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        # Loop Setting
        lbl_loop = ttk.Label(timing_frame, text="Loop Count (0 = Infinite):")
        lbl_loop.grid(row=2, column=0, sticky="w", pady=2)

        self.entry_loop = ttk.Entry(timing_frame, width=10)
        self.entry_loop.insert(0, "0")
        self.entry_loop.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        # Export Action Frame
        export_frame = ttk.Frame(self.root, padding=10)
        export_frame.pack(fill="x", padx=10, pady=5)

        btn_convert = ttk.Button(export_frame, text="Convert & Save GIF", command=self.create_gif)
        btn_convert.pack(fill="x", ipady=5)

    # --- UI Callbacks & Logic ---

    def add_images(self):
        files = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[
                ("Image Files", "*.png *.jpg *.jpeg *.bmp *.webp *.tiff"),
                ("All Files", "*.*")
            ]
        )
        for file in files:
            if file not in self.image_paths:
                self.image_paths.append(file)
                self.listbox.insert(tk.END, os.path.basename(file))

    def remove_selected(self):
        selected_idx = self.listbox.curselection()
        if selected_idx:
            idx = selected_idx[0]
            self.listbox.delete(idx)
            del self.image_paths[idx]

    def clear_all(self):
        self.listbox.delete(0, tk.END)
        self.image_paths.clear()

    def move_up(self):
        selected_idx = self.listbox.curselection()
        if selected_idx and selected_idx[0] > 0:
            idx = selected_idx[0]
            # Swap in memory
            self.image_paths[idx], self.image_paths[idx - 1] = self.image_paths[idx - 1], self.image_paths[idx]
            # Swap in Listbox
            filename = self.listbox.get(idx)
            self.listbox.delete(idx)
            self.listbox.insert(idx - 1, filename)
            self.listbox.selection_set(idx - 1)

    def move_down(self):
        selected_idx = self.listbox.curselection()
        if selected_idx and selected_idx[0] < len(self.image_paths) - 1:
            idx = selected_idx[0]
            # Swap in memory
            self.image_paths[idx], self.image_paths[idx + 1] = self.image_paths[idx + 1], self.image_paths[idx]
            # Swap in Listbox
            filename = self.listbox.get(idx)
            self.listbox.delete(idx)
            self.listbox.insert(idx + 1, filename)
            self.listbox.selection_set(idx + 1)

    def toggle_mode(self):
        if self.mode_var.get() == "duration":
            self.entry_duration.config(state="normal")
            self.entry_fps.config(state="disabled")
        else:
            self.entry_duration.config(state="disabled")
            self.entry_fps.config(state="normal")

    def get_duration_ms(self):
        mode = self.mode_var.get()
        if mode == "duration":
            duration = float(self.entry_duration.get())
            if duration <= 0:
                raise ValueError("Duration must be greater than 0.")
            return duration
        else:
            fps = float(self.entry_fps.get())
            if fps <= 0:
                raise ValueError("FPS must be greater than 0.")
            # Convert FPS (frequency) to duration per frame in milliseconds
            return 1000.0 / fps

    def create_gif(self):
        if not self.image_paths:
            messagebox.showwarning("No Images", "Please add at least one image.")
            return

        try:
            duration_ms = self.get_duration_ms()
            loop_count = int(self.entry_loop.get())
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please enter valid numeric parameters:\n{e}")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".gif",
            filetypes=[("GIF Files", "*.gif")],
            title="Save GIF As"
        )

        if not save_path:
            return

        try:
            # Load images using Pillow
            images = []
            for path in self.image_paths:
                img = Image.open(path)
                # Convert images with transparency/alpha channels to RGBA or RGB to avoid issues
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA")
                images.append(img)

            # Save as animated GIF using Pillow
            first_image = images[0]
            first_image.save(
                save_path,
                save_all=True,
                append_images=images[1:],
                duration=duration_ms,  # Duration per frame in milliseconds
                loop=loop_count,       # 0 means loop infinitely
                disposition=2          # Restore to background to handle transparency/clean frames
            )

            messagebox.showinfo("Success", f"GIF created successfully!\nSaved to: {save_path}")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while creating the GIF:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = GifMakerApp(root)
    root.mainloop()