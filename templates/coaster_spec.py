"""build-a-roller-coaster: shared timing + overlay spec (imported by build.py inside Blender AND by compose.py / make_mix.py).

All times are seconds on the final timeline (= vo.wav time). S(i)/E(i) = start/end of narration line i
(audio/vo_lines.json, 1-based, written by narrate.py). W(word, after) = start of the first spoken occurrence of
`word` after time `after` (audio/vo.scan/ears.json word timestamps).
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
FPS = 60
LINES = json.loads((BASE / "audio" / "vo_lines.json").read_text(encoding="utf8"))
_EARS = json.loads((BASE / "audio" / "vo.scan" / "ears.json").read_text(encoding="utf8"))
WORDS = [w for s in _EARS["segments"] for w in s["words"]]


def _norm(w):
    return "".join(ch for ch in w.lower() if ch.isalnum())
# caption fixes where Whisper heard a homophone: (after time, heard, correct)
for _after, _bad, _good in ((LINES[22]["s"] - 0.5, "kenai", "Coney"),):
    for _w in WORDS:
        if _w["s"] >= _after and _w["w"].strip(" .,").lower() == _bad and _w["s"] < _after + 3:
            _w["w"] = _good


_SAYS = {"eighteen ninety-five": "1895", "koney": "coney"}      # how a line is SPOKEN vs how Whisper WRITES it


def _said_as_written(text):
    t = text.lower()
    for a, b in _SAYS.items():
        t = t.replace(a, b)
    return t


def _align(lines, words):
    """Snap Whisper words to the narration lines: consume words until their letters cover the line's letters
    (robust to 'sawtooth' vs 'saw-tooth'), then rescale their times into that line's exact [s, e]."""
    out, i = [], 0
    for ln in lines:
        need = len(_norm(_said_as_written(ln["text"])))
        got, have = [], 0
        while i < len(words) and have < need - 1:
            got.append(words[i])
            have += len(_norm(words[i]["w"]))
            i += 1
        if got:
            a0, a1 = got[0]["s"], max(got[-1]["e"], got[0]["s"] + 1e-3)
            k = (ln["e"] - ln["s"]) / (a1 - a0)
            for w in got:
                out.append(dict(w, s=round(ln["s"] + (w["s"] - a0) * k, 3), e=round(ln["s"] + (w["e"] - a0) * k, 3)))
    return out


CAPTION_WORDS = _align(LINES, WORDS)   # captions use line-snapped words; W() (picture timing) keeps the raw times
DUR = round(LINES[-1]["e"] + 0.03, 2)          # ends on "...what happens" -> loops straight into line 1
NF = int(DUR * FPS)
TITLE = ("BUILD A", "CASTLE")                   # second part is yellow


def S(i):
    return LINES[i - 1]["s"]


def E(i):
    return LINES[i - 1]["e"]


def _norm(w):
    return "".join(ch for ch in w.lower() if ch.isalnum())


def W(word, after=0.0):
    word = _norm(word)
    for w in WORDS:
        if w["s"] >= after - 0.45 and _norm(w["w"]) == word:
            return w["s"]
    raise KeyError(f"word {word!r} not found after {after}")


# key terms: (caption words, time the term word is spoken) -> yellow+underline caption, ding, 3D flash
TERMS = {
    "lift hill": W("lift", S(4)),
    "anti-rollback": W("anti", S(7)),
    "upstop and guide wheels": W("upstop", S(11)),
    "clothoid loop": W("clothoid", S(15)),
    "magnetic brake": W("magnetic", S(18)),
    "block system": W("block", S(22)),
}
TITLE = ("BUILD A", "ROLLER COASTER")

# 2D tags: text, anchor, t0, t1, dx, dy, term
TAGS = [
    ("WOODEN RAMP", "ramp", 1.2, 5.0, -40, -170, False),
    ("FRICTION", "wood_cart", W("friction", S(2)), E(2) - 0.3, 120, -150, False),
    ("CHAIN", "chain", W("chain", S(3)), E(3), 150, -120, False),
    ("LIFT HILL", "lift", TERMS["lift hill"], E(4) + 0.5, -60, -200, True),
    ("SNAP", "chain_break", W("snaps", S(5)), E(5) + 0.2, 120, -140, False),
    ("SAW-TOOTH STRIP", "ratchet", W("strip", S(6)) - 0.3, W("latch", S(6)) + 0.8, -150, 170, False),
    ("LATCH", "latch", W("latch", S(6)), E(6), 160, 150, False),
    ("ANTI-ROLLBACK", "latch", TERMS["anti-rollback"], E(7) + 0.5, 0, 220, True),
    ("ROAD WHEEL", "w_road", W("wheels", S(10)) + 0.5, E(11) + 0.4, -180, -150, False),
    ("UPSTOP", "w_up", W("under", S(10)), E(11) + 0.4, -170, 170, True),
    ("GUIDE", "w_guide", W("beside", S(10)), E(11) + 0.4, 190, 60, True),
    ("CLOTHOID LOOP", "loop_top", TERMS["clothoid loop"], E(15) + 0.6, 0, -170, True),
    ("BRAKE PADS", "pads", W("brake", S(16)), E(16), -120, -170, False),
    ("COPPER FIN", "fin", W("fins", S(17)), E(17) - 0.5, -170, 160, False),
    ("MAGNETS", "magnets", W("magnets", S(17)), E(18) + 0.4, 170, -150, False),
    ("MAGNETIC BRAKE", "magnets", TERMS["magnetic brake"], E(18) + 0.4, -60, -230, True),
    ("STALLED", "trainA", W("stalls", S(20)) - 0.2, E(20) + 0.3, 80, -190, False),
    ("BLOCK BRAKE", "clamp", W("only", S(21)), E(22) + 0.4, -140, -180, False),
]
COUNTERS = [
    ("~6", "G AT THE BOTTOM", "ABOUT", W("six", S(13)) - 0.15, E(13) + 0.5, 540, 470),
]
CARDS = [
    (["CLICK-CLACK"], W("click", S(8)) - 0.1, E(8) + 0.2, 1420),
    (["SEA LION PARK, CONEY ISLAND", "1895"], S(23), E(23) + 0.2, 470),
]
DINGS = list(TERMS.values())

# ------------------------------------------------------------------ mix
MUSIC = {"file": "audio/music_takes/take_a.wav", "src_start": 0.0, "under_voice_db": -14.0, "gap_lift_db": 4.0,
         "fade_in": 0.05, "fade_out": 0.08, "loop": True}
_d = [("ding_a.wav", "ding_b.wav")[i % 2] for i in range(len(TERMS))]
SFX = [(f, t + 0.02, -15.0) for f, t in zip(_d, sorted(TERMS.values()))]
_clk = []
_t = S(8) + 0.1
while _t < E(8) + 0.2:                       # the latch ticking over the teeth while the cart climbs
    _clk.append(("click.wav", round(_t, 3), -22.0))
    _t += 0.21
_t = S(7) + 0.1
while _t < W("rolling", S(7)) - 0.1:
    _clk.append(("click.wav", round(_t, 3), -24.0))
    _t += 0.3
SFX += _clk + [("click.wav", W("catches", S(7)), -12.0),
               ("whoosh.wav", W("over", S(9)) + 0.4, -16.0),
               ("whoosh.wav", W("bottom", S(13)) - 0.6, -17.0),
               ("whoosh.wav", S(15) + 0.4, -18.0)]
