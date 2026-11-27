#!/usr/bin/env python3
"""build-explainer installer (stdlib only, Python 3.10+, Windows / macOS / Linux). Safe to re-run.

  python setup/install.py            install / repair everything; stops and says so if something needs you
  python setup/install.py --check    report only, change nothing
  python setup/install.py --yes      also install missing Blender / ffmpeg with the system package manager
  python setup/install.py --home DIR treat DIR as the home folder (testing in a sandbox)
  python setup/install.py --films-dir DIR   where films are made (default ~/build-explainer-films)

What it does: puts the skill in ~/.claude/skills/build-explainer, creates a venv at ~/.build-explainer/venv with
requirements.txt, downloads the Kokoro voice model into ~/.build-explainer/models, finds Blender 5.x + ffmpeg,
picks the video encoder (NVENC if it really works, else libx264), makes sure fonts exist, writes config.json and
runs a smoke test (narrate one line, transcribe it). Ends with a PASS/FAIL table.
"""
import argparse
import glob
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OS = {"Windows": "win", "Darwin": "mac"}.get(platform.system(), "linux")
KOKORO_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
KOKORO_FILES = {"kokoro-v1.0.onnx": 325532387, "voices-v1.0.bin": 28214398}
GF = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
FONTS = {  # config key -> (file name, url); both SIL OFL
    "font_bold": ("BarlowCondensed-Bold.ttf", GF + "barlowcondensed/BarlowCondensed-Bold.ttf"),
    "font_mono": ("JetBrainsMono[wght].ttf", GF + "jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf"),
}
WIN_FONTS = {"font_bold": r"C:\Windows\Fonts\bahnschrift.ttf", "font_mono": r"C:\Windows\Fonts\consolab.ttf"}
MODULES = ["numpy", "scipy", "soundfile", "PIL", "kokoro_onnx", "faster_whisper"]

rows = []  # (item, status, detail)


def note(item, status, detail=""):
    rows.append((item, status, detail))
    print(f"[{status:4}] {item}: {detail}", flush=True)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def venv_python(venv):
    return venv / ("Scripts/python.exe" if OS == "win" else "bin/python")


def same(a, b):
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return False


def download(url, dest, size=None, label=""):
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "build-explainer-installer"})
    with urllib.request.urlopen(req, timeout=60) as r, open(part, "wb") as f:
        total = int(r.headers.get("Content-Length") or size or 0)
        got, last = 0, -10
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
            got += len(b)
            pct = int(got * 100 / total) if total else 0
            if pct - last >= 10:
                print(f"    {label or dest.name}: {got / 1e6:.0f}/{total / 1e6:.0f} MB ({pct}%)", flush=True)
                last = pct
    if size and part.stat().st_size != size:
        n = part.stat().st_size
        part.unlink()
        raise RuntimeError(f"{dest.name}: got {n} bytes, expected {size}")
    part.replace(dest)


# ---------- skill folder ----------
def is_this_skill(p):
    sk = p / "SKILL.md"
    return sk.is_file() and re.search(r"^name:\s*build-explainer\s*$", sk.read_text(encoding="utf8", errors="ignore"), re.M)


