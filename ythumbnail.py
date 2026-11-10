import os
import re
import sys
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk
import tkinter.font as tkfont
import xml.etree.ElementTree as ET


class YouTubeThumbnailStudio:

  def __init__(self, root):
    self.root = root
    self.root.title("YouTube Thumbnail Studio (SVG + Text)")
    self.root.geometry("1180x780")
    self.root.minsize(1000, 700)

    # Standard YouTube Thumbnail Resolution
    self.tb_width = 1280
    self.tb_height = 720

    # UI Preview Scale (1280x720 -> 768x432)
    self.scale = 0.6
    self.preview_width = int(self.tb_width * self.scale)
    self.preview_height = int(self.tb_height * self.scale)

    # Safely load system fonts
    try:
      self.available_fonts = sorted(list(set(tkfont.families(self.root))))
    except Exception:
      self.available_fonts = ["Arial", "Helvetica", "Times New Roman", "Courier"]

    # App State
    self.transparent_bg = tk.BooleanVar(value=False)
    self.bg_color = "#121212"
    self.elements = []
    self.selected_index = None
    self.drag_data = {"x": 0, "y": 0}

    self.create_widgets()
    self.redraw_canvas()

  def create_widgets(self):
    # Top Toolbar
    toolbar = tk.Frame(self.root, bg="#2d2d2d", padx=10, pady=8)
    toolbar.pack(side=tk.TOP, fill=tk.X)

    btn_add_svg = tk.Button(
        toolbar,
        text="📁 Add SVG",
        command=self.add_svg,
        bg="#0066cc",
        fg="white",
        font=("Arial", 10, "bold"),
        padx=10,
        pady=4,
    )
    btn_add_svg.pack(side=tk.LEFT, padx=5)

    btn_add_text = tk.Button(
        toolbar,
        text="✏️ Add Text",
        command=self.add_text,
        bg="#e67e22",
        fg="white",
        font=("Arial", 10, "bold"),
        padx=10,
        pady=4,
    )
    btn_add_text.pack(side=tk.LEFT, padx=5)

    btn_bg = tk.Button(
        toolbar,
        text="🎨 Background Color",
        command=self.change_background,
        bg="#444",
        fg="white",
        font=("Arial", 10),
        padx=10,
        pady=4,
    )
    btn_bg.pack(side=tk.LEFT, padx=5)

    chk_trans = tk.Checkbutton(
        toolbar,
        text="Transparent BG",
        variable=self.transparent_bg,
        command=self.on_transparent_toggle,
        bg="#2d2d2d",
        fg="white",
        selectcolor="#444",
        activebackground="#2d2d2d",
        activeforeground="white",
        font=("Arial", 9, "bold"),
    )
    chk_trans.pack(side=tk.LEFT, padx=15)

    btn_export = tk.Button(
        toolbar,
        text="💾 Export Master SVG (1280x720)",
        command=self.export_svg,
        bg="#28a745",
        fg="white",
        font=("Arial", 10, "bold"),
        padx=10,
        pady=4,
    )
    btn_export.pack(side=tk.RIGHT, padx=5)

    # Main Workspace Container
    main_container = tk.Frame(self.root, bg="#1e1e1e")
    main_container.pack(
        side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10
    )

    # Canvas Area (Center)
    canvas_frame = tk.Frame(main_container, bg="#1e1e1e")
    canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

    tk.Label(
        canvas_frame,
        text=f"Thumbnail Preview ({self.tb_width}x{self.tb_height} Canvas)",
        bg="#1e1e1e",
        fg="#aaa",
        font=("Arial", 9),
    ).pack(anchor="w", pady=(0, 4))

    self.canvas = tk.Canvas(
        canvas_frame,
        width=self.preview_width,
        height=self.preview_height,
        bg=self.bg_color,
        highlightthickness=1,
        highlightbackground="#444",
    )
    self.canvas.pack(anchor="nw")

    self.canvas.bind("<Button-1>", self.on_canvas_click)
    self.canvas.bind("<B1-Motion>", self.on_canvas_drag)

    # Sidebar Properties Panel (Right)
    self.sidebar = tk.Frame(
        main_container, bg="#252526", width=330, padx=15, pady=15
    )
    self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)
    self.sidebar.pack_propagate(False)

    tk.Label(
        self.sidebar,
        text="Element Properties",
        bg="#252526",
        fg="white",
        font=("Arial", 12, "bold"),
    ).pack(anchor="w", pady=(0, 15))

    self.prop_container = tk.Frame(self.sidebar, bg="#252526")
    self.prop_container.pack(fill=tk.BOTH, expand=True)

    self.build_empty_sidebar()

  def build_empty_sidebar(self):
    for widget in self.prop_container.winfo_children():
      widget.destroy()
    tk.Label(
        self.prop_container,
        text="No element selected.\nClick an SVG or Text on canvas.",
        bg="#252526",
        fg="#777",
        font=("Arial", 10),
        justify=tk.LEFT,
    ).pack(anchor="nw", pady=20)

  def add_svg(self):
    file_path = filedialog.askopenfilename(
        title="Select SVG File", filetypes=[("SVG Files", "*.svg")]
    )
    if not file_path:
      return

    try:
      with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

      inner_content, vb_w, vb_h = self.extract_svg_details(content)

      init_w, init_h = 350, 350
      init_x = (self.tb_width - init_w) // 2
      init_y = (self.tb_height - init_h) // 2

      element = {
          "type": "svg",
          "filename": os.path.basename(file_path),
          "inner_content": inner_content,
          "viewbox_w": vb_w,
          "viewbox_h": vb_h,
          "x": float(init_x),
          "y": float(init_y),
          "width": float(init_w),
          "height": float(init_h),
      }

      self.elements.append(element)
      self.selected_index = len(self.elements) - 1
      self.update_sidebar()
      self.redraw_canvas()

    except Exception as e:
      messagebox.showerror("Error", f"Could not read SVG file:\n{str(e)}")

  def add_text(self):
    init_x = self.tb_width / 2 - 250
    init_y = self.tb_height / 2 - 40

    default_font = (
        "Arial"
        if "Arial" in self.available_fonts
        else self.available_fonts[0]
    )

    element = {
        "type": "text",
        "text": "YOUR TITLE HERE",
        "font_family": default_font,
        "font_size": 64,
        "font_weight": "bold",
        "font_style": "normal",
        "fill": "#FFFFFF",
        "x": float(init_x),
        "y": float(init_y),
    }

    self.elements.append(element)
    self.selected_index = len(self.elements) - 1
    self.update_sidebar()
    self.redraw_canvas()

  def extract_svg_details(self, raw_svg):
    clean_svg = re.sub(r"<\?xml.*?\?>", "", raw_svg, flags=re.DOTALL)
    clean_svg = re.sub(r"<!DOCTYPE.*?>", "", clean_svg, flags=re.DOTALL).strip()
    vb_w, vb_h = 100.0, 100.0

    try:
      root_elem = ET.fromstring(clean_svg)
      viewbox = root_elem.attrib.get("viewBox") or root_elem.attrib.get(
          "viewbox"
      )
      if viewbox:
        parts = [float(p) for p in re.split(r"[\s,]+", viewbox.strip()) if p]
        if len(parts) == 4:
          vb_w, vb_h = parts[2], parts[3]
      else:
        w_str = root_elem.attrib.get("width", "100")
        h_str = root_elem.attrib.get("height", "100")
        vb_w = float(re.sub(r"[^\d.]", "", w_str) or 100)
        vb_h = float(re.sub(r"[^\d.]", "", h_str) or 100)

      inner = "".join(
          ET.tostring(child, encoding="unicode") for child in root_elem
      )
    except Exception:
      inner_match = re.search(
          r"<svg[^>]*>(.*?)</svg>", clean_svg, re.DOTALL | re.IGNORECASE
      )
      inner = inner_match.group(1) if inner_match else clean_svg

    return inner, vb_w, vb_h

  def on_transparent_toggle(self):
    if self.transparent_bg.get():
      self.canvas.config(bg="#333333")
    else:
      self.canvas.config(bg=self.bg_color)
    self.redraw_canvas()

  def change_background(self):
    color = colorchooser.askcolor(
        initialcolor=self.bg_color, title="Choose Background Color"
    )
    if color[1]:
      self.bg_color = color[1]
      self.transparent_bg.set(False)
      self.canvas.config(bg=self.bg_color)
      self.redraw_canvas()

  def redraw_canvas(self):
    self.canvas.delete("all")

    for idx, el in enumerate(self.elements):
      is_selected = idx == self.selected_index

      if el["type"] == "svg":
        x1 = el["x"] * self.scale
        y1 = el["y"] * self.scale
        x2 = (el["x"] + el["width"]) * self.scale
        y2 = (el["y"] + el["height"]) * self.scale

        box_color = "#00a2ff" if is_selected else "#666666"
        dash_style = (4, 4) if not is_selected else None

        self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            fill="#2a2d32",
            outline=box_color,
            width=2 if is_selected else 1,
            dash=dash_style,
        )

        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        label_text = (
            f"📄 {el['filename']}\n{int(el['width'])}x{int(el['height'])}"
        )
        self.canvas.create_text(
            center_x,
            center_y,
            text=label_text,
            fill="#ffffff",
            font=("Arial", 9, "bold"),
            justify=tk.CENTER,
        )

      elif el["type"] == "text":
        px = el["x"] * self.scale
        py = el["y"] * self.scale

        tk_weight = "bold" if el["font_weight"] == "bold" else "normal"
        preview_font_size = max(8, int(el["font_size"] * self.scale))

        try:
          font_tuple = (el["font_family"], preview_font_size, tk_weight)
        except Exception:
          font_tuple = ("Arial", preview_font_size, tk_weight)

        text_item = self.canvas.create_text(
            px,
            py,
            text=el["text"],
            fill=el["fill"],
            font=font_tuple,
            anchor="nw",
        )

        if is_selected:
          bbox = self.canvas.bbox(text_item)
          if bbox:
            pad = 4
            self.canvas.create_rectangle(
                bbox[0] - pad,
                bbox[1] - pad,
                bbox[2] + pad,
                bbox[3] + pad,
                outline="#00a2ff",
                width=2,
                dash=(4, 4),
            )

  def on_canvas_click(self, event):
    clicked_index = None
    for idx in range(len(self.elements) - 1, -1, -1):
      el = self.elements[idx]
      if el["type"] == "svg":
        ex1 = el["x"] * self.scale
        ey1 = el["y"] * self.scale
        ex2 = (el["x"] + el["width"]) * self.scale
        ey2 = (el["y"] + el["height"]) * self.scale
        if ex1 <= event.x <= ex2 and ey1 <= event.y <= ey2:
          clicked_index = idx
          break
      elif el["type"] == "text":
        px = el["x"] * self.scale
        py = el["y"] * self.scale
        approx_w = len(el["text"]) * (el["font_size"] * 0.5 * self.scale)
        approx_h = el["font_size"] * self.scale
        if (
            px <= event.x <= px + max(50, approx_w)
            and py <= event.y <= py + approx_h + 10
        ):
          clicked_index = idx
          break

    self.selected_index = clicked_index
    if self.selected_index is not None:
      self.drag_data["x"] = event.x
      self.drag_data["y"] = event.y

    self.update_sidebar()
    self.redraw_canvas()

  def on_canvas_drag(self, event):
    if self.selected_index is None:
      return

    dx = (event.x - self.drag_data["x"]) / self.scale
    dy = (event.y - self.drag_data["y"]) / self.scale

    self.drag_data["x"] = event.x
    self.drag_data["y"] = event.y

    el = self.elements[self.selected_index]
    el["x"] += dx
    el["y"] += dy

    self.update_sidebar_values()
    self.redraw_canvas()

  def update_sidebar(self):
    for widget in self.prop_container.winfo_children():
      widget.destroy()

    if (
        self.selected_index is None
        or not (0 <= self.selected_index < len(self.elements))
    ):
      self.build_empty_sidebar()
      return

    el = self.elements[self.selected_index]

    if el["type"] == "svg":
      tk.Label(
          self.prop_container,
          text="SVG Properties",
          bg="#252526",
          fg="#00a2ff",
          font=("Arial", 10, "bold"),
      ).pack(anchor="w", pady=(0, 10))

      self.x_var = tk.StringVar(value=str(int(el["x"])))
      self.y_var = tk.StringVar(value=str(int(el["y"])))
      self.w_var = tk.StringVar(value=str(int(el["width"])))
      self.h_var = tk.StringVar(value=str(int(el["height"])))

      self.create_prop_field("X Position (px):", self.x_var)
      self.create_prop_field("Y Position (px):", self.y_var)
      self.create_prop_field("Width (px):", self.w_var)
      self.create_prop_field("Height (px):", self.h_var)

    elif el["type"] == "text":
      tk.Label(
          self.prop_container,
          text="Text Properties",
          bg="#252526",
          fg="#e67e22",
          font=("Arial", 10, "bold"),
      ).pack(anchor="w", pady=(0, 10))

      tk.Label(
          self.prop_container, text="Text Content:", bg="#252526", fg="#ccc"
      ).pack(anchor="w")
      self.text_var = tk.StringVar(value=el["text"])
      text_entry = tk.Entry(
          self.prop_container, textvariable=self.text_var, width=28
      )
      text_entry.pack(anchor="w", pady=(2, 8))
      text_entry.bind("<Return>", self.apply_text_props)
      text_entry.bind("<FocusOut>", self.apply_text_props)

      tk.Label(
          self.prop_container, text="Font Family:", bg="#252526", fg="#ccc"
      ).pack(anchor="w")
      self.font_family_var = tk.StringVar(value=el["font_family"])
      font_combo = ttk.Combobox(
          self.prop_container,
          textvariable=self.font_family_var,
          values=self.available_fonts,
          state="readonly",
          width=26,
      )
      font_combo.pack(anchor="w", pady=(2, 8))
      font_combo.bind("<<ComboboxSelected>>", self.apply_text_props)

      self.font_size_var = tk.StringVar(value=str(int(el["font_size"])))
      self.create_prop_field("Font Size (px):", self.font_size_var)

      style_frame = tk.Frame(self.prop_container, bg="#252526")
      style_frame.pack(anchor="w", fill=tk.X, pady=(2, 8))

      self.bold_var = tk.BooleanVar(value=(el["font_weight"] == "bold"))
      chk_bold = tk.Checkbutton(
          style_frame,
          text="Bold",
          variable=self.bold_var,
          command=self.apply_text_props,
          bg="#252526",
          fg="white",
          selectcolor="#333",
          activebackground="#252526",
          activeforeground="white",
      )
      chk_bold.pack(side=tk.LEFT, padx=(0, 15))

      self.italic_var = tk.BooleanVar(value=(el["font_style"] == "italic"))
      chk_italic = tk.Checkbutton(
          style_frame,
          text="Italic",
          variable=self.italic_var,
          command=self.apply_text_props,
          bg="#252526",
          fg="white",
          selectcolor="#333",
          activebackground="#252526",
          activeforeground="white",
      )
      chk_italic.pack(side=tk.LEFT)

      color_frame = tk.Frame(self.prop_container, bg="#252526")
      color_frame.pack(anchor="w", fill=tk.X, pady=(2, 8))
      tk.Label(
          color_frame, text="Text Color:", bg="#252526", fg="#ccc"
      ).pack(side=tk.LEFT, padx=(0, 10))
      self.color_btn = tk.Button(
          color_frame,
          text=" Pick Color ",
          bg=el["fill"],
          fg="black" if self.is_color_light(el["fill"]) else "white",
          command=self.pick_text_color,
      )
      self.color_btn.pack(side=tk.LEFT)

      self.x_var = tk.StringVar(value=str(int(el["x"])))
      self.y_var = tk.StringVar(value=str(int(el["y"])))
      self.create_prop_field("X Position (px):", self.x_var)
      self.create_prop_field("Y Position (px):", self.y_var)

    btn_delete = tk.Button(
        self.prop_container,
        text="🗑️ Delete Element",
        command=self.delete_selected,
        bg="#d9534f",
        fg="white",
        font=("Arial", 9, "bold"),
    )
    btn_delete.pack(anchor="w", fill=tk.X, pady=(15, 0))

  def create_prop_field(self, label_text, var):
    tk.Label(
        self.prop_container, text=label_text, bg="#252526", fg="#ccc"
    ).pack(anchor="w")
    entry = tk.Entry(self.prop_container, textvariable=var, width=18)
    entry.pack(anchor="w", pady=(2, 8))
    entry.bind("<Return>", self.apply_props_from_entry)
    entry.bind("<FocusOut>", self.apply_props_from_entry)

  def update_sidebar_values(self):
    if (
        self.selected_index is not None
        and 0 <= self.selected_index < len(self.elements)
    ):
      el = self.elements[self.selected_index]
      if hasattr(self, "x_var"):
        self.x_var.set(str(int(el["x"])))
      if hasattr(self, "y_var"):
        self.y_var.set(str(int(el["y"])))

  def apply_props_from_entry(self, event=None):
    if (
        self.selected_index is not None
        and 0 <= self.selected_index < len(self.elements)
    ):
      try:
        el = self.elements[self.selected_index]
        el["x"] = float(self.x_var.get())
        el["y"] = float(self.y_var.get())
        if el["type"] == "svg":
          el["width"] = max(10, float(self.w_var.get()))
          el["height"] = max(10, float(self.h_var.get()))
        elif el["type"] == "text":
          el["font_size"] = max(6, float(self.font_size_var.get()))
        self.redraw_canvas()
      except ValueError:
        pass

  def apply_text_props(self, event=None):
    if (
        self.selected_index is not None
        and 0 <= self.selected_index < len(self.elements)
    ):
      el = self.elements[self.selected_index]
      if el["type"] == "text":
        el["text"] = self.text_var.get()
        el["font_family"] = self.font_family_var.get()
        el["font_weight"] = "bold" if self.bold_var.get() else "normal"
        el["font_style"] = "italic" if self.italic_var.get() else "normal"
        try:
          el["font_size"] = max(6, float(self.font_size_var.get()))
        except ValueError:
          pass
        self.redraw_canvas()

  def pick_text_color(self):
    if (
        self.selected_index is not None
        and 0 <= self.selected_index < len(self.elements)
    ):
      el = self.elements[self.selected_index]
      if el["type"] == "text":
        color = colorchooser.askcolor(
            initialcolor=el["fill"], title="Choose Text Color"
        )
        if color[1]:
          el["fill"] = color[1]
          self.color_btn.config(
              bg=el["fill"],
              fg="black" if self.is_color_light(el["fill"]) else "white",
          )
          self.redraw_canvas()

  def is_color_light(self, hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
      return False
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return brightness > 130

  def delete_selected(self):
    if (
        self.selected_index is not None
        and 0 <= self.selected_index < len(self.elements)
    ):
      del self.elements[self.selected_index]
      self.selected_index = None
      self.build_empty_sidebar()
      self.redraw_canvas()

  def export_svg(self):
    file_path = filedialog.asksaveasfilename(
        defaultextension=".svg",
        filetypes=[("SVG Vector Image", "*.svg")],
        initialfile="youtube_thumbnail.svg",
        title="Export Master SVG",
    )
    if not file_path:
      return

    svg_out = [
        '<svg xmlns="http://www.w3.org/2000/svg"'
        ' xmlns:xlink="http://www.w3.org/1999/xlink"'
        f' width="{self.tb_width}" height="{self.tb_height}" viewBox="0 0'
        f' {self.tb_width} {self.tb_height}">'
    ]

    if not self.transparent_bg.get():
      svg_out.append(
          f'<rect width="{self.tb_width}" height="{self.tb_height}"'
          f' fill="{self.bg_color}"/>'
      )

    for el in self.elements:
      if el["type"] == "svg":
        scale_x = el["width"] / el["viewbox_w"]
        scale_y = el["height"] / el["viewbox_h"]
        svg_out.append(
            f'<g transform="translate({el["x"]}, {el["y"]}) scale({scale_x},'
            f' {scale_y})">'
        )
        svg_out.append(el["inner_content"])
        svg_out.append("</g>")

      elif el["type"] == "text":
        escaped_text = (
            el["text"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        weight_attr = (
            f'font-weight="{el["font_weight"]}"'
            if el["font_weight"] == "bold"
            else ""
        )
        style_attr = (
            f'font-style="{el["font_style"]}"'
            if el["font_style"] == "italic"
            else ""
        )
        svg_out.append(
            f'<text x="{el["x"]}" y="{el["y"]}" font-family="{el["font_family"]}"'
            f' font-size="{el["font_size"]}" fill="{el["fill"]}" {weight_attr}'
            f' {style_attr} dominant-baseline="hanging">{escaped_text}</text>'
        )

    svg_out.append("</svg>")

    try:
      with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_out))
      messagebox.showinfo(
          "Export Successful",
          f"Master SVG saved to:\n{file_path}\n\nConvert to PNG using ImageMagick:"
          f'\nmagick convert "{file_path}" thumbnail.png',
      )
    except Exception as e:
      messagebox.showerror("Export Error", f"Failed to save SVG:\n{str(e)}")


if __name__ == "__main__":
  try:
    root = tk.Tk()
    app = YouTubeThumbnailStudio(root)
    root.mainloop()
  except Exception as e:
    print(f"An error occurred while launching the app: {e}")
    input("Press Enter to exit...")