"""why-elevators-dont-fall: shared timing + overlay spec (imported by build.py inside Blender AND by compose.py / make_mix.py).

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
for _after, _bad, _good in ():
    for _w in WORDS:
        if _w["s"] >= _after and _w["w"].strip(" .,").lower() == _bad and _w["s"] < _after + 3:
            _w["w"] = _good


_SAYS = {"eighteen fifty-four": "1854"}      # how a line is SPOKEN vs how Whisper WRITES it


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
DUR = round(LINES[-1]["e"] + 0.06, 2)          # ends on "...when the rope finally snaps" -> loops into the hook
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


# key terms
TERMS = {
    "counterweight": W("counterweight", S(6)),
    "safety gear": W("safety", S(10)),
    "overspeed governor": W("overspeed", S(13)),
    "buffers": W("buffers", S(15)),
}
TITLE = None                                   # hook rule: no title card - the hook text IS the opening
HOOKS = [                                      # big slammed text: text, t0, t1, y, colour ("y" yellow / "w" white)
    ("THIS SHOULD KILL YOU.", 0.0, 1.7, 360, "w"),
    ("...SO WHY DOESN'T IT?", 1.75, 3.15, 360, "y"),
]
NO_CAPTIONS = [(0.0, 3.2)]                     # the hook text replaces captions here

TAGS = [
    ("ONE ROPE", "rope", W("rope", S(3)) - 0.2, E(3), 150, -150, False),
    ("MOTOR", "motor", W("motor", S(4)) - 0.4, E(4) + 0.2, -150, -160, False),
    ("COUNTERWEIGHT", "cw", TERMS["counterweight"], E(7), 160, -170, True),
    ("SNAP", "snap", W("snaps", S(8)), E(8) + 0.2, 150, -140, False),
    ("GUIDE RAIL", "rail", W("rails", S(9)) - 0.2, E(9) + 0.3, -170, -160, False),
    ("SAFETY GEAR", "gear", TERMS["safety gear"], E(10) + 0.4, 170, -170, True),
    ("GOVERNOR ROPE", "govrope", W("second", S(12)), W("wheel", S(12)) + 0.8, -160, 150, False),
    ("FLYWEIGHTS", "fly", W("weights", S(12)) - 0.1, E(12) + 0.3, 170, -150, False),
    ("OVERSPEED GOVERNOR", "gov", TERMS["overspeed governor"], E(13) + 0.5, -60, -190, True),
    ("BUFFERS", "buffer", TERMS["buffers"], E(15) + 0.4, 120, -180, True),
    ("BRAKE", "brake", W("brake", S(18)) - 0.2, E(18) + 0.4, -150, -170, False),
    ("HANDWHEEL", "hand", W("hand", S(19)) - 0.4, E(19) + 0.2, 150, -150, False),
]
COUNTERS = []
CARDS = [
    (["STEEL ROPES", "x 4-8, BIG SAFETY MARGIN"], W("set", S(14)) - 0.2, E(14) + 0.3, 470),
    (["NEW YORK, 1854", "ELISHA OTIS"], S(20), E(20) + 0.2, 470),
]
DINGS = list(TERMS.values())

# ------------------------------------------------------------------ mix
MUSIC = {"file": "audio/music_takes/take_a.wav", "src_start": 0.0, "under_voice_db": -14.0, "gap_lift_db": 4.0,
         "fade_in": 0.6, "fade_out": 0.35, "start_at": S(3) - 0.25}
_d = [("ding_a.wav", "ding_b.wav")[i % 2] for i in range(len(TERMS))]
SFX = [(f, t + 0.02, -15.0) for f, t in zip(_d, sorted(TERMS.values()))]
# hook + story SFX (synth: audio/make_sfx.py; bank: earshot whip/metal/chop/dings, all local, no licences needed)
_bite = W("bite", S(10)) - 0.3
SFX += [("snap.wav", 0.10, -6.0), ("whip.wav", 0.10, -6.0), ("metal.wav", 0.10, -16.0),
        ("rush.wav", 0.75, -11.0),
        ("bite.wav", 1.37, -5.0), ("metal.wav", 1.37, -12.0),
        ("rewind.wav", 3.2, -8.0),
        ("snap.wav", W("snaps", S(8)), -8.0), ("whip.wav", W("snaps", S(8)), -12.0),
        ("bite.wav", _bite, -6.0),
        ("chop.wav", W("lock", S(12)), -6.0),
        ("bite.wav", W("yanks", S(13)) - 0.1, -9.0),
        ("metal.wav", W("landing", S(15)), -16.0),
        ("powerdown.wav", W("cuts", S(17)), -6.0),
        ("chop.wav", W("power", S(18)) + 0.1, -4.0),
        ("chop.wav", W("cut", S(20)), -2.0), ("metal.wav", W("cut", S(20)) + 0.3, -16.0)]
MUSIC["file"] = "audio/music_takes/take_b.wav"
