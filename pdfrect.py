import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pymupdf as fitz
from PIL import Image, ImageTk, ImageDraw
import io

class PDFViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Viewer with Rectangle Overlay")
        self.root.geometry("1000x700")
        
        # Initialize variables
        self.pdf_document = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_factor = 1.0
        self.photo = None
        self.fit_to_window = True  # New flag for fit-to-window mode
        
        # Create the GUI
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control frame (top)
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File operations
        ttk.Button(control_frame, text="Open PDF", command=self.open_pdf).pack(side=tk.LEFT, padx=(0, 5))
        
        # Page navigation
        ttk.Label(control_frame, text="Page:").pack(side=tk.LEFT, padx=(20, 5))
        self.page_var = tk.StringVar(value="0")
        self.page_label = ttk.Label(control_frame, textvariable=self.page_var)
        self.page_label.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(control_frame, text="Previous", command=self.prev_page).pack(side=tk.LEFT, padx=(5, 2))
        ttk.Button(control_frame, text="Next", command=self.next_page).pack(side=tk.LEFT, padx=(2, 5))
        
        # Zoom controls
        ttk.Label(control_frame, text="Zoom:").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Button(control_frame, text="Zoom In", command=self.zoom_in).pack(side=tk.LEFT, padx=(5, 2))
        ttk.Button(control_frame, text="Zoom Out", command=self.zoom_out).pack(side=tk.LEFT, padx=(2, 5))
        ttk.Button(control_frame, text="Reset Zoom", command=self.reset_zoom).pack(side=tk.LEFT, padx=(2, 5))
        ttk.Button(control_frame, text="Fit to Window", command=self.fit_to_window).pack(side=tk.LEFT, padx=(2, 5))
        
        # Content frame
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for PDF display
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Canvas with scrollbars for PDF display
        canvas_frame = ttk.Frame(left_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg='white')
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Right panel for rectangle controls
        right_frame = ttk.LabelFrame(content_frame, text="Rectangle Controls", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # Rectangle coordinate inputs
        ttk.Label(right_frame, text="Rectangle Coordinates:").pack(anchor=tk.W, pady=(0, 5))
        
        # X0 input
        ttk.Label(right_frame, text="X0:").pack(anchor=tk.W)
        self.x0_var = tk.StringVar(value="100")
        self.x0_entry = ttk.Entry(right_frame, textvariable=self.x0_var, width=15)
        self.x0_entry.pack(anchor=tk.W, pady=(0, 5))
        
        # Y0 input
        ttk.Label(right_frame, text="Y0:").pack(anchor=tk.W)
        self.y0_var = tk.StringVar(value="100")
        self.y0_entry = ttk.Entry(right_frame, textvariable=self.y0_var, width=15)
        self.y0_entry.pack(anchor=tk.W, pady=(0, 5))
        
        # X1 input
        ttk.Label(right_frame, text="X1:").pack(anchor=tk.W)
        self.x1_var = tk.StringVar(value="300")
        self.x1_entry = ttk.Entry(right_frame, textvariable=self.x1_var, width=15)
        self.x1_entry.pack(anchor=tk.W, pady=(0, 5))
        
        # Y1 input
        ttk.Label(right_frame, text="Y1:").pack(anchor=tk.W)
        self.y1_var = tk.StringVar(value="200")
        self.y1_entry = ttk.Entry(right_frame, textvariable=self.y1_var, width=15)
        self.y1_entry.pack(anchor=tk.W, pady=(0, 5))
        
        # Page Rect button
        ttk.Button(right_frame, text="Page Rect", command=self.set_page_rect).pack(pady=(5, 10))
        
        # Rectangle color selection
        ttk.Label(right_frame, text="Rectangle Color:").pack(anchor=tk.W, pady=(10, 5))
        self.color_var = tk.StringVar(value="red")
        color_combo = ttk.Combobox(right_frame, textvariable=self.color_var, 
                                  values=["red", "blue", "green", "yellow", "orange", "purple", "black"],
                                  state="readonly", width=12)
        color_combo.pack(anchor=tk.W, pady=(0, 5))
        
        # Rectangle opacity
        ttk.Label(right_frame, text="Opacity:").pack(anchor=tk.W, pady=(10, 5))
        self.opacity_var = tk.DoubleVar(value=0.3)
        opacity_scale = ttk.Scale(right_frame, from_=0.1, to=1.0, variable=self.opacity_var, 
                                 orient=tk.HORIZONTAL, length=150)
        opacity_scale.pack(anchor=tk.W, pady=(0, 5))
        
        # Update button
        ttk.Button(right_frame, text="Update Rectangle", command=self.update_display).pack(pady=(10, 5))
        
        # Show/Hide rectangle
        self.show_rect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_frame, text="Show Rectangle", variable=self.show_rect_var,
                       command=self.update_display).pack(pady=(5, 0))
        
        # Show page border
        self.show_border_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_frame, text="Show Page Border", variable=self.show_border_var,
                       command=self.update_display).pack(pady=(5, 0))
        
        # Rectangle info
        ttk.Label(right_frame, text="Rectangle Info:").pack(anchor=tk.W, pady=(20, 5))
        self.info_text = tk.Text(right_frame, height=4, width=20, wrap=tk.WORD)
        self.info_text.pack(anchor=tk.W, pady=(0, 5))
        
        # Bind events
        self.bind_events()
        
    def bind_events(self):
        # Bind Enter key to update rectangle for all entry fields
        #for entry in [self.x0_entry, self.y0_entry, self.x1_entry, self.y1_entry]:
            #entry.bind('<Return>', lambda e: self.update_display())
            #entry.bind('<FocusOut>', lambda e: self.update_display())
        
        # Bind mouse wheel for zooming
        self.canvas.bind('<MouseWheel>', self.on_mousewheel)
        self.canvas.bind('<Button-4>', self.on_mousewheel)
        self.canvas.bind('<Button-5>', self.on_mousewheel)
        
        # Bind canvas resize to maintain fit-to-window
        self.canvas.bind('<Configure>', self.on_canvas_resize)
        
    def on_canvas_resize(self, event):
        # Only update if fit-to-window is enabled and we have a document
        if self.fit_to_window and self.pdf_document:
            self.calculate_fit_zoom()
            self.update_display()
        
    def on_mousewheel(self, event):
        # Zoom with mouse wheel while holding Ctrl
        if event.state & 0x4:  # Ctrl key held
            if event.delta > 0 or event.num == 4:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            # Scroll normally
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
    def open_pdf(self):
        file_path = filedialog.askopenfilename(
            title="Select PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.pdf_document = fitz.open(file_path)
                self.total_pages = len(self.pdf_document)
                self.current_page = 0
                self.update_page_info()
                self.calculate_fit_zoom()
                self.update_display()
                messagebox.showinfo("Success", f"PDF loaded successfully!\nTotal pages: {self.total_pages}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open PDF: {str(e)}")
    
    def prev_page(self):
        if self.pdf_document and self.current_page > 0:
            self.current_page -= 1
            self.update_page_info()
            if self.fit_to_window:
                self.calculate_fit_zoom()
            self.update_display()
    
    def next_page(self):
        if self.pdf_document and self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_page_info()
            if self.fit_to_window:
                self.calculate_fit_zoom()
            self.update_display()
    
    def update_page_info(self):
        if self.pdf_document:
            self.page_var.set(f"{self.current_page + 1} / {self.total_pages}")
        else:
            self.page_var.set("No PDF loaded")
    
    def zoom_in(self):
        self.fit_to_window = False
        self.zoom_factor *= 1.2
        self.update_display()
    
    def zoom_out(self):
        self.fit_to_window = False
        self.zoom_factor /= 1.2
        self.update_display()
    
    def reset_zoom(self):
        self.fit_to_window = False
        self.zoom_factor = 1.0
        self.update_display()
    
    def fit_to_window(self):
        self.fit_to_window = True
        self.calculate_fit_zoom()
        self.update_display()
    
    def calculate_fit_zoom(self):
        if not self.pdf_document:
            return
        
        # Get current page dimensions
        page = self.pdf_document[self.current_page]
        page_rect = page.rect
        
        # Get canvas dimensions (subtract some padding)
        canvas_width = self.canvas.winfo_width() - 40
        canvas_height = self.canvas.winfo_height() - 40
        
        # Calculate zoom factors for width and height
        if canvas_width > 0 and canvas_height > 0:
            zoom_width = canvas_width / page_rect.width
            zoom_height = canvas_height / page_rect.height
            
            # Use the smaller zoom factor to fit within both dimensions
            self.zoom_factor = min(zoom_width, zoom_height)
    
    def set_page_rect(self):
        if not self.pdf_document:
            messagebox.showwarning("Warning", "Please load a PDF first")
            return
        
        page = self.pdf_document[self.current_page]
        page_rect = page.rect
        
        # Set the input fields to page rectangle coordinates
        self.x0_var.set(f"{page_rect.x0:.1f}")
        self.y0_var.set(f"{page_rect.y0:.1f}")
        self.x1_var.set(f"{page_rect.x1:.1f}")
        self.y1_var.set(f"{page_rect.y1:.1f}")
        
        # Update display
        self.update_display()
    
    def get_rect_coordinates(self):
        try:
            x0 = float(self.x0_var.get())
            y0 = float(self.y0_var.get())
            x1 = float(self.x1_var.get())
            y1 = float(self.y1_var.get())
            return fitz.Rect(x0, y0, x1, y1)
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric coordinates")
            return None
    
    def update_display(self):
        if not self.pdf_document:
            return
        
        try:
            # Get current page
            page = self.pdf_document[self.current_page]
            
            # Create matrix for zoom
            mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            
            # Render page to pixmap
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("ppm")
            pil_image = Image.open(io.BytesIO(img_data))
            
            # Convert to RGBA for transparency support
            pil_image = pil_image.convert('RGBA')
            
            # Draw page border if enabled
            if self.show_border_var.get():
                page_rect = page.rect
                scaled_page_rect = page_rect * mat
                
                draw = ImageDraw.Draw(pil_image)
                draw.rectangle(
                    [scaled_page_rect.x0, scaled_page_rect.y0, scaled_page_rect.x1-1, scaled_page_rect.y1-1],
                    outline=(0, 0, 0, 255),
                    width=2
                )
            
            # Draw rectangle if enabled
            if self.show_rect_var.get():
                rect = self.get_rect_coordinates()
                if rect:
                    # Scale rectangle coordinates according to zoom
                    scaled_rect = rect * mat
                    
                    # Get color and opacity
                    color = self.color_var.get()
                    opacity = int(self.opacity_var.get() * 255)
                    
                    # Color mapping
                    color_map = {
                        "red": (255, 0, 0, opacity),
                        "blue": (0, 0, 255, opacity),
                        "green": (0, 255, 0, opacity),
                        "yellow": (255, 255, 0, opacity),
                        "orange": (255, 165, 0, opacity),
                        "purple": (128, 0, 128, opacity),
                        "black": (0, 0, 0, opacity)
                    }
                    
                    # Create overlay for transparency
                    overlay = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
                    overlay_draw = ImageDraw.Draw(overlay)
                    
                    # Draw rectangle
                    overlay_draw.rectangle(
                        [scaled_rect.x0, scaled_rect.y0, scaled_rect.x1, scaled_rect.y1],
                        fill=color_map.get(color, (255, 0, 0, opacity)),
                        outline=color_map.get(color, (255, 0, 0, 255))[:3] + (255,),
                        width=2
                    )
                    
                    # Composite overlay onto image
                    pil_image = Image.alpha_composite(pil_image, overlay)
                    
                    # Update rectangle info
                    self.update_rect_info(rect, page)
            
            # Convert back to RGB for display
            pil_image = pil_image.convert('RGB')
            
            # Convert to PhotoImage
            self.photo = ImageTk.PhotoImage(pil_image)
            
            # Update canvas
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            
            # Update scroll region
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update display: {str(e)}")
    
    def update_rect_info(self, rect, page):
        info = f"Rect: ({rect.x0:.1f}, {rect.y0:.1f}, {rect.x1:.1f}, {rect.y1:.1f})\n"
        info += f"Width: {rect.width:.1f}\n"
        info += f"Height: {rect.height:.1f}\n"
        info += f"Area: {rect.width * rect.height:.1f}"
        
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info)

def main():
    root = tk.Tk()
    app = PDFViewerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
