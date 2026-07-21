import os
import shutil
import json
import time
import re
import pandas as pd
import argparse
import logging
import sys
import subprocess
import platform
from datetime import datetime
import multiprocessing
import io
from concurrent.futures import ProcessPoolExecutor

# Root directory for development mode when engine lives under f/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
try:
    from dotenv import load_dotenv, dotenv_values
except ImportError:
    load_dotenv = None
    dotenv_values = None
try:
    import x.xActions as xActions
except ImportError:
    # Fallback for bundled execution: add data folder 'x' to sys.path and import module
    x_dir = None
    try:
        x_dir = os.path.abspath(os.path.join(sys._MEIPASS, 'x'))  # type: ignore[attr-defined]
    except Exception:
        pass
    if not x_dir or not os.path.isdir(x_dir):
        x_dir = os.path.abspath(os.path.join(PROJECT_ROOT, 'x'))
    if x_dir not in sys.path:
        sys.path.insert(0, x_dir)
    import xActions as xActions  # type: ignore[import-not-found]

# Configure logging to suppress technical details
logging.basicConfig(level=logging.ERROR, format='%(message)s')
logger = logging.getLogger(__name__)

# Suppress third-party library logs
logging.getLogger('selenium').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)

# User-friendly output functions
def print_header(title):
    """Print a formatted header for sections."""
    print(f"\n{'='*60}", flush=True)
    print(f"  {title}", flush=True)
    print(f"{'='*60}", flush=True)

def print_progress(current, total, item_name="items"):
    """Print progress information."""
    percentage = (current / total) * 100 if total > 0 else 0
    bar_length = 30
    filled_length = int(bar_length * current // total) if total > 0 else 0
    bar = '#' * filled_length + '-' * (bar_length - filled_length)
    progress_text = f"Progress: |{bar}| {percentage:.1f}% ({current}/{total} {item_name})"
    try:
        if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            print(f"\r{progress_text}", end='', flush=True)
        else:
            print(progress_text, flush=True)
    except UnicodeEncodeError:
        _safe_console_print(progress_text)

def _safe_console_print(text):
    """Print to console; fall back to ASCII-safe text on Windows cp1252."""
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        safe = text
        for src, dst in (('\u2713', '[OK]'), ('\u2717', '[X]'), ('\u2192', '->')):
            safe = safe.replace(src, dst)
        print(safe.encode('ascii', errors='replace').decode('ascii'), flush=True)

def print_status(message, status="INFO"):
    """Print status messages with formatting (always flush for Arena live console)."""
    status_symbols = {
        "INFO": "ℹ️",
        "SUCCESS": "✅", 
        "WARNING": "⚠️",
        "ERROR": "❌",
        "RUNNING": "🔄"
    }
    ascii_symbols = {
        "INFO": "[i]",
        "SUCCESS": "[OK]",
        "WARNING": "[!]",
        "ERROR": "[X]",
        "RUNNING": "[~]",
    }
    symbol = status_symbols.get(status, "•")
    line = f"{symbol} {message}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        _safe_console_print(f"{ascii_symbols.get(status, '*')} {message}")

def print_summary(stats):
    """Print execution summary."""
    print_header("EXECUTION SUMMARY")
    _safe_console_print(f"📊 Total Plans: {stats['total_plans']}")
    _safe_console_print(f"✅ Passed: {stats['passed']}")
    _safe_console_print(f"❌ Failed: {stats['failed']}")
    _safe_console_print(f"⏱️  Total Time: {stats['total_time']:.2f} seconds")
    _safe_console_print(f"📁 Results saved to: {stats['output_dir']}")
    _safe_console_print(f"🌐 Dashboard: {stats['dashboard_path']}")
    print(f"{'='*60}\n", flush=True)

def cleanup_empty_directories(directory):
    """Remove empty directories recursively, but keep the root directory."""
    if not os.path.exists(directory):
        return 0
    
    removed_count = 0
    # Walk through all subdirectories, starting from the deepest ones
    for root, dirs, files in os.walk(directory, topdown=False):
        # Skip the root directory itself
        if root == directory:
            continue
        
        # Check if directory is empty (no files and no subdirectories)
        try:
            if not os.listdir(root):
                os.rmdir(root)
                removed_count += 1
        except OSError:
            # Directory might have been removed already or permission issue
            pass
    
    return removed_count

def kill_chromedriver_processes():
    """Kill any running chromedriver processes to prevent conflicts."""
    try:
        system = platform.system()
        
        if system == 'Windows':
            # Windows: use taskkill to kill chromedriver.exe processes
            try:
                # Kill chromedriver.exe processes
                subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL,
                            timeout=5)
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                pass  # Process might not exist, or taskkill not available
        elif system == 'Linux':
            # Linux: use pkill to kill chromedriver processes
            try:
                subprocess.run(['pkill', '-f', 'chromedriver'], 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL,
                            timeout=5)
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                pass
        elif system == 'Darwin':  # macOS
            # macOS: use pkill to kill chromedriver processes
            try:
                subprocess.run(['pkill', '-f', 'chromedriver'], 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL,
                            timeout=5)
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                pass
    except Exception:
        pass  # Don't fail if process killing fails

# Global cache for action results
action_cache = {}

# Environment variables from .env (sensitive placeholders for y3Designs)
_env_dict = {}

