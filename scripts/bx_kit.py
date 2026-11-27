"""bx_kit.py - reusable Blender 5.2 kit for /build-explainer films (stylized low-poly "build it from scratch" explainers).

Import it from a film's build.py (the film copies this file next to build.py so later kit edits never break old films):
    import sys; sys.path.insert(0, str(BASE)); import bx_kit as K
    K.setup_scene(res=(1080, 1920), fps=30, samples=24)

Everything is a pure function of the frame: the film's animate(f) sets every transform/material value for frame f,
then render_frame() renders it. No keyframes, no simulation state -> any frame can be rendered alone, in any order.

Contents
  scene/look   setup_scene(), sky + sun, distance fog baked into every kit material, inverted-hull toon outline
  materials    mat(), brick_mat(), water_mat(), flame_mat(); every kit material carries the HIGHLIGHT hook:
               highlight(obj, amount) turns that object solid yellow (object colour R channel, no material copies)
  geometry     box(), cyl(), sphere(), ring_sector(), stick() (stretch a cylinder between two points), hide()
  Mannequin    faceless jointed wooden figure, pose library POSES + walk/climb cycles, blend(), tint (blue/orange/red)
  Swarm        n linked-duplicate particles driven by a function (i, f) -> (loc, rot, scale, visible)
  CamPath      ONE continuous camera: keys (t, pos, target, lens) -> centripetal Catmull-Rom + gentle drift
  anchors      anchor(name, obj|point) ; dump_anchors(f) writes anchors/f_####.json (screen xy) for the 2D overlay pass
  easing       clamp, smooth, seg, ease_out, ease_in, overshoot, lerp, lerpv, noise1, rng(seed)
"""
import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Matrix, Vector

scene = None
RES = (1080, 1920)
FPS = 30
FOG = {"near": 35.0, "far": 230.0, "max": 0.85, "color": (0.74, 0.80, 0.86)}
OUTLINE = {"on": True, "color": (0.10, 0.09, 0.08), "w": 0.035}
HL_YELLOW = (1.0, 0.78, 0.08)
_ANCHORS = {}


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = clamp(x)
    return x ** 3


def overshoot(x, c=1.7):
    x = clamp(x)
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def lerp(a, b, t):
    return a + (b - a) * t


def lerpv(a, b, t):
    return Vector(tuple(lerp(x, y, t) for x, y in zip(a, b)))


def seg(x, a, b):
    """0..1 progress of x through [a, b] (works in seconds or frames)."""
    return clamp((x - a) / max(1e-6, b - a))


def pulse(x, a, b):
    """0 -> 1 -> 0 over [a, b] (sine bump)."""
    return math.sin(seg(x, a, b) * math.pi) if a <= x <= b else 0.0


def noise1(t, seed=0.0):
    return (math.sin(t * 1.7 + seed) * 0.5 + math.sin(t * 2.9 + seed * 2.3) * 0.3
            + math.sin(t * 5.3 + seed * 0.7) * 0.2)


def rng(seed):
    return random.Random(seed)


def D(a):
    return math.radians(a)


def lin(c):
    """Author colours as sRGB picker values; shaders want linear."""
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


# ------------------------------------------------------------------ scene + look
def setup_scene(res=(1080, 1920), fps=30, samples=24, draft=False, sky=(0.62, 0.74, 0.88), horizon=None,
                sun_dir=(-35, 0, -40), sun_energy=3.2, sun_color=(1.0, 0.95, 0.86), sky_strength=0.9,
                look="AgX - Medium High Contrast"):
    """Factory-empty scene, EEVEE, AgX, soft daylight. Returns the scene."""
    global scene, RES, FPS
    RES, FPS = res, fps
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            pass
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 50 if draft else 100
    scene.render.fps = fps
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 93
    ee = scene.eevee
    ee.taa_render_samples = 8 if draft else samples
    for attr, val in (("use_shadows", True), ("use_gtao", True), ("use_raytracing", False),
                      ("shadow_ray_count", 1), ("shadow_step_count", 6)):
        try:
            setattr(ee, attr, val)
        except (AttributeError, TypeError):
            pass
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = look
    except TypeError:
        pass
    if horizon:
        FOG["color"] = horizon
    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    # vertical gradient: horizon (fog colour) -> sky
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 0.45
    ramp = nt.nodes.new("ShaderNodeMix")
    ramp.data_type = "RGBA"
    ramp.inputs[6].default_value = (*lin(FOG["color"]), 1)
    ramp.inputs[7].default_value = (*lin(sky), 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Factor"])
    nt.links.new(ramp.outputs[2], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = sky_strength
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = sun_energy
    sun.color = sun_color
    sun.angle = D(4)
    so = bpy.data.objects.new("sun", sun)
    scene.collection.objects.link(so)
    so.rotation_euler = Euler((D(sun_dir[0]), D(sun_dir[1]), D(sun_dir[2])))
    try:
        sun.use_shadow_jitter = False
    except AttributeError:
        pass
    return scene


def link(obj):
    scene.collection.objects.link(obj)
    return obj


def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    link(e)
    e.parent = parent
    e.location = loc
    return e


# ------------------------------------------------------------------ materials
def _fog_and_highlight(m, shader_out, base_socket=None):
    """Insert the highlight hook (object colour R: 1 = normal, 0 = full yellow) and distance fog."""
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(oi.outputs["Color"], sep.inputs[0])
    nt.links.new(sep.outputs[0], inv.inputs[1])
    hl_em = nt.nodes.new("ShaderNodeEmission")
    hl_em.inputs["Color"].default_value = (*lin(HL_YELLOW), 1)
    hl_em.inputs["Strength"].default_value = 1.15
    mix_hl = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(inv.outputs[0], mix_hl.inputs[0])
    nt.links.new(shader_out, mix_hl.inputs[1])
    nt.links.new(hl_em.outputs[0], mix_hl.inputs[2])
    cd = nt.nodes.new("ShaderNodeCameraData")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = FOG["near"]
    mr.inputs["From Max"].default_value = FOG["far"]
    mr.inputs["To Max"].default_value = FOG["max"]
    nt.links.new(cd.outputs["View Distance"], mr.inputs["Value"])
    fog_em = nt.nodes.new("ShaderNodeEmission")
    fog_em.inputs["Color"].default_value = (*lin(FOG["color"]), 1)
    mix_fog = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mr.outputs["Result"], mix_fog.inputs[0])
    nt.links.new(mix_hl.outputs[0], mix_fog.inputs[1])
    nt.links.new(fog_em.outputs[0], mix_fog.inputs[2])
    nt.links.new(mix_fog.outputs[0], out.inputs["Surface"])


def mat(name, color, rough=0.75, emit=0.0, emit_col=None, metal=0.0, fog=True, alpha=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*lin(color), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    try:
        b.inputs["Specular IOR Level"].default_value = 0.3
    except KeyError:
        pass
    if emit:
        b.inputs["Emission Color"].default_value = (*lin(emit_col or color), 1)
        b.inputs["Emission Strength"].default_value = emit
    if alpha is not None:
        b.inputs["Alpha"].default_value = alpha
        for attr, val in (("surface_render_method", "BLENDED"),):
            try:
                setattr(m, attr, val)
            except (AttributeError, TypeError):
                pass
    if fog:
        _fog_and_highlight(m, b.outputs[0])
    m["bsdf"] = b.name
    return m


def set_color(m, color):
    """Per-frame base colour change (tints, burning, wet)."""
    b = m.node_tree.nodes[m["bsdf"]]
    b.inputs["Base Color"].default_value = (*lin(color), 1)


def set_emit(m, strength, color=None):
    b = m.node_tree.nodes[m["bsdf"]]
    b.inputs["Emission Strength"].default_value = strength
    if color:
        b.inputs["Emission Color"].default_value = (*lin(color), 1)


def brick_mat(name, c1, c2, mortar, scale=1.6, rough=0.85, row_h=0.5, local=False):
    """local=False: world coords (pattern stays fixed while pieces drop in... use local=True for moving parts)."""
    """Stone/brick courses in object space (stays put while the object moves)."""
    m = mat(name, c1, rough=rough, fog=False)
    nt = m.node_tree
    b = nt.nodes[m["bsdf"]]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    bt = nt.nodes.new("ShaderNodeTexBrick")
    bt.inputs["Color1"].default_value = (*lin(c1), 1)
    bt.inputs["Color2"].default_value = (*lin(c2), 1)
    bt.inputs["Mortar"].default_value = (*lin(mortar), 1)
    bt.inputs["Scale"].default_value = scale
    bt.inputs["Mortar Size"].default_value = 0.025
    bt.inputs["Brick Width"].default_value = 1.1
    bt.inputs["Row Height"].default_value = row_h
    bt.offset = 0.5
    # brick texture is 2D: feed it (x + y, z) so courses run horizontally on walls facing X and Y alike
    sp = nt.nodes.new("ShaderNodeSeparateXYZ")
    ad = nt.nodes.new("ShaderNodeMath")
    cb = nt.nodes.new("ShaderNodeCombineXYZ")
    src = tc.outputs["Object"] if local else nt.nodes.new("ShaderNodeNewGeometry").outputs["Position"]
    nt.links.new(src, sp.inputs[0])
    nt.links.new(sp.outputs["X"], ad.inputs[0])
    nt.links.new(sp.outputs["Y"], ad.inputs[1])
    nt.links.new(ad.outputs[0], cb.inputs["X"])
    nt.links.new(sp.outputs["Z"], cb.inputs["Y"])
    nt.links.new(cb.outputs[0], bt.inputs["Vector"])
    nt.links.new(bt.outputs["Color"], b.inputs["Base Color"])
    _fog_and_highlight(m, b.outputs[0])
    return m


def outline_mat():
    if "outline" in bpy.data.materials:
        return bpy.data.materials["outline"]
    m = bpy.data.materials.new("outline")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*lin(OUTLINE["color"]), 1)
    em.inputs["Strength"].default_value = 1.0
    # fade outlines into the fog with distance
    cd = nt.nodes.new("ShaderNodeCameraData")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = FOG["near"] * 0.6
    mr.inputs["From Max"].default_value = FOG["far"] * 0.6
    fog_em = nt.nodes.new("ShaderNodeEmission")
    fog_em.inputs["Color"].default_value = (*lin(FOG["color"]), 1)
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(cd.outputs["View Distance"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], mx.inputs[0])
    nt.links.new(em.outputs[0], mx.inputs[1])
    nt.links.new(fog_em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    m.use_backface_culling = True
    try:
        m.use_backface_culling_shadow = True
    except AttributeError:
        pass
    return m


def add_outline(o, w=None):
    """Inverted-hull toon outline (cheap in EEVEE, renders deterministically)."""
    if not OUTLINE["on"] or o.type != "MESH":
        return o
    om = outline_mat()
    if om.name not in [s.name for s in o.data.materials if s]:
        o.data.materials.append(om)
    sm = o.modifiers.new("outline", "SOLIDIFY")
    sm.thickness = -(w if w is not None else OUTLINE["w"])
    sm.offset = 1.0
    sm.use_flip_normals = True
    sm.use_rim = False
    sm.material_offset = len(o.data.materials) - 1
    try:
        sm.use_even_offset = False
    except AttributeError:
        pass
    o.visible_shadow = True
    return o


# ------------------------------------------------------------------ geometry
def _finish(name, bm, m, parent, loc, bevel, outline):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    o = bpy.data.objects.new(name, me)
    link(o)
    o.parent = parent
    o.location = loc
    if m is not None:
        me.materials.append(m)
    if bevel:
        bv = o.modifiers.new("bevel", "BEVEL")
        bv.width = bevel
        bv.segments = 2
        bv.limit_method = "ANGLE"
    if outline:
        add_outline(o, None if outline is True else outline)
    return o


def box(name, loc, size, m, parent=None, off=(0, 0, 0), bevel=0.0, outline=True, base=False):
    """Axis box. base=True puts the origin at the bottom face (so scale.z 'grows' it from the ground)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    oz = size[2] / 2 if base else 0
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0] + off[0], v.co.y * size[1] + off[1], v.co.z * size[2] + off[2] + oz))
    return _finish(name, bm, m, parent, loc, bevel, outline)


def cyl(name, loc, r, h, m, parent=None, off=(0, 0, 0), seg_n=16, r2=None, axis="Z", bevel=0.0, outline=True,
        base=False):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg_n, radius1=r,
                          radius2=r if r2 is None else r2, depth=h)
    for v in bm.verts:
        c = v.co.copy()
        if base:
            c.z += h / 2
        if axis == "X":
            c = Vector((c.z, c.y, c.x))
        elif axis == "Y":
            c = Vector((c.x, c.z, c.y))
        v.co = c + Vector(off)
    o = _finish(name, bm, m, parent, loc, bevel, outline)
    for p in o.data.polygons:
        p.use_smooth = len(p.vertices) == 4
    return o


def sphere(name, loc, r, m, parent=None, scale=(1, 1, 1), seg_u=16, seg_v=10, outline=True, smooth_shade=True):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg_u, v_segments=seg_v, radius=r)
    for v in bm.verts:
        v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
    o = _finish(name, bm, m, parent, loc, 0, outline)
    for p in o.data.polygons:
        p.use_smooth = smooth_shade
    return o


def ring_sector(name, loc, r_in, r_out, h, a0, a1, m, parent=None, n=24, outline=True):
    """Thick arc (tower shell / cutaway). Angles in degrees, CCW from +X. Origin at the base centre."""
    bm = bmesh.new()
    rows = []
    for i in range(n + 1):
        a = D(a0 + (a1 - a0) * i / n)
        c, s = math.cos(a), math.sin(a)
        rows.append([bm.verts.new((r_in * c, r_in * s, 0)), bm.verts.new((r_out * c, r_out * s, 0)),
                     bm.verts.new((r_out * c, r_out * s, h)), bm.verts.new((r_in * c, r_in * s, h))])
    for i in range(n):
        A, B = rows[i], rows[i + 1]
        for k in range(4):
            bm.faces.new((A[k], B[k], B[(k + 1) % 4], A[(k + 1) % 4]))
    if abs((a1 - a0) % 360) > 1e-3:
        bm.faces.new(tuple(reversed(rows[0])))
        bm.faces.new(tuple(rows[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _finish(name, bm, m, parent, loc, 0, outline)
    return o


def multi_box(name, boxes, m, parent=None, loc=(0, 0, 0), outline=True, bevel=0.0):
    """Many boxes in ONE mesh object: boxes = [(center, size), ...] (centres relative to loc)."""
    bm = bmesh.new()
    for c, sz in boxes:
        r = bmesh.ops.create_cube(bm, size=1.0)
        for v in r["verts"]:
            v.co = Vector((v.co.x * sz[0] + c[0], v.co.y * sz[1] + c[1], v.co.z * sz[2] + c[2]))
    return _finish(name, bm, m, parent, loc, bevel, outline)


def gable(name, loc, w, d, h, m, parent=None, overhang=0.25, outline=True):
    """Pitched roof: ridge along X (width w), slopes down to the +-Y eaves (depth d), height h. Origin at eave level."""
    bm = bmesh.new()
    x0, x1 = -w / 2 - overhang, w / 2 + overhang
    y0, y1 = -d / 2 - overhang, d / 2 + overhang
    v = [bm.verts.new(p) for p in ((x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0), (x0, 0, h), (x1, 0, h))]
    for f in ((0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)):
        bm.faces.new([v[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish(name, bm, m, parent, loc, 0, outline)


def join(objs, name):
    """Join meshes into one object (fewer objects = faster scene updates)."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


def stick(obj, p0, p1):
    """Place a unit-length Z cylinder (made with base=True, h=1) from p0 to p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    obj.location = p0
    obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    obj.scale = (1, 1, max(1e-4, d.length))


def hide(obj, h):
    obj.hide_render = h
    obj.hide_viewport = h
    for c in obj.children:
        hide(c, h)


def highlight(obj, amount, recursive=True):
    """0 = normal, 1 = solid yellow (flash on the narrator's term)."""
    a = clamp(amount)
    obj.color = (1 - a, 1, 1, 1)
    if recursive:
        for c in obj.children:
            highlight(c, a)


def flash_amount(t, t0, hold=1.2, blinks=2):
    """Typical term flash: on at t0, blinks, then fades by t0+hold."""
    if t < t0 or t > t0 + hold + 0.4:
        return 0.0
    x = t - t0
    if x < hold * 0.55:
        return 0.55 + 0.45 * abs(math.cos(x / (hold * 0.55) * math.pi * blinks))
    return 1.0 - seg(x, hold * 0.55, hold + 0.4)


# ------------------------------------------------------------------ mannequin
WOOD = (0.80, 0.64, 0.45)
TINTS = {"none": None, "blue": (0.42, 0.58, 0.86), "orange": (0.98, 0.62, 0.26), "red": (0.80, 0.30, 0.24),
         "grey": (0.55, 0.55, 0.57)}

# Pose library: semantic angles in degrees. Limbs: (fwd, out, twist); elbows/knees: bend; spine/neck: (fwd, side, twist).
# hipz = pelvis height offset (m). Missing keys = 0.
POSES = {
    "stand": {},
    "relax": {"shL": (5, 40, 0), "elL": 110, "shR": (5, 40, 0), "elR": 110, "spine": (-4, 0, 0)},   # hands on hips
    "cower": {"spine": (38, 0, 0), "neck": (25, 0, 0), "shL": (140, 25, 0), "elL": 120, "shR": (140, 25, 0),
              "elR": 120, "thL": (55, 8, 0), "knL": 85, "thR": (55, 8, 0), "knR": 85, "hipz": -0.28},
    "cheer": {"shL": (165, 25, 0), "elL": 15, "shR": (165, 25, 0), "elR": 15, "neck": (-15, 0, 0)},
    "point": {"shR": (85, 5, 0), "elR": 5, "shL": (10, 8, 0), "elL": 15},
    "shrug": {"shL": (10, 30, 0), "elL": 95, "shR": (10, 30, 0), "elR": 95, "neck": (0, 12, 0)},
    "look_up": {"neck": (-35, 0, 0), "spine": (-8, 0, 0), "shL": (5, 10, 0), "shR": (5, 10, 0)},
    "aim_bow": {"shL": (90, 0, 0), "elL": 0, "shR": (90, 0, -90), "elR": 150, "spine": (0, 0, -15),
                "neck": (0, 0, 15)},
    "duck": {"spine": (55, 0, 0), "neck": (10, 0, 0), "shL": (150, 15, 0), "elL": 130, "shR": (150, 15, 0),
             "elR": 130, "thL": (70, 6, 0), "knL": 110, "thR": (70, 6, 0), "knR": 110, "hipz": -0.42},
    "carry": {"shL": (55, 5, 0), "elL": 60, "shR": (55, -5, 0), "elR": 60, "spine": (10, 0, 0)},
    "push": {"shL": (80, 8, 0), "elL": 25, "shR": (80, 8, 0), "elR": 25, "spine": (22, 0, 0), "thL": (30, 0, 0),
             "knL": 30, "thR": (-15, 0, 0), "knR": 10},
    "pour": {"shL": (75, -8, 0), "elL": 50, "shR": (75, -8, 0), "elR": 50, "spine": (35, 0, 0), "neck": (25, 0, 0)},
    "sit": {"thL": (90, 4, 0), "knL": 90, "thR": (90, 4, 0), "knR": 90, "hipz": -0.45, "shL": (20, 6, 0),
            "elL": 40, "shR": (20, 6, 0), "elR": 40},
    "fallen": {"shL": (170, 40, 0), "shR": (170, 40, 0), "thL": (10, 15, 0), "thR": (10, 15, 0)},
    "hold_up": {"shL": (160, 10, 0), "elL": 20, "shR": (160, 10, 0), "elR": 20},   # holding something overhead
    "wave": {"shR": (160, 30, 0), "elR": 35, "shL": (5, 8, 0)},
}
_JOINTS = ("spine", "neck", "shL", "elL", "shR", "elR", "thL", "knL", "thR", "knR", "hipz")


def blend(a, b, k):
    """Blend two pose dicts (or names)."""
    a = POSES[a] if isinstance(a, str) else a
    b = POSES[b] if isinstance(b, str) else b
    out = {}
    for j in _JOINTS:
        va, vb = a.get(j), b.get(j)
        if va is None and vb is None:
            continue
        if j in ("elL", "elR", "knL", "knR", "hipz"):
            out[j] = lerp(va or 0.0, vb or 0.0, k)
        else:
            va, vb = va or (0, 0, 0), vb or (0, 0, 0)
            out[j] = tuple(lerp(x, y, k) for x, y in zip(va, vb))
    return out


def walk_pose(phase, amt=1.0):
    s = math.sin(phase)
    return {"thL": (28 * s * amt, 3, 0), "thR": (-28 * s * amt, 3, 0),
            "knL": max(0, -s) * 45 * amt + 6, "knR": max(0, s) * 45 * amt + 6,
            "shL": (-22 * s * amt, 6, 0), "shR": (22 * s * amt, 6, 0), "elL": 18, "elR": 18,
            "hipz": -0.03 + 0.04 * abs(math.cos(phase)) * amt, "spine": (4, 0, 0)}


def climb_pose(phase):
    s = math.sin(phase)
    return {"shL": (150 + 20 * s, 10, 0), "elL": 40 - 30 * s, "shR": (150 - 20 * s, 10, 0), "elR": 40 + 30 * s,
            "thL": (60 + 30 * s, 6, 0), "knL": 80 + 30 * s, "thR": (60 - 30 * s, 6, 0), "knR": 80 - 30 * s,
            "spine": (8, 0, 0), "neck": (-15, 0, 0)}


class Mannequin:
    """Faceless jointed wooden figure, ~1.8 m. Front = -Y, character right = -X. Origin at the feet."""

    def __init__(self, name, tint="none", scale=1.0, outline_w=0.018):
        self.name = name
        self.m = mat(f"{name}_wood", WOOD, rough=0.55)
        self.mj = mat(f"{name}_joint", tuple(c * 0.82 for c in WOOD), rough=0.5)
        self.base_tint = tint
        self.root = empty(f"{name}_root")
        self.root.scale = (scale,) * 3
        self.hip = empty(f"{name}_hip", (0, 0, 0.98), self.root)
        ow = outline_w
        sphere(f"{name}_pelvis", (0, 0, 0.02), 0.15, self.m, self.hip, scale=(1.25, 0.85, 0.8), outline=ow)
        self.spine = empty(f"{name}_spine", (0, 0, 0.08), self.hip)
        sphere(f"{name}_belly", (0, 0, 0.14), 0.11, self.mj, self.spine, outline=ow)
        sphere(f"{name}_chest", (0, 0, 0.36), 0.17, self.m, self.spine, scale=(1.25, 0.8, 1.15), outline=ow)
        self.neck = empty(f"{name}_neck", (0, 0, 0.56), self.spine)
        cyl(f"{name}_neckm", (0, 0, 0), 0.04, 0.1, self.mj, self.neck, off=(0, 0, 0.04), seg_n=10, outline=ow)
        sphere(f"{name}_head", (0, -0.01, 0.2), 0.115, self.m, self.neck, scale=(0.92, 1.0, 1.22), outline=ow)
        self.j = {"spine": self.spine, "neck": self.neck}
        for side, sx in (("L", 1), ("R", -1)):
            sh = empty(f"{name}_sh{side}", (0.23 * sx, 0, 0.46), self.spine)
            sh.rotation_mode = "ZXY"      # twist = about the arm's own axis (lets the elbow bend sideways, e.g. drawing a bow)
            sphere(f"{name}_shb{side}", (0, 0, 0), 0.055, self.mj, sh, outline=ow)
            cyl(f"{name}_ua{side}", (0, 0, 0), 0.05, 0.27, self.m, sh, off=(0, 0, -0.15), seg_n=10, r2=0.042,
                outline=ow)
            el = empty(f"{name}_el{side}", (0, 0, -0.3), sh)
            sphere(f"{name}_elb{side}", (0, 0, 0), 0.042, self.mj, el, outline=ow)
            cyl(f"{name}_fa{side}", (0, 0, 0), 0.042, 0.24, self.m, el, off=(0, 0, -0.13), seg_n=10, r2=0.034,
                outline=ow)
            sphere(f"{name}_hand{side}", (0, 0, -0.29), 0.05, self.m, el, scale=(0.7, 0.9, 1.25), outline=ow)
            th = empty(f"{name}_th{side}", (0.1 * sx, 0, 0), self.hip)
            sphere(f"{name}_hipb{side}", (0, 0, 0), 0.065, self.mj, th, outline=ow)
            cyl(f"{name}_thm{side}", (0, 0, 0), 0.07, 0.4, self.m, th, off=(0, 0, -0.22), seg_n=10, r2=0.055,
                outline=ow)
            kn = empty(f"{name}_kn{side}", (0, 0, -0.45), th)
            sphere(f"{name}_knb{side}", (0, 0, 0), 0.052, self.mj, kn, outline=ow)
            cyl(f"{name}_sh{side}m", (0, 0, 0), 0.054, 0.4, self.m, kn, off=(0, 0, -0.22), seg_n=10, r2=0.042,
                outline=ow)
            box(f"{name}_foot{side}", (0, 0, 0), (0.1, 0.22, 0.07), self.m, kn, off=(0, -0.05, -0.46),
                bevel=0.02, outline=ow)
            self.j[f"sh{side}"], self.j[f"el{side}"] = sh, el
            self.j[f"th{side}"], self.j[f"kn{side}"] = th, kn
        self.set_tint(tint)

    def add_bow(self, m_wood, m_string, side="L"):
        """A simple longbow held in the `side` hand (grip at the hand, limbs up/down, tips curving back).
        Shown only while self.bow_on is True (set it each frame; apply with sync_bow())."""
        el = self.j[f"el{side}"]
        self.bow = empty(f"{self.name}_bow", (0, 0, -0.29), el)
        pts = [Vector((0, 0.62 * s_, 0.2 * s_ * s_)) for s_ in [i / 4 - 1 for i in range(9)]]
        for i in range(len(pts) - 1):
            c = cyl(f"{self.name}_bow{i}", (0, 0, 0), 0.022, 1.0, m_wood, self.bow, base=True, seg_n=6, outline=0.008)
            d = pts[i + 1] - pts[i]
            c.location = pts[i]
            c.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
            c.scale = (1, 1, d.length)
        st = cyl(f"{self.name}_bowstr", (0, 0, 0), 0.006, 1.0, m_string, self.bow, base=True, seg_n=4, outline=False)
        st.location = pts[0]
        st.rotation_euler = (pts[-1] - pts[0]).to_track_quat("Z", "Y").to_euler()
        st.scale = (1, 1, (pts[-1] - pts[0]).length)
        self.bow_on = False
        return self.bow

    def sync_bow(self):
        if getattr(self, "bow", None) is not None:
            hide(self.bow, self.root.hide_render or not self.bow_on)

    def hand(self, side="R"):
        bpy.context.view_layer.update()
        return self.j[f"el{side}"].matrix_world @ Vector((0, 0, -0.3))

    def head(self):
        bpy.context.view_layer.update()
        return self.neck.matrix_world @ Vector((0, 0, 0.2))

    def set_tint(self, tint, k=1.0):
        """Mood colour: 'blue' cold/scared, 'orange' warm/safe, 'red' enemy. k blends from wood."""
        c = TINTS.get(tint) if isinstance(tint, str) else tint
        col = WOOD if c is None else tuple(lerp(w, x, k) for w, x in zip(WOOD, c))
        set_color(self.m, col)
        set_color(self.mj, tuple(x * 0.82 for x in col))

    def place(self, loc, yaw_deg=0.0, roll_deg=0.0, pitch_deg=0.0):
        self.root.location = loc
        self.root.rotation_euler = (D(pitch_deg), D(roll_deg), D(yaw_deg))

    def face(self, target):
        """Yaw so the figure's front (-Y) looks at target (xy)."""
        d = Vector(target) - self.root.location
        self.root.rotation_euler = (0, 0, math.atan2(d.x, -d.y))

    def pose(self, p):
        p = POSES[p] if isinstance(p, str) else p
        self.hip.location = (0, 0, 0.98 + p.get("hipz", 0.0))
        for j in ("spine", "neck"):
            f, s, t = p.get(j, (0, 0, 0))
            self.j[j].rotation_euler = (D(f), D(s), D(t))
        for side, sgn in (("L", -1), ("R", 1)):
            f, o, tw = p.get(f"sh{side}", (0, 0, 0))
            self.j[f"sh{side}"].rotation_euler = (D(-f), D(o * sgn), D(tw))
            self.j[f"el{side}"].rotation_euler = (D(-p.get(f"el{side}", 0.0)), 0, 0)
            f, o, tw = p.get(f"th{side}", (0, 0, 0))
            self.j[f"th{side}"].rotation_euler = (D(-f), D(o * sgn), D(tw))
            self.j[f"kn{side}"].rotation_euler = (D(p.get(f"kn{side}", 0.0)), 0, 0)

    def hide(self, h):
        hide(self.root, h)


# ------------------------------------------------------------------ particles
class Swarm:
    """n linked duplicates of one mesh object. drive(fn) with fn(i) -> (loc, rot_euler, scale) or None (hidden)."""

    def __init__(self, name, proto, n):
        self.items = [proto]
        for i in range(1, n):
            o = proto.copy()
            o.name = f"{name}_{i}"
            link(o)
            self.items.append(o)
        self.n = n

    def drive(self, fn):
        for i, o in enumerate(self.items):
            r = fn(i)
            if r is None:
                o.hide_render = True
                o.hide_viewport = True
                continue
            loc, rot, sc = r
            o.hide_render = False
            o.hide_viewport = False
            o.location = loc
            o.rotation_euler = rot
            o.scale = sc if hasattr(sc, "__len__") else (sc, sc, sc)

    def off(self):
        self.drive(lambda i: None)


def ballistic(p0, p1, apex_h, k):
    """Point on an arc from p0 to p1 (k 0..1) with apex apex_h above the straight line."""
    p0, p1 = Vector(p0), Vector(p1)
    p = p0.lerp(p1, k)
    p.z += 4 * apex_h * k * (1 - k)
    return p


# ------------------------------------------------------------------ camera
class CamPath:
    """ONE continuous camera. keys = [(t_sec, pos, target, lens), ...]; centripetal Catmull-Rom through them,
    time-eased per segment (smoothstep), plus a gentle handheld drift."""

    def __init__(self, keys, drift=0.04, lens_scale=1.0, taper=None):
        """lens_scale < 1 widens every key (vertical 9:16 frames feel cramped: 0.8 is a good default)."""
        self.keys = sorted(keys, key=lambda k: k[0])
        self.drift = drift
        self.lens_scale = lens_scale
        self.taper = taper        # (t_start, t_end): drift fades to 0 at both ends so the last frame == frame 0
        cd = bpy.data.cameras.new("cam")
        self.cam = bpy.data.objects.new("cam", cd)
        link(self.cam)
        scene.camera = self.cam
        cd.sensor_fit = "VERTICAL"
        cd.sensor_height = 24
        cd.clip_start = 0.1
        cd.clip_end = 1200

    @staticmethod
    def _cr(p0, p1, p2, p3, u):
        p0, p1, p2, p3 = map(Vector, (p0, p1, p2, p3))
        # centripetal Catmull-Rom (alpha 0.5): no loops/overshoot on uneven spacing
        def tj(ti, a, b):
            return ti + max(1e-4, (b - a).length) ** 0.5
        t0 = 0.0
        t1 = tj(t0, p0, p1)
        t2 = tj(t1, p1, p2)
        t3 = tj(t2, p2, p3)
        t = lerp(t1, t2, u)
        a1 = p0 * ((t1 - t) / (t1 - t0)) + p1 * ((t - t0) / (t1 - t0))
        a2 = p1 * ((t2 - t) / (t2 - t1)) + p2 * ((t - t1) / (t2 - t1))
        a3 = p2 * ((t3 - t) / (t3 - t2)) + p3 * ((t - t2) / (t3 - t2))
        b1 = a1 * ((t2 - t) / (t2 - t0)) + a2 * ((t - t0) / (t2 - t0))
        b2 = a2 * ((t3 - t) / (t3 - t1)) + a3 * ((t - t1) / (t3 - t1))
        return b1 * ((t2 - t) / (t2 - t1)) + b2 * ((t - t1) / (t2 - t1))

    def eval(self, t):
        K = self.keys
        if t <= K[0][0]:
            return Vector(K[0][1]), Vector(K[0][2]), K[0][3]
        if t >= K[-1][0]:
            return Vector(K[-1][1]), Vector(K[-1][2]), K[-1][3]
        i = max(j for j in range(len(K) - 1) if K[j][0] <= t)
        a, b = K[i], K[i + 1]
        u = seg(t, a[0], b[0])
        u = u * u * (3 - 2 * u) * 0.65 + u * 0.35          # mostly eased, never fully stops
        k0, k3 = K[max(0, i - 1)], K[min(len(K) - 1, i + 2)]
        pos = self._cr(k0[1], a[1], b[1], k3[1], u)
        tgt = self._cr(k0[2], a[2], b[2], k3[2], u)
        lens = lerp(a[3], b[3], u)
        return pos, tgt, lens

    def apply(self, t):
        pos, tgt, lens = self.eval(t)
        d = self.drift
        if self.taper:
            a_, b_ = self.taper
            d *= smooth(seg(t, a_, a_ + 1.5)) * (1 - smooth(seg(t, b_ - 1.5, b_)))
        pos = pos + Vector((noise1(t * 0.6, 1.1) * d, noise1(t * 0.6, 4.2) * d, noise1(t * 0.6, 7.7) * d))
        self.cam.location = pos
        self.cam.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
        self.cam.data.lens = lens * self.lens_scale
        return pos, tgt


# ------------------------------------------------------------------ anchors for the 2D overlay pass
def anchor(name, target, offset=(0, 0, 0)):
    """target: an object (uses its world matrix @ offset) or a fixed world point."""
    _ANCHORS[name] = (target, Vector(offset))


def anchor_screen(name):
    target, off = _ANCHORS[name]
    if hasattr(target, "matrix_world"):
        p = target.matrix_world @ off
    else:
        p = Vector(target) + off
    c = world_to_camera_view(scene, scene.camera, p)
    return [round(c.x * RES[0], 1), round((1 - c.y) * RES[1], 1), c.z > 0]


def dump_anchors(f, folder):
    bpy.context.view_layer.update()
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    data = {n: anchor_screen(n) for n in _ANCHORS}
    (folder / f"f_{f:04d}.json").write_text(json.dumps(data))


# ------------------------------------------------------------------ CLI / render loop
def cli_args():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def render_frame(f, path, animate, anchors_dir=None):
    scene.frame_set(f)
    animate(f)
    bpy.context.view_layer.update()
    if anchors_dir:
        dump_anchors(f, anchors_dir)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def run(animate, base, nf, default_snaps):
    """Standard CLI:  -- snaps f1,f2,.. [tag] [draft] | render a b [step] | anchors a b | blend f"""
    args = cli_args()
    mode = args[0] if args else "snaps"
    base = Path(base)
    anchors_dir = base / "anchors"
    if mode == "snaps":
        frames = [int(x) for x in args[1].split(",")] if len(args) > 1 and args[1] != "draft" else default_snaps
        tag = args[2] if len(args) > 2 and args[2] != "draft" else "s"
        (base / "snaps").mkdir(exist_ok=True)
        for fr in frames:
            render_frame(fr, base / "snaps" / f"{tag}_{fr:04d}.jpg", animate, anchors_dir)
            print("SNAP", fr, flush=True)
        print("SNAPS DONE")
    elif mode == "render":
        a, b = int(args[1]), int(args[2])
        step = int(args[3]) if len(args) > 3 else 1
        (base / "frames").mkdir(exist_ok=True)
        for fr in range(a, min(b, nf - 1) + 1, step):
            out = base / "frames" / f"f_{fr:04d}.jpg"
            if out.exists() and out.stat().st_size > 1000 and (anchors_dir / f"f_{fr:04d}.json").exists():
                continue
            render_frame(fr, out, animate, anchors_dir)
            print("FRAME", fr, flush=True)
        print("RENDER DONE")
    elif mode == "anchors":          # recompute overlay anchors only (no render) after a camera tweak
        a, b = int(args[1]), int(args[2])
        for fr in range(a, min(b, nf - 1) + 1):
            scene.frame_set(fr)
            animate(fr)
            dump_anchors(fr, anchors_dir)
        print("ANCHORS DONE")
    elif mode == "blend":
        animate(int(args[1]) if len(args) > 1 else 0)
        bpy.ops.wm.save_as_mainfile(filepath=str(base / "scene_debug.blend"))


# ------------------------------------------------------------------ tracks / rails (coasters, rails, roads, pipes)
def catmull_dense(pts, step=0.25, closed=False):
    """Centripetal Catmull-Rom through pts -> dense list of Vectors about `step` apart."""
    P = [Vector(p) for p in pts]
    if closed:
        P = [P[-1]] + P + [P[0], P[1]]
    else:
        P = [P[0] + (P[0] - P[1])] + P + [P[-1] + (P[-1] - P[-2])]
    out = []
    for i in range(1, len(P) - 2):
        n = max(2, int((P[i + 1] - P[i]).length / step))
        for k in range(n):
            out.append(CamPath._cr(P[i - 1], P[i], P[i + 1], P[i + 2], k / n))
    if not closed:
        out.append(P[-2].copy())
    return out


class TrackPath:
    """A rail path: dense points + rotation-minimising frames (T tangent, U up, B side) + arc length.
    U starts as `up0` and is parallel-transported, so a vertical loop turns the frame upside down at the top
    (a cart riding it is correct) while flat curves keep U = world up (no unwanted roll)."""

    def __init__(self, pts, up0=(0, 0, 1), dense=False, step=0.25):
        self.P = [Vector(p) for p in pts] if dense else catmull_dense(pts, step)
        n = len(self.P)
        self.T = []
        for i in range(n):
            a, b = self.P[max(0, i - 1)], self.P[min(n - 1, i + 1)]
            self.T.append((b - a).normalized())
        U = Vector(up0)
        U = (U - self.T[0] * U.dot(self.T[0])).normalized()
        self.U = [U]
        for i in range(1, n):     # double reflection RMF (Wang et al. 2008)
            v1 = self.P[i] - self.P[i - 1]
            c1 = v1.dot(v1) or 1e-9
            rL = self.U[-1] - (2 / c1) * v1.dot(self.U[-1]) * v1
            tL = self.T[i - 1] - (2 / c1) * v1.dot(self.T[i - 1]) * v1
            v2 = self.T[i] - tL
            c2 = v2.dot(v2) or 1e-9
            r = rL - (2 / c2) * v2.dot(rL) * v2
            self.U.append(r.normalized())
        self.S = [0.0]
        for i in range(1, n):
            self.S.append(self.S[-1] + (self.P[i] - self.P[i - 1]).length)
        self.L = self.S[-1]

    def frame(self, s):
        """(pos, T, U, B) at arc length s (clamped). B = T x U points to the rider's LEFT... see side()."""
        s = clamp(s, 0, self.L)
        import bisect
        i = min(len(self.S) - 2, max(0, bisect.bisect_right(self.S, s) - 1))
        k = (s - self.S[i]) / max(1e-9, self.S[i + 1] - self.S[i])
        p = self.P[i].lerp(self.P[i + 1], k)
        t = self.T[i].lerp(self.T[i + 1], k).normalized()
        u = self.U[i].lerp(self.U[i + 1], k)
        u = (u - t * u.dot(t)).normalized()
        return p, t, u, t.cross(u)

    def matrix(self, s, lift=0.0, forward=-1):
        """World matrix for a vehicle at s: local -Y = travel direction (forward=-1, like the mannequin), +Z = track up."""
        p, t, u, b = self.frame(s)
        y = t * forward
        z = u
        x = y.cross(z)
        m = Matrix((x, y, z)).transposed().to_4x4()
        m.translation = p + u * lift
        return m

    def sweep(self, name, m, s0=0.0, s1=None, offsets=((0.0, 0.0),), radius=0.08, sides=8, every=1,
              parent=None, outline=0.02):
        """Tubes along [s0, s1]; offsets = (side, up) per tube. Faces are created in order of s, so a BUILD
        modifier reveals the track along its length."""
        s1 = self.L if s1 is None else s1
        idx = [i for i in range(len(self.P)) if s0 - 1e-6 <= self.S[i] <= s1 + 1e-6][::every]
        bm = bmesh.new()
        radii = radius if hasattr(radius, "__len__") else [radius] * len(offsets)
        allr = []
        for (so, uo), rad in zip(offsets, radii):
            rings = []
            for i in idx:
                p, t, u = self.P[i], self.T[i], self.U[i]
                b = t.cross(u)
                c = p + b * so + u * uo
                ring = [bm.verts.new(c + (b * math.cos(2 * math.pi * k / sides) + u * math.sin(2 * math.pi * k / sides)) * rad)
                        for k in range(sides)]
                rings.append(ring)
            allr.append(rings)
        for j in range(len(idx) - 1):          # interleaved so a BUILD reveal grows all tubes together
            for rings in allr:
                r0, r1 = rings[j], rings[j + 1]
                for k in range(sides):
                    bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
        o = _finish(name, bm, m, parent, (0, 0, 0), 0, outline)
        for pl in o.data.polygons:
            pl.use_smooth = True
        return o

    def ties(self, name, m, s0=0.0, s1=None, spacing=1.2, width=1.3, size=(0.12, 0.14), up=-0.12, parent=None,
             outline=0.015):
        """Cross ties every `spacing` m (one mesh)."""
        s1 = self.L if s1 is None else s1
        bm = bmesh.new()
        s = s0
        while s <= s1:
            p, t, u, b = self.frame(s)
            c = p + u * up
            hx, ht, hu = width / 2, size[0] / 2, size[1] / 2
            vs = [bm.verts.new(c + b * sx * hx + t * st * ht + u * su * hu)
                  for sx in (-1, 1) for st in (-1, 1) for su in (-1, 1)]
            for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
                bm.faces.new([vs[j] for j in f])
            s += spacing
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return _finish(name, bm, m, parent, (0, 0, 0), 0, outline)

    def supports(self, name, m, s0=0.0, s1=None, spacing=4.0, r=0.16, min_z=0.8, down=0.45, parent=None,
                 outline=0.02):
        """Vertical columns from under the spine to the ground where the track is upright."""
        s1 = self.L if s1 is None else s1
        bm = bmesh.new()
        s = s0
        while s <= s1:
            p, t, u, b = self.frame(s)
            top = p - u * down
            if u.z > 0.7 and top.z > min_z:
                r_ = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=r, radius2=r * 0.8, depth=top.z)
                for v in r_["verts"]:
                    v.co += Vector((top.x, top.y, top.z / 2))
            s += spacing
        return _finish(name, bm, m, parent, (0, 0, 0), 0, outline)


def build_reveal(obj, f0, f1):
    """Reveal a mesh face by face between frames f0..f1 (BUILD modifier; deterministic per frame)."""
    md = obj.modifiers.new("build", "BUILD")
    md.frame_start = f0
    md.frame_duration = max(1, f1 - f0)
    obj.modifiers.move(len(obj.modifiers) - 1, 0)
    return md
