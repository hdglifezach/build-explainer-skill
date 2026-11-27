"""Build a Roller Coaster -- /build-explainer film #2 (1080x1920, 30 fps, ~103 s).

  blender -b --factory-startup -P build.py -- snaps 45,300,900 [tag] [draft]
  blender -b --factory-startup -P build.py -- render 0 3092

Every frame is a pure function of f. Timing comes from spec.py (narration). Track = bx_kit.TrackPath (dense points
with rotation-minimising frames), carts ride it by arc length using the track's own frame (upside down only inside
the loop). The loop morphs circle -> teardrop with a shape key; carts on the loop interpolate both paths.
"""
import math
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent  # build.py lives in the film folder
sys.path.insert(0, str(BASE))
import bx_kit as K  # noqa: E402
import spec  # noqa: E402
from spec import S, E, W, TERMS  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from bx_kit import (D, box, cyl, sphere, hide, highlight, flash_amount, seg, smooth, ease_out, ease_in, lerp,  # noqa: E402
                    pulse, rng, mat, Swarm, Mannequin, blend, TrackPath, build_reveal, ballistic)

FPS = spec.FPS
NF = spec.NF
DRAFT = "draft" in K.cli_args()
K.setup_scene(res=(1080, 1920), fps=FPS, samples=24, draft=DRAFT, sky=(0.52, 0.70, 0.90),
              horizon=(0.82, 0.86, 0.88), sun_dir=(-38, 6, -50), sun_energy=4.2, sky_strength=1.05)
K.FOG["near"], K.FOG["far"] = 45.0, 260.0


def F(t):
    return int(round(t * FPS))


# ------------------------------------------------------------------ materials
M = {
    "grass": mat("grass", (0.52, 0.66, 0.38), rough=0.95),
    "path": mat("path", (0.80, 0.72, 0.58), rough=0.95),
    "rail": mat("rail", (0.20, 0.52, 0.68), rough=0.35, metal=0.3),
    "rail_lift": mat("rail_lift", (0.20, 0.52, 0.68), rough=0.35, metal=0.3),
    "rail_loop": mat("rail_loop", (0.20, 0.52, 0.68), rough=0.35, metal=0.3),
    "sec1": mat("sec1", (0.20, 0.52, 0.68), rough=0.35, metal=0.3),
    "sec2": mat("sec2", (0.20, 0.52, 0.68), rough=0.35, metal=0.3),
    "support": mat("support", (0.92, 0.91, 0.87), rough=0.7),
    "tie": mat("tie", (0.30, 0.33, 0.36), rough=0.6),
    "wood": mat("wood", (0.62, 0.44, 0.27), rough=0.8),
    "wood_d": mat("wood_d", (0.42, 0.29, 0.18), rough=0.8),
    "cart": mat("cart", (0.86, 0.22, 0.20), rough=0.45),
    "cart2": mat("cart2", (0.95, 0.70, 0.18), rough=0.45),
    "seat": mat("seat", (0.16, 0.16, 0.18), rough=0.6),
    "lapbar": mat("lapbar", (0.95, 0.80, 0.18), rough=0.4),
    "flag1": mat("flag1", (0.95, 0.30, 0.30), rough=0.7),
    "flag2": mat("flag2", (0.98, 0.82, 0.25), rough=0.7),
    "flag3": mat("flag3", (0.30, 0.62, 0.95), rough=0.7),
    "tent1": mat("tent1", (0.95, 0.35, 0.35), rough=0.8),
    "tent2": mat("tent2", (0.97, 0.95, 0.90), rough=0.8),
    "wheelframe": mat("wheelframe", (0.93, 0.93, 0.95), rough=0.5),
    "metal_d": mat("metal_d", (0.30, 0.30, 0.32), rough=0.5, metal=0.4),
    "wheel": mat("wheel", (0.18, 0.18, 0.20), rough=0.5),
    "wheel_hub": mat("wheel_hub", (0.75, 0.76, 0.78), rough=0.3, metal=0.6),
    "steel": mat("steel", (0.62, 0.64, 0.67), rough=0.35, metal=0.6),
    "chain": mat("chain", (0.25, 0.25, 0.27), rough=0.4, metal=0.7),
    "tooth": mat("tooth", (0.78, 0.66, 0.20), rough=0.4, metal=0.5),
    "copper": mat("copper", (0.90, 0.48, 0.22), rough=0.45, metal=0.0),
    "magnet": mat("magnet", (0.20, 0.20, 0.24), rough=0.4),
    "magnet_tip": mat("magnet_tip", (0.85, 0.18, 0.16), rough=0.4),
    "pad": mat("pad", (0.35, 0.30, 0.28), rough=0.8, emit=0.0, emit_col=(1.0, 0.45, 0.10)),
    "spark": mat("spark", (1.0, 0.75, 0.3), emit=3.0, emit_col=(1.0, 0.65, 0.2), fog=False),
    "field": mat("field", (0.45, 0.75, 1.0), emit=2.0, emit_col=(0.45, 0.75, 1.0), fog=False),
    "lamp_r": mat("lamp_r", (1.0, 0.2, 0.15), emit=0.0, emit_col=(1.0, 0.15, 0.1)),
    "lamp_g": mat("lamp_g", (0.2, 0.9, 0.3), emit=0.0, emit_col=(0.2, 1.0, 0.35)),
    "post": mat("post", (0.30, 0.30, 0.32), rough=0.5),
    "roof": mat("roof", (0.92, 0.40, 0.30), rough=0.7),
    "plaster": mat("plaster", (0.95, 0.92, 0.84), rough=0.9),
    "leaf": mat("leaf", (0.36, 0.56, 0.32), rough=0.9),
    "trunk": mat("trunk", (0.40, 0.28, 0.18), rough=0.9),
    "hill": mat("hill", (0.52, 0.62, 0.46), rough=1.0),
    "link_break": mat("link_break", (0.25, 0.25, 0.27), rough=0.4, metal=0.7),
}

# ------------------------------------------------------------------ ground + scenery
box("ground", (30, 4, -0.5), (900, 900, 1.0), M["grass"], outline=False)
box("path_main", (30, 8, 0.01), (110, 3.0, 0.02), M["path"], outline=False)
R = rng(5)
for i in range(60):
    for _ in range(50):
        a = R.uniform(0, 2 * math.pi)
        d = R.uniform(55, 150)
        x, y = 35 + math.cos(a) * d, 5 + math.sin(a) * d
        if y < -30 and abs(x - 35) < 60:
            continue
        break
    s_ = R.uniform(0.9, 1.6)
    t_ = K.empty(f"tree_{i}", (x, y, 0))
    cyl(f"tree_{i}_t", (0, 0, 0), 0.25 * s_, 1.6 * s_, M["trunk"], t_, base=True, seg_n=6, outline=0.03)
    sphere(f"tree_{i}_c", (0, 0, 2.6 * s_), 1.6 * s_, M["leaf"], t_, scale=(1, 1, 1.15), seg_u=8, seg_v=6, outline=0.04,
           smooth_shade=False)
for i, (a, d, r, h) in enumerate(((0.3, 240, 95, 30), (1.2, 260, 120, 40), (2.2, 240, 100, 32), (3.1, 250, 110, 36),
                                 (4.0, 235, 95, 28), (4.9, 260, 120, 42), (5.7, 240, 100, 30))):
    sphere(f"hill_{i}", (35 + math.cos(a) * d, 5 + math.sin(a) * d, -h * 0.35), r, M["hill"], scale=(1, 1, h / r),
           seg_u=12, seg_v=8, outline=False)
