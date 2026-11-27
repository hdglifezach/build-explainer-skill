"""qa_sheet.py - contact sheets for QA.

  python qa_sheet.py snaps "<film>/snaps/s_*.jpg" <out_prefix> [--cols 4] [--w 360]
      tile snapshot JPGs (label = file name)
  python qa_sheet.py video <film>/<film>_v1.mp4 <out_prefix> [--fps 2] [--cols 6] [--rows 5] [--w 220]
      the WHOLE video at 2 fps (owner rule: QA every second of the render before delivery), timestamp on each tile

Writes <out_prefix>_01.jpg, _02.jpg ... and prints their paths. Run with python.
"""
import argparse
import glob
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\consolab.ttf"


def tile(items, out_prefix, cols, rows, w):
    font = ImageFont.truetype(FONT, max(12, w // 14))
    per = cols * rows
    outs = []
    for s in range(0, len(items), per):
        chunk = items[s:s + per]
        im0 = Image.open(chunk[0][0])
        h = int(w * im0.height / im0.width)
        r = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * w, r * (h + 4)), (20, 20, 22))
        d = ImageDraw.Draw(sheet)
        for i, (p, label) in enumerate(chunk):
            im = Image.open(p).convert("RGB").resize((w, h), Image.LANCZOS)
            x, y = (i % cols) * w, (i // cols) * (h + 4)
            sheet.paste(im, (x, y))
            d.rectangle((x, y, x + len(label) * w // 22 + 8, y + w // 12), fill=(0, 0, 0))
            d.text((x + 4, y + 2), label, font=font, fill=(255, 230, 80))
        o = f"{out_prefix}_{s // per + 1:02d}.jpg"
        sheet.save(o, quality=88)
        outs.append(o)
        print(o)
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["snaps", "video"])
    ap.add_argument("src")
    ap.add_argument("out_prefix")
    ap.add_argument("--fps", type=float, default=2.0)
    ap.add_argument("--cols", type=int, default=None)
    ap.add_argument("--rows", type=int, default=None)
    ap.add_argument("--w", type=int, default=None)
    a = ap.parse_args()
    if a.mode == "snaps":
        files = sorted(glob.glob(a.src))
        items = [(f, Path(f).stem) for f in files]
        tile(items, a.out_prefix, a.cols or 4, a.rows or 3, a.w or 360)
    else:
        tmp = Path(tempfile.mkdtemp(prefix="qa_"))
        subprocess.run(["ffmpeg", "-v", "error", "-i", a.src, "-vf", f"fps={a.fps},scale=320:-2",
                        str(tmp / "q_%05d.jpg")], check=True)
        files = sorted(tmp.glob("q_*.jpg"))
        items = []
        for i, f in enumerate(files):
            t = (i + 0.5) / a.fps
            items.append((str(f), f"{int(t // 60)}:{t % 60:04.1f}"))
        tile(items, a.out_prefix, a.cols or 6, a.rows or 5, a.w or 220)


if __name__ == "__main__":
    main()
