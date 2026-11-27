"""make_mix.py - voice-first explainer mix: narration + music bed ducked ~14 dB under the voice + soft SFX.

  python -I make_mix.py <film_dir>

Reads <film>/spec.py: DUR, LINES (speech regions), MUSIC {file, src_start, under_voice_db, gap_lift_db, fade_in,
fade_out, loop (True = the bed's first second continues its last one, for Shorts that loop)}, SFX [(file in audio/sfx, t, gain_db)] (the loudest moment of each SFX lands on t).
Writes audio/mix.wav (48 kHz stereo 24-bit, exactly DUR s) at -14 LUFS integrated, true peak <= -1.5 dBTP, and
audio/cues.json for earshot timeline. One pass, one limiter (owner rule: no double limiting).
"""
import importlib.util
import json
import re
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bx_config import cfg  # noqa: E402

FFMPEG = cfg("ffmpeg")
SR = 48000
TARGET, CEIL = -14.0, -1.5


def load(p):
    x, sr = sf.read(str(p), always_2d=True)
    if sr != SR:
        x = signal.resample_poly(x, SR, sr, axis=0)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, 1)
    return x[:, :2].astype(np.float64)


def db(g):
    return 10 ** (g / 20)


def lufs(path):
    p = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(path), "-af",
                        f"loudnorm=I={TARGET}:TP={CEIL}:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    j = json.loads(re.findall(r"\{[^{}]+\}", p.stderr)[-1])
    return float(j["input_i"]), float(j["input_tp"])


def movavg(x, k):
    """Centred moving average via cumsum (np.convolve with a long kernel takes minutes on 5M samples)."""
    c = np.cumsum(np.pad(x, (k // 2 + 1, k - k // 2)))
    return (c[k:k + len(x)] - c[:len(x)]) / k


def lufs_arr(x, tmp):
    sf.write(str(tmp), x.astype(np.float32), SR, subtype="FLOAT")
    return lufs(tmp)


def limiter(x, ceiling_db, look=0.003, release=0.08):
    ceil = db(ceiling_db)
    up = signal.resample_poly(x, 4, 1, axis=0)
    pk = np.abs(up).max(1).reshape(-1, 4).max(1)[: len(x)]
    pk = np.pad(pk, (0, len(x) - len(pk)))
    raw = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    la = int(look * SR)
    need = np.lib.stride_tricks.sliding_window_view(np.pad(raw, (0, la), constant_values=1.0), la + 1).min(1)
    g = np.empty_like(need)
    a = np.exp(-1 / (release * SR))
    cur = 1.0
    for i, nd in enumerate(need):
        cur = nd if nd < cur else nd + (cur - nd) * a
        g[i] = cur
    return x * np.minimum(g, raw)[:, None]


def main():
    film = Path(sys.argv[1])
    sp = importlib.util.spec_from_file_location("spec", str(film / "spec.py"))
    spec = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(spec)
    n = int(round(spec.DUR * SR))
    tmp = film / "audio" / "_tmp.wav"

    vo = load(film / "audio" / "vo.wav")[:n]
    vo = np.pad(vo, ((0, n - len(vo)), (0, 0)))
    v_l, _ = lufs_arr(vo, tmp)

    M = spec.MUSIC
    mu = load(film / M["file"])
    s0 = int(M.get("src_start", 0) * SR)
    xf = int(1.0 * SR)
    tail = mu[s0 + n: s0 + n + xf]
    mu = mu[s0:s0 + n]
    mu = np.pad(mu, ((0, n - len(mu)), (0, 0)))
    if M.get("loop") and len(tail) == xf:
        # seamless loop: the first second becomes the continuation of the last one (equal-power crossfade)
        r = np.linspace(0, 1, xf)[:, None]
        mu[:xf] = mu[:xf] * np.sin(r * np.pi / 2) + tail * np.cos(r * np.pi / 2)
    m_l, _ = lufs_arr(mu, tmp)
    if M.get("start_at"):                                   # bed enters after a cold-open hook
        st = int(M["start_at"] * SR)
        mu = np.concatenate([np.zeros((st, 2)), mu[:n - st]])
    mu *= db(v_l + M["under_voice_db"] - m_l)          # bed sits under_voice_db below the voice
    # lift the bed a little in pauses longer than 0.6 s, with 0.25 s ramps
    t = np.arange(n) / SR
    speech = np.zeros(n, bool)
    for ln in spec.LINES:
        speech[int(ln["s"] * SR): int(ln["e"] * SR)] = True
    lift = np.where(speech, 0.0, 1.0)
    k = int(0.6 * SR)
    run = movavg(lift, k)
    lift = np.clip((run - 0.5) * 2, 0, 1)
    sm = int(0.25 * SR)
    lift = movavg(lift, sm)
    mu *= db(M["gap_lift_db"] * lift)[:, None]
    if not M.get("loop"):
        fi, fo = int(M["fade_in"] * SR), int(M["fade_out"] * SR)
        st = int(M.get("start_at", 0) * SR)
        mu[st:st + fi] *= np.linspace(0, 1, fi)[:, None]
        mu[-fo:] *= np.linspace(1, 0, fo)[:, None]

    fx = np.zeros((n, 2))
    cues = []
    for fname, tt, gain in spec.SFX:
        x = load(film / "audio" / "sfx" / fname) * db(gain)
        env = np.sqrt(np.maximum(movavg((x ** 2).mean(1), 240), 0))
        st = int(round(tt * SR)) - int(env.argmax())
        a, b = max(0, st), min(n, st + len(x))
        fx[a:b] += x[a - st: b - st]
        cues.append({"t": round(tt, 3), "kind": fname})

    mix = vo + mu + fx
    out = mix
    for _ in range(4):
        L, tp = lufs_arr(out, tmp)
        if abs(L - TARGET) < 0.15 and tp <= CEIL:
            break
        mix = mix * db(TARGET - L)
        out = limiter(mix, CEIL - 0.4)
    tmp.unlink(missing_ok=True)
    sf.write(str(film / "audio" / "mix.wav"), out.astype(np.float32), SR, subtype="PCM_24")
    L, tp = lufs(film / "audio" / "mix.wav")
    (film / "audio" / "cues.json").write_text(json.dumps({"fps": spec.FPS, "events": cues}, indent=1))
    print(f"mix.wav {n / SR:.2f} s  {L:.2f} LUFS  TP {tp:.2f} dBTP  (voice {v_l:.1f}, bed {M['under_voice_db']} dB under)")


if __name__ == "__main__":
    main()