# fairground flair (seen behind the opening shot and the wide shots): ferris wheel, striped tents, bunting
fair = K.empty("fair")
FW_C = Vector((62.0, 46.0, 15.0))
fwheel = K.empty("fwheel", FW_C, fair)
K.ring_sector("fw_rim", (0, 0, 0), 12.2, 12.8, 0.35, 0, 360, M["wheelframe"], fwheel, n=48, outline=0.03).rotation_euler = (D(90), 0, 0)
K.ring_sector("fw_rim2", (0, 0, 0), 6.0, 6.4, 0.3, 0, 360, M["wheelframe"], fwheel, n=36, outline=0.02).rotation_euler = (D(90), 0, 0)
CABINS = []
for i in range(12):
    a_ = 2 * math.pi * i / 12
    sp = cyl(f"fw_spoke{i}", (0, 0, 0), 0.09, 12.5, M["wheelframe"], fwheel, base=True, seg_n=6, outline=0.01)
    sp.rotation_euler = (0, a_, 0)
    cab = K.empty(f"fw_cab{i}", (0, 0, 0), fair)
    box(f"fw_cabm{i}", (0, 0, -0.9), (1.4, 1.4, 1.3), (M["flag1"], M["flag2"], M["flag3"])[i % 3], cab, bevel=0.1, outline=0.02)
    CABINS.append((cab, a_))
for sx in (-1, 1):
    for sy in (-1, 1):
        lg = cyl(f"fw_leg{sx}{sy}", (FW_C.x, FW_C.y + sy * 1.2, FW_C.z), 0.25, 16.5, M["wheelframe"], fair, base=True, seg_n=8,
                 outline=0.02)
        lg.rotation_euler = (D(180 + sy * 6), D(sx * 24), 0)
for i, (x, y, r, m_) in enumerate(((28, 38, 4.5, "tent1"), (40, 52, 3.5, "tent2"), (86, 36, 4.0, "tent1"), (14, 50, 3.2, "tent2"),
                                   (98, 50, 3.6, "tent1"))):
    tn = K.empty(f"tent{i}", (x, y, 0), fair)
    for k in range(8):
        a_ = 2 * math.pi * k / 8
        K.ring_sector(f"tent{i}_w{k}", (0, 0, 0), r - 0.05, r, 2.6, math.degrees(a_), math.degrees(a_) + 45,
                      M["tent1"] if k % 2 else M["tent2"], tn, n=4, outline=0.015)
    cyl(f"tent{i}_roof", (0, 0, 2.6), r * 1.08, 2.8, M[m_], tn, base=True, r2=0.05, seg_n=16, outline=0.02)
    cyl(f"tent{i}_pole", (0, 0, 5.3), 0.05, 1.2, M["post"], tn, base=True, seg_n=6, outline=False)
    box(f"tent{i}_flag", (0.3, 0, 6.2), (0.6, 0.03, 0.35), M["flag1"] if i % 2 else M["flag3"], tn, outline=0.006)
for j in range(9):
    x0 = -6 + j * 9
    cyl(f"bpole{j}", (x0, 27.0, 0), 0.07, 4.2, M["post"], fair, base=True, seg_n=6, outline=0.01)
    for k in range(7):
        x = x0 + (k + 0.5) * 9 / 7
        z = 4.0 - 0.5 * math.sin(math.pi * (k + 0.5) / 7)
        cyl(f"bflag{j}_{k}", (x, 27.0, z), 0.24, 0.5, (M["flag1"], M["flag2"], M["flag3"])[(j + k) % 3], fair, axis="Z",
            r2=0.0, seg_n=3, outline=False).rotation_euler = (D(180), 0, 0)

# station
st = K.empty("station")
box("st_platform", (3, -2.4, 0), (10, 2.6, 1.0), M["plaster"], st, base=True, outline=0.03)
for x in (-1.5, 7.5):
    cyl(f"st_post{x}", (x, -3.3, 1.0), 0.12, 3.2, M["post"], st, base=True, seg_n=8, outline=0.02)
K.gable("st_roof", (3, -1.6, 4.2), 11.0, 4.6, 1.2, M["roof"], st, overhang=0.2, outline=0.03)

# ------------------------------------------------------------------ track paths
OUT = TrackPath([(-2, 0, 1.2), (6, 0, 1.2), (10, 0, 1.6), (12.5, 0, 3.0), (23.5, 0, 13.6), (26.5, 0, 14.6),
                 (29.5, 0, 13.8), (37, 0, 2.3), (40, 0, 1.4), (44, 0, 5.2), (46.5, 0, 6.6), (49, 0, 5.2),
                 (53.5, 0, 1.4), (57, 0, 1.2), (59.99, 0, 1.2)], step=0.2)
LX, ZB, LR = 60.0, 1.2, 6.0
LY = 2.6
NLOOP = 241


def loop_pts(k):
    pts = []
    for i in range(NLOOP):
        u = i / (NLOOP - 1)
        ph = 2 * math.pi * u
        y = LY * K.smooth(u)
        circ = Vector((LX + LR * math.sin(ph), y, ZB + LR * (1 - math.cos(ph))))
        hh = LR * 1.22                                    # teardrop: taller, wide gentle bottom, tight top
        wdt = LR * (0.52 + 0.48 * (1 + math.cos(ph)) / 2)
        tear = Vector((LX + wdt * math.sin(ph) * (1.0 + 0.35 * (1 + math.cos(ph)) / 2), y, ZB + hh * (1 - math.cos(ph))))
        pts.append(circ.lerp(tear, k))
    return pts


LOOP0 = TrackPath(loop_pts(0.0), dense=True)
LOOP1 = TrackPath(loop_pts(1.0), dense=True)
BACK = TrackPath([(60.0, LY, 1.2), (66, LY, 1.2), (72, LY, 1.4), (76.5, 4.2, 1.8), (80.0, 7.5, 2.2), (80.5, 10.4, 2.3),
                  (78.5, 13.8, 2.0), (73.5, 16, 1.6), (66, 16, 1.4), (50, 16, 1.3), (35, 16, 1.3), (20, 16, 1.3),
                  (8, 16, 1.3), (1, 15.2, 1.3), (-5.5, 12.8, 1.25), (-8.8, 8.0, 1.2), (-6.5, 2.6, 1.2), (-2.2, 0.15, 1.2),
                  (-2.0, 0.0, 1.2)], step=0.2)
WOOD = TrackPath([(11.5, -11, 9.6), (13.5, -11, 9.5), (24, -11, 1.6), (30, -11, 1.2), (34.5, -11, 3.6), (37, -11, 4.6),
                  (39.5, -11, 3.6), (44, -11, 1.2), (49, -11, 1.2)], step=0.2)

RAILS = ((0.55, 0.0), (-0.55, 0.0), (0.0, -0.5))
RAD = (0.09, 0.09, 0.17)


def nearest_s(path, x):
    best = min(range(len(path.P)), key=lambda i: abs(path.P[i].x - x) + (0 if path.T[i].x * 0 == 0 else 0))
    return path.S[best]


def s_at_x(path, x, lo=0.0, hi=None):
    hi = path.L if hi is None else hi
    idx = [i for i in range(len(path.P)) if lo <= path.S[i] <= hi]
    i = min(idx, key=lambda j: abs(path.P[j].x - x))
    return path.S[i]


S_LIFT0 = s_at_x(OUT, 12.5)
S_LIFT1 = s_at_x(OUT, 23.5)
S_CREST = s_at_x(OUT, 26.5)
S_DROPB = s_at_x(OUT, 40.0)
S_AIR = s_at_x(OUT, 46.5)
S_VALLEY = s_at_x(OUT, 54.5)
B_PADS = s_at_x(BACK, 66.0, 20, 60)
B_MAG0, B_MAG1 = s_at_x(BACK, 58.0, 20, 80), s_at_x(BACK, 46.0, 20, 80)
B_BLOCK = s_at_x(BACK, 40.0, 20, 90)
B_STALL = s_at_x(BACK, 26.0, 20, 100)
B_SEC2 = s_at_x(BACK, 20.0, 20, 100)
B_TURN = s_at_x(BACK, 80.4, 0, 40)

# --- track geometry: segments so each can build / flash on its own
seg_station = OUT.sweep("trk_station", M["rail"], 0, S_LIFT0, RAILS, RAD, outline=False)   # no hull on rails: hulls leave seam rings at joins
seg_lift = OUT.sweep("trk_lift", M["rail_lift"], S_LIFT0, S_CREST, RAILS, RAD, outline=False)   # no hull on rails: hulls leave seam rings at joins
seg_drop = OUT.sweep("trk_drop", M["rail"], S_CREST, OUT.L, RAILS, RAD, outline=False)   # no hull on rails: hulls leave seam rings at joins
ties_out = OUT.ties("ties_out", M["tie"], 0, OUT.L, spacing=1.1)
sup_out = OUT.supports("sup_out", M["support"], 0, OUT.L, spacing=3.5)
# loop with a circle -> teardrop shape key (same topology)
loop_obj = LOOP0.sweep("trk_loop", M["rail_loop"], 0, LOOP0.L, RAILS, RAD, outline=False)   # no hull on rails: hulls leave seam rings at joins
tmp = LOOP1.sweep("trk_loop_tmp", M["rail_loop"], 0, LOOP1.L, RAILS, RAD, outline=False)
loop_obj.shape_key_add(name="Basis")
sk = loop_obj.shape_key_add(name="tear")
for i, v in enumerate(tmp.data.vertices):
    sk.data[i].co = v.co
bpy.data.objects.remove(tmp)
LOOP_KEY = loop_obj.data.shape_keys.key_blocks["tear"]


