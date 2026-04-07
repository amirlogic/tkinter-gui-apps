import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import csv
import io

class CreateTaskDialog(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Create New Task")
        self.geometry("400x300")
        self.callback = callback
        self.resizable(False, False)

        # Form Variables
        self.name_var = tk.StringVar()
        self.path_var = tk.StringVar()
        self.schedule_var = tk.StringVar(value="DAILY")
        self.time_var = tk.StringVar(value="12:00")

        self.create_widgets()

    def create_widgets(self):
        padding = {'padx': 10, 'pady': 5}
        
        # Task Name
        ttk.Label(self, text="Task Name (no spaces recommended):").pack(fill=tk.X, **padding)
        ttk.Entry(self, textvariable=self.name_var).pack(fill=tk.X, **padding)

        # Task Path
        ttk.Label(self, text="Program/Script Path:").pack(fill=tk.X, **padding)
        ttk.Entry(self, textvariable=self.path_var).pack(fill=tk.X, **padding)

        # Schedule Type
        ttk.Label(self, text="Schedule:").pack(fill=tk.X, **padding)
        schedules = ["MINUTE", "HOURLY", "DAILY", "WEEKLY", "MONTHLY", "ONLOGON", "ONIDLE"]
        ttk.Combobox(self, textvariable=self.schedule_var, values=schedules, state="readonly").pack(fill=tk.X, **padding)

        # Start Time
        ttk.Label(self, text="Start Time (HH:mm):").pack(fill=tk.X, **padding)
        ttk.Entry(self, textvariable=self.time_var).pack(fill=tk.X, **padding)

        # Submit
        ttk.Button(self, text="Create Task", command=self.submit).pack(pady=20)

    def submit(self):
        # Basic validation
        name = self.name_var.get().strip()
        path = self.path_var.get().strip()
        sched = self.schedule_var.get()
        time = self.time_var.get().strip()

        if not name or not path:
            messagebox.showwarning("Error", "Name and Path are required!")
            return

        # Pass data back to main app
        self.callback(name, path, sched, time)
        self.destroy()

class SchtasksGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows Task Manager (schtasks)")
        self.root.geometry("900x500")

        self.setup_styles()
        self.create_widgets()
        self.refresh_task_list()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.configure("Treeview", rowheight=25)

    def create_widgets(self):
        btn_frame = ttk.Frame(self.root, padding="10")
        btn_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(btn_frame, text="Refresh List", command=self.refresh_task_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="➕ Create Task", command=self.open_create_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        ttk.Button(btn_frame, text="▶ Run", command=self.run_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⏹ Stop", command=self.end_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑 Delete", command=self.delete_task).pack(side=tk.LEFT, padx=5)

        self.tree_frame = ttk.Frame(self.root)
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(self.tree_frame, columns=("TaskName", "NextRun", "Status"), show='headings')
        self.tree.heading("TaskName", text="Task Name")
        self.tree.heading("NextRun", text="Next Run Time")
        self.tree.heading("Status", text="Status")
        
        self.tree.column("TaskName", width=450)
        self.tree.column("NextRun", width=180)
        self.tree.column("Status", width=100)

        self.scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=self.scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def run_command(self, cmd):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Command Error", e.stderr if e.stderr else "Operation failed.")
            return None

    def refresh_task_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        # /fo csv = CSV format, /nh = no header
        output = self.run_command("schtasks /query /fo csv /nh")
        
        if output:
            reader = csv.reader(io.StringIO(output))
            for row in reader:
                if len(row) >= 3:
                    self.tree.insert("", tk.END, values=(row[0], row[1], row[2]))

    def open_create_dialog(self):
        CreateTaskDialog(self.root, self.create_task_action)

    def create_task_action(self, name, path, sched, time):
        # Construct the schtasks command
        # /create: action
        # /tn: task name
        # /tr: task run (command)
        # /sc: schedule
        # /st: start time
        # /f: force create (overwrite existing)
        cmd = f'schtasks /create /f /tn "{name}" /tr "{path}" /sc {sched} /st {time}'
        
        result = self.run_command(cmd)
        if result is not None:
            messagebox.showinfo("Success", f"Task '{name}' created successfully.")
            self.refresh_task_list()

    def get_selected_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection", "Please select a task from the list.")
            return None
        return self.tree.item(selected[0])['values'][0]

    def run_task(self):
        task_name = self.get_selected_task()
        if task_name and self.run_command(f'schtasks /run /tn "{task_name}"') is not None:
            messagebox.showinfo("Success", f"Task started.")

    def end_task(self):
        task_name = self.get_selected_task()
        if task_name and self.run_command(f'schtasks /end /tn "{task_name}"') is not None:
            messagebox.showinfo("Success", f"Task stopped.")

    def delete_task(self):
        task_name = self.get_selected_task()
        if task_name:
            if messagebox.askyesno("Confirm", f"Are you sure you want to delete '{task_name}'?"):
                if self.run_command(f'schtasks /delete /tn "{task_name}" /f') is not None:
                    self.refresh_task_list()

if __name__ == "__main__":
    root = tk.Tk()
    app = SchtasksGUI(root)
    root.mainloop()