def place_skill(dest, check):
    if same(REPO, dest):
        note("Skill folder", "PASS", f"running from {dest}")
        return dest
    if dest.exists() and any(dest.iterdir()):
        if is_this_skill(dest):
            note("Skill folder", "PASS", f"{dest} already has the skill (using it; update with git pull there)")
            return dest
        note("Skill folder", "FAIL", f"{dest} exists and is not build-explainer. Move it away or ask the user; stopping.")
        return None
    if check:
        note("Skill folder", "TODO", f"would copy {REPO} -> {dest}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(REPO, dest, ignore=shutil.ignore_patterns("__pycache__", "config.json", "fonts", "*.pyc"))
    note("Skill folder", "PASS", f"copied to {dest}")
    return dest


# ---------- python env ----------
def setup_venv(skill, venv, check):
    py = venv_python(venv)
    if sys.version_info < (3, 10):
        note("Python", "FAIL", f"need 3.10+, running {platform.python_version()}")
        return None
    note("Python", "PASS", platform.python_version())

    def have():
        return py.exists() and run([str(py), "-c", "import " + ",".join(MODULES)]).returncode == 0

    if have():
        note("Venv + packages", "PASS", str(venv))
        return py
    if check:
        note("Venv + packages", "TODO", f"would create {venv} and pip install requirements.txt")
        return None
    if not py.exists():
        print(f"creating venv {venv} ...", flush=True)
        r = run([sys.executable, "-m", "venv", str(venv)])
        if r.returncode:
            note("Venv + packages", "FAIL", "venv creation failed: " + r.stderr.strip()[-300:] +
                 ("  (Linux: sudo apt install python3-venv)" if OS == "linux" else ""))
            return None
    print("pip install -r requirements.txt (a few minutes) ...", flush=True)
    run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
    r = subprocess.run([str(py), "-m", "pip", "install", "-r", str(skill / "requirements.txt")], text=True)
    if r.returncode or not have():
        note("Venv + packages", "FAIL", "pip install failed (see output above)")
        return None
    note("Venv + packages", "PASS", str(venv))
    return py


# ---------- models ----------
def setup_models(mdir, check):
    missing = [n for n, sz in KOKORO_FILES.items() if not (mdir / n).is_file() or (mdir / n).stat().st_size != sz]
    if not missing:
        note("Kokoro models", "PASS", str(mdir))
        return True
    if check:
        note("Kokoro models", "TODO", f"would download {', '.join(missing)} (~340 MB) to {mdir}")
        return False
    try:
        for n in missing:
            print(f"downloading {n} ...", flush=True)
            download(KOKORO_BASE + n, mdir / n, KOKORO_FILES[n])
    except Exception as e:
        note("Kokoro models", "FAIL", f"download failed: {e}")
        return False
    note("Kokoro models", "PASS", str(mdir))
    return True


# ---------- blender / ffmpeg ----------
def blender_version(exe):
    try:
        out = run([str(exe), "--version"], timeout=90).stdout
        m = re.search(r"Blender (\d+)\.(\d+)", out)
        return (int(m.group(1)), int(m.group(2))) if m else None
    except Exception:
        return None


def find_blender():
    cands = []
    w = shutil.which("blender")
    if w:
        cands.append(w)
    if OS == "win":
        for base in {os.environ.get("ProgramFiles", r"C:\Program Files"), r"C:\Program Files"}:
            cands += sorted(glob.glob(base + "/Blender Foundation/Blender */blender.exe"), reverse=True)
        cands += sorted(glob.glob(os.path.expanduser("~/AppData/Local/Programs/Blender Foundation/Blender */blender.exe")), reverse=True)
        cands += glob.glob(r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe")
    elif OS == "mac":
        cands += ["/Applications/Blender.app/Contents/MacOS/Blender",
                  os.path.expanduser("~/Applications/Blender.app/Contents/MacOS/Blender")]
    else:
        cands += ["/usr/bin/blender", "/usr/local/bin/blender", "/snap/bin/blender"]
        cands += sorted(glob.glob(os.path.expanduser("~/blender*/blender")), reverse=True)
    best = None
    seen = set()
    for c in cands:
        if not c or c in seen or not os.path.isfile(c):
            continue
        seen.add(c)
        v = blender_version(c)
        if v and (best is None or (v[0] >= 5, v) > (best[1][0] >= 5, best[1])):
            best = (c, v)
    return best


def find_ffmpeg():
    w = shutil.which("ffmpeg")
    if w:
        return w
    if OS == "win":
        for pat in (os.path.expanduser("~/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/**/bin/ffmpeg.exe"),
                    r"C:\ffmpeg\bin\ffmpeg.exe", r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"):
            g = glob.glob(pat, recursive=True)
            if g:
                return g[0]
    elif OS == "mac":
        for p in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"):
            if os.path.isfile(p):
                return p
    return None


INSTALL_CMDS = {
    "blender": {"win": ["winget", "install", "-e", "--id", "BlenderFoundation.Blender"],
                "mac": ["brew", "install", "--cask", "blender"],
                "linux": ["sudo", "snap", "install", "blender", "--classic"]},
    "ffmpeg": {"win": ["winget", "install", "-e", "--id", "Gyan.FFmpeg"],
               "mac": ["brew", "install", "ffmpeg"],
               "linux": ["sudo", "apt", "install", "-y", "ffmpeg"]},
}


def ensure_tool(name, finder, yes, check):
    r = finder()
    if r or check or not yes:
        return r
    cmd = INSTALL_CMDS[name][OS]
    if shutil.which(cmd[1] if cmd[0] == "sudo" else cmd[0]):
        print(f"installing {name}: {' '.join(cmd)}", flush=True)
        subprocess.run(cmd)
        r = finder()
    return r


def detect_encoder(ffmpeg):
    try:
        if "h264_nvenc" not in run([ffmpeg, "-hide_banner", "-encoders"]).stdout:
            return "libx264", "no h264_nvenc in this ffmpeg"
        t = run([ffmpeg, "-v", "error", "-f", "lavfi", "-i", "color=black:s=320x240:d=0.2", "-frames:v", "1",
                 "-c:v", "h264_nvenc", "-f", "null", "-"])
        if t.returncode == 0:
            return "h264_nvenc", "NVENC test encode worked"
        return "libx264", "NVENC listed but test encode failed (no NVIDIA GPU?)"
    except Exception as e:
        return "libx264", f"encoder probe failed: {e}"


# ---------- fonts ----------
def setup_fonts(skill, check, force_download=False):
    out, notes, bad = {}, [], False
    for key, (fname, url) in FONTS.items():
        win = WIN_FONTS[key]
        local = skill / "fonts" / fname
        if OS == "win" and os.path.isfile(win) and not force_download:
            out[key] = win
            notes.append(f"{Path(win).name} (system)")
        elif local.is_file() and local.stat().st_size > 10000:
            out[key] = str(local)
            notes.append(f"{fname} (downloaded)")
        elif check:
            out[key] = str(local)
            notes.append(f"would download {fname}")
            bad = True
        else:
            out[key] = str(local)
            try:
                print(f"downloading font {fname} (SIL OFL) ...", flush=True)
                download(url, local, label=fname)
                notes.append(f"{fname} (downloaded)")
            except Exception as e:
                notes.append(f"{fname} FAILED: {e}")
                bad = True
    note("Fonts", "TODO" if (bad and check) else ("FAIL" if bad else "PASS"), "; ".join(notes))
    return out


# ---------- smoke test ----------
def smoke(py, skill):
    tmp = Path(tempfile.mkdtemp(prefix="bx_smoke_"))
    try:
        (tmp / "script.txt").write_text("If you stack stones, you have got a wall.\n", encoding="utf8")
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        r = run([str(py), "-X", "utf8", str(skill / "scripts" / "narrate.py"), str(tmp / "script.txt"), str(tmp / "vo.wav")], env=env)
        if r.returncode:
            return False, "narrate failed: " + (r.stderr or r.stdout).strip()[-400:]
        print("    transcribing (first run downloads the Whisper model, ~500 MB) ...", flush=True)
        r = run([str(py), "-X", "utf8", str(skill / "scripts" / "transcribe.py"), str(tmp / "vo.wav")], env=env)
        if r.returncode:
            return False, "transcribe failed: " + (r.stderr or r.stdout).strip()[-400:]
        data = json.loads((tmp / "vo.scan" / "ears.json").read_text(encoding="utf8"))
        words = [w for s in data["segments"] for w in s["words"]]
        if not words:
            return False, "no words recognised"
        return True, "heard: " + " ".join(f"{w['w']}({w['s']:.2f})" for w in words)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def finish():
    print("\n==== build-explainer setup summary ====")
    w = max(len(r[0]) for r in rows) if rows else 10
    for item, st, det in rows:
        print(f"{item:<{w}}  {st:<5} {det}")
    bad = [r for r in rows if r[1] == "FAIL"]
    todo = [r for r in rows if r[1] == "TODO"]
    if bad:
        print(f"\nRESULT: FAIL ({len(bad)} item(s) need attention; fix them and re-run, it is safe to repeat)")
        return 1
    if todo:
        print(f"\nRESULT: CHECK ONLY - {len(todo)} item(s) would be done by a real install")
        return 0
    print("\nRESULT: PASS - restart Claude Code (or open a new session), then type /build-explainer <thing>")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report only, change nothing")
    ap.add_argument("--yes", action="store_true", help="install missing Blender / ffmpeg via winget/brew/apt/snap")
    ap.add_argument("--home", default=None, help="use this folder as ~ (sandbox testing)")
    ap.add_argument("--films-dir", default=None)
    ap.add_argument("--no-smoke", action="store_true")
    ap.add_argument("--download-fonts", action="store_true", help="use the free OFL fonts even if Bahnschrift/Consolas exist")
    a = ap.parse_args()

    home = Path(a.home).expanduser() if a.home else Path.home()
    work = home / ".build-explainer"
    dest = home / ".claude" / "skills" / "build-explainer"
    print(f"build-explainer installer  OS={OS}  home={home}  mode={'CHECK' if a.check else 'INSTALL'}\n", flush=True)

    skill = place_skill(dest, a.check)
    if skill is None:
        return finish()
    if a.check and not skill.exists():
        skill = REPO  # check mode: inspect from the repo copy
    py = setup_venv(skill, work / "venv", a.check)
    models_ok = setup_models(work / "models", a.check)

    bl = ensure_tool("blender", find_blender, a.yes, a.check)
    if bl and bl[1][0] >= 5:
        note("Blender", "PASS", f"{bl[0]} (v{bl[1][0]}.{bl[1][1]})")
    elif bl:
        note("Blender", "WARN", f"{bl[0]} is v{bl[1][0]}.{bl[1][1]}; the kit is written for 5.x. "
             f"Install 5.x: {' '.join(INSTALL_CMDS['blender'][OS])}")
    else:
        note("Blender", "FAIL", "not found. Install: " + " ".join(INSTALL_CMDS["blender"][OS]) +
             "  (or https://www.blender.org/download/), then re-run this installer")
    ff = ensure_tool("ffmpeg", find_ffmpeg, a.yes, a.check)
    if ff:
        note("ffmpeg", "PASS", ff)
        enc, why = detect_encoder(ff)
        note("Video encoder", "PASS", f"{enc} ({why})")
    else:
        enc = "libx264"
        note("ffmpeg", "FAIL", "not found. Install: " + " ".join(INSTALL_CMDS["ffmpeg"][OS]) + "  then re-run")
        note("Video encoder", "SKIP", "needs ffmpeg")

    fonts = setup_fonts(skill, a.check, a.download_fonts)
    films = Path(a.films_dir).expanduser() if a.films_dir else home / "build-explainer-films"
    cfgd = {"python": str(py or venv_python(work / "venv")), "blender": bl[0] if bl else "",
            "ffmpeg": ff or "", "kokoro_models": str(work / "models"), "films_dir": str(films),
            "encoder": enc, "font_bold": fonts["font_bold"], "font_mono": fonts["font_mono"]}
    cpath = (skill if skill.exists() and not same(skill, REPO) or not a.check else dest) / "config.json"
    if a.check:
        note("config.json", "TODO", f"would write {cpath}")
    else:
        films.mkdir(parents=True, exist_ok=True)
        cpath.write_text(json.dumps(cfgd, indent=2), encoding="utf8")
        note("config.json", "PASS", str(cpath))

    if a.check or a.no_smoke:
        note("Smoke test", "SKIP", "check mode" if a.check else "--no-smoke")
    elif py and models_ok:
        ok, msg = smoke(py, skill)
        note("Smoke test", "PASS" if ok else "FAIL", msg)
    else:
        note("Smoke test", "FAIL", "needs the venv and Kokoro models first")
    return finish()


if __name__ == "__main__":
    sys.exit(main())
