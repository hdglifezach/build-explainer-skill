"""bx_config.py - tiny stdlib loader for the skill's config.json (written by setup/install.py).

Lookup order for every key: config.json (skill folder) -> environment variable -> default.
  from bx_config import cfg, load_font
  cfg("ffmpeg"), cfg("kokoro_models"), cfg("encoder"), ...
"""
import json
import os
import shutil
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
_ENV = {"python": "PY", "blender": "BLENDER", "ffmpeg": "FFMPEG", "kokoro_models": "KOKORO_MODELS",
        "films_dir": "BX_FILMS", "encoder": "BX_ENCODER", "font_bold": "BX_FONT_BOLD", "font_mono": "BX_FONT_MONO"}
_WIN = r"C:\Windows\Fonts"


def _config():
    for p in (SKILL_DIR / "config.json", Path.home() / ".claude" / "skills" / "build-explainer" / "config.json"):
        try:
            return json.loads(p.read_text(encoding="utf8"))
        except Exception:
            continue
    return {}


def _default(key):
    home = Path.home()
    if key == "ffmpeg":
        return shutil.which("ffmpeg") or "ffmpeg"
    if key == "kokoro_models":
        return str(home / ".build-explainer" / "models")
    if key == "films_dir":
        return str(home / "build-explainer-films")
    if key == "encoder":
        return "libx264"
    if key == "font_bold":
        return _first_existing([_WIN + r"\bahnschrift.ttf", str(SKILL_DIR / "fonts" / "BarlowCondensed-Bold.ttf"),
                                "/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"])
    if key == "font_mono":
        return _first_existing([_WIN + r"\consolab.ttf", str(SKILL_DIR / "fonts" / "JetBrainsMono[wght].ttf"),
                                "/System/Library/Fonts/Menlo.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"])
    return ""


def _first_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[0]


def cfg(key):
    v = _config().get(key) or os.environ.get(_ENV.get(key, ""), "")
    return v or _default(key)


def load_font(path, size, weight="Bold"):
    """PIL font; variable fonts (Bahnschrift, JetBrains Mono) get the named weight when they support it."""
    from PIL import ImageFont
    f = ImageFont.truetype(path, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f