def loop_ties(path, name):
    bm = bmesh.new()
    for i in range(0, NLOOP, 6):
        p, t, u = path.P[i], path.T[i], path.U[i]
        b = t.cross(u)
        c = p + u * -0.12
        vs = [bm.verts.new(c + b * sx * 0.65 + t * st_ * 0.06 + u * su * 0.07)
              for sx in (-1, 1) for st_ in (-1, 1) for su in (-1, 1)]
        for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            bm.faces.new([vs[j] for j in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


bm0 = loop_ties(LOOP0, "lt0")
me = bpy.data.meshes.new("loop_ties")
bm0.to_mesh(me)
bm0.free()
loop_ties_obj = bpy.data.objects.new("loop_ties", me)
K.link(loop_ties_obj)
me.materials.append(M["tie"])
loop_ties_obj.shape_key_add(name="Basis")
sk2 = loop_ties_obj.shape_key_add(name="tear")
bm1 = loop_ties(LOOP1, "lt1")
for i, v in enumerate(bm1.verts):
    sk2.data[i].co = v.co
bm1.free()
LOOP_TIE_KEY = loop_ties_obj.data.shape_keys.key_blocks["tear"]
# loop legs (A-frames at the bottom so it does not float)
for sx in (-1, 1):
    cyl(f"loop_leg{sx}", (LX + sx * 1.5, LY / 2, 0), 0.16, 0.8, M["support"], base=True, seg_n=8, outline=0.02)

# back leg: sections 1 (loop exit -> block brake at x 40) and 2 (x 40 -> station)
seg_back1 = BACK.sweep("trk_back1", M["sec1"], 0, B_BLOCK, RAILS, RAD, outline=False)   # no hull on rails: hulls leave seam rings at joins
seg_back2 = BACK.sweep("trk_back2", M["sec2"], B_BLOCK, BACK.L, RAILS, RAD, outline=False)   # no hull on rails: hulls leave seam rings at joins
ties_back = BACK.ties("ties_back", M["tie"], 0, BACK.L, spacing=1.1)
sup_back = BACK.supports("sup_back", M["support"], 0, BACK.L, spacing=3.5)

# wooden ramp (lines 1-2)
wood = K.empty("woodramp")
WOOD.sweep("wood_rails", M["wood"], 0, WOOD.L, ((0.55, 0.0), (-0.55, 0.0)), (0.1, 0.1), parent=wood, outline=0.02)
WOOD.ties("wood_ties", M["wood_d"], 0, WOOD.L, spacing=0.6, width=1.5, size=(0.25, 0.1), parent=wood)
WOOD.supports("wood_sup", M["wood_d"], 0, WOOD.L, spacing=2.2, r=0.14, min_z=0.6, down=0.1, parent=wood)
box("wood_deck", (11.2, -11, 9.25), (2.6, 2.4, 0.2), M["wood"], wood, base=True, outline=0.02)
for sx in (-1, 1):
    for sy in (-1, 1):
        cyl(f"wood_leg{sx}{sy}", (11.2 + sx * 1.1, -11 + sy * 1.0, 0), 0.12, 9.3, M["wood_d"], wood, base=True, seg_n=6,
            outline=0.015)
for z in (3.0, 6.0):
    box(f"wood_brace{z}", (11.2, -12.0, z), (2.3, 0.1, 0.12), M["wood_d"], wood, outline=0.01)
    box(f"wood_brace2{z}", (11.2, -10.0, z), (2.3, 0.1, 0.12), M["wood_d"], wood, outline=0.01)

# ratchet (anti-rollback) strip along the lift: saw teeth between the rails
TOOTH = 0.32
bm = bmesh.new()
s_ = S_LIFT0 + 0.3
while s_ < S_CREST - 0.5:
    p, t, u, b = OUT.frame(s_)
    base = p + u * -0.16
    v = [bm.verts.new(base + b * sx * 0.09 + t * tt + u * uu)
         for sx in (-1, 1) for (tt, uu) in ((0, 0), (TOOTH * 0.95, 0), (TOOTH * 0.95, 0.13))]
    bm.faces.new((v[0], v[1], v[2]))
    bm.faces.new((v[5], v[4], v[3]))
    bm.faces.new((v[0], v[3], v[4], v[1]))
    bm.faces.new((v[1], v[4], v[5], v[2]))
    bm.faces.new((v[2], v[5], v[3], v[0]))
    s_ += TOOTH
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
ratchet = K._finish("ratchet", bm, M["tooth"], None, (0, 0, 0), 0, 0.006)

# chain links (swarm along the lift centreline)
link_proto = box("link_p", (0, 0, 0), (0.08, 0.22, 0.06), M["chain"], outline=False)
NLINK = 70
LINKS = Swarm("link", link_proto, NLINK)

# magnets (return leg, x 58 -> 46) and friction pads (x 67 -> 65), block clamp at x 40, signals
mag = K.empty("magnets")
bm = bmesh.new()
s_ = B_MAG0
while s_ < B_MAG1:
    p, t, u, b = BACK.frame(s_)
    for sx in (-1, 1):
        c = p + u * -0.24 + b * sx * 0.12
        r_ = bmesh.ops.create_cube(bm, size=1.0)
        for vv in r_["verts"]:
            lc = vv.co.copy()
            vv.co = c + b * lc.x * 0.12 + t * lc.y * 0.45 + u * lc.z * 0.22
    s_ += 0.6
magnets = K._finish("magnets_m", bm, M["magnet"], mag, (0, 0, 0), 0, 0.01)
PADS = []
PADS_MOUNTS = []
for sx in (-1, 1):
    p, t, u, b = BACK.frame(B_PADS)
    pd = box(f"pad{sx}", (0, 0, 0), (0.14, 1.6, 0.26), M["pad"], outline=0.012)
    pd.matrix_world = Matrix.Translation(p + u * 0.55 + b * sx * 0.92) @ BACK.matrix(B_PADS).to_3x3().to_4x4()
    for dy in (-0.6, 0.6):    # mounts down to the ties so the pads do not float
        mt = box(f"padmount{sx}{dy}", (0, 0, 0), (0.08, 0.08, 0.75), M["steel"], outline=0.008)
        mt.matrix_world = Matrix.Translation(p + u * 0.2 + b * sx * 0.92 + t * dy) @ BACK.matrix(B_PADS).to_3x3().to_4x4()
        PADS_MOUNTS.append(mt)
    PADS.append((pd, sx))
p, t, u, b = BACK.frame(B_BLOCK)
CLAMPS = []
for sx in (-1, 1):
    c_ = box(f"clamp{sx}", (0, 0, 0), (0.12, 1.2, 0.24), M["steel"], outline=0.012)
    CLAMPS.append((c_, sx, p + u * -0.25, b, BACK.matrix(B_BLOCK).to_3x3().to_4x4()))
SIGNALS = []
for name, sb in (("sig1", B_BLOCK), ("sig2", B_SEC2)):
    p, t, u, b = BACK.frame(sb)
    base = Vector((p.x, p.y + 1.6, 0))
    e = K.empty(name, base)
    cyl(f"{name}_pole", (0, 0, 0), 0.07, 3.0, M["post"], e, base=True, seg_n=8, outline=0.015)
    box(f"{name}_box", (0, 0, 3.0), (0.4, 0.3, 0.9), M["post"], e, outline=0.015)
    sphere(f"{name}_r", (0, -0.17, 3.25), 0.12, M["lamp_r"], e, outline=False)
    sphere(f"{name}_g", (0, -0.17, 2.85), 0.12, M["lamp_g"], e, outline=False)
    SIGNALS.append(e)

# particles
spark_proto = sphere("spark_p", (0, 0, 0), 0.05, M["spark"], seg_u=6, seg_v=4, outline=False)
SPARKS = Swarm("spark", spark_proto, 30)
field_proto = cyl("field_p", (0, 0, 0), 0.025, 0.4, M["field"], axis="Y", seg_n=5, outline=False)
FIELD = Swarm("field", field_proto, 24)
heat_proto = sphere("heat_p", (0, 0, 0), 0.06, M["spark"], seg_u=6, seg_v=4, outline=False)
HEAT = Swarm("heat", heat_proto, 12)


# ------------------------------------------------------------------ carts
def make_cart(name, body_mat, wheels_full=True):
    c = K.empty(name)
    # hollow tub: floor + four walls, so the seated rider sits INSIDE it (no clipping)
    box(f"{name}_floor", (0, 0, 0.36), (1.25, 1.9, 0.1), body_mat, c, bevel=0.02, outline=0.02)
    for sx in (-1, 1):
        box(f"{name}_side{sx}", (sx * 0.585, 0, 0.7), (0.08, 1.9, 0.62), body_mat, c, bevel=0.03, outline=0.02)
        box(f"{name}_trim{sx}", (sx * 0.63, 0, 0.62), (0.02, 1.7, 0.08), M["steel"], c, outline=0.006)
    box(f"{name}_front", (0, -0.91, 0.7), (1.25, 0.08, 0.62), body_mat, c, bevel=0.03, outline=0.02)
    box(f"{name}_rear", (0, 0.91, 0.75), (1.25, 0.08, 0.72), body_mat, c, bevel=0.03, outline=0.02)
    box(f"{name}_nose", (0, -1.1, 0.6), (1.15, 0.35, 0.42), body_mat, c, bevel=0.08, outline=0.02)
    sphere(f"{name}_lamp", (0, -1.28, 0.66), 0.07, M["wheel_hub"], c, outline=0.006)
    box(f"{name}_seat", (0, 0.42, 0.78), (1.0, 0.7, 0.14), M["seat"], c, bevel=0.03, outline=0.015)
    box(f"{name}_back", (0, 0.8, 1.12), (1.0, 0.14, 0.62), M["seat"], c, bevel=0.03, outline=0.015)
    box(f"{name}_head", (0, 0.82, 1.5), (0.4, 0.12, 0.26), M["seat"], c, bevel=0.03, outline=0.01)
    lap = K.empty(f"{name}_lappiv", (0, 0.2, 1.08), c)          # lap bar pivots at the sides of the seat front
    for sx in (-1, 1):
        box(f"{name}_laparm{sx}", (sx * 0.5, 0, 0), (0.06, 0.06, 0.05), M["steel"], lap, off=(0, -0.2, 0.05), outline=0.006)
        box(f"{name}_laparm2{sx}", (sx * 0.5, -0.4, 0.05), (0.05, 0.05, 0.05), M["steel"], lap, outline=0.006)
    cyl(f"{name}_lapbar", (0, -0.42, 0.06), 0.045, 1.0, M["lapbar"], lap, axis="X", seg_n=10, outline=0.008)
    box(f"{name}_chassis", (0, 0, 0.32), (1.3, 1.5, 0.12), M["steel"], c, outline=0.015)
    parts = {"road": [], "up": [], "guide": [], "brk": []}
    for sx in (-1, 1):
        for sy in (-1, 1):
            w = cyl(f"{name}_road{sx}{sy}", (sx * 0.55, sy * 0.55, 0.22), 0.13, 0.12, M["wheel"], c, axis="X",
                    seg_n=14, outline=0.01)
            parts["road"].append(w)
            ue = K.empty(f"{name}_upg{sx}{sy}", (sx * 0.55, sy * 0.55, 0), c)
            box(f"{name}_brk{sx}{sy}", (sx * 0.2, 0, 0.05), (0.07, 0.2, 0.5), M["steel"], ue, outline=0.008)
            cyl(f"{name}_up{sx}{sy}", (0, 0, -0.18), 0.09, 0.1, M["wheel_hub"], ue, axis="X", seg_n=12, outline=0.008)
            parts["up"].append(ue)
            ge = K.empty(f"{name}_gdg{sx}{sy}", (sx * 0.37, sy * 0.55, 0.0), c)
            cyl(f"{name}_gd{sx}{sy}", (0, 0, 0), 0.09, 0.08, M["wheel_hub"], ge, seg_n=12, outline=0.008)
            box(f"{name}_gdb{sx}{sy}", (0, 0, 0.17), (0.06, 0.12, 0.26), M["steel"], ge, outline=0.006)
            parts["guide"].append(ge)
    fin = box(f"{name}_fin", (0, 0, -0.24), (0.04, 1.3, 0.3), M["copper"], c, outline=0.008)
    latch_piv = K.empty(f"{name}_latchpiv", (0, 0.45, 0.22), c)
    box(f"{name}_latch", (0, 0, 0), (0.08, 0.42, 0.05), M["steel"], latch_piv, off=(0, 0.2, 0), outline=0.008)
    return c, parts, fin, latch_piv


CA, PA, FIN_A, LATCH_A = make_cart("cartA", M["cart"])
CB, PB, FIN_B, LATCH_B = make_cart("cartB", M["cart2"])
CW = K.empty("cartW")                    # the wooden cart for the ramp beat
box("cw_floor", (0, 0, 0.38), (1.2, 1.8, 0.1), M["wood_d"], CW, outline=0.02)
for sx in (-1, 1):
    for k in range(3):                       # plank sides
        box(f"cw_plank{sx}{k}", (sx * 0.57, 0, 0.5 + k * 0.15), (0.07, 1.8, 0.13), M["wood"], CW, bevel=0.015, outline=0.012)
    for sy in (-1, 1):                       # iron corner brackets
        box(f"cw_brk{sx}{sy}", (sx * 0.6, sy * 0.86, 0.62), (0.04, 0.1, 0.46), M["metal_d"], CW, outline=0.006)
for sy in (-1, 1):
    for k in range(3):
        box(f"cw_plankf{sy}{k}", (0, sy * 0.87, 0.5 + k * 0.15), (1.2, 0.07, 0.13), M["wood"], CW, bevel=0.015, outline=0.012)
box("cw_bumper", (0, -0.97, 0.42), (1.0, 0.1, 0.12), M["metal_d"], CW, outline=0.008)
box("cw_seat", (0, 0.42, 0.78), (1.0, 0.6, 0.12), M["wood_d"], CW, outline=0.015)
box("cw_back", (0, 0.78, 1.08), (1.0, 0.1, 0.5), M["wood_d"], CW, outline=0.012)
for sx in (-1, 1):
    for sy in (-1, 1):
        cyl(f"cw_wh{sx}{sy}", (sx * 0.55, sy * 0.6, 0.2), 0.16, 0.1, M["wood_d"], CW, axis="X", seg_n=10, outline=0.01)
        cyl(f"cw_hub{sx}{sy}", (sx * 0.61, sy * 0.6, 0.2), 0.06, 0.04, M["metal_d"], CW, axis="X", seg_n=8, outline=False)

YOU = Mannequin("you")
RIDER2 = Mannequin("rider2")
CROWD = [Mannequin(f"crowd{i}", tint=("none", "none", "orange", "none", "blue", "none")[i]) for i in range(6)]
FF_RIDER = Mannequin("ffrider")
SEATED = {"thL": (90, 6, 0), "knL": 85, "thR": (90, 6, 0), "knR": 85, "hipz": -0.47,
          "shL": (55, 8, 0), "elL": 30, "shR": (55, 8, 0), "elR": 30}

# Flip Flap (1895) mini circular loop for the payoff
FFX, FFY = 64.0, -15.0
ff = K.empty("flipflap")
FFP = TrackPath([(FFX - 9, FFY, 1.0)] + [(FFX + 3.2 * math.sin(2 * math.pi * i / 80), FFY,
                                          1.0 + 3.2 * (1 - math.cos(2 * math.pi * i / 80))) for i in range(81)]
                + [(FFX + 9, FFY, 1.0)], step=0.15)
FFP.sweep("ff_rails", M["wood"], 0, FFP.L, ((0.45, 0.0), (-0.45, 0.0)), (0.08, 0.08), parent=ff, outline=0.015)
FFP.ties("ff_ties", M["wood_d"], 0, FFP.L, spacing=0.5, width=1.2, size=(0.15, 0.1), parent=ff)
for sx in (-1, 1):
    for x in (FFX - 3.6, FFX + 3.6):
        cyl(f"ff_leg{sx}{x}", (x, FFY + sx * 0.9, 0), 0.1, 8.1, M["wood_d"], ff, base=True, seg_n=6, outline=0.012)
box("ff_beam", (FFX, FFY, 8.2), (8.0, 2.0, 0.2), M["wood_d"], ff, outline=0.015)    # clears the loop top (7.4 m)
FFC = K.empty("ff_cart")
box("ffc_body", (0, 0, 0.45), (1.0, 1.4, 0.4), M["cart2"], FFC, bevel=0.04, outline=0.015)

# ------------------------------------------------------------------ anchors
K.anchor("ramp", (17.5, -11, 6.0))
K.anchor("wood_cart", CW, (0, 0, 0.3))
K.anchor("chain", OUT.frame(S_LIFT0 + 6)[0])
K.anchor("lift", OUT.frame((S_LIFT0 + S_LIFT1) / 2)[0] + Vector((0, 0, 0.4)))
K.anchor("chain_break", OUT.frame(S_LIFT0 + 8.5)[0])
K.anchor("ratchet", OUT.frame(S_LIFT0 + 5.0)[0] + Vector((0, 0, -0.1)))
K.anchor("latch", LATCH_A, (0, 0.25, 0))
K.anchor("w_road", PA["road"][0])
K.anchor("w_up", PA["up"][0], (0, 0, -0.18))
K.anchor("w_guide", PA["guide"][0])
loop_top = K.empty("loop_top_anchor")
K.anchor("loop_top", loop_top)
K.anchor("pads", PADS[0][0])
K.anchor("fin", FIN_A, (0, 0, -0.1))
K.anchor("magnets", BACK.frame((B_MAG0 + B_MAG1) / 2)[0])
K.anchor("trainA", CA, (0, 0, 1.8))
K.anchor("clamp", BACK.frame(B_BLOCK)[0])


# ------------------------------------------------------------------ helpers
def route(s, k):
    """Frame on OUT + LOOP(k) + BACK at route arc length s. Returns (pos, T, U)."""
    Lk = lerp(LOOP0.L, LOOP1.L, k)
    if s <= OUT.L:
        p, t, u, b = OUT.frame(s)
        return p, t, u
    s -= OUT.L
    if s <= Lk:
        uu = s / Lk
        fa = LOOP0.frame(uu * LOOP0.L)
        fb = LOOP1.frame(uu * LOOP1.L)
        p = fa[0].lerp(fb[0], k)
        t = fa[1].lerp(fb[1], k).normalized()
        u = fa[2].lerp(fb[2], k)
        u = (u - t * u.dot(t)).normalized()
        return p, t, u
    p, t, u, b = BACK.frame(s - Lk)
    return p, t, u


def place_on(obj, frame, lift=0.0):
    p, t, u = frame
    y = -t
    z = u
    x = y.cross(z)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = p + u * lift
    obj.matrix_world = m


def sched(t, keys):
    """keys = [(t, value, ease)] ease of the segment ending at that key: 'l' linear, 'i' in, 'o' out, 's' smooth."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0, _), (t1, v1, e) in zip(keys, keys[1:]):
        if t <= t1:
            u = seg(t, t0, t1)
            u = {"l": u, "i": ease_in(u), "o": ease_out(u), "s": smooth(u)}[e]
            return lerp(v0, v1, u)
    return keys[-1][1]


def seat(m, cart, pose=None):
    m.hide(False)
    m.root.parent = cart
    m.root.location = (0, 0.32, 0.37)
    m.root.rotation_euler = (0, 0, 0)
    m.pose(pose or SEATED)


L_OUT = OUT.L


def k_loop(t):
    return smooth(seg(t, S(14) + 0.5, E(14) - 0.6))


def LK(t):
    return lerp(LOOP0.L, LOOP1.L, k_loop(t))


# timeline (seconds)
T = {
    "wood_build1": 2.8, "roll0": W("friction", S(2)) - 0.3, "stop": W("halfway", S(2)) + 0.3, "back": E(2),
    "wood_out0": S(3) - 0.1, "wood_out1": S(3) + 0.8,
    "steel0": S(3) - 0.2, "steel1": S(3) + 2.2,
    "climb0": W("chain", S(3)), "crest": E(4) - 1.6,
    "snap": W("snaps", S(5)),
    "strip0": W("strip", S(6)) - 0.4, "strip1": W("strip", S(6)) + 0.8,
    "latch0": W("latch", S(6)) - 0.3, "latch1": W("latch", S(6)) + 0.3,
    "slip0": W("rolling", S(7)) - 0.1, "catch": W("catches", S(7)),
    "air_up": W("lifts", S(9)) - 0.3, "air_dn": E(9) + 0.1,
    "wheels0": W("under", S(10)) - 0.3, "wheels1": W("beside", S(10)) + 0.4,
    "loop_b0": S(12) + 0.5, "loop_b1": E(12) - 0.2,
    "pads": W("pads", S(16)),
    "fin0": W("fins", S(17)) - 0.3,
    "stall": W("stalls", S(20)),
    "rewind0": S(21), "rewind1": S(21) + 1.2,
    "ff0": S(23) - 0.6, "ff1": S(23) + 1.6,
    "end0": S(25) + 0.2, "end1": spec.DUR - 0.2,
}


def cart_A_s(t):
    """Route arc length of cart A (only valid for t >= steel phase)."""
    k = k_loop(t)
    lk = LK(t)
    climb_mid = S_LIFT0 + 9.0
    if t < T["crest"]:
        return sched(t, [(S(3) + 0.6, 3.0, "l"), (T["climb0"] + 0.2, S_LIFT0 - 0.5, "s"),
                         (T["crest"], S_CREST, "l")])
    if t < S(5) - 0.15:
        return sched(t, [(T["crest"], S_CREST, "l"), (S(5) - 0.15, S_DROPB + 4, "i")])
    if t < S(6):
        sl = climb_mid - 3.0 + 3.0 * seg(t, S(5), T["snap"])
        if t > T["snap"]:
            sl = climb_mid - 2.6 * ease_in(seg(t, T["snap"], S(6) + 0.2))
        return sl
    if t < S(7):
        return sched(t, [(S(6), climb_mid - 2.6, "l"), (T["latch1"] + 0.3, climb_mid - 2.6, "l"), (S(7), climb_mid - 1.0, "l")])
    if t < S(8):
        s0 = climb_mid - 1.0 + 1.2 * seg(t, S(7), T["slip0"])
        slip = 0.27 * smooth(seg(t, T["slip0"], T["catch"]))
        bounce = 0.04 * pulse(t, T["catch"], T["catch"] + 0.25)
        return s0 - slip + bounce
    if t < S(9):
        return sched(t, [(S(8), climb_mid - 0.07, "l"), (E(8) + 0.25, S_CREST, "s")])
    if t < S(12):
        return sched(t, [(S(9), S_CREST, "l"), (W("over", S(9)) + 0.6, S_DROPB, "i"),
                         (T["air_up"] + 0.5, S_AIR, "l"), (T["air_dn"] - 0.3, S_AIR + 1.0, "o")])
    if t < S(13):
        return sched(t, [(S(12), S_AIR + 1.0, "l"), (E(12), S_VALLEY - 1.0, "s")])
    if t < S(14) + 0.4:
        return sched(t, [(S(13), S_VALLEY - 1.0, "l"), (S(13) + 0.6, S_VALLEY + 2.0, "i"),
                         (W("bottom", S(13)) + 0.2, L_OUT + LOOP0.L + 1.5, "l"),
                         (W("six", S(13)), L_OUT + LOOP0.L + 4.0, "o")])
    # out of the loop to the turnaround, waits; then the fast return through the brakes
    base = L_OUT + lk
    if t < S(16):
        return base + sched(t, [(S(14) + 0.4, LOOP0.L + 4.0 - lk, "l"), (S(14) + 2.0, B_TURN, "s")])
    if t < S(19):
        return base + sched(t, [(S(16), B_TURN, "l"), (T["pads"] - 0.3, B_PADS - 0.8, "i"),
                                (W("overheat", S(16)) + 0.5, B_PADS + 6.0, "l"),
                                (S(17) + 1.5, B_MAG0 + 1.0, "l"), (E(17) - 0.2, B_MAG1 - 0.5, "o"),
                                (S(19), B_MAG1, "l")])
    return base + sched(t, [(S(19), B_MAG1, "l"), (T["stall"] - 0.6, B_STALL, "s")])


def cart_B_s(t):
    """Cart B: the teardrop pass (line 15) and the second train (lines 20-22)."""
    lk = LK(t)
    if t < S(20) - 0.5:
        return sched(t, [(E(14) - 0.8, S_VALLEY - 6, "l"), (S(15) - 0.1, S_VALLEY + 1.0, "i"),
                         (E(15) + 0.2, L_OUT + lk + 3.0, "l"), (E(15) + 0.9, L_OUT + lk + 5.0, "o")])
    base = L_OUT + lk
    return base + sched(t, [(S(20) - 0.5, B_MAG0 - 6, "l"), (E(20) - 0.1, B_STALL - 4.2, "o"),
                            (T["rewind0"] + 0.1, B_STALL - 4.2, "l"), (T["rewind1"], B_BLOCK - 1.1, "s")])


# ------------------------------------------------------------------ camera
def P(path, s, off=(0, 0, 0)):
    return tuple(path.frame(s)[0] + Vector(off))


LIFTMID = OUT.frame(S_LIFT0 + 9.0)[0]
CL = OUT.frame(S_LIFT0 + 6.6)[0]                    # where cart A sits during the latch close-up
_pa, _ta, _ua, _ba = OUT.frame(S_AIR + 1.0)
CW_ = _pa + _ta * 0.55 - _ba * 0.55 * 0 + Vector((0, -0.55, 0.15))   # front, camera-side wheel corner
CAM = K.CamPath([
    (0.0, (-3.0, -30.0, 14.0), (22.0, -10.0, 4.5), 24),
    (S(2) + 0.8, (18.0, -27.0, 8.0), (33.0, -11.0, 3.0), 26),
    (E(2), (12.0, -29.0, 10.0), (28.0, -11.0, 3.5), 25),
    (S(3) + 0.6, (4.0, -26.0, 12.0), (20.0, 0.0, 6.0), 26),
    (S(4) - 0.5, (12.0, -24.0, 16.0), (26.0, 0.0, 10.0), 26),
    (E(4), (18.0, -22.0, 13.0), (32.0, 0.0, 7.0), 26),
    (S(5) + 0.5, (LIFTMID.x - 1.0, -12.0, LIFTMID.z + 1.0), tuple(LIFTMID), 28),
    (S(6) + 2.0, (CL.x - 1.8, -6.6, CL.z - 1.4), tuple(CL + Vector((0, 0, -0.1))), 30),
    (S(7) + 0.5, (CL.x - 1.2, -4.6, CL.z - 1.3), tuple(CL + Vector((0.2, 0, -0.2))), 30),
    (S(8), (CL.x - 2.2, -6.2, CL.z - 0.5), tuple(CL + Vector((0.6, 0, 0.1))), 30),
    (E(8) - 0.2, (16.0, -20.0, 14.0), (26.0, 0.0, 10.0), 26),
    (S(9) + 1.4, (36.0, -20.0, 7.0), (44.0, 0.0, 4.5), 26),
    (E(9) - 0.4, (44.0, -15.0, 8.0), (46.5, 0.0, 6.0), 28),
    (S(10) + 1.6, tuple(CW_ + Vector((1.2, -3.4, -0.2))), tuple(CW_ + Vector((0.0, 0.2, 0.1))), 30),
    (S(11), tuple(CW_ + Vector((0.6, -2.9, -0.35))), tuple(CW_ + Vector((-0.1, 0.2, 0.05))), 32),
    (E(11), tuple(CW_ + Vector((0.2, -3.6, 0.4))), tuple(CW_ + Vector((-0.3, 0.2, 0.2))), 30),
    (S(12) + 1.2, (48.0, -26.0, 10.0), (58.0, 2.0, 5.5), 26),
    (S(13) + 1.0, (58.0, -24.0, 8.0), (60.0, 1.5, 6.5), 26),
    (E(13) - 0.6, (60.0, -16.0, 4.5), (61.0, 2.6, 2.4), 28),
    (S(14) + 1.0, (62.0, -27.0, 9.0), (60.0, 1.5, 7.5), 26),
    (E(15), (66.0, -26.0, 9.0), (61.0, 1.5, 7.5), 26),
    (S(16) + 0.7, (90.0, -2.0, 9.0), (79.0, 9.0, 2.0), 26),
    (W("pads", S(16)) + 0.4, (70.0, 6.0, 6.0), (66.0, 16.0, 1.5), 28),
    (S(17) + 1.4, (56.5, 11.6, 2.0), (56.0, 16.0, 1.0), 28),
    (E(17), (46.5, 11.2, 1.7), (46.5, 16.0, 1.0), 28),
    (E(18), (48.0, 9.0, 4.0), (44.0, 16.0, 1.5), 30),
    (S(20), (40.0, -6.0, 14.0), (36.0, 16.0, 1.5), 26),
    (E(20), (33.0, -5.0, 16.0), (33.0, 16.0, 1.0), 21),
    (E(22), (33.5, -4.5, 15.5), (33.5, 16.0, 1.2), 21),
    (S(23) + 1.5, (58.0, -32.0, 8.0), (64.0, -15.0, 3.5), 26),
    (E(24) - 0.5, (56.0, -29.0, 6.0), (64.0, -15.0, 3.0), 28),
    (S(25) + 0.3, (2.0, -40.0, 18.0), (30.0, 4.0, 4.0), 26),
    (spec.DUR - 0.12, (-3.0, -30.0, 14.0), (22.0, -10.0, 4.5), 24),      # == the first key: seamless loop
], drift=0.05, lens_scale=0.8, taper=(0.0, spec.DUR - 0.12))


# ------------------------------------------------------------------ animate
def animate(f):
    t = f / FPS
    CAM.apply(t)
    k = k_loop(t)
    LOOP_KEY.value = k
    LOOP_TIE_KEY.value = k
    # loop-top anchor follows the morph
    top = route(L_OUT + LK(t) * 0.5, k)[0]
    loop_top.location = top + Vector((0, 0, 0.3))

    # ---- builds / visibility
    endk = smooth(seg(t, T["end0"], T["end1"]))            # loop back to frame 0: steel sinks, the wooden ramp returns
    out_w = smooth(seg(t, T["wood_out0"], T["wood_out1"])) * (1 - endk)
    wood.scale = (1, 1, max(0.001, 1 - out_w))
    hide(wood, out_w >= 0.999)
    sinkz = -18.0 * endk
    gone = endk > 0.97
    steel_vis = t >= T["steel0"] and not gone
    for o in (seg_station, seg_lift, seg_drop, ties_out, sup_out):
        hide(o, not steel_vis)
    sk_ = ease_out(seg(t, T["steel0"], T["steel1"]))
    for o in (seg_station, seg_lift, seg_drop, ties_out, sup_out):
        o.scale = (1, 1, 1)
    # steel grows up out of the ground
    for o in (sup_out,):
        o.scale = (1, 1, max(0.001, sk_ * (1 - endk)))
    for o in (seg_station, seg_lift, seg_drop, ties_out, ratchet):
        o.location = (0, 0, -6.0 * (1 - sk_) + sinkz)
    loop_vis = t >= T["loop_b0"] and not gone
    lk_ = ease_out(seg(t, T["loop_b0"], T["loop_b1"]))
    for o in (loop_obj, loop_ties_obj):
        hide(o, not loop_vis)
        o.scale = (1, 1, max(0.001, lk_))
        o.location = (LX * (1 - 1), 0, 0)
    back_vis = t >= T["loop_b0"] and not gone
    for o in (seg_back1, seg_back2, ties_back, sup_back):
        hide(o, not back_vis)
        o.location = (0, 0, -6.0 * (1 - lk_) + sinkz)
    for o in (loop_obj, loop_ties_obj):
        o.location = (0, 0, sinkz)
    for nm in ("loop_leg-1", "loop_leg1"):
        hide(bpy.data.objects[nm], not loop_vis)
    hide(ratchet, t < T["strip0"] or gone)
    if t >= T["strip0"]:
        rk = ease_out(seg(t, T["strip0"], T["strip1"]))
        ratchet.scale = (1, 1, max(0.001, rk))
    hide(mag, t < T["fin0"] or gone)
    mk = ease_out(seg(t, T["fin0"], T["fin0"] + 0.8))
    mag.location = (0, 0, -1.5 * (1 - mk) + sinkz)
    for pd, sx in PADS:
        hide(pd, t < T["pads"] - 0.8 or t > S(17) + 1.0)
    for mt in PADS_MOUNTS:
        hide(mt, t < T["pads"] - 0.8 or t > S(17) + 1.0)
    for c_, sx, cp, b, rot in CLAMPS:
        vis = t >= S(21) + 0.4
        hide(c_, not vis)
        close = smooth(seg(t, T["rewind1"] - 0.1, T["rewind1"] + 0.4))
        c_.matrix_world = Matrix.Translation(cp + b * sx * lerp(0.35, 0.07, close)) @ rot
    for e in SIGNALS:
        hide(e, t < S(21) or endk > 0.02)
    hide(ff, t < T["ff0"] or endk > 0.98)
    ffk = ease_out(seg(t, T["ff0"], T["ff1"])) * (1 - endk)
    ff.scale = (1, 1, max(0.001, ffk))
    for nm in ("loop_leg-1", "loop_leg1"):
        bpy.data.objects[nm].location.z = sinkz
    wa = t / 70.0 * 2 * math.pi                         # ferris wheel turns slowly; cabins hang level
    fwheel.rotation_euler = (0, wa, 0)
    for cab, a_ in CABINS:
        cab.location = FW_C + Vector((math.cos(a_ - wa) * 12.4, 0, math.sin(a_ - wa) * 12.4))

    # ---- term highlight flashes
    for o in (seg_lift, ratchet, loop_obj, mag, seg_back1, seg_back2) + tuple(SIGNALS):
        highlight(o, 0)
    highlight(seg_lift, flash_amount(t, TERMS["lift hill"]))
    for o in PA["up"] + PA["guide"]:
        highlight(o, flash_amount(t, TERMS["upstop and guide wheels"]))
    highlight(loop_obj, flash_amount(t, TERMS["clothoid loop"]))
    highlight(mag, flash_amount(t, TERMS["magnetic brake"]))
    for e in SIGNALS:
        highlight(e, flash_amount(t, TERMS["block system"]))

    # ---- chain on the lift
    chain_on = (T["steel1"] - 0.6 < t < S(9)) and not (T["snap"] < t < S(6) + 0.6)
    chain_speed = (S_CREST - S_LIFT0) / max(0.1, T["crest"] - T["climb0"])

    def link(i):
        if t > S(9) or t < T["steel1"] - 0.6:
            return None
        ln = S_CREST - S_LIFT0
        sp = S_LIFT0 + ((i * ln / NLINK + t * chain_speed * (1 if chain_on else 0)) % ln)
        p, tt, u, b = OUT.frame(sp)
        pos = p + u * -0.08
        if T["snap"] < t < S(6) + 0.6:
            brk = S_LIFT0 + 8.5
            ks = seg(t, T["snap"], T["snap"] + 1.2)
            sp0 = S_LIFT0 + ((i * ln / NLINK + T["snap"] * chain_speed) % ln)
            p0, tt0, u0, b0 = OUT.frame(sp0)
            pos = p0 + u0 * -0.08
            if sp0 > brk - 1.0:
                R_ = rng(i + 900)
                v = Vector((R_.uniform(-2, 2), R_.uniform(-3, 3), R_.uniform(0, 3)))
                tt_ = ks * 1.2
                pos = pos + v * tt_ + Vector((0, 0, -9.8 * tt_ * tt_ / 2))
                if pos.z < 0.05:
                    pos.z = 0.05
            tt = tt0
        rot = tt.to_track_quat("Y", "Z").to_euler()
        return (pos, rot, 1.0)

    LINKS.drive(link)

    # ---- wooden cart (lines 1-3)
    endk = smooth(seg(t, T["end0"], T["end1"]))
    wood_phase = t <= T["wood_out0"] + 0.4 or endk > 0.0
    hide(CW, not wood_phase)
    if wood_phase:
        stop_s = 0.3 + (WOOD.L - 0.3) * 0.0
        s_valley = WOOD.S[min(range(len(WOOD.P)), key=lambda i: abs(WOOD.P[i].x - 30.0))]
        s_half = WOOD.S[min(range(len(WOOD.P)), key=lambda i: abs(WOOD.P[i].x - 34.0) + abs(WOOD.P[i].z - 3.3) * 0)]
        sw = sched(t, [(T["roll0"], 0.6, "l"), (T["roll0"] + 1.3, s_valley, "i"), (T["stop"], s_half, "o"),
                       (T["back"], s_valley + 0.6, "s")])
        _ = stop_s
        if endk > 0:
            sw = 0.6
        p, tt, u, b = WOOD.frame(sw)
        sc_w = wood.scale.z if endk > 0 else 1.0           # rides up with the ramp as it rises back
        place_on(CW, (Vector((p.x, p.y, p.z * sc_w)), tt, u))

    # ---- cart A + YOU
    YOU.set_tint("none")
    YOU.root.scale = (1, 1, 1)
    hide(CA, t < S(3) + 0.4 or endk > 0.97)
    ride = CW if wood_phase else CA
    seat(YOU, ride)
    if ride is CW:
        stopk = smooth(seg(t, T["stop"] - 0.3, T["stop"] + 0.4))
        YOU.set_tint("blue", stopk * (1 - seg(t, T["back"], T["back"] + 0.5)))
        YOU.pose(blend(SEATED, "shrug", stopk * 0.7))
    else:
        sA = cart_A_s(t)
        fr = route(sA, k)
        lift = 0.0
        if T["air_up"] < t < T["wheels0"]:                     # airtime: cart leaves the rails (no upstops yet)
            lift = 0.75 * pulse(t, T["air_up"], T["air_dn"] + 0.2)
        if t < S(3) + 0.9:
            sc = ease_out(seg(t, S(3) + 0.4, S(3) + 0.9))
            CA.scale = (sc, sc, sc)
        else:
            CA.scale = (1, 1, 1)
        place_on(CA, fr, lift)
        CA.location.z += -18.0 * endk
        if CA.scale.x < 1:
            CA.matrix_world = CA.matrix_world @ Matrix.Scale(max(0.01, CA.scale.x), 4)
        # rider moods / poses
        if T["snap"] < t < S(6) + 0.5:
            YOU.set_tint("blue", seg(t, T["snap"], T["snap"] + 0.3))
            YOU.pose(blend(SEATED, "cower", 0.6))
        if T["air_up"] - 0.2 < t < T["wheels0"]:
            a = pulse(t, T["air_up"], T["air_dn"] + 0.2)
            YOU.pose(blend(SEATED, "cheer", a))
            YOU.root.location = (0, 0.3, 0.37 + 0.35 * a)
            YOU.set_tint("blue", a)
        if S(13) < t < S(14) + 0.5:
            sq = smooth(seg(t, W("bottom", S(13)) - 0.4, W("bottom", S(13)) + 0.2))
            YOU.root.scale = (1 + 0.12 * sq, 1 + 0.12 * sq, 1 - 0.25 * sq)
            YOU.pose(blend(SEATED, "cower", sq * 0.7))
            YOU.set_tint("blue", sq)
        if S(19) - 0.2 < t < S(20):
            YOU.set_tint("orange", smooth(seg(t, S(19) - 0.2, S(19) + 0.3)))
            YOU.pose(blend(SEATED, "relax", 0.6))
        if t >= S(20):
            YOU.set_tint("orange", 1 - seg(t, T["stall"], T["stall"] + 0.5))
            if t > T["stall"]:
                YOU.pose(blend(SEATED, "look_up", 0.5))
    # wheels: road always, upstop/guide from line 10
    wk2 = ease_out(seg(t, T["wheels0"], T["wheels1"]))
    for o in PA["up"] + PA["guide"] + PB["up"] + PB["guide"]:
        hide(o, wk2 <= 0)
        o.scale = (max(0.001, wk2),) * 3
    # latch: hidden until line 6, then rides the teeth
    hide(LATCH_A, t < T["latch0"])
    hide(LATCH_B, True)
    lk2 = ease_out(seg(t, T["latch0"], T["latch1"]))
    if t >= T["latch0"]:
        sA = cart_A_s(t) if t >= S(3) + 0.4 else 0
        ph = ((sA - S_LIFT0) % TOOTH) / TOOTH
        on_lift = S_LIFT0 < sA < S_CREST
        ang = 32 + 16 * ph if on_lift else 18
        LATCH_A.rotation_euler = (D(-ang * lk2 - 80 * (1 - lk2)), 0, 0)
    for fin, cart in ((FIN_A, CA), (FIN_B, CB)):
        fk = ease_out(seg(t, T["fin0"], T["fin0"] + 0.6))
        hide(fin, fk <= 0)
        fin.scale = (1, max(0.001, fk), 1)

    # ---- cart B
    b_vis = ((E(14) - 0.8 < t < E(15) + 1.0) or (t >= S(20) - 0.5)) and endk < 0.97
    hide(CB, not b_vis)
    RIDER2.hide(True)
    if b_vis:
        sB = cart_B_s(t)
        place_on(CB, route(sB, k))
        CB.location.z += -18.0 * smooth(seg(t, T["end0"], T["end1"]))
        seat(RIDER2, CB)
        if t < E(15) + 1.0:
            RIDER2.set_tint("orange", 1.0)
            RIDER2.pose(blend(SEATED, "cheer", smooth(seg(t, S(15), S(15) + 0.5))))
        else:
            RIDER2.set_tint("none")
            if t > E(20) - 0.8:
                RIDER2.pose(blend(SEATED, "cower", smooth(seg(t, E(20) - 0.8, E(20) - 0.2)) * (1 - seg(t, T["rewind1"], T["rewind1"] + 0.6))))

    # ---- friction pads (glow + sparks + wear) and magnetic field arcs
    sA = cart_A_s(t) if t > S(3) + 0.4 else -1
    on_pads = S(16) < t < S(17) and abs(sA - (L_OUT + LK(t) + B_PADS)) < 1.3
    glow = smooth(seg(t, T["pads"] - 0.2, T["pads"] + 0.6)) * (1 - seg(t, S(17) - 0.2, S(17) + 0.8))
    K.set_emit(M["pad"], 1.6 * glow, (1.0, 0.42, 0.08))
    wear = seg(t, T["pads"], E(16))
    for pd, sx in PADS:
        pd.scale = (1, 1, 1 - 0.45 * wear)

    def spark(i):
        if not (T["pads"] - 0.1 < t < E(16)):
            return None
        R_ = rng(i + 77)
        ph = ((t * 2.2 + R_.random()) % 1.0)
        pd, sx = PADS[i % 2]
        p0 = pd.matrix_world.translation
        v = Vector((R_.uniform(-1, 1), R_.uniform(-1, 1), R_.uniform(1, 3)))
        pos = p0 + v * ph * 0.9 + Vector((0, 0, -4.0 * ph * ph))
        return (pos, (0, 0, 0), 0.9 * (1 - ph))

    SPARKS.drive(spark)
    _ = on_pads

    def heat(i):
        if not (T["roll0"] + 0.4 < t < T["stop"]):
            return None
        R_ = rng(i + 300)
        ph = (t * 1.8 + R_.random()) % 1.0
        p0 = CW.matrix_world @ Vector((R_.choice((-0.55, 0.55)), R_.choice((-0.6, 0.6)), 0.15))
        return (p0 + Vector((0, 0, ph * 0.7)), (0, 0, 0), 0.8 * (1 - ph))

    HEAT.drive(heat)

    def field(i):
        if not (W("magnets", S(17)) - 0.3 < t < E(18) + 0.3):
            return None
        R_ = rng(i + 500)
        sm = lerp(B_MAG0, B_MAG1, (i + 0.5) / 24)
        p, tt, u, b = BACK.frame(sm)
        wob = math.sin(t * 6 + i) * 0.03
        pos = p + u * (-0.24 + wob)
        return (pos, b.to_track_quat("Y", "Z").to_euler(), (1, 0.55 + 0.1 * math.sin(t * 9 + i), 1))

    FIELD.drive(field)

    # ---- block system: section colours + signals
    sec_on = smooth(seg(t, S(21) + 0.3, S(21) + 1.0)) * (1 - seg(t, E(22) + 0.4, E(22) + 1.2))
    base = (0.20, 0.52, 0.68)
    K.set_color(M["sec2"], tuple(lerp(c, d, sec_on) for c, d in zip(base, (0.85, 0.30, 0.26))))
    K.set_color(M["sec1"], tuple(lerp(c, d, sec_on) for c, d in zip(base, (0.30, 0.75, 0.38))))
    red = 2.2 * sec_on
    K.set_emit(M["lamp_r"], red, (1.0, 0.15, 0.1))
    K.set_emit(M["lamp_g"], 0.0, (0.2, 1.0, 0.35))

    # ---- crowd + Flip Flap rider
    for m in CROWD + [FF_RIDER]:
        m.hide(True)
    if S(24) - 0.4 <= t < T["end0"] + 0.6:
        for i, m in enumerate(CROWD):
            m.hide(False)
            m.root.parent = None
            m.place((FFX - 6 + 2.0 * i + 0.3 * math.sin(i), FFY - 4.5 - 0.6 * (i % 2), 0), 0)
            m.face((FFX, FFY, 0))
            m.pose(blend("stand", "point" if i % 3 == 0 else "look_up", 0.8))
    endk2 = smooth(seg(t, T["end0"], T["end1"]))
    hide(FFC, t < T["ff1"] or endk2 > 0.3)
    if T["ff1"] <= t and endk2 <= 0.3:
        u_ = sched(t, [(T["ff1"], 0.15, "l"), (S(24) + 0.4, 0.5, "s"), (E(24), 0.62, "o")])
        p, tt, u, b = FFP.frame(u_ * FFP.L)
        place_on(FFC, (p, tt, u))
        FF_RIDER.hide(False)
        seat(FF_RIDER, FFC, {"thL": (90, 6, 0), "knL": 85, "thR": (90, 6, 0), "knR": 85, "hipz": -0.47,
                             "shR": (150, 10, 0), "elR": 120, "shL": (40, 8, 0), "elL": 30, "neck": (15, 12, 0)})
        FF_RIDER.root.location = (0, 0.1, 0.2)
        FF_RIDER.set_tint("blue", smooth(seg(t, S(24), S(24) + 0.6)))


K.run(animate, BASE, NF, default_snaps=[60, 240, 330, 400, 470, 540, 650, 760, 860, 990, 1110, 1230, 1330, 1450,
                                        1560, 1700, 1800, 1900, 2000, 2130, 2250, 2330, 2440, 2560, 2700, 2900, 3060])
