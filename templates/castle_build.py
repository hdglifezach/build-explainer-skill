"""Build a Castle -- /build-explainer film #1 (1080x1920, 30 fps, ~106 s).

  blender -b --factory-startup -P build.py -- snaps 30,300,900 [tag] [draft]
  blender -b --factory-startup -P build.py -- render 0 3179
  blender -b --factory-startup -P build.py -- anchors 0 3179     (overlay anchors only, no render)

Every frame is a pure function of f (animate(f)); timings come from spec.py (narration line/word times).
Overlays (tags, captions, counters, cards, title) are drawn afterwards by compose.py from anchors/f_####.json.
"""
import math
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent  # build.py lives in the film folder
sys.path.insert(0, str(BASE))
import bx_kit as K  # noqa: E402
import spec  # noqa: E402
from spec import S, E, W, TERMS  # noqa: E402

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from bx_kit import (D, box, cyl, sphere, multi_box, ring_sector, hide, highlight, flash_amount, seg, smooth,  # noqa: E402
                    ease_out, ease_in, overshoot, lerp, lerpv, pulse, noise1, rng, mat, brick_mat, Swarm,
                    Mannequin, POSES, blend, walk_pose, climb_pose, ballistic, stick)

FPS = spec.FPS
NF = spec.NF
DRAFT = "draft" in K.cli_args()
K.setup_scene(res=(1080, 1920), fps=FPS, samples=24, draft=DRAFT, sky=(0.52, 0.68, 0.88),
              horizon=(0.80, 0.84, 0.86), sun_dir=(-32, 8, -38), sun_energy=4.2, sky_strength=1.05)

# ------------------------------------------------------------------ materials
M = {
    "grass": mat("grass", (0.50, 0.64, 0.36), rough=0.95),
    "grass_far": mat("grass_far", (0.55, 0.66, 0.42), rough=0.95),
    "dirt": mat("dirt", (0.55, 0.40, 0.27), rough=0.95),
    "dirt_dark": mat("dirt_dark", (0.42, 0.30, 0.21), rough=0.95),
    "stone": brick_mat("stone", (0.78, 0.75, 0.69), (0.70, 0.67, 0.62), (0.58, 0.55, 0.50), scale=0.55,
                       row_h=0.42),
    "stone2": brick_mat("stone2", (0.83, 0.80, 0.73), (0.76, 0.73, 0.67), (0.62, 0.59, 0.54), scale=0.55,
                        row_h=0.42),
    "stone_plain": mat("stone_plain", (0.74, 0.71, 0.66), rough=0.9),
    "cut": mat("cut", (0.88, 0.84, 0.76), rough=0.9),          # cutaway section faces (lighter)
    "log": mat("log", (0.58, 0.40, 0.24), rough=0.8),
    "log_end": mat("log_end", (0.80, 0.64, 0.42), rough=0.8),
    "wood": mat("wood", (0.55, 0.38, 0.23), rough=0.7),
    "wood_d": mat("wood_d", (0.36, 0.24, 0.15), rough=0.7),
    "iron": mat("iron", (0.22, 0.22, 0.24), rough=0.45, metal=0.6),
    "plaster": mat("plaster", (0.92, 0.86, 0.74), rough=0.9),
    "roof": mat("roof", (0.62, 0.30, 0.22), rough=0.8),
    "water": mat("water", (0.24, 0.47, 0.58), rough=0.08),
    "slit": mat("slit", (0.06, 0.06, 0.07), rough=0.9),
    "leaf": mat("leaf", (0.34, 0.52, 0.30), rough=0.9),
    "leaf2": mat("leaf2", (0.42, 0.58, 0.32), rough=0.9),
    "trunk": mat("trunk", (0.40, 0.28, 0.18), rough=0.9),
    "hill": mat("hill", (0.50, 0.60, 0.44), rough=1.0),
    "flame": mat("flame", (1.0, 0.38, 0.04), emit=1.3, emit_col=(1.0, 0.30, 0.02), fog=False),
    "flame_core": mat("flame_core", (1.0, 0.70, 0.15), emit=1.8, emit_col=(1.0, 0.62, 0.08), fog=False),
    "smoke": mat("smoke", (0.60, 0.57, 0.54), rough=1.0),
    "ash": mat("ash", (0.16, 0.14, 0.13), rough=1.0),
    "rock": mat("rock", (0.52, 0.50, 0.47), rough=0.9),
    "splash": mat("splash", (0.70, 0.86, 0.95), rough=0.2, emit=0.4, emit_col=(0.7, 0.86, 0.95)),
    "paper": mat("paper", (0.97, 0.95, 0.88), rough=0.6, emit=0.25, emit_col=(1, 1, 0.95)),
    "seal": mat("seal", (0.75, 0.10, 0.10), rough=0.5),
    "flag": mat("flag", (0.98, 0.98, 0.96), rough=0.7, emit=0.15),
    "arrow": mat("arrow", (0.30, 0.22, 0.14), rough=0.7),
    "arrow_dir": mat("arrow_dir", (1.0, 0.80, 0.12), emit=2.5, emit_col=(1.0, 0.78, 0.1), fog=False),
    "dust": mat("dust", (0.80, 0.74, 0.64), rough=1.0),
}

# ------------------------------------------------------------------ layout constants
W_ = 9.0          # outer curtain wall centreline half-size
T_ = 2.2          # wall thickness ("up to ten feet")
H_ = 6.5          # wall height
NC = 8            # stone courses
CH = H_ / NC
OUT = W_ + T_ / 2    # 10.1 outer face
INN = W_ - T_ / 2    # 7.9 inner face
GATE_X = 1.6
GATE_Z = 4.06        # top of the gate opening (5 courses)
BR_X = (-6.6, -3.4)  # breach panel (front wall), courses 2..5
BR_C = (2, 5)
MO_IN, MO_OUT, MO_D = 11.0, 15.0, 2.6     # moat ring + depth
IW, IT, IH = 4.4, 1.6, 9.6                 # inner wall (concentric)
TOW_R, TOW_H = 2.8, 9.2
CUT_T = Vector((W_, -W_, 0))               # front-right tower = the cutaway / stair tower

# ------------------------------------------------------------------ ground + moat
gz = -MO_D
# inner platform and outer land (dirt bodies with grass tops), leaving the moat ring open
box("plat", (0, 0, gz), (2 * MO_IN, 2 * MO_IN, MO_D - 0.12), M["dirt"], base=True, outline=False)
box("plat_top", (0, 0, -0.12), (2 * MO_IN, 2 * MO_IN, 0.12), M["grass"], base=True, outline=False)
FAR = 420.0
for nm, c, sz in (("land_n", (0, (MO_OUT + FAR) / 2), (2 * FAR, FAR - MO_OUT)),
                  ("land_s", (0, -(MO_OUT + FAR) / 2), (2 * FAR, FAR - MO_OUT)),
                  ("land_e", ((MO_OUT + FAR) / 2, 0), (FAR - MO_OUT, 2 * MO_OUT)),
                  ("land_w", (-(MO_OUT + FAR) / 2, 0), (FAR - MO_OUT, 2 * MO_OUT))):
    box(nm, (c[0], c[1], gz), (sz[0], sz[1], MO_D - 0.12), M["dirt"], base=True, outline=False)
    box(nm + "_top", (c[0], c[1], -0.12), (sz[0], sz[1], 0.12), M["grass"], base=True, outline=False)
box("moat_floor", (0, 0, gz - 0.3), (2 * MO_OUT, 2 * MO_OUT, 0.3), M["dirt_dark"], base=True, outline=False)
# moat fill: ring pieces of earth that get dug out one after another (origin at the moat floor)
MID = (MO_IN + MO_OUT) / 2
fill = []
for k in range(4):
    x0 = -MO_OUT + k * 7.5
    fill.append(((x0 + 3.75, -MID), (7.5, MO_OUT - MO_IN)))
    fill.append(((x0 + 3.75, MID), (7.5, MO_OUT - MO_IN)))
for k in range(3):
    y0 = -MO_IN + k * (2 * MO_IN / 3)
    fill.append(((-MID, y0 + MO_IN / 3), (MO_OUT - MO_IN, 2 * MO_IN / 3)))
    fill.append(((MID, y0 + MO_IN / 3), (MO_OUT - MO_IN, 2 * MO_IN / 3)))
fill.sort(key=lambda p: abs(math.atan2(p[0][0], -p[0][1])))   # dig order: from the gate outward, both sides together
FILL = []
for i, (c, sz) in enumerate(fill):
    e = K.empty(f"fill_{i}", (c[0], c[1], gz))
    box(f"fill_{i}_d", (0, 0, 0), (sz[0], sz[1], MO_D - 0.12), M["dirt"], e, base=True, outline=False)
    box(f"fill_{i}_g", (0, 0, MO_D - 0.12), (sz[0], sz[1], 0.12), M["grass"], e, base=True, outline=False)
    FILL.append(e)
