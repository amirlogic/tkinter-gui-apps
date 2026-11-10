import os
import re
import io
import sys
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk
import tkinter.font as tkfont
import xml.etree.ElementTree as ET

# ── SVG rendering: try svglib+reportlab, then fall back to placeholder ──────
try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
    from PIL import Image, ImageTk
    SVG_RENDER = "svglib"
except ImportError:
    try:
        from PIL import Image, ImageTk
        SVG_RENDER = "pil_only"
    except ImportError:
        SVG_RENDER = "none"

# ── Resize handle constants ──────────────────────────────────────────────────
HANDLE_SIZE   = 8    # half-size of each corner/edge handle square
HANDLE_NAMES  = ["nw","n","ne","e","se","s","sw","w"]


def _handle_cursors():
    return {
        "nw": "size_nw_se", "se": "size_nw_se",
        "ne": "size_ne_sw", "sw": "size_ne_sw",
        "n":  "size_ns",    "s":  "size_ns",
        "e":  "size_we",    "w":  "size_we",
    }


# ── Colour helpers ───────────────────────────────────────────────────────────
def is_color_light(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return False
    r, g, b = int(hex_color[0:2],16), int(hex_color[2:4],16), int(hex_color[4:6],16)
    return (r*299 + g*587 + b*114)/1000 > 130


# ── Theme palette ────────────────────────────────────────────────────────────
C = {
    "bg":          "#17181c",
    "surface":     "#1f2128",
    "panel":       "#252830",
    "border":      "#35373f",
    "toolbar":     "#1a1b20",
    "accent":      "#4f8ef7",
    "accent2":     "#f0a500",
    "success":     "#3ecf6e",
    "danger":      "#e85555",
    "fg":          "#e2e4ec",
    "fg_dim":      "#7a7f96",
    "fg_muted":    "#4a4f63",
    "sel_outline": "#4f8ef7",
    "handle_fill": "#ffffff",
    "handle_out":  "#4f8ef7",
    "entry_bg":    "#2b2d38",
    "entry_fg":    "#dde0f0",
}

LABEL_FONT  = ("Segoe UI", 9)
HEADER_FONT = ("Segoe UI", 10, "bold")
MONO_FONT   = ("Consolas", 9)
TITLE_FONT  = ("Segoe UI", 11, "bold")


def styled_label(parent, text, fg=None, font=None, **kw):
    return tk.Label(parent, text=text,
                    bg=kw.pop("bg", C["panel"]),
                    fg=fg or C["fg_dim"],
                    font=font or LABEL_FONT, **kw)


def styled_entry(parent, textvariable, width=14):
    return tk.Entry(parent,
                    textvariable=textvariable,
                    width=width,
                    bg=C["entry_bg"],
                    fg=C["entry_fg"],
                    insertbackground=C["entry_fg"],
                    relief="flat",
                    highlightthickness=1,
                    highlightbackground=C["border"],
                    highlightcolor=C["accent"],
                    font=MONO_FONT)


def separator(parent, orient="h", **kw):
    if orient == "h":
        return tk.Frame(parent, height=1,
                        bg=C["border"], **kw)
    return tk.Frame(parent, width=1, bg=C["border"], **kw)


# ── SVG rasterisation helper ─────────────────────────────────────────────────
def rasterise_svg(svg_path, out_w, out_h):
    """Return a PIL Image of the SVG at (out_w × out_h), or None on failure."""
    out_w, out_h = max(1, int(out_w)), max(1, int(out_h))
    if SVG_RENDER == "svglib":
        try:
            drawing = svg2rlg(svg_path)
            if drawing is None:
                return None
            # scale to fit
            sx = out_w / drawing.width  if drawing.width  else 1
            sy = out_h / drawing.height if drawing.height else 1
            drawing.width  = out_w
            drawing.height = out_h
            drawing.transform = f"scale({sx},{sy})"
            buf = io.BytesIO()
            renderPM.drawToFile(drawing, buf, fmt="PNG")
            buf.seek(0)
            return Image.open(buf).convert("RGBA")
        except Exception:
            return None
    return None


class YouTubeThumbnailStudio:

    # ── Init ─────────────────────────────────────────────────────────────────
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Thumbnail Studio")
        self.root.geometry("1340x820")
        self.root.minsize(1100, 720)
        self.root.configure(bg=C["bg"])

        self.tb_width   = 1280
        self.tb_height  = 720
        self.scale      = 0.585          # 1280×720 → 749×421
        self.prev_w     = int(self.tb_width  * self.scale)
        self.prev_h     = int(self.tb_height * self.scale)

        try:
            self.available_fonts = sorted(set(tkfont.families(self.root)))
        except Exception:
            self.available_fonts = ["Arial","Helvetica","Times New Roman","Courier"]

        # state
        self.transparent_bg = tk.BooleanVar(value=False)
        self.bg_color  = "#121318"
        self.elements  = []            # list of dicts
        self.sel_idx   = None          # selected element index
        self._tk_images = {}           # keep refs: idx → PhotoImage

        # interaction state
        self._drag_mode   = None       # "move" | "resize"
        self._drag_handle = None       # e.g. "se"
        self._drag_start  = {}         # {mx,my, ox,oy,ow,oh}

        self._configure_ttk()
        self._build_ui()
        self.redraw_canvas()
        self._set_status("Ready  ·  Add SVG or Text to get started")

    # ── TTK style ─────────────────────────────────────────────────────────────
    def _configure_ttk(self):
        st = ttk.Style()
        st.theme_use("default")
        st.configure("TCombobox",
                     fieldbackground=C["entry_bg"],
                     background=C["entry_bg"],
                     foreground=C["entry_fg"],
                     selectbackground=C["accent"],
                     selectforeground="#fff",
                     relief="flat",
                     borderwidth=0)
        st.map("TCombobox",
               fieldbackground=[("readonly", C["entry_bg"])],
               foreground=[("readonly", C["entry_fg"])])
        st.configure("Vertical.TScrollbar",
                     background=C["panel"],
                     troughcolor=C["surface"],
                     borderwidth=0,
                     arrowcolor=C["fg_dim"])

    # ── UI skeleton ───────────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_toolbar()

        body = tk.Frame(self.root, bg=C["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6,0))

        # layers panel (left, narrow)
        self._build_layers_panel(body)

        # canvas (centre)
        self._build_canvas_area(body)

        # properties panel (right)
        self._build_sidebar(body)

        # status bar
        self._build_statusbar()

    # ── Toolbar ───────────────────────────────────────────────────────────────
    def _build_toolbar(self):
        bar = tk.Frame(self.root, bg=C["toolbar"], pady=7)
        bar.pack(fill=tk.X)

        def btn(parent, text, cmd, color, side=tk.LEFT):
            b = tk.Button(parent, text=text, command=cmd,
                          bg=color, fg="#fff",
                          font=("Segoe UI", 9, "bold"),
                          relief="flat", cursor="hand2",
                          padx=12, pady=5,
                          activebackground=color,
                          activeforeground="#fff",
                          bd=0)
            b.pack(side=side, padx=4)
            return b

        btn(bar, "＋ SVG",        self.add_svg,          C["accent"])
        btn(bar, "＋ Text",       self.add_text,         C["accent2"])

        separator(bar, orient="v").pack(side=tk.LEFT, fill=tk.Y,
                                        padx=8, pady=4)

        btn(bar, "🎨 Background", self.change_background, "#3a3c47")

        chk = tk.Checkbutton(bar, text="Transparent",
                             variable=self.transparent_bg,
                             command=self.on_transparent_toggle,
                             bg=C["toolbar"], fg=C["fg_dim"],
                             selectcolor=C["surface"],
                             activebackground=C["toolbar"],
                             activeforeground=C["fg"],
                             font=("Segoe UI", 9),
                             cursor="hand2")
        chk.pack(side=tk.LEFT, padx=(2, 8))

        # layer order buttons
        separator(bar, orient="v").pack(side=tk.LEFT, fill=tk.Y,
                                        padx=8, pady=4)
        btn(bar, "▲ Forward",  self.bring_forward,  "#3a3c47")
        btn(bar, "▼ Backward", self.send_backward,  "#3a3c47")

        btn(bar, "💾 Export SVG", self.export_svg, C["success"], side=tk.RIGHT)

    # ── Layers panel ─────────────────────────────────────────────────────────
    def _build_layers_panel(self, parent):
        pane = tk.Frame(parent, bg=C["panel"], width=170)
        pane.pack(side=tk.LEFT, fill=tk.Y, padx=(0,8))
        pane.pack_propagate(False)

        hdr = tk.Frame(pane, bg=C["surface"], pady=8, padx=10)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="LAYERS", bg=C["surface"],
                 fg=C["fg_dim"], font=("Segoe UI",8,"bold")).pack(anchor="w")

        self.layers_frame = tk.Frame(pane, bg=C["panel"])
        self.layers_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _refresh_layers(self):
        for w in self.layers_frame.winfo_children():
            w.destroy()

        for idx in range(len(self.elements)-1, -1, -1):
            el = self.elements[idx]
            is_sel = idx == self.sel_idx
            icon  = "◈" if el["type"]=="svg" else "T"
            label = el.get("filename", el.get("text",""))[:18]
            bg    = C["accent"] if is_sel else C["surface"]
            fg    = "#fff"      if is_sel else C["fg_dim"]

            row = tk.Frame(self.layers_frame, bg=bg,
                           cursor="hand2", pady=4)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f" {icon}  {label}",
                     bg=bg, fg=fg,
                     font=("Segoe UI",9),
                     anchor="w").pack(fill=tk.X, padx=6)

            row.bind("<Button-1>", lambda e, i=idx: self._select(i))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, i=idx: self._select(i))

    # ── Canvas ────────────────────────────────────────────────────────────────
    def _build_canvas_area(self, parent):
        area = tk.Frame(parent, bg=C["bg"])
        area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,8))

        # label row
        lbl_row = tk.Frame(area, bg=C["bg"])
        lbl_row.pack(fill=tk.X, pady=(0,5))
        tk.Label(lbl_row, text=f"Preview  {self.tb_width}×{self.tb_height}",
                 bg=C["bg"], fg=C["fg_dim"],
                 font=("Segoe UI",8,"bold")).pack(side=tk.LEFT)

        # checkerboard frame  (shows transparency)
        canvas_outer = tk.Frame(area, bg=C["border"],
                                padx=1, pady=1)
        canvas_outer.pack(anchor="nw")

        self.canvas = tk.Canvas(canvas_outer,
                                width=self.prev_w,
                                height=self.prev_h,
                                bg=self.bg_color,
                                highlightthickness=0,
                                cursor="crosshair")
        self.canvas.pack()

        self.canvas.bind("<Button-1>",         self._on_press)
        self.canvas.bind("<B1-Motion>",         self._on_drag)
        self.canvas.bind("<ButtonRelease-1>",   self._on_release)
        self.canvas.bind("<Motion>",            self._on_hover)
        self.canvas.bind("<Delete>",            lambda e: self.delete_selected())
        self.canvas.bind("<BackSpace>",         lambda e: self.delete_selected())
        self.canvas.focus_set()

    # ── Sidebar / properties ──────────────────────────────────────────────────
    def _build_sidebar(self, parent):
        self.sidebar = tk.Frame(parent, bg=C["panel"], width=290)
        self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        hdr = tk.Frame(self.sidebar, bg=C["surface"], pady=8, padx=14)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="PROPERTIES", bg=C["surface"],
                 fg=C["fg_dim"], font=("Segoe UI",8,"bold")).pack(anchor="w")

        # scrollable inner
        outer = tk.Frame(self.sidebar, bg=C["panel"])
        outer.pack(fill=tk.BOTH, expand=True)

        self._sb_canvas = tk.Canvas(outer, bg=C["panel"],
                                    highlightthickness=0,
                                    bd=0)
        self._sb_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(outer, orient="vertical",
                                  command=self._sb_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._sb_canvas.configure(yscrollcommand=scrollbar.set)

        self.prop_container = tk.Frame(self._sb_canvas, bg=C["panel"])
        self._sb_win = self._sb_canvas.create_window(
            (0,0), window=self.prop_container, anchor="nw")

        self.prop_container.bind("<Configure>", self._on_prop_configure)
        self._sb_canvas.bind("<Configure>", self._on_sb_canvas_configure)

        self._build_empty_sidebar()

    def _on_prop_configure(self, event):
        self._sb_canvas.configure(
            scrollregion=self._sb_canvas.bbox("all"))

    def _on_sb_canvas_configure(self, event):
        self._sb_canvas.itemconfig(self._sb_win, width=event.width)

    # ── Status bar ────────────────────────────────────────────────────────────
    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg=C["toolbar"], pady=4)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        self._status_var = tk.StringVar(value="")
        tk.Label(bar, textvariable=self._status_var,
                 bg=C["toolbar"], fg=C["fg_muted"],
                 font=("Segoe UI",8),
                 anchor="w", padx=12).pack(side=tk.LEFT)
        render_lbl = f"SVG renderer: {SVG_RENDER}"
        tk.Label(bar, text=render_lbl,
                 bg=C["toolbar"], fg=C["fg_muted"],
                 font=("Segoe UI",8),
                 padx=12).pack(side=tk.RIGHT)

    def _set_status(self, msg):
        self._status_var.set(msg)

    # ── Layer ordering ────────────────────────────────────────────────────────
    def bring_forward(self):
        if self.sel_idx is None: return
        idx = self.sel_idx
        if idx < len(self.elements)-1:
            self.elements[idx], self.elements[idx+1] = \
                self.elements[idx+1], self.elements[idx]
            self.sel_idx = idx+1
            self._finish_interaction()

    def send_backward(self):
        if self.sel_idx is None: return
        idx = self.sel_idx
        if idx > 0:
            self.elements[idx], self.elements[idx-1] = \
                self.elements[idx-1], self.elements[idx]
            self.sel_idx = idx-1
            self._finish_interaction()

    # ── Add elements ──────────────────────────────────────────────────────────
    def add_svg(self):
        path = filedialog.askopenfilename(
            title="Select SVG File",
            filetypes=[("SVG Files","*.svg")])
        if not path:
            return
        try:
            with open(path,"r",encoding="utf-8") as f:
                content = f.read()
            inner, vb_w, vb_h = self._extract_svg_details(content)
            init_w = min(400, self.tb_width//2)
            init_h = int(init_w * (vb_h/vb_w)) if vb_w else init_w
            el = {
                "type":         "svg",
                "filename":     os.path.basename(path),
                "filepath":     path,
                "inner_content":inner,
                "viewbox_w":    vb_w,
                "viewbox_h":    vb_h,
                "x":   float((self.tb_width  - init_w) // 2),
                "y":   float((self.tb_height - init_h) // 2),
                "width":  float(init_w),
                "height": float(init_h),
                "_img_cache": {},      # (w,h) → PhotoImage
                "lock_ar":    True,    # lock aspect ratio during resize
            }
            self.elements.append(el)
            self.sel_idx = len(self.elements)-1
            self._finish_interaction()
            self._set_status(f"Added  {el['filename']}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not read SVG:\n{e}")

    def add_text(self):
        default_font = "Arial" if "Arial" in self.available_fonts \
                       else self.available_fonts[0]
        el = {
            "type":        "text",
            "text":        "YOUR TITLE HERE",
            "font_family": default_font,
            "font_size":   64,
            "font_weight": "bold",
            "font_style":  "normal",
            "fill":        "#FFFFFF",
            "x":   float(self.tb_width  / 2 - 250),
            "y":   float(self.tb_height / 2 - 40),
        }
        self.elements.append(el)
        self.sel_idx = len(self.elements)-1
        self._finish_interaction()
        self._set_status("Added text element")

    # ── SVG parsing ───────────────────────────────────────────────────────────
    def _extract_svg_details(self, raw):
        clean = re.sub(r"<\?xml.*?\?>", "", raw, flags=re.DOTALL)
        clean = re.sub(r"<!DOCTYPE.*?>", "", clean, flags=re.DOTALL).strip()
        vb_w, vb_h = 100.0, 100.0
        try:
            root_el = ET.fromstring(clean)
            vb = root_el.attrib.get("viewBox") or root_el.attrib.get("viewbox")
            if vb:
                parts = [float(p) for p in re.split(r"[\s,]+", vb.strip()) if p]
                if len(parts)==4:
                    vb_w, vb_h = parts[2], parts[3]
            else:
                vb_w = float(re.sub(r"[^\d.]","", root_el.attrib.get("width","100")) or 100)
                vb_h = float(re.sub(r"[^\d.]","", root_el.attrib.get("height","100")) or 100)
            inner = "".join(ET.tostring(c, encoding="unicode") for c in root_el)
        except Exception:
            m = re.search(r"<svg[^>]*>(.*?)</svg>", clean, re.DOTALL|re.IGNORECASE)
            inner = m.group(1) if m else clean
        return inner, vb_w, vb_h

    # ── Background ────────────────────────────────────────────────────────────
    def on_transparent_toggle(self):
        self.canvas.config(bg="#2d2f38" if self.transparent_bg.get()
                           else self.bg_color)
        self.redraw_canvas()

    def change_background(self):
        c = colorchooser.askcolor(initialcolor=self.bg_color,
                                  title="Background Color")
        if c[1]:
            self.bg_color = c[1]
            self.transparent_bg.set(False)
            self.canvas.config(bg=self.bg_color)
            self.redraw_canvas()

    # ── Selection helper ──────────────────────────────────────────────────────
    def _select(self, idx):
        self.sel_idx = idx
        self._finish_interaction()

    def _el_bounds(self, el):
        """Return (x1,y1,x2,y2) in CANVAS (scaled) coords.
        Uses live bbox for text when available (set during redraw)."""
        if el["type"] == "svg":
            x1 = el["x"] * self.scale
            y1 = el["y"] * self.scale
            x2 = (el["x"] + el["width"])  * self.scale
            y2 = (el["y"] + el["height"]) * self.scale
            return x1, y1, x2, y2
        elif el["type"] == "text":
            x1 = el["x"] * self.scale
            y1 = el["y"] * self.scale
            x2 = el.get("_live_x2", x1 + len(el["text"]) *
                         el["font_size"] * 0.58 * self.scale)
            y2 = el.get("_live_y2", y1 + el["font_size"] * self.scale)
            return x1, y1, x2, y2
        return 0,0,0,0

    # ── Handle geometry ───────────────────────────────────────────────────────
    def _handle_positions(self, x1, y1, x2, y2):
        mx, my = (x1+x2)/2, (y1+y2)/2
        return {
            "nw":(x1,y1), "n":(mx,y1), "ne":(x2,y1),
            "e": (x2,my),
            "se":(x2,y2), "s":(mx,y2), "sw":(x1,y2),
            "w": (x1,my),
        }

    def _hit_handle(self, x1,y1,x2,y2, mx,my):
        """Return handle name or None."""
        H = HANDLE_SIZE
        for name,(hx,hy) in self._handle_positions(x1,y1,x2,y2).items():
            if abs(mx-hx)<=H and abs(my-hy)<=H:
                return name
        return None

    def _hit_element(self, ex, ey):
        """Return index of topmost element under canvas point, or None."""
        for idx in range(len(self.elements)-1,-1,-1):
            el = self.elements[idx]
            x1,y1,x2,y2 = self._el_bounds(el)
            if x1<=ex<=x2 and y1<=ey<=y2:
                return idx
        return None

    # ── Mouse interaction ─────────────────────────────────────────────────────
    def _on_press(self, event):
        self.canvas.focus_set()
        mx, my = event.x, event.y

        # check resize handles on selected element first
        if self.sel_idx is not None:
            el = self.elements[self.sel_idx]
            x1,y1,x2,y2 = self._el_bounds(el)
            h = self._hit_handle(x1,y1,x2,y2, mx,my)
            if h:
                self._drag_mode   = "resize"
                self._drag_handle = h
                self._drag_start  = dict(mx=mx, my=my,
                                         ox=el["x"], oy=el["y"],
                                         ow=el.get("width",0),
                                         oh=el.get("height",0))
                return

        # check element body
        idx = self._hit_element(mx, my)
        self.sel_idx = idx
        if idx is not None:
            el = self.elements[idx]
            self._drag_mode  = "move"
            self._drag_start = dict(mx=mx, my=my,
                                    ox=el["x"], oy=el["y"])
        else:
            self._drag_mode = None

        self._finish_interaction()

    def _on_drag(self, event):
        if self._drag_mode is None or self.sel_idx is None:
            return
        el = self.elements[self.sel_idx]
        dx = (event.x - self._drag_start["mx"]) / self.scale
        dy = (event.y - self._drag_start["my"]) / self.scale

        if self._drag_mode == "move":
            el["x"] = self._drag_start["ox"] + dx
            el["y"] = self._drag_start["oy"] + dy

        elif self._drag_mode == "resize" and el["type"] == "svg":
            h = self._drag_handle
            ox  = self._drag_start["ox"]
            oy  = self._drag_start["oy"]
            ow  = self._drag_start["ow"]
            oh  = self._drag_start["oh"]
            ar  = ow / oh if oh else 1.0

            new_x, new_y = ox, oy
            new_w, new_h = ow, oh

            if "e" in h: new_w = max(20, ow + dx)
            if "s" in h: new_h = max(20, oh + dy)
            if "w" in h:
                new_w = max(20, ow - dx)
                new_x = ox + (ow - new_w)
            if "n" in h:
                new_h = max(20, oh - dy)
                new_y = oy + (oh - new_h)

            # apply aspect-ratio lock
            if el.get("lock_ar", True):
                if h in ("e", "w"):
                    # width is leading — derive height
                    new_h = new_w / ar
                    if "n" in h:
                        new_y = oy + (oh - new_h)
                elif h in ("n", "s"):
                    # height is leading — derive width
                    new_w = new_h * ar
                    if "w" in h:
                        new_x = ox + (ow - new_w)
                else:
                    # corner handle — use whichever axis moved more
                    if abs(dx) >= abs(dy):
                        new_h = new_w / ar
                        if "n" in h:
                            new_y = oy + (oh - new_h)
                    else:
                        new_w = new_h * ar
                        if "w" in h:
                            new_x = ox + (ow - new_w)

            el["x"], el["y"] = new_x, new_y
            el["width"], el["height"] = new_w, new_h

        self._update_sidebar_values()
        self.redraw_canvas()

    def _on_release(self, event):
        if self._drag_mode == "resize":
            # invalidate cached image so it re-renders at new size
            if self.sel_idx is not None:
                el = self.elements[self.sel_idx]
                if "_img_cache" in el:
                    el["_img_cache"].clear()
            self.redraw_canvas()
        self._drag_mode   = None
        self._drag_handle = None

    def _on_hover(self, event):
        mx, my = event.x, event.y
        cursor = "crosshair"
        if self.sel_idx is not None:
            el = self.elements[self.sel_idx]
            x1,y1,x2,y2 = self._el_bounds(el)
            h = self._hit_handle(x1,y1,x2,y2, mx,my)
            if h:
                cursor = _handle_cursors().get(h, "crosshair")
            elif x1<=mx<=x2 and y1<=my<=y2:
                cursor = "fleur"
        self.canvas.configure(cursor=cursor)

    # ── Draw ──────────────────────────────────────────────────────────────────
    def redraw_canvas(self):
        self.canvas.delete("all")
        H = HANDLE_SIZE

        for idx, el in enumerate(self.elements):
            is_sel = idx == self.sel_idx

            if el["type"] == "svg":
                x1 = el["x"] * self.scale
                y1 = el["y"] * self.scale
                px_w = max(1, int(el["width"]  * self.scale))
                px_h = max(1, int(el["height"] * self.scale))
                x2, y2 = x1 + px_w, y1 + px_h

                # ── try rasterised preview ──
                rendered = False
                if SVG_RENDER == "svglib" and "filepath" in el:
                    cache_key = (px_w, px_h)
                    if cache_key not in el["_img_cache"]:
                        pil_img = rasterise_svg(el["filepath"], px_w, px_h)
                        if pil_img:
                            el["_img_cache"][cache_key] = ImageTk.PhotoImage(pil_img)
                    tkimg = el["_img_cache"].get(cache_key)
                    if tkimg:
                        self.canvas.create_image(x1, y1, anchor="nw", image=tkimg)
                        rendered = True

                # ── placeholder if no render ──
                if not rendered:
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2,
                        fill="#23262f", outline="#444",
                        width=1)
                    self.canvas.create_text(
                        (x1+x2)/2, (y1+y2)/2,
                        text=f"⬜  {el['filename']}\n{int(el['width'])}×{int(el['height'])}",
                        fill="#5a5f7a", font=("Segoe UI",8),
                        justify=tk.CENTER)

                # ── selection outline ──
                if is_sel:
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2,
                        outline=C["sel_outline"], width=2,
                        fill="")
                    for hx, hy in self._handle_positions(x1,y1,x2,y2).values():
                        self.canvas.create_rectangle(
                            hx-H, hy-H, hx+H, hy+H,
                            fill=C["handle_fill"],
                            outline=C["handle_out"], width=1)

            elif el["type"] == "text":
                px = el["x"] * self.scale
                py = el["y"] * self.scale
                fs = max(8, int(el["font_size"] * self.scale))
                weight = "bold"   if el["font_weight"] == "bold"   else "normal"
                slant  = "italic" if el["font_style"]  == "italic" else "roman"
                try:
                    fnt = tkfont.Font(family=el["font_family"],
                                      size=fs, weight=weight, slant=slant)
                except Exception:
                    fnt = tkfont.Font(family="Arial", size=fs)

                tid = self.canvas.create_text(
                    px, py, text=el["text"],
                    fill=el["fill"], font=fnt, anchor="nw")

                if is_sel:
                    bb = self.canvas.bbox(tid)
                    if bb:
                        pad = 4
                        x1b = bb[0]-pad; y1b = bb[1]-pad
                        x2b = bb[2]+pad; y2b = bb[3]+pad
                        self.canvas.create_rectangle(
                            x1b, y1b, x2b, y2b,
                            outline=C["sel_outline"], width=2,
                            dash=(5,3), fill="")
                        for hx,hy in self._handle_positions(
                                x1b,y1b,x2b,y2b).values():
                            self.canvas.create_rectangle(
                                hx-H, hy-H, hx+H, hy+H,
                                fill=C["handle_fill"],
                                outline=C["handle_out"], width=1)
                        # update live bounds for hit-testing
                        el["_live_x2"] = (x2b+pad) / self.scale
                        el["_live_y2"] = (y2b+pad) / self.scale

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _build_empty_sidebar(self):
        for w in self.prop_container.winfo_children():
            w.destroy()
        tk.Label(self.prop_container,
                 text="No element selected",
                 bg=C["panel"], fg=C["fg_muted"],
                 font=("Segoe UI",9)).pack(anchor="nw",
                                          padx=14, pady=16)

    def _section_label(self, text):
        f = tk.Frame(self.prop_container, bg=C["panel"])
        f.pack(fill=tk.X, padx=14, pady=(14,4))
        tk.Label(f, text=text.upper(),
                 bg=C["panel"], fg=C["fg_dim"],
                 font=("Segoe UI",7,"bold")).pack(anchor="w")
        separator(f).pack(fill=tk.X, pady=(3,0))

    def _prop_row(self, label, var, apply_cmd=None):
        """Two-column label+entry row inside prop_container."""
        row = tk.Frame(self.prop_container, bg=C["panel"])
        row.pack(fill=tk.X, padx=14, pady=2)
        tk.Label(row, text=label, width=12, anchor="w",
                 bg=C["panel"], fg=C["fg_dim"],
                 font=("Segoe UI",8)).grid(row=0, column=0, sticky="w")
        e = styled_entry(row, var)
        e.grid(row=0, column=1, sticky="ew", padx=(4,0))
        row.columnconfigure(1, weight=1)
        cmd = apply_cmd or self._apply_props
        e.bind("<Return>",   lambda _: cmd())
        e.bind("<FocusOut>", lambda _: cmd())
        return e

    def update_sidebar(self):
        for w in self.prop_container.winfo_children():
            w.destroy()

        if self.sel_idx is None or \
                not (0 <= self.sel_idx < len(self.elements)):
            self._build_empty_sidebar()
            self._refresh_layers()
            return

        el = self.elements[self.sel_idx]

        if el["type"] == "svg":
            self._section_label("SVG Element")
            fn_row = tk.Frame(self.prop_container, bg=C["panel"])
            fn_row.pack(fill=tk.X, padx=14, pady=(0,8))
            tk.Label(fn_row, text=el["filename"],
                     bg=C["panel"], fg=C["fg_dim"],
                     font=("Segoe UI",8),
                     wraplength=220, anchor="w").pack(anchor="w")

            self._section_label("Position & Size")
            self.x_var = tk.StringVar(value=str(int(el["x"])))
            self.y_var = tk.StringVar(value=str(int(el["y"])))
            self.w_var = tk.StringVar(value=str(int(el["width"])))
            self.h_var = tk.StringVar(value=str(int(el["height"])))
            self._prop_row("X (px)", self.x_var)
            self._prop_row("Y (px)", self.y_var)
            self._prop_row("Width",  self.w_var)
            self._prop_row("Height", self.h_var)

            # lock aspect ratio toggle — persisted on the element
            self.lock_ar = tk.BooleanVar(value=el.get("lock_ar", True))
            def _on_lock_toggle():
                self.elements[self.sel_idx]["lock_ar"] = self.lock_ar.get()
            lock_row = tk.Frame(self.prop_container, bg=C["panel"])
            lock_row.pack(fill=tk.X, padx=14, pady=(6,2))
            tk.Checkbutton(lock_row, text="🔒  Lock aspect ratio",
                           variable=self.lock_ar,
                           command=_on_lock_toggle,
                           bg=C["panel"], fg=C["fg_dim"],
                           selectcolor=C["surface"],
                           activebackground=C["panel"],
                           activeforeground=C["fg"],
                           font=("Segoe UI",8),
                           cursor="hand2").pack(anchor="w")

        elif el["type"] == "text":
            self._section_label("Text Content")
            self.text_var = tk.StringVar(value=el["text"])
            tf = tk.Frame(self.prop_container, bg=C["panel"])
            tf.pack(fill=tk.X, padx=14, pady=(0,8))
            te = styled_entry(tf, self.text_var, width=28)
            te.pack(fill=tk.X)
            te.bind("<Return>",   lambda _: self._apply_text())
            te.bind("<FocusOut>", lambda _: self._apply_text())

            self._section_label("Font")
            self.font_family_var = tk.StringVar(value=el["font_family"])
            ff = tk.Frame(self.prop_container, bg=C["panel"])
            ff.pack(fill=tk.X, padx=14, pady=(0,6))
            cb = ttk.Combobox(ff, textvariable=self.font_family_var,
                              values=self.available_fonts,
                              state="readonly", width=24)
            cb.pack(fill=tk.X)
            cb.bind("<<ComboboxSelected>>", lambda _: self._apply_text())

            self.font_size_var = tk.StringVar(value=str(int(el["font_size"])))
            self._prop_row("Size (px)", self.font_size_var, self._apply_text)

            style_row = tk.Frame(self.prop_container, bg=C["panel"])
            style_row.pack(fill=tk.X, padx=14, pady=(4,8))
            self.bold_var   = tk.BooleanVar(value=(el["font_weight"]=="bold"))
            self.italic_var = tk.BooleanVar(value=(el["font_style"]=="italic"))
            for text, var in [("Bold",self.bold_var),("Italic",self.italic_var)]:
                tk.Checkbutton(style_row, text=text, variable=var,
                               command=self._apply_text,
                               bg=C["panel"], fg=C["fg"],
                               selectcolor=C["surface"],
                               activebackground=C["panel"],
                               activeforeground=C["fg"],
                               font=("Segoe UI",9),
                               cursor="hand2").pack(side=tk.LEFT, padx=(0,12))

            self._section_label("Color")
            clr_row = tk.Frame(self.prop_container, bg=C["panel"])
            clr_row.pack(fill=tk.X, padx=14, pady=(0,8))
            self._clr_swatch = tk.Frame(clr_row, bg=el["fill"],
                                        width=22, height=22,
                                        relief="flat", cursor="hand2")
            self._clr_swatch.pack(side=tk.LEFT, padx=(0,8))
            self._clr_swatch.bind("<Button-1>", lambda _: self.pick_text_color())
            self._clr_label = tk.Label(clr_row, text=el["fill"].upper(),
                                       bg=C["panel"], fg=C["fg_dim"],
                                       font=MONO_FONT)
            self._clr_label.pack(side=tk.LEFT)

            self._section_label("Position")
            self.x_var = tk.StringVar(value=str(int(el["x"])))
            self.y_var = tk.StringVar(value=str(int(el["y"])))
            self._prop_row("X (px)", self.x_var, self._apply_text)
            self._prop_row("Y (px)", self.y_var, self._apply_text)

        # delete button at the bottom
        separator(self.prop_container).pack(fill=tk.X, padx=14, pady=(16,8))
        del_btn = tk.Button(self.prop_container,
                            text="Delete Element",
                            command=self.delete_selected,
                            bg=C["danger"], fg="#fff",
                            font=("Segoe UI",9,"bold"),
                            relief="flat", cursor="hand2",
                            padx=10, pady=6,
                            activebackground="#cc3333",
                            activeforeground="#fff", bd=0)
        del_btn.pack(fill=tk.X, padx=14, pady=(0,14))

        self._refresh_layers()

    def _update_sidebar_values(self):
        if self.sel_idx is None: return
        el = self.elements[self.sel_idx]
        for attr, var in [("x","x_var"),("y","y_var")]:
            if hasattr(self, var):
                getattr(self, var).set(str(int(el[attr])))
        if el["type"]=="svg":
            for attr, var in [("width","w_var"),("height","h_var")]:
                if hasattr(self, var):
                    getattr(self, var).set(str(int(el[attr])))

    def _apply_props(self):
        if self.sel_idx is None: return
        el = self.elements[self.sel_idx]
        try:
            el["x"] = float(self.x_var.get())
            el["y"] = float(self.y_var.get())
            if el["type"]=="svg":
                new_w = max(10, float(self.w_var.get()))
                new_h = max(10, float(self.h_var.get()))
                if el.get("lock_ar", True):
                    if new_w != el["width"]:
                        new_h = new_w * (el["height"] / el["width"])
                    elif new_h != el["height"]:
                        new_w = new_h * (el["width"] / el["height"])
                el["width"], el["height"] = new_w, new_h
                if "_img_cache" in el: el["_img_cache"].clear()
            self.redraw_canvas()
        except ValueError:
            pass

    def _apply_text(self):
        if self.sel_idx is None: return
        el = self.elements[self.sel_idx]
        if el["type"]!="text": return
        el["text"]        = self.text_var.get()
        el["font_family"] = self.font_family_var.get()
        el["font_weight"] = "bold"   if self.bold_var.get()   else "normal"
        el["font_style"]  = "italic" if self.italic_var.get() else "normal"
        try:
            el["x"] = float(self.x_var.get())
            el["y"] = float(self.y_var.get())
            el["font_size"] = max(6, float(self.font_size_var.get()))
        except ValueError:
            pass
        self.redraw_canvas()

    def pick_text_color(self):
        if self.sel_idx is None: return
        el = self.elements[self.sel_idx]
        if el["type"]!="text": return
        c = colorchooser.askcolor(initialcolor=el["fill"],
                                  title="Text Color")
        if c[1]:
            el["fill"] = c[1]
            self._clr_swatch.config(bg=el["fill"])
            self._clr_label.config(text=el["fill"].upper())
            self.redraw_canvas()

    def delete_selected(self):
        if self.sel_idx is None: return
        del self.elements[self.sel_idx]
        self.sel_idx = None
        self._build_empty_sidebar()
        self._refresh_layers()
        self.redraw_canvas()
        self._set_status("Element deleted")

    # ── Finish interaction (sidebar + layers + redraw) ────────────────────────
    def _finish_interaction(self):
        self.update_sidebar()
        self.redraw_canvas()

    # ── Export ────────────────────────────────────────────────────────────────
    def export_svg(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG Vector Image","*.svg")],
            initialfile="youtube_thumbnail.svg",
            title="Export SVG")
        if not path:
            return

        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg"'
            f' xmlns:xlink="http://www.w3.org/1999/xlink"'
            f' width="{self.tb_width}" height="{self.tb_height}"'
            f' viewBox="0 0 {self.tb_width} {self.tb_height}">'
        ]
        if not self.transparent_bg.get():
            lines.append(
                f'<rect width="{self.tb_width}" height="{self.tb_height}"'
                f' fill="{self.bg_color}"/>')

        for el in self.elements:
            if el["type"]=="svg":
                sx = el["width"]  / el["viewbox_w"]
                sy = el["height"] / el["viewbox_h"]
                lines.append(
                    f'<g transform="translate({el["x"]:.2f},{el["y"]:.2f})'
                    f' scale({sx:.6f},{sy:.6f})">')
                lines.append(el["inner_content"])
                lines.append("</g>")
            elif el["type"]=="text":
                txt = (el["text"]
                       .replace("&","&amp;")
                       .replace("<","&lt;")
                       .replace(">","&gt;"))
                attrs = (f'x="{el["x"]:.2f}" y="{el["y"]:.2f}"'
                         f' font-family="{el["font_family"]}"'
                         f' font-size="{el["font_size"]}"'
                         f' fill="{el["fill"]}"'
                         f' dominant-baseline="hanging"')
                if el["font_weight"]=="bold":
                    attrs += ' font-weight="bold"'
                if el["font_style"]=="italic":
                    attrs += ' font-style="italic"'
                lines.append(f'<text {attrs}>{txt}</text>')

        lines.append("</svg>")
        try:
            with open(path,"w",encoding="utf-8") as f:
                f.write("\n".join(lines))
            self._set_status(f"Exported → {os.path.basename(path)}")
            messagebox.showinfo("Exported",
                f"Saved to:\n{path}\n\n"
                "To convert to PNG:\n"
                f'  magick "{path}" thumbnail.png\n'
                f'  rsvg-convert -w 1280 -h 720 "{path}" -o thumbnail.png')
        except Exception as e:
            messagebox.showerror("Export Error", str(e))


if __name__ == "__main__":
    try:
        root = tk.Tk()
        root.tk.call("tk", "scaling", 1.0)
        app = YouTubeThumbnailStudio(root)
        root.mainloop()
    except Exception as e:
        print(f"Launch error: {e}")
        input("Press Enter to exit...")
