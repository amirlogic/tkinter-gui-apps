import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

# Common Social Media Image Dimensions (Width x Height in px) based on standard guidelines
SOCIAL_MEDIA_SIZES = {
    "Custom": None,
    "Instagram Feed - Portrait (1080 x 1350)": (1080, 1350),
    "Instagram / FB Feed - Square (1080 x 1080)": (1080, 1080),
    "Instagram / FB Story / Reel (1080 x 1920)": (1080, 1920),
    "Facebook Feed - Landscape (1200 x 630)": (1200, 630),
    "Facebook Cover (851 x 315)": (851, 315),
    "X / Twitter Post (1600 x 900)": (1600, 900),
    "X / Twitter Header (1500 x 500)": (1500, 500),
    "LinkedIn Post (1200 x 627)": (1200, 627),
    "LinkedIn Banner (1584 x 396)": (1584, 396),
    "YouTube Thumbnail (1280 x 720)": (1280, 720),
    "Pinterest Pin (1000 x 1500)": (1000, 1500),
}


class ImageCropperApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Social Media Image Cropper")
        self.geometry("1100x750")

        # Image state variables
        self.image_path = None
        self.original_image = None
        self.display_image = None
        self.tk_image = None
        self.scale_factor = 1.0  # display / original scale

        # Overlay selection box coordinates (in canvas pixels)
        self.crop_x1 = 50
        self.crop_y1 = 50
        self.crop_x2 = 250
        self.crop_y2 = 250

        # Mouse interaction flags
        self.drag_data = {"x": 0, "y": 0, "anchor": None}
        self.HANDLE_SIZE = 8

        self._create_widgets()

    def _create_widgets(self):
        # --- Top Toolbar Frame ---
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        btn_open = ttk.Button(
            top_frame, text="Open Image", command=self.load_image
        )
        btn_open.pack(side=tk.LEFT, padx=(0, 15))

        # Size Dropdown
        ttk.Label(top_frame, text="Preset Size:").pack(
            side=tk.LEFT, padx=(0, 5)
        )
        self.combo_presets = ttk.Combobox(
            top_frame,
            values=list(SOCIAL_MEDIA_SIZES.keys()),
            state="readonly",
            width=38,
        )
        self.combo_presets.current(0)
        self.combo_presets.pack(side=tk.LEFT, padx=(0, 15))
        self.combo_presets.bind("<<ComboboxSelected>>", self.on_preset_change)

        # Custom Dimensions Inputs
        ttk.Label(top_frame, text="W:").pack(side=tk.LEFT)
        self.entry_width = ttk.Entry(top_frame, width=6)
        self.entry_width.pack(side=tk.LEFT, padx=(2, 8))

        ttk.Label(top_frame, text="H:").pack(side=tk.LEFT)
        self.entry_height = ttk.Entry(top_frame, width=6)
        self.entry_height.pack(side=tk.LEFT, padx=(2, 15))

        btn_apply_custom = ttk.Button(
            top_frame, text="Apply Custom", command=self.apply_custom_size
        )
        btn_apply_custom.pack(side=tk.LEFT, padx=(0, 15))

        # Backend Engine Toggle (Pillow vs ImageMagick v7)
        self.use_imagemagick = tk.BooleanVar(value=False)
        chk_im = ttk.Checkbutton(
            top_frame,
            text="Use ImageMagick v7 CLI",
            variable=self.use_imagemagick,
        )
        chk_im.pack(side=tk.LEFT, padx=(0, 15))

        btn_crop = ttk.Button(
            top_frame, text="Crop & Save", command=self.crop_and_save
        )
        btn_crop.pack(side=tk.RIGHT, padx=5)

        # --- Main Canvas Area ---
        self.canvas_frame = ttk.Frame(self)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#2b2b2b")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Canvas Mouse Events for moving/resizing crop area
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)

    def load_image(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.webp *.bmp *.tiff")
            ]
        )
        if not path:
            return

        self.image_path = path
        self.original_image = Image.open(path)
        self.redraw_canvas()

        # Default selection size on load
        self.entry_width.delete(0, tk.END)
        self.entry_width.insert(0, str(self.original_image.width))
        self.entry_height.delete(0, tk.END)
        self.entry_height.insert(0, str(self.original_image.height))

    def redraw_canvas(self):
        if not self.original_image:
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        if canvas_w < 10 or canvas_h < 10:
            canvas_w, canvas_h = 1000, 650

        # Calculate fit-scale factor for canvas preview
        orig_w, orig_h = self.original_image.size
        self.scale_factor = min(canvas_w / orig_w, canvas_h / orig_h, 1.0)

        disp_w = int(orig_w * self.scale_factor)
        disp_h = int(orig_h * self.scale_factor)

        # Resize image for view
        self.display_image = self.original_image.resize(
            (disp_w, disp_h), Image.Resampling.LANCZOS
        )
        self.tk_image = ImageTk.PhotoImage(self.display_image)

        self.canvas.delete("all")
        # Center image on canvas
        self.img_x_offset = (canvas_w - disp_w) // 2
        self.img_y_offset = (canvas_h - disp_h) // 2

        self.canvas.create_image(
            self.img_x_offset,
            self.img_y_offset,
            anchor=tk.NW,
            image=self.tk_image,
        )

        # Initialize crop overlay relative to image if not set
        if self.crop_x2 <= self.crop_x1:
            self.crop_x1 = self.img_x_offset + 20
            self.crop_y1 = self.img_y_offset + 20
            self.crop_x2 = self.img_x_offset + min(200, disp_w)
            self.crop_y2 = self.img_y_offset + min(200, disp_h)

        self.draw_crop_box()

    def draw_crop_box(self):
        self.canvas.delete("crop_overlay")

        # Rectangle outline & darkened background outside crop box
        x1, y1, x2, y2 = (
            self.crop_x1,
            self.crop_y1,
            self.crop_x2,
            self.crop_y2,
        )

        # Draw primary overlay rectangle
        self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline="#00ffcc",
            width=2,
            dash=(4, 4),
            tags="crop_overlay",
        )

        # Draw resize handles (corners)
        hs = self.HANDLE_SIZE
        handles = [
            (x1 - hs, y1 - hs, x1 + hs, y1 + hs),  # NW
            (x2 - hs, y1 - hs, x2 + hs, y1 + hs),  # NE
            (x1 - hs, y2 - hs, x1 + hs, y2 + hs),  # SW
            (x2 - hs, y2 - hs, x2 + hs, y2 + hs),  # SE
        ]
        for hx1, hy1, hx2, hy2 in handles:
            self.canvas.create_rectangle(
                hx1,
                hy1,
                hx2,
                hy2,
                fill="#00ffcc",
                outline="black",
                tags="crop_overlay",
            )

    def on_preset_change(self, event):
        selected_key = self.combo_presets.get()
        target_size = SOCIAL_MEDIA_SIZES.get(selected_key)

        if not target_size or not self.original_image:
            return

        target_w, target_h = target_size

        # Update text entries
        self.entry_width.delete(0, tk.END)
        self.entry_width.insert(0, str(target_w))
        self.entry_height.delete(0, tk.END)
        self.entry_height.insert(0, str(target_h))

        # Adjust selection box aspect ratio based on preset
        self._set_crop_box_aspect(target_w / target_h)

    def apply_custom_size(self):
        try:
            w = float(self.entry_width.get())
            h = float(self.entry_height.get())
            if w > 0 and h > 0:
                self._set_crop_box_aspect(w / h)
        except ValueError:
            messagebox.showerror(
                "Invalid Input", "Please enter valid numbers for Width/Height."
            )

    def _set_crop_box_aspect(self, aspect_ratio):
        """Sets the selection box aspect ratio on screen."""
        current_w = abs(self.crop_x2 - self.crop_x1)

        # Calculate new height from aspect ratio
        new_h = current_w / aspect_ratio

        # Check if box exceeds canvas boundaries
        canvas_h = self.canvas.winfo_height()
        if self.crop_y1 + new_h > canvas_h - 10:
            new_h = canvas_h - self.crop_y1 - 20
            current_w = new_h * aspect_ratio

        self.crop_x2 = self.crop_x1 + current_w
        self.crop_y2 = self.crop_y1 + new_h
        self.draw_crop_box()

    # --- Mouse Event Handlers for Moving & Resizing ---
    def on_mouse_down(self, event):
        x, y = event.x, event.y
        hs = self.HANDLE_SIZE + 4  # Click hit radius

        # Determine if click is on corner handles
        if abs(x - self.crop_x1) <= hs and abs(y - self.crop_y1) <= hs:
            anchor = "NW"
        elif abs(x - self.crop_x2) <= hs and abs(y - self.crop_y1) <= hs:
            anchor = "NE"
        elif abs(x - self.crop_x1) <= hs and abs(y - self.crop_y2) <= hs:
            anchor = "SW"
        elif abs(x - self.crop_x2) <= hs and abs(y - self.crop_y2) <= hs:
            anchor = "SE"
        elif (self.crop_x1 <= x <= self.crop_x2) and (
            self.crop_y1 <= y <= self.crop_y2
        ):
            anchor = "MOVE"
        else:
            anchor = None

        self.drag_data = {"x": x, "y": y, "anchor": anchor}

    def on_mouse_drag(self, event):
        anchor = self.drag_data["anchor"]
        if not anchor:
            return

        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]

        if anchor == "MOVE":
            self.crop_x1 += dx
            self.crop_y1 += dy
            self.crop_x2 += dx
            self.crop_y2 += dy
        elif anchor == "SE":
            self.crop_x2 += dx
            self.crop_y2 += dy
        elif anchor == "NW":
            self.crop_x1 += dx
            self.crop_y1 += dy
        elif anchor == "NE":
            self.crop_x2 += dx
            self.crop_y1 += dy
        elif anchor == "SW":
            self.crop_x1 += dx
            self.crop_y2 += dy

        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.draw_crop_box()

    # --- Crop Execution ---
    def crop_and_save(self):
        if not self.original_image or not self.image_path:
            messagebox.showwarning(
                "No Image Loaded", "Please open an image first."
            )
            return

        # Translate canvas overlay box coordinates back to full image pixel space
        box_x1 = max(0, self.crop_x1 - self.img_x_offset)
        box_y1 = max(0, self.crop_y1 - self.img_y_offset)
        box_x2 = self.crop_x2 - self.img_x_offset
        box_y2 = self.crop_y2 - self.img_y_offset

        # Normalize boundaries
        left = int(min(box_x1, box_x2) / self.scale_factor)
        top = int(min(box_y1, box_y2) / self.scale_factor)
        right = int(max(box_x1, box_x2) / self.scale_factor)
        bottom = int(max(box_y1, box_y2) / self.scale_factor)

        crop_w = max(1, right - left)
        crop_h = max(1, bottom - top)

        # Prompt user for output location
        ext = os.path.splitext(self.image_path)[1]
        out_path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[
                ("PNG Image", "*.png"),
                ("JPEG Image", "*.jpg"),
                ("All files", "*.*"),
            ],
        )

        if not out_path:
            return

        if self.use_imagemagick.get():
            # ImageMagick v7 Command Syntax: magick input.jpg -crop WxH+X+Y output.jpg
            cmd = [
                "magick",
                self.image_path,
                "-crop",
                f"{crop_w}x{crop_h}+{left}+{top}",
                "+repage",
                out_path,
            ]
            try:
                subprocess.run(cmd, check=True)
                messagebox.showinfo(
                    "Success",
                    f"Cropped with ImageMagick and saved to:\n{out_path}",
                )
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Failed running ImageMagick command:\n{e}\n\nEnsure ImageMagick v7 is installed and added to your system PATH.",
                )
        else:
            # Native Pillow Crop
            try:
                cropped_img = self.original_image.crop(
                    (left, top, right, bottom)
                )

                # Optional resize if preset target size specifies different target resolution
                selected_key = self.combo_presets.get()
                preset_dims = SOCIAL_MEDIA_SIZES.get(selected_key)
                if preset_dims:
                    cropped_img = cropped_img.resize(
                        preset_dims, Image.Resampling.LANCZOS
                    )

                cropped_img.save(out_path)
                messagebox.showinfo(
                    "Success", f"Image cropped and saved to:\n{out_path}"
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to crop image:\n{e}")


if __name__ == "__main__":
    app = ImageCropperApp()
    # Trigger redraw once Tkinter window is rendered to set initial dimensions
    app.after(100, app.redraw_canvas)
    app.mainloop()