"""Build an animated GIF and/or film-strip PNG from site_shots (or any z/ run) PNGs.

Examples (from KK/):

  python FoXYiZ/pyUtils/site_shot_roll.py --run z/20260722_103452_site_shots
  python FoXYiZ/pyUtils/site_shot_roll.py --latest site_shots --gif --filmstrip
  python FoXYiZ/pyUtils/site_shot_roll.py --run z/... --delay-ms 900 --height 360
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from _paths import FOXYIZ_ROOT  # type: ignore[import-not-found]

Z_ROOT = FOXYIZ_ROOT / "z"

# Prefer plan order from author defaults when filenames match these slugs.
_SLUG_ORDER = [
    "home",
    "ideas",
    "dashboard",
    "integrate",
    "docs",
    "login",
    "register",
    "forgot_password",
    "reset_password",
    "embed",
    "view_private",
    "unknown_404",
]


def _slug_from_name(name: str) -> str:
    # e.g. PShot_Home_D1_4_home_103459.png → home
    m = re.search(r"_D\d+_\d+_([a-z0-9_]+)_\d+\.png$", name, re.I)
    if m:
        return m.group(1).lower()
    stem = Path(name).stem.lower()
    for s in _SLUG_ORDER:
        if s in stem:
            return s
    return stem


def _sort_key(path: Path) -> tuple:
    slug = _slug_from_name(path.name)
    try:
        idx = _SLUG_ORDER.index(slug)
    except ValueError:
        idx = 999
    return (idx, path.name.lower())


def find_latest_run(suite: str) -> Path:
    matches = sorted(
        Z_ROOT.glob(f"*_{suite}"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        raise FileNotFoundError(f"No z/*_{suite} run folders under {Z_ROOT}")
    return matches[0]


def collect_pngs(run_dir: Path) -> list[Path]:
    pngs = [p for p in run_dir.rglob("*.png") if p.is_file()]
    # Skip prior roll outputs if re-run inside same folder
    pngs = [p for p in pngs if "filmstrip" not in p.stem.lower() and "roll" not in p.stem.lower()]
    pngs.sort(key=_sort_key)
    if not pngs:
        raise FileNotFoundError(f"No PNGs under {run_dir}")
    return pngs


def _fit_height(im: Image.Image, height: int) -> Image.Image:
    if im.height == height:
        return im.convert("RGB")
    w = max(1, int(im.width * (height / im.height)))
    return im.convert("RGB").resize((w, height), Image.Resampling.LANCZOS)


def build_gif(pngs: list[Path], out: Path, *, height: int, delay_ms: int) -> Path:
    frames: list[Image.Image] = []
    # Uniform canvas = max width among fitted frames (pad with dark bars)
    fitted = [_fit_height(Image.open(p), height) for p in pngs]
    max_w = max(f.width for f in fitted)
    for f in fitted:
        canvas = Image.new("RGB", (max_w, height), (18, 18, 22))
        x = (max_w - f.width) // 2
        canvas.paste(f, (x, 0))
        frames.append(canvas)
    out.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=delay_ms,
        loop=0,
        optimize=False,
    )
    return out


def build_filmstrip(
    pngs: list[Path],
    out: Path,
    *,
    height: int,
    gap: int = 10,
    label: bool = True,
) -> Path:
    """Horizontal film roll: sprocket rails + framed cells + optional slug labels."""
    cell_h = height
    fitted = [_fit_height(Image.open(p), cell_h) for p in pngs]
    labels = [_slug_from_name(p.name) for p in pngs]
    rail = 18
    label_h = 22 if label else 0
    frame_pad = 4
    cell_outer_h = rail + frame_pad + cell_h + frame_pad + label_h + rail
    widths = [f.width + 2 * frame_pad for f in fitted]
    total_w = gap + sum(w + gap for w in widths)

    bg = (12, 12, 14)
    rail_c = (28, 28, 32)
    hole_c = (8, 8, 10)
    frame_c = (40, 40, 48)
    strip = Image.new("RGB", (total_w, cell_outer_h), bg)
    draw = ImageDraw.Draw(strip)
    draw.rectangle([0, 0, total_w, rail], fill=rail_c)
    draw.rectangle([0, cell_outer_h - rail, total_w, cell_outer_h], fill=rail_c)

    # Sprocket holes
    hole_w, hole_h, hole_gap = 10, 8, 22
    for y0 in (4, cell_outer_h - rail + 5):
        x = 8
        while x + hole_w < total_w:
            draw.rounded_rectangle([x, y0, x + hole_w, y0 + hole_h], radius=2, fill=hole_c)
            x += hole_gap

    try:
        font = ImageFont.truetype("segoeui.ttf", 12)
    except OSError:
        font = ImageFont.load_default()

    x = gap
    y_img = rail + frame_pad
    for im, w_outer, slug in zip(fitted, widths, labels):
        draw.rectangle(
            [x, y_img - frame_pad, x + w_outer, y_img + cell_h + frame_pad],
            fill=frame_c,
        )
        strip.paste(im, (x + frame_pad, y_img))
        if label:
            ty = y_img + cell_h + frame_pad + 4
            draw.text((x + frame_pad, ty), slug.replace("_", " "), fill=(200, 200, 210), font=font)
        x += w_outer + gap

    out.parent.mkdir(parents=True, exist_ok=True)
    strip.save(out, format="PNG")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="PNG sequence → GIF / filmstrip")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--run", type=str, help="Path to z/<ts>_suite run folder (abs or under FoXYiZ)")
    g.add_argument("--latest", type=str, metavar="SUITE", help="Use newest z/*_<suite> folder")
    ap.add_argument("--gif", action="store_true", default=False, help="Write animated GIF")
    ap.add_argument("--filmstrip", action="store_true", default=False, help="Write film-roll PNG")
    ap.add_argument("--height", type=int, default=360, help="Frame height in px (default 360)")
    ap.add_argument("--delay-ms", type=int, default=800, help="GIF frame delay ms (default 800)")
    ap.add_argument("--out-dir", type=str, default="", help="Output folder (default: run folder)")
    args = ap.parse_args()

    if not args.gif and not args.filmstrip:
        args.gif = True
        args.filmstrip = True

    if args.latest:
        run_dir = find_latest_run(args.latest.strip())
    else:
        run = Path(args.run)
        run_dir = run if run.is_absolute() else (FOXYIZ_ROOT / run)
        if not run_dir.is_dir():
            raise SystemExit(f"Run folder not found: {run_dir}")

    out_dir = Path(args.out_dir) if args.out_dir else run_dir
    if not out_dir.is_absolute():
        out_dir = FOXYIZ_ROOT / out_dir

    pngs = collect_pngs(run_dir)
    print(f"Run   {run_dir}")
    print(f"Frames {len(pngs)}")
    for p in pngs:
        print(f"  - {_slug_from_name(p.name)}: {p.name}")

    if args.gif:
        gif_path = out_dir / f"{run_dir.name}_roll.gif"
        build_gif(pngs, gif_path, height=args.height, delay_ms=args.delay_ms)
        print(f"GIF   {gif_path}  ({gif_path.stat().st_size // 1024} KB)")

    if args.filmstrip:
        strip_path = out_dir / f"{run_dir.name}_filmstrip.png"
        build_filmstrip(pngs, strip_path, height=min(args.height, 240))
        print(f"Film  {strip_path}  ({strip_path.stat().st_size // 1024} KB)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
