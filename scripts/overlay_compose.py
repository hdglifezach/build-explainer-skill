"""overlay_compose.py - draw the explainer overlays on rendered frames and encode the film.

The film folder must have spec.py (TITLE, TAGS, COUNTERS, CARDS, TERMS, WORDS, LINES, DUR, NF, FPS),
frames/f_####.jpg + anchors/f_####.json (from build.py render), audio/mix.wav.

  python overlay_compose.py <film_dir> encode <out.mp4>        full film: frames + overlays + mix -> NVENC H.264
  python overlay_compose.py <film_dir> stills <tag>            overlays on snaps/<tag>_####.jpg -> snaps/<tag>_####_ov.jpg

Overlay language (the channel format, own look):
  title      top, first 3 s, last word yellow
  captions   bold uppercase, middle third, 1-3 words; the word being spoken is yellow; key terms yellow + underlined
  tags       small dark label + leader line + dot on a 3D anchor; terms are yellow
  counters   big yellow number (counts up) + small caption above + unit below
  cards      monospace caption card ("1271", "A FEW HOURS LATER")
Run with python.
"""
import importlib.util
import json
import math
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
YEL = (255, 204, 31)
WHITE = (255, 255, 255)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bx_config import cfg, load_font  # noqa: E402

BAHN = cfg("font_bold")   # Bahnschrift if present, else the downloaded OFL font (config.json)
MONO = cfg("font_mono")
FFMPEG = cfg("ffmpeg")
ENCODER = cfg("encoder")


def font(size, weight="Bold"):
    return load_font(BAHN, size, weight)


F_CAP = font(84)
F_TITLE = font(118)
F_TAG = font(38, "SemiBold")
F_NUM = font(170)
F_UNIT = font(40, "SemiBold")
F_SMALL = load_font(MONO, 34)
F_CARD = load_font(MONO, 44)


def load_spec(film):
    sp = importlib.util.spec_from_file_location("spec", str(Path(film) / "spec.py"))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def env(t, t0, t1, fin=0.18, fout=0.2):
    if t < t0 or t > t1:
        return 0.0
    return clamp((t - t0) / fin) * clamp((t1 - t) / fout)


# ------------------------------------------------------------------ captions
def build_chunks(spec):
    words = []
    for w in getattr(spec, "CAPTION_WORDS", spec.WORDS):      # Whisper splits "anti -rollback": glue it back
        if words and w["w"].startswith("-"):
            words[-1] = dict(words[-1], w=words[-1]["w"] + w["w"], e=w["e"])
        else:
            words.append(dict(w))
    starts = [ln["s"] for ln in spec.LINES]

    def line_of(w):
        mid = (w["s"] + w["e"]) / 2
        return max([i for i, s0 in enumerate(starts) if s0 - 0.12 <= mid] or [0])
    chunks, cur = [], []
    for i, w in enumerate(words):
        w["txt"] = re.sub(r"[^\w'\u2019%-]", "", w["w"]).upper()
        if not w["txt"]:
            continue
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        chars = sum(len(x["txt"]) + 1 for x in cur)
        brk = (nxt is None or len(cur) >= 3 or chars > 13 or re.search(r"[.,?!;:]$", w["w"])
               or line_of(w) != line_of(nxt)
               or nxt["s"] - w["e"] > 0.28)
        if nxt is not None and len(cur) < 3 and chars + len(nxt["w"]) > 15:
            brk = True
        if brk:
            chunks.append(cur)
            cur = []
    out = []
    for k, c in enumerate(chunks):
        t0 = c[0]["s"] - 0.04
        t1 = chunks[k + 1][0]["s"] - 0.04 if k + 1 < len(chunks) else c[-1]["e"] + 0.5
        t1 = min(t1, c[-1]["e"] + 0.45)
        out.append((t0, t1, c))
    return out


def term_words(spec):
    """(start, end, set-of-words) spans where a key term is underlined."""
    spans = []
    for term, tt in spec.TERMS.items():
        n = len(term.split())
        spans.append((tt - 0.05, tt + 0.45 * n + 0.6, set(term.upper().split())))
    return spans


