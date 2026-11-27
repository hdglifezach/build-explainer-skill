# build-explainer (Claude Code skill)

## Quick start
**Paste this repo's link into Claude Code and say: `set this up`.** Claude reads this README, follows the section
"Instructions for Claude (setup)" below, installs everything, and tells you when to restart Claude Code. Then type
`/build-explainer a castle`.

## Instructions for Claude (setup)
When the user pastes this repo link and asks to set it up, do exactly this:
1. Make sure `git` and Python 3.10+ exist (`python --version`; on macOS/Linux use `python3`). If not, tell the user how to install them and stop.
2. Clone the repo into the skills folder: `git clone https://github.com/hdglifezach/build-explainer-skill ~/.claude/skills/build-explainer`
   (Windows: `%USERPROFILE%\.claude\skillsuild-explainer``). If that folder already exists and is not this repo, stop and ask the user. If it is this repo, `git pull` instead. The repo is private; if the clone asks for credentials, ask the user to sign in with `gh auth login`.
3. Run `python ~/.claude/skills/build-explainer/setup/install.py --check` and show the user what it found. Then run `python ~/.claude/skills/build-explainer/setup/install.py` (no flags). It downloads about 340 MB of voice models plus packages and takes a few minutes; run it in the background or with a long timeout.
4. If Blender 5.x or ffmpeg is reported missing, ASK the user before installing anything. With a yes, run the exact command the table printed (Windows `winget install BlenderFoundation.Blender` / `winget install Gyan.FFmpeg`; macOS `brew install --cask blender` / `brew install ffmpeg`; Linux `sudo snap install blender --classic` / `sudo apt install ffmpeg`), or re-run the installer with `--yes`. Then re-run `install.py`.
5. Read the PASS/FAIL table at the end. Every row must be PASS (Blender WARN means a non-5.x version; mention it). Fix any FAIL from its message and re-run; the installer is idempotent. Do not claim success unless the Smoke test row says PASS.
6. Tell the user: restart Claude Code (or start a new session) so the `/build-explainer` skill loads, then type `/build-explainer <thing>` (for example `/build-explainer a castle`). Mention that films are written to the `films_dir` shown in `config.json` and that the music bed can be any royalty-free file they own the rights to.

## What it makes
`/build-explainer <thing>` makes a 75-150 second vertical (1080x1920, 30 fps) "build it from scratch" 3D engineering
explainer Short in Blender. One continuous moving camera flies over one stylized low-poly set that grows piece by piece
("If you put a ring of logs around your house, you've got a castle. But wood burns. So you build it out of stone...").
A faceless wooden mannequin plays "you". The video has label tags with leader lines, yellow highlight flashes on each
new term, big counters, monospace cards, word-timed captions, a calm local narrator (Kokoro), an ACE-Step music bed and
soft dings. The whole render is QA'd on contact sheets at 2 fps before delivery.

Example output: a ~106 s Short, "Build a Castle", where walls rise course by course, a moat floods, a drawbridge swings
and the last line loops back into the first. Templates for three films (castle, roller coaster, elevator) are in
`templates/`.

## Requirements
The installer handles all of this except Blender and ffmpeg (it tells you the exact install command).
- Claude Code, Python 3.10+ (to run the installer)
- Blender 5.x (the kit is written against 5.2; EEVEE, headless `-b`)
- ffmpeg (NVENC is used automatically if your GPU supports it, otherwise libx264)
- In the venv the installer builds: `numpy scipy soundfile Pillow kokoro-onnx faster-whisper` (see `requirements.txt`)
- Kokoro TTS model files (`kokoro-v1.0.onnx`, `voices-v1.0.bin`, ~340 MB, downloaded to `~/.build-explainer/models`)
- Word timestamps come from `scripts/transcribe.py` (faster-whisper, model `small.en`, downloaded on first use, ~500 MB)
- Fonts: Windows Bahnschrift + Consolas if present, otherwise free OFL fonts (Barlow Condensed Bold, JetBrains Mono) downloaded into `fonts/`
- Music bed: any royalty-free file you have the rights to (ACE-Step 1.5 is an optional local generator)

## Install
### Automatic (recommended)
Paste this repo's link into Claude Code and say "set this up" (see the next section), or run it yourself:
```
git clone https://github.com/hdglifezach/build-explainer-skill ~/.claude/skills/build-explainer
python ~/.claude/skills/build-explainer/setup/install.py          # add --check to only report, --yes to let it install Blender/ffmpeg
```
`install.py` is safe to re-run. It creates a venv at `~/.build-explainer/venv`, downloads the Kokoro models, finds
Blender and ffmpeg, picks the encoder, sorts out fonts, writes `config.json`, runs a smoke test (narrates one line, then
transcribes it) and prints a PASS/FAIL table. Restart Claude Code afterwards so the skill loads.

### Manual
1. Copy/clone this folder to `~/.claude/skills/build-explainer`.
2. `python -m venv ~/.build-explainer/venv` and `pip install -r requirements.txt` in it.
3. Put `kokoro-v1.0.onnx` and `voices-v1.0.bin` (from the kokoro-onnx `model-files-v1.0` release) in one folder.
4. Create `config.json` in the skill folder:

| Key | Meaning |
|---|---|
| `python` | the venv's python |
| `blender` | Blender 5.x executable |
| `ffmpeg` | ffmpeg executable |
| `kokoro_models` | folder with the two Kokoro files (read by `narrate.py`) |
| `films_dir` | folder holding one subfolder per film |
| `encoder` | `h264_nvenc` or `libx264` (used by `overlay_compose.py`) |
| `font_bold`, `font_mono` | TTF files for captions/titles and cards (used by `overlay_compose.py`, `qa_sheet.py`) |

Scripts fall back to the env vars `PY BLENDER FFMPEG KOKORO_MODELS BX_FILMS BX_ENCODER BX_FONT_BOLD BX_FONT_MONO` and then to defaults.

## Usage
`/build-explainer a castle` (or any thing whose design is a chain of fixes: chimney, bike, bridge, lock, dam ...).

## Pipeline
1. Topic + script (formula: "If you X, you've got a Y. But Z. So you W. That's the term." x 8-12, one twist, one payoff, loop line); wait for approval.
2. Narration with Kokoro, one take per line, then Whisper word times (`transcribe.py`).
3. `spec.py`: shared timing (terms, tags, counters, cards, music, SFX) derived from the narration.
4. Blender scene `build.py` (+ copied `bx_kit.py`): every frame is a pure function of the frame number.
5. Snap QA: stills with overlays, contact sheet, iterate.
6. Full render in a single Blender process (resumable).
7. Music (ACE-Step) + SFX + voice-first mix at -14 LUFS.
8. Encode with overlays, then QA the whole video at 2 fps.
9-10. Optional VideoHub registration and post metadata.

## Files
| File | Job |
|---|---|
| `SKILL.md` | the skill itself: format, workflow, orientation rules |
| `scripts/bx_kit.py` | Blender kit: look, materials, `Mannequin` + poses, `Swarm`, `CamPath`, `TrackPath`, anchors, CLI |
| `scripts/bx_config.py` | loads `config.json` (paths, encoder, fonts) for the scripts |
| `scripts/transcribe.py` | faster-whisper word timestamps -> `audio/vo.scan/ears.json` + `ears.md` |
| `setup/install.py` | one-shot installer (`--check`, `--yes`, `--home`) |
| `scripts/narrate.py` | Kokoro narration -> `audio/vo.wav` + `vo_lines.json` |
| `scripts/overlay_compose.py` | title, captions, tags, counters, cards, hooks drawn on frames; encode with the mix (NVENC or libx264) |
| `scripts/make_mix.py` | voice-first mix, one limiter, -14 LUFS |
| `scripts/qa_sheet.py` | contact sheets of snaps or the whole video at 2 fps |
| `templates/*_build.py`, `*_spec.py`, `*_script.*` | worked examples: castle, roller coaster, elevator (cold-open hook) |
| `templates/elevator_make_sfx.py` | synthesised hook SFX example |

## Optional external tools (not included)
`SKILL.md` was written inside a larger private setup and mentions tools you can skip or replace: VideoHub (film
review/registration, steps 9-10), `earshot` (audio analysis for picking music/SFX),
`voice-music` (ACE-Step wrapper), `/postit` (posting) and some owner style rules. The core pipeline works without them.

## License
MIT, see `LICENSE`.
