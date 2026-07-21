import json
import os
import queue
import re
import subprocess
import tempfile
import threading
import time
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class FoXYiZGui:
    PROGRESS_RE = re.compile(r"Progress:\s*\|.*\|\s*([\d.]+)%\s*\((\d+)/(\d+)\s+plans\)")
    OUTPUT_DIR_RE = re.compile(r"Output Directory:\s*(.+)")
    DASHBOARD_RE = re.compile(r"Dashboard:\s*(.+)")

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("FoXYiZ Runner")
        self.root.geometry("980x700")

        self.util_dir = Path(__file__).resolve().parent
        self.project_root = self.util_dir.parent
        self.f_dir = self.project_root / "f"
        self.fstart_path = self.f_dir / "fStart" / "default.json"

        self.output_queue: queue.Queue[str] = queue.Queue()
        self.process: subprocess.Popen | None = None
        self.run_thread: threading.Thread | None = None
        self.run_start_ts: float | None = None
        self.dashboard_paths: list[Path] = []
        self.unicode_pipe_error_detected = False
        self.safe_mode_running = False
        self.safe_pulse_after_id: str | None = None

        self.exe_var = tk.StringVar(value=str(self._default_executable_path()))
        self.thread_count_var = tk.StringVar(value="4")
        self.timeout_var = tk.StringVar(value="3")
        self.headless_var = tk.BooleanVar(value=False)
        self.debug_var = tk.BooleanVar(value=False)
        self.tags_var = tk.StringVar(value="")

        self.progress_var = tk.DoubleVar(value=0.0)
        self.status_var = tk.StringVar(value="Ready")
        self.eta_var = tk.StringVar(value="ETA: --")

        self._build_ui()
        self._load_from_fstart()
        self._poll_output()

    def _default_executable_path(self) -> Path:
        root = self.f_dir.parent
        candidates = [
            root / "FoXYiZ.exe",
            root / "Foxyiz.exe",
            self.f_dir / "FoXYiZ.exe",
            self.f_dir / "Foxyiz.exe",
            self.f_dir / "foxyiz.exe",
            self.f_dir / "Foxyiz",
            self.f_dir / "foxyiz",
        ]
        for path in candidates:
            if path.exists():
                return path
        return root / "FoXYiZ.exe"

    def _build_ui(self) -> None:
        frm_top = ttk.Frame(self.root, padding=10)
        frm_top.pack(fill=tk.X)

        ttk.Label(frm_top, text="Executable").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm_top, textvariable=self.exe_var, width=90).grid(
            row=0, column=1, sticky="ew", padx=6
        )
        ttk.Button(frm_top, text="Browse", command=self._pick_executable).grid(row=0, column=2)

        frm_top.columnconfigure(1, weight=1)

        frm_cfg = ttk.LabelFrame(self.root, text="fStart.json Settings", padding=10)
        frm_cfg.pack(fill=tk.X, padx=10, pady=(2, 8))

        ttk.Label(frm_cfg, text="Thread Count").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm_cfg, textvariable=self.thread_count_var, width=10).grid(row=0, column=1, sticky="w", padx=(6, 20))

        ttk.Label(frm_cfg, text="Timeout").grid(row=0, column=2, sticky="w")
        ttk.Entry(frm_cfg, textvariable=self.timeout_var, width=10).grid(row=0, column=3, sticky="w", padx=(6, 20))

        ttk.Checkbutton(frm_cfg, text="Headless", variable=self.headless_var).grid(row=0, column=4, sticky="w", padx=(0, 20))
        ttk.Checkbutton(frm_cfg, text="Debug", variable=self.debug_var).grid(row=0, column=5, sticky="w")

        ttk.Label(frm_cfg, text="Tags (comma-separated)").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frm_cfg, textvariable=self.tags_var, width=70).grid(row=1, column=1, columnspan=5, sticky="ew", padx=6, pady=(10, 0))
        frm_cfg.columnconfigure(1, weight=1)

        frm_configs = ttk.LabelFrame(self.root, text="yPAD Config Selection", padding=10)
        frm_configs.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 8))

        self.config_listbox = tk.Listbox(frm_configs, selectmode=tk.EXTENDED, height=7)
        self.config_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(frm_configs, orient=tk.VERTICAL, command=self.config_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.config_listbox.config(yscrollcommand=sb.set)

        frm_buttons = ttk.Frame(self.root, padding=(10, 0))
        frm_buttons.pack(fill=tk.X)
        ttk.Button(frm_buttons, text="Reload fStart + yPADs", command=self._load_from_fstart).pack(side=tk.LEFT)
        ttk.Button(frm_buttons, text="Save fStart.json", command=self._save_fstart).pack(side=tk.LEFT, padx=6)
        self.btn_run = ttk.Button(frm_buttons, text="Execute", command=self._start_run)
        self.btn_run.pack(side=tk.LEFT, padx=6)
        self.btn_stop = ttk.Button(frm_buttons, text="Stop", command=self._stop_run, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT)

        frm_progress = ttk.LabelFrame(self.root, text="Execution Progress", padding=10)
        frm_progress.pack(fill=tk.X, padx=10, pady=8)
        ttk.Progressbar(frm_progress, variable=self.progress_var, maximum=100, length=760).pack(fill=tk.X)
        ttk.Label(frm_progress, textvariable=self.status_var).pack(anchor="w", pady=(6, 0))
        ttk.Label(frm_progress, textvariable=self.eta_var).pack(anchor="w")

        frm_log = ttk.LabelFrame(self.root, text="Live Output", padding=10)
        frm_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        self.log_text = tk.Text(frm_log, height=14, wrap=tk.NONE)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

        frm_dash = ttk.LabelFrame(self.root, text="Run Dashboards", padding=10)
        frm_dash.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))
        self.dashboard_list = tk.Listbox(frm_dash, height=4)
        self.dashboard_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.dashboard_list.bind("<Double-Button-1>", lambda _e: self._open_selected_dashboard())
        dash_sb = ttk.Scrollbar(frm_dash, orient=tk.VERTICAL, command=self.dashboard_list.yview)
        dash_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.dashboard_list.config(yscrollcommand=dash_sb.set)

    def _pick_executable(self) -> None:
        picked = filedialog.askopenfilename(
            title="Select FoXYiZ executable",
            initialdir=str(self.f_dir),
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if picked:
            self.exe_var.set(picked)

    @staticmethod
    def _normalize_exe_text(value: str) -> str:
        # Handle plain quotes and escaped quotes copied from logs/UI.
        cleaned = value.strip()
        cleaned = cleaned.replace('\\"', '"').replace("\\'", "'")
        cleaned = cleaned.strip().strip('"').strip("'")
        # If any stray quote characters remain, remove them.
        cleaned = cleaned.replace('"', "").replace("'", "")
        return cleaned

    def _discover_configs(self) -> list[str]:
        """Find all suite JSON files under y/ (root and subfolders)."""
        y_dir = self.project_root / "y"
        if not y_dir.is_dir():
            return []
        configs: list[str] = []
        for path in sorted(y_dir.glob("**/*.json")):
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(data, dict) and "input_files" in data:
                configs.append(path.relative_to(self.project_root).as_posix())
        return configs

    def _load_from_fstart(self) -> None:
        if not self.fstart_path.exists():
            messagebox.showerror("Missing file", f"Could not find {self.fstart_path}")
            return

        data = json.loads(self.fstart_path.read_text(encoding="utf-8"))

        self.thread_count_var.set(str(data.get("thread_count", 4)))
        self.timeout_var.set(str(data.get("timeout", 3)))
        self.headless_var.set(bool(data.get("headless", False)))
        self.debug_var.set(bool(data.get("debug", False)))
        self.tags_var.set(",".join(data.get("tags", [])))

        discovered = self._discover_configs()
        self.config_listbox.delete(0, tk.END)
        for cfg in discovered:
            self.config_listbox.insert(tk.END, cfg)

        selected = set(data.get("configs", []))
        for idx, cfg in enumerate(discovered):
            if cfg in selected:
                self.config_listbox.selection_set(idx)

    def _save_fstart(self) -> bool:
        try:
            selected = self._selected_configs()
            if not selected:
                messagebox.showwarning("No yPAD selected", "Select at least one config in the yPAD list.")
                return False

            tags = [t.strip() for t in self.tags_var.get().split(",") if t.strip()]
            data = {
                "configs": selected,
                "thread_count": int(self.thread_count_var.get()),
                "timeout": int(self.timeout_var.get()),
                "headless": bool(self.headless_var.get()),
                "debug": bool(self.debug_var.get()),
                "tags": tags,
            }
            self.fstart_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return True
        except ValueError:
            messagebox.showerror("Invalid input", "Thread Count and Timeout must be integers.")
            return False
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            return False

    def _selected_configs(self) -> list[str]:
        return [self.config_listbox.get(i) for i in self.config_listbox.curselection()]

    def _start_run(self) -> None:
        if self.process is not None:
            return
        if not self._save_fstart():
            return

        exe = Path(self._normalize_exe_text(self.exe_var.get()))
        if not exe.exists():
            messagebox.showerror("Executable not found", f"Could not find executable:\n{exe}")
            return

        self._reset_run_ui()
        self.btn_run.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_var.set("Starting FoXYiZ...")
        self.run_start_ts = time.time()

        # On Windows, avoid piped stdout by default because FoXYiZ can crash
        # with cp1252 UnicodeEncodeError when writing progress symbols.
        if os.name == "nt":
            self._start_safe_console_run(exe)
            return

        def worker() -> None:
            cmd_file_path: Path | None = None
            try:
                child_env = dict(os.environ)
                # Prevent Windows codepage crashes when FoXYiZ prints Unicode symbols.
                child_env["PYTHONIOENCODING"] = "utf-8"
                child_env["PYTHONUTF8"] = "1"
                if os.name == "nt":
                    # Use a temporary launcher script to avoid cmd quoting issues.
                    exe_cmd = self._normalize_exe_text(str(exe))
                    with tempfile.NamedTemporaryFile(
                        mode="w",
                        suffix=".cmd",
                        delete=False,
                        encoding="utf-8",
                        newline="\r\n",
                    ) as cmd_file:
                        cmd_file.write("@echo off\n")
                        cmd_file.write("chcp 65001>nul\n")
                        cmd_file.write(f"\"{exe_cmd}\"\n")
                        cmd_file_path = Path(cmd_file.name)
                    popen_args = ["cmd", "/d", "/c", str(cmd_file_path)]
                else:
                    popen_args = [str(exe)]
                self.process = subprocess.Popen(
                    popen_args,
                    cwd=str(exe.parent),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=child_env,
                )
                assert self.process.stdout is not None
                for line in self.process.stdout:
                    self.output_queue.put(line.rstrip("\n"))
                self.process.wait()
                self.output_queue.put(f"[PROCESS_EXIT] {self.process.returncode}")
            except Exception as exc:
                self.output_queue.put(f"[ERROR] {exc}")
            finally:
                self.process = None
                if cmd_file_path and cmd_file_path.exists():
                    try:
                        cmd_file_path.unlink()
                    except OSError:
                        pass

        self.run_thread = threading.Thread(target=worker, daemon=True)
        self.run_thread.start()

    def _start_safe_console_run(self, exe: Path) -> None:
        """Fallback: run exe in a real console to avoid pipe encoding crash."""
        self.safe_mode_running = True
        self.status_var.set("Running in safe console mode...")
        self._start_safe_pulse()
        self._append_log("[INFO] Running in safe console mode (Windows default).")

        z_dir = self.project_root / "z"
        before_dash = set(str(p) for p in z_dir.glob("**/*zDash.html")) if z_dir.exists() else set()

        def worker() -> None:
            try:
                child_env = dict(os.environ)
                child_env["PYTHONIOENCODING"] = "utf-8"
                child_env["PYTHONUTF8"] = "1"
                creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
                proc = subprocess.Popen(
                    [str(exe)],
                    cwd=str(exe.parent),
                    env=child_env,
                    creationflags=creationflags,
                )
                rc = proc.wait()
                self.output_queue.put(f"[SAFE_PROCESS_EXIT] {rc}")
            except Exception as exc:
                self.output_queue.put(f"[ERROR] Safe mode failed: {exc}")
            finally:
                # Discover new dashboards from this run.
                if z_dir.exists():
                    after_dash = [str(p) for p in z_dir.glob("**/*zDash.html")]
                    for p in after_dash:
                        if p not in before_dash:
                            self.output_queue.put(f"[DASHBOARD] {p}")

        threading.Thread(target=worker, daemon=True).start()

    def _start_safe_pulse(self) -> None:
        def pulse() -> None:
            if not self.safe_mode_running:
                return
            next_val = (self.progress_var.get() + 4) % 100
            self.progress_var.set(next_val)
            self.safe_pulse_after_id = self.root.after(200, pulse)

        if self.safe_pulse_after_id is None:
            pulse()

    def _stop_safe_pulse(self) -> None:
        if self.safe_pulse_after_id is not None:
            try:
                self.root.after_cancel(self.safe_pulse_after_id)
            except Exception:
                pass
            self.safe_pulse_after_id = None

    def _stop_run(self) -> None:
        if self.process is None:
            return
        try:
            self.process.terminate()
            self.output_queue.put("[INFO] Stop requested by user.")
        except Exception as exc:
            self.output_queue.put(f"[ERROR] Failed to stop process: {exc}")

    def _reset_run_ui(self) -> None:
        self.dashboard_paths.clear()
        self.dashboard_list.delete(0, tk.END)
        self.progress_var.set(0)
        self.eta_var.set("ETA: --")
        self.unicode_pipe_error_detected = False
        self.safe_mode_running = False
        self._stop_safe_pulse()
        self._append_log("\n=== New Run ===\n")

    def _append_log(self, line: str) -> None:
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, line + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _poll_output(self) -> None:
        while not self.output_queue.empty():
            line = self.output_queue.get_nowait()
            self._append_log(line)
            self._handle_output_line(line)
        self.root.after(120, self._poll_output)

    def _handle_output_line(self, line: str) -> None:
        m = self.PROGRESS_RE.search(line)
        if m:
            pct = float(m.group(1))
            cur = int(m.group(2))
            total = int(m.group(3))
            self.progress_var.set(pct)
            self.status_var.set(f"Running... {pct:.1f}% ({cur}/{total} plans)")
            self._update_eta(pct)

        m_out = self.OUTPUT_DIR_RE.search(line)
        if m_out:
            out_dir = m_out.group(1).strip()
            self.status_var.set(f"Running | Output: {out_dir}")

        m_dash = self.DASHBOARD_RE.search(line)
        if m_dash:
            path = Path(m_dash.group(1).strip())
            if path not in self.dashboard_paths:
                self.dashboard_paths.append(path)
                self.dashboard_list.insert(tk.END, str(path))

        if line.startswith("[DASHBOARD]"):
            raw = line.replace("[DASHBOARD]", "", 1).strip()
            path = Path(raw)
            if path not in self.dashboard_paths:
                self.dashboard_paths.append(path)
                self.dashboard_list.insert(tk.END, str(path))

        if "UnicodeEncodeError" in line and "cp1252" in line:
            self.unicode_pipe_error_detected = True

        if line.startswith("[PROCESS_EXIT]"):
            rc = int(line.split()[-1])
            # Auto-retry in safe mode for known Windows pipe encoding failure.
            if (
                rc != 0
                and self.unicode_pipe_error_detected
                and not self.safe_mode_running
            ):
                exe = Path(self._normalize_exe_text(self.exe_var.get()))
                if exe.exists():
                    self._start_safe_console_run(exe)
                    return
            self.btn_run.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            if rc == 0:
                self.progress_var.set(100)
                self.status_var.set("Execution completed successfully.")
                self.eta_var.set("ETA: done")
            else:
                self.status_var.set(f"Execution finished with code {rc}.")
                self.eta_var.set("ETA: --")

        if line.startswith("[SAFE_PROCESS_EXIT]"):
            rc = int(line.split()[-1])
            self.safe_mode_running = False
            self._stop_safe_pulse()
            self.btn_run.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            if rc == 0:
                self.progress_var.set(100)
                self.status_var.set("Execution completed successfully (safe mode).")
                self.eta_var.set("ETA: done")
            else:
                self.status_var.set(f"Execution finished with code {rc} (safe mode).")
                self.eta_var.set("ETA: --")

        if line.startswith("[ERROR]"):
            self.btn_run.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            self.status_var.set("Execution failed to start.")
            self.eta_var.set("ETA: --")

    def _update_eta(self, pct: float) -> None:
        if pct <= 0 or self.run_start_ts is None:
            self.eta_var.set("ETA: --")
            return
        elapsed = time.time() - self.run_start_ts
        total_est = elapsed / (pct / 100.0)
        remain = max(0, int(total_est - elapsed))
        mins, secs = divmod(remain, 60)
        self.eta_var.set(f"ETA: {mins:02d}:{secs:02d}")

    def _open_selected_dashboard(self) -> None:
        selection = self.dashboard_list.curselection()
        if not selection:
            return
        path = self.dashboard_list.get(selection[0])
        if Path(path).exists():
            webbrowser.open(Path(path).resolve().as_uri())
        else:
            messagebox.showwarning("Missing file", f"Dashboard not found:\n{path}")


def main() -> None:
    root = tk.Tk()
    app = FoXYiZGui(root)
    _ = app
    root.mainloop()


if __name__ == "__main__":
    main()