def draw_caption(d, t, chunks, spans):
    for t0, t1, c in chunks:
        if not (t0 <= t < t1):
            continue
        pieces = []
        for w in c:
            is_term = any(a <= w["s"] <= b and w["txt"] in ws for a, b, ws in spans)
            col = YEL if (is_term or w["s"] - 0.04 <= t < w["e"] + 0.08) else WHITE
            pieces.append((w["txt"], col, is_term))
        widths = [d.textlength(p[0], font=F_CAP) for p in pieces]
        sp = d.textlength(" ", font=F_CAP)
        total = sum(widths) + sp * (len(pieces) - 1)
        scale = min(1.0, (W - 120) / max(1, total))
        f = F_CAP if scale >= 1 else font(int(84 * scale))
        if scale < 1:
            widths = [d.textlength(p[0], font=f) for p in pieces]
            sp = d.textlength(" ", font=f)
            total = sum(widths) + sp * (len(pieces) - 1)
        pop = 1.0
        x = (W - total) / 2
        y = int(H * 0.60)
        for (txt, col, term), wd in zip(pieces, widths):
            d.text((x + 4, y + 5), txt, font=f, fill=(0, 0, 0, 110))
            d.text((x, y), txt, font=f, fill=col + (255,), stroke_width=5, stroke_fill=(20, 18, 16, 235))
            if term:
                uy = y + int(f.size * 1.02)
                d.rectangle((x, uy, x + wd, uy + 7), fill=(20, 18, 16, 235))
                d.rectangle((x + 2, uy + 1, x + wd - 2, uy + 5), fill=YEL + (255,))
            x += wd + sp
        _ = pop


# ------------------------------------------------------------------ elements
def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def draw_hooks(img, t, spec):
    """Hook text: huge, centred, slammed in (scale 1.35 -> 1.0 in 0.12 s) - the cold open's 2-4 word claim."""
    for text, t0, t1, y, col in getattr(spec, "HOOKS", []):
        if not (t0 <= t <= t1):
            continue
        k = clamp((t - t0) / 0.12)
        sc = 1.35 - 0.35 * (1 - (1 - k) ** 3)
        a = clamp((t1 - t) / 0.15)
        L = layer()
        d = ImageDraw.Draw(L)
        lines = text.split("\n")                       # "\n" = two-line hook, lines stacked around y
        size = 150 if len(lines) == 1 else 160
        f = font(size)
        while max(d.textlength(ln, font=f) for ln in lines) > (W - 80) / sc and size > 40:
            size -= 6
            f = font(size)
        f = font(int(size * sc))
        colour = YEL if col == "y" else WHITE
        for i, ln in enumerate(lines):
            w = d.textlength(ln, font=f)
            x = (W - w) / 2
            yy = y + (i - (len(lines) - 1) / 2) * f.size * 0.95 - f.size / 2
            d.text((x + 6, yy + 8), ln, font=f, fill=(0, 0, 0, 150))
            d.text((x, yy), ln, font=f, fill=colour + (255,), stroke_width=9, stroke_fill=(15, 14, 12, 245))
        img.alpha_composite(fade(L, a))


