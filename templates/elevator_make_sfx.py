"""Synthesised hook SFX for why-elevators-dont-fall (deterministic, seeded). Punchy for the hook, never clicky:
every sound has a >= 3 ms attack ramp and is low-passed.
Run: python -I make_sfx.py
"""
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
OUT = Path(__file__).resolve().parent / "sfx"
OUT.mkdir(exist_ok=True)
R = np.random.default_rng(7)


def env(n, a, d):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
    return e


def lp(x, hz, order=4):
    return signal.sosfilt(signal.butter(order, hz, "low", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def save(name, x, peak_db=-3.0):
    x = x / max(1e-9, np.abs(x).max()) * 10 ** (peak_db / 20)
    fade = int(0.01 * SR)
    x[-fade:] *= np.linspace(1, 0, fade)
    sf.write(str(OUT / name), np.stack([x, x], 1).astype(np.float32), SR, subtype="PCM_24")
    print(name, f"{len(x) / SR:.2f}s")


# cable snap: crack (filtered noise) + twang (gliding inharmonic partials) + low body thump
n = int(1.4 * SR)
t = np.arange(n) / SR
crack = lp(R.standard_normal(n), 6000) * env(n, 0.003, 0.018)
f0 = 180 + 520 * np.exp(-t / 0.05)
ph = 2 * np.pi * np.cumsum(f0) / SR
twang = (np.sin(ph) + 0.5 * np.sin(2.76 * ph) + 0.3 * np.sin(5.4 * ph)) * env(n, 0.004, 0.35)
thump = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-t / 0.2) + 40) / SR) * env(n, 0.004, 0.12)
save("snap.wav", 0.9 * crack + 0.6 * lp(twang, 4000) + 0.8 * thump)

# wind rush while falling: band noise sweeping up over 1.3 s
n = int(1.5 * SR)
t = np.arange(n) / SR
noise = R.standard_normal(n)
lo = bp(noise, 200, 900)
hi = bp(noise, 900, 3500)
k = np.clip(t / 1.3, 0, 1)
rush = (lo * (0.6 + 0.4 * k) + hi * k ** 2) * np.minimum(1, t / 0.15) * np.where(t > 1.32, np.exp(-(t - 1.32) / 0.03), 1)
save("rush.wav", lp(rush, 5000), -6)

# safety-gear bite: metallic clunk + short warm screech (resonant noise, low-passed, decays fast)
n = int(1.2 * SR)
t = np.arange(n) / SR
clunk = np.sin(2 * np.pi * 95 * t) * env(n, 0.003, 0.09) + 0.4 * lp(R.standard_normal(n), 2500) * env(n, 0.003, 0.03)
sc = R.standard_normal(n)
screech = sum(bp(sc, f * 0.97, f * 1.03) * a for f, a in ((1650, 1.0), (2380, 0.7), (3120, 0.4)))
screech *= np.minimum(1, t / 0.01) * np.exp(-t / 0.28) * (1 + 0.3 * np.sin(2 * np.pi * 23 * t))
save("bite.wav", clunk + 0.9 * lp(screech, 5000))

# rewind: reversed swell
n = int(0.7 * SR)
t = np.arange(n) / SR
sw = bp(R.standard_normal(n), 300, 2500) * (t / t[-1]) ** 2
save("rewind.wav", lp(sw[::1], 4500) * np.minimum(1, (t[-1] - t) / 0.02), -8)

# power down: soft thunk + falling hum
n = int(1.3 * SR)
t = np.arange(n) / SR
hum = np.sin(2 * np.pi * np.cumsum(120 * np.exp(-t / 0.5) + 30) / SR) * env(n, 0.01, 0.5)
th = np.sin(2 * np.pi * 60 * t) * env(n, 0.004, 0.1)
save("powerdown.wav", 0.7 * hum + th, -5)
