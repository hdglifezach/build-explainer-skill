---
name: build-explainer
description: Make a 75-150 s vertical (1080x1920, 30 fps) "build it from scratch" 3D engineering explainer Short in Blender, ConstrucBIM-style format with an original script and look - one continuous moving camera over one stylized low-poly set built up piece by piece, a faceless wooden mannequin as "you", label tags with leader lines, yellow highlight flashes, big counters, monospace caption cards, word-timed captions, a calm local narrator (Kokoro), an ACE-Step music bed and soft dings, QA'd at 2 fps and registered in VideoHub. Use when the owner types /build-explainer <thing>, or asks for a "build a X from scratch" / "if you ... you've got a ..." / ConstrucBIM-style explainer video.
---

# /build-explainer <thing>

**Path variables used below** (set them in your shell; see README): `$BX_FILMS` films root, `$BX_SKILL` this skill's folder,
`$PY` Python env, `$BLENDER` Blender 5.x executable, `$KOKORO_MODELS` Kokoro model folder (read by narrate.py),
optional: `$EARS_PY` word-timestamp tool (writes `audio/vo.scan/ears.json`), `$ACESTEP_PY`/`$MUSIC_PY` ACE-Step runner.
VideoHub (steps 9-10) and earshot are the owner's optional private tools and can be skipped.

One film = one folder `$BX_FILMS/<slug>/` (slug like `build-a-castle`).
Reference film (copy its files to start): `<skill>/templates/castle_*` (castle_build.py -> build.py, castle_spec.py -> spec.py, castle_script.*, plus scripts/bx_kit.py)
(`script.md`, `script.txt`, `spec.py`, `build.py`, `bx_kit.py`).
Kit + tools live in `$BX_SKILL/scripts/` (`$BX_SKILL` = `~/.claude/skills/build-explainer`):

| Script | Job |
|---|---|
| `narrate.py` | Kokoro narration, one take per script line, controlled pauses -> `audio/vo.wav` + `vo_lines.json` |
| `bx_kit.py` | Blender kit: look (sky, sun, distance fog, toon outline), materials with a highlight hook, `Mannequin` + pose library, `Swarm` particles, `CamPath` one-camera spline, anchors for 2D overlays, the snaps/render/anchors CLI |
| `overlay_compose.py` | title, captions, tags + leader lines, counters, cards drawn on the frames, NVENC encode with the mix; `stills` mode for snaps |
| `make_mix.py` | voice-first mix: bed ~14 dB under the voice, soft SFX on cue, -14 LUFS / -1.5 dBTP, one limiter |
| `qa_sheet.py` | contact sheets of snaps, or of the WHOLE video at 2 fps |

Python for tools: `$PY` (a Python 3.10+ env with numpy, scipy, soundfile, Pillow, kokoro-onnx, faster-whisper). Blender: `"$BLENDER" -b --factory-startup -P build.py -- ...`

## The format (make it ORIGINAL: own script, own models, own look; never copy the channel's scripts or assets)
- 75-150 s, ONE continuous camera move (no cuts): reframe every 1.5-3 s with push-ins, orbits, crane-ups, pull-outs.
  One environment that grows piece by piece; cutaways (a removable quarter of a tower, an open side of a tunnel).
- Look: clean stylized low-poly, soft daylight, fog to the horizon, light ink outline. Never photoreal (owner rule).
- "You" = faceless jointed wooden mannequin. Mood by pose + tint: blue = cold/scared, orange = warm/safe, red = enemy.
- Overlays: small dark tags with leader lines; the named part flashes solid yellow on its term; big counters
  ("10 FT THICK", "~200 LB"); monospace cards ("1271"); particles for invisible things (heat, rays, direction arrows).
  Captions bold uppercase in the middle third, 1-3 words, spoken word yellow, key term yellow + underlined. Title on top for 3 s.
- Sound: calm even male narrator ~3 words/s, music bed ~14 dB under the voice, a soft ding on each new term,
  a few warm/soft SFX for big physical beats. No meme SFX, no harsh clicks (owner rule: soft foley).

## Cold open / hook (plan it FIRST, before the script)
Viewer feedback on the coaster: "it looked entertaining but didn't catch me" - they scrolled past and only came back
consciously. The first 1-2 s must grab WITHOUT the viewer thinking:
- **Open on the most dramatic, already-moving moment**: a flash-forward to the failure or the payoff (the cable snaps
  and the car drops, the wall cracks, the train is about to hit). No title card, no calm wide establishing shot, no
  slow fade-in. Motion in frame 0, a camera already moving or shaking.