def draw_title(img, t, spec):
    if getattr(spec, "TITLE", None) is None:
        return
    a = env(t, -1.0, 3.0, 0.01, 0.35)                    # fully on at frame 0 (thumbnail + loop seam)
    if getattr(spec, "LOOP_TITLE", True):                 # fade back in over the last 0.4 s so the loop is seamless
        a = max(a, clamp((t - (spec.DUR - 0.45)) / 0.35))
    if a <= 0:
        return
    L = layer()
    d = ImageDraw.Draw(L)
    first, last = spec.TITLE
    ft = F_TITLE
    w1 = d.textlength(first + " ", font=ft)
    w2 = d.textlength(last, font=ft)
    if w1 + w2 > W - 90:                      # long titles shrink to fit
        ft = font(int(118 * (W - 90) / (w1 + w2)))
        w1 = d.textlength(first + " ", font=ft)
        w2 = d.textlength(last, font=ft)
    x = (W - w1 - w2) / 2
    y = 230
    d.rectangle(((W - 90) / 2, y - 34, (W + 90) / 2, y - 26), fill=YEL + (255,))
    for txt, col, xx in ((first, WHITE, x), (last, YEL, x + w1)):
        d.text((xx + 5, y + 6), txt, font=ft, fill=(0, 0, 0, 120))
        d.text((xx, y), txt, font=ft, fill=col + (255,), stroke_width=6, stroke_fill=(20, 18, 16, 240))
    img.alpha_composite(fade(L, a))


def fade(L, a):
    if a >= 0.999:
        return L
    r, g, b, al = L.split()
    al = al.point(lambda v: int(v * a))
    return Image.merge("RGBA", (r, g, b, al))


def draw_tag(img, t, tag, anchors):
    text, name, t0, t1, dx, dy, term = tag
    a = env(t, t0, t1)
    if a <= 0 or name not in anchors:
        return
    ax, ay, vis = anchors[name]
    if not vis or not (-200 < ax < W + 200 and -200 < ay < H + 200):
        return
    L = layer()
    d = ImageDraw.Draw(L)
    tw = d.textlength(text, font=F_TAG) + 6 * len(text) * 0.0
    bw, bh = tw + 40, 62
    k = 0.85 + 0.15 * clamp((t - t0) / 0.2)
    bx = clamp(ax + dx - bw / 2, 30, W - 30 - bw)
    by = clamp(ay + dy - bh / 2, 120, H - 260)
    col = YEL if term else WHITE
    # leader line from the box edge to the anchor
    lx = clamp(ax, bx + 10, bx + bw - 10)
    ly = by + bh if ay > by + bh else by
    d.line((lx, ly, ax, ay), fill=(20, 18, 16, 200), width=5)
    d.line((lx, ly, ax, ay), fill=col + (255,), width=2)
    d.ellipse((ax - 9, ay - 9, ax + 9, ay + 9), fill=(20, 18, 16, 220))
    d.ellipse((ax - 5, ay - 5, ax + 5, ay + 5), fill=col + (255,))
    d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=6, fill=(24, 24, 26, 225),
                        outline=col + (255,) if term else (90, 90, 90, 255), width=2)
    d.text((bx + 20, by + 10), text, font=F_TAG, fill=col + (255,))
    _ = k
    img.alpha_composite(fade(L, a))


def draw_counter(img, t, c):
    val, unit, cap, t0, t1, x, y = c
    a = env(t, t0, t1, 0.15, 0.25)
    if a <= 0:
        return
    L = layer()
    d = ImageDraw.Draw(L)
    m = re.search(r"\d[\d,]*", val)
    shown = val
    if m:
        n = int(m.group().replace(",", ""))
        k = clamp((t - t0) / 0.6)
        k = 1 - (1 - k) ** 3
        cur = int(round(n * k))
        s = f"{cur:,}" if "," in m.group() or n >= 10000 else str(cur)
        shown = val[:m.start()] + s + val[m.end():]
    nw = d.textlength(val, font=F_NUM)
    d.text((x - nw / 2 + 5, y - 95 + 7), shown, font=F_NUM, fill=(0, 0, 0, 110))
    d.text((x - nw / 2, y - 95), shown, font=F_NUM, fill=YEL + (255,), stroke_width=5, stroke_fill=(20, 18, 16, 230))
    cw = d.textlength(" ".join(cap), font=F_SMALL)
    d.text((x - cw / 2, y - 140), " ".join(cap), font=F_SMALL, fill=WHITE + (255,), stroke_width=3,
           stroke_fill=(20, 18, 16, 220))
    uw = d.textlength(unit, font=F_UNIT)
    d.line((x - max(uw, nw) / 2, y + 100, x + max(uw, nw) / 2, y + 100), fill=(255, 255, 255, 200), width=2)
    d.text((x - uw / 2, y + 108), unit, font=F_UNIT, fill=WHITE + (255,), stroke_width=3, stroke_fill=(20, 18, 16, 220))
    img.alpha_composite(fade(L, a))


