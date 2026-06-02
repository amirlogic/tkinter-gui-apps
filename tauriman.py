import os
import re
import json
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

class TauriManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tauri v2 Project Manager")
        self.root.geometry("850x650")
        self.root.minsize(700, 500)

        self.project_dir = tk.StringVar(value=os.getcwd())
        self.package_manager = "pnpm"

        self.create_layout()
        self.refresh_project_context()

    def create_layout(self):
        # --- Top Directory Selector ---
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="Project Directory:").pack(side=tk.LEFT, padx=5)
        self.dir_entry = ttk.Entry(top_frame, textvariable=self.project_dir, width=50)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_btn = ttk.Button(top_frame, text="Browse...", command=self.browse_directory)
        browse_btn.pack(side=tk.LEFT, padx=5)

        # --- Info Bar ---
        self.info_label = ttk.Label(self.root, text="Package Manager Detected: None", font=("Arial", 10, "italic"))
        self.info_label.pack(anchor=tk.W, padx=15, pady=2)

        # --- Notebook Layout ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Setup individual tabs
        self.setup_plugins_tab()
        self.setup_config_tab()
        self.setup_cargo_tab()

    # --------------------------------------------------------
    # TAB 1: PLUGINS
    # --------------------------------------------------------
    def setup_plugins_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Plugins")

        # Top splitting layout
        top_paned = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        top_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel: Installed list
        left_frame = ttk.LabelFrame(top_paned, text="Installed Plugins", padding=10)
        top_paned.add(left_frame, weight=1)

        self.plugins_listbox = tk.Listbox(left_frame, height=8)
        self.plugins_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        list_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.plugins_listbox.yview)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.plugins_listbox.config(yscrollcommand=list_scroll.set)

        # Right panel: Installation Tools
        right_frame = ttk.LabelFrame(top_paned, text="Install New Plugin", padding=10)
        top_paned.add(right_frame, weight=1)

        ttk.Label(right_frame, text="Plugin Name (e.g., store, notification):").pack(anchor=tk.W, pady=2)
        self.plugin_name_entry = ttk.Entry(right_frame)
        self.plugin_name_entry.pack(fill=tk.X, pady=5)

        install_btn = ttk.Button(right_frame, text="Install Plugin", command=self.install_plugin)
        install_btn.pack(anchor=tk.E, pady=5)

        refresh_btn = ttk.Button(right_frame, text="Scan / Refresh List", command=self.scan_installed_plugins)
        refresh_btn.pack(anchor=tk.E, pady=5)

        # Bottom Frame: Terminal Output
        output_frame = ttk.LabelFrame(tab, text="Terminal Output", padding=5)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.plugins_output = scrolledtext.ScrolledText(output_frame, height=10, bg="black", fg="white", insertbackground="white", font=("Courier", 10))
        self.plugins_output.pack(fill=tk.BOTH, expand=True)
        self.plugins_output.configure(state='disabled')

    # --------------------------------------------------------
    # TAB 2: CONFIG
    # --------------------------------------------------------
    def setup_config_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Config")

        btn_frame = ttk.Frame(tab, padding=5)
        btn_frame.pack(fill=tk.X)

        load_btn = ttk.Button(btn_frame, text="Reload tauri.conf.json", command=self.load_config_file)
        load_btn.pack(side=tk.LEFT, padx=5)

        save_btn = ttk.Button(btn_frame, text="Save Changes", command=self.save_config_file)
        save_btn.pack(side=tk.LEFT, padx=5)

        self.config_editor = scrolledtext.ScrolledText(tab, bg="#1e1e1e", fg="#d4d4d4", insertbackground="white", font=("Courier", 11), undo=True)
        self.config_editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    # --------------------------------------------------------
    # TAB 3: CARGO
    # --------------------------------------------------------
    def setup_cargo_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Cargo")

        btn_frame = ttk.Frame(tab, padding=10)
        btn_frame.pack(fill=tk.X)

        check_btn = ttk.Button(btn_frame, text="Cargo Check", command=lambda: self.run_cargo_command("cargo check"))
        check_btn.pack(side=tk.LEFT, padx=10, pady=5, expand=True, fill=tk.X)

        clean_btn = ttk.Button(btn_frame, text="Cargo Clean", command=lambda: self.run_cargo_command("cargo clean"))
        clean_btn.pack(side=tk.LEFT, padx=10, pady=5, expand=True, fill=tk.X)

        upgrade_btn = ttk.Button(btn_frame, text="Cargo Upgrade", command=lambda: self.run_cargo_command("cargo upgrade"))
        upgrade_btn.pack(side=tk.LEFT, padx=10, pady=5, expand=True, fill=tk.X)

        output_frame = ttk.LabelFrame(tab, text="Terminal Output", padding=5)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.cargo_output = scrolledtext.ScrolledText(output_frame, bg="black", fg="white", insertbackground="white", font=("Courier", 10))
        self.cargo_output.pack(fill=tk.BOTH, expand=True)
        self.cargo_output.configure(state='disabled')

    # --------------------------------------------------------
    # LOGIC & UTILITIES
    # --------------------------------------------------------
    def browse_directory(self):
        selected = filedialog.askdirectory(initialdir=self.project_dir.get())
        if selected:
            self.project_dir.set(selected)
            self.refresh_project_context()

    def refresh_project_context(self):
        path = self.project_dir.get()
        if not os.path.exists(path):
            return

        # 1. Detect Package Manager
        if os.path.exists(os.path.join(path, "pnpm-lock.yaml")):
            self.package_manager = "pnpm"
        elif os.path.exists(os.path.join(path, "package-lock.json")):
            self.package_manager = "npm"
        elif os.path.exists(os.path.join(path, "yarn.lock")):
            self.package_manager = "yarn"
        elif os.path.exists(os.path.join(path, "bun.lockb")) or os.path.exists(os.path.join(path, "bun.lock")):
            self.package_manager = "bun"
        else:
            self.package_manager = "pnpm" # Default fall-back

        self.info_label.config(text=f"Package Manager Detected: {self.package_manager}")
        
        # 2. Update downstream fields
        self.scan_installed_plugins()
        self.load_config_file()

    def scan_installed_plugins(self):
        self.plugins_listbox.delete(0, tk.END)
        path = self.project_dir.get()
        found_plugins = set()

        # Parse Cargo.toml for standard tauri-plugins
        cargo_path = os.path.join(path, "src-tauri", "Cargo.toml")
        if os.path.exists(cargo_path):
            try:
                with open(cargo_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Find dependencies matching tauri-plugin-xxxxx
                    matches = re.findall(r'tauri-plugin-([\w-]+)', content)
                    for match in matches:
                        found_plugins.add(match)
            except Exception as e:
                self.log_to_widget(self.plugins_output, f"[Error Reading Cargo.toml]: {e}\n")

        # Parse package.json for web-side packages
        pkg_json_path = os.path.join(path, "package.json")
        if os.path.exists(pkg_json_path):
            try:
                with open(pkg_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    for key in deps.keys():
                        if key.startswith("@tauri-apps/plugin-"):
                            found_plugins.add(key.replace("@tauri-apps/plugin-", ""))
            except Exception as e:
                self.log_to_widget(self.plugins_output, f"[Error Reading package.json]: {e}\n")

        if found_plugins:
            for plugin in sorted(found_plugins):
                self.plugins_listbox.insert(tk.END, f"🔌 {plugin}")
        else:
            self.plugins_listbox.insert(tk.END, "No plugins detected.")

    def install_plugin(self):
        plugin_name = self.plugin_name_entry.get().strip()
        if not plugin_name:
            messagebox.showwarning("Warning", "Please enter a valid plugin name.")
            return

        # Handle formatting formatting standard syntax variants seamlessly
        plugin_name = plugin_name.replace("tauri-plugin-", "").replace("@tauri-apps/plugin-", "")
        
        # Formulate exact instruction string required
        command = f"{self.package_manager} tauri add {plugin_name}"
        
        self.log_to_widget(self.plugins_output, f"\n> Executing: {command}\n")
        threading.Thread(target=self.execute_shell_cmd, args=(command, self.plugins_output, self.scan_installed_plugins), daemon=True).start()

    def load_config_file(self):
        config_path = os.path.join(self.project_dir.get(), "src-tauri", "tauri.conf.json")
        self.config_editor.delete("1.0", tk.END)
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config_editor.insert(tk.END, f.read())
            except Exception as e:
                self.config_editor.insert(tk.END, f"Error opening configuration file:\n{e}")
        else:
            self.config_editor.insert(tk.END, f"Could not find configuration file at:\n{config_path}\nMake sure your active workspace holds a valid Tauri structure.")

    def save_config_file(self):
        config_path = os.path.join(self.project_dir.get(), "src-tauri", "tauri.conf.json")
        if not os.path.exists(config_path):
            messagebox.showerror("Error", "Target path tauri.conf.json configuration file non-existent.")
            return
            
        raw_content = self.config_editor.get("1.0", tk.END).strip()
        
        # Optional: Basic JSON syntax check prior to saving
        try:
            json.loads(raw_content)
        except json.JSONDecodeError as err:
            if not messagebox.askyesno("Invalid JSON syntax detected", f"JSON Syntax analysis returned syntax compilation errors:\n\n{err}\n\nDo you want to save anyway?"):
                return

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(raw_content)
            messagebox.showinfo("Success", "tauri.conf.json written successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed saving alterations to target configuration system:\n{e}")

    def run_cargo_command(self, command):
        # Target directory explicitly paths to /src-tauri when triggering Cargo actions
        cargo_working_dir = os.path.join(self.project_dir.get(), "src-tauri")
        
        if not os.path.exists(cargo_working_dir):
            messagebox.showerror("Error", "Missing directory: 'src-tauri' is required to run Cargo commands.")
            return

        self.log_to_widget(self.cargo_output, f"\n> Executing: {command}\n")
        threading.Thread(target=self.execute_shell_cmd, args=(command, self.cargo_output, None, cargo_working_dir), daemon=True).start()

    # --------------------------------------------------------
    # THREAD-SAFE ASYNC SHELL INTERFACING
    # --------------------------------------------------------
    def log_to_widget(self, widget, text):
        """Safely updates Tkinter UI elements from arbitrary threading tasks."""
        def append():
            widget.configure(state='normal')
            widget.insert(tk.END, text)
            widget.see(tk.END)
            widget.configure(state='disabled')
        self.root.after(0, append)

    def execute_shell_cmd(self, command, output_widget, on_complete_callback=None, alternative_cwd=None):
        cwd = alternative_cwd if alternative_cwd else self.project_dir.get()
        
        try:
            # shell=True ensures shell configuration variables/executables resolution matches terminal expectations
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Stream pipe output line-by-line while operational
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    self.log_to_widget(output_widget, line)
            
            return_code = process.poll()
            self.log_to_widget(output_widget, f"\n[Process concluded with return code: {return_code}]\n")
            
            if on_complete_callback:
                self.root.after(0, on_complete_callback)

        except Exception as e:
            self.log_to_widget(output_widget, f"\nAn application exception event occurred executing command chain:\n{str(e)}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = TauriManagerApp(root)
    root.mainloop()