water = K.empty("water")
for nm, c, sz in (("w_s", (0, -MID), (2 * MO_OUT, MO_OUT - MO_IN)), ("w_n", (0, MID), (2 * MO_OUT, MO_OUT - MO_IN)),
                  ("w_e", (MID, 0), (MO_OUT - MO_IN, 2 * MO_IN)), ("w_w", (-MID, 0), (MO_OUT - MO_IN, 2 * MO_IN))):
    box(nm, (c[0], c[1], 0), (sz[0] - 0.02, sz[1] - 0.02, 0.1), M["water"], water, outline=False)

# scenery: low-poly trees + far hills (fog does the depth)
R = rng(7)
for i in range(70):
    for _ in range(40):
        a = R.uniform(0, 2 * math.pi)
        d = R.uniform(24, 130)
        x, y = math.cos(a) * d, math.sin(a) * d
        if (y < -10 and d < 95) or d < 48:      # keep the camera side + trebuchet field open
            continue
        break
    s = R.uniform(0.8, 1.5)
    t = K.empty(f"tree_{i}", (x, y, 0))
    cyl(f"tree_{i}_t", (0, 0, 0), 0.25 * s, 1.6 * s, M["trunk"], t, base=True, seg_n=6, outline=0.03)
    cyl(f"tree_{i}_c", (0, 0, 1.2 * s), 1.5 * s, 3.6 * s, M["leaf" if i % 2 else "leaf2"], t, base=True, r2=0.0,
        seg_n=7, outline=0.04)
for i, (a, d, r, h) in enumerate(((0.5, 230, 90, 30), (1.4, 260, 120, 42), (2.3, 240, 100, 34), (3.2, 250, 110, 38),
                                 (4.1, 230, 95, 28), (5.0, 260, 120, 40), (5.8, 240, 100, 30))):
    sphere(f"hill_{i}", (math.cos(a) * d, math.sin(a) * d, -h * 0.35), r, M["hill"], scale=(1, 1, h / r),
           seg_u=12, seg_v=8, outline=False, smooth_shade=True)

# ------------------------------------------------------------------ the hut (your house)
hut = K.empty("hut", (0, 1.4, 0))
box("hut_walls", (0, 0, 0), (3.6, 3.4, 2.5), M["plaster"], hut, base=True, outline=0.03)
K.gable("hut_roof", (0, 0, 2.5), 3.6, 3.4, 1.5, M["roof"], hut, overhang=0.3, outline=0.04)
for sx in (-1, 1):
    for sy in (-1, 1):
        box(f"hut_post{sx}{sy}", (sx * 1.78, sy * 1.68, 0), (0.22, 0.22, 2.55), M["wood_d"], hut, base=True, outline=0.02)
box("hut_door", (0.6, -1.72, 0), (0.9, 0.08, 1.7), M["wood_d"], hut, base=True, outline=0.02)
box("hut_win", (-0.8, -1.72, 1.1), (0.7, 0.06, 0.6), M["slit"], hut, outline=0.02)
flagpole = cyl("flagpole", (1.6, -IW - 0.2, IH), 0.05, 3.4, M["wood_d"], base=True, seg_n=8, outline=0.015)
flag = box("flag", (0, 0, 0), (0.02, 1.3, 0.85), M["flag"], outline=0.015)

# ------------------------------------------------------------------ palisade (log ring)
PAL_R = 8.6
NLOG = 72
LOGS = []
for i in range(NLOG):
    a = 2 * math.pi * i / NLOG
    if abs(math.atan2(math.cos(a), -math.sin(a))) < 0.0:   # (no gap: closed ring)
        continue
    e = K.empty(f"log_{i}", (math.cos(a) * PAL_R, math.sin(a) * PAL_R, 0))
    h = 3.4 + 0.25 * math.sin(i * 2.3)
    cyl(f"log_{i}_m", (0, 0, 0), 0.36, h, M["log"], e, base=True, seg_n=7, outline=0.025)
    cyl(f"log_{i}_tip", (0, 0, h), 0.36, 0.55, M["log_end"], e, base=True, r2=0.02, seg_n=7, outline=0.025)
    LOGS.append((e, a))
ASH = []
for i in range(24):
    a = 2 * math.pi * i / 24
    ASH.append(box(f"ash_{i}", (math.cos(a) * PAL_R, math.sin(a) * PAL_R, 0), (2.4, 0.9, 0.12), M["ash"],
                   outline=False))
    ASH[-1].rotation_euler = (0, 0, a + math.pi / 2)

# ------------------------------------------------------------------ outer curtain wall (8 courses)
def wall_side_boxes(c, side):
    """Boxes for course c of one side. Front side has the gate (courses 0-4) and the breach (courses 2-5)."""
    z = c * CH + CH / 2
    L = 2 * W_ + T_
    out = []
    if side == "S":
        cuts = []
        if c < 5:
            cuts.append((-GATE_X, GATE_X))
        if BR_C[0] <= c <= BR_C[1]:
            cuts.append(BR_X)
        xs = [-L / 2]
        for a, b in sorted(cuts):
            xs += [a, b]
        xs.append(W_ - 2.0)          # stop short of the cutaway tower's hollow interior
        for i in range(0, len(xs), 2):
            x0, x1 = xs[i], xs[i + 1]
            out.append((((x0 + x1) / 2, -W_, z), (x1 - x0, T_, CH)))
    elif side == "N":
        out.append(((0, W_, z), (L, T_, CH)))
    elif side == "E":
        y0, y1 = -(W_ - 2.0), W_ - T_ / 2
        out.append(((W_, (y0 + y1) / 2, z), (T_, y1 - y0, CH)))
    else:
        out.append(((-W_, 0, z), (T_, 2 * W_ - T_, CH)))
    return out


COURSES = []
for c in range(NC):
    bxs = []
    for sd in "SNEW":
        bxs += wall_side_boxes(c, sd)
    e = K.empty(f"course_{c}")
    multi_box(f"course_{c}_m", bxs, M["stone"], e, outline=0.03)
    COURSES.append(e)
# merlons along the outer edge
mer = []
for sd in "SNEW":
    for k in range(-5, 6):
        p = k * 1.7
        if (sd == "S" and p > W_ - 2.6) or (sd == "E" and p < -(W_ - 2.6)):
            continue
        if sd == "S":
            mer.append(((p, -OUT + 0.3, H_ + 0.45), (0.95, 0.6, 0.9)))
        elif sd == "N":
            mer.append(((p, OUT - 0.3, H_ + 0.45), (0.95, 0.6, 0.9)))
        elif sd == "E":
            mer.append(((OUT - 0.3, p, H_ + 0.45), (0.6, 0.95, 0.9)))
        else:
            mer.append(((-OUT + 0.3, p, H_ + 0.45), (0.6, 0.95, 0.9)))
MERLONS = K.empty("merlons")
multi_box("merlons_m", mer, M["stone"], MERLONS, outline=0.03)
# breach blocks (fall out when the trebuchet cracks the wall)
BREACH = []
for c in range(BR_C[0], BR_C[1] + 1):
    n = 3 if c % 2 else 4
    w = (BR_X[1] - BR_X[0]) / n
    for k in range(n):
        x = BR_X[0] + (k + 0.5) * w
        b = box(f"breach_{c}_{k}", (x, -W_, c * CH + CH / 2), (w - 0.03, T_ - 0.04, CH - 0.03), M["stone2"],
                outline=0.025)
        BREACH.append((b, Vector(b.location), c, k))
# towers: three solid + the cutaway stair tower (front-right)
TOWERS = []
for sx, sy in ((-1, -1), (-1, 1), (1, 1)):
    e = K.empty(f"tower_{sx}{sy}", (sx * W_, sy * W_, 0))
    cyl(f"tower_{sx}{sy}_m", (0, 0, 0), TOW_R, TOW_H, M["stone"], e, base=True, seg_n=24, outline=0.03)
    for k in range(8):
        a = 2 * math.pi * k / 8
        box(f"tower_{sx}{sy}_mer{k}", (math.cos(a) * (TOW_R - 0.3), math.sin(a) * (TOW_R - 0.3), TOW_H),
            (0.75, 0.75, 0.85), M["stone"], e, base=True, outline=0.02).rotation_euler = (0, 0, a)
    TOWERS.append(e)
ct = K.empty("tower_cut", CUT_T)
CUT_A0, CUT_A1 = 250, 380     # the removable quadrant faces the camera side (+x, -y)
CUT_MAIN = ring_sector("tower_cut_shell", (0, 0, 0), 1.9, TOW_R, TOW_H, CUT_A1 - 360, CUT_A0, M["stone"], ct, n=36, outline=0.03)
for k in range(8):
    a = 2 * math.pi * k / 8
    if CUT_A0 - 360 < math.degrees(a if a <= math.pi else a - 2 * math.pi) < CUT_A1 - 360:
        continue
    box(f"tower_cut_mer{k}", (math.cos(a) * (TOW_R - 0.3), math.sin(a) * (TOW_R - 0.3), TOW_H), (0.75, 0.75, 0.85),
        M["stone"], ct, base=True, outline=0.02).rotation_euler = (0, 0, a)
