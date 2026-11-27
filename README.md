# build-explainer (Claude Code skill)

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
- Claude Code
- Blender 5.x (the kit is written against 5.2; EEVEE, headless `-b`)
- Python 3.10+ with `numpy scipy soundfile Pillow` (+ `kokoro-onnx`, `faster-whisper`)
- Kokoro TTS model files (`kokoro-v1.0.onnx`, `voices-v1.0.bin`), folder given by `KOKORO_MODELS`
- Whisper word timestamps (faster-whisper) written to `audio/vo.scan/ears.json` as `{"segments":[{"words":[{"w","s","e"}]}]}`
- ffmpeg; NVENC optional (`overlay_compose.py` encodes with `h264_nvenc`; change the codec for CPU encoding)
- ACE-Step 1.5 for the music bed (optional; any royalty-free music file works)
- Windows fonts Bahnschrift and Consolas are used by the overlay scripts (edit the paths at the top of
  `overlay_compose.py` / `qa_sheet.py` on other systems)

## Install
Copy this folder to `~/.claude/skills/build-explainer`, then set these variables in your shell:

| Variable | Meaning |
|---|---|
| `BX_FILMS` | folder holding one subfolder per film |
| `BX_SKILL` | `~/.claude/skills/build-explainer` |
| `PY` | Python env from the requirements |
| `BLENDER` | Blender 5.x executable |
| `KOKORO_MODELS` | Kokoro model folder (read by `narrate.py`) |
| `EARS_PY`, `ACESTEP_PY`, `MUSIC_PY` | optional: word-timestamp tool, ACE-Step python and music runner |

## Usage
`/build-explainer a castle` (or any thing whose design is a chain of fixes: chimney, bike, bridge, lock, dam ...).

## Pipeline
1. Topic + script (formula: "If you X, you've got a Y. But Z. So you W. That's the term." x 8-12, one twist, one payoff, loop line); wait for approval.
2. Narration with Kokoro, one take per line, then Whisper word times.
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
| `scripts/narrate.py` | Kokoro narration -> `audio/vo.wav` + `vo_lines.json` |
| `scripts/overlay_compose.py` | title, captions, tags, counters, cards, hooks drawn on frames; NVENC encode with the mix |
| `scripts/make_mix.py` | voice-first mix, one limiter, -14 LUFS |
| `scripts/qa_sheet.py` | contact sheets of snaps or the whole video at 2 fps |
| `templates/*_build.py`, `*_spec.py`, `*_script.*` | worked examples: castle, roller coaster, elevator (cold-open hook) |
| `templates/elevator_make_sfx.py` | synthesised hook SFX example |

## Optional external tools (not included)
`SKILL.md` was written inside a larger private setup and mentions tools you can skip or replace: VideoHub (film
review/registration, steps 9-10), `ears` (Whisper word timestamps), `earshot` (audio analysis for picking music/SFX),
`voice-music` (ACE-Step wrapper), `/postit` (posting) and some owner style rules. The core pipeline works without them.

## License
MIT, see `LICENSE`.
