import tkinter as tk
from tkinter import simpledialog, scrolledtext, Menu, messagebox
import keyword
import time
import threading
import re

class CodeAnimator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Python Syntax Highlighting Animator")
        self.geometry("800x600")

        self.text = tk.Text(self, font=("DejaVu Sans Mono", 14), bg="#000000", fg="#ffffff", insertbackground='white', padx=20, pady=20)
        self.text.pack(expand=True, fill="both")
        self.text.config(state="disabled")

        self._setup_tags()
        self._setup_menu()

        self.code = ''
        self.delay = 30

        self.after(100, self.get_code_input)  # ensure the main window shows first before input

    def _setup_tags(self):
        self.text.tag_configure("keyword", foreground="#569CD6")
        self.text.tag_configure("string", foreground="#CE9178")
        self.text.tag_configure("comment", foreground="#6A9955")
        self.text.tag_configure("default", foreground="#D4D4D4")

    def _setup_menu(self):
        menubar = Menu(self)
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Restart Animation", command=self.restart_animation)
        file_menu.add_command(label="Update Code", command=self.get_code_input)
        file_menu.add_command(label="Change Speed", command=self.change_speed)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)

    def get_code_input(self):
        input_window = tk.Toplevel(self)
        input_window.title("Enter Python Code")
        input_window.geometry("600x400")
        input_window.transient(self)
        input_window.grab_set()

        txt_area = scrolledtext.ScrolledText(input_window, font=("DejaVu Sans Mono", 12), wrap="none")
        txt_area.pack(expand=True, fill="both", padx=10, pady=10)

        btn_frame = tk.Frame(input_window)
        btn_frame.pack(fill="x", pady=5)

        submit_btn = tk.Button(btn_frame, text="Start Animation", command=lambda: self._submit_code(input_window, txt_area))
        submit_btn.pack(side="right", padx=10)

    def _submit_code(self, window, txt_area):
        self.code = txt_area.get("1.0", tk.END).strip()
        if self.code:
            window.destroy()
            threading.Thread(target=self.animate_code, daemon=True).start()
        else:
            messagebox.showwarning("Input Required", "Please enter some code to animate.")

    def change_speed(self):
        delay = simpledialog.askinteger("Speed", "Enter speed in ms per character (e.g., 30):", initialvalue=self.delay)
        if delay:
            self.delay = delay

    def restart_animation(self):
        if self.code:
            self.text.config(state="normal")
            self.text.delete("1.0", tk.END)
            self.text.config(state="disabled")
            threading.Thread(target=self.animate_code, daemon=True).start()
        else:
            messagebox.showinfo("No Code", "Please input code first using the File > Update Code option.")

    def highlight_line(self, lineno):
        line_start = f"{lineno}.0"
        line_end = f"{lineno}.end"
        line_text = self.text.get(line_start, line_end)
        self.text.tag_remove("keyword", line_start, line_end)
        self.text.tag_remove("string", line_start, line_end)
        self.text.tag_remove("comment", line_start, line_end)
        self.text.tag_remove("default", line_start, line_end)

        for match in re.finditer(r'#.*', line_text):
            start, end = match.span()
            self.text.tag_add("comment", f"{lineno}.{start}", f"{lineno}.{end}")

        for match in re.finditer(r'(\".*?\"|\'.*?\')', line_text):
            start, end = match.span()
            self.text.tag_add("string", f"{lineno}.{start}", f"{lineno}.{end}")

        words = line_text.split()
        index = 0
        for word in words:
            idx = line_text.find(word, index)
            if word in keyword.kwlist:
                self.text.tag_add("keyword", f"{lineno}.{idx}", f"{lineno}.{idx+len(word)}")
            index = idx + len(word)

    def animate_code(self):
        self.text.config(state="normal")
        self.text.delete("1.0", tk.END)
        lineno = 1
        colno = 0

        for char in self.code:
            if char == '\n':
                self.text.insert(f"{lineno}.{colno}", char)
                self.highlight_line(lineno)
                lineno += 1
                colno = 0
            else:
                self.text.insert(f"{lineno}.{colno}", char)
                colno += 1
            self.text.see(tk.END)
            self.update()
            time.sleep(self.delay / 1000)

        self.highlight_line(lineno)
        self.text.config(state="disabled")

if __name__ == "__main__":
    app = CodeAnimator()
    app.mainloop()
