import json
import re
import urllib.request
import urllib.error
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


def fetch_latest_npm_version(package_name: str) -> str | None:
    """Fetch the latest published version of an npm package from the npm registry."""
    url = f"https://registry.npmjs.org/{package_name}/latest"
    req = urllib.request.Request(
        url, headers={"User-Agent": "TauriVersionSyncApp/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return data.get("version")
    except Exception:
        pass
    return None


def extract_major_minor(version_str: str) -> str:
    """Extract major and minor version numbers (e.g., '2.5.6' -> '2.5')."""
    # Remove semver prefixes like ^, ~, >=, =
    clean_version = re.sub(r"^[^\d]+", "", version_str.strip())
    parts = clean_version.split(".")
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[1]}"
    elif len(parts) == 1:
        return parts[0]
    return clean_version


class TauriPluginSyncApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tauri v2 Plugin Sync Tool")
        self.geometry("780x520")
        self.minsize(650, 400)

        # Apply a clean theme style
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.project_dir = None
        self.scan_results = []  # List of dicts storing package/plugin state

        self.create_widgets()

    def create_widgets(self):
        # Top Frame: Path selection
        top_frame = ttk.LabelFrame(self, text=" Project Directory ", padding=10)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        self.path_entry = ttk.Entry(top_frame, font=("Segoe UI", 9))
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        btn_browse = ttk.Button(top_frame, text="Browse...", command=self.browse_directory)
        btn_browse.pack(side=tk.LEFT, padx=2)

        btn_scan = ttk.Button(top_frame, text="Scan & Fetch Latest", command=self.start_scan_thread)
        btn_scan.pack(side=tk.LEFT, padx=2)

        # Center Frame: Treeview Table
        center_frame = ttk.Frame(self, padding=10)
        center_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("npm_package", "cargo_crate", "latest_npm", "target_toml")
        self.tree = ttk.Treeview(center_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("npm_package", text="NPM Package (@tauri-apps/plugin-*)")
        self.tree.heading("cargo_crate", text="Cargo Crate (tauri-plugin-*)")
        self.tree.heading("latest_npm", text="Latest NPM Version")
        self.tree.heading("target_toml", text="Target Cargo Version (X.Y)")

        self.tree.column("npm_package", width=220, anchor=tk.W)
        self.tree.column("cargo_crate", width=200, anchor=tk.W)
        self.tree.column("latest_npm", width=140, anchor=tk.CENTER)
        self.tree.column("target_toml", width=160, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(center_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom Frame: Status bar & Sync Action
        bottom_frame = ttk.Frame(self, padding=10)
        bottom_frame.pack(fill=tk.X)

        self.status_var = tk.StringVar(value="Select a project folder containing package.json and src-tauri/Cargo.toml")
        self.status_label = ttk.Label(bottom_frame, textvariable=self.status_var, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_sync = ttk.Button(bottom_frame, text="Update Cargo.toml", command=self.apply_cargo_updates, state=tk.DISABLED)
        self.btn_sync.pack(side=tk.RIGHT)

    def browse_directory(self):
        selected = filedialog.askdirectory(title="Select Tauri Project Root Folder")
        if selected:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, selected)
            self.project_dir = Path(selected)

    def start_scan_thread(self):
        path_str = self.path_entry.get().strip()
        if not path_str:
            messagebox.showwarning("Warning", "Please select or paste a project directory path first.")
            return

        p = Path(path_str)
        package_json_path = p / "package.json"
        cargo_toml_path = p / "src-tauri" / "Cargo.toml"

        if not package_json_path.exists():
            messagebox.showerror("Error", f"Could not find package.json in:\n{p}")
            return

        if not cargo_toml_path.exists():
            messagebox.showerror("Error", f"Could not find src-tauri/Cargo.toml in:\n{p}")
            return

        self.project_dir = p
        self.status_var.set("Scanning dependencies and querying npm registry...")
        self.btn_sync.config(state=tk.DISABLED)

        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Run fetch in background thread so GUI doesn't freeze
        threading.Thread(target=self.scan_and_fetch, daemon=True).start()

    def scan_and_fetch(self):
        package_json_path = self.project_dir / "package.json"

        try:
            with open(package_json_path, "r", encoding="utf-8") as f:
                pkg_data = json.load(f)
        except Exception as e:
            self.status_var.set(f"Error reading package.json: {e}")
            return

        # Combine dependencies and devDependencies
        deps = {}
        deps.update(pkg_data.get("dependencies", {}))
        deps.update(pkg_data.get("devDependencies", {}))

        # Filter Tauri v2 plugins, ignoring CLI packages (e.g. @tauri-apps/cli)
        tauri_plugins = [
            pkg for pkg in deps.keys()
            if pkg.startswith("@tauri-apps/plugin-")
        ]

        if not tauri_plugins:
            self.status_var.set("No Tauri v2 plugin dependencies found in package.json.")
            return

        self.scan_results = []
        for pkg_name in tauri_plugins:
            latest_version = fetch_latest_npm_version(pkg_name)
            
            # Convert NPM package name '@tauri-apps/plugin-dialog' -> Cargo crate name 'tauri-plugin-dialog'
            plugin_suffix = pkg_name.replace("@tauri-apps/plugin-", "")
            cargo_crate = f"tauri-plugin-{plugin_suffix}"

            if latest_version:
                target_ver = extract_major_minor(latest_version)
            else:
                latest_version = "Failed to fetch"
                target_ver = "N/A"

            item_data = {
                "npm_package": pkg_name,
                "cargo_crate": cargo_crate,
                "latest_npm": latest_version,
                "target_toml": target_ver,
            }
            self.scan_results.append(item_data)

            # Update Treeview in main thread safely
            self.tree.after(0, self._add_tree_item, item_data)

        self.tree.after(0, self._scan_finished)

    def _add_tree_item(self, data):
        self.tree.insert("", tk.END, values=(
            data["npm_package"],
            data["cargo_crate"],
            data["latest_npm"],
            data["target_toml"]
        ))

    def _scan_finished(self):
        self.status_var.set(f"Finished. Found {len(self.scan_results)} Tauri plugin(s).")
        if self.scan_results:
            self.btn_sync.config(state=tk.NORMAL)

    def apply_cargo_updates(self):
        cargo_toml_path = self.project_dir / "src-tauri" / "Cargo.toml"
        if not cargo_toml_path.exists():
            messagebox.showerror("Error", "Cargo.toml not found.")
            return

        try:
            with open(cargo_toml_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Could not read Cargo.toml: {e}")
            return

        updated_count = 0
        new_content = content

        for item in self.scan_results:
            crate = item["cargo_crate"]
            target_ver = item["target_toml"]

            if target_ver == "N/A":
                continue

            # Pattern matches lines like:
            # tauri-plugin-dialog = "2.0"
            # tauri-plugin-dialog = { version = "2.0.1", features = [...] }
            # tauri-plugin-dialog.workspace = true (skipped)
            pattern = re.compile(rf'^(\s*{re.escape(crate)}\s*=\s*)(?:"[^"]*"|\{{\s*version\s*=\s*"[^"]*")', re.MULTILINE)

            def replacer(match):
                prefix = match.group(1)
                if "version =" in match.group(0):

                    # Preserves inline table metadata if present
                    return re.sub(r'version\s*=\s*"[^"]*"', f'version = "{target_ver}"', match.group(0))
                else:
                    return f'{prefix}"{target_ver}"'

            if pattern.search(new_content):
                new_content, count = pattern.subn(replacer, new_content)
                if count > 0:
                    updated_count += count

        if updated_count > 0:
            try:
                with open(cargo_toml_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                messagebox.showinfo("Success", f"Successfully updated {updated_count} plugin version(s) in:\nsrc-tauri/Cargo.toml")
                self.status_var.set(f"Updated {updated_count} crate entry/entries in Cargo.toml.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to write Cargo.toml: {e}")
        else:
            messagebox.showinfo("No Changes", "No matching crate dependencies found in Cargo.toml to update.")

if __name__ == "__main__":
    app = TauriPluginSyncApp()
    app.mainloop()