import os
import sqlite3
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

DB_NAME = "conda_launcher.db"

def init_db():
    """Create the SQLite database table for Conda script configurations."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            work_dir TEXT NOT NULL,
            conda_env TEXT NOT NULL,
            shell TEXT NOT NULL,
            target TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

class CondaLauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Conda Script Manager & Launcher")
        self.geometry("800x480")
        self.minsize(650, 380)

        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        # Action Toolbar
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="▶ Launch Script", command=self.launch_script).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="+ Add New", command=self.open_add_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✏ Edit", command=self.open_edit_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑 Delete", command=self.delete_script).pack(side=tk.LEFT, padx=5)

        # Main Table (Treeview)
        tree_frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "name", "work_dir", "conda_env", "shell", "target")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("work_dir", text="Directory")
        self.tree.heading("conda_env", text="Conda Env")
        self.tree.heading("shell", text="Shell")
        self.tree.heading("target", text="Target Script")

        self.tree.column("id", width=35, anchor=tk.CENTER)
        self.tree.column("name", width=140)
        self.tree.column("work_dir", width=220)
        self.tree.column("conda_env", width=110)
        self.tree.column("shell", width=80, anchor=tk.CENTER)
        self.tree.column("target", width=150)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Double-click shortcut to launch
        self.tree.bind("<Double-1>", lambda event: self.launch_script())

    def load_data(self):
        """Reload records from SQLite database."""
        for row in self.tree.get_children():
            self.tree.delete(row)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, work_dir, conda_env, shell, target FROM scripts")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def get_selected_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select a script from the list.")
            return None
        return self.tree.item(selected[0])['values']

    def launch_script(self):
        """Construct shell launch command and execute in selected window type."""
        item = self.get_selected_item()
        if not item:
            return

        _, name, work_dir, conda_env, shell, target = item

        if not os.path.exists(work_dir):
            messagebox.showerror("Error", f"Working directory does not exist:\n{work_dir}")
            return

        target_path = os.path.join(work_dir, target)
        if not os.path.exists(target_path):
            messagebox.showerror("Error", f"Target file does not exist:\n{target_path}")
            return

        try:
            if sys.platform == "win32":
                if shell.lower() == "powershell":
                    # Spawns a PowerShell window, activates environment, and runs python target
                    ps_cmd = f"conda activate {conda_env}; python {target}"
                    full_cmd = f'start powershell -NoExit -Command "{ps_cmd}"'
                else:  # CMD
                    # Spawns CMD window, activates conda env, and executes python target
                    cmd_str = f"conda activate {conda_env} && python {target}"
                    full_cmd = f'start cmd.exe /k "{cmd_str}"'
            else:
                # Linux / macOS fallback using system default terminal
                full_cmd = f'gnome-terminal -- bash -c "conda activate {conda_env} && python {target}; exec bash"'

            subprocess.Popen(full_cmd, cwd=work_dir, shell=True)

        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to launch script {name}:\n{str(e)}")

    def open_add_dialog(self):
        ScriptFormDialog(self, title="Add Conda Script", callback=self.save_new_script)

    def save_new_script(self, name, work_dir, conda_env, shell, target):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scripts (name, work_dir, conda_env, shell, target) 
            VALUES (?, ?, ?, ?, ?)
        """, (name, work_dir, conda_env, shell, target))
        conn.commit()
        conn.close()
        self.load_data()

    def open_edit_dialog(self):
        item = self.get_selected_item()
        if not item:
            return
        ScriptFormDialog(self, title="Edit Script Entry", script_data=item, callback=self.update_script)

    def update_script(self, script_id, name, work_dir, conda_env, shell, target):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE scripts SET name=?, work_dir=?, conda_env=?, shell=?, target=? 
            WHERE id=?
        """, (name, work_dir, conda_env, shell, target, script_id))
        conn.commit()
        conn.close()
        self.load_data()

    def delete_script(self):
        item = self.get_selected_item()
        if not item:
            return

        script_id, name, _, _, _, _ = item
        if messagebox.askyesno("Confirm Delete", f"Delete '{name}' configuration?"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scripts WHERE id=?", (script_id,))
            conn.commit()
            conn.close()
            self.load_data()


class ScriptFormDialog(tk.Toplevel):
    """Modal Form Dialog for Add/Edit actions."""
    def __init__(self, parent, title, callback, script_data=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("500x260")
        self.resizable(False, False)
        self.grab_set()

        self.callback = callback
        self.script_id = script_data[0] if script_data else None

        # Grid form design
        ttk.Label(self, text="Script/App Name:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.ent_name = ttk.Entry(self, width=45)
        self.ent_name.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(self, text="Directory:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        dir_frame = ttk.Frame(self)
        dir_frame.grid(row=1, column=1, padx=10, pady=5, sticky=tk.EW)
        
        self.ent_dir = ttk.Entry(dir_frame, width=33)
        self.ent_dir.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_frame, text="Browse", width=7, command=self.browse_dir).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(self, text="Target (e.g. main.py):").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        target_frame = ttk.Frame(self)
        target_frame.grid(row=2, column=1, padx=10, pady=5, sticky=tk.EW)

        self.ent_target = ttk.Entry(target_frame, width=33)
        self.ent_target.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(target_frame, text="File", width=7, command=self.browse_file).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(self, text="Conda Environment:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        self.ent_env = ttk.Entry(self, width=45)
        self.ent_env.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(self, text="Shell Execution:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        self.cmb_shell = ttk.Combobox(self, values=["cmd", "powershell"], state="readonly", width=42)
        self.cmb_shell.set("cmd")
        self.cmb_shell.grid(row=4, column=1, padx=10, pady=5)

        # Pre-fill fields if in Edit mode
        if script_data:
            self.ent_name.insert(0, script_data[1])
            self.ent_dir.insert(0, script_data[2])
            self.ent_env.insert(0, script_data[3])
            self.cmb_shell.set(script_data[4])
            self.ent_target.insert(0, script_data[5])

        ttk.Button(self, text="Save Configuration", command=self.on_save).grid(row=5, column=0, columnspan=2, pady=12)

    def browse_dir(self):
        chosen_dir = filedialog.askdirectory()
        if chosen_dir:
            self.ent_dir.delete(0, tk.END)
            self.ent_dir.insert(0, chosen_dir)

    def browse_file(self):
        current_dir = self.ent_dir.get().strip() or os.getcwd()
        chosen_file = filedialog.askopenfilename(initialdir=current_dir, filetypes=[("Python Files", "*.py"), ("All Files", "*.*")])
        if chosen_file:
            # If selected file is in the chosen directory, store relative filename; otherwise store absolute path
            rel_path = os.path.basename(chosen_file)
            self.ent_target.delete(0, tk.END)
            self.ent_target.insert(0, rel_path)

    def on_save(self):
        name = self.ent_name.get().strip()
        work_dir = self.ent_dir.get().strip()
        conda_env = self.ent_env.get().strip()
        shell = self.cmb_shell.get().strip()
        target = self.ent_target.get().strip()

        if not all([name, work_dir, conda_env, shell, target]):
            messagebox.showwarning("Validation Error", "All fields are required.", parent=self)
            return

        if self.script_id:
            self.callback(self.script_id, name, work_dir, conda_env, shell, target)
        else:
            self.callback(name, work_dir, conda_env, shell, target)

        self.destroy()

if __name__ == "__main__":
    init_db()
    app = CondaLauncherApp()
    app.mainloop()