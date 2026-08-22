import os
import subprocess
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

DB_NAME = "web_apps.db"

def init_db():
    """Create the SQLite database table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            work_dir TEXT NOT NULL,
            command TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

class AppManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Local Web App Launcher")
        self.geometry("700x450")
        self.minsize(600, 350)
        
        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        # Top Action Bar
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="▶ Launch App", command=self.launch_app).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="+ Add New", command=self.open_add_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✏ Edit", command=self.open_edit_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑 Delete", command=self.delete_app).pack(side=tk.LEFT, padx=5)

        # Treeview (Data Table)
        tree_frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "name", "work_dir", "command")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="App Name")
        self.tree.heading("work_dir", text="Working Directory")
        self.tree.heading("command", text="Command")

        self.tree.column("id", width=40, anchor=tk.CENTER)
        self.tree.column("name", width=150)
        self.tree.column("work_dir", width=250)
        self.tree.column("command", width=200)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Double-click to launch shortcut
        self.tree.bind("<Double-1>", lambda event: self.launch_app())

    def load_data(self):
        """Fetch all rows from SQLite and display in Treeview."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, work_dir, command FROM apps")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def get_selected_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select an app from the list.")
            return None
        return self.tree.item(selected[0])['values']

    def launch_app(self):
        """Execute the command in a new CMD window from the specified directory."""
        item = self.get_selected_item()
        if not item:
            return

        _, name, work_dir, command = item

        if not os.path.exists(work_dir):
            messagebox.showerror("Error", f"Working directory does not exist:\n{work_dir}")
            return

        try:
            # Shell command: start opens a new CMD window without blocking Tkinter
            full_cmd = f'start cmd.exe /k "{command}"'
            subprocess.Popen(full_cmd, cwd=work_dir, shell=True)
        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to launch {name}:\n{str(e)}")

    def open_add_dialog(self):
        AppFormDialog(self, title="Add Local Web App", callback=self.save_new_app)

    def save_new_app(self, name, work_dir, command):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO apps (name, work_dir, command) VALUES (?, ?, ?)",
                       (name, work_dir, command))
        conn.commit()
        conn.close()
        self.load_data()

    def open_edit_dialog(self):
        item = self.get_selected_item()
        if not item:
            return
        AppFormDialog(self, title="Edit Web App", app_data=item, callback=self.update_app)

    def update_app(self, app_id, name, work_dir, command):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE apps SET name=?, work_dir=?, command=? WHERE id=?",
                       (name, work_dir, command, app_id))
        conn.commit()
        conn.close()
        self.load_data()

    def delete_app(self):
        item = self.get_selected_item()
        if not item:
            return

        app_id, name, _, _ = item
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{name}'?"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM apps WHERE id=?", (app_id,))
            conn.commit()
            conn.close()
            self.load_data()


class AppFormDialog(tk.Toplevel):
    """Modal dialog for creating or editing app records."""
    def __init__(self, parent, title, callback, app_data=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("450x220")
        self.resizable(False, False)
        self.grab_set()  # Make window modal

        self.callback = callback
        self.app_id = app_data[0] if app_data else None

        # Form fields
        ttk.Label(self, text="App Name:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.ent_name = ttk.Entry(self, width=40)
        self.ent_name.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(self, text="Working Directory:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        dir_frame = ttk.Frame(self)
        dir_frame.grid(row=1, column=1, padx=10, pady=5, sticky=tk.EW)
        
        self.ent_dir = ttk.Entry(dir_frame, width=30)
        self.ent_dir.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_frame, text="Browse", width=7, command=self.browse_dir).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(self, text="Command:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        self.ent_cmd = ttk.Entry(self, width=40)
        self.ent_cmd.grid(row=2, column=1, padx=10, pady=5)

        # Pre-fill data if editing
        if app_data:
            self.ent_name.insert(0, app_data[1])
            self.ent_dir.insert(0, app_data[2])
            self.ent_cmd.insert(0, app_data[3])

        # Submit button
        ttk.Button(self, text="Save", command=self.on_save).grid(row=3, column=0, columnspan=2, pady=15)

    def browse_dir(self):
        chosen_dir = filedialog.askdirectory()
        if chosen_dir:
            self.ent_dir.delete(0, tk.END)
            self.ent_dir.insert(0, chosen_dir)

    def on_save(self):
        name = self.ent_name.get().strip()
        work_dir = self.ent_dir.get().strip()
        command = self.ent_cmd.get().strip()

        if not name or not work_dir or not command:
            messagebox.showwarning("Validation Error", "All fields are required.", parent=self)
            return

        if self.app_id:
            self.callback(self.app_id, name, work_dir, command)
        else:
            self.callback(name, work_dir, command)

        self.destroy()

if __name__ == "__main__":
    init_db()
    app = AppManager()
    app.mainloop()