CUT_PIECE = K.empty("tower_cut_piece", CUT_T)
ring_sector("tower_cut_piece_m", (0, 0, 0), 1.9, TOW_R, TOW_H, CUT_A0, CUT_A1, M["stone"], CUT_PIECE, n=10, outline=0.03)
for a in (D(280), D(337)):
    box(f"tower_cut_piece_mer{a:.2f}", (math.cos(a) * (TOW_R - 0.3), math.sin(a) * (TOW_R - 0.3), TOW_H),
        (0.75, 0.75, 0.85), M["stone"], CUT_PIECE, base=True, outline=0.02).rotation_euler = (0, 0, a)
ring_sector("tower_cut_cap", (0, 0, TOW_H - 0.25), 0.0, 1.9, 0.25, CUT_A1 - 360, CUT_A0, M["stone_plain"], ct, n=20, outline=0.02)
# spiral stair (clockwise going up = angle decreases as z rises)
cyl("newel", (0, 0, 0), 0.32, TOW_H - 0.3, M["stone_plain"], ct, base=True, seg_n=12, outline=0.02)
STEP_H = 0.24
NSTEP = 36
TH0 = 330.0
DTH = -20.0
for i in range(NSTEP):
    a = D(TH0 + DTH * i)
    st = box(f"step_{i}", (0, 0, 0), (1.62, 0.62, 0.16), M["stone_plain"], ct, off=(1.12, 0, 0), outline=0.015)
    st.location = (0, 0, STEP_H * (i + 1) - 0.08)
    st.rotation_euler = (0, 0, a)


def stair_point(u, r=1.15):
    """Point on the stair walking line at step index u (float)."""
    a = D(TH0 + DTH * u)
    return CUT_T + Vector((math.cos(a) * r, math.sin(a) * r, STEP_H * (u + 1)))


# arrow slits (splayed wedges through the wall: wide inside, narrow outside)
def wedge(name, w_in, w_out, depth, h, m, parent=None):
    import bmesh
    bm = bmesh.new()
    vs = []
    for z in (0, h):
        vs += [bm.verts.new((-w_in / 2, 0, z)), bm.verts.new((w_in / 2, 0, z)),
               bm.verts.new((w_out / 2, depth, z)), bm.verts.new((-w_out / 2, depth, z))]
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return K._finish(name, bm, m, parent, (0, 0, 0), 0, False)


SLITS = []
for k, (ang, z) in enumerate(((244, 2.45), (244, 5.6), (30, 2.8), (100, 2.8), (30, 6.2))):
    a = D(ang)
    s = wedge(f"slit_cut{k}", 0.75, 0.13, TOW_R - 1.9 + 0.06, 1.35, M["slit"], ct)
    s.location = (math.cos(a) * 1.87, math.sin(a) * 1.87, z)
    s.rotation_euler = (0, 0, a - math.pi / 2)
    SLITS.append(s)
for t in TOWERS:
    for ang, z in ((225 if t.location.x < 0 and t.location.y < 0 else 0, 3.0), (300, 6.0), (135, 4.5)):
        a = D(ang)
        s = wedge(f"slit_{t.name}_{ang}", 0.75, 0.13, 0.95, 1.35, M["slit"], t)
        s.location = (math.cos(a) * (TOW_R - 0.9), math.sin(a) * (TOW_R - 0.9), z)
        s.rotation_euler = (0, 0, a - math.pi / 2)
        SLITS.append(s)
for k, x in enumerate((-7.2, -2.6, 3.2, 6.2)):
    s = wedge(f"slit_wall{k}", 0.75, 0.13, T_ + 0.04, 1.3, M["slit"])
    s.location = (x, -INN + 0.02, 2.1 if k != 1 else 4.5)
    s.rotation_euler = (0, 0, math.pi)
    SLITS.append(s)

# ------------------------------------------------------------------ gate: drawbridge, chains, portcullis, gatehouse
br_piv = K.empty("bridge_piv", (0, -OUT - 0.05, 0.3))
BR_L = MO_OUT - OUT + 0.9
bridge = multi_box("bridge_m", [((0, -BR_L / 2, -0.15), (3.0, BR_L, 0.3))] +
                   [((x, -BR_L / 2, 0.02), (0.12, BR_L, 0.06)) for x in (-1.2, 1.2)], M["wood"], br_piv, outline=0.025)
for k in range(9):
    box(f"plank_{k}", (0, -0.3 - k * BR_L / 9, 0.01), (3.0, 0.06, 0.04), M["wood_d"], br_piv, outline=False)
CHAINS = [cyl(f"chain_{s}", (0, 0, 0), 0.05, 1.0, M["iron"], base=True, seg_n=6, outline=0.015) for s in (-1, 1)]
port = K.empty("portcullis")
pbx = [((x, 0, 2.05), (0.14, 0.16, 4.1)) for x in (-1.35, -0.9, -0.45, 0, 0.45, 0.9, 1.35)]
pbx += [((0, 0, z), (3.0, 0.16, 0.14)) for z in (0.6, 1.5, 2.4, 3.3)]
multi_box("portcullis_m", pbx, M["wood_d"], port, outline=0.02)
for x in (-1.35, -0.9, -0.45, 0, 0.45, 0.9, 1.35):
    cyl(f"port_spike{x}", (x, 0, -0.25), 0.07, 0.3, M["iron"], port, base=True, r2=0.0, seg_n=6, outline=False)
PORT_Y = -OUT + 0.7
gh = K.empty("gatehouse")
GH_Y0, GH_Y1 = -INN, -5.7
ghb = []
ghb.append((((-GATE_X - 1.0), (GH_Y0 + GH_Y1) / 2, 3.75), (2.0, GH_Y0 - GH_Y1, 7.5)))     # left block (full)
ghb.append((((GATE_X + 1.0), (GH_Y0 + GH_Y1) / 2, 0.55), (2.0, GH_Y0 - GH_Y1, 1.1)))      # right block: cut low
GH_SOLID = multi_box("gatehouse_m", ghb, M["stone"], gh, outline=0.03)
cut_face = box("gatehouse_cutface", (GATE_X + 1.0, (GH_Y0 + GH_Y1) / 2, 1.105), (2.0, GH_Y0 - GH_Y1, 0.01),
               M["cut"], gh, outline=False)
# tunnel roof slab with 3 murder holes (gaps)
HOLES_Y = (-7.3, -6.5)
slab = []
ys = [GH_Y0 - 0.6, HOLES_Y[0] - 0.25, HOLES_Y[0] + 0.25, HOLES_Y[1] - 0.25, HOLES_Y[1] + 0.25, GH_Y1]
for i in range(0, len(ys), 2):
    a, b = ys[i], ys[i + 1]
    slab.append(((0, (a + b) / 2, 4.55), (2 * GATE_X + 0.02, abs(b - a), 0.9)))
for y in HOLES_Y:   # rims beside each hole
    slab.append(((-1.0, y, 4.55), (1.2, 0.5, 0.9)))
    slab.append(((1.0, y, 4.55), (1.2, 0.5, 0.9)))
ROOF = multi_box("gate_roof", slab, M["stone_plain"], gh, outline=0.025)
inner_door = box("inner_door", (0, GH_Y1 + 0.1, 0), (2 * GATE_X, 0.2, 4.1), M["wood_d"], gh, base=True, outline=0.02)

# battering ram + ladders + trebuchet
ram = K.empty("ram")
cyl("ram_log", (0, 0, 0), 0.28, 5.0, M["wood"], ram, axis="Y", seg_n=8, outline=0.025)
cyl("ram_head", (0, 2.6, 0), 0.32, 0.4, M["iron"], ram, axis="Y", seg_n=8, outline=0.02)
LADDERS = []
for k, x in enumerate((-5.0, 4.6)):
    lp = K.empty(f"ladder_{k}")
    Lh = 7.3
    multi_box(f"ladder_{k}_m", [((-0.35, 0, Lh / 2), (0.1, 0.1, Lh)), ((0.35, 0, Lh / 2), (0.1, 0.1, Lh))] +
              [((0, 0, 0.35 + j * 0.42), (0.7, 0.07, 0.07)) for j in range(17)], M["wood"], lp, outline=0.015)
    LADDERS.append((lp, x))
tre = K.empty("trebuchet", (-11.0, -40.0, 0))
TRE_PARTS = []
for nm, c, sz in (("tb_base_l", (-1.4, 0, 0.25), (0.4, 7.0, 0.5)), ("tb_base_r", (1.4, 0, 0.25), (0.4, 7.0, 0.5)),
                  ("tb_cross_a", (0, -3.0, 0.3), (3.2, 0.4, 0.4)), ("tb_cross_b", (0, 3.0, 0.3), (3.2, 0.4, 0.4)),
                  ("tb_up_l", (-1.4, 0, 3.2), (0.35, 0.35, 6.0)), ("tb_up_r", (1.4, 0, 3.2), (0.35, 0.35, 6.0))):
    TRE_PARTS.append(box(nm, c, sz, M["wood"], tre, outline=0.025))
for nm, sy in (("tb_brace_a", -1), ("tb_brace_b", 1)):
    b = box(nm, (0, sy * 1.6, 3.0), (3.0, 0.25, 0.25), M["wood_d"], tre, outline=0.02)
    TRE_PARTS.append(b)