- **A big 2-4 word claim slammed on screen within ~0.3 s** ("THIS SHOULD KILL YOU.") - huge, centred, punch-scaled
  in; then the turn ("...so why doesn't it?") as the action resolves.
- **A sharp sound in frame 1** (snap, crack, hit) - the music can start on that punch or come in after the hook.
- Then "here's why" -> rewind / match-cut into line 1 of the loop formula.
- **Thumbnail test:** look at frame 0 and frame 30 (and 15, 45) as if each were the thumbnail. Each must read alone:
  one subject, action visible, big text.
- The loop ending must flow back into the HOOK (last frame matches frame 0's state + camera), not into a calm intro.
- Budget: hook 1.5-3 s; it may replay later in the film slowed down as the explained cutaway.
- **Implementation** (reference: `films/why-elevators-dont-fall`, templates `elevator_*`): narrate the hook as the
  first 1-2 script lines with `--lead 0.12`; in spec set `TITLE = None`, `HOOKS = [(text, t0, t1, y, "w"|"y")]`
  (slammed, auto-fit) and `NO_CAPTIONS = [(0, hook_end)]`; `MUSIC["start_at"]` lets the bed enter after the hook. In
  build.py the hook camera is a function of the subject (with fall lag + shake) and the last ~1.4 s blend the
  CamPath back into that same function, so the final frame equals frame 0. Punchy hook SFX are synthesised in
  `audio/make_sfx.py` (snap, rush, bite) and kept 3-5 dB under the voice so the hook does not distort.

## Workflow
### 1. Topic + script (then STOP for the owner's OK)
- Pick a thing whose design is a chain of fixes (castle, chimney, bike, igloo, bridge, toilet, lock, dam ...).
- Formula: line 1 = "If you [naive build], you've got a [thing]."; then 8-12 x "But [problem]. So you [fix]. That's the [term]."
  with ONE twist "Now you're [safe/warm/fine]... until [new threat]."; one payoff fact (a surprising real event or number);
  the last line is a half sentence that flows into line 1 so the Short loops ("...ended up no better than" -> "if you put a ring of logs...").
- Every "So you X" must be something the picture can SHOW (owner rule: every narrated action visibly happens).
- Fact-check each claim with WebSearch. Soften or drop anything historians dispute (e.g. clockwise-stair "sword arm" story ->
  "some say... probably a myth"). Write `script.md` (table: line | what is on screen | sources + softened facts) and
  `script.txt` (one VO line per text line; `|| 0.5` = pause after; split "That's the X." onto its own line).
- Show the owner the script and wait for an OK before building (skip only if the owner already approved the idea and said go).

### 2. Narration + word times
```
PY=python   # the env described above
$PY -X utf8 $BX_SKILL/scripts/narrate.py script.txt audio/vo.wav --speed 1.0 --gap 0.28 --term-gap 0.5
$PY -X utf8 $EARS_PY audio/vo.wav --no-separate --no-events --no-speakers --vocab "Term1,Term2"
```
- Voice: **Kokoro `am_michael`, speed 1.0** (calm, even US male; Apache-2.0, local, free). At 0.94 it is slower but a
  ~290-word script then runs ~119 s. Alternatives: `bm_george` (British), or Qwen3-TTS VoiceDesign (a local Qwen3-TTS install,
  describe "calm middle-aged male documentary narrator") if the owner wants more warmth.
- **Pronunciation:** read back EVERY proper name and number with ears/Whisper. Kokoro misreads some ("Coney" ->
  "Kenai"); test 3-4 spellings of the line in the scratchpad (e.g. "Koney", "Coh-nee", numbers spelled out:
  "eighteen ninety-five") and keep the one Whisper writes back correctly. Map spoken->written forms in spec `_SAYS`
  so caption alignment still counts letters right.
- Length check: `vo.wav` length = film length. Trim the script, not the speed, if it runs long.
- Read `audio/vo.scan/ears.md`; Whisper homophones (then/than) are fixed in `spec.py` (caption fix list).
- Whisper smears pauses into words (a line's first word can start inside the previous line). `spec.py` keeps the raw
  times for `W()` (picture timing) and builds `CAPTION_WORDS` snapped to each narration line's exact [s, e] (`_align`),
  which the captions use. Decide this BEFORE the full render: changing `W()` later shifts every beat.
### 3. spec.py (shared timing)
`S(i)`/`E(i)` = line start/end, `W(word, after)` = word start. Define `TERMS`, `TAGS` (text, anchor, t0, t1, dx, dy, term),
`COUNTERS`, `CARDS`, `MUSIC`, `SFX`. Everything is timed from the narration, so a re-voiced line moves the picture with it.
### 4. Blender scene (`build.py` + copied `bx_kit.py`)
- `K.setup_scene(...)`; build static geometry once; `animate(f)` sets EVERY transform/material value from `f` alone
  (no keyframes, no state) so any frame renders alone. End with `K.run(animate, BASE, NF, default_snaps=[...])`.
- Build-up helpers: courses that drop in one after another (`multi_box` one mesh per course), `scale.z` growth from
  `base=True` origins, earth "fill" pieces that shrink to dig, water planes that rise, `stick()` for chains/ropes.
- `Mannequin(name, tint)`: `.place(loc, yaw)`, `.face(target)`, `.pose(name|dict)`, `blend(a, b, k)`, `walk_pose(phase)`,
  `climb_pose(phase)`, `.set_tint("blue"|"orange"|"red", k)`, `.add_bow(m_wood, m_string)` / `.bow_on` / `.sync_bow()`. Pose library: stand, relax, cower, cheer, point, shrug,
  look_up, aim_bow, duck, carry, push, pour, sit, fallen, hold_up, wave. Mannequin front = -Y (yaw 180 faces +Y).
- **Orientation rules (the castle v1 got 8 owner notes from these):** Mannequin front = -Y; yaw ψ (degrees, about Z)
  turns the front to (sin ψ, -cos ψ): yaw 0 faces -Y, 180 faces +Y, **90 faces +X, -90 faces -X**. Prefer
  `.face(target)` over literal yaws. A figure walking a circle CLOCKWISE (angle a decreasing) needs yaw = a; counter-
  clockwise needs a + 180. A prop leaned with `rotation_euler.x = +θ` tips its top toward **-Y**; lean a ladder at a
  wall on +Y with `-θ`. Gable roofs: use `K.gable` (ridge along X), not a 3-sided cylinder. Siege engines: the
  throwing arm's long end points AWAY from the target and swings up and over. Archers get `add_bow()` +
  `bow_on = True` + `sync_bow()`; `aim_bow` twists the draw arm (shoulder rotation_mode ZXY) so the elbow bends back.
  When a part flashes for a term, every piece of it must flash (separate blocks too) and its tag must point at it.
  Characters standing on stairs/ramps: put their feet on the step height, not z = 0.
- **Tracks / rails / pipes** (`K.TrackPath`): control points -> dense centripetal spline with rotation-minimising
  frames (T, U, B) and arc length. `frame(s)`, `matrix(s)`, `sweep(name, mat, s0, s1, offsets, radii)` (tubes; faces
  in order of s so they can be revealed along their length), `ties(...)`, `supports(...)`. Ride vehicles by arc length
  with the track's own frame (local -Y = travel, +Z = track up) so they turn upside down only inside a loop. Shape
  morphs (circle -> teardrop loop): sweep both versions with the same sample count and add the second as a shape key;
  vehicles on the morphing part lerp the two frames. Reference: `films/build-a-roller-coaster/build.py` (route(),
  place_on(), sched() for scripted speed/stop/rollback, cart close-ups with push-ins).
- `highlight(obj, flash_amount(t, TERMS[term]))` = the yellow flash. `Swarm(name, proto, n).drive(fn)` = particles.
- `K.anchor(name, obj|point)` for each tag; the renderer writes `anchors/f_####.json` (screen xy) per frame.
- Camera: `K.CamPath([(t, pos, target, lens), ...], lens_scale=0.8)`; keys at narration times; one smooth path.
  Vertical frames feel cramped: keep lens_scale ~0.8 and pull back more than you think.
- Hollow cutaways: cut the walls that run INTO a hollow tower (they otherwise fill it with boxes).
- The spline does not avoid geometry: when a move goes from outside to inside (over a wall, past a tower), add a key
  that lifts the camera clear, and check the in-between frames in the 2 fps QA (the castle's first render flew
  through a tower and a row of merlons between two good keys). Characters must not walk through solid walls either
  (route them over a breach sill, along a bridge).
- **Seamless loop (owner note):** frame 0 must already show the opening state (nothing "builds from nothing" at f=0,
  no floating riders), the title is fully on at frame 0, and the last ~3 s return the scene to exactly that state
  (new parts sink away, the opening props rise back) while the camera's last key == its first key
  (`CamPath(..., taper=(0, DUR - 0.12))` removes drift at both ends). Set `DUR = last line end + 0.03` and
  `MUSIC["loop"] = True` so the bed's first second continues its last. Compare the last frame with frame 0 in snaps.
- **Riders and vehicles:** vehicles are hollow (floor + walls + seat), riders sit on the seat inside, restraints
  (lap bar) where a real one would be. Rails/tubes get no hull outline (hulls leave visible seam rings where
  segments join).
- **Background flair:** the opening wide shot needs something eye-catching behind the subject (ferris wheel, tents,
  bunting for a fairground) and the title on screen from frame 0.

### 5. Snaps QA (iterate until it reads)
```
blender ... -P build.py -- snaps 45,240,470,... tag [draft]
$PY .../overlay_compose.py <film> stills tag
$PY .../qa_sheet.py snaps "snaps/tag_*_ov.jpg" snaps/sheet_tag --cols 6 --rows 3 --w 300
```
Read the sheet yourself. Check: framing (subject centred, nothing cut off), labels readable and pointing at the right
part, nothing clipping/intersecting, the mannequin visible and reading clearly, each narrated action visible, captions
not covering the action. Debug invisible things with a temporary anchor (e.g. `you_head`) and read its json.
### 6. Full render: ONE Blender process (the GPU is shared)
`blender -b --factory-startup -P build.py -- render 0 <NF-1> > render.log` (run in background; resumable: skips
finished frames). EEVEE at 24 samples ran ~0.8 s/frame for the castle (~45 min for 106 s).
### 7. Music + SFX + mix
- Music: ACE-Step 1.5 (MIT, own music; never ripped commercial music):
  `$ACESTEP_PY $MUSIC_PY "<calm documentary underscore ...>" audio/music_takes --duration <DUR+6> --bpm 84 --count 1 --no-lm [--seed N]`
  (count>1 gives one file; run twice with seeds). Pick with earshot `describe` (calm, low LRA, no ding-like hits that
  fight the term dings); `measure music=true` gives the key -> pitch the dings to it.
- SFX: earshot shipped bank via `sfx_render` (CC0 fits / computed): `notify/m2` dings pitched to the key (alternate two
  notes), `pro_impact/deep` soft thuds, `fit/hit/bamboo_tok` wood knocks. Or CC0 SFX packs (check licences).
- `$PY -I .../make_mix.py <film>` -> `audio/mix.wav` (-14 LUFS, -1.5 dBTP). Check with earshot `measure` (and `timeline`).
### 8. Encode + full QA at 2 fps (owner rule, before delivery)
```
$PY .../overlay_compose.py <film> encode <film>/<slug>_v1.mp4
$PY .../qa_sheet.py video <film>/<slug>_v1.mp4 <film>/snaps/qa_v1
```
Read EVERY qa sheet (whole video). Fix, delete the bad frames and re-render only those ranges (`render a b`; a
camera key change alters the spline from two keys before to one key after it, so re-render that whole span), then
re-encode and re-check those ranges.
### 9. VideoHub (manual registration; VideoHub's browser render.js is NOT for Blender films)
Write `.videohub/project.json` `{"title": ..., "status": "review", "updated": ISO}` and `.videohub/versions.json`
(`[{"v":1,"file":"<slug>_v1.mp4","kind":"final","created":ISO,"job":"manual","mode":"manual","session":{"title":"Claude"},
"parent":null,"changedRanges":null,"chunks":null,"notes":[],"note":"..."}]`), like `films/cookie-3am-roblox/.videohub/`.
(Owner-specific: also junction the film folder into a renders folder.)
Then VERIFY VideoHub sees the video: the VideoHub CLI `hub_project` must print `Latest video: <slug>_vN.mp4`.
If it prints `Latest video: —`, VideoHub cached a failed ffprobe (VideoHub's `data/probe-cache.json` shows `ok: false`; it has
happened even after the file was complete): `touch` the mp4, `curl -X POST http://127.0.0.1:7788/api/scan`, wait ~30 s, check again
(repeat once if needed). The owner sees an empty review page until this is right.
### 10. Post metadata (never post from this skill)
`tags.txt` + `post_meta.json` (same shape as `films/noob-1000-furnaces-mc/post_meta.json`) so `/postit` (or `/postitai`)
can publish when the owner says so. Title idea: "How to Build a <Thing> (From Scratch)".

## Owner rules baked in
Stylized not photoreal · own/licensed music only · warm soft SFX · every narrated action visible · QA the whole render
at 2 fps · one Blender process · never upload/post without the owner · ask before any paid credits (this pipeline is all local).