def _env_path():
    """Return path to .env file: next to script/exe, then cwd."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = PROJECT_ROOT
    for d in (base, os.getcwd()):
        p = os.path.join(d, '.env')
        if os.path.isfile(p):
            return p
    return None

def load_env():
    """Load .env into os.environ and return dict of key=value for design placeholder substitution."""
    global _env_dict
    path = _env_path()
    if not path:
        _env_dict = {}
        return _env_dict
    if load_dotenv and dotenv_values:
        load_dotenv(path)
        raw = dotenv_values(path)
        _env_dict = {k: (v if v is not None else '') for k, v in (raw or {}).items()}
        _env_dict = _normalize_env_dict_keys(_env_dict)
        return _env_dict
    # Fallback: parse .env manually (KEY=VALUE, strip quotes, skip comments)
    _env_dict = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, _, v = line.partition('=')
                    key = k.strip()
                    val = v.strip()
                    if len(val) >= 2 and (val.startswith('"') and val.endswith('"') or val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    os.environ[key] = val
                    _env_dict[key] = val
        _env_dict = _normalize_env_dict_keys(_env_dict)
    except Exception:
        pass
    return _env_dict

def _normalize_env_dict_keys(env_dict):
    """Add key aliases so y3Designs placeholders match .env despite stray quotes (e.g. KEY\"=)."""
    if not env_dict:
        return env_dict
    extra = {}
    for k, v in env_dict.items():
        k2 = k.strip().strip('"').strip("'")
        if k2 and k2 != k and k2 not in env_dict:
            extra[k2] = v
    if extra:
        out = dict(env_dict)
        out.update(extra)
        return out
    return env_dict

def _substitute_env_in_value(data_value):
    """Replace any .env placeholder keys in data_value with their values."""
    if not data_value or not _env_dict:
        return data_value
    s = str(data_value)
    # Replace longest keys first to avoid partial replacements (e.g. KEY vs KEY2)
    for key in sorted(_env_dict.keys(), key=len, reverse=True):
        val = _env_dict.get(key)
        if val is None:
            val = ''
        s = s.replace(str(key), str(val))
    return s

def _default_main_config_path():
    """Default path to the main JSON config.

    Development: repo layout has ``f/fStart/default.json`` relative to project root.

    Frozen (PyInstaller onedir user package): exe lives under ``f/`` with
    ``f/fStart/default.json`` beside it. Also accept legacy layouts where the
    exe sat at package root with top-level ``fStart/`` or ``f/fStart/``.
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.abspath(os.path.dirname(sys.executable))
        parent = os.path.dirname(exe_dir)
        candidates = [
            (os.path.join(exe_dir, 'fStart', 'default.json'), os.path.join('fStart', 'default.json')),
            (os.path.join(exe_dir, 'f', 'fStart', 'default.json'), 'f/fStart/default.json'),
            (os.path.join(parent, 'f', 'fStart', 'default.json'), 'f/fStart/default.json'),
            (os.path.join(exe_dir, 'fStart.json'), 'fStart.json'),
        ]
        for abs_path, rel_path in candidates:
            if os.path.isfile(abs_path):
                return rel_path
        return os.path.join('fStart', 'default.json')
    return 'f/fStart/default.json'


def _frozen_data_search_bases():
    """Directories to search for user data (y/, z/ beside exe, etc.) when running frozen.

    If the exe lives in ``f/Foxyiz.exe``, repo data usually sits one level up (``../y/``),
    not under ``f/y/``. Try exe directory first, then its parent.
    """
    exe_dir = os.path.abspath(os.path.dirname(sys.executable))
    bases = [exe_dir]
    parent = os.path.dirname(exe_dir)
    if parent and parent != exe_dir:
        bases.append(parent)
    return bases


def _results_z_root():
    """Absolute path to the ``z`` folder where run outputs are written.

    Development: ``<project root>/z`` so results do not depend on current working directory.

    Frozen: if ``y/`` sits next to the exe, use ``<exe_dir>/z``; if ``y/`` is only under the
    parent (exe inside ``f/``), use ``<parent>/z`` so results align with the same layout as
    ``python f/fEngine.py`` from the repo.
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.abspath(os.path.dirname(sys.executable))
        parent = os.path.dirname(exe_dir)
        if os.path.isdir(os.path.join(exe_dir, 'y')):
            return os.path.join(exe_dir, 'z')
        if parent and os.path.isdir(os.path.join(parent, 'y')):
            return os.path.join(parent, 'z')
        return os.path.join(exe_dir, 'z')
    return os.path.join(PROJECT_ROOT, 'z')


_RUN_OUTPUT_DIR_RE = re.compile(r'^(\d{8}_\d{6})_(.+)$')


def parse_run_output_dir(output_dir):
    """Parse ``z/<YYYYMMDD_HHMMSS>_<suite>/`` into (timestamp, suite_name)."""
    base = os.path.basename(os.path.normpath(output_dir))
    match = _RUN_OUTPUT_DIR_RE.match(base)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def brahl_report_filename(suite_name, timestamp=None):
    """Flat index filename: ``brahl_report_<YYYYMMDD_HHMMSS>_<suite>.md``."""
    ts = timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_suite = re.sub(r'[^\w.-]', '_', str(suite_name or 'suite'))
    return f"brahl_report_{ts}_{safe_suite}.md"


def brahl_report_paths(suite_name=None, verify_output_dir=None, timestamp=None):
    """Return BRAHL report paths for a completed cycle (Verify run).

    - ``in_run``: ``z/<ts>_<suite>/brahl_report.md`` — alongside zDash / zResults
    - ``flat``: ``z/brahl_report_<ts>_<suite>.md`` — grep-friendly index at z root

    Pass ``verify_output_dir`` from the Verify engine run to derive timestamp and suite.
    """
    z_root = _results_z_root()
    ts = timestamp
    suite = suite_name
    if verify_output_dir:
        parsed_ts, parsed_suite = parse_run_output_dir(verify_output_dir)
        ts = ts or parsed_ts
        suite = suite or parsed_suite
    ts = ts or datetime.now().strftime('%Y%m%d_%H%M%S')
    suite = suite or 'suite'
    in_run_dir = verify_output_dir
    if not in_run_dir:
        in_run_dir = os.path.join(z_root, f"{ts}_{suite}")
    return {
        'in_run': os.path.join(in_run_dir, 'brahl_report.md'),
        'flat': os.path.join(z_root, brahl_report_filename(suite, ts)),
        'timestamp': ts,
        'suite': suite,
    }


def write_brahl_report(content, suite_name=None, verify_output_dir=None, timestamp=None):
    """Write cycle report to in-run and flat z paths; return path dict."""
    paths = brahl_report_paths(suite_name, verify_output_dir, timestamp)
    os.makedirs(os.path.dirname(paths['in_run']), exist_ok=True)
    with open(paths['in_run'], 'w', encoding='utf-8') as f:
        f.write(content)
    with open(paths['flat'], 'w', encoding='utf-8') as f:
        f.write(content)
    return paths


def _find_plans_column(df, name):
    for col in df.columns:
        if col.strip().strip('"').strip("'").lower() == name.lower():
            return col
    return None


def resolve_suite_config(config_path):
    """Resolve fStart JSON to the underlying suite yPAD config path."""
    cfg = load_config(config_path)
    if isinstance(cfg, dict) and cfg.get('configs'):
        suite_path = cfg['configs'][0]
        return load_config(suite_path), suite_path.replace('\\', '/')
    return cfg, config_path.replace('\\', '/')


def snapshot_ypad_plans(config_path):
    """Snapshot y1Plans for BRAHL baseline (before Loop 1) or endline (after Verify)."""
    ypad_config, suite_config_path = resolve_suite_config(config_path)
    y1_plans_list = []
    plan_paths = []
    for plan_file in ypad_config['input_files']['yPlans']:
        plan_paths.append(plan_file.replace('\\', '/'))
        y1_plans_list.append(load_csv(plan_file))
    if not y1_plans_list:
        raise ValueError('No yPlans files found in suite config')
    y1_plans = pd.concat(y1_plans_list, ignore_index=True)
    run_col = _find_plans_column(y1_plans, 'run')
    tags_col = _find_plans_column(y1_plans, 'tags')
    plan_id_col = _find_plans_column(y1_plans, 'planid')
    plan_name_col = _find_plans_column(y1_plans, 'planname')
    if not plan_id_col:
        raise ValueError('PlanId column not found in y1Plans')

    plans = []
    for _, row in y1_plans.iterrows():
        plans.append({
            'planId': str(row[plan_id_col]).strip(),
            'planName': str(row[plan_name_col]).strip() if plan_name_col else '',
            'run': str(row[run_col]).strip().upper() if run_col else '',
            'tags': str(row[tags_col]).strip() if tags_col and pd.notna(row.get(tags_col)) else '',
        })

    run_y = [p for p in plans if p['run'] == 'Y']
    run_n = [p for p in plans if p['run'] != 'Y']
    reuse = [p for p in plans if p['planId'].startswith('PReuse_') or 'reuse' in p['tags'].lower()]

    return {
        'capturedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'suiteConfig': suite_config_path,
        'yPlansPaths': plan_paths,
        'totalRows': len(plans),
        'runY': len(run_y),
        'runN': len(run_n),
        'reuseCount': len(reuse),
        'runnablePlanIds': [p['planId'] for p in run_y],
        'disabledPlanIds': [p['planId'] for p in run_n],
        'plans': plans,
    }


def brahl_context_filename(suite_name, timestamp=None):
    ts = timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_suite = re.sub(r'[^\w.-]', '_', str(suite_name or 'suite'))
    return f"brahl_context_{ts}_{safe_suite}.json"


def write_brahl_context(initial_prompt, config_path, suite_name=None, timestamp=None, extra=None):
    """Save cycle-start context (user prompt + yPlans baseline) under z/ before Loop 1."""
    snapshot = snapshot_ypad_plans(config_path)
    _, suite_config_path = resolve_suite_config(config_path)
    suite = suite_name or os.path.splitext(os.path.basename(suite_config_path))[0]
    ts = timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')
    context_path = os.path.join(_results_z_root(), brahl_context_filename(suite, ts))
    payload = {
        'initialPrompt': initial_prompt,
        'baseline': snapshot,
        'fStartConfig': config_path.replace('\\', '/'),
        'cycleStartedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    if extra:
        payload.update(extra)
    with open(context_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    return context_path, snapshot


def format_ypad_snapshot_markdown(snapshot, title='yPAD snapshot'):
    """Render a yPlans snapshot dict as markdown for BRAHL reports."""
    paths = ', '.join(f'`{p}`' for p in snapshot.get('yPlansPaths', []))
    lines = [
        f'### {title}',
        '',
        f'- **yPlans files:** {paths}',
        f'- **Total rows:** {snapshot.get("totalRows", 0)} · **Run=Y:** {snapshot.get("runY", 0)} · **Run=N:** {snapshot.get("runN", 0)} · **Reuse blocks:** {snapshot.get("reuseCount", 0)}',
        '',
    ]
    runnable = snapshot.get('runnablePlanIds') or []
    disabled = snapshot.get('disabledPlanIds') or []
    if runnable:
        lines.append('**Run=Y plans:**')
        lines.append('')
        for pid in runnable:
            lines.append(f'- `{pid}`')
        lines.append('')
    if disabled:
        lines.append('**Run=N plans:**')
        lines.append('')
        for pid in disabled:
            lines.append(f'- `{pid}`')
        lines.append('')
    return '\n'.join(lines)


def _resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    # If running as PyInstaller executable
    if getattr(sys, 'frozen', False):
        # First try the bundled resources in _MEIPASS
        try:
            bundled_path = os.path.abspath(os.path.join(sys._MEIPASS, relative_path))  # type: ignore[attr-defined]
            if os.path.exists(bundled_path):
                return bundled_path
        except Exception:
            pass
        # Non-bundled files (y/, optional z/): exe dir, then parent (exe inside f/)
        for base in _frozen_data_search_bases():
            candidate = os.path.abspath(os.path.join(base, relative_path))
            if os.path.exists(candidate):
                return candidate
        return os.path.abspath(os.path.join(_frozen_data_search_bases()[0], relative_path))
    else:
        # Development mode: use script directory
        base_path = PROJECT_ROOT
        return os.path.abspath(os.path.join(base_path, relative_path))

def load_config(config_path):
    """Load configuration from a JSON file."""
    resolved = config_path
    if not os.path.isabs(config_path):
        # Frozen: search exe dir then parent (exe in f/, package root has y/)
        if getattr(sys, 'frozen', False):
            found = None
            for base in _frozen_data_search_bases():
                candidate = os.path.join(base, config_path)
                if os.path.exists(candidate):
                    found = candidate
                    break
            resolved = found if found else _resource_path(config_path)
        else:
            resolved = _resource_path(config_path)
    with open(resolved, 'r') as f:
        return json.load(f)

def load_csv(file_path):
    """
    Load data file (CSV, Excel, TXT, or JSON) into a DataFrame.
    Supports multiple file formats while maintaining the same template structure.
    """
    resolved = file_path
    if not os.path.isabs(file_path):
        resolved = _resource_path(file_path)
    
    # Get file extension to determine file type
    file_ext = os.path.splitext(resolved)[1].lower()
    
    last_error = None
    df = None
    
    # Read file based on extension
    if file_ext in ['.csv', '.txt']:
        # CSV and TXT files - treat both as CSV (TXT can be tab or comma delimited)
        # Try comma first, then tab delimiter for TXT files
        try:
            df = pd.read_csv(resolved, encoding='utf-8-sig', quotechar='"', doublequote=True)  # utf-8-sig handles BOM
        except Exception as e:
            last_error = e
            # For TXT files, try tab delimiter
            if file_ext == '.txt':
                try:
                    df = pd.read_csv(resolved, encoding='utf-8-sig', sep='\t', quotechar='"', doublequote=True)
                except Exception as e2:
                    last_error = e2
                    # Try comma delimiter
                    try:
                        df = pd.read_csv(resolved, encoding='utf-8-sig', sep=',', quotechar='"', doublequote=True)
                    except Exception as e3:
                        last_error = e3
                        # Fallback: try without quotechar specification
                        try:
                            df = pd.read_csv(resolved, encoding='utf-8-sig', doublequote=True)
                        except Exception as e4:
                            last_error = e4
                            # Last resort: try default encoding
                            try:
                                df = pd.read_csv(resolved, doublequote=True)
                            except Exception as e5:
                                last_error = e5
                                # Final fallback: basic read
                                try:
                                    df = pd.read_csv(resolved)
                                except Exception as e6:
                                    raise Exception(f"Failed to read TXT/CSV file '{resolved}'. Last error: {str(e6)}. "
                                                  f"Previous errors: {str(e)}, {str(e2)}, {str(e3)}, {str(e4)}, {str(e5)}")
            else:
                # For CSV files, try fallback options
                try:
                    df = pd.read_csv(resolved, encoding='utf-8-sig', doublequote=True)
                except Exception as e2:
                    last_error = e2
                    # Last resort: try default encoding
                    try:
                        df = pd.read_csv(resolved, doublequote=True)
                    except Exception as e3:
                        last_error = e3
                        # Final fallback: basic read
                        try:
                            df = pd.read_csv(resolved)
                        except Exception as e4:
                            # If all attempts fail, raise with helpful message
                            raise Exception(f"Failed to read CSV file '{resolved}'. Last error: {str(e4)}. "
                                          f"Previous errors: {str(e)}, {str(e2)}, {str(e3)}")
    
    elif file_ext in ['.xlsx', '.xls']:
        # Excel files
        try:
            df = pd.read_excel(resolved, engine='openpyxl')
        except ImportError:
            raise Exception(f"Excel file support requires 'openpyxl' package. Please install it: pip install openpyxl")
        except Exception as e:
            last_error = e
            # Try with xlrd engine for older .xls files
            if file_ext == '.xls':
                try:
                    df = pd.read_excel(resolved, engine='xlrd')
                except ImportError:
                    raise Exception(f"Excel .xls file support requires 'xlrd' package. Please install it: pip install xlrd")
                except Exception as e2:
                    raise Exception(f"Failed to read Excel file '{resolved}'. Last error: {str(e2)}. "
                                  f"Previous error: {str(e)}")
            else:
                raise Exception(f"Failed to read Excel file '{resolved}'. Error: {str(e)}")
    
    elif file_ext == '.json':
        # JSON files
        try:
            df = pd.read_json(resolved, orient='records')
        except Exception as e:
            last_error = e
            # Try reading as JSON lines (JSONL) format
            try:
                df = pd.read_json(resolved, lines=True)
            except Exception as e2:
                last_error = e2
                # Try reading JSON and converting to DataFrame
                try:
                    with open(resolved, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        df = pd.DataFrame(data)
                    elif isinstance(data, dict):
                        # If it's a dict, try to find a list or convert values
                        if 'data' in data and isinstance(data['data'], list):
                            df = pd.DataFrame(data['data'])
                        else:
                            df = pd.DataFrame([data])
                    else:
                        raise Exception(f"Unsupported JSON structure in '{resolved}'")
                except Exception as e3:
                    raise Exception(f"Failed to read JSON file '{resolved}'. Last error: {str(e3)}. "
                                  f"Previous errors: {str(e)}, {str(e2)}")
    
    else:
        raise Exception(f"Unsupported file format '{file_ext}' for file '{resolved}'. "
                       f"Supported formats: .csv, .txt, .xlsx, .xls, .json")
    
    if df is None or df.empty:
        raise Exception(f"File '{resolved}' is empty or could not be read properly")
    
    # Clean column names: strip whitespace and remove quotes (same template as CSV)
    df.columns = df.columns.str.strip().str.strip('"').str.strip("'")
    
    # Fix PlanId column to be string if it exists (same template as CSV)
    if 'PlanId' in df.columns:
        # Only add 'P' prefix if it's not already there
        df['PlanId'] = df['PlanId'].astype(str)
        df['PlanId'] = df['PlanId'].apply(lambda x: x if x.startswith('P') else 'P' + x)
    
    return df

def _clean_dashboard_value(value):
    """Normalize CSV cell values for dashboard JSON."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() in ('nan', 'none', 'nat'):
        return None
    return text

def _find_artifact_path(output_dir, plan_id, filename):
    """Locate artifact file under run output directory."""
    if not filename:
        return None
    filename = os.path.basename(filename.strip())
    direct = os.path.join(output_dir, filename)
    if os.path.exists(direct):
        return filename.replace('\\', '/')
    plan_hint = str(plan_id or '')
    for root, _, files in os.walk(output_dir):
        if filename in files:
            rel = os.path.relpath(os.path.join(root, filename), output_dir).replace('\\', '/')
            if plan_hint and plan_hint in rel:
                return rel
    for root, _, files in os.walk(output_dir):
        if filename in files:
            return os.path.relpath(os.path.join(root, filename), output_dir).replace('\\', '/')
    return None

def _parse_artifact_links(output_text, output_dir, plan_id):
    """Extract artifact filenames from FoXYiZ output strings."""
    links = []
    if not output_text:
        return links
    text = str(output_text)
    for match in re.finditer(r'\[Link to ([^\]]+)\]', text, re.IGNORECASE):
        name = match.group(1).strip()
        path = _find_artifact_path(output_dir, plan_id, name)
        if path:
            links.append({'label': name, 'path': path, 'kind': 'output'})
    artifacts_match = re.search(r'\[Artifacts => ([^\]]+)\]', text, re.IGNORECASE)
    if artifacts_match:
        for part in artifacts_match.group(1).split('|'):
            part = part.strip()
            if ':' in part:
                _, name = part.split(':', 1)
            else:
                name = part
            name = name.strip()
            path = _find_artifact_path(output_dir, plan_id, name)
            if path:
                kind = 'screenshot' if name.lower().endswith('.png') else (
                    'page' if name.lower().endswith('.html') else 'error'
                )
                links.append({'label': name, 'path': path, 'kind': kind})
    return links

def _build_plan_dashboard_data(df, plans_df):
    """Build plan-level rollup records with metadata from y1Plans."""
    plan_meta = {}
    if plans_df is not None and not plans_df.empty:
        for _, row in plans_df.iterrows():
            plan_id = _clean_dashboard_value(row.get('PlanId'))
            if not plan_id:
                continue
            tags_raw = _clean_dashboard_value(row.get('Tags')) or ''
            plan_meta[plan_id] = {
                'planId': plan_id,
                'planName': _clean_dashboard_value(row.get('PlanName')) or plan_id,
                'designId': _clean_dashboard_value(row.get('DesignId')) or '',
                'tags': [t.strip() for t in tags_raw.split(';') if t.strip()],
                'output': _clean_dashboard_value(row.get('Output')),
            }

    plans_data = []
    for plan_id, group in df.groupby('PlanId', sort=False):
        results = group['Result'].tolist()
        if all(r == 'Pass' for r in results if pd.notna(r) and r):
            rollup = 'Pass'
        elif any(r == 'Fail' for r in results if pd.notna(r)):
            rollup = 'Fail'
        else:
            rollup = 'Pending'
        duration = round(float(group['TimeTaken'].fillna(0).sum()), 2)
        failed_rows = group[group['Result'] == 'Fail']
        failed_step = None
        if not failed_rows.empty:
            fr = failed_rows.iloc[0]
            failed_step = {
                'stepId': _clean_dashboard_value(fr.get('StepId')),
                'stepInfo': _clean_dashboard_value(fr.get('StepInfo')),
                'actionName': _clean_dashboard_value(fr.get('ActionName')),
            }
        meta = plan_meta.get(plan_id, {})
        plans_data.append({
            'planId': plan_id,
            'planName': meta.get('planName', plan_id),
            'designId': meta.get('designId') or _clean_dashboard_value(group.iloc[0].get('DesignId')),
            'tags': meta.get('tags', []),
            'output': meta.get('output'),
            'result': rollup,
            'duration': duration,
            'stepCount': len(group),
            'passedSteps': int((group['Result'] == 'Pass').sum()),
            'failedSteps': int((group['Result'] == 'Fail').sum()),
            'failedStep': failed_step,
        })
    return plans_data

def _build_tag_summary(plans_data):
    """Aggregate pass/fail counts per tag token."""
    tag_stats = {}
    for plan in plans_data:
        tags = plan.get('tags') or ['Untagged']
        if not tags:
            tags = ['Untagged']
        for tag in tags:
            entry = tag_stats.setdefault(tag, {'tag': tag, 'total': 0, 'pass': 0, 'fail': 0, 'pending': 0})
            entry['total'] += 1
            result = plan.get('result', 'Pending')
            if result == 'Pass':
                entry['pass'] += 1
            elif result == 'Fail':
                entry['fail'] += 1
            else:
                entry['pending'] += 1
    return sorted(tag_stats.values(), key=lambda x: (-x['total'], x['tag'].lower()))

def generate_dashboard(df, output_dir, ypad_name, plans_df=None, run_meta=None):
    """Generate modern interactive HTML dashboard from results DataFrame."""
    run_meta = run_meta or {}
    plans_data = _build_plan_dashboard_data(df, plans_df)
    tag_summary = _build_tag_summary(plans_data)

    summary_plans = {
        "total": len(plans_data),
        "pass": sum(1 for p in plans_data if p['result'] == 'Pass'),
        "fail": sum(1 for p in plans_data if p['result'] == 'Fail'),
        "pending": sum(1 for p in plans_data if p['result'] == 'Pending'),
        "duration": round(float(df['TimeTaken'].fillna(0).sum()), 2),
    }
    summary_steps = {
        "total": len(df),
        "pass": int((df['Result'] == 'Pass').sum()),
        "fail": int((df['Result'] == 'Fail').sum()),
        "pending": int(df['Result'].isna().sum()),
        "duration": summary_plans["duration"],
    }

    template_path = _resource_path('z/zDash_template.html')
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        html_content = _get_inline_dashboard_template()

    results_data = []
    for _, row in df.iterrows():
        plan_id = _clean_dashboard_value(row.get('PlanId')) or ''
        output_raw = row.get('Output', '')
        output_text = _clean_dashboard_value(output_raw) or ''
        artifact_links = _parse_artifact_links(output_raw, output_dir, plan_id)

        screenshot_file = None
        for link in artifact_links:
            if link['kind'] == 'screenshot' or link['label'].lower().endswith('.png'):
                screenshot_file = link['path']
                break
        if not screenshot_file and row.get('ActionType') == 'xUI' and row.get('Result') == 'Fail':
            potential_screenshot = f"{plan_id}_{row.get('DesignId', '')}_{row.get('StepId', '')}.png"
            screenshot_path = os.path.join(output_dir, potential_screenshot)
            if os.path.exists(screenshot_path):
                screenshot_file = potential_screenshot
        if not screenshot_file and pd.notna(row.get('Screenshot')):
            shot = _clean_dashboard_value(row.get('Screenshot'))
            if shot:
                screenshot_file = _find_artifact_path(output_dir, plan_id, shot) or shot

        error_details = None
        if row.get('Result') == 'Fail':
            error_details = {
                'type': 'TestFailure',
                'message': output_text or 'Test failed',
                'url': None,
                'stackTrace': None,
            }

        results_data.append({
            'designId': _clean_dashboard_value(row.get('DesignId')),
            'planId': plan_id,
            'stepId': _clean_dashboard_value(row.get('StepId')),
            'stepInfo': _clean_dashboard_value(row.get('StepInfo')),
            'actionType': _clean_dashboard_value(row.get('ActionType')),
            'actionName': _clean_dashboard_value(row.get('ActionName')),
            'input': _clean_dashboard_value(row.get('Input')),
            'output': output_text,
            'expected': _clean_dashboard_value(row.get('Expected')),
            'result': _clean_dashboard_value(row.get('Result')),
            'time': _clean_dashboard_value(row.get('Time')) or datetime.now().strftime("%H:%M:%S"),
            'timeTaken': round(float(row.get('TimeTaken', 0) or 0), 2),
            'critical': _clean_dashboard_value(row.get('Critical')) or 'n',
            'screenshot': screenshot_file,
            'artifactLinks': artifact_links,
            'errorDetails': error_details,
        })

    run_meta_payload = {
        'suite': ypad_name,
        'generatedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'outputDir': os.path.basename(output_dir),
        'resultsCsv': f"{ypad_name}_zResults.csv",
        'errorsCsv': '_errors.csv' if os.path.exists(os.path.join(output_dir, '_errors.csv')) else None,
        'brahlReport': 'brahl_report.md' if os.path.exists(os.path.join(output_dir, 'brahl_report.md')) else None,
        'tagsFilter': run_meta.get('tags', []),
        'threadCount': run_meta.get('thread_count', 1),
        'timeout': run_meta.get('timeout', 10),
        'headless': run_meta.get('headless', False),
        'wallClockSeconds': round(float(run_meta.get('wall_clock_seconds', summary_plans['duration'])), 2),
        'suiteUrl': run_meta.get('suite_url'),
        'summaryPlans': summary_plans,
        'summarySteps': summary_steps,
    }

    replacements = {
        '{YPAD_NAME}': ypad_name,
        '{GENERATION_TIME}': run_meta_payload['generatedAt'],
        '{RESULTS_DATA_JSON}': json.dumps(results_data, indent=2),
        '{PLANS_DATA_JSON}': json.dumps(plans_data, indent=2),
        '{RUN_META_JSON}': json.dumps(run_meta_payload, indent=2),
        '{TAG_SUMMARY_JSON}': json.dumps(tag_summary, indent=2),
    }
    for placeholder, value in replacements.items():
        html_content = html_content.replace(placeholder, value)

    dashboard_path = os.path.join(output_dir, f"{ypad_name}_zDash.html")
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return dashboard_path

def _get_inline_dashboard_template():
    """Fallback inline dashboard template if external file is not available."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FoXYiZ Test Dashboard - {YPAD_NAME}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f8fafc; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 12px; margin-bottom: 2rem; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .card h3 { margin: 0 0 0.5rem 0; color: #64748b; font-size: 0.875rem; text-transform: uppercase; }
        .card .value { font-size: 2rem; font-weight: bold; color: #1e293b; }
        .results { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
        th { background: #f8fafc; font-weight: 600; }
        .status-pass { background: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
        .status-fail { background: #fecaca; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>FoXYiZ Test Dashboard</h1>
            <p>Test Suite: <strong>{YPAD_NAME}</strong> | Generated: <strong>{GENERATION_TIME}</strong></p>
        </div>
        <div class="summary">
            <div class="card"><h3>Total Tests</h3><div class="value">{TOTAL_ACTIONS}</div></div>
            <div class="card"><h3>Passed</h3><div class="value">{PASSED_ACTIONS}</div></div>
            <div class="card"><h3>Failed</h3><div class="value">{FAILED_ACTIONS}</div></div>
            <div class="card"><h3>Pending</h3><div class="value">{PENDING_ACTIONS}</div></div>
            <div class="card"><h3>Duration</h3><div class="value">{TOTAL_TIME}s</div></div>
        </div>
        <div class="results">
            <table id="results-table">
                <thead>
                    <tr><th>Plan ID</th><th>Step</th><th>Action</th><th>Status</th><th>Duration</th></tr>
                </thead>
                <tbody id="results-tbody"></tbody>
            </table>
        </div>
    </div>
    <script>
        const testResults = [];
        // Fallback simple table rendering
        const tbody = document.getElementById('results-tbody');
        testResults.forEach(result => {
            const row = document.createElement('tr');
            const statusClass = result.result === 'Pass' ? 'status-pass' : 'status-fail';
            row.innerHTML = `
                <td><strong>${result.planId}</strong></td>
                <td>${result.stepId} - ${result.stepInfo}</td>
                <td>${result.actionType} → ${result.actionName}</td>
                <td><span class="${statusClass}">${result.result}</span></td>
                <td>${result.timeTaken ? result.timeTaken.toFixed(2) + 's' : '-'}</td>
            `;
            tbody.appendChild(row);
        });
    </script>
</body>
</html>"""

def _generate_basic_dashboard(df, output_dir, ypad_name):
    """Fallback function to generate basic dashboard if template is not found (from fEngine2.py v2)."""
    summary_plans = {
        "Total": len(df['PlanId'].unique()),
        "Executed": len(df[df['Result'].notna()]['PlanId'].unique()),
        "Pending": len(df[df['Result'].isna()]['PlanId'].unique()),
        "Time Taken (s)": round(df['TimeTaken'].sum(), 2),
        "Pass": len(df[df['Result'] == 'Pass']['PlanId'].unique()),
        "Fail": len(df[df['Result'] == 'Fail']['PlanId'].unique())
    }
    summary_actions = {
        "Total": len(df),
        "Executed": len(df[df['Result'].notna()]),
        "Pending": len(df[df['Result'].isna()]),
        "Time Taken (s)": round(df['TimeTaken'].sum(), 2),
        "Pass": len(df[df['Result'] == 'Pass']),
        "Fail": len(df[df['Result'] == 'Fail'])
    }

    html_content = """
    <html>
    <head>
        <title>Test Dashboard - {}</title>
        <style>
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>Test Dashboard - {}</h1>
        <h2>Summary - Plans</h2>
        <table>
            <tr><th>Total</th><td>{}</td></tr>
            <tr><th>Executed</th><td>{}</td></tr>
            <tr><th>Pending</th><td>{}</td></tr>
            <tr><th>Time Taken (s)</th><td>{}</td></tr>
            <tr><th>Pass</th><td>{}</td></tr>
            <tr><th>Fail</th><td>{}</td></tr>
        </table>
        <h2>Summary - Actions</h2>
        <table>
            <tr><th>Total</th><td>{}</td></tr>
            <tr><th>Executed</th><td>{}</td></tr>
            <tr><th>Pending</th><td>{}</td></tr>
            <tr><th>Time Taken (s)</th><td>{}</td></tr>
            <tr><th>Pass</th><td>{}</td></tr>
            <tr><th>Fail</th><td>{}</td></tr>
        </table>
        <h2>Plans</h2>
        <table>
            <tr><th>DesignId</th><th>PlanId</th><th>Output</th><th>Result</th><th>Time (s)</th></tr>
            {}
        </table>
        <h2>Actions</h2>
        <table>
            <tr><th>DesignId</th><th>PlanId</th><th>StepId</th><th>StepInfo</th><th>ActionType</th><th>ActionName</th><th>Input</th><th>Output</th><th>Expected</th><th>Result</th><th>TimeTaken (s)</th></tr>
            {}
        </table>
    </body>
    </html>
    """

    plan_rows = ""
    for _, row in df.groupby(['DesignId', 'PlanId']).first().reset_index().iterrows():
        plan_rows += f"<tr><td>{row['DesignId']}</td><td>{row['PlanId']}</td><td>{row.get('Output', '')}</td><td>{row['Result']}</td><td>{round(row['TimeTaken'], 2)}</td></tr>\n"

    action_rows = ""
    for _, row in df.iterrows():
        action_rows += f"<tr><td>{row['DesignId']}</td><td>{row['PlanId']}</td><td>{row['StepId']}</td><td>{row['StepInfo']}</td><td>{row['ActionType']}</td><td>{row['ActionName']}</td><td>{row['Input']}</td><td>{row['Output']}</td><td>{row.get('Expected', '')}</td><td>{row['Result']}</td><td>{round(row['TimeTaken'], 2)}</td></tr>\n"

    html_content = html_content.format(
        ypad_name, ypad_name,
        summary_plans["Total"], summary_plans["Executed"], summary_plans["Pending"],
        summary_plans["Time Taken (s)"], summary_plans["Pass"], summary_plans["Fail"],
        summary_actions["Total"], summary_actions["Executed"], summary_actions["Pending"],
        summary_actions["Time Taken (s)"], summary_actions["Pass"], summary_actions["Fail"],
        plan_rows, action_rows
    )

    dashboard_path = os.path.join(output_dir, f"{ypad_name}_zDash.html")
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

def process_action(args):
    """Process a single action for a given plan and design.
    args may include optional previous_results (list of result dicts from earlier steps)
    so that placeholders like {{step:S2}} can be replaced with that step's Output.
    """
    plan_id, design_id, action_row, results_dir, timeout, ypad_config = args[:6]
    previous_results = args[6] if len(args) > 6 else []
    ui_handler = args[7] if len(args) > 7 else None
    step_id = action_row['StepId']
    action_type = action_row['ActionType']
    action_name = action_row['ActionName']
    input_data = str(action_row['Input'])
    expected = str(action_row.get('Expected', ''))
    output = action_row.get('Output', '')
    step_info = action_row.get('StepInfo', '')
    critical = str(action_row.get('Critical', 'n')).strip().lower()

    # Suppress technical logging - only log warnings and errors
    # logger.info(f"Processing action for PlanId={plan_id}")

    # Resolve variables from y3Designs.csv (load all design files and concatenate)
    try:
        y3_designs_list = []
        for design_file in ypad_config['input_files']['yDesigns']:
            try:
                df = load_csv(design_file)
                y3_designs_list.append(df)
            except Exception as e:
                logger.warning(f"Failed to load design file {design_file}: {str(e)}")
        if y3_designs_list:
            y3_designs = pd.concat(y3_designs_list, ignore_index=True)
        else:
            y3_designs = pd.DataFrame()
    except Exception as e:
        # If loading designs fails, log but continue (variables won't be resolved)
        logger.warning(f"Failed to load y3Designs files: {str(e)}")
        y3_designs = pd.DataFrame()
    
    import re
    for col in y3_designs.columns:
        if col not in ['Type', 'DataName']:
            if col == design_id:
                for _, row in y3_designs.iterrows():
                    try:
                        data_name = row['DataName']
                        data_value = str(row[design_id])
                        # Clean the data value: remove leading/trailing quotes only if they wrap the entire value
                        # This handles cases where CSV values have extra outer quotes, but preserves quotes in content
                        data_value = data_value.strip()
                        
                        # Remove outer quotes more aggressively - handle cases where value has quotes inside
                        # Keep removing outer quotes until no more can be removed
                        # This handles: "value", ""value"", """value""", etc.
                        max_iterations = 10  # Prevent infinite loops
                        iteration = 0
                        while iteration < max_iterations and len(data_value) >= 2:
                            iteration += 1
                            original_value = data_value
                            
                            # Check for double quote at start and end
                            if data_value.startswith('"') and data_value.endswith('"'):
                                # Count consecutive quotes at the start and end
                                start_quotes = 0
                                end_quotes = 0
                                for i in range(len(data_value)):
                                    if data_value[i] == '"':
                                        start_quotes += 1
                                    else:
                                        break
                                for i in range(len(data_value) - 1, -1, -1):
                                    if data_value[i] == '"':
                                        end_quotes += 1
                                    else:
                                        break
                                # If we have matching quotes at start and end, remove one layer
                                if start_quotes > 0 and end_quotes > 0 and start_quotes == end_quotes:
                                    data_value = data_value[start_quotes:-end_quotes].strip()
                                    # Continue loop to check if there are more outer quotes
                                    continue
                            
                            # Check for single quote at start and end
                            if data_value.startswith("'") and data_value.endswith("'"):
                                start_quotes = 0
                                end_quotes = 0
                                for i in range(len(data_value)):
                                    if data_value[i] == "'":
                                        start_quotes += 1
                                    else:
                                        break
                                for i in range(len(data_value) - 1, -1, -1):
                                    if data_value[i] == "'":
                                        end_quotes += 1
                                    else:
                                        break
                                if start_quotes > 0 and end_quotes > 0 and start_quotes == end_quotes:
                                    data_value = data_value[start_quotes:-end_quotes].strip()
                                    # Continue loop to check if there are more outer quotes
                                    continue
                            
                            # If no changes were made, break
                            if data_value == original_value:
                                break
                        
                        # Fix CSS selectors: convert double quotes to single quotes in attribute selectors
                        # This fixes issues like: button[onclick="addElement()"] -> button[onclick='addElement()']
                        # Also handles escaped quotes: button[onclick=""addElement()""] -> button[onclick='addElement()']
                        # CSS attribute selectors work better with single quotes inside
                        if data_value.startswith('css==') or '[' in data_value:
                            try:
                                # First, handle escaped double quotes ("" -> ")
                                # This handles cases where CSV has ""addElement()"" which pandas might not fully unescape
                                # Replace all occurrences of "" with " (handle multiple escaped quotes)
                                while '""' in data_value:
                                    data_value = data_value.replace('""', '"')
                                
                                # Pattern to match attribute selectors with double quotes: [attr="value"]
                                # Replace with single quotes: [attr='value']
                                def fix_css_quotes(match):
                                    try:
                                        attr_part = match.group(1)  # The attribute name and = sign
                                        value = match.group(2)  # The value inside double quotes
                                        return f"[{attr_part}'{value}']"
                                    except Exception:
                                        # If regex replacement fails, return original match
                                        return match.group(0)
                                
                                # Match pattern: [attribute="value"] and replace with [attribute='value']
                                # Use try-except to handle any regex errors gracefully
                                # Apply multiple times to handle nested or multiple attribute selectors
                                prev_value = ""
                                while prev_value != data_value:
                                    prev_value = data_value
                                    data_value = re.sub(r'\[([^=]+=)"([^"]+)"\]', fix_css_quotes, data_value)
                            except Exception:
                                # If CSS quote fixing fails, continue with original value
                                # This ensures the code doesn't crash on Linux if regex fails
                                pass
                        
                        # Substitute sensitive placeholders from .env (e.g. OPENWEATHERMAP_API, EMAIL_ID, YOUR_PASSWORD)
                        data_value = _substitute_env_in_value(data_value)
                        
                        # Use word boundary replacement to avoid partial matches
                        # But exclude matches that are part of dot-notation paths (e.g., coord.lat should not replace 'lat')
                        # Match variable name only when it's not preceded by a dot and not followed by a dot
                        pattern = r'(?<!\.)\b' + re.escape(data_name) + r'\b(?!\.)'
                        # Use lambda to avoid regex interpretation of replacement string
                        input_data = re.sub(pattern, lambda m: data_value, input_data)
                        expected = re.sub(pattern, lambda m: data_value, expected)
                    except Exception as e:
                        # If variable resolution fails for one row, log and continue
                        logger.warning(f"Failed to resolve variable {data_name if 'data_name' in locals() else 'unknown'}: {str(e)}")
                        continue

    # Resolve {{step:StepId}} placeholders from previous steps' Output (same plan/design)
    for prev in previous_results:
        if prev.get('PlanId') != plan_id or prev.get('DesignId') != design_id:
            continue
        ref_step_id = str(prev.get('StepId', ''))
        out_val = prev.get('Output', '')
        if ref_step_id and out_val is not None:
            placeholder = '{{step:' + ref_step_id + '}}'
            input_data = input_data.replace(placeholder, str(out_val))
            expected = expected.replace(placeholder, str(out_val))

    # Check cache for repeated actions
    cache_key = f"{plan_id}_{step_id}_{input_data}"
    if cache_key in action_cache:
        result, output, time_taken = action_cache[cache_key]
        return {
            'DesignId': design_id, 'PlanId': plan_id, 'StepId': step_id,
            'StepInfo': step_info, 'ActionType': action_type, 'ActionName': action_name,
            'Input': input_data, 'Output': output, 'Expected': expected,
            'Result': result, 'Time': datetime.now().strftime("%H:%M:%S"), 'TimeTaken': time_taken
        }

    # Handle xReuse by re-running the reused plan's actions
    if ui_handler is None:
        ui_handler = xActions.UIActionHandler(timeout=timeout)
    if action_type == "xReuse":
        reused_plan_id = action_name
        # Load all plan files and concatenate
        y1_plans_list = []
        for plan_file in ypad_config['input_files']['yPlans']:
            try:
                df = load_csv(plan_file)
                y1_plans_list.append(df)
            except Exception as e:
                logger.warning(f"Failed to load plan file {plan_file}: {str(e)}")
        y1_plans = pd.concat(y1_plans_list, ignore_index=True) if y1_plans_list else pd.DataFrame()
        
        # Load all action files and concatenate
        y2_actions_list = []
        for action_file in ypad_config['input_files']['yActions']:
            try:
                df = load_csv(action_file)
                y2_actions_list.append(df)
            except Exception as e:
                logger.warning(f"Failed to load action file {action_file}: {str(e)}")
        y2_actions = pd.concat(y2_actions_list, ignore_index=True) if y2_actions_list else pd.DataFrame()
        
        reused_plan = y1_plans[y1_plans['PlanId'] == reused_plan_id]
        if reused_plan.empty:
            raise ValueError(f"Reused plan {reused_plan_id} not found")
        reused_actions = y2_actions[y2_actions['PlanId'] == reused_plan_id]
        
        # Process all reused actions and collect results (from fEngine.py v1 - better reporting)
        reuse_results = []
        for _, reused_action in reused_actions.iterrows():
            reused_args = (reused_plan_id, design_id, reused_action, results_dir, timeout, ypad_config, reuse_results, ui_handler)
            action_result = process_action(reused_args)
            reuse_results.append(action_result)
            if action_result['ActionType'] == "xUI" and action_result['ActionName'] == "xOpenBrowser":
                continue  # Browser already opened by ui_handler
            if action_result['Result'] == "Fail":
                return action_result
        
        # Return success result for xReuse (from fEngine.py v1 - provides better feedback)
        return {
            'DesignId': design_id, 'PlanId': plan_id, 'StepId': step_id,
            'StepInfo': step_info, 'ActionType': action_type, 'ActionName': action_name,
            'Input': input_data, 'Output': f"Successfully reused plan {reused_plan_id} with {len(reuse_results)} actions", 
            'Expected': expected, 'Result': 'Pass', 'Time': datetime.now().strftime("%H:%M:%S"), 'TimeTaken': 0
        }

    # Execute the action (no driver_path logic)
    # Only pass ui_handler for UI/capture actions to maintain browser session and timer state
    if ui_handler is None:
        ui_handler = xActions.UIActionHandler(timeout=timeout)
    handler_param = ui_handler if action_type in ("xUI", "xCapture") else None
    
    # Add 0-second delay before closing browser to ensure all operations complete (from fEngine2.py v2)
    if action_type == "xUI" and action_name == "xCloseBrowser":
        time.sleep(0)
    
    result, output, time_taken = xActions.runAction(
        action_type, action_name, input_data, output, expected,
        plan_id, design_id, step_id, results_dir, handler=handler_param, timeout=timeout
    )

    # Cache the result
    action_cache[cache_key] = (result, output, time_taken)

    return {
        'DesignId': design_id, 'PlanId': plan_id, 'StepId': step_id,
        'StepInfo': step_info, 'ActionType': action_type, 'ActionName': action_name,
        'Input': input_data, 'Output': output, 'Expected': expected,
        'Critical': critical,
        'Result': result, 'Time': datetime.now().strftime("%H:%M:%S"), 'TimeTaken': time_taken
    }

def process_plan(args):
    """Process a single plan for a given design."""
    plan_row, ypad_config, output_dir, timeout, plan_index, total_plans = args
    plan_id = plan_row['PlanId']
    design_ids = str(plan_row['DesignId']).split(';')
    
    # Load all action files and concatenate
    y2_actions_list = []
    for action_file in ypad_config['input_files']['yActions']:
        try:
            df = load_csv(action_file)
            y2_actions_list.append(df)
        except Exception as e:
            logger.warning(f"Failed to load action file {action_file}: {str(e)}")
    y2_actions = pd.concat(y2_actions_list, ignore_index=True) if y2_actions_list else pd.DataFrame()
    
    actions = y2_actions[y2_actions['PlanId'] == plan_id]
    results = []

    # Show plan execution start
    print_status(f"Starting plan: {plan_id}", "RUNNING")
    
    for design_id in design_ids:
        # Suppress technical logging
        # logger.info(f"Executing PlanId={plan_id} for DesignId={design_id}")
        results_dir = os.path.join(output_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{plan_id}")
        os.makedirs(results_dir, exist_ok=True)
        ui_handler = xActions.UIActionHandler(timeout=timeout)

        # Process each action (pass previous results so {{step:StepId}} can be resolved)
        for action_index, (_, action_row) in enumerate(actions.iterrows(), 1):
            action_args = (plan_id, design_id, action_row, results_dir, timeout, ypad_config, results, ui_handler)
            result = process_action(action_args)
            results.append(result)
            
            # Show action progress
            if result['Result'] == 'Pass':
                print_status(f"  ✓ {action_row['StepInfo']}", "SUCCESS")
            elif result['Result'] == 'Fail':
                print_status(f"  ✗ {action_row['StepInfo']} - {result.get('Output', 'Failed')}", "ERROR")
                # If action marked Critical, stop executing remaining actions for this plan/design
                is_critical = str(action_row.get('Critical', 'n')).strip().lower() in {'y', 'yes', 'true', '1'}
                if is_critical:
                    print_status(f"  → Critical step failed. Skipping remaining actions for plan {plan_id} / design {design_id}.", "WARNING")
                    break

    # Show plan completion
    plan_results = [r for r in results if r['PlanId'] == plan_id]
    passed_actions = len([r for r in plan_results if r['Result'] == 'Pass'])
    total_actions = len(plan_results)
    
    if passed_actions == total_actions:
        print_status(f"Plan {plan_id} completed successfully ({passed_actions}/{total_actions} actions)", "SUCCESS")
    else:
        print_status(f"Plan {plan_id} completed with issues ({passed_actions}/{total_actions} actions passed)", "WARNING")

    return results


def _execute_single_ypad_suite(config_index, total_configs, config_path, main_config, debug_mode, timeout, start_time):
    """Run one YPAD (test suite): load plans, execute plans, write results and dashboard."""
    # Each process (including multiprocessing workers) must load .env for y3Designs substitution.
    load_env()
    try:
        if hasattr(xActions, "set_debug_mode"):
            xActions.set_debug_mode(debug_mode)
        if hasattr(xActions, "set_capture_config"):
            xActions.set_capture_config(main_config.get("capture"))
    except Exception:
        pass

    print_header(f"Processing Test Suite {config_index}/{total_configs}")

    try:
        ypad_config = load_config(config_path)
    except FileNotFoundError:
        print_status(f"yPAD config not found: {config_path}", "ERROR")
        return
    ypad_name = os.path.splitext(os.path.basename(config_path))[0]
    output_dir = os.path.join(
        _results_z_root(),
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{ypad_name}",
    )
    os.makedirs(output_dir, exist_ok=True)
    if debug_mode:
        os.makedirs(os.path.join(output_dir, "_debug"), exist_ok=True)

    print_status(f"Test Suite: {ypad_name}", "INFO")
    print_status(f"Output Directory: {output_dir}", "INFO")

    # Load plans and filter by Run=Y (load all plan files and concatenate)
    y1_plans_list = []
    for plan_file in ypad_config['input_files']['yPlans']:
        try:
            df = load_csv(plan_file)
            y1_plans_list.append(df)
            print_status(f"Loaded plan file: {os.path.basename(plan_file)} ({len(df)} plans)", "INFO")
        except Exception as e:
            print_status(f"Failed to load plan file {plan_file}: {str(e)}", "ERROR")
    if y1_plans_list:
        y1_plans = pd.concat(y1_plans_list, ignore_index=True)
        print_status(f"Total plans loaded: {len(y1_plans)} from {len(y1_plans_list)} file(s)", "INFO")
    else:
        print_status("No plan files could be loaded", "ERROR")
        return

    # Check if 'Run' column exists (case-insensitive check)
    run_column = None
    for col in y1_plans.columns:
        cleaned_col = col.strip().strip('"').strip("'")
        if cleaned_col.lower() == 'run':
            run_column = col
            break

    if run_column is None:
        available_columns = ', '.join([f"'{col}'" for col in y1_plans.columns.tolist()])
        print_status(f"Error: 'Run' column not found in y1Plans.csv", "ERROR")
        print_status(f"Available columns: {available_columns}", "ERROR")
        print_status(f"CSV file: {ypad_config['input_files']['yPlans'][0]}", "ERROR")
        print_status(f"Number of columns: {len(y1_plans.columns)}", "ERROR")
        return

    plans_to_run = y1_plans[y1_plans[run_column] == 'Y']

    tags_config = main_config.get("tags", [])
    if tags_config is None:
        tags_config = []
    elif isinstance(tags_config, str):
        tags_config = [tags_config] if tags_config.strip() else []
    elif not isinstance(tags_config, list):
        tags_config = []

    tags_column = None
    for col in y1_plans.columns:
        cleaned_col = col.strip().strip('"').strip("'")
        if cleaned_col.lower() == 'tags':
            tags_column = col
            break

    if tags_column and tags_config:
        tags_lower = [str(tag).strip().lower() for tag in tags_config if tag]
        if 'all' in tags_lower:
            print_status("Tag filter: 'All' specified - running all plans", "INFO")
        else:
            def tag_matches(row):
                plan_tags_raw = str(row[tags_column]).strip().lower() if pd.notna(row[tags_column]) else ""
                plan_tags = [t.strip().strip('"').strip("'") for t in plan_tags_raw.split(';') if t.strip()]
                return any(tag_lower in plan_tags for tag_lower in tags_lower)

            plans_to_run = plans_to_run[plans_to_run.apply(tag_matches, axis=1)]
            if len(tags_lower) > 0:
                print_status(f"Tag filter: Running plans with tags: {', '.join(tags_config)}", "INFO")
    elif tags_config and not tags_column:
        print_status("Warning: Tags specified but 'Tags' column not found in y1Plans.csv - running all plans", "WARNING")

    print_status(f"Found {len(plans_to_run)} plans to execute", "INFO")

    if len(plans_to_run) == 0:
        print_status("No plans marked for execution (Run=Y)", "WARNING")
        return

    all_results = []
    for plan_index, (_, plan_row) in enumerate(plans_to_run.iterrows(), 1):
        plan_args = (plan_row, ypad_config, output_dir, timeout, plan_index, len(plans_to_run))
        results = process_plan(plan_args)
        all_results.extend(results)
        print_progress(plan_index, len(plans_to_run), "plans")

    print()

    print_status("Generating results and dashboard...", "INFO")
    df = pd.DataFrame(all_results)
    df.to_csv(os.path.join(output_dir, f"{ypad_name}_zResults.csv"), index=False)
    suite_url = ypad_config.get('url') if isinstance(ypad_config, dict) else None
    run_meta = {
        'tags': tags_config,
        'thread_count': main_config.get('thread_count', 1),
        'timeout': timeout,
        'headless': main_config.get('headless', False),
        'capture': main_config.get('capture') or xActions.get_capture_config(),
        'wall_clock_seconds': time.time() - start_time,
        'suite_url': suite_url,
    }
    generate_dashboard(df, output_dir, ypad_name, plans_df=plans_to_run, run_meta=run_meta)

    try:
        removed = cleanup_empty_directories(output_dir)
        if removed > 0:
            print_status(f"Cleaned up {removed} empty directory(ies)", "INFO")
    except Exception as e:
        logger.debug(f"Failed to clean up empty directories: {str(e)}")

    try:
        err_csv = os.path.join(output_dir, "_errors.csv")
        if os.path.exists(err_csv):
            print_status(f"Error summary saved: {err_csv}", "WARNING")
    except Exception:
        pass

    total_plans = len(plans_to_run)
    plan_results = df.groupby('PlanId').agg({
        'Result': lambda x: 'Pass' if (x == 'Pass').all() else 'Fail'
    }).reset_index()

    passed_plans = len(plan_results[plan_results['Result'] == 'Pass'])
    failed_plans = len(plan_results[plan_results['Result'] == 'Fail'])
    total_time = time.time() - start_time

    dashboard_path = os.path.join(output_dir, f"{ypad_name}_zDash.html")

    summary_stats = {
        'total_plans': total_plans,
        'passed': passed_plans,
        'failed': failed_plans,
        'total_time': total_time,
        'output_dir': output_dir,
        'dashboard_path': dashboard_path
    }

    print_summary(summary_stats)
    print_status(f"Test suite '{ypad_name}' completed successfully!", "SUCCESS")

    try:
        if hasattr(xActions, 'UIActionHandler'):
            if hasattr(xActions.UIActionHandler, '_shared_driver') and xActions.UIActionHandler._shared_driver:
                try:
                    xActions.UIActionHandler._shared_driver.quit()
                except Exception:
                    pass
                xActions.UIActionHandler._shared_driver = None
            if getattr(xActions.UIActionHandler, '_chrome_user_data_dir', None):
                try:
                    shutil.rmtree(xActions.UIActionHandler._chrome_user_data_dir, ignore_errors=True)
                except Exception:
                    pass
                xActions.UIActionHandler._chrome_user_data_dir = None

            if hasattr(xActions.UIActionHandler, '_thread_local'):
                if hasattr(xActions.UIActionHandler._thread_local, 'driver') and xActions.UIActionHandler._thread_local.driver:
                    try:
                        xActions.UIActionHandler._thread_local.driver.quit()
                    except Exception:
                        pass
                    xActions.UIActionHandler._thread_local.driver = None
    except Exception:
        pass


def run_ypad_suite_worker(args):
    """Worker for parallel YPAD runs: capture stdout/stderr so the parent can print in config order."""
    import traceback
    import logging
    config_index, total_configs, config_path, main_config, debug_mode, timeout, start_time = args
    buf = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level
    try:
        sys.stdout = buf
        sys.stderr = buf
        # Rebind logging to the worker buffer so third-party INFO logs (e.g., webdriver_manager)
        # are captured and replayed in-order with suite output.
        buffer_handler = logging.StreamHandler(buf)
        buffer_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        root_logger.handlers = [buffer_handler]
        if original_level > logging.INFO:
            root_logger.setLevel(logging.INFO)
        _execute_single_ypad_suite(
            config_index, total_configs, config_path, main_config, debug_mode, timeout, start_time
        )
    except Exception:
        traceback.print_exc(file=buf)
    finally:
        root_logger.handlers = original_handlers
        root_logger.setLevel(original_level)
        sys.stdout = old_out
        sys.stderr = old_err
    return config_index, buf.getvalue()


def _normalize_buffered_output(text):
    """Normalize buffered output so replay in parent console is stable."""
    # Keep only the visible segment after the last carriage return on each line.
    normalized = []
    for line in text.replace('\r\n', '\n').split('\n'):
        normalized.append(line.split('\r')[-1] if '\r' in line else line)
    return '\n'.join(normalized)


def _wait_future_with_heartbeat(future, suite_name, config_index, total_configs, interval_sec):
    """
    Block until future completes while printing a live heartbeat on the real console.
    Worker output stays buffered; this only shows that suites are still running.
    """
    bar_len = 24
    tick = 0
    start = time.time()
    while True:
        if future.done():
            sys.stdout.write("\r" + " " * 120 + "\r")
            sys.stdout.flush()
            return future.result()
        elapsed = int(time.time() - start)
        phase = tick % (bar_len + 1)
        bar = "█" * phase + "-" * (bar_len - phase)
        extra = ""
        if total_configs > 1:
            extra = " (parallel workers may be running other suites)"
        line = (
            f"\rProgress: |{bar}| {elapsed}s — waiting for {suite_name} "
            f"(suite {config_index}/{total_configs}){extra}…"
        )
        sys.stdout.write(line)
        sys.stdout.flush()
        tick += 1
        time.sleep(max(0.5, float(interval_sec)))


def main():
    """Main function to execute the test framework."""
    # Clear action cache to ensure fresh execution
    global action_cache
    action_cache.clear()
    
    # Kill any leftover chromedriver processes from previous executions
    kill_chromedriver_processes()
    
    # Clean up any leftover browser drivers from previous executions
    try:
        if hasattr(xActions, 'UIActionHandler'):
            # Clean up shared driver
            if hasattr(xActions.UIActionHandler, '_shared_driver') and xActions.UIActionHandler._shared_driver:
                try:
                    xActions.UIActionHandler._shared_driver.quit()
                except Exception:
                    pass
                xActions.UIActionHandler._shared_driver = None
            if getattr(xActions.UIActionHandler, '_chrome_user_data_dir', None):
                try:
                    shutil.rmtree(xActions.UIActionHandler._chrome_user_data_dir, ignore_errors=True)
                except Exception:
                    pass
                xActions.UIActionHandler._chrome_user_data_dir = None
            
            # Clean up thread-local driver if it exists
            if hasattr(xActions.UIActionHandler, '_thread_local'):
                if hasattr(xActions.UIActionHandler._thread_local, 'driver') and xActions.UIActionHandler._thread_local.driver:
                    try:
                        xActions.UIActionHandler._thread_local.driver.quit()
                    except Exception:
                        pass
                    xActions.UIActionHandler._thread_local.driver = None
    except Exception:
        pass  # Don't fail if cleanup fails
    
    parser = argparse.ArgumentParser(description="FoXYiZ Test Framework")
    parser.add_argument(
        '--config',
        required=False,
        default=_default_main_config_path(),
        help="Path to the main config JSON file (default: f/fStart/default.json in dev)",
    )
    parser.add_argument('--debug', action='store_true', help="Enable verbose debug logging and error artifacts")
    args = parser.parse_args()

    # Show startup banner
    print_header("FoXYiZ Test Framework")
    print_status("Loading configuration...", "INFO")
    
    # Load .env for sensitive placeholders used in y3Designs (e.g. OPENWEATHERMAP_API, EMAIL_ID)
    env_path = _env_path()
    if env_path:
        load_env()
        print_status(f"Loaded .env from {os.path.dirname(env_path)}", "INFO")
    else:
        load_env()
    
    # Load main config
    # Resolve default config if not provided
    try:
        main_config = load_config(args.config)
    except FileNotFoundError:
        print_status(f"Main config not found: {args.config}", "ERROR")
        print_status(
            "Ensure f/fStart/default.json exists, or pass --config.",
            "ERROR",
        )
        return 2

    # Tag fan-out: thread_count > 1 with 2+ tags on one suite → orchestrator
    try:
        if getattr(sys, "frozen", False):
            _pu = os.path.abspath(os.path.join(sys._MEIPASS, "pyUtils"))  # type: ignore[attr-defined]
        else:
            _pu = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pyUtils"))
        if _pu not in sys.path:
            sys.path.insert(0, _pu)
        import fOrchestrate  # type: ignore

        orch_code = fOrchestrate.maybe_orchestrate_config(args.config)
        if orch_code is not None:
            return orch_code
    except Exception as orch_exc:
        print_status(f"Orchestrator skip/fallback: {orch_exc}", "WARNING")

    configs = main_config.get("configs", [])
    timeout = main_config.get("timeout", 6)
    debug_mode = bool(args.debug or main_config.get("debug", False))
    headless_mode = bool(main_config.get("headless", False))  # From fEngine2.py v2

    # Set headless mode environment variable if configured (from fEngine2.py v2)
    # Note: Even if headless is False, xActions will auto-detect cloud environments
    # and enable headless mode automatically for cloud execution
    if headless_mode:
        os.environ['FOXYIZ_HEADLESS'] = 'true'
        print_status("Headless mode enabled", "INFO")
    else:
        # Explicitly disable headless mode to ensure browsers open (for local execution)
        # Cloud environments will be auto-detected and headless mode enabled automatically
        os.environ['FOXYIZ_HEADLESS'] = 'false'
        print_status("Headless mode disabled - browsers will open (cloud auto-detection enabled)", "INFO")

    # propagate debug mode into action layer
    try:
        if hasattr(xActions, 'set_debug_mode'):
            xActions.set_debug_mode(debug_mode)
        if hasattr(xActions, 'set_capture_config'):
            xActions.set_capture_config(main_config.get("capture"))
            cap = xActions.get_capture_config()
            if cap.get("image") != "on_fail" or cap.get("video") != "off":
                print_status(
                    f"Capture policy — image: {cap.get('image')}, video: {cap.get('video')}",
                    "INFO",
                )
    except Exception:
        pass

    # Dynamically adjust thread count based on CPU cores, capped at 4
    max_threads = min(multiprocessing.cpu_count(), 4)
    thread_count = int(main_config.get("thread_count", max_threads))
    print_status(f"Using {thread_count} threads for parallel execution", "INFO")

    start_time = time.time()

    total_configs = len(configs)
    suite_args = [
        (i, total_configs, path, main_config, debug_mode, timeout, start_time)
        for i, path in enumerate(configs, 1)
    ]

    # Parallel across YPADs when thread_count > 1 and multiple configs; print in config order (buffered per suite).
    if total_configs > 1 and thread_count > 1:
        workers = min(thread_count, total_configs)
        heartbeat_interval = main_config.get("heartbeat_interval", 3)
        try:
            heartbeat_interval = float(heartbeat_interval)
        except (TypeError, ValueError):
            heartbeat_interval = 3.0
        if heartbeat_interval < 0.5:
            heartbeat_interval = 0.5
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures_by_index = {
                idx: executor.submit(run_ypad_suite_worker, suite_args[idx - 1])
                for idx in range(1, total_configs + 1)
            }
            for idx in range(1, total_configs + 1):
                config_path = suite_args[idx - 1][2]
                suite_name = os.path.splitext(os.path.basename(config_path))[0]
                _, captured = _wait_future_with_heartbeat(
                    futures_by_index[idx],
                    suite_name,
                    idx,
                    total_configs,
                    heartbeat_interval,
                )
                sys.stdout.write(_normalize_buffered_output(captured))
                sys.stdout.flush()
    else:
        for args in suite_args:
            _execute_single_ypad_suite(*args)

if __name__ == "__main__":
    # Multiprocessing support for Windows and PyInstaller
    # Freeze support must be called first for PyInstaller executables
    try:
        multiprocessing.freeze_support()
    except Exception:
        pass  # Not running as frozen executable, continue normally
    
    # Set start method to 'spawn' on Windows for better compatibility
    # This must be called before any multiprocessing operations
    try:
        if sys.platform == 'win32':
            multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        # Start method already set, ignore
        pass
    except Exception:
        # Other platforms or errors, continue
        pass
    
    # YPAD suites may run in parallel worker processes; output is replayed in config order.
    
    try:
        main()
    except KeyboardInterrupt:
        print_status("Execution interrupted by user.", "WARNING")
        try:
            # Attempt graceful cleanup of shared UI driver if present
            if hasattr(xActions, 'UIActionHandler') and getattr(xActions.UIActionHandler, '_shared_driver', None):
                try:
                    xActions.UIActionHandler._shared_driver.quit()
                except Exception:
                    pass
                xActions.UIActionHandler._shared_driver = None
            if hasattr(xActions, 'UIActionHandler') and getattr(xActions.UIActionHandler, '_chrome_user_data_dir', None):
                try:
                    shutil.rmtree(xActions.UIActionHandler._chrome_user_data_dir, ignore_errors=True)
                except Exception:
                    pass
                xActions.UIActionHandler._chrome_user_data_dir = None
        except Exception:
            pass
        sys.exit(130)