"""narrate.py - calm explainer narration with Kokoro (local, Apache-2.0), one take per script line.

Usage (py-media python):
  python -X utf8 narrate.py <film>/script.txt <film>/audio/vo.wav
      [--voice am_michael] [--speed 0.94] [--gap 0.32] [--term-gap 0.55] [--lead 0.35]

script.txt: one narration line per text line. Lines starting with # are ignored.
  A line ending in  "|| 0.8"  forces the pause AFTER it (seconds).
  Lines that start with "That's the" / "Those are the" get --term-gap after them (room for the ding + flash).
Writes vo.wav (48 kHz mono, peak -3 dBFS) and vo_lines.json [{i, text, s, e}].
Then get exact word times (writes audio/vo.scan/ears.json + ears.md):
  python -X utf8 transcribe.py vo.wav --vocab "Term1,Term2"
"""
import argparse
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bx_config import cfg  # noqa: E402

MODELS = cfg("kokoro_models")  # folder with kokoro-v1.0.onnx + voices-v1.0.bin (config.json)


def trim(a, sr, thr=0.008):
    idx = np.where(np.abs(a) > thr)[0]
    if not len(idx):
        return a
    s = max(0, idx[0] - int(0.02 * sr))
    e = min(len(a), idx[-1] + int(0.06 * sr))
    return a[s:e]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("out")
    ap.add_argument("--voice", default="am_michael")
    ap.add_argument("--speed", type=float, default=0.94)
    ap.add_argument("--gap", type=float, default=0.32)
    ap.add_argument("--term-gap", type=float, default=0.55)
    ap.add_argument("--lead", type=float, default=0.35, help="silence before the first word")
    ap.add_argument("--only", type=str, default="", help="comma list of line numbers to print only (debug)")
    a = ap.parse_args()

    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    lines = []
    for raw in open(a.script, encoding="utf8").read().splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        pause = None
        if "||" in raw:
            raw, p = raw.split("||", 1)
            raw, pause = raw.strip(), float(p)
        lines.append((raw, pause))

    SR = 48000
    out = [np.zeros(int(a.lead * SR))]
    t = a.lead
    meta = []
    for i, (text, pause) in enumerate(lines):
        audio, sr = k.create(text, voice=a.voice, speed=a.speed, lang="en-us")
        audio = trim(np.asarray(audio, dtype=np.float64), sr)
        if sr != SR:
            audio = signal.resample_poly(audio, SR, sr)
        meta.append({"i": i + 1, "text": text, "s": round(t, 3), "e": round(t + len(audio) / SR, 3)})
        out.append(audio)
        t += len(audio) / SR
        if pause is None:
            pause = a.term_gap if re.match(r"(that's|those are|this is) the", text, re.I) else a.gap
        out.append(np.zeros(int(pause * SR)))
        t += pause
        print(f"{i + 1:2d} {meta[-1]['s']:7.2f}-{meta[-1]['e']:7.2f}  {text}")
    y = np.concatenate(out)
    y = y / max(1e-9, np.abs(y).max()) * 10 ** (-3 / 20)
    sf.write(a.out, y.astype(np.float32), SR, subtype="PCM_24")
    json.dump(meta, open(os.path.splitext(a.out)[0] + "_lines.json", "w", encoding="utf8"), indent=1)
    print(f"wrote {a.out}  {len(y) / SR:.2f} s")


if __name__ == "__main__":
    main()