def draw_card(img, t, c):
    lines, t0, t1, y = c
    a = env(t, t0, t1)
    if a <= 0:
        return
    L = layer()
    d = ImageDraw.Draw(L)
    spaced = [" ".join(s) if len(s) < 14 else s for s in lines]
    ws = [d.textlength(s, font=F_CARD) for s in spaced]
    bw, bh = max(ws) + 70, 62 * len(lines) + 34
    bx, by = (W - bw) / 2, y - bh / 2
    d.rectangle((bx, by, bx + bw, by + bh), fill=(22, 22, 24, 215), outline=(255, 255, 255, 70), width=2)
    for i, (s, w) in enumerate(zip(spaced, ws)):
        col = YEL if i == 0 and len(lines) == 1 else (WHITE if i == 0 else (205, 205, 205))
        # typewriter reveal
        n = int(len(s) * clamp((t - t0) / 0.5))
        d.text(((W - w) / 2, by + 20 + 62 * i), s[:n], font=F_CARD, fill=col + (255,))
    img.alpha_composite(fade(L, a))


def overlay(img, t, spec, anchors, chunks, spans):
    img = img.convert("RGBA")
    for tag in spec.TAGS:
        draw_tag(img, t, tag, anchors)
    for c in spec.COUNTERS:
        draw_counter(img, t, c)
    for c in spec.CARDS:
        draw_card(img, t, c)
    draw_title(img, t, spec)
    draw_hooks(img, t, spec)
    L = layer()
    if not any(a <= t < b for a, b in getattr(spec, "NO_CAPTIONS", [])):
        draw_caption(ImageDraw.Draw(L), t, chunks, spans)
    img.alpha_composite(L)
    return img.convert("RGB")


def main():
    film = Path(sys.argv[1])
    mode = sys.argv[2]
    spec = load_spec(film)
    chunks = build_chunks(spec)
    spans = term_words(spec)
    if mode == "stills":
        tag = sys.argv[3]
        for p in sorted((film / "snaps").glob(f"{tag}_[0-9][0-9][0-9][0-9].jpg")):
            f = int(p.stem.split("_")[-1])
            an = film / "anchors" / f"f_{f:04d}.json"
            anchors = json.loads(an.read_text()) if an.exists() else {}
            im = Image.open(p).convert("RGB")
            if im.size != (W, H):
                im = im.resize((W, H))
            overlay(im, f / spec.FPS, spec, anchors, chunks, spans).save(p.with_name(p.stem + "_ov.jpg"), quality=90)
            print("ov", p.name)
        return
    out = Path(sys.argv[3])
    if ENCODER == "h264_nvenc":
        venc = ["-c:v", "h264_nvenc", "-preset", "p7", "-rc", "vbr", "-cq", "19", "-b:v", "0"]
    else:
        venc = ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]
    cmd = [FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(spec.FPS),
           "-i", "-", "-i", str(film / "audio" / "mix.wav"), "-map", "0:v", "-map", "1:a",
           *venc, "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(out)]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    last = None
    for f in range(spec.NF):
        p = film / "frames" / f"f_{f:04d}.jpg"
        if p.exists():
            last = Image.open(p).convert("RGB")
        elif last is None:
            raise SystemExit(f"missing {p}")
        an = film / "anchors" / f"f_{f:04d}.json"
        anchors = json.loads(an.read_text()) if an.exists() else {}
        im = overlay(last, f / spec.FPS, spec, anchors, chunks, spans)
        pr.stdin.write(im.tobytes())
        if f % 300 == 0:
            print("compose", f, "/", spec.NF, flush=True)
    pr.stdin.close()
    pr.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
