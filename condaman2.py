import concurrent.futures
import os
import platform
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import END, Listbox, messagebox, simpledialog


def run_conda_command(args):
    try:
        result = subprocess.run(
            ["conda"] + args, text=True, capture_output=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr or e.stdout}"


def get_python_version(env_name):
    """Retrieve the Python version installed in a given conda environment."""
    output = run_conda_command(["list", "-n", env_name, "^python$"])
    for line in output.splitlines():
        if not line.startswith("#") and line.strip():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "python":
                return env_name, parts[1]
    return env_name, "N/A"


class CondaManagerApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Conda Environment Manager")

        self.env_map = {}

        self.status_label = tk.Label(
            self, text="Ready", anchor="w", fg="gray"
        )
        self.status_label.pack(fill=tk.X, padx=10, pady=(5, 0))

        self.env_listbox = Listbox(self, width=60)
        self.env_listbox.pack(padx=10, pady=10)

        btn_frame = tk.Frame(self)
        btn_frame.pack(padx=10, pady=5)

        self.btn_refresh = tk.Button(
            btn_frame, text="Refresh List", command=self.refresh_env_list
        )
        self.btn_refresh.pack(side=tk.LEFT, padx=5)

        self.btn_create = tk.Button(
            btn_frame, text="Create Env", command=self.create_env
        )
        self.btn_create.pack(side=tk.LEFT, padx=5)

        self.btn_delete = tk.Button(
            btn_frame, text="Delete Env", command=self.delete_env
        )
        self.btn_delete.pack(side=tk.LEFT, padx=5)

        terminal_frame = tk.Frame(self)
        terminal_frame.pack(padx=10, pady=5)

        tk.Button(
            terminal_frame,
            text="Launch Terminal",
            command=self.launch_terminal,
        ).pack(side=tk.LEFT, padx=5)

        self.refresh_env_list()

    def set_loading(self, is_loading, message="Loading..."):
        """Main-thread safe toggle for UI controls."""

        def _update_ui():
            state = tk.DISABLED if is_loading else tk.NORMAL
            self.btn_refresh.config(state=state)
            self.btn_create.config(state=state)
            self.btn_delete.config(state=state)
            self.status_label.config(text=message if is_loading else "Ready")

        self.after(0, _update_ui)

    def refresh_env_list(self):
        self.set_loading(True, "Fetching conda environments...")
        threading.Thread(target=self._fetch_envs_worker, daemon=True).start()

    def _fetch_envs_worker(self):
        output = run_conda_command(["env", "list"])
        env_names = []

        for line in output.splitlines():
            if line and not line.startswith("#"):
                parts = line.split()
                if parts and parts[0] != "*":
                    env_names.append(parts[0])

        env_versions = {}
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=5
        ) as executor:
            results = executor.map(get_python_version, env_names)
            for env_name, ver in results:
                env_versions[env_name] = ver

        self.after(0, self._update_listbox_ui, env_names, env_versions)

    def _update_listbox_ui(self, env_names, env_versions):
        self.env_listbox.delete(0, END)
        self.env_map.clear()

        for idx, env_name in enumerate(env_names):
            py_ver = env_versions.get(env_name, "N/A")
            display_text = f"{env_name:<25} (Python {py_ver})"
            self.env_listbox.insert(END, display_text)
            self.env_map[idx] = env_name

        self.set_loading(False)

    def create_env(self):
        env_name = simpledialog.askstring(
            "Create Environment", "Enter new environment name:"
        )
        if env_name:
            python_version = simpledialog.askstring(
                "Python Version",
                "Python version (e.g., 3.11 or leave empty for default):",
            )
            args = ["create", "-n", env_name, "-y"]
            if python_version and python_version.strip():
                args.append(f"python={python_version.strip()}")

            self.set_loading(True, f"Creating environment '{env_name}'...")
            threading.Thread(
                target=self._run_async_cmd,
                args=(args, "Environment created successfully!"),
                daemon=True,
            ).start()

    def delete_env(self):
        selected = self.env_listbox.curselection()
        if not selected:
            messagebox.showwarning("Warning", "Select an environment to delete.")
            return

        env_name = self.env_map[selected[0]]
        if messagebox.askyesno("Delete", f"Delete environment '{env_name}'?"):
            self.set_loading(True, f"Removing environment '{env_name}'...")
            args = ["env", "remove", "-n", env_name, "-y"]
            threading.Thread(
                target=self._run_async_cmd,
                args=(args, "Environment removed successfully!"),
                daemon=True,
            ).start()

    def _run_async_cmd(self, args, success_message):
        result = run_conda_command(args)
        self.after(0, self._on_cmd_complete, result, success_message)

    def _on_cmd_complete(self, result, success_message):
        if "Error" in result:
            messagebox.showerror("Error", result)
        else:
            messagebox.showinfo("Result", success_message)
        self.refresh_env_list()

    def launch_terminal(self):
        selected = self.env_listbox.curselection()
        if not selected:
            messagebox.showwarning("Warning", "Select an environment to launch.")
            return

        env_name = self.env_map[selected[0]]
        system_os = platform.system()

        if system_os == "Windows":
            dialog = tk.Toplevel(self)
            dialog.title("Select Shell")
            dialog.geometry("250x100")
            dialog.grab_set()

            tk.Label(dialog, text="Choose shell to launch:").pack(pady=5)

            def open_cmd():
                dialog.destroy()
                cmd = f'start cmd.exe /k "conda activate {env_name}"'
                subprocess.Popen(cmd, shell=True)

            def open_ps():
                dialog.destroy()
                ps_cmd = f"conda activate {env_name}"
                cmd = f'start powershell.exe -NoExit -Command "{ps_cmd}"'
                subprocess.Popen(cmd, shell=True)

            btn_box = tk.Frame(dialog)
            btn_box.pack(pady=5)
            tk.Button(btn_box, text="CMD", command=open_cmd, width=10).pack(
                side=tk.LEFT, padx=5
            )
            tk.Button(
                btn_box, text="PowerShell", command=open_ps, width=10
            ).pack(side=tk.LEFT, padx=5)

        elif system_os == "Darwin":
            cmd = f'osascript -e \'tell application "Terminal" to do script "conda activate {env_name}"\''
            subprocess.Popen(cmd, shell=True)

        else:
            cmd = f'x-terminal-emulator -e "bash -c \'conda activate {env_name}; exec bash\'"'
            subprocess.Popen(cmd, shell=True)


if __name__ == "__main__":
    app = CondaManagerApp()
    app.mainloop()