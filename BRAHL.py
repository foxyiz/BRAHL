#!/usr/bin/env python3
"""
BRAHL Desktop — Build · Run · Analyze · Heal · Loop (+ Verify · Report)

Desktop GUI for the FoXYiZ quality lifecycle (Docs/BRAHL.md):
  Step 0  Capture context (prompt + yPlans baseline) → z/brahl_context_*.json
  Loop 1  Full in-scope run → Analyze → Heal
  Loop 2  Failures only (Run=N on passes)
  Loop 3  Failures only
  Verify  Restore all Run=Y, full regression run
  Report  brahl_report.md in z/ (Verify run folder + flat index)

Launch from installation root:
  python BRAHL.py
"""

from __future__ import annotations

import csv
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

BRAHL_PHASES = ("Build", "Run", "Analyze", "Heal", "Loop")
A1_DEFECT_TAGS = ("Issue", "Link", "Security", "Element", "BrokenLink", "Regression")


class BrahLApp:
    PROGRESS_RE = re.compile(r"Progress:\s*\|.*\|\s*([\d.]+)%\s*\((\d+)/(\d+)\s+plans\)")
    OUTPUT_DIR_RE = re.compile(r"Output Directory:\s*(.+)")
    DASHBOARD_RE = re.compile(r"Dashboard:\s*(.+)")

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("BRAHL — Build · Run · Analyze · Heal · Loop · Verify · Report")
        self.root.geometry("1100x780")
        self.root.minsize(900, 640)

        self.project_root = Path(__file__).resolve().parent
        self.f_dir = self.project_root / "f"
        self.y_dir = self.project_root / "y"
        self.z_dir = self.project_root / "z"
        self.docs_dir = self.project_root / "Docs"
        self.fstart_path = self.f_dir / "fStart.json"
        self.brahl_md_path = self.docs_dir / "BRAHL.md"
        self._engine_helpers = None

        self.output_queue: queue.Queue[str] = queue.Queue()
        self.process: subprocess.Popen | None = None
        self.run_thread: threading.Thread | None = None
        self.run_start_ts: float | None = None
        self.safe_mode_running = False
        self.safe_pulse_after_id: str | None = None
        self.loop_running = False
        self.loop_cancel = False
        self.cycle_history: list[dict] = []
        self.brahl_context_path: Path | None = None

        self.exe_var = tk.StringVar(value=str(self._default_executable()))
        self.engine_py_var = tk.StringVar(value=str(self.f_dir / "fEngine2.py"))
        self.thread_count_var = tk.StringVar(value="1")
        self.timeout_var = tk.StringVar(value="6")
        self.headless_var = tk.BooleanVar(value=False)
        self.tags_var = tk.StringVar(value="Admin")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.status_var = tk.StringVar(value="Ready — BRAHL lifecycle for FoXYiZ")
        self.latest_run_var = tk.StringVar(value="(none)")
        self.fstart_config_var = tk.StringVar(value="f/fStart.json")
        self.cycle_prompt_var = tk.StringVar(value="")
        self.active_suite_var = tk.StringVar(value="(select config)")
        self.cycle_step_var = tk.StringVar(value="Idle")

        self.brahl_text = self._load_brahl_md()
        self._build_ui()
        self._refresh_fstart_combo()
        self._load_fstart()
        self._refresh_z_runs()
        self._poll_output()

    def _load_brahl_md(self) -> str:
        if self.brahl_md_path.is_file():
            return self.brahl_md_path.read_text(encoding="utf-8", errors="replace")
        return "# BRAHL\n\nDocs/BRAHL.md not found."

    def _default_executable(self) -> Path:
        for name in ("Foxyiz2.exe", "Foxyiz.exe", "foxyiz.exe"):
            p = self.f_dir / name
            if p.is_file():
                return p
        return self.f_dir / "Foxyiz2.exe"

    def _phase_blurb(self, phase: str) -> str:
        blurbs = {
            "Build": "Define yPAD (y1Plans, y2Actions, y3Designs). Explore first; add Issue/Link/Security/Element plans for A1 defects.",
            "Run": "Execute plans with fEngine2.py. Results → z/<timestamp>_<suite>/. Use fStart_*.json for suite + tags.",
            "Analyze": "Classify failures: T1 yPAD, T2 engine, T3 env, A1 app defect. Read _errors.csv, zDash, brahl_report.md.",
            "Heal": "Fix T1/T2/T3 only. Never weaken Issue/A1 tests. Prefer css= locators (commas in xpath break resolution).",
            "Loop": "Loop 1 (full) → Loop 2–3 (failures only, Run=N on passes) → Verify (restore Run=Y) → Report in z/.",
        }
        return blurbs.get(phase, "")

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=(12, 8))
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text="BRAHL — f(x,y)=z",
            font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT)
        ttk.Label(header, textvariable=self.status_var).pack(side=tk.RIGHT)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        self.tab_build = ttk.Frame(self.notebook, padding=10)
        self.tab_run = ttk.Frame(self.notebook, padding=10)
        self.tab_analyze = ttk.Frame(self.notebook, padding=10)
        self.tab_heal = ttk.Frame(self.notebook, padding=10)
        self.tab_loop = ttk.Frame(self.notebook, padding=10)
        self.tab_help = ttk.Frame(self.notebook, padding=10)

        for name, frame in zip(BRAHL_PHASES, (self.tab_build, self.tab_run, self.tab_analyze, self.tab_heal, self.tab_loop)):
            self.notebook.add(frame, text=name)
        self.notebook.add(self.tab_help, text="BRAHL Guide")

        self._build_build_tab()
        self._build_run_tab()
        self._build_analyze_tab()
        self._build_heal_tab()
        self._build_loop_tab()
        self._build_help_tab()

        log_frame = ttk.LabelFrame(self.root, text="Activity log", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _phase_header(self, parent: ttk.Frame, phase: str) -> None:
        ttk.Label(parent, text=phase, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(parent, text=self._phase_blurb(phase), wraplength=980).pack(anchor="w", pady=(2, 10))

    def _build_build_tab(self) -> None:
        self._phase_header(self.tab_build, "Build — yPAD")
        body = ttk.Frame(self.tab_build)
        body.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(body, text="Build checklist", padding=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        checks = [
            "Suite JSON loads all CSV paths",
            "ActionNames exist in x/xCapa.csv",
            "Reuse plans marked Run=N",
            "Smoke plans cover login + critical path",
            "Tags semicolon-separated (suite;Smoke;Issue)",
            "A1 defect plans tagged Issue/Link/Security/Element",
        ]
        self.build_check_vars = []
        for item in checks:
            var = tk.BooleanVar(value=False)
            self.build_check_vars.append(var)
            ttk.Checkbutton(left, text=item, variable=var).pack(anchor="w", pady=2)

        btns = ttk.Frame(left)
        btns.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(btns, text="Validate suite", command=self._validate_build).pack(side=tk.LEFT)
        ttk.Button(btns, text="Open y/", command=lambda: self._open_folder(self.y_dir)).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Visualize yPAD", command=self._run_yvisualizer).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Open visualization", command=self._open_y_visualization).pack(side=tk.LEFT)

        right = ttk.LabelFrame(body, text="Active suite yPAD (from fStart config)", padding=10)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.build_file_list = ttk.Frame(right)
        self.build_file_list.pack(fill=tk.BOTH, expand=True)
        self._refresh_build_file_list()

    def _build_run_tab(self) -> None:
        self._phase_header(self.tab_run, "Run — f/")
        cfg_pick = ttk.Frame(self.tab_run)
        cfg_pick.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(cfg_pick, text="fStart config:").pack(side=tk.LEFT)
        self.fstart_combo = ttk.Combobox(cfg_pick, textvariable=self.fstart_config_var, width=36, state="readonly")
        self.fstart_combo.pack(side=tk.LEFT, padx=6)
        self.fstart_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_fstart_selected())
        ttk.Button(cfg_pick, text="Reload", command=self._load_fstart).pack(side=tk.LEFT)

        cfg = ttk.LabelFrame(self.tab_run, text="Run configuration", padding=10)
        cfg.pack(fill=tk.X)

        ttk.Label(cfg, text="Executable").grid(row=0, column=0, sticky="w")
        ttk.Entry(cfg, textvariable=self.exe_var, width=70).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(cfg, text="Browse", command=self._pick_executable).grid(row=0, column=2)

        ttk.Label(cfg, text="Python engine").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(cfg, textvariable=self.engine_py_var, width=70).grid(row=1, column=1, sticky="ew", padx=6, pady=(8, 0))
        ttk.Button(cfg, text="Run with Python", command=self._start_python_run).grid(row=1, column=2, pady=(8, 0))

        ttk.Label(cfg, text="Thread count").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(cfg, textvariable=self.thread_count_var, width=8).grid(row=2, column=1, sticky="w", padx=6, pady=(8, 0))
        ttk.Label(cfg, text="Timeout").grid(row=2, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(cfg, textvariable=self.timeout_var, width=8).grid(row=2, column=3, sticky="w", padx=6, pady=(8, 0))
        ttk.Checkbutton(cfg, text="Headless", variable=self.headless_var).grid(row=2, column=4, sticky="w", pady=(8, 0))

        ttk.Label(cfg, text="Tags (comma-separated)").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(cfg, textvariable=self.tags_var, width=40).grid(row=3, column=1, columnspan=2, sticky="w", padx=6, pady=(8, 0))
        cfg.columnconfigure(1, weight=1)

        configs_frame = ttk.LabelFrame(self.tab_run, text="Suite configs", padding=10)
        configs_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        self.config_listbox = tk.Listbox(configs_frame, selectmode=tk.EXTENDED, height=6)
        self.config_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(configs_frame, orient=tk.VERTICAL, command=self.config_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.config_listbox.config(yscrollcommand=sb.set)

        run_btns = ttk.Frame(self.tab_run)
        run_btns.pack(fill=tk.X)
        ttk.Button(run_btns, text="Reload fStart", command=self._load_fstart).pack(side=tk.LEFT)
        ttk.Button(run_btns, text="Save fStart", command=self._save_fstart).pack(side=tk.LEFT, padx=6)
        self.btn_run = ttk.Button(run_btns, text="Run (exe)", command=self._start_exe_run)
        self.btn_run.pack(side=tk.LEFT, padx=6)
        self.btn_stop = ttk.Button(run_btns, text="Stop", command=self._stop_run, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT)

        prog = ttk.LabelFrame(self.tab_run, text="Progress", padding=10)
        prog.pack(fill=tk.X, pady=8)
        ttk.Progressbar(prog, variable=self.progress_var, maximum=100).pack(fill=tk.X)
        self.dashboard_list = tk.Listbox(prog, height=3)
        self.dashboard_list.pack(fill=tk.X, pady=(8, 0))
        self.dashboard_list.bind("<Double-Button-1>", lambda _e: self._open_selected_dashboard())
        self.dashboard_paths: list[Path] = []

    def _build_analyze_tab(self) -> None:
        self._phase_header(self.tab_analyze, "Analyze — z/")
        top = ttk.Frame(self.tab_analyze)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Latest run:").pack(side=tk.LEFT)
        ttk.Label(top, textvariable=self.latest_run_var).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Refresh runs", command=self._refresh_z_runs).pack(side=tk.LEFT, padx=8)
        ttk.Button(top, text="Open run folder", command=self._open_latest_run_folder).pack(side=tk.LEFT)
        ttk.Button(top, text="Open zDash", command=self._open_latest_dashboard).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Open BRAHL report", command=self._open_brahl_report).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Open context JSON", command=self._open_brahl_context).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Build defects dashboard", command=self._run_zdefects).pack(side=tk.LEFT, padx=6)

        mid = ttk.Frame(self.tab_analyze)
        mid.pack(fill=tk.BOTH, expand=True, pady=8)

        runs_frame = ttk.LabelFrame(mid, text="z/ runs", padding=8)
        runs_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 8))
        self.runs_listbox = tk.Listbox(runs_frame, width=36, height=14)
        self.runs_listbox.pack(fill=tk.BOTH, expand=True)
        self.runs_listbox.bind("<<ListboxSelect>>", lambda _e: self._on_run_selected())
        self.z_run_paths: list[Path] = []

        fail_frame = ttk.LabelFrame(mid, text="Failures + RCA hint (T1 yPAD / T2 engine / T3 env / A1 app)", padding=8)
        fail_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cols = ("plan", "step", "class", "output")
        self.fail_tree = ttk.Treeview(fail_frame, columns=cols, show="headings", height=14)
        for c, w in zip(cols, (180, 50, 70, 420)):
            self.fail_tree.heading(c, text=c.title())
            self.fail_tree.column(c, width=w, anchor="w")
        self.fail_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        fsb = ttk.Scrollbar(fail_frame, orient=tk.VERTICAL, command=self.fail_tree.yview)
        fsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.fail_tree.config(yscrollcommand=fsb.set)

    def _build_heal_tab(self) -> None:
        self._phase_header(self.tab_heal, "Heal — fix T1/T2/T3")
        body = ttk.Frame(self.tab_heal)
        body.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(body, text="Heal priority (active suite)", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        self.heal_file_btns = ttk.Frame(left)
        self.heal_file_btns.pack(fill=tk.X)
        self._refresh_heal_file_list()

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Button(left, text="Re-run (Run tab)", command=self._start_python_run).pack(fill=tk.X, pady=3)
        ttk.Button(left, text="Shrink to failures (Loop 2 prep)", command=self._shrink_plans_to_failures).pack(fill=tk.X, pady=3)
        ttk.Button(left, text="Restore all Run=Y (Verify prep)", command=self._restore_plans_run_y).pack(fill=tk.X, pady=3)
        if (self.f_dir / "fEngine.py").is_file():
            ttk.Button(left, text="LLM heal (fEngine.py --heal)", command=self._run_llm_heal).pack(fill=tk.X, pady=3)

        right = ttk.LabelFrame(body, text="Common heal patterns", padding=10)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        patterns = (
            "Comma in xpath locator → use css= selector (contains(.,'x') breaks CSV resolution)\n"
            "Perf timer lost between steps → fEngine2 shares UIActionHandler per plan\n"
            "Post-login not on expected page → xNavigate on session, not full login reuse\n"
            "Issue plan 'passes' on 404 → A1 defect documented; do NOT weaken assertion\n"
            "App-log API 429 → wait ~60s between full runs or disable redundant beacon plan\n"
            "Parallel perf timer fails → thread_count: 1 in fStart\n"
            "Admin tag finds 0 plans → engine tag split on ; or rebuild exe\n"
        )
        txt = scrolledtext.ScrolledText(right, height=12, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert("1.0", patterns)
        txt.config(state=tk.DISABLED)

        notes = ttk.LabelFrame(self.tab_heal, text="Heal notes (session)", padding=8)
        notes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.heal_notes = scrolledtext.ScrolledText(notes, height=5, wrap=tk.WORD)
        self.heal_notes.pack(fill=tk.BOTH, expand=True)

    def _build_loop_tab(self) -> None:
        self._phase_header(self.tab_loop, "Loop — Loop 1 → 2 → 3 → Verify → Report")
        top = ttk.LabelFrame(self.tab_loop, text="Step 0 — before Loop 1", padding=10)
        top.pack(fill=tk.X)
        ttk.Label(top, text="User prompt (verbatim — saved to brahl_context_*.json):").pack(anchor="w")
        self.cycle_prompt_text = scrolledtext.ScrolledText(top, height=3, wrap=tk.WORD)
        self.cycle_prompt_text.pack(fill=tk.X, pady=(4, 4))
        ttk.Label(top, text="Reference documents (paths relative to project root, one per line):").pack(anchor="w")
        self.cycle_docs_text = scrolledtext.ScrolledText(top, height=2, wrap=tk.WORD)
        self.cycle_docs_text.pack(fill=tk.X, pady=(4, 8))
        ttk.Button(top, text="Capture context (Step 0)", command=self._capture_brahl_context).pack(anchor="w")

        status_row = ttk.Frame(self.tab_loop)
        status_row.pack(fill=tk.X, pady=(8, 4))
        ttk.Label(status_row, text="Active suite:").pack(side=tk.LEFT)
        ttk.Label(status_row, textvariable=self.active_suite_var).pack(side=tk.LEFT, padx=6)
        ttk.Label(status_row, text="Cycle step:").pack(side=tk.LEFT, padx=(16, 0))
        ttk.Label(status_row, textvariable=self.cycle_step_var).pack(side=tk.LEFT, padx=6)

        btns = ttk.LabelFrame(self.tab_loop, text="BRAHL cycle steps", padding=10)
        btns.pack(fill=tk.X, pady=4)
        for label, step in (
            ("Loop 1 — full run", "Loop 1"),
            ("Loop 2 — failures only", "Loop 2"),
            ("Loop 3 — failures only", "Loop 3"),
            ("Verify — restore Run=Y + full run", "Verify"),
        ):
            ttk.Button(btns, text=label, command=lambda s=step: self._start_cycle_step(s)).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Generate report template", command=self._generate_brahl_report).pack(side=tk.LEFT, padx=12)
        if (self.f_dir / "fEngine.py").is_file():
            ttk.Button(btns, text="LLM loop (fEngine.py)", command=self._run_llm_loop).pack(side=tk.LEFT, padx=4)

        ctrl = ttk.Frame(self.tab_loop)
        ctrl.pack(fill=tk.X, pady=4)
        self.btn_loop_stop = ttk.Button(ctrl, text="Cancel run", command=self._cancel_loop, state=tk.DISABLED)
        self.btn_loop_stop.pack(side=tk.LEFT)
        ttk.Label(
            ctrl,
            text="Between loops: heal T1/T2/T3 in Heal tab, then Loop 2/3 auto-shrinks Run=Y to last failures.",
            wraplength=700,
        ).pack(side=tk.LEFT, padx=12)

        self.loop_log = scrolledtext.ScrolledText(self.tab_loop, height=14, wrap=tk.WORD, state=tk.DISABLED)
        self.loop_log.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

    def _build_help_tab(self) -> None:
        ttk.Label(self.tab_help, text="BRAHL.md — full context", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(
            self.tab_help,
            text="One-line: Build yPAD → Loop 1 (full) → Loop 2–3 (failures) → Verify (full) → Report in z/.",
        ).pack(anchor="w", pady=(0, 8))
        viewer = scrolledtext.ScrolledText(self.tab_help, wrap=tk.WORD, font=("Consolas", 10))
        viewer.pack(fill=tk.BOTH, expand=True)
        viewer.insert("1.0", self.brahl_text)
        viewer.config(state=tk.DISABLED)
        ttk.Button(self.tab_help, text="Open BRAHL.md in editor", command=lambda: self._open_file(self.brahl_md_path)).pack(anchor="w", pady=8)

    # --- logging ---
    def _log(self, line: str) -> None:
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, line + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _loop_log(self, line: str) -> None:
        self.loop_log.config(state=tk.NORMAL)
        self.loop_log.insert(tk.END, line + "\n")
        self.loop_log.see(tk.END)
        self.loop_log.config(state=tk.DISABLED)
        self._log(line)

    # --- filesystem helpers ---
    def _open_file(self, path: Path) -> None:
        if not path.is_file():
            messagebox.showwarning("Missing file", str(path))
            return
        os.startfile(str(path))  # type: ignore[attr-defined]

    def _open_folder(self, path: Path) -> None:
        if not path.is_dir():
            messagebox.showwarning("Missing folder", str(path))
            return
        os.startfile(str(path))  # type: ignore[attr-defined]

    def _pick_executable(self) -> None:
        picked = filedialog.askopenfilename(initialdir=str(self.f_dir), filetypes=[("Executable", "*.exe"), ("All", "*.*")])
        if picked:
            self.exe_var.set(picked)

    # --- engine helpers & suite discovery ---
    def _import_engine_helpers(self):
        if self._engine_helpers is not None:
            return self._engine_helpers
        f_path = str(self.f_dir)
        if f_path not in sys.path:
            sys.path.insert(0, f_path)
        import fEngine2  # noqa: WPS433

        self._engine_helpers = fEngine2
        return fEngine2

    def _discover_fstart_configs(self) -> list[str]:
        if not self.f_dir.is_dir():
            return ["f/fStart.json"]
        files = sorted(self.f_dir.glob("fStart*.json"))
        if not files:
            return ["f/fStart.json"]
        return [f"f/{p.name}" for p in files]

    def _refresh_fstart_combo(self) -> None:
        configs = self._discover_fstart_configs()
        self.fstart_combo["values"] = configs
        current = self.fstart_config_var.get()
        if current not in configs:
            self.fstart_config_var.set(configs[0])

    def _on_fstart_selected(self) -> None:
        rel = self.fstart_config_var.get().strip()
        self.fstart_path = self.project_root / rel.replace("/", os.sep)
        self._load_fstart()
        self._refresh_build_file_list()
        self._refresh_heal_file_list()

    def _get_primary_suite_config(self) -> Path | None:
        sel = self.config_listbox.curselection()
        if sel:
            return self.project_root / self.config_listbox.get(sel[0]).replace("/", os.sep)
        if not self.fstart_path.is_file():
            return None
        data = json.loads(self.fstart_path.read_text(encoding="utf-8"))
        configs = data.get("configs", [])
        if configs:
            return self.project_root / configs[0].replace("/", os.sep)
        return None

    def _suite_name_from_config(self, suite_path: Path | None = None) -> str:
        path = suite_path or self._get_primary_suite_config()
        if not path or not path.is_file():
            return "suite"
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("name") or path.stem

    def _suite_ypad_paths(self) -> list[tuple[str, Path]]:
        suite_path = self._get_primary_suite_config()
        if not suite_path or not suite_path.is_file():
            return []
        data = json.loads(suite_path.read_text(encoding="utf-8"))
        suite_dir = suite_path.parent
        out: list[tuple[str, Path]] = [(suite_path.name, suite_path)]
        for key in ("yPlans", "yActions", "yDesigns"):
            for rel in data.get("input_files", {}).get(key, []):
                p = self.project_root / rel.replace("\\", "/")
                out.append((Path(rel).name, p))
        common = suite_dir / "Common"
        if common.is_dir():
            for p in sorted(common.glob("yD_*.csv")):
                out.append((p.name, p))
        custom = self.project_root / "x" / "xCustom.py"
        if custom.is_file():
            out.append(("xCustom.py", custom))
        return out

    def _refresh_build_file_list(self) -> None:
        for w in self.build_file_list.winfo_children():
            w.destroy()
        for label, path in self._suite_ypad_paths():
            row = ttk.Frame(self.build_file_list)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
            ttk.Button(row, text="Open", command=lambda p=path: self._open_file(p)).pack(side=tk.RIGHT)
        self.active_suite_var.set(self._suite_name_from_config())

    def _refresh_heal_file_list(self) -> None:
        for w in self.heal_file_btns.winfo_children():
            w.destroy()
        suite_path = self._get_primary_suite_config()
        suite_dir = suite_path.parent if suite_path else self.y_dir
        heal_files = [
            ("1. Locators / URLs", suite_dir / "Common" / "yD_Common.csv"),
            ("2. Credentials", suite_dir / "Common" / "yD_Secure.csv"),
            ("3. Steps", suite_dir / "y2Actions.csv"),
            ("4. Plans / tags", suite_dir / "y1Plans.csv"),
            ("5. Run config", self.fstart_path),
            ("6. Engine source", self.f_dir / "fEngine2.py"),
        ]
        for label, path in heal_files:
            ttk.Button(self.heal_file_btns, text=label, command=lambda p=path: self._open_file(p)).pack(fill=tk.X, pady=3)

    def _y1_plans_paths(self) -> list[Path]:
        suite_path = self._get_primary_suite_config()
        if not suite_path or not suite_path.is_file():
            return []
        data = json.loads(suite_path.read_text(encoding="utf-8"))
        return [self.project_root / rel.replace("\\", "/") for rel in data.get("input_files", {}).get("yPlans", [])]

    def _find_results_csv(self, run_dir: Path) -> Path | None:
        matches = sorted(run_dir.glob("*_zResults.csv"))
        return matches[0] if matches else None

    def _find_dash_html(self, run_dir: Path) -> Path | None:
        matches = sorted(run_dir.glob("*_zDash.html"))
        return matches[0] if matches else None

    def _failed_plan_ids(self, run_dir: Path | None) -> set[str]:
        if not run_dir:
            return set()
        results = self._find_results_csv(run_dir)
        if not results or not results.is_file():
            return set()
        failed: set[str] = set()
        with results.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if (row.get("Result") or "").strip().lower() == "fail":
                    pid = (row.get("PlanId") or "").strip()
                    if pid:
                        failed.add(pid)
        return failed

    def _run_stats(self, run_dir: Path | None) -> tuple[int, int]:
        if not run_dir:
            return 0, 0
        results = self._find_results_csv(run_dir)
        if not results or not results.is_file():
            return 0, 0
        passes = fails = 0
        seen: set[tuple[str, str]] = set()
        with results.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                key = (row.get("PlanId", ""), row.get("StepId", ""))
                if key in seen:
                    continue
                seen.add(key)
                if (row.get("Result") or "").strip().lower() == "fail":
                    fails += 1
                else:
                    passes += 1
        return passes, fails

    def _edit_y1_plans_run_flags(self, run_y_ids: set[str] | None, run_n_ids: set[str] | None) -> int:
        changed = 0
        for plans_path in self._y1_plans_paths():
            if not plans_path.is_file():
                continue
            rows: list[dict[str, str]] = []
            with plans_path.open(encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                for row in reader:
                    pid = (row.get("PlanId") or "").strip()
                    if pid.startswith("PReuse_"):
                        if (row.get("Run") or "").upper() != "N":
                            row["Run"] = "N"
                            changed += 1
                    elif run_y_ids is not None and pid in run_y_ids and (row.get("Run") or "").upper() != "Y":
                        row["Run"] = "Y"
                        changed += 1
                    elif run_n_ids is not None and pid in run_n_ids and (row.get("Run") or "").upper() != "N":
                        row["Run"] = "N"
                        changed += 1
                    rows.append(row)
            with plans_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        return changed

    def _shrink_plans_to_failures(self) -> None:
        run = self._selected_run_dir()
        failed = self._failed_plan_ids(run)
        if not run:
            messagebox.showwarning("No run", "Select a z/ run with failures first.")
            return
        if not failed:
            messagebox.showinfo("No failures", "Last run had zero failures — Loop 2/3 not needed.")
            return
        all_ids: set[str] = set()
        for plans_path in self._y1_plans_paths():
            if not plans_path.is_file():
                continue
            with plans_path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    pid = (row.get("PlanId") or "").strip()
                    if pid and not pid.startswith("PReuse_"):
                        all_ids.add(pid)
        pass_ids = all_ids - failed
        n = self._edit_y1_plans_run_flags(run_y_ids=failed, run_n_ids=pass_ids)
        self._log(f"[Heal] Shrunk to {len(failed)} failure(s); Run=N on {len(pass_ids)} pass(es). {n} row(s) updated.")
        messagebox.showinfo("Shrink complete", f"Run=Y on {len(failed)} failed plan(s).\nRun=N on {len(pass_ids)} passed plan(s).")

    def _restore_plans_run_y(self) -> None:
        run_y: set[str] = set()
        for plans_path in self._y1_plans_paths():
            if not plans_path.is_file():
                continue
            with plans_path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    pid = (row.get("PlanId") or "").strip()
                    if pid and not pid.startswith("PReuse_"):
                        run_y.add(pid)
        n = self._edit_y1_plans_run_flags(run_y_ids=run_y, run_n_ids=None)
        self._log(f"[Heal] Restored Run=Y on {len(run_y)} plan(s). {n} row(s) updated.")
        messagebox.showinfo("Restore complete", f"Run=Y restored on {len(run_y)} in-scope plan(s) (reuse stays Run=N).")

    def _parse_context_documents(self) -> list[dict]:
        raw = self.cycle_docs_text.get("1.0", tk.END).strip()
        if not raw:
            return []
        docs: list[dict] = []
        for line in raw.splitlines():
            path = line.strip().strip('"')
            if not path:
                continue
            docs.append({"name": Path(path).name, "path": path.replace("\\", "/")})
        return docs

    def _capture_brahl_context(self) -> None:
        prompt = self.cycle_prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showwarning("Missing prompt", "Enter the user prompt that started this BRAHL cycle.")
            return
        if not self._save_fstart():
            return
        try:
            eng = self._import_engine_helpers()
            rel_config = self.fstart_path.relative_to(self.project_root).as_posix()
            docs = self._parse_context_documents()
            extra = {"documents": docs} if docs else None
            ctx_path, _baseline = eng.write_brahl_context(prompt, rel_config, extra=extra)
            self.brahl_context_path = Path(ctx_path)
            self.cycle_history.clear()
            self.cycle_step_var.set("Step 0 — context captured")
            self._loop_log(f"[Step 0] Context saved: {self.brahl_context_path.name}")
            messagebox.showinfo("Context captured", f"Saved:\n{self.brahl_context_path}")
        except Exception as exc:
            messagebox.showerror("Context failed", str(exc))

    def _open_brahl_report(self) -> None:
        run = self._selected_run_dir()
        if run:
            report = run / "brahl_report.md"
            if report.is_file():
                self._open_file(report)
                return
        flat = sorted(self.z_dir.glob("brahl_report_*.md"), key=lambda p: p.name, reverse=True) if self.z_dir.is_dir() else []
        if flat:
            self._open_file(flat[0])
        else:
            messagebox.showinfo("No report", "Run Verify and Generate report template, or open a Verify run folder.")

    def _open_brahl_context(self) -> None:
        if self.brahl_context_path and self.brahl_context_path.is_file():
            self._open_file(self.brahl_context_path)
            return
        contexts = sorted(self.z_dir.glob("brahl_context_*.json"), key=lambda p: p.name, reverse=True) if self.z_dir.is_dir() else []
        if contexts:
            self._open_file(contexts[0])
        else:
            messagebox.showinfo("No context", "Capture context (Step 0) before Loop 1.")

    def _generate_brahl_report(self) -> None:
        run = self._selected_run_dir()
        if not run:
            messagebox.showwarning("No run", "Select the Verify run folder in Analyze tab.")
            return
        suite = self._suite_name_from_config()
        suite_path = self._get_primary_suite_config()
        url = ""
        if suite_path and suite_path.is_file():
            url = json.loads(suite_path.read_text(encoding="utf-8")).get("url", "")
        rel_config = self.fstart_path.relative_to(self.project_root).as_posix() if self.fstart_path.is_file() else "f/fStart.json"
        prompt = self.cycle_prompt_text.get("1.0", tk.END).strip() or "(not captured — fill from context JSON)"
        ctx_name = self.brahl_context_path.name if self.brahl_context_path else "z/brahl_context_*.json"

        try:
            eng = self._import_engine_helpers()
            endline = eng.snapshot_ypad_plans(rel_config)
            endline_md = eng.format_ypad_snapshot_markdown(endline, title="yPAD after BRAHL (Verify state)")
        except Exception as exc:
            endline_md = f"*(Could not snapshot yPlans: {exc})*"
            endline = {}

        baseline_md = ""
        docs_md = ""
        if self.brahl_context_path and self.brahl_context_path.is_file():
            ctx = json.loads(self.brahl_context_path.read_text(encoding="utf-8"))
            prompt = ctx.get("initialPrompt", prompt)
            baseline = ctx.get("baseline", {})
            docs = ctx.get("documents") or []
            if docs:
                docs_md = "\n**Reference documents:**\n\n| Document | Path |\n|----------|------|\n"
                docs_md += "\n".join(f"| {d.get('name', '')} | `{d.get('path', '')}` |" for d in docs) + "\n"
            try:
                eng = self._import_engine_helpers()
                baseline_md = eng.format_ypad_snapshot_markdown(baseline, title="yPAD baseline (before Loop 1)")
            except Exception:
                baseline_md = f"- Run=Y before: {baseline.get('runY', '?')}"

        lines = [
            f"# BRAHL Report — {suite} — {datetime.now().strftime('%Y-%m-%d')}",
            "",
            f"**App:** {url or '(see suite JSON)'}",
            f"**Scope:** tags={self.tags_var.get() or '(all Run=Y)'} · **Config:** `{rel_config}`",
            f"**Engine:** fEngine2.py · timeout={self.timeout_var.get()} · headless={self.headless_var.get()}",
            f"**Context file:** `{ctx_name}`",
            "",
            "## Origin — user prompt",
            "",
            f"> {prompt}",
            "",
            "**Cycle intent:** _(one line)_",
            "",
            docs_md,
            "## yPAD baseline (before Loop 1)",
            "",
            baseline_md or "_(Capture Step 0 context before Loop 1)_",
            "",
            endline_md,
            "",
            "## Cycle summary",
            "",
            "| Step | Plans run | Pass | Fail | z/ folder |",
            "|------|-----------|------|------|-----------|",
        ]
        for entry in self.cycle_history:
            lines.append(
                f"| {entry.get('step', '')} | {entry.get('plans', '')} | {entry.get('pass', '')} | "
                f"{entry.get('fail', '')} | `{entry.get('folder', '')}` |"
            )
        if not self.cycle_history:
            lines.append("| Loop 1 | | | | |")
            lines.append("| Loop 2 | | | | |")
            lines.append("| Loop 3 | | | | |")
            lines.append("| Verify | | | | |")
        lines.extend([
            "",
            "## A1 defects (if any)",
            "",
            "| PlanId | Step | Evidence | Repro |",
            "|--------|------|----------|-------|",
            "",
            "## Verdict",
            "",
            "- [ ] Automation complete for in-scope set",
            "- [ ] Verify run green (or A1-only failures documented)",
            "- [ ] Full Run=Y restored for CI / user regression",
            "",
            f"**Dashboard:** `{run.name}/{self._find_dash_html(run).name if self._find_dash_html(run) else '<suite>_zDash.html'}`",
        ])
        content = "\n".join(lines)
        try:
            eng = self._import_engine_helpers()
            paths = eng.write_brahl_report(content, verify_output_dir=str(run))
            self._loop_log(f"[Report] Written: {paths['in_run']}")
            messagebox.showinfo("Report generated", f"Canonical:\n{paths['in_run']}\n\nFlat index:\n{paths['flat']}")
        except Exception as exc:
            messagebox.showerror("Report failed", str(exc))

    # --- fStart ---
    def _discover_configs(self) -> list[str]:
        if not self.y_dir.is_dir():
            return []
        out: list[str] = []
        for path in sorted(self.y_dir.glob("**/*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(data, dict) and "input_files" in data:
                out.append(path.relative_to(self.project_root).as_posix())
        return out

    def _load_fstart(self) -> None:
        self._refresh_fstart_combo()
        rel = self.fstart_config_var.get().strip()
        self.fstart_path = self.project_root / rel.replace("/", os.sep)
        if not self.fstart_path.is_file():
            return
        data = json.loads(self.fstart_path.read_text(encoding="utf-8"))
        self.thread_count_var.set(str(data.get("thread_count", 1)))
        self.timeout_var.set(str(data.get("timeout", 6)))
        self.headless_var.set(bool(data.get("headless", False)))
        self.tags_var.set(",".join(data.get("tags", [])))
        discovered = self._discover_configs()
        self.config_listbox.delete(0, tk.END)
        for cfg in discovered:
            self.config_listbox.insert(tk.END, cfg)
        selected = set(data.get("configs", []))
        for idx, cfg in enumerate(discovered):
            if cfg in selected:
                self.config_listbox.selection_set(idx)
        self.active_suite_var.set(self._suite_name_from_config())
        self._refresh_build_file_list()
        self._refresh_heal_file_list()

    def _save_fstart(self) -> bool:
        try:
            selected = [self.config_listbox.get(i) for i in self.config_listbox.curselection()]
            if not selected:
                messagebox.showwarning("No suite", "Select at least one yPAD config.")
                return False
            tags = [t.strip() for t in self.tags_var.get().split(",") if t.strip()]
            data = {
                "configs": selected,
                "thread_count": int(self.thread_count_var.get()),
                "timeout": int(self.timeout_var.get()),
                "headless": bool(self.headless_var.get()),
                "debug": False,
                "tags": tags,
            }
            self.fstart_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return True
        except ValueError:
            messagebox.showerror("Invalid input", "Thread count and timeout must be integers.")
            return False

    # --- Build actions ---
    def _validate_build(self) -> None:
        issues: list[str] = []
        suite_json = self._get_primary_suite_config()
        if suite_json and suite_json.is_file():
            data = json.loads(suite_json.read_text(encoding="utf-8"))
            for key in ("yPlans", "yActions", "yDesigns"):
                for rel in data.get("input_files", {}).get(key, []):
                    if not (self.project_root / rel.replace("\\", "/")).is_file():
                        issues.append(f"Missing {rel}")
        else:
            issues.append("No suite config selected in fStart")

        capa_path = self.project_root / "x" / "xCapa.csv"
        capa_names: set[str] = set()
        if capa_path.is_file():
            with capa_path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    capa_names.add((row.get("ActionName") or "").strip())

        actions_path = suite_json.parent / "y2Actions.csv" if suite_json else None
        if actions_path and actions_path.is_file() and capa_names:
            with actions_path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    name = (row.get("ActionName") or "").strip()
                    if name and name not in capa_names:
                        issues.append(f"Unknown action: {name}")

        for plans_path in self._y1_plans_paths():
            if not plans_path.is_file():
                continue
            with plans_path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    if (row.get("PlanId") or "").startswith("PReuse_") and (row.get("Run") or "").upper() == "Y":
                        issues.append(f"Reuse plan should be Run=N: {row.get('PlanId')}")
                    tags = (row.get("Tags") or "").lower()
                    if any(t in tags for t in ("issue", "link", "security", "element")):
                        pass  # A1 defect plans present — good

        ok_flags = [not issues, bool(suite_json and suite_json.is_file()), bool(capa_path.is_file()), True, True, True]
        for var, ok in zip(self.build_check_vars, ok_flags):
            var.set(ok)

        if issues:
            messagebox.showwarning("Build validation", "\n".join(issues[:12]))
            self._log(f"[Build] Validation found {len(issues)} issue(s).")
        else:
            messagebox.showinfo("Build validation", "Suite structure looks good.")
            self._log("[Build] Validation passed.")

    def _run_yvisualizer(self) -> None:
        script = self.y_dir / "yVisualizer.py"
        if not script.is_file():
            messagebox.showerror("Missing script", str(script))
            return
        self._run_script_async([sys.executable, str(script)], "yVisualizer")

    def _open_y_visualization(self) -> None:
        path = self.y_dir / "y_visualization.html"
        if path.is_file():
            webbrowser.open(path.resolve().as_uri())
        else:
            messagebox.showinfo("Not built yet", "Click 'Visualize yPAD' first.")

    # --- Run actions ---
    def _start_exe_run(self) -> None:
        if self.process is not None or self.loop_running:
            return
        if not self._save_fstart():
            return
        exe = Path(self.exe_var.get().strip().strip('"'))
        if not exe.is_file():
            messagebox.showerror("Executable not found", str(exe))
            return
        self._reset_run_ui()
        self.btn_run.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_var.set("Running tests…")
        self._start_safe_console_run(exe)

    def _start_python_run(self) -> None:
        if self.process is not None or self.loop_running:
            return
        if not self._save_fstart():
            return
        engine = Path(self.engine_py_var.get().strip())
        if not engine.is_file():
            messagebox.showerror("Engine not found", str(engine))
            return
        self._reset_run_ui()
        self.btn_run.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_var.set("Running tests (Python)…")

        def worker() -> None:
            try:
                self.process = subprocess.Popen(
                    [sys.executable, str(engine), "--config", str(self.fstart_path)],
                    cwd=str(self.project_root),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
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

        self.run_thread = threading.Thread(target=worker, daemon=True)
        self.run_thread.start()

    def _start_safe_console_run(self, exe: Path) -> None:
        self.safe_mode_running = True
        self.run_start_ts = time.time()
        before = self._snapshot_dashboards()

        def worker() -> None:
            try:
                flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
                proc = subprocess.Popen([str(exe), "--config", str(self.fstart_path.name)], cwd=str(exe.parent), creationflags=flags)
                rc = proc.wait()
                self.output_queue.put(f"[SAFE_PROCESS_EXIT] {rc}")
            except Exception as exc:
                self.output_queue.put(f"[ERROR] {exc}")
            finally:
                for p in self._snapshot_dashboards() - before:
                    self.output_queue.put(f"[DASHBOARD] {p}")

        threading.Thread(target=worker, daemon=True).start()

    def _snapshot_dashboards(self) -> set[str]:
        if not self.z_dir.is_dir():
            return set()
        return {str(p) for p in self.z_dir.glob("**/*zDash.html")}

    def _stop_run(self) -> None:
        if self.process is not None:
            try:
                self.process.terminate()
            except Exception:
                pass
        self.loop_cancel = True

    def _reset_run_ui(self) -> None:
        self.dashboard_paths.clear()
        self.dashboard_list.delete(0, tk.END)
        self.progress_var.set(0)
        self._log("\n=== Run started ===")

    def _open_selected_dashboard(self) -> None:
        sel = self.dashboard_list.curselection()
        if not sel:
            return
        path = Path(self.dashboard_list.get(sel[0]))
        if path.is_file():
            webbrowser.open(path.resolve().as_uri())

    # --- Analyze ---
    def _refresh_z_runs(self) -> None:
        self.z_run_paths = []
        self.runs_listbox.delete(0, tk.END)
        if not self.z_dir.is_dir():
            return
        runs = sorted(
            [p for p in self.z_dir.iterdir() if p.is_dir() and self._find_results_csv(p)],
            key=lambda p: p.name,
            reverse=True,
        )
        self.z_run_paths = runs
        for p in runs:
            self.runs_listbox.insert(tk.END, p.name)
        if runs:
            self.runs_listbox.selection_set(0)
            self.latest_run_var.set(runs[0].name)
            self._load_failures(runs[0])
        else:
            self.latest_run_var.set("(none)")

    def _selected_run_dir(self) -> Path | None:
        sel = self.runs_listbox.curselection()
        if not sel:
            return self.z_run_paths[0] if self.z_run_paths else None
        return self.z_run_paths[sel[0]]

    def _on_run_selected(self) -> None:
        run = self._selected_run_dir()
        if run:
            self.latest_run_var.set(run.name)
            self._load_failures(run)

    def _open_latest_run_folder(self) -> None:
        run = self._selected_run_dir()
        if run:
            self._open_folder(run)

    def _open_latest_dashboard(self) -> None:
        run = self._selected_run_dir()
        if not run:
            return
        dash = self._find_dash_html(run)
        if dash and dash.is_file():
            webbrowser.open(dash.resolve().as_uri())
        else:
            messagebox.showwarning("Missing", f"No *_zDash.html in {run}")

    def _run_zdefects(self) -> None:
        script = self.z_dir / "zDefects.py"
        if not script.is_file():
            messagebox.showerror("Missing", str(script))
            return
        self._run_script_async([sys.executable, str(script)], "zDefects", on_done=self._open_defects_dashboard)

    def _open_defects_dashboard(self) -> None:
        path = self.z_dir / "zDefectsDashboard.html"
        if path.is_file():
            webbrowser.open(path.resolve().as_uri())

    @staticmethod
    def _classify_rca(output: str, plan_id: str = "", tags: str = "") -> str:
        tag_lower = (tags or "").lower()
        if any(t in tag_lower for t in A1_DEFECT_TAGS):
            return "A1"
        if any(t in (plan_id or "").lower() for t in ("issue", "link", "sec", "elem")):
            return "A1"
        out = (output or "").lower()
        if "tag" in out and "plan" in out:
            return "T2"
        if "timer" in out or "cache" in out:
            return "T2"
        if "credential" in out or "auth" in out or "login" in out and "denied" in out:
            return "T3"
        if "404" in out or "page not found" in out:
            return "A1"
        if "element" in out or "locator" in out or "xclick" in out:
            return "T1"
        if "expected" in out:
            return "T1"
        return "T1?"

    def _plan_tags_map(self) -> dict[str, str]:
        tags_map: dict[str, str] = {}
        for plans_path in self._y1_plans_paths():
            if not plans_path.is_file():
                continue
            with plans_path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    pid = (row.get("PlanId") or "").strip()
                    if pid:
                        tags_map[pid] = (row.get("Tags") or "")
        return tags_map

    def _load_failures(self, run_dir: Path) -> None:
        for item in self.fail_tree.get_children():
            self.fail_tree.delete(item)
        results = self._find_results_csv(run_dir)
        if not results or not results.is_file():
            return
        tags_map = self._plan_tags_map()
        with results.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if (row.get("Result") or "").strip().lower() != "fail":
                    continue
                plan_id = row.get("PlanId", "")
                output = (row.get("Output") or "")[:200]
                rca = self._classify_rca(row.get("Output") or "", plan_id, tags_map.get(plan_id, ""))
                self.fail_tree.insert(
                    "",
                    tk.END,
                    values=(plan_id, row.get("StepId", ""), rca, output),
                )

    # --- Heal / LLM optional ---
    def _run_llm_heal(self) -> None:
        suite_path = self._get_primary_suite_config()
        suite_dir = suite_path.parent if suite_path else self.y_dir / "qoa2"
        engine = self.f_dir / "fEngine.py"
        self._run_script_async([sys.executable, str(engine), "--heal", str(suite_dir.relative_to(self.project_root)).replace("\\", "/") + "/"], "LLM heal")

    def _run_llm_loop(self) -> None:
        suite_path = self._get_primary_suite_config()
        suite_dir = suite_path.parent if suite_path else self.y_dir / "qoa2"
        engine = self.f_dir / "fEngine.py"
        self._run_script_async([sys.executable, str(engine), "--loop", str(suite_dir.relative_to(self.project_root)).replace("\\", "/") + "/"], "LLM loop")

    # --- Loop (BRAHL.md cycle) ---
    def _start_cycle_step(self, step: str) -> None:
        if self.loop_running or self.process is not None:
            messagebox.showwarning("Busy", "A run is already in progress.")
            return
        if step == "Loop 1" and not self.brahl_context_path:
            if not messagebox.askyesno("Step 0 skipped", "Capture context (Step 0) before Loop 1?\n\nChoose No to run Loop 1 anyway."):
                return
        if not self._save_fstart():
            return

        self.loop_running = True
        self.loop_cancel = False
        self.btn_loop_stop.config(state=tk.NORMAL)
        self.cycle_step_var.set(f"Running {step}…")

        def worker() -> None:
            try:
                if step == "Loop 1":
                    self._restore_plans_run_y_silent()
                elif step in ("Loop 2", "Loop 3"):
                    self._shrink_plans_to_failures_silent()
                elif step == "Verify":
                    self._restore_plans_run_y_silent()

                self.output_queue.put(f"[LOOP] {step} — starting engine run")
                rc = self._run_blocking()
                self.output_queue.put(f"[LOOP] {step} finished (code {rc})")
                self.root.after(0, self._refresh_z_runs)
                run = self._selected_run_dir()
                passes, fails = self._run_stats(run)
                failed_ids = self._failed_plan_ids(run)
                entry = {
                    "step": step,
                    "plans": len(failed_ids) if step in ("Loop 2", "Loop 3") and failed_ids else passes + fails,
                    "pass": passes,
                    "fail": fails,
                    "folder": run.name if run else "",
                    "failed_plan_ids": sorted(failed_ids),
                }
                self.cycle_history.append(entry)
                self.output_queue.put(f"[LOOP] {step}: {passes} pass, {fails} fail")
                if step == "Verify" and fails == 0:
                    self.output_queue.put("[LOOP] Verify green — click Generate report template")
                elif fails:
                    self.output_queue.put(f"[LOOP] Heal T1/T2/T3, then run next loop step. Failures: {', '.join(sorted(failed_ids)[:8])}")
            finally:
                self.loop_running = False
                self.root.after(0, lambda: (
                    self.btn_loop_stop.config(state=tk.DISABLED),
                    self.cycle_step_var.set(step),
                ))

        threading.Thread(target=worker, daemon=True).start()

    def _restore_plans_run_y_silent(self) -> None:
        run_y: set[str] = set()
        for plans_path in self._y1_plans_paths():
            if not plans_path.is_file():
                continue
            with plans_path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    pid = (row.get("PlanId") or "").strip()
                    if pid and not pid.startswith("PReuse_"):
                        run_y.add(pid)
        self._edit_y1_plans_run_flags(run_y_ids=run_y, run_n_ids=None)
        self.output_queue.put(f"[LOOP] Restored Run=Y on {len(run_y)} plan(s)")

    def _shrink_plans_to_failures_silent(self) -> None:
        run = self._selected_run_dir()
        failed = self._failed_plan_ids(run)
        if not failed:
            self.output_queue.put("[LOOP] No failures to shrink — running current Run=Y set")
            return
        all_ids: set[str] = set()
        for plans_path in self._y1_plans_paths():
            if not plans_path.is_file():
                continue
            with plans_path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    pid = (row.get("PlanId") or "").strip()
                    if pid and not pid.startswith("PReuse_"):
                        all_ids.add(pid)
        pass_ids = all_ids - failed
        self._edit_y1_plans_run_flags(run_y_ids=failed, run_n_ids=pass_ids)
        self.output_queue.put(f"[LOOP] Shrunk: Run=Y on {len(failed)} failure(s), Run=N on {len(pass_ids)} pass(es)")

    def _save_fstart_sync(self) -> bool:
        try:
            selected = [self.config_listbox.get(i) for i in self.config_listbox.curselection()]
            if not selected:
                suite = self._get_primary_suite_config()
                if suite:
                    selected = [suite.relative_to(self.project_root).as_posix()]
                else:
                    selected = ["y/qoa2/qoa2.json"]
            tags = [t.strip() for t in self.tags_var.get().split(",") if t.strip()]
            data = {
                "configs": selected,
                "thread_count": int(self.thread_count_var.get()),
                "timeout": int(self.timeout_var.get()),
                "headless": bool(self.headless_var.get()),
                "debug": False,
                "tags": tags,
            }
            self.fstart_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    def _run_blocking(self) -> int:
        engine = Path(self.engine_py_var.get())
        if engine.is_file():
            proc = subprocess.run(
                [sys.executable, str(engine), "--config", str(self.fstart_path)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for line in (proc.stdout or "").splitlines():
                self.output_queue.put(line)
            return proc.returncode
        exe = Path(self.exe_var.get())
        if exe.is_file():
            proc = subprocess.run([str(exe), "--config", str(self.fstart_path.name)], cwd=str(exe.parent))
            return proc.returncode
        return 1

    def _cancel_loop(self) -> None:
        self.loop_cancel = True
        self._stop_run()

    # --- subprocess utility ---
    def _run_script_async(self, cmd: list[str], label: str, on_done=None) -> None:
        def worker() -> None:
            try:
                self._log(f"[{label}] Starting…")
                proc = subprocess.run(cmd, cwd=str(self.project_root), capture_output=True, text=True, encoding="utf-8", errors="replace")
                if proc.stdout:
                    for line in proc.stdout.splitlines():
                        self._log(line)
                if proc.stderr:
                    for line in proc.stderr.splitlines():
                        self._log(line)
                self._log(f"[{label}] Exit {proc.returncode}")
                if on_done and proc.returncode == 0:
                    self.root.after(0, on_done)
            except Exception as exc:
                self._log(f"[{label}] Error: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    # --- output polling ---
    def _poll_output(self) -> None:
        while not self.output_queue.empty():
            line = self.output_queue.get_nowait()
            if line.startswith("[LOOP]"):
                self._loop_log(line)
            else:
                self._log(line)
            self._handle_output_line(line)
        self.root.after(120, self._poll_output)

    def _handle_output_line(self, line: str) -> None:
        m = self.PROGRESS_RE.search(line)
        if m:
            self.progress_var.set(float(m.group(1)))
            self.status_var.set(f"Running… {m.group(1)}% ({m.group(2)}/{m.group(3)} plans)")

        m_dash = self.DASHBOARD_RE.search(line)
        if m_dash:
            path = Path(m_dash.group(1).strip())
            if path not in self.dashboard_paths:
                self.dashboard_paths.append(path)
                self.dashboard_list.insert(tk.END, str(path))

        if line.startswith("[DASHBOARD]"):
            path = Path(line.replace("[DASHBOARD]", "", 1).strip())
            if path not in self.dashboard_paths:
                self.dashboard_paths.append(path)
                self.dashboard_list.insert(tk.END, str(path))

        if line.startswith("[SAFE_PROCESS_EXIT]") or line.startswith("[PROCESS_EXIT]"):
            rc = int(line.split()[-1])
            self.safe_mode_running = False
            self.btn_run.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            self.status_var.set("Run complete." if rc == 0 else f"Run finished (code {rc}).")
            self.progress_var.set(100 if rc == 0 else self.progress_var.get())
            self.root.after(500, self._refresh_z_runs)


def main() -> None:
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass
    BrahLApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