tb_piv = K.empty("tb_pivot", (0, 0, 6.0), tre)
tb_arm = box("tb_arm", (0, 0, 0), (0.3, 11.0, 0.3), M["wood"], tb_piv, off=(0, -2.5, 0), outline=0.025)   # long end -Y (away from the castle)
tb_cw = box("tb_cw", (0, 2.6, -1.2), (1.8, 1.4, 1.6), M["wood_d"], tb_piv, outline=0.025)
TRE_PARTS += [tb_arm, tb_cw]

# ------------------------------------------------------------------ inner (concentric) wall
INNER_C = []
INC = 10
ICH = IH / INC
for c in range(INC):
    z = c * ICH + ICH / 2
    L = 2 * IW + IT
    bx = [((0, IW, z), (L, IT, ICH)), ((IW, 0, z), (IT, 2 * IW - IT, ICH)), ((-IW, 0, z), (IT, 2 * IW - IT, ICH))]
    if c < 4:
        bx += [((-(L / 2 + 1.4) / 2, -IW, z), (L / 2 - 1.4, IT, ICH)), (((L / 2 + 1.4) / 2, -IW, z), (L / 2 - 1.4, IT, ICH))]
    else:
        bx += [((0, -IW, z), (L, IT, ICH))]
    e = K.empty(f"icourse_{c}")
    multi_box(f"icourse_{c}_m", bx, M["stone2"], e, outline=0.03)
    INNER_C.append(e)
imer = []
for k in range(-3, 4):
    p = k * 1.5
    imer += [((p, -IW - IT / 2 + 0.3, IH + 0.45), (0.9, 0.6, 0.9)), ((p, IW + IT / 2 - 0.3, IH + 0.45), (0.9, 0.6, 0.9)),
             ((IW + IT / 2 - 0.3, p, IH + 0.45), (0.6, 0.9, 0.9)), ((-IW - IT / 2 + 0.3, p, IH + 0.45), (0.6, 0.9, 0.9))]
IMER = K.empty("imerlons")
multi_box("imerlons_m", imer, M["stone2"], IMER, outline=0.03)

# ------------------------------------------------------------------ props: torch, letter, particles
torch = K.empty("torch")
cyl("torch_stick", (0, 0, 0), 0.06, 0.9, M["wood_d"], torch, base=True, seg_n=6, outline=0.015)
sphere("torch_fire", (0, 0, 1.0), 0.2, M["flame"], torch, scale=(1, 1, 1.6), outline=False)
letter = K.empty("letter")
box("letter_m", (0, 0, 0), (0.55, 0.75, 0.03), M["paper"], letter, outline=0.012)
cyl("letter_seal", (0, -0.2, 0.03), 0.08, 0.03, M["seal"], letter, seg_n=10, outline=False)

flame_proto = cyl("flame_p", (0, 0, 0), 0.5, 2.0, M["flame"], base=True, r2=0.0, seg_n=6, outline=False)
FLAMES = Swarm("flame", flame_proto, NLOG)
core_proto = cyl("core_p", (0, 0, 0), 0.28, 1.2, M["flame_core"], base=True, r2=0.0, seg_n=6, outline=False)
CORES = Swarm("core", core_proto, NLOG)
smoke_proto = sphere("smoke_p", (0, 0, 0), 0.5, M["smoke"], scale=(1.15, 1.15, 1.0), seg_u=10, seg_v=7, outline=False)
SMOKE = Swarm("smoke", smoke_proto, 18)
rock_proto = sphere("rock_p", (0, 0, 0), 0.16, M["rock"], seg_u=7, seg_v=5, outline=0.01, smooth_shade=False)
ROCKS = Swarm("rock", rock_proto, 14)
drop_proto = sphere("drop_p", (0, 0, 0), 0.07, M["splash"], seg_u=6, seg_v=4, outline=False)
DROPS = Swarm("drop", drop_proto, 40)
arrow_proto = K.empty("arrow_p")
cyl("arrow_p_shaft", (0, 0, 0), 0.025, 0.9, M["arrow"], arrow_proto, axis="Y", seg_n=5, outline=False)
cyl("arrow_p_head", (0, -0.5, 0), 0.0, 0.16, M["iron"], arrow_proto, axis="Y", r2=0.06, seg_n=5, outline=False)
ARROWS = []
for i in range(14):
    a = arrow_proto.copy() if i else arrow_proto
    if i:
        K.link(a)
        for ch in arrow_proto.children:
            c2 = ch.copy()
            K.link(c2)
            c2.parent = a
    ARROWS.append(a)
ball_proto = sphere("ball_p", (0, 0, 0), 0.55, M["rock"], seg_u=10, seg_v=7, outline=0.02, smooth_shade=False)
BALLS = Swarm("ball", ball_proto, 3)
dust_proto = sphere("dust_p", (0, 0, 0), 0.6, M["dust"], seg_u=8, seg_v=6, outline=False)
DUST = Swarm("dust", dust_proto, 30)
dir_proto = cyl("dir_p", (0, 0, 0), 0.16, 0.38, M["arrow_dir"], r2=0.0, axis="Y", seg_n=4, outline=False)
DIRS = Swarm("dir", dir_proto, 9)
spl_proto = sphere("spl_p", (0, 0, 0), 0.18, M["splash"], seg_u=8, seg_v=5, outline=False)
SPLASH = Swarm("spl", spl_proto, 24)

# ------------------------------------------------------------------ cast
YOU = Mannequin("you")
DEF = [Mannequin(f"def{i}") for i in range(3)]
EN = [Mannequin(f"en{i}", tint="red") for i in range(6)]
CAST = [YOU] + DEF + EN
M_BOWSTR = mat("bowstring", (0.92, 0.90, 0.84), rough=0.6)
for m_ in [YOU] + DEF + EN[4:6]:
    m_.add_bow(M["wood_d"], M_BOWSTR)

# ------------------------------------------------------------------ anchors (screen positions for the overlay pass)
K.anchor("palisade", (-5.4, -6.7, 3.3))
K.anchor("fire", (-7.6, -4.2, 3.0))
K.anchor("wall", (-4.6, -OUT, 5.7))
K.anchor("gate_th", (GATE_X, -W_, 3.0))
K.anchor("ladder", (-5.0, -11.6, 3.6))
K.anchor("moat", (5.0, -MID, -0.6))
K.anchor("chain", (1.45, -12.8, 3.2))
K.anchor("bridge", (0.0, -13.0, 0.2))
K.anchor("portcullis", (0.6, PORT_Y, 2.6))
K.anchor("ram", ram, (0.0, 0.0, 0.35))
K.anchor("holes", (0.0, HOLES_Y[1], 5.0))
K.anchor("stones", (0.0, HOLES_Y[0], 2.6))
K.anchor("water_drop", (0.0, HOLES_Y[1], 2.0))
K.anchor("slit_in", CUT_T + Vector((math.cos(D(244)) * 1.85, math.sin(D(244)) * 1.85, 3.1)))
K.anchor("slit_out", CUT_T + Vector((math.cos(D(244)) * 2.85, math.sin(D(244)) * 2.85, 3.1)))
K.anchor("stair", CUT_T + Vector((0.0, -1.1, 4.2)))
K.anchor("trebuchet", (-11.0, -40.0, 9.0))
K.anchor("cweight", (-11.0, -37.4, 4.6))
K.anchor("breach", (-5.0, -OUT, 3.3))
K.anchor("inner", (-IW, -IW, IH + 0.5))
K.anchor("gap", (-4.0, -6.6, 1.6))
K.anchor("letter", letter)
K.anchor("you_head", YOU.neck, (0, 0, 0.2))

# ------------------------------------------------------------------ timeline (seconds; from the narration)
T = {
    "logs0": 0.25, "logs1": 3.4,
    "torch": W("torch", S(3)) - 0.2, "torch_land": W("torch", S(3)) + 0.9,
    "burn_end": E(3) + 0.1, "logs_gone": S(4) + 0.6,
    "wall0": S(4) + 0.2, "wall1": E(4) - 0.4,
    "ladder0": S(6), "ladder1": E(6),
    "dig0": S(7) + 0.3, "dig1": W("flood", S(7)), "flood1": E(7) + 0.6,
    "walk_gate0": S(9), "walk_gate1": S(9) + 1.4,
    "bridge_in": S(10) + 0.2, "bridge_up0": W("swings", S(10)), "bridge_up1": W("swings", S(10)) + 1.0,
    "bridge_down0": E(11) + 0.2, "bridge_down1": E(11) + 1.1,
    "port0": W("drops", S(12)) - 0.3, "port1": W("drops", S(12)) + 0.25,
    "ram0": S(12) + 2.0, "ram_hit1": W("smashed", S(14)) - 0.15, "ram_hit2": W("smashed", S(14)) + 0.55,
    "gh0": S(15) + 0.2, "gh1": W("holes", S(15)),
    "enter0": W("anyone", S(16)) - 1.0, "enter1": W("anyone", S(16)) + 0.8,
    "drop0": W("stones", S(16)), "drop1": E(17),
    "archer0": S(18) - 0.3, "arrows0": W("open", S(18)) - 0.9, "duck": W("open", S(18)),
    "slits0": S(19) + 0.3, "slits1": E(19),
    "cut0": S(20) - 0.4, "cut1": S(20) + 0.3,
    "aim_arrows": W("barely", S(20)) - 0.6,
    "climb0": S(22) + 0.2, "climb1": E(24),
    "safe": S(25), "tre0": W("trebuchet", S(26)) - 0.7, "tre1": W("trebuchet", S(26)) + 0.9,
    "throw1": W("throws", S(26)), "hit1": W("one", S(27)),
    "hit2": W("after", S(27)) + 0.35, "hit3": W("cracks", S(27)),
    "inner0": S(28) + 0.5, "inner1": E(28),
    "swarm0": S(29), "swarm1": W("trapped", S(29)),
    "letter0": W("forged", S(33)) - 0.8, "letter1": W("letter", S(33)) + 0.5,
    "flag0": W("surrender", S(33)) - 0.3, "flag1": E(33) + 0.4,
}
THROWS = [(T["throw1"], T["hit1"]), (T["hit1"] + 0.15, T["hit2"]), (T["hit2"] + 0.1, T["hit3"])]
IMPACT = [Vector((-5.4, -OUT - 0.1, 3.5)), Vector((-4.4, -OUT - 0.1, 2.6)), Vector((-5.0, -OUT - 0.1, 3.2))]

