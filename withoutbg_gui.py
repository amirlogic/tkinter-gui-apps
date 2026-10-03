import os
import sys
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

# Import check for withoutbg
try:
    from withoutbg import WithoutBG
    HAS_WITHOUTBG = True
except ImportError:
    HAS_WITHOUTBG = False


class ConsoleRedirector:
    """Redirects stdout/stderr streams to a Tkinter Text widget safely via a Queue."""
    def __init__(self, log_queue):
        self.queue = log_queue

    def write(self, string):
        if string:
            self.queue.put(string)

    def flush(self):
        pass


class BackgroundRemoverApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Local Background Remover (withoutbg)")
        self.geometry("900x720")
        self.minsize(800, 600)

        # Saved model instance to avoid re-loading/downloading every time
        self.model_instance = None

        # Application state variables
        self.input_path_var = tk.StringVar()
        self.output_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")

        self.log_queue = queue.Queue()

        self._create_widgets()
        self._setup_logging()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        # Top Frame: File Configuration
        config_frame = ttk.LabelFrame(self, text=" Configuration & Files ", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)

        # Input File Selection
        ttk.Label(config_frame, text="Input Image:").grid(row=0, column=0, sticky=tk.W, pady=3)
        input_entry = ttk.Entry(config_frame, textvariable=self.input_path_var, width=60)
        input_entry.grid(row=0, column=1, padx=5, pady=3, sticky=tk.EW)
        ttk.Button(config_frame, text="Browse...", command=self._browse_input).grid(row=0, column=2, padx=2, pady=3)

        # Output File Selection
        ttk.Label(config_frame, text="Output Image:").grid(row=1, column=0, sticky=tk.W, pady=3)
        output_entry = ttk.Entry(config_frame, textvariable=self.output_path_var, width=60)
        output_entry.grid(row=1, column=1, padx=5, pady=3, sticky=tk.EW)
        ttk.Button(config_frame, text="Browse...", command=self._browse_output).grid(row=1, column=2, padx=2, pady=3)

        config_frame.columnconfigure(1, weight=1)

        # Middle Frame: Previews & Action
        middle_frame = ttk.Frame(self, padding=10)
        middle_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        preview_frame = ttk.LabelFrame(middle_frame, text=" Image Preview ", padding=5)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        # Input Preview Canvas
        self.input_preview_lbl = ttk.Label(preview_frame, text="No Input Image Loaded", anchor=tk.CENTER)
        self.input_preview_lbl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        ttk.Separator(preview_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Output Preview Canvas
        self.output_preview_lbl = ttk.Label(preview_frame, text="Output Preview Will Appear Here", anchor=tk.CENTER)
        self.output_preview_lbl.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        # Action Button & Progress
        action_frame = ttk.Frame(self, padding=5)
        action_frame.pack(fill=tk.X, padx=10)

        self.btn_process = ttk.Button(action_frame, text="Remove Background", command=self._start_processing)
        self.btn_process.pack(side=tk.LEFT, padx=5)

        self.progress_bar = ttk.Progressbar(action_frame, mode="indeterminate")
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.lbl_status = ttk.Label(action_frame, textvariable=self.status_var)
        self.lbl_status.pack(side=tk.RIGHT, padx=5)

        # Bottom Frame: Console Output
        console_frame = ttk.LabelFrame(self, text=" Console Log ", padding=5)
        console_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)

        self.console_text = tk.Text(console_frame, height=8, state=tk.DISABLED, bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9))
        self.console_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(console_frame, orient=tk.VERTICAL, command=self.console_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.console_text.config(yscrollcommand=scrollbar.set)

    def _setup_logging(self):
        """Redirect standard output and error to the log window."""
        self.orig_stdout = sys.stdout
        self.orig_stderr = sys.stderr
        sys.stdout = ConsoleRedirector(self.log_queue)
        sys.stderr = ConsoleRedirector(self.log_queue)
        self.after(100, self._process_log_queue)

    def _process_log_queue(self):
        """Periodically flush log queue messages into the Tkinter Text widget without freezing."""
        # Process at most 50 messages per tick to prevent UI locking during heavy output
        count = 0
        while not self.log_queue.empty() and count < 50:
            msg = self.log_queue.get_nowait()
            self.console_text.config(state=tk.NORMAL)
            self.console_text.insert(tk.END, msg)
            self.console_text.see(tk.END)
            self.console_text.config(state=tk.DISABLED)
            count += 1
        self.after(100, self._process_log_queue)

    def _browse_input(self):
        file_path = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp *.bmp")]
        )
        if file_path:
            self.input_path_var.set(file_path)
            base, _ = os.path.splitext(file_path)
            self.output_path_var.set(f"{base}_nobg.png")
            self._update_preview(file_path, is_input=True)

    def _browse_output(self):
        file_path = filedialog.asksaveasfilename(
            title="Save Output Image",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")]
        )
        if file_path:
            self.output_path_var.set(file_path)

    def _update_preview(self, img_path, is_input=True):
        """Load and scale image for local UI preview display."""
        try:
            img = Image.open(img_path)
            img.thumbnail((350, 350))
            photo = ImageTk.PhotoImage(img)

            lbl = self.input_preview_lbl if is_input else self.output_preview_lbl
            lbl.config(image=photo, text="")
            lbl.image = photo
        except Exception as e:
            print(f"Failed to load preview for {img_path}: {e}")

    def _start_processing(self):
        if not HAS_WITHOUTBG:
            messagebox.showerror(
                "Missing Dependency",
                "The 'withoutbg' library is not installed.\n\nPlease install it via:\npip install withoutbg"
            )
            return

        input_path = self.input_path_var.get()
        output_path = self.output_path_var.get()

        if not input_path or not os.path.exists(input_path):
            messagebox.showwarning("Invalid Input", "Please select a valid input image file.")
            return

        if not output_path:
            messagebox.showwarning("Invalid Output", "Please specify an output image path.")
            return

        self.btn_process.config(state=tk.DISABLED)
        self.progress_bar.start(10)
        self.status_var.set("Downloading/Loading model..." if self.model_instance is None else "Removing background...")

        threading.Thread(
            target=self._run_inference_thread,
            args=(input_path, output_path),
            daemon=True
        ).start()

    def _run_inference_thread(self, input_path, output_path):
        print("--- Starting Background Removal ---")
        print(f"Input File : {input_path}")
        print(f"Output File: {output_path}")

        try:
            # 1. Load model weights (re-use instance if already downloaded)
            if self.model_instance is None:
                print("Initializing model weights (Downloading ONNX weights if first time run)...")
                
                # Temporarily restore true stdout/stderr during HF download to avoid GUI queue saturation
                sys.stdout = self.orig_stdout
                sys.stderr = self.orig_stderr
                
                model = WithoutBG.open_weights()
                
                # Re-enable Tkinter redirected logging
                sys.stdout = ConsoleRedirector(self.log_queue)
                sys.stderr = ConsoleRedirector(self.log_queue)
                
                self.model_instance = model
                print("Model weights loaded into memory successfully.")

            # Update status label on GUI thread
            self.after(0, lambda: self.status_var.set("Processing image..."))

            # 2. Perform background removal and save output
            result_img = self.model_instance.remove_background(input_path)
            result_img.save(output_path)

            print(f"Success: Image saved to {output_path}")
            self.after(0, self._on_processing_success, output_path)

        except Exception as err:
            # Ensure standard output streams are restored on error
            sys.stdout = ConsoleRedirector(self.log_queue)
            sys.stderr = ConsoleRedirector(self.log_queue)
            
            print(f"Error during processing: {str(err)}")
            self.after(0, self._on_processing_error, str(err))

    def _on_processing_success(self, output_path):
        self.progress_bar.stop()
        self.btn_process.config(state=tk.NORMAL)
        self.status_var.set("Completed!")
        self._update_preview(output_path, is_input=False)
        messagebox.showinfo("Success", f"Background removed successfully!\nSaved to: {output_path}")

    def _on_processing_error(self, error_msg):
        self.progress_bar.stop()
        self.btn_process.config(state=tk.NORMAL)
        self.status_var.set("Failed")
        messagebox.showerror("Execution Error", f"An error occurred during execution:\n{error_msg}")

    def _on_close(self):
        sys.stdout = self.orig_stdout
        sys.stderr = self.orig_stderr
        self.destroy()


if __name__ == "__main__":
    app = BackgroundRemoverApp()
    app.mainloop()