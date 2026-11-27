"""Why Elevators Don't Fall -- /build-explainer film #3 (1080x1920, 30 fps, ~81 s).

  blender -b --factory-startup -P build.py -- snaps 0,15,30,45 [tag] [draft]
  blender -b --factory-startup -P build.py -- render 0 <NF-1>

Cold open (hook): the car is already moving, the ropes snap at frame 3, it free-falls past the floors with camera
shake and the safety gear stops it dead at ~1.5 s. The last 1.1 s return to exactly frame 0's state + camera.
Every frame is a pure function of f; timings from spec.py.
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
from mathutils import Matrix, Vector  # noqa: E402

from bx_kit import (D, box, cyl, sphere, hide, highlight, flash_amount, seg, smooth, ease_out, ease_in, lerp,  # noqa: E402
                    pulse, rng, mat, Swarm, Mannequin, blend, stick, noise1, ring_sector)

FPS = spec.FPS
NF = spec.NF
DUR = spec.DUR
DRAFT = "draft" in K.cli_args()
K.setup_scene(res=(1080, 1920), fps=FPS, samples=24, draft=DRAFT, sky=(0.55, 0.70, 0.90),
              horizon=(0.82, 0.85, 0.88), sun_dir=(-40, 8, -32), sun_energy=4.0, sky_strength=1.15)
K.FOG["near"], K.FOG["far"] = 40.0, 240.0

M = {
    "ground": mat("ground", (0.55, 0.62, 0.50), rough=0.95),
    "street": mat("street", (0.45, 0.46, 0.48), rough=0.9),
    "concrete": mat("concrete", (0.80, 0.79, 0.76), rough=0.9),
    "slab": mat("slab", (0.70, 0.69, 0.66), rough=0.9),
    "cut": mat("cut", (0.90, 0.88, 0.84), rough=0.9),
    "brick": K.brick_mat("brick", (0.78, 0.52, 0.42), (0.72, 0.47, 0.38), (0.86, 0.82, 0.76), scale=0.9, row_h=0.35),
    "window": mat("window", (0.25, 0.35, 0.45), rough=0.2, emit=0.0, emit_col=(1.0, 0.85, 0.55)),
    "door": mat("door", (0.62, 0.66, 0.70), rough=0.35, metal=0.5),
    "car": mat("car", (0.20, 0.52, 0.62), rough=0.4, metal=0.2),
    "car_in": mat("car_in", (0.82, 0.62, 0.40), rough=0.7),
    "car_floor": mat("car_floor", (0.35, 0.33, 0.32), rough=0.8),
    "steel": mat("steel", (0.55, 0.57, 0.60), rough=0.35, metal=0.6),
    "steel_d": mat("steel_d", (0.30, 0.31, 0.33), rough=0.4, metal=0.5),
    "rail": mat("rail", (0.36, 0.37, 0.40), rough=0.35, metal=0.7),
    "rope": mat("rope", (0.15, 0.15, 0.16), rough=0.5, metal=0.4),
    "gov_rope": mat("gov_rope", (0.85, 0.55, 0.15), rough=0.5),
    "cw": mat("cw", (0.42, 0.46, 0.55), rough=0.5, metal=0.3),
    "machine": mat("machine", (0.30, 0.50, 0.36), rough=0.5),
    "gear": mat("gear", (0.95, 0.75, 0.15), rough=0.4),
    "magnet": mat("magnet", (0.25, 0.30, 0.55), rough=0.4, emit=0.0, emit_col=(0.4, 0.7, 1.0)),
    "spring": mat("spring", (0.85, 0.25, 0.22), rough=0.4),
    "spark": mat("spark", (1.0, 0.7, 0.25), emit=3.0, emit_col=(1.0, 0.6, 0.15), fog=False),
    "wood": mat("wood", (0.62, 0.44, 0.27), rough=0.8),
    "wood_d": mat("wood_d", (0.40, 0.28, 0.18), rough=0.8),
    "hat": mat("hat", (0.08, 0.08, 0.09), rough=0.6),
    "sky_b": mat("sky_b", (0.66, 0.70, 0.76), rough=0.9),
    "lamp": mat("lamp", (1.0, 0.95, 0.85), emit=0.0, emit_col=(1.0, 0.9, 0.7)),
}

FH = 3.5             # floor height
NFLOOR = 8
TOP = FH * NFLOOR    # 28.0 machine room floor
PIT = -1.6
SX, SY = 1.45, 1.45  # shaft half sizes
CAR_W, CAR_D, CAR_H = 1.6, 1.3, 2.3
CAR_Y = -0.15
RAIL_X = 1.02
CW_Y = 1.0
SHEAVE = Vector((0.0, 0.35, TOP + 1.45))
SHEAVE_R = 0.62

# ------------------------------------------------------------------ city + ground
box("ground", (0, 0, -0.5 + PIT), (900, 900, 1.0), M["ground"], outline=False)
for nm, c, sz in (("gt_s", (0, -257.0, -0.06), (900, 500, 0.1)), ("gt_n", (0, 255.75, -0.06), (900, 500, 0.1)),
                  ("gt_w", (-254.2, 2.5, -0.06), (500, 10, 0.1)), ("gt_e", (254.2, 2.5, -0.06), (500, 10, 0.1))):
    box(nm, c, sz, M["ground"], outline=False)       # ground with a hole over the building (so the pit is visible)
# section cut in front of the shaft so the pit (below ground) can be seen from the front
soil = mat("soil", (0.55, 0.42, 0.30), rough=0.95)
for nm, c, sz in (("gt_cut_l", (-(3.0 + 7.1) / 2 - 0.0, -3.8, -0.06), (7.1 - 3.0 + 0.4, 4.4, 0.1)),
                  ("gt_cut_r", ((3.0 + 7.1) / 2, -3.8, -0.06), (7.1 - 3.0 + 0.4, 4.4, 0.1)),
                  ("gt_cut_s", (0, -5.0 - 1.0, -0.06), (6.2, 2.0, 0.1))):
    box(nm, c, sz, M["ground"], outline=False)
box("soil_front", (0, -5.0, (PIT - 0.3) / 2), (6.0, 0.1, -(PIT - 0.3)), soil, outline=0.015)
for sx in (-1, 1):
    box(f"soil_side{sx}", (sx * 3.0, -3.3, (PIT - 0.3) / 2), (0.1, 3.4, -(PIT - 0.3)), soil, outline=0.015)
box("soil_floor", (0, -3.3, PIT - 0.35), (6.0, 3.4, 0.1), soil, outline=False)
box("gt_bld_l", (-4.3, 2.5, -0.06), (5.6, 10, 0.1), M["slab"], outline=False)
box("gt_bld_r", (4.3, 2.5, -0.06), (5.6, 10, 0.1), M["slab"], outline=False)
box("street", (0, -14, -0.0), (300, 8, 0.02), M["street"], outline=False)
R = rng(11)
for i in range(46):                         # skyline: blocks with warm windows
    a = R.uniform(0.15 * math.pi, 0.85 * math.pi)
    d = R.uniform(40, 120)
    x, y = math.cos(a) * d, math.sin(a) * d + 10
    h = R.uniform(10, 46)
    w_ = R.uniform(6, 14)
    box(f"city{i}", (x, y, 0), (w_, w_, h), M["sky_b"], base=True, outline=0.04)
for i in range(18):                         # street trees
    x = -40 + i * 5 + R.uniform(-1, 1)
    if abs(x) < 9 or 11 < x < 22:
        continue
    cyl(f"tr{i}", (x, -10.5, 0), 0.2, 1.8, mat(f"trunk{i}", (0.4, 0.28, 0.18)), base=True, seg_n=6, outline=0.02)
    sphere(f"trc{i}", (x, -10.5, 2.6), 1.4, mat(f"leaf{i}", (0.36, 0.56, 0.32)), seg_u=8, seg_v=6, outline=0.03,
           smooth_shade=False)

# ------------------------------------------------------------------ the building (cutaway: front removed)
bld = K.empty("building")
BW = 7.0
for k in range(NFLOOR + 1):
    z = k * FH
    # floor slabs left and right of the shaft and behind it
    box(f"slabL{k}", ((-BW - SX - 0.25) / 2, 2.0, z - 0.15), (BW - SX - 0.25, 7.0, 0.3), M["slab"], bld, outline=0.02)
    box(f"slabR{k}", ((BW + SX + 0.25) / 2, 2.0, z - 0.15), (BW - SX - 0.25, 7.0, 0.3), M["slab"], bld, outline=0.02)
    box(f"slabB{k}", (0, (SY + 0.25 + 5.5) / 2, z - 0.15), (2 * SX + 0.5, 5.5 - SY - 0.25, 0.3), M["slab"], bld, outline=0.02)
# bright floor-edge bands with big floor numbers: they whip past in the hook
for k in range(NFLOOR + 1):
    z = k * FH
    for sx in (-1, 1):
        box(f"band{k}{sx}", (sx * (BW + SX) / 2, -1.52, z - 0.15), (BW - SX - 0.2, 0.06, 0.32), M["gear"], bld, outline=0.01)
    if k < NFLOOR:
        box(f"numplate{k}", (-2.3, -1.56, z + 1.6), (0.9, 0.05, 0.9), M["concrete"], bld, outline=0.012)
        box(f"numstripe{k}", (-2.3, -1.6, z + 1.6), (0.7, 0.03, 0.12 + 0.07 * (k % 3)), M["rope"], bld, outline=False)
# shaft walls (sides + back, with landing door openings in the back)
for sx in (1,):                                       # left shaft wall cut away for the close-ups
    box(f"shaftwall{sx}", (sx * (SX + 0.12), 0.25, (PIT + TOP + 3.2) / 2), (0.24, 2 * SY + 0.5, TOP + 3.2 - PIT),
        M["concrete"], bld, outline=0.02)
box("shaftwall_cutL", (-(SX + 0.12), 1.2, (PIT + TOP) / 2), (0.24, 0.6, TOP - PIT), M["cut"], bld, outline=0.015)
DOORS = []
for k in range(NFLOOR):
    z = k * FH
    box(f"backwall_l{k}", (-1.05, SY + 0.12, z + FH / 2), (0.8, 0.24, FH), M["concrete"], bld, outline=0.015)
    box(f"backwall_r{k}", (1.05, SY + 0.12, z + FH / 2), (0.8, 0.24, FH), M["concrete"], bld, outline=0.015)
    box(f"backwall_t{k}", (0, SY + 0.12, z + 2.4 + (FH - 2.4) / 2), (1.3, 0.24, FH - 2.4), M["concrete"], bld, outline=0.015)
    dl = box(f"door_l{k}", (0, 0, 0), (0.64, 0.05, 2.35), M["door"], outline=0.01)
    dr = box(f"door_r{k}", (0, 0, 0), (0.64, 0.05, 2.35), M["door"], outline=0.01)
    DOORS.append((dl, dr, z))
box("pit_floor", (0, 0, PIT - 0.15), (2 * SX + 0.5, 2 * SY + 0.5, 0.3), M["concrete"], bld, outline=0.02)
box("pit_back", (0, SY + 0.12, PIT / 2), (2 * SX, 0.24, -PIT), M["concrete"], bld, outline=0.015)
# exterior side walls with windows + roof
WINDOWS = []
for sx in (1,):
    box(f"extwall{sx}", (sx * (BW + 0.15), 2.0, (TOP + 3.2) / 2), (0.3, 7.0, TOP + 3.2), M["brick"], bld, outline=0.03)
    for k in range(NFLOOR):
        for j, yy in enumerate((0.0, 2.2, 4.4)):
            wdw = box(f"win{sx}{k}{j}", (sx * (BW + 0.31), yy, k * FH + 1.7), (0.05, 1.1, 1.5), M["window"], bld,
                      outline=0.006)
            WINDOWS.append(wdw)
box("backwall_bld", (0, 5.6, (TOP + 3.2) / 2), (2 * BW + 0.6, 0.3, TOP + 3.2), M["brick"], bld, outline=0.03)
box("roof", (BW / 2 + 1.2, 2.0, TOP + 3.2), (BW - 1.8, 7.6, 0.3), M["slab"], bld, outline=0.03)
# room lights (ceiling panels on each floor; off in the power cut)
LAMPS = []
for k in range(NFLOOR):
    for sx in (-1, 1):
        LAMPS.append(box(f"lamp{k}{sx}", (sx * 4.2, 2.0, (k + 1) * FH - 0.33), (1.4, 0.6, 0.05), M["lamp"], bld,
                         outline=False))
# a few furnishings in the cut floors so it reads as a building
for k in range(1, NFLOOR):
    for sx in (-1, 1):
        box(f"desk{k}{sx}", (sx * 4.6, 2.6, k * FH), (1.6, 0.8, 0.75), M["wood"], bld, base=True, outline=0.012)
        cyl(f"plant{k}{sx}", (sx * 6.2, 0.8, k * FH), 0.25, 0.6, M["spring"], bld, base=True, seg_n=8, outline=0.01)

# ------------------------------------------------------------------ guide rails, machine room parts
rails = K.empty("rails")
for sx in (-1, 1):
    box(f"rail{sx}", (sx * RAIL_X, CAR_Y, (PIT + TOP) / 2), (0.08, 0.14, TOP - PIT), M["rail"], rails, outline=0.008)
    box(f"railweb{sx}", (sx * (RAIL_X + 0.1), CAR_Y, (PIT + TOP) / 2), (0.16, 0.04, TOP - PIT), M["rail"], rails, outline=0.006)
    box(f"cwrail{sx}", (sx * 0.78, CW_Y, (PIT + TOP) / 2), (0.06, 0.08, TOP - PIT), M["rail"], rails, outline=0.006)
machine = K.empty("machine")
cyl("sheave", SHEAVE, SHEAVE_R, 0.35, M["steel"], machine, axis="X", seg_n=32, outline=0.015)
SHEAVE_SPIN = K.empty("sheave_spin", SHEAVE, machine)
for k in range(6):
    b_ = box(f"spoke{k}", (0, 0, 0), (0.37, 0.06, 2 * SHEAVE_R * 0.9), M["steel_d"], SHEAVE_SPIN, outline=False)
    b_.rotation_euler = (D(30 * k), 0, 0)
motor = K.empty("motor", (-1.2, 0.35, TOP + 1.45))
cyl("motor_body", (0, 0, 0), 0.55, 1.2, M["machine"], motor, axis="X", seg_n=20, outline=0.02)
box("motor_base", (0, 0, -0.75), (1.4, 1.2, 0.3), M["steel_d"], motor, outline=0.015)
for k in range(5):
    cyl(f"motor_fin{k}", (-0.45 + k * 0.22, 0, 0), 0.6, 0.05, M["machine"], motor, axis="X", seg_n=20, outline=False)
cyl("shaft_axle", (-0.55, 0.35, TOP + 1.45), 0.08, 1.4, M["steel"], machine, axis="X", seg_n=10, outline=False)
# brake: drum + two shoes + electromagnet + springs
BRK = Vector((-0.65, 0.35, TOP + 1.45))
cyl("brake_drum", BRK, 0.36, 0.22, M["steel_d"], machine, axis="X", seg_n=24, outline=0.012)
SHOES = []
for sy in (-1, 1):
    sh = box(f"shoe{sy}", (0, 0, 0), (0.2, 0.12, 0.5), M["gear"], outline=0.01)
    SHOES.append((sh, sy))
mag_box = box("brake_magnet", BRK + Vector((0, 0, 0.75)), (0.3, 0.5, 0.3), M["magnet"], machine, outline=0.012)
for sy in (-1, 1):
    cyl(f"brake_spring{sy}", BRK + Vector((0, sy * 0.75, 0)), 0.07, 0.35, M["spring"], machine, axis="Y", seg_n=8,
        outline=0.008)
hw = K.empty("handwheel", Vector((-2.05, 0.35, TOP + 1.45)), machine)
ring_sector("handwheel_rim", (0, 0, 0), 0.32, 0.4, 0.06, 0, 360, M["gear"], hw, n=24, outline=0.008).rotation_euler = (0, D(90), 0)
for k in range(3):
    b_ = box(f"hw_spoke{k}", (0, 0, 0), (0.05, 0.05, 0.7), M["gear"], hw, outline=False)
    b_.rotation_euler = (D(60 * k), 0, 0)
box("machine_floor", (0, 0.5, TOP + 0.15), (2 * SX + 0.4, 2 * SY + 0.6, 0.3), M["slab"], outline=0.02)

# governor at the top right + its rope loop down to a tension sheave in the pit
GOV = Vector((1.2, -0.95, TOP + 0.95))
gov = K.empty("governor", GOV)
cyl("gov_wheel", (0, 0, 0), 0.34, 0.1, M["steel"], gov, axis="X", seg_n=24, outline=0.01)
GOV_SPIN = K.empty("gov_spin", (0, 0, 0), gov)
FLY = []
for k, sz in enumerate((1, -1)):
    piv = K.empty(f"fly_piv{k}", (0.09, 0, sz * 0.08), GOV_SPIN)
    box(f"fly{k}", (0, 0, 0), (0.06, 0.26, 0.09), M["gear"], piv, off=(0, 0.11, 0), outline=0.008)
    FLY.append((piv, sz))
pawl = K.empty("pawl", (0.09, -0.36, 0.25), gov)
box("pawl_m", (0, 0, 0), (0.06, 0.06, 0.22), M["spring"], pawl, off=(0, 0, -0.1), outline=0.008)
box("gov_stand", (0, 0, -0.45), (0.18, 0.18, 0.7), M["steel_d"], gov, outline=0.01)
cyl("gov_pit", (1.2, -0.95, PIT + 0.45), 0.2, 0.08, M["steel"], axis="X", seg_n=16, outline=0.008)
GOV_ROPES = [cyl(f"govrope{k}", (0, 0, 0), 0.025, 1.0, M["gov_rope"], base=True, seg_n=6, outline=False) for k in range(3)]

# buffers in the pit
buffers = K.empty("buffers")
BUF = []
for x, y in ((-0.35, CAR_Y), (0.35, CAR_Y), (0.0, CW_Y)):
    bf = K.empty(f"buf{x}{y}", (x, y, PIT))
    bf.parent = buffers
    cyl(f"buf_base{x}{y}", (0, 0, 0), 0.22, 0.12, M["steel_d"], bf, base=True, seg_n=12, outline=0.008)
    for k in range(6):
        ring_sector(f"buf_coil{x}{y}{k}", (0, 0, 0.14 + k * 0.13), 0.12, 0.17, 0.06, 0, 360, M["spring"], bf, n=14,
                    outline=0.004)
    cyl(f"buf_cap{x}{y}", (0, 0, 0.95), 0.2, 0.08, M["steel_d"], bf, base=True, seg_n=12, outline=0.008)
    BUF.append(bf)

# ------------------------------------------------------------------ the car (hollow, open front cutaway) + sling
car = K.empty("car")
box("car_floor", (0, 0, -0.06), (CAR_W, CAR_D, 0.12), M["car_floor"], car, outline=0.015)
box("car_back", (0, CAR_D / 2 - 0.04, CAR_H / 2), (CAR_W, 0.08, CAR_H), M["car_in"], car, outline=0.015)
for sx in (-1, 1):
    box(f"car_side{sx}", (sx * (CAR_W / 2 - 0.04), 0, CAR_H / 2), (0.08, CAR_D, CAR_H), M["car_in"], car, outline=0.015)
    box(f"car_skin{sx}", (sx * (CAR_W / 2 + 0.005), 0, CAR_H / 2), (0.02, CAR_D, CAR_H), M["car"], car, outline=0.015)
    box(f"car_jamb{sx}", (sx * (CAR_W / 2 - 0.12), -CAR_D / 2 + 0.03, CAR_H / 2), (0.24, 0.06, CAR_H), M["car"], car,
        outline=0.012)
box("car_top", (0, 0, CAR_H + 0.05), (CAR_W, CAR_D, 0.1), M["car"], car, outline=0.015)
box("car_header", (0, -CAR_D / 2 + 0.03, CAR_H - 0.12), (CAR_W, 0.06, 0.24), M["car"], car, outline=0.012)
box("car_light", (0, 0, CAR_H - 0.02), (0.8, 0.5, 0.03), M["lamp"], car, outline=False)
box("car_rail_in", (0, CAR_D / 2 - 0.12, 0.95), (1.2, 0.05, 0.05), M["steel"], car, outline=False)
# sling: uprights beside the rails, crosshead on top, plank below
for sx in (-1, 1):
    box(f"sling_up{sx}", (sx * 0.9, 0, CAR_H / 2 + 0.15), (0.1, 0.16, CAR_H + 0.6), M["steel_d"], car, outline=0.01)
box("crosshead", (0, 0, CAR_H + 0.45), (1.9, 0.18, 0.16), M["steel_d"], car, outline=0.012)
box("plank", (0, 0, -0.25), (1.9, 0.18, 0.16), M["steel_d"], car, outline=0.012)
# safety gear: a block around each rail with two wedge jaws
GEAR = []
for sx in (-1, 1):
    g = K.empty(f"gear{sx}", (sx * RAIL_X, 0, -0.15), car)
    box(f"gear_body{sx}", (0, 0, 0), (0.22, 0.5, 0.3), M["gear"], g, outline=0.01)
    jaws = []
    for sy in (-1, 1):
        j = box(f"jaw{sx}{sy}", (0, 0, 0), (0.1, 0.07, 0.26), M["steel"], g, outline=0.006)
        jaws.append((j, sy))
    GEAR.append((g, jaws))
lever = box("gov_lever", (0.98, -0.55, 0.4), (0.06, 0.4, 0.06), M["gov_rope"], car, outline=0.006)
# hoist ropes (4) from the crosshead up to the sheave, and down the back to the counterweight
ROPE_X = (-0.24, -0.08, 0.08, 0.24)
ROPES = [cyl(f"rope{k}", (0, 0, 0), 0.03, 1.0, M["rope"], base=True, seg_n=6, outline=False) for k in range(4)]
ROPE_TOP = [cyl(f"ropetop{k}", (0, 0, 0), 0.03, 1.0, M["rope"], base=True, seg_n=6, outline=False) for k in range(4)]
ROPES_CW = [cyl(f"ropecw{k}", (0, 0, 0), 0.03, 1.0, M["rope"], base=True, seg_n=6, outline=False) for k in range(4)]
cwt = K.empty("counterweight")
box("cw_frame", (0, 0, 1.1), (1.3, 0.3, 2.3), M["steel_d"], cwt, outline=0.012)
for k in range(9):
    box(f"cw_plate{k}", (0, 0, 0.25 + k * 0.22), (1.15, 0.34, 0.18), M["cw"], cwt, outline=0.008)

YOU = Mannequin("you")
TECH = Mannequin("tech", tint=(0.95, 0.6, 0.2))
OTIS = Mannequin("otis")
AXE = Mannequin("axeman", tint=(0.5, 0.5, 0.55))
CROWD = [Mannequin(f"crowd{i}", tint=("none", "blue", "none", "orange", "none")[i]) for i in range(5)]
top_hat = K.empty("tophat")
cyl("hat_brim", (0, 0, 0), 0.17, 0.02, M["hat"], top_hat, base=True, seg_n=14, outline=0.006)
cyl("hat_top", (0, 0, 0.02), 0.11, 0.22, M["hat"], top_hat, base=True, seg_n=14, outline=0.006)
axe = K.empty("axe")
cyl("axe_handle", (0, 0, 0), 0.03, 0.9, M["wood_d"], axe, base=True, seg_n=6, outline=0.006)
box("axe_head", (0.08, 0, 0.82), (0.18, 0.04, 0.14), M["steel"], axe, outline=0.006)

# Otis 1854 demo rig (outside, right of the building)
OX, OY = 16.5, -6.0
otis_rig = K.empty("otis_rig", (OX, OY, 0))
for sx in (-1, 1):
    box(f"ot_post{sx}", (sx * 1.3, 0, 4.0), (0.25, 0.25, 8.0), M["wood_d"], otis_rig, outline=0.015)
    for k in range(22):                                   # ratchet teeth on the inside of each post
        box(f"ot_tooth{sx}{k}", (sx * 1.13, 0, 0.6 + k * 0.33), (0.1, 0.18, 0.1), M["steel_d"], otis_rig, outline=False)
box("ot_beam", (0, 0, 8.1), (3.0, 0.3, 0.25), M["wood_d"], otis_rig, outline=0.015)
cyl("ot_pulley", (0, 0, 8.35), 0.25, 0.3, M["steel"], otis_rig, axis="Y", seg_n=14, outline=0.008)
platform = K.empty("ot_platform")
box("ot_floor", (0, 0, 0), (2.2, 1.6, 0.12), M["wood"], platform, outline=0.012)
box("ot_bar", (0, 0, 1.1), (2.2, 0.08, 0.08), M["wood_d"], platform, outline=0.008)
for sx in (-1, 1):
    box(f"ot_side{sx}", (sx * 1.05, 0, 0.55), (0.08, 0.08, 1.1), M["wood_d"], platform, outline=0.008)
spring_bar = box("ot_spring", (0, 0, 1.5), (2.3, 0.1, 0.06), M["spring"], platform, outline=0.008)
ot_rope = cyl("ot_rope", (0, 0, 0), 0.035, 1.0, M["wood_d"], base=True, seg_n=6, outline=False)
ot_rope2 = cyl("ot_rope2", (0, 0, 0), 0.035, 1.0, M["wood_d"], base=True, seg_n=6, outline=False)

streak_proto = box("streak_p", (0, 0, 0), (0.02, 0.02, 1.0), mat("streak", (0.95, 0.97, 1.0), emit=1.2,
                    emit_col=(0.95, 0.97, 1.0), fog=False), outline=False)
STREAKS = Swarm("streak", streak_proto, 26)
spark_proto = sphere("spark_p", (0, 0, 0), 0.04, M["spark"], seg_u=6, seg_v=4, outline=False)
SPARKS = Swarm("spark", spark_proto, 40)

# ------------------------------------------------------------------ anchors
K.anchor("rope", ROPES[0], (0, 0, 0.6))
K.anchor("motor", motor, (0, 0, 0.6))
K.anchor("cw", cwt, (0, -0.15, 1.6))
K.anchor("snap", ROPE_TOP[0], (0, 0, 0.1))
K.anchor("rail", (-RAIL_X, CAR_Y, 15.0))
K.anchor("gear", GEAR[0][0])
K.anchor("govrope", GOV_ROPES[0], (0, 0, 0.5))
K.anchor("fly", GOV_SPIN)
K.anchor("gov", gov, (0, 0, 0.4))
K.anchor("buffer", BUF[0], (0, 0, 0.9))
K.anchor("brake", BRK + Vector((0, 0, 0.3)))
K.anchor("hand", hw)


# ------------------------------------------------------------------ motion
def sched(t, keys):
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0, _), (t1, v1, e) in zip(keys, keys[1:]):
        if t <= t1:
            u = seg(t, t0, t1)
            u = {"l": u, "i": ease_in(u), "o": ease_out(u), "s": smooth(u)}[e]
            return lerp(v0, v1, u)
    return keys[-1][1]


Z0 = 21.0              # hook: car level at frame 0, descending at V0
V0 = 1.0
T_SNAP = 0.10
T_STOP = 1.42
T = {
    "rewind0": 3.0, "rewind1": 3.45,
    "pull0": W("pull", S(3)) - 0.2,
    "motor0": W("huge", S(4)) - 0.3, "motor1": W("difference", S(7)),
    "cw0": W("heavy", S(5)) - 0.3,
    "snap2": W("snaps", S(8)),
    "rails0": W("rails", S(9)) - 1.0, "gear0": W("clamps", S(9)) - 0.3,
    "bite": W("bite", S(10)),
    "restore": S(11) - 0.1,
    "fast": W("fast", S(12)) - 0.2, "lock": W("lock", S(12)),
    "yank": W("yanks", S(13)),
    "ropes4": W("never", S(14)),
    "buf0": W("springs", S(15)) - 0.5, "land": W("landing", S(15)),
    "cut": W("cuts", S(17)),
    "noPower": W("power", S(18)),
    "tech0": S(19), "lower1": E(19) - 0.3,
    "otis": S(20) - 0.3, "axe": W("cut", S(20)), "stop_ot": W("stopped", S(21)),
    "back": S(22) - 0.6,
}


def hook_z(t):
    if t < T_SNAP:
        return Z0 - V0 * t
    if t < T_STOP:
        tt = t - T_SNAP
        return Z0 - V0 * t - 0.5 * 9.8 * tt * tt
    z_stop = hook_z(T_STOP - 1e-6)
    return z_stop - 0.25 * ease_out(seg(t, T_STOP, T_STOP + 0.18))


HOOK_LOW = hook_z(3.0)


def car_z(t):
    """Car floor height at time t (the whole story)."""
    if t < T["rewind0"]:
        return hook_z(t)
    if t < S(4):
        return sched(t, [(T["rewind0"], HOOK_LOW, "l"), (T["rewind1"], 0.0, "s"), (T["pull0"], 0.0, "l"),
                         (E(3), FH, "s")])
    if t < S(8):
        return sched(t, [(S(4), FH, "l"), (E(4), FH + 1.2, "s"), (T["cw0"] + 0.8, FH + 1.2, "l"),
                         (E(7), 4 * FH, "s")])
    if t < S(11) - 0.1:            # rope snaps: falls a little, freezes while the explanation builds, then the bite
        z_s = 4 * FH
        if t < T["snap2"]:
            return z_s
        if t < T["snap2"] + 0.55:
            tt = t - T["snap2"]
            return z_s - 0.5 * 9.8 * tt * tt
        z_f = z_s - 0.5 * 9.8 * 0.55 ** 2
        if t < T["bite"] - 0.3:
            return z_f - 0.04 * math.sin((t - T["snap2"]) * 3)      # frozen mid-fall (slight drift)
        return z_f - 0.9 * ease_out(seg(t, T["bite"] - 0.3, T["bite"] + 0.5))
    z_hold = 4 * FH - 0.5 * 9.8 * 0.55 ** 2 - 0.9
    if t < S(14):
        # restored: travels down, overspeeds, governor locks, clamps stop it
        z_a = z_hold + 4.0
        return sched(t, [(S(11) - 0.1, z_a, "l"), (T["fast"], z_a - 2.6, "l"), (T["lock"] + 0.3, z_a - 6.2, "i"),
                         (T["yank"] + 0.4, z_a - 7.2, "o")])
    z_g = z_hold + 4.0 - 7.2
    if t < S(16):
        return sched(t, [(S(14), z_g + 3.0, "l"), (T["buf0"] + 0.6, z_g + 3.0, "l"), (T["land"] - 0.2, PIT + 0.95 + 0.25, "i"),
                         (T["land"] + 0.5, PIT + 0.95 + 0.25 - 0.18, "o")])
    if t < S(19):
        return sched(t, [(S(16), 2 * FH - 1.0, "l"), (T["cut"], 2 * FH + 2.3, "o")])
    if t < T["back"]:
        return sched(t, [(S(19), 2 * FH + 2.3, "l"), (T["tech0"] + 1.2, 2 * FH + 2.3, "l"), (T["lower1"], 2 * FH, "s")])
    # loop: arrive exactly at frame 0's state (Z0, descending at V0)
    return Z0 + V0 * (DUR - t)


def ropes_intact(t):
    if t < T_SNAP:
        return True
    if t < T["rewind1"]:
        return False
    if T["snap2"] <= t < T["restore"]:
        return False
    if T["buf0"] + 0.6 < t < S(16):          # "if everything still fails": slack, car on the buffers
        return False
    return True


def n_ropes(t):
    if t < T["rewind0"] or t >= T["ropes4"] or t >= T["back"]:
        return 4
    return 1


def place_rope(obj, p0, p1, show=True):
    hide(obj, not show)
    if show:
        stick(obj, p0, p1)


# ------------------------------------------------------------------ camera
def hook_cam(t, shake=True):
    z = car_z(t)
    lag = 0.0
    if T_SNAP < t < 3.0:              # the camera falls a beat slower than the car, then catches it at the stop
        lag = min(1.4, 0.35 * (Z0 - V0 * t - z)) * (1 - smooth(seg(t, T_STOP, T_STOP + 0.25)))
    pos = Vector((-2.9, -5.4, z + 1.4 + lag))
    tgt = Vector((0.05, 0.0, z + 0.7 + lag * 0.8))
    if shake and T_SNAP < t < 2.9:
        a = 0.09 * seg(t, T_SNAP, 0.4) * (1 - seg(t, T_STOP, T_STOP + 0.05)) + 0.22 * pulse(t, T_STOP - 0.02, T_STOP + 0.35)
        a += 0.03 * pulse(t, T_STOP + 0.35, 2.6)
        pos += Vector((noise1(t * 9, 1.3) * a, noise1(t * 9, 4.1) * a, noise1(t * 9, 7.7) * a))
    return pos, tgt, 19


CZF = 4 * FH - 0.5 * 9.8 * 0.55 ** 2          # where the car freezes mid-fall
CAM = K.CamPath([
    (3.3, (-4.5, -11.0, 4.5), (0.0, 0.0, 3.0), 24),
    (S(3) + 2.4, (-5.5, -13.0, 7.5), (0.0, 0.0, 5.5), 24),
    (S(4) + 0.5, (-4.2, -7.5, TOP + 2.6), (-1.0, 0.3, TOP + 1.5), 24),
    (E(4), (-4.6, -8.2, TOP + 2.8), (-1.2, 0.3, TOP + 1.6), 24),
    (S(5) + 1.0, (-6.0, -15.0, TOP - 1.5), (0.0, 0.6, TOP - 4.5), 24),
    (S(7), (-8.0, -21.0, 13.5), (0.0, 0.5, 13.0), 24),
    (S(8), (-6.0, -15.0, 14.5), (0.0, 0.0, 12.5), 24),
    (S(9) + 0.8, (-4.0, -8.5, 13.0), (0.0, 0.0, 11.4), 24),
    (W("clamps", S(9)) + 0.6, (-2.7, -3.9, CZF + 0.5), (-0.95, CAR_Y, CZF - 0.1), 24),
    (S(10) + 0.6, (-2.3, -3.0, CZF - 0.1), (-1.0, CAR_Y, CZF - 0.35), 24),
    (E(10), (-2.9, -4.3, CZF - 0.4), (-0.95, CAR_Y, CZF - 0.9), 24),
    (S(11) + 0.5, (-6.0, -16.0, 20.0), (0.0, 0.0, 18.0), 24),
    (S(12) + 0.6, (-0.6, -5.2, TOP + 1.6), (1.15, -0.95, TOP + 0.95), 26),
    (W("lock", S(12)) + 0.3, (-0.2, -3.9, TOP + 1.3), (1.15, -0.95, TOP + 0.9), 28),
    (S(13) + 1.2, (-4.0, -11.0, 18.0), (0.6, -0.5, 13.0), 24),
    (S(14) + 0.8, (-4.5, -10.0, 22.0), (0.0, 0.0, 21.0), 24),
    (E(14), (-3.0, -6.5, 26.0), (0.0, 0.2, 27.5), 24),
    (S(15) + 1.0, (-5.0, -10.0, 3.0), (0.0, 0.0, 0.0), 24),
    (E(15), (-3.2, -6.0, 1.2), (0.0, 0.0, -0.6), 24),
    (S(16) + 0.2, (-12.0, -32.0, 17.0), (0.0, 1.0, 13.0), 24),
    (S(17) + 1.6, (-8.0, -18.0, 10.5), (0.0, 0.0, 9.5), 24),
    (S(18) + 0.6, (-2.6, -3.6, TOP + 2.3), (-0.7, 0.35, TOP + 1.45), 26),
    (E(18), (-2.4, -3.3, TOP + 2.1), (-0.8, 0.35, TOP + 1.4), 26),
    (S(19) + 1.0, (-3.6, -5.4, TOP + 2.4), (-1.6, 0.0, TOP + 1.2), 24),
    (E(19), (-8.0, -18.0, 9.0), (0.0, 0.0, 8.0), 24),
    (S(20) + 1.2, (8.0, -22.0, 6.0), (OX, OY, 3.6), 24),
    (E(21), (11.0, -15.0, 4.6), (OX, OY, 3.4), 26),
    (T["back"] + 0.9, (-6.0, -20.0, 22.0), (0.0, 0.0, 21.0), 24),
], drift=0.04, lens_scale=0.8)
END_BLEND0 = DUR - 1.4


def apply_camera(t):
    if t < 3.0:
        pos, tgt, lens = hook_cam(t)
        k = 0.0
    else:
        pos, tgt, lens = CAM.eval(t)
        lens *= 0.8
        k = smooth(seg(t, 3.0, 3.6))
        if k < 1:
            hp, ht, hl = hook_cam(2.999, shake=False)
            pos, tgt, lens = hp.lerp(pos, k), ht.lerp(tgt, k), lerp(hl, lens, k)
        if t > END_BLEND0:
            kk = smooth(seg(t, END_BLEND0, DUR - 0.12))
            hp, ht, hl = hook_cam(t, shake=False)
            pos, tgt, lens = pos.lerp(hp, kk), tgt.lerp(ht, kk), lerp(lens, hl, kk)
    cam = CAM.cam
    cam.location = pos
    cam.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens


# ------------------------------------------------------------------ animate
def animate(f):
    t = f / FPS
    apply_camera(t)
    z = car_z(t)
    car.location = (0, CAR_Y, z)
    sway = 0.0
    if T_STOP < t < 3.0:
        sway = 1.6 * math.sin((t - T_STOP) * 9) * math.exp(-(t - T_STOP) * 2.2)
    car.rotation_euler = (0, D(sway * 0.4), 0)

    # ---- what exists when (complete in the hook and at the end; built up in the story)
    story = T["rewind0"] < t < T["back"]
    vis_cw = (not story) or t >= T["cw0"]
    vis_rails = (not story) or t >= T["rails0"]
    vis_gear = (not story) or t >= T["gear0"]
    vis_gov = (not story) or t >= S(12) - 0.2
    vis_buf = (not story) or t >= T["buf0"]
    hide(cwt, not vis_cw)
    hide(rails, not vis_rails)
    for g, jaws in GEAR:
        hide(g, not vis_gear)
    hide(gov, not vis_gov)
    hide(bpy.data.objects["gov_pit"], not vis_gov)
    hide(lever, not vis_gov)
    hide(buffers, not vis_buf)
    # pop-in scales for things that appear in the story
    rk = ease_out(seg(t, T["rails0"], T["rails0"] + 0.9)) if story else 1.0
    rails.scale = (1, 1, max(0.001, rk))
    rails.location = (0, 0, PIT * (1 - rk))
    gk = ease_out(seg(t, T["gear0"], T["gear0"] + 0.5)) if story else 1.0
    for g, jaws in GEAR:
        g.scale = (max(0.001, gk),) * 3
    bk = ease_out(seg(t, T["buf0"], T["buf0"] + 0.5)) if story else 1.0
    buffers.scale = (1, 1, max(0.001, bk))
    # the motor: huge and straining while it lifts the car alone, normal with the counterweight
    big = smooth(seg(t, T["motor0"], T["motor0"] + 0.5)) * (1 - smooth(seg(t, T["motor1"], T["motor1"] + 0.6))) if story else 0
    strain = big * 0.03 * math.sin(t * 40)
    motor.scale = (1 + 1.1 * big,) * 3
    motor.location = (-1.2 - 0.9 * big + strain, 0.35, TOP + 1.45 + 0.45 * big)

    # ---- safety gear jaws (engaged in the hook stop, the bite and the governor stop)
    eng = 0.0
    if T_STOP - 0.05 < t < 3.0:
        eng = 1.0
    if t >= T["bite"] - 0.3 and t < S(11) - 0.1:
        eng = smooth(seg(t, T["bite"] - 0.3, T["bite"] - 0.1))
    if T["yank"] - 0.1 < t < S(14):
        eng = smooth(seg(t, T["yank"] - 0.1, T["yank"] + 0.1))
    for g, jaws in GEAR:
        for j, sy in jaws:
            j.location = (0, sy * lerp(0.17, 0.085, eng), 0)
    highlight_gear = flash_amount(t, TERMS["safety gear"])
    for g, jaws in GEAR:
        highlight(g, highlight_gear)

    # ---- sparks where the jaws bite
    bites = [T_STOP - 0.05, T["bite"] - 0.3, T["yank"] - 0.1]

    def spark(i):
        for bt in bites:
            if bt < t < bt + 0.9:
                R_ = rng(i * 7 + int(bt * 10))
                ph = ((t - bt) * 2.6 + R_.random() * 0.4) % 1.0
                if t - bt > 0.6 and ph > 0.6:
                    return None
                sx = (-1, 1)[i % 2]
                p0 = car.matrix_world @ Vector((sx * RAIL_X, 0, -0.15))
                v = Vector((sx * R_.uniform(0.2, 1.4), R_.uniform(-1.5, 0.3), R_.uniform(0.5, 2.5)))
                p = p0 + v * ph * 0.7 + Vector((0, 0, -3.0 * ph * ph))
                return (p, (0, 0, 0), 1.2 * (1 - ph))
        return None

    SPARKS.drive(spark)

    def streak(i):                                   # speed lines while the car free-falls
        if not (T_SNAP + 0.15 < t < T_STOP + 0.05):
            return None
        R_ = rng(i + 40)
        v = 9.8 * (t - T_SNAP)
        ph = ((t * (0.6 + v * 0.12) + R_.random()) % 1.0)
        x = R_.choice((-1, 1)) * R_.uniform(1.0, 1.9)
        p = Vector((x, R_.uniform(-1.9, -1.0), z - 2.0 + 6.0 * ph))
        return (p, (0, 0, 0), (1, 1, 0.4 + v * 0.18))

    STREAKS.drive(streak)

    # ---- hoist ropes: car crosshead -> sheave front; sheave back -> counterweight
    bpy.context.view_layer.update()
    n = n_ropes(t)
    intact = ropes_intact(t)
    cw_z = (TOP - 1.2) - (z - 0.0) * 1.0 if vis_cw else TOP
    cw_z = max(PIT + 1.0, min(TOP - 2.6, (TOP - 4.0) - z + 0.5))
    if not intact and t < T["rewind1"]:
        cw_z = max(PIT + 1.0, (TOP - 4.0) - Z0 + 0.5)
    cwt.location = (0, CW_Y, cw_z)
    for k in range(4):
        show = k < n or (k == 0)
        x = ROPE_X[k] if n == 4 else 0.0
        a = car.matrix_world @ Vector((x, 0, CAR_H + 0.53))
        top = Vector((x * 0.6, SHEAVE.y - SHEAVE_R, SHEAVE.z))
        if intact:
            place_rope(ROPES[k], a, top, show and (k < n))
            hide(ROPE_TOP[k], True)
        else:
            # snapped near the top: the car keeps a short tail, the upper end whips up and away
            ts = T_SNAP if t < 3.0 else T["snap2"]
            whip = ease_out(seg(t, ts, ts + 0.35))
            brk = Vector((x * 0.6, SHEAVE.y - SHEAVE_R, SHEAVE.z - 2.0))
            tail = a + (Vector((0, 0, 1)) * 1.6)
            place_rope(ROPES[k], a, tail + Vector((0.15 * math.sin(t * 20 + k), 0, 0)), show and (k < n))
            place_rope(ROPE_TOP[k], top, brk.lerp(top, whip * 0.8) + Vector((0.3 * whip * (k - 1.5), -0.2 * whip, 0)),
                       show and (k < n))
        cwtop = Vector((x * 0.6, SHEAVE.y + SHEAVE_R, SHEAVE.z))
        place_rope(ROPES_CW[k], Vector((x * 0.6, CW_Y, cw_z + 2.3)), cwtop, vis_cw and k < n and intact)
    SHEAVE_SPIN.rotation_euler = (z / SHEAVE_R, 0, 0)

    # ---- governor: wheel turns with the car, flyweights swing out when too fast, pawl locks it
    locked = T["lock"] < t < S(14) or (T_STOP - 0.1 < t < 3.0)
    spin = z / 0.34
    if T["lock"] < t < S(14):
        spin = car_z(T["lock"]) / 0.34
    if T_STOP - 0.1 < t < 3.0:
        spin = hook_z(T_STOP - 0.1) / 0.34
    GOV_SPIN.rotation_euler = (spin, 0, 0)
    fly_out = 0.0
    if T["fast"] - 0.2 < t < S(14):
        fly_out = smooth(seg(t, T["fast"], T["lock"]))
    if t < 3.0 and t > T_SNAP:
        fly_out = smooth(seg(t, T_SNAP, T_STOP - 0.2))
    for piv, sz in FLY:
        piv.rotation_euler = (D(-sz * 55 * fly_out), 0, 0)
    pawl.rotation_euler = (D(-35 * (1 if locked else 0)), 0, 0)
    highlight(gov, flash_amount(t, TERMS["overspeed governor"]))
    # governor rope loop: down from the wheel to the pit sheave on both sides; one side clips to the car's lever
    lev = car.matrix_world @ Vector((0.98, -0.75, 0.4))
    gx = 1.2
    for gr, p0, p1 in ((GOV_ROPES[0], Vector((gx, GOV.y - 0.34, GOV.z)), lev),
                       (GOV_ROPES[1], lev, Vector((gx, GOV.y - 0.2, PIT + 0.45))),
                       (GOV_ROPES[2], Vector((gx, GOV.y + 0.34, GOV.z)), Vector((gx, GOV.y + 0.2, PIT + 0.45)))):
        place_rope(gr, p0, p1, vis_gov)

    # ---- buffers squash when the car lands on them
    sq = 0.0
    if T["land"] - 0.2 < t < S(16):
        sq = smooth(seg(t, T["land"] - 0.2, T["land"] + 0.5))
    for bf in BUF[:2]:
        bf.scale = (1, 1, max(0.001, bk * (1 - 0.2 * sq)))
    highlight(buffers, flash_amount(t, TERMS["buffers"]))
    highlight(cwt, flash_amount(t, TERMS["counterweight"]))

    # ---- power: building lights, car light, brake magnet
    power = 1.0 - smooth(seg(t, T["cut"], T["cut"] + 0.25)) * (1 - smooth(seg(t, T["lower1"] + 0.3, T["lower1"] + 1.2)))
    K.set_emit(M["window"], 1.6 * power, (1.0, 0.85, 0.55))
    K.set_emit(M["lamp"], 2.2 * power, (1.0, 0.92, 0.75))
    held = power
    if S(18) - 0.2 < t < W("power", S(18)) + 0.1:          # re-show "held open by electricity" before it drops
        held = 1.0
    if t >= W("power", S(18)) and t < T["lower1"] + 0.3:
        held = 1.0 - smooth(seg(t, W("power", S(18)), W("power", S(18)) + 0.25))
    if T["tech0"] + 0.6 < t < T["lower1"]:                   # technician eases the brake by hand
        held = 0.55
    K.set_emit(M["magnet"], 2.5 * (held if held > 0.9 else 0.0), (0.4, 0.7, 1.0))
    for sh, sy in SHOES:
        gap = lerp(0.02, 0.16, held)
        sh.location = BRK + Vector((0, sy * (0.36 + 0.06 + gap), 0))
    highlight(machine, 0)

    # ---- landing doors (closed; the floor-2 door opens after the rescue)
    for dl, dr, zz in DOORS:
        op = 0.0
        if abs(zz - 2 * FH) < 0.1 and T["lower1"] < t < T["back"]:
            op = smooth(seg(t, T["lower1"], T["lower1"] + 0.8))
        dl.location = (-0.33 - 0.62 * op, SY + 0.02, zz + 1.17)
        dr.location = (0.33 + 0.62 * op, SY + 0.02, zz + 1.17)

    # ---- people
    for m in [YOU, TECH, OTIS, AXE] + CROWD:
        m.hide(True)
        m.set_tint("none")
    YOU.hide(False)
    YOU.root.parent = car
    YOU.root.location = (0.2, 0.05, 0.0)
    YOU.root.rotation_euler = (0, 0, D(-15))
    YOU.root.scale = (1, 1, 1)
    YOU.pose("stand")
    if T_SNAP < t < 3.0:                               # the drop: float up, then knocked down by the stop
        if t < T_STOP:
            fl = seg(t, T_SNAP, T_STOP)
            YOU.root.location = (0.2, 0.05, 0.25 * fl)
            YOU.pose(blend("stand", "cheer", fl))
        else:
            YOU.pose(blend("cheer", "cower", smooth(seg(t, T_STOP, T_STOP + 0.2))))
        YOU.set_tint("blue", seg(t, T_SNAP, 0.6))
    if T["snap2"] < t < T["bite"] + 0.6:
        fr = t < T["bite"] - 0.3
        YOU.root.location = (0.2, 0.05, 0.25 if fr else 0.0)
        YOU.pose("cheer" if fr else blend("cheer", "cower", seg(t, T["bite"] - 0.3, T["bite"])))
        YOU.set_tint("blue", 1.0)
    if T["fast"] < t < T["yank"] + 0.5:
        YOU.pose(blend("stand", "cower", smooth(seg(t, T["fast"], T["lock"]))))
        YOU.set_tint("blue", smooth(seg(t, T["fast"], T["lock"])))
    if S(16) - 0.3 < t < S(17):
        YOU.set_tint("orange", smooth(seg(t, S(16) - 0.3, S(16) + 0.3)))
        YOU.pose("relax")
    if T["cut"] < t < T["lower1"] + 0.6:
        YOU.set_tint("blue", smooth(seg(t, T["cut"], T["cut"] + 0.4)) * (1 - seg(t, T["lower1"], T["lower1"] + 0.6)))
        YOU.pose("shrug" if t < S(19) else "look_up")
    if T["buf0"] + 0.4 < t < S(16):                    # "if everything still fails": the car is empty
        YOU.hide(True)
    # technician in the machine room
    if T["tech0"] - 0.5 < t < E(19) + 0.3:
        TECH.hide(False)
        TECH.root.parent = None
        TECH.place((-2.05, -0.6, TOP + 0.3), 0)
        TECH.face((-2.05, 0.35, TOP + 1.4))
        turn = seg(t, T["tech0"] + 0.6, T["lower1"])
        hw.rotation_euler = (turn * 6.0, 0, 0)
        TECH.pose({"shL": (80 + 20 * math.sin(turn * 18), 6, 0), "elL": 40, "shR": (80 - 20 * math.sin(turn * 18), 6, 0),
                   "elR": 40, "spine": (12, 0, 0)})
    # Otis 1854
    otis_on = T["otis"] - 0.5 < t < T["back"] + 0.6
    hide(otis_rig, not otis_on)
    hide(platform, not otis_on)
    hide(top_hat, not otis_on)
    hide(axe, not otis_on)
    hide(ot_rope, not otis_on)
    hide(ot_rope2, not otis_on)
    if otis_on:
        drop = 0.18 * ease_in(seg(t, T["axe"] + 0.1, T["axe"] + 0.3))
        pz = 4.5 - drop + 0.03 * pulse(t, T["axe"] + 0.3, T["axe"] + 0.5)
        platform.location = (OX, OY, pz)
        cut = t > T["axe"] + 0.05
        place_rope(ot_rope, Vector((OX, OY, pz + 1.55)), Vector((OX, OY, 8.1)) if not cut else Vector((OX, OY, pz + 2.1)), True)
        place_rope(ot_rope2, Vector((OX, OY, 8.1)), Vector((OX + 2.3, OY + 0.4, 1.3)) if not cut else Vector((OX + 2.3, OY + 0.4, 1.3)),
                   True)
        OTIS.hide(False)
        OTIS.root.parent = None
        OTIS.place((OX, OY, pz + 0.06), 0)
        OTIS.pose(blend("stand", "wave", smooth(seg(t, T["axe"] + 0.4, T["axe"] + 1.0))) if t > T["axe"] else
                  blend("stand", "point", pulse(t, W("rope", S(20)) - 0.6, T["axe"] + 0.1)))
        bpy.context.view_layer.update()
        top_hat.matrix_world = OTIS.neck.matrix_world @ Matrix.Translation((0, -0.01, 0.31))
        AXE.hide(False)
        AXE.root.parent = None
        AXE.place((OX + 2.6, OY + 0.2, 0), 0)
        AXE.face((OX + 2.3, OY + 0.4, 0))
        sw = pulse(t, T["axe"] - 0.35, T["axe"] + 0.15)
        AXE.pose({"shR": (150 - 110 * sw, 10, 0), "elR": 20, "shL": (120 - 80 * sw, -10, 0), "elL": 30, "spine": (10 * sw, 0, 0)})
        bpy.context.view_layer.update()
        axe.matrix_world = AXE.j["elR"].matrix_world @ Matrix.Translation((0, 0, -0.3)) @ Matrix.Rotation(D(180), 4, "X")
        for i, m in enumerate(CROWD):
            m.hide(False)
            m.root.parent = None
            m.place((OX - 4.0 + 1.7 * i, OY - 4.0 - 0.5 * (i % 2), 0), 0)
            m.face((OX, OY, 0))
            m.pose(blend("look_up", "cheer", smooth(seg(t, T["stop_ot"] + 0.2 * i, T["stop_ot"] + 0.6 + 0.2 * i))))


K.run(animate, BASE, NF, default_snaps=[0, 15, 30, 45, 60, 90, 150, 250, 330, 450, 560, 640, 700, 790, 870, 1000, 1080,
                                        1180, 1300, 1400, 1520, 1600, 1700, 1800, 1900, 2000, 2150, 2280, 2350, 2400, 2432])