# ------------------------------------------------------------------ camera: ONE continuous move
CAM = K.CamPath([
    (0.0, (-12.0, -22.0, 10.0), (0.0, -1.0, 1.6), 28),
    (S(2), (-12.0, -21.0, 8.8), (-1.0, -2.0, 1.6), 30),
    (T["torch_land"], (-16.5, -16.0, 7.0), (-5.0, -4.5, 1.8), 30),
    (S(4) + 0.6, (-17.0, -23.0, 10.0), (-1.0, -3.0, 2.4), 27),
    (T["wall1"] - 0.6, (4.5, -19.0, 4.4), (0.0, -9.0, 2.6), 30),
    (TERMS["curtain wall"] + 0.2, (-3.0, -28.0, 9.0), (-2.0, -9.0, 3.6), 25),
    (S(6) + 0.8, (9.0, -25.0, 6.5), (-0.5, -10.5, 3.6), 27),
    (S(7) + 0.8, (15.0, -31.0, 13.0), (0.0, -9.0, 0.5), 26),
    (S(8), (13.0, -30.0, 14.0), (0.0, -12.0, -1.0), 24),
    (S(9) + 0.6, (5.0, -23.0, 4.6), (0.0, -9.5, 1.6), 30),
    (S(10) + 1.5, (13.0, -19.0, 6.0), (0.0, -12.5, 2.0), 27),
    (S(12) + 0.6, (6.5, -18.0, 3.8), (0.0, -10.5, 2.2), 30),
    (S(13), (5.0, -16.5, 3.2), (0.0, -10.0, 2.1), 31),
    (S(14) - 0.3, (12.0, -25.0, 5.0), (0.0, -14.0, 1.6), 27),
    (S(15) - 0.2, (8.0, -18.5, 3.4), (0.0, -10.5, 1.8), 28),
    (S(15) + 2.0, (4.5, -15.5, 13.0), (0.0, -7.5, 3.0), 25),
    (S(16) + 0.4, (6.0, -3.0, 9.0), (0.0, -7.4, 2.4), 24),
    (E(17), (5.6, -2.6, 8.4), (0.0, -7.5, 2.6), 25),
    (E(17) + 0.45, (2.0, -6.0, 13.5), (-3.5, -8.6, 6.5), 27),
    (S(18) + 0.3, (-2.0, -16.0, 11.5), (-5.0, -9.0, 7.2), 30),
    (S(19) - 0.1, (-3.2, -17.0, 11.0), (-5.0, -9.0, 7.0), 30),
    (S(19) + 1.5, (5.0, -21.0, 7.5), (8.5, -9.0, 4.0), 27),
    (S(20) + 0.8, (19.0, -21.5, 7.5), (9.2, -9.8, 2.6), 27),
    (E(21), (17.5, -18.5, 5.0), (9.0, -9.6, 2.2), 29),
    (S(23), (17.5, -17.5, 8.5), (9.0, -9.0, 3.8), 29),
    (S(24), (16.5, -17.0, 10.5), (9.0, -9.0, 5.6), 29),
    (S(25) - 0.3, (2.0, -22.0, 12.0), (-1.5, -8.0, 6.0), 27),
    (T["tre0"] + 0.5, (-25.0, -33.0, 8.0), (-11.0, -40.0, 4.5), 26),
    (T["throw1"] - 0.4, (-25.5, -32.0, 8.5), (-10.0, -36.0, 4.8), 25),
    (T["throw1"] + 0.5, (-26.0, -30.0, 9.5), (-7.0, -20.0, 4.5), 23),
    (T["hit2"], (-15.0, -25.0, 7.0), (-4.5, -10.5, 3.2), 26),
    (S(28) + 0.8, (-14.0, -27.0, 16.0), (0.0, -3.0, 4.0), 25),
    (S(29) + 1.0, (-4.5, -12.5, 20.0), (-3.5, -6.6, 0.5), 27),
    (S(30), (-4.0, -18.0, 32.0), (0.0, -2.0, 2.0), 27),
    (S(31) + 1.0, (8.0, -26.0, 20.0), (0.0, -1.0, 3.0), 28),
    (S(33), (4.0, -16.0, 15.0), (0.0, -4.5, 9.0), 28),
    (E(33), (3.5, -13.5, 13.2), (0.4, -4.4, 10.2), 30),
    (spec.DUR, (-17.0, -31.0, 21.0), (0.0, -2.0, 3.0), 28),
], drift=0.05, lens_scale=0.8)


# ------------------------------------------------------------------ animation
def course_drop(e, t, t0, dur=0.45):
    k = seg(t, t0, t0 + dur)
    hide(e, k <= 0)
    e.location.z = 1.6 * (1 - ease_out(k))


def at_wall_top(x, y, z=H_):
    return Vector((x, y, z))


