import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pymupdf
import pathlib
from typing import List, Tuple

class PDFEmbedderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF File Embedder")
        self.root.geometry("800x600")
        
        # Supported file types
        self.ftypes = ('.png', '.jpg', '.jpeg', '.bmp', '.svg', '.mp4')
        
        # Variables
        self.pdf_file = tk.StringVar()
        self.working_dir = tk.StringVar()
        self.output_file = tk.StringVar()
        self.files_to_embed = []  # List of (file_path, embed_name) tuples
        self.doc = None
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # PDF File Selection
        ttk.Label(main_frame, text="PDF File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.pdf_file, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_pdf).grid(row=0, column=2, padx=5)
        
        # Working Directory Selection
        ttk.Label(main_frame, text="Working Directory:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.working_dir, width=50).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_directory).grid(row=1, column=2, padx=5)
        
        # Load Files Button
        ttk.Button(main_frame, text="Load Files from Directory", command=self.load_files).grid(row=2, column=0, columnspan=3, pady=10)
        
        # Files List Frame
        files_frame = ttk.LabelFrame(main_frame, text="Files to Embed", padding="5")
        files_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)
        
        # Treeview for files
        self.tree = ttk.Treeview(files_frame, columns=('File', 'Embed Name'), show='headings', height=10)
        self.tree.heading('File', text='File Path')
        self.tree.heading('Embed Name', text='Embed Name')
        self.tree.column('File', width=400)
        self.tree.column('Embed Name', width=200)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Buttons frame
        buttons_frame = ttk.Frame(files_frame)
        buttons_frame.grid(row=1, column=0, columnspan=2, pady=5)
        
        ttk.Button(buttons_frame, text="Add File", command=self.add_single_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Edit Embed Name", command=self.edit_embed_name).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        
        # Output File Selection
        ttk.Label(main_frame, text="Output PDF:").grid(row=4, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_file, width=50).grid(row=4, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_output).grid(row=4, column=2, padx=5)
        
        # Embed Files Button
        ttk.Button(main_frame, text="Embed Files to PDF", command=self.embed_files, style='Accent.TButton').grid(row=5, column=0, columnspan=3, pady=20)
        
        # Status Label
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="green")
        self.status_label.grid(row=6, column=0, columnspan=3, pady=5)
        
        # Configure grid weights for main frame
        main_frame.rowconfigure(3, weight=1)
        
    def browse_pdf(self):
        filename = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if filename:
            self.pdf_file.set(filename)
            
    def browse_directory(self):
        directory = filedialog.askdirectory(title="Select Working Directory")
        if directory:
            self.working_dir.set(directory)
            
    def browse_output(self):
        filename = filedialog.asksaveasfilename(
            title="Save PDF As",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if filename:
            self.output_file.set(filename)
            
    def load_files(self):
        if not self.working_dir.get():
            messagebox.showerror("Error", "Please select a working directory first.")
            return
            
        try:
            wlkpath = pathlib.Path(self.working_dir.get())
            if not wlkpath.exists():
                messagebox.showerror("Error", "Working directory does not exist.")
                return
                
            # Clear existing files
            self.clear_all()
            
            # Find all supported files
            supported_files = []
            for file_path in wlkpath.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in self.ftypes:
                    supported_files.append(file_path)
            
            if not supported_files:
                messagebox.showinfo("Info", f"No supported files found in directory.\nSupported types: {', '.join(self.ftypes)}")
                return
            
            # Show file selection dialog
            self.show_file_selection_dialog(supported_files)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading files: {str(e)}")
            
    def show_file_selection_dialog(self, files: List[pathlib.Path]):
        # Create a new window for file selection
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Files to Embed")
        dialog.geometry("700x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # File list with checkboxes
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Select files to embed:").pack(anchor=tk.W)
        
        # Create frame for checkboxes with scrollbar
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Checkbox variables
        checkbox_vars = {}
        embed_name_vars = {}
        
        for file_path in files:
            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill=tk.X, padx=5, pady=2)
            
            var = tk.BooleanVar(value=True)  # Select all by default
            checkbox_vars[file_path] = var
            
            ttk.Checkbutton(frame, variable=var, text=str(file_path.name)).pack(side=tk.LEFT)
            
            # Entry for embed name
            embed_var = tk.StringVar(value=file_path.name)
            embed_name_vars[file_path] = embed_var
            ttk.Label(frame, text="Embed as:").pack(side=tk.LEFT, padx=(10, 5))
            ttk.Entry(frame, textvariable=embed_var, width=30).pack(side=tk.LEFT, padx=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def select_all():
            for var in checkbox_vars.values():
                var.set(True)
                
        def select_none():
            for var in checkbox_vars.values():
                var.set(False)
                
        def confirm_selection():
            selected_files = []
            for file_path, var in checkbox_vars.items():
                if var.get():
                    embed_name = embed_name_vars[file_path].get().strip()
                    if not embed_name:
                        embed_name = file_path.name
                    selected_files.append((file_path, embed_name))
            
            if selected_files:
                self.files_to_embed.extend(selected_files)
                self.update_files_display()
                self.status_label.config(text=f"Loaded {len(selected_files)} files", foreground="green")
            
            dialog.destroy()
        
        ttk.Button(button_frame, text="Select All", command=select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Select None", command=select_none).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="OK", command=confirm_selection).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
    def add_single_file(self):
        filename = filedialog.askopenfilename(
            title="Select File to Embed",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.svg"),
                ("Video files", "*.mp4"),
                ("All files", "*.*")
            ]
        )
        if filename:
            file_path = pathlib.Path(filename)
            embed_name = tk.simpledialog.askstring("Embed Name", f"Enter embed name for {file_path.name}:", initialvalue=file_path.name)
            if embed_name:
                self.files_to_embed.append((file_path, embed_name))
                self.update_files_display()
                self.status_label.config(text=f"Added {file_path.name}", foreground="green")
    
    def remove_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select a file to remove.")
            return
        
        for item in selected_items:
            index = self.tree.index(item)
            del self.files_to_embed[index]
        
        self.update_files_display()
        self.status_label.config(text="Selected files removed", foreground="green")
    
    def edit_embed_name(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select a file to edit.")
            return
        
        if len(selected_items) > 1:
            messagebox.showwarning("Warning", "Please select only one file to edit.")
            return
        
        item = selected_items[0]
        index = self.tree.index(item)
        current_embed_name = self.files_to_embed[index][1]
        
        new_name = tk.simpledialog.askstring("Edit Embed Name", "Enter new embed name:", initialvalue=current_embed_name)
        if new_name:
            file_path = self.files_to_embed[index][0]
            self.files_to_embed[index] = (file_path, new_name)
            self.update_files_display()
            self.status_label.config(text="Embed name updated", foreground="green")
    
    def clear_all(self):
        self.files_to_embed.clear()
        self.update_files_display()
        self.status_label.config(text="All files cleared", foreground="green")
    
    def update_files_display(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add files to display
        for file_path, embed_name in self.files_to_embed:
            self.tree.insert('', 'end', values=(str(file_path), embed_name))
    
    def embed_files(self):
        if not self.pdf_file.get():
            messagebox.showerror("Error", "Please select a PDF file.")
            return
        
        if not self.output_file.get():
            messagebox.showerror("Error", "Please specify an output file.")
            return
        
        if not self.files_to_embed:
            messagebox.showerror("Error", "No files selected for embedding.")
            return
        
        try:
            self.status_label.config(text="Embedding files...", foreground="blue")
            self.root.update()
            
            # Open PDF
            doc = pymupdf.open(self.pdf_file.get())
            
            # Embed files
            embedded_count = 0
            for file_path, embed_name in self.files_to_embed:
                try:
                    embytes = pathlib.Path(file_path).read_bytes()
                    doc.embfile_add(embed_name, embytes)
                    embedded_count += 1
                except Exception as e:
                    messagebox.showwarning("Warning", f"Failed to embed {file_path.name}: {str(e)}")
            
            # Save the document
            doc.save(self.output_file.get())
            doc.close()
            
            self.status_label.config(text=f"Successfully embedded {embedded_count} files", foreground="green")
            messagebox.showinfo("Success", f"Successfully embedded {embedded_count} files to {self.output_file.get()}")
            
        except Exception as e:
            self.status_label.config(text="Error occurred", foreground="red")
            messagebox.showerror("Error", f"Error embedding files: {str(e)}")

# Import simpledialog for embed name input
import tkinter.simpledialog

def main():
    root = tk.Tk()
    app = PDFEmbedderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()