"""build-a-castle: shared timing + overlay spec (imported by build.py inside Blender AND by compose.py / make_mix.py).

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
for _after, _bad, _good in ((LINES[-1]["s"] - 0.3, "then", "than"),):
    for _w in WORDS:
        if _w["s"] >= _after and _w["w"].strip(" .,").lower() == _bad:
            _w["w"] = _good


def _align(lines, words):
    """Snap Whisper words to the narration lines: consume the words of each script line in order, then rescale their
    times into that line's exact [s, e] (Whisper smears pauses and can push a line's first word into the previous line)."""
    import re as _re
    nums = set("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
               "seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand".split())
    def toks(t):
        return [x for x in _re.split(r"[^a-z0-9']+", t.lower().replace("-", " ")) if x]
    out, i = [], 0
    for ln in lines:
        exp = toks(ln["text"])
        got = []
        j = 0
        while j < len(exp) and i < len(words):
            w = _norm(words[i]["w"])
            if w.isdigit():
                while j < len(exp) and exp[j] in nums:
                    j += 1
            else:
                j += 1
            got.append(words[i])
            i += 1
        if got:
            a0, a1 = got[0]["s"], max(got[-1]["e"], got[0]["s"] + 1e-3)
            k = (ln["e"] - ln["s"]) / (a1 - a0)
            for w in got:
                out.append(dict(w, s=round(ln["s"] + (w["s"] - a0) * k, 3), e=round(ln["s"] + (w["e"] - a0) * k, 3)))
    return out


CAPTION_WORDS = _align(LINES, WORDS)   # captions use line-snapped words; W() (picture timing) keeps the raw times
DUR = round(LINES[-1]["e"] + 0.12, 2)          # ends on "...no better than" -> loops into line 1
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
    "curtain wall": W("curtain", S(5)),
    "moat": W("moat", S(8)),
    "drawbridge": W("drawbridge", S(11)),
    "portcullis": W("portcullis", S(13)),
    "murder holes": W("murder", S(17)),
    "arrow slit": W("arrow", S(21)),
    "concentric castle": W("concentric", S(30)),
}

# 2D tags with a leader line to a 3D anchor (anchor names are defined in build.py)
#   text, anchor, t0, t1, dx, dy (tag offset from the anchor, px), term (True = yellow, flashes)
TAGS = [
    ("SHARPENED LOGS", "palisade", 1.6, 4.8, -40, -170, False),
    ("FIRE", "fire", W("torch", S(3)) + 0.9, E(3), 60, -170, False),
    ("CURTAIN WALL", "wall", TERMS["curtain wall"], E(5) + 0.6, -60, -190, True),
    ("SIEGE LADDER", "ladder", S(6) + 0.6, E(6) + 0.2, 40, -170, False),
    ("MOAT", "moat", TERMS["moat"], E(8) + 1.0, 30, -200, True),
    ("CHAINS", "chain", W("chains", S(10)) - 0.2, E(10), 110, -120, False),
    ("DRAWBRIDGE", "bridge", TERMS["drawbridge"], E(11) + 0.5, -40, -200, True),
    ("PORTCULLIS", "portcullis", TERMS["portcullis"], E(13) + 0.4, 120, -210, True),
    ("BATTERING RAM", "ram", S(14), E(14) + 0.3, -60, -190, False),
    ("STONES", "stones", W("stones", S(16)), E(16), -170, -150, False),
    ("SCALDING WATER", "water_drop", W("scalding", S(16)), E(16) + 0.2, 140, -230, False),
    ("MURDER HOLES", "holes", TERMS["murder holes"], E(17) + 0.5, 20, -230, True),
    ("WIDE INSIDE", "slit_in", S(20), E(20), -200, -130, False),
    ("NARROW OUTSIDE", "slit_out", S(20) + 0.4, E(20), 150, 170, False),
    ("ARROW SLIT", "slit_out", TERMS["arrow slit"], E(21) + 0.5, 150, -150, True),
    ("CLOCKWISE?", "stair", W("clockwise", S(23)), E(23) + 0.2, -220, -120, False),
    ("TREBUCHET", "trebuchet", W("trebuchet", S(26)), W("trebuchet", S(26)) + 2.6, 0, -230, False),
    ("COUNTERWEIGHT", "cweight", W("trebuchet", S(26)) + 0.6, W("trebuchet", S(26)) + 2.6, 170, 120, False),
    ("CRACK", "breach", W("cracks", S(27)), E(27) + 0.9, -40, -180, False),
    ("INNER WALL", "inner", W("second", S(28)) + 0.6, E(28) + 0.3, 60, -170, False),
    ("TRAPPED", "gap", W("trapped", S(29)), E(29), -150, -160, False),
    ("CONCENTRIC CASTLE", "inner", TERMS["concentric castle"], E(30) + 0.7, 0, -230, True),
    ("FORGED LETTER", "letter", W("forged", S(33)) - 0.2, E(33), 80, -170, False),
]

# big counters: value text, unit, caption above, t0, t1, screen x, y (centre of the number)
COUNTERS = [
    ("10", "FT THICK", "UP TO", W("ten", S(4)) - 0.1, E(4) + 0.3, 540, 470),
    ("~200", "LB", "HEAVIER THAN A MAN", W("heavier", S(26)) - 0.1, W("heavier", S(26)) + 2.4, 540, 470),
]

# monospace caption cards: lines, t0, t1, screen y
CARDS = [
    (["MANY TURN THE OTHER WAY", "\"PROBABLY A MYTH\""], W("plenty", S(24)), E(24) + 0.3, 470),
    (["KRAK DES CHEVALIERS", "SYRIA"], S(31), E(31) + 0.2, 470),
    (["1271"], W("1271", S(32)) - 0.1, E(32) + 0.2, 470),
]

# soft dings: every key term + a few accents (see audio/make_mix.py for the sounds)
DINGS = [t for t in TERMS.values()]

# ------------------------------------------------------------------ mix (audio/make_mix via the skill's make_mix.py)
MUSIC = {"file": "audio/music_takes/take_a.wav", "src_start": 0.0, "under_voice_db": -14.0, "gap_lift_db": 4.0,
         "fade_in": 0.4, "fade_out": 0.25}
_d = [("ding_g5.wav", "ding_c6.wav")[i % 2] for i in range(len(TERMS))]
SFX = [(f, t + 0.02, -15.0) for f, t in zip(_d, sorted(TERMS.values()))]
SFX += [("thud.wav", W("one", S(27)), -14.0), ("thud.wav", W("after", S(27)) + 0.35, -14.0),
        ("thud.wav", W("cracks", S(27)), -11.0),                                   # trebuchet stones land
        ("tok.wav", W("smashed", S(14)) - 0.15, -4.0), ("tok.wav", W("smashed", S(14)) + 0.55, -4.0),   # ram hits
        ("thud.wav", W("drops", S(12)) + 0.25, -20.0)]                             # portcullis lands