def animate(f):
    t = f / FPS
    CAM.apply(t)

    # ---------------- palisade: logs pop up around the ring, burn, sink to ash
    for i, (e, a) in enumerate(LOGS):
        t_up = T["logs0"] + (T["logs1"] - T["logs0"]) * i / NLOG
        k = ease_out(seg(t, t_up, t_up + 0.35))
        sink = smooth(seg(t, T["burn_end"] - 0.4 + 0.3 * math.sin(i), T["logs_gone"]))
        e.scale = (1, 1, max(0.001, k * (1 - 0.97 * sink)))
        hide(e, k <= 0 or sink >= 1)
    burn = smooth(seg(t, T["torch_land"], T["burn_end"]))
    K.set_color(M["log"], tuple(lerp(c, d, burn) for c, d in zip((0.58, 0.40, 0.24), (0.14, 0.11, 0.09))))
    K.set_color(M["log_end"], tuple(lerp(c, d, burn) for c, d in zip((0.80, 0.64, 0.42), (0.18, 0.13, 0.10))))
    land_a = math.atan2(-5.6, -6.4)

    def fire_k(a):
        d = abs((a - land_a + math.pi) % (2 * math.pi) - math.pi)
        t_on = T["torch_land"] + d / math.pi * 1.4
        return seg(t, t_on, t_on + 0.3) * (1 - seg(t, T["logs_gone"] - 0.9, T["logs_gone"] + 0.2))

    def flame(i, core=False):
        e, a = LOGS[i]
        fk = fire_k(a)
        if fk <= 0:
            return None
        fl = 0.75 + 0.25 * math.sin(t * 17 + i * 1.7) + 0.1 * math.sin(t * 29 + i)
        p = Vector((math.cos(a) * PAL_R, math.sin(a) * PAL_R, 0.3 + 2.4 * e.scale.z))
        s = fk * fl * (0.6 if core else 1.0)
        return (p, (0, 0, math.sin(t * 7 + i) * 0.15), (s, s, s * 1.6))

    FLAMES.drive(lambda i: flame(i))
    CORES.drive(lambda i: flame(i, True))

    def smoke(i):
        R2 = rng(i)
        a = land_a + R2.uniform(-math.pi, math.pi)
        fk = fire_k(a)
        if fk <= 0 and t < T["torch_land"]:
            return None
        per = 2.2
        ph = ((t + R2.uniform(0, per)) % per) / per
        if t > T["logs_gone"] + 1.5:
            return None
        p = Vector((math.cos(a) * PAL_R, math.sin(a) * PAL_R, 3.0 + ph * 6.0)) + Vector((ph * 2.0, ph * 1.0, 0))
        s = (0.5 + ph * 1.6) * min(1, fk * 3 + 0.0) * (1 - ph) ** 0.5
        if s <= 0.02:
            return None
        return (p, (0, 0, 0), s)

    SMOKE.drive(smoke)
    for i, a in enumerate(ASH):
        k = seg(t, T["burn_end"] - 0.2, T["logs_gone"]) * (1 - seg(t, S(4) + 1.6, S(4) + 2.6))
        hide(a, k <= 0)
        a.scale = (1, 1, max(0.01, k))
    # torch flies in from the field
    tk = seg(t, T["torch"], T["torch_land"])
    hide(torch, not (0 < tk < 1))
    if 0 < tk < 1:
        torch.location = ballistic((-15.0, -30.0, 1.6), (-6.4, -5.6, 2.4), 5.0, tk)
        torch.rotation_euler = (D(-40 - 300 * tk), 0, D(20))

    # ---------------- stone wall, towers, merlons
    for c, e in enumerate(COURSES):
        course_drop(e, t, T["wall0"] + (T["wall1"] - T["wall0"] - 0.45) * c / (NC - 1))
    k_t = ease_out(seg(t, T["wall0"], T["wall1"] + 0.3))
    for tw in TOWERS + [ct]:
        tw.scale = (1, 1, max(0.001, k_t))
        hide(tw, k_t <= 0)
    course_drop(MERLONS, t, T["wall1"] - 0.1, 0.4)
    cut_lift = smooth(seg(t, T["cut0"], T["cut1"]))
    CUT_PIECE.scale = (1, 1, max(0.001, k_t))
    CUT_PIECE.location = CUT_T + Vector((1.5, -1.5, 0)) * cut_lift * 0 + Vector((0, 0, 14 * cut_lift))
    hide(CUT_PIECE, k_t <= 0 or cut_lift >= 0.98)
    # breach blocks: in the wall with their course, then knocked inward at the third hit
    for b, home, c, k in BREACH:
        tc = T["wall0"] + (T["wall1"] - T["wall0"] - 0.45) * c / (NC - 1)
        kk = seg(t, tc, tc + 0.45)
        hide(b, kk <= 0)
        p = home.copy()
        p.z += 1.6 * (1 - ease_out(kk))
        fall = seg(t, T["hit3"], T["hit3"] + 1.1)
        if fall > 0:
            R3 = rng(c * 7 + k)
            v = Vector((R3.uniform(-1.5, 1.5), R3.uniform(3.0, 5.5), R3.uniform(1.0, 2.5)))
            tt = fall * 1.1
            p = home + v * tt + Vector((0, 0, -9.8 * tt * tt / 2))
            p.z = max(p.z, CH / 2 - 0.1 + 0.25 * k)
            b.rotation_euler = (R3.uniform(-2, 2) * fall, R3.uniform(-2, 2) * fall, 0)
        else:
            b.rotation_euler = (0, 0, 0)
            if t > T["hit1"]:      # shake on each hit
                sh = sum(pulse(t, h, h + 0.25) for h in (T["hit1"], T["hit2"]))
                p.y += 0.06 * sh * math.sin(t * 60 + k)
        b.location = p

    sk = ease_out(seg(t, T["slits0"], T["slits1"]))
    for i, sl in enumerate(SLITS):
        hide(sl, sk <= 0)
        sl.scale = (max(0.001, sk), 1, max(0.001, sk))

    # ---------------- moat
    for i, e in enumerate(FILL):
        td = T["dig0"] + (T["dig1"] - T["dig0"]) * i / len(FILL)
        k = smooth(seg(t, td, td + 0.6))
        e.scale = (1, 1, max(0.001, 1 - k))
        hide(e, k >= 0.999)
    lvl = smooth(seg(t, T["dig1"] - 0.2, T["flood1"]))
    water.location.z = lerp(-MO_D - 0.2, -0.55, lvl)
    hide(water, lvl <= 0)

    # ---------------- drawbridge + chains
    bk = seg(t, T["bridge_in"], T["bridge_in"] + 0.5)
    hide(br_piv, bk <= 0)
    up = smooth(seg(t, T["bridge_up0"], T["bridge_up1"])) * (1 - smooth(seg(t, T["bridge_down0"], T["bridge_down1"])))
    br_piv.rotation_euler = (D(-88 * up), 0, 0)
    br_piv.scale = (1, max(0.001, ease_out(bk)), 1)
    bpy.context.view_layer.update()
    for s, ch in zip((-1, 1), CHAINS):
        hide(ch, bk < 1)
        tip = br_piv.matrix_world @ Vector((s * 1.35, -BR_L + 0.2, 0.0))
        stick(ch, tip, (s * 1.35, -OUT - 0.05, GATE_Z + 1.5))

    # ---------------- portcullis (drops, shakes under the ram, then is forced up)
    pk = ease_in(seg(t, T["port0"], T["port1"]))
    bounce = 0.12 * pulse(t, T["port1"], T["port1"] + 0.25)
    lift = smooth(seg(t, T["ram_hit2"] + 0.4, T["enter0"] + 0.6))
    port.location = (0.0, PORT_Y, lerp(GATE_Z + 0.2, 0.0, pk) + bounce + 2.9 * lift)
    hit_shake = sum(pulse(t, h, h + 0.3) for h in (T["ram_hit1"], T["ram_hit2"]))
    port.rotation_euler = (D(5 * hit_shake * math.sin(t * 50) + 9 * lift), 0, D(4 * lift))
    hide(port, t < T["port0"])

    # ---------------- gatehouse
    gk = ease_out(seg(t, T["gh0"], T["gh1"]))
    hide(gh, gk <= 0)
    gh.scale = (1, max(0.001, gk), 1)
    gh.location = (0, -INN * (1 - gk) * 0.0, 0)

    # ---------------- ladders
    for k, (lp, x) in enumerate(LADDERS):
        a0 = T["ladder0"] + 0.2 * k
        ap = ease_out(seg(t, a0, a0 + 0.6))
        topple = ease_in(seg(t, T["dig0"] + 0.5 + 0.4 * k, T["dig0"] + 1.6 + 0.4 * k))
        hide(lp, ap <= 0 or t > T["flood1"] + 0.5)
        base = Vector((x, -OUT - 2.4, 0))
        lean = D(20) * ap + D(70) * (1 - ap) - D(80) * topple
        lp.location = base + Vector((0, 0, -2.5 * topple))
        lp.rotation_euler = (-lean, 0, 0)   # +lean tips the top toward the wall (+Y)

    # ---------------- trebuchet build + throws
    for i, p in enumerate(TRE_PARTS):
        tp = T["tre0"] + (T["tre1"] - T["tre0"]) * i / len(TRE_PARTS)
        kk = ease_out(seg(t, tp, tp + 0.4))
        hide(p, kk <= 0)
        p.scale = (1, 1, max(0.001, kk)) if p not in (tb_arm, tb_cw) else (max(0.001, kk),) * 3
    swing = 0.0
    for t0, t1 in THROWS:
        if t0 - 0.35 <= t <= t1 + 0.6:
            swing = max(swing, smooth(seg(t, t0 - 0.35, t0 + 0.1)) * (1 - smooth(seg(t, t1 - 0.2, t1 + 0.5))))
    tb_piv.rotation_euler = (D(lerp(50, -105, swing)), 0, 0)     # cocked: long end down at the back (+50) -> swings up and over toward the castle

    def ball(i):
        t0, t1 = THROWS[i]
        k = seg(t, t0, t1)
        if not (0 < k < 1):
            return None
        p = ballistic(Vector((-11.0, -38.4, 13.8)), IMPACT[i], 7.0, k)
        return (p, (t * 3, t * 2, 0), 1.0)

    BALLS.drive(ball)

    def dust(i):
        h = i // 10
        hits = [T["hit1"], T["hit2"], T["hit3"]]
        k = seg(t, hits[h], hits[h] + 1.4)
        if not (0 < k < 1):
            return None
        R4 = rng(i * 13)
        d = Vector((R4.uniform(-1, 1), R4.uniform(-1.6, -0.3), R4.uniform(-0.2, 1.2)))
        p = IMPACT[h] + d * (0.4 + 2.2 * ease_out(k))
        return (p, (0, 0, 0), (0.4 + 1.2 * k) * (1 - k) ** 0.6)

    DUST.drive(dust)

    # ---------------- inner wall
    for c, e in enumerate(INNER_C):
        course_drop(e, t, T["inner0"] + (T["inner1"] - T["inner0"] - 0.45) * c / (INC - 1), 0.4)
    course_drop(IMER, t, T["inner1"] - 0.1, 0.4)

    # ---------------- letter + white flag
    lk = seg(t, T["letter0"], T["letter1"])
    hide(letter, not (0 < lk) or t > T["flag1"] + 2.5)
    if lk > 0:
        p = ballistic((-7.0, -20.0, 13.0), (-1.2, -IW - 0.6, IH + 1.2), 2.5, ease_out(lk))
        p.x += 0.3 * math.sin(t * 5) * (1 - lk)
        letter.location = p
        letter.rotation_euler = (D(20 * math.sin(t * 4) * (1 - lk)), D(30 * math.sin(t * 3) * (1 - lk)), D(-20 + 30 * lk))
    fk = smooth(seg(t, T["flag0"], T["flag1"]))
    hide(flag, fk <= 0)
    hide(flagpole, fk <= 0)
    flag.location = (1.6, -IW - 0.2 - 0.65, IH + 0.9 + 2.3 * fk)
    flag.rotation_euler = (0, 0, D(6 * math.sin(t * 3)))

    # ---------------- murder-hole stones + water
    def rock(i):
        per = 0.9
        if not (T["drop0"] - 0.3 < t < T["drop1"]):
            return None
        ph = ((t - T["drop0"] + i * per / 14 * 3) % per) / per
        R5 = rng(i)
        p = Vector((R5.uniform(-0.25, 0.25), HOLES_Y[0] + R5.uniform(-0.12, 0.12), 4.2 - 4.4 * ph * ph))
        if p.z < 0.1:
            return None
        return (p, (t * 4 + i, t * 3, 0), 1.0 + 0.4 * R5.random())

    ROCKS.drive(rock)

    def drop(i):
        if not (W("scalding", S(16)) - 0.2 < t < T["drop1"]):
            return None
        per = 0.6
        ph = ((t + i * per / 40 * 7) % per) / per
        R6 = rng(i + 100)
        p = Vector((R6.uniform(-0.3, 0.3), HOLES_Y[1] + R6.uniform(-0.15, 0.15), 4.1 - 4.2 * ph * ph))
        if p.z < 0.05:
            return None
        return (p, (0, 0, 0), (0.8, 0.8, 1.6 + 2.0 * ph))

    DROPS.drive(drop)

    # splash in the moat when ladders + climbers fall
    def splash(i):
        k = seg(t, T["dig0"] + 1.5 + 0.4 * (i % 2), T["dig0"] + 2.6 + 0.4 * (i % 2))
        if not (0 < k < 1) or water.hide_render:
            return None
        R7 = rng(i + 300)
        x = LADDERS[i % 2][1] + R7.uniform(-1.2, 1.2)
        v = Vector((R7.uniform(-1.5, 1.5), R7.uniform(-1.5, 1.5), R7.uniform(3, 6)))
        tt = k * 1.1
        p = Vector((x, -OUT - 2.6, water.location.z)) + v * tt + Vector((0, 0, -9.8 * tt * tt / 2))
        if p.z < water.location.z:
            return None
        return (p, (0, 0, 0), 0.8 * (1 - k))

    SPLASH.drive(splash)

    # ---------------- incoming arrows (archer beat + slit beat + concentric crossfire)
    def place_arrow(a, p0, p1, k, apex=1.5):
        if not (0 < k < 1):
            hide(a, True)
            return
        hide(a, False)
        p = ballistic(p0, p1, apex, k)
        q = ballistic(p0, p1, apex, min(1, k + 0.02))
        a.location = p
        d = (q - p)
        a.rotation_euler = d.to_track_quat("-Y", "Z").to_euler() if d.length > 1e-5 else (0, 0, 0)

    for i, a in enumerate(ARROWS):
        hide(a, True)
        R8 = rng(i + 500)
        if T["arrows0"] < t < S(19):          # at the exposed archer on the wall
            t0 = T["arrows0"] + i * 0.18
            tgt = Vector((-5.0 + R8.uniform(-1.6, 1.6), -9.0 + R8.uniform(-0.6, 1.5), H_ + R8.uniform(0.2, 2.0)))
            place_arrow(a, Vector((-8 + R8.uniform(-6, 6), -40, 1.5)), tgt, seg(t, t0, t0 + 0.9), 3.0)
        elif T["aim_arrows"] < t < E(21) + 0.5:    # bounce off the stone beside the slit
            t0 = T["aim_arrows"] + i * 0.22
            sl = CUT_T + Vector((math.cos(D(244)) * 2.85, math.sin(D(244)) * 2.85, 3.1))
            tgt = sl + Vector((R8.choice((-0.5, 0.5)) * R8.uniform(0.6, 1.0), 0, R8.uniform(-0.6, 0.8)))
            place_arrow(a, Vector((14 + R8.uniform(-5, 5), -40, 2.0)), tgt, seg(t, t0, t0 + 0.8), 2.0)
        elif T["swarm1"] - 0.6 < t < E(30) + 0.3:     # crossfire into the gap
            t0 = T["swarm1"] - 0.6 + (i % 7) * 0.3
            src = Vector((R8.uniform(-6, 2), -IW + 0.3, IH + 1.2)) if i % 2 else Vector((R8.uniform(-7, 3), -W_ - 0.4, H_ + 1.2))
            tgt = Vector((R8.uniform(-7, 0), R8.uniform(-7.4, -5.8), 0.2))
            place_arrow(a, src, tgt, seg(t, t0, t0 + 0.7), 0.6)

    # direction arrows circling the newel (the "clockwise" claim)
    def dirs(i):
        if not (W("clockwise", S(23)) - 0.2 < t < E(23) + 0.3):
            return None
        u = (t * 1.6 + i * 1.0) % 9.0 + 3 * (i % 3)
        a = D(TH0 + DTH * u * 3)
        p = CUT_T + Vector((math.cos(a) * 1.15, math.sin(a) * 1.15, STEP_H * (u * 3 + 1) * 0.5 + 0.9))
        tang = Vector((math.sin(a), -math.cos(a), 0.15))
        if p.z > TOW_H - 0.5:
            return None
        return (p, tang.to_track_quat("Y", "Z").to_euler(), 1.0)

    DIRS.drive(dirs)

    # ---------------- highlights on the key terms
    for o in COURSES + [MERLONS] + TOWERS + [ct]:
        highlight(o, 0)
    for o in INNER_C + [IMER, water, br_piv, port, gh] + SLITS:
        highlight(o, 0)
    for b, *_ in BREACH:
        highlight(b, 0)
    fa = flash_amount(t, TERMS["curtain wall"])
    if fa:
        for o in COURSES + [MERLONS] + [b for b, *_ in BREACH]:
            highlight(o, fa)
    highlight(water, flash_amount(t, TERMS["moat"]) * 0.8)
    highlight(br_piv, flash_amount(t, TERMS["drawbridge"]))
    highlight(port, flash_amount(t, TERMS["portcullis"]))
    highlight(ROOF, flash_amount(t, TERMS["murder holes"]), recursive=False)
    for s in SLITS:
        highlight(s, flash_amount(t, TERMS["arrow slit"]))
    fc = flash_amount(t, TERMS["concentric castle"], hold=1.6)
    if fc:
        for o in INNER_C + [IMER]:
            highlight(o, fc)
        for o in COURSES + [MERLONS] + [b for b, *_ in BREACH]:
            highlight(o, fc * 0.6)

    animate_cast(t)


def animate_cast(t):
    for m in CAST:
        m.hide(True)
        m.pose("stand")
        m.bow_on = False
    # ===== YOU
    you = YOU
    you.set_tint("none")
    you.hide(False)
    home = Vector((1.9, -2.2, 0))
    gate_in = Vector((0.0, -INN - 0.9, 0))
    if t < S(9):
        you.place(home, 0)
        if t < W("torch", S(3)):
            you.face((0, -12, 0))
            you.pose(blend("stand", "look_up", pulse(t, 1.0, 4.0) * 0.6))
        elif t < S(4) + 0.4:
            you.face((-6.4, -5.6, 0))
            k = smooth(seg(t, T["torch_land"] - 0.2, T["torch_land"] + 0.4))
            you.pose(blend("stand", "cower", k))
            you.set_tint("blue", k)
        else:
            you.face((-4, -12, 0))
            k = smooth(seg(t, S(4) + 0.4, S(4) + 1.5))
            you.set_tint("blue", 1 - k)
            you.pose(blend("cower", "look_up", k) if t < S(6) else blend("look_up", "relax", seg(t, S(7), S(7) + 0.8)))
    elif t < S(14) - 0.5:
        k = smooth(seg(t, T["walk_gate0"], T["walk_gate1"]))
        p = home.lerp(gate_in, k)
        you.place(p, 0)
        you.face(gate_in + Vector((0, -5, 0)) if k >= 1 else gate_in)
        if 0 < k < 1:
            you.pose(walk_pose(t * 9.0))
        elif t < S(10):
            you.pose(blend("stand", "shrug", pulse(t, T["walk_gate1"], S(10))))
        else:
            you.pose("stand" if t < S(12) else blend("stand", "point", pulse(t, S(12) + 0.4, E(13))))
    elif t < S(18) - 0.3:
        # on the gatehouse roof, pouring through the murder holes
        you.place((1.15, HOLES_Y[0] + 0.05, 5.0), -90)   # faces -X, toward the hole
        k = smooth(seg(t, T["drop0"] - 0.6, T["drop0"]))
        you.pose(blend("stand", "pour", k))
        hide(you.root, t < T["gh1"])
    elif t < S(20) - 0.4:
        # exposed archer on the front wall
        you.place((-5.0, -W_ + 0.2, H_), 0)
        k = smooth(seg(t, T["duck"] - 0.2, T["duck"] + 0.3))
        you.pose(blend("aim_bow", "duck", k))
        you.bow_on = True
        you.set_tint("blue", k)
    elif t < S(22):
        # inside the cut tower behind the slit, aiming out
        a = D(244)
        u_step = (TH0 - 244) / -DTH                 # the stair step under the slit
        you.place(CUT_T + Vector((math.cos(a) * 1.3, math.sin(a) * 1.3, STEP_H * (round(u_step) + 1))), 0)
        you.face(CUT_T + Vector((math.cos(a) * 6, math.sin(a) * 6, 0)))
        you.pose("aim_bow")
        you.bow_on = True
    elif t < S(25) - 0.2:
        # climbing the spiral stair, clockwise
        u = lerp(0.0, 24.0, smooth(seg(t, T["climb0"], T["climb1"])) * 0.15 + seg(t, T["climb0"], T["climb1"]) * 0.85)
        p = stair_point(u)
        p.z -= 0.08
        you.place(p, 0)
        a = D(TH0 + DTH * u)
        you.root.rotation_euler = (0, 0, a)      # front (-Y) rotated by a = (sin a, -cos a) = the clockwise walking direction
        wp = walk_pose(t * 8.0)
        wp["thL"] = (wp["thL"][0] + 22, 3, 0)
        wp["thR"] = (wp["thR"][0] + 22, 3, 0)
        you.pose(wp if t < E(24) - 0.2 else "stand")
        if t > S(24):
            you.pose(blend(wp, "shrug", smooth(seg(t, S(24), S(24) + 0.6))))
    elif t < S(28):
        you.place((-1.4, -W_ + 0.2, H_), 0)
        hk = smooth(seg(t, T["hit1"] - 0.1, T["hit1"] + 0.3))
        you.pose(blend("relax", "cower", hk))
        if t < T["hit1"]:
            you.set_tint("orange", smooth(seg(t, S(25), S(25) + 0.6)))
        else:
            you.set_tint("blue", hk)
    else:
        # on the inner wall (concentric), later holding the forged letter
        ik = seg(t, T["inner1"] - 0.3, T["inner1"] + 0.1)
        hide(you.root, ik <= 0)
        you.place((-1.2, -IW, IH), 0)
        if t < S(31):
            you.pose(blend("stand", "aim_bow", smooth(seg(t, T["swarm1"] - 0.5, T["swarm1"]))))
            you.bow_on = True
            you.set_tint("orange", 0.6 * smooth(seg(t, S(30), E(30))))
        else:
            hold = smooth(seg(t, T["letter1"] - 0.3, T["letter1"]))
            you.pose(blend("stand", "hold_up", hold * (1 - smooth(seg(t, T["flag0"] + 0.4, T["flag1"])))))
            if t > T["flag0"]:
                you.pose(blend("hold_up", "shrug", smooth(seg(t, T["flag0"] + 0.3, T["flag1"]))))
                you.set_tint("blue", smooth(seg(t, T["flag0"], T["flag1"])) * 0.8)

    # ===== DEFENDERS
    if T["gh1"] < t < S(18) - 0.3:
        d = DEF[0]
        d.hide(False)
        d.place((-1.15, HOLES_Y[1] - 0.05, 5.0), 90)    # faces +X, toward the hole
        d.pose(blend("stand", "pour", smooth(seg(t, W("scalding", S(16)) - 0.6, W("scalding", S(16))))))
    if T["swarm0"] < t:
        for d, p, yaw in ((DEF[0], (2.8, -IW, IH), 0), (DEF[1], (-5.5, -W_ + 0.4, H_), 180),
                          (DEF[2], (2.5, -W_ + 0.4, H_), 180)):
            d.hide(False)
            d.place(p, yaw)
            d.pose(blend("stand", "aim_bow", smooth(seg(t, T["swarm1"] - 0.5, T["swarm1"]))))
            d.bow_on = True
            if t > T["flag0"]:
                d.pose(blend("aim_bow", "stand", smooth(seg(t, T["flag0"], T["flag1"]))))

    # ===== ENEMIES
    if T["torch"] - 1.2 < t < T["torch"] + 1.2:            # torch thrower in the field
        e = EN[0]
        e.hide(False)
        e.place((-15.5, -31.0, 0), 0)
        e.face((-6, -5, 0))
        k = seg(t, T["torch"] - 0.6, T["torch"] + 0.1)
        e.pose(blend("hold_up", "point", smooth(k)))
    if T["ladder0"] < t < T["dig0"] + 2.6:                 # ladder climbers
        for k, (lp, x) in enumerate(LADDERS):
            e = EN[k]
            e.hide(False)
            ap = seg(t, T["ladder0"] + 0.8 + 0.3 * k, T["ladder1"])
            topple = seg(t, T["dig0"] + 0.5 + 0.4 * k, T["dig0"] + 1.8 + 0.4 * k)
            u = 0.1 + 0.55 * ap
            p = Vector((x, -OUT - 2.4 + 2.35 * u - 0.45, 6.9 * u))
            if topple > 0:
                p = p + Vector((0, -4.0 * topple, -6.0 * topple * topple))
                e.place(p, 0, roll_deg=0, pitch_deg=-80 * topple)
                e.pose(blend(climb_pose(t * 6), "fallen", topple))
                hide(e.root, p.z < water.location.z - 0.5)
            else:
                e.place(p, 180)
                e.pose(climb_pose(t * 6 + k))
        e = EN[2]
        e.hide(False)
        e.place((1.0, -OUT - 5.0, 0), 0)
        e.face((0, 0, 0))
        e.pose("point" if t < T["dig0"] + 0.8 else blend("point", "cower", seg(t, T["dig0"] + 0.8, T["dig0"] + 1.3)))
        hide(e.root, t > T["dig0"] + 1.2)
    if T["ram0"] < t < T["enter1"] + 0.1:                   # ram carriers
        k = smooth(seg(t, T["ram0"], T["ram_hit1"]))
        back = pulse(t, T["ram_hit1"] + 0.05, T["ram_hit2"]) * 1.4
        y_tip = lerp(-30.0, PORT_Y - 0.45, k) - back
        hide(ram, False)
        ram.location = (0.0, y_tip - 2.8, 1.25)
        for j in range(4):
            e = EN[j]
            e.hide(False)
            e.place((0.55 * (1 if j % 2 else -1), y_tip - 1.6 - 1.3 * (j // 2), 0), 180)
            e.pose(blend(walk_pose(t * 9 + j), "carry", 0.7) if k < 1 else "push")
    else:
        hide(ram, True)
    if T["enter0"] < t < S(18) - 0.3:                       # stuck in the tunnel under the murder holes
        for j in range(3):
            e = EN[j + 1]
            e.hide(False)
            k = smooth(seg(t, T["enter0"] + 0.2 * j, T["enter1"] + 0.2 * j))
            y = lerp(-14.0 - j, HOLES_Y[0] + 0.6 - 0.75 * j + 0.75, k)
            e.place((0.55 * (j - 1), y, 0), 180)
            hit = smooth(seg(t, T["drop0"] + 0.3 + 0.5 * j, T["drop0"] + 0.9 + 0.5 * j))
            e.pose(blend(walk_pose(t * 8 + j) if k < 1 else "stand", "cower", hit))
            if t > W("scalding", S(16)) + 0.8 + 0.4 * j:
                kk = smooth(seg(t, W("scalding", S(16)) + 0.8 + 0.4 * j, W("scalding", S(16)) + 1.4 + 0.4 * j))
                e.place((0.55 * (j - 1), y, 0.1 * kk), 180, pitch_deg=-80 * kk)
                e.pose(blend("cower", "fallen", kk))
    if S(18) - 1.0 < t < S(19):                             # archers in the field
        for j in range(2):
            e = EN[4 + j]
            e.hide(False)
            e.place((-11.0 + 5 * j, -33.0 + j, 0), 0)
            e.face((-5, -9, 0))
            e.pose("aim_bow")
            e.bow_on = True
    if T["swarm0"] < t:                                     # pour through the breach into the gap
        for j in range(5):
            e = EN[j]
            e.hide(False)
            k = smooth(seg(t, T["swarm0"] + 0.25 * j, T["swarm1"] + 0.25 * j))
            p0 = Vector((-5.0 + 0.6 * (j - 2), -OUT - 1.6, 0))
            pb = Vector((-5.0 + 0.5 * (j - 2), -W_, 1.62))          # climb in through the breach (course 2 sill)
            p1 = Vector((-6.5 + 1.5 * j, -6.6 + 0.35 * (j % 2), 0))
            if k < 0.5:
                p = p0.lerp(pb, k * 2)
                p.z = 1.62 * smooth(seg(k, 0.25, 0.5))
            else:
                p = pb.lerp(p1, (k - 0.5) * 2)
                p.z = 1.62 * (1 - smooth(seg(k, 0.62, 0.8)))
            e.place(p, 0)
            e.face(p1 + Vector((0, 3, 0)) if k >= 1 else p1)
            under_fire = smooth(seg(t, T["swarm1"] + 0.3 * j, T["swarm1"] + 0.6 + 0.3 * j))
            pose = walk_pose(t * 9 + j) if k < 1 else "stand"
            e.pose(blend(pose, "cower", under_fire))
            if t > T["flag0"]:
                e.pose(blend("cower", "cheer", smooth(seg(t, T["flag0"] + 0.1 * j, T["flag1"] + 0.1 * j))))
    for m in CAST:
        m.sync_bow()


K.run(animate, BASE, NF, default_snaps=[30, 120, 230, 380, 470, 600, 740, 900, 1050, 1150, 1300, 1430,
                                        1560, 1700, 1800, 1950, 2050, 2200, 2330, 2450, 2560, 2700, 2900, 3050])
