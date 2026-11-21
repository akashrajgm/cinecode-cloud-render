"""Shared toolkit for every shot script (Blender 5.2, EEVEE).

Import from a shot script with:
    import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
    from common import *

Conventions
- 24 fps, 1920x1080, AgX view transform, scene-linear compositor bloom.
- Every shot script ends with finish("sNN_name") which handles CLI flags:
    --still F [--pct 50]        render one frame to film/tests/<shot>_fF.png
    --stills F1,F2,F3 [--pct]   render several stills
    --anim [--from A --to B]    render PNG sequence to film/renders/<shot>/####.png
    --save                      save film/blend/<shot>.blend
    --samples N                 override EEVEE samples
"""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Euler, Matrix, Color

FILM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER_DIR = os.path.dirname(os.environ.get("BLENDER", r"E:\experimentswithclaude\tools\blender\blender-5.2.2-windows-x64\blender.exe"))
HDRI_DIR = os.path.join(BLENDER_DIR, "5.2", "datafiles", "studiolights", "world")
FPS = 24

# ----------------------------------------------------------------------------- scene

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    return sc


def setup_render(start=1, end=48, res=(1920, 1080), samples=48, mb=True, shutter=0.5,
                 raytrace=True, vol_tile='8', vol_samples=64, vol_end=200.0, vol_start=0.1,
                 look='AgX - Medium High Contrast', exposure=0.0, gamma=1.0, film_transparent=False):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = start, end
    sc.render.film_transparent = film_transparent
    ee = sc.eevee
    ee.taa_render_samples = samples
    ee.use_raytracing = raytrace
    try:
        ee.ray_tracing_method = 'SCREEN'
        ee.ray_tracing_options.resolution_scale = '2'
        ee.ray_tracing_options.use_denoise = True
    except Exception:
        pass
    ee.use_shadows = True
    ee.shadow_ray_count = 2
    ee.shadow_step_count = 8
    ee.use_fast_gi = True
    try:
        ee.fast_gi_method = 'GLOBAL_ILLUMINATION'
    except Exception:
        pass
    ee.volumetric_tile_size = vol_tile
    ee.volumetric_samples = vol_samples
    ee.volumetric_start = vol_start
    ee.volumetric_end = vol_end
    ee.use_volumetric_shadows = True
    ee.volumetric_shadow_samples = 16
    ee.clamp_surface_indirect = 10.0
    sc.render.use_motion_blur = mb
    sc.render.motion_blur_shutter = shutter
    ee.motion_blur_steps = 1
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = look
    sc.view_settings.exposure = exposure
    sc.view_settings.gamma = gamma
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_depth = '16'
    sc.render.image_settings.compression = 15
    return sc


def highlight_shoulder(tree, img, knee=0.5, cap=1.6):
    """Client rule: nothing may blow out. Rolls each pixel's brightest channel off smoothly from `knee`
    toward `cap` (scene-linear) and scales RGB equally, so hues survive and AgX never reaches white."""
    def math(op, a, b=None):
        m = tree.nodes.new("ShaderNodeMath")
        m.operation = op
        for idx, v in ((0, a), (1, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[idx].default_value = v
            else:
                tree.links.new(v, m.inputs[idx])
        return m.outputs[0]
    sep = tree.nodes.new("CompositorNodeSeparateColor")
    tree.links.new(img, sep.inputs['Image'])
    mx = math('MAXIMUM', math('MAXIMUM', sep.outputs['Red'], sep.outputs['Green']), sep.outputs['Blue'])
    span = cap - knee
    excess = math('MAXIMUM', math('SUBTRACT', mx, knee), 0.0)
    rolled = math('ADD', math('MINIMUM', mx, knee),
                  math('MULTIPLY', math('SUBTRACT', 1.0, math('EXPONENT', math('DIVIDE', excess, -span))), span))
    factor = math('DIVIDE', rolled, math('MAXIMUM', mx, 1e-4))
    comb = tree.nodes.new("CompositorNodeCombineColor")
    for ch in ('Red', 'Green', 'Blue'):
        tree.links.new(factor, comb.inputs[ch])
    comb.inputs['Alpha'].default_value = 1.0
    mul = tree.nodes.new("ShaderNodeMix")
    mul.data_type = 'RGBA'
    mul.blend_type = 'MULTIPLY'
    mul.inputs['Factor'].default_value = 1.0
    tree.links.new(img, mul.inputs[6])
    tree.links.new(comb.outputs['Image'], mul.inputs[7])
    return mul.outputs[2]


def compositor(bloom=0.35, threshold=1.0, bloom_size=0.6, dispersion=0.006, distortion=0.0, glare_type='Bloom',
               shoulder=True, knee=0.5, cap=1.6):
    """Scene-linear post: highlight shoulder + (capped) bloom + subtle lens dispersion.

    Director override (client: "never too bright"): bloom strength is capped at 0.12 and its threshold
    raised to >= 1.0 whatever a shot script asks for; the highlight shoulder is on by default."""
    bloom = min(bloom, 0.12)
    threshold = max(threshold, 1.0)
    sc = bpy.context.scene
    tree = bpy.data.node_groups.new("Comp", "CompositorNodeTree")
    sc.compositing_node_group = tree
    sc.render.use_compositing = True
    tree.interface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = tree.nodes.new("CompositorNodeRLayers")
    out = tree.nodes.new("NodeGroupOutput")
    cur = rl.outputs['Image']
    if shoulder:
        cur = highlight_shoulder(tree, cur, knee, cap)
    if bloom > 0:
        g = tree.nodes.new("CompositorNodeGlare")
        _set_in(g, 'Type', glare_type)
        _set_in(g, 'Quality', 'High')
        _set_in(g, 'Threshold', threshold)
        _set_in(g, 'Strength', bloom)
        _set_in(g, 'Size', bloom_size)
        tree.links.new(cur, g.inputs['Image'])
        cur = g.outputs['Image']
    if dispersion > 0 or distortion != 0:
        ld = tree.nodes.new("CompositorNodeLensdist")
        _set_in(ld, 'Distortion', distortion)
        _set_in(ld, 'Dispersion', dispersion)
        tree.links.new(cur, ld.inputs['Image'])
        cur = ld.outputs['Image']
    tree.links.new(cur, out.inputs[0])
    return tree


def _set_in(node, name, val):
    try:
        node.inputs[name].default_value = val
    except Exception as e:
        print("[comp] could not set", node.name, name, val, e)

# ----------------------------------------------------------------------------- world

def world_color(color=(0.01, 0.012, 0.015), strength=1.0):
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    nt = w.node_tree if w.node_tree else _world_nodes(w)
    bg = nt.nodes.get('Background') or nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (*color, 1)
    bg.inputs['Strength'].default_value = strength
    return w


def _world_nodes(w):
    try:
        w.use_nodes = True
    except Exception:
        pass
    return w.node_tree


def world_hdri(name='sunset.exr', strength=1.0, rot_z=0.0, tint=None, fog=None):
    """name: one of city/courtyard/forest/interior/night/studio/sunrise/sunset .exr
    fog: optional (density, color, anisotropy) world volume scatter."""
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    nt = _world_nodes(w)
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    env = nt.nodes.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(os.path.join(HDRI_DIR, name), check_existing=True)
    mp = nt.nodes.new('ShaderNodeMapping')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp.inputs['Rotation'].default_value[2] = rot_z
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
    col = env.outputs['Color']
    if tint:
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 1.0
        nt.links.new(col, mix.inputs[6]); mix.inputs[7].default_value = (*tint, 1)
        col = mix.outputs[2]
    nt.links.new(col, bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    if fog:
        add_world_fog(w, *fog)
    return w


def world_sky(sun_elev_deg=6.0, sun_rot_deg=0.0, strength=1.0, altitude=0.0, air=1.0, dust=1.0, ozone=1.0, fog=None):
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    nt = _world_nodes(w)
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    sky = nt.nodes.new('ShaderNodeTexSky')
    for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING', 'HOSEK_WILKIE'):
        try:
            sky.sky_type = t
            break
        except Exception:
            continue
    for attr, val in (('sun_elevation', math.radians(sun_elev_deg)), ('sun_rotation', math.radians(sun_rot_deg)),
                      ('altitude', altitude), ('air_density', air), ('dust_density', dust), ('aerosol_density', dust),
                      ('ozone_density', ozone), ('sun_intensity', 1.0)):
        try:
            setattr(sky, attr, val)
        except Exception:
            pass
    nt.links.new(sky.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    if fog:
        add_world_fog(w, *fog)
    return w


def add_world_fog(world, density=0.01, color=(0.6, 0.7, 0.75), anisotropy=0.4):
    nt = world.node_tree
    out = [n for n in nt.nodes if n.type == 'OUTPUT_WORLD'][0]
    vs = nt.nodes.new('ShaderNodeVolumePrincipled')
    vs.inputs['Density'].default_value = density
    vs.inputs['Color'].default_value = (*color, 1)
    vs.inputs['Anisotropy'].default_value = anisotropy
    nt.links.new(vs.outputs['Volume'], out.inputs['Volume'])
    return vs

# ----------------------------------------------------------------------------- objects

def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def mesh_obj(name, verts, faces, coll=None, smooth=True, sharp_angle=30.0):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    link(o, coll)
    if smooth:
        shade(o, sharp_angle)
    return o


def shade(o, sharp_angle=30.0):
    me = o.data
    try:
        me.shade_smooth()
        me.set_sharpness_by_angle(angle=math.radians(sharp_angle))
    except Exception:
        for p in me.polygons:
            p.use_smooth = True


def from_bmesh(name, bm, coll=None, smooth=True, sharp_angle=30.0):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    link(o, coll)
    if smooth:
        shade(o, sharp_angle)
    return o


def prim(kind, name="obj", loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), coll=None, **kw):
    """kind: cube|cylinder|sphere|plane|cone|torus|ico via bmesh ops (no bpy.ops context issues)."""
    bm = bmesh.new()
    if kind == 'cube':
        bmesh.ops.create_cube(bm, size=1.0)
    elif kind == 'cylinder':
        bmesh.ops.create_cone(bm, cap_ends=True, segments=kw.get('segments', 48), radius1=kw.get('r', 0.5),
                              radius2=kw.get('r', 0.5), depth=kw.get('depth', 1.0))
    elif kind == 'cone':
        bmesh.ops.create_cone(bm, cap_ends=True, segments=kw.get('segments', 48), radius1=kw.get('r1', 0.5),
                              radius2=kw.get('r2', 0.0), depth=kw.get('depth', 1.0))
    elif kind == 'sphere':
        bmesh.ops.create_uvsphere(bm, u_segments=kw.get('u', 48), v_segments=kw.get('v', 24), radius=kw.get('r', 0.5))
    elif kind == 'ico':
        bmesh.ops.create_icosphere(bm, subdivisions=kw.get('sub', 3), radius=kw.get('r', 0.5))
    elif kind == 'plane':
        bmesh.ops.create_grid(bm, x_segments=kw.get('xs', 1), y_segments=kw.get('ys', 1), size=0.5)
    elif kind == 'torus':
        R, r = kw.get('R', 1.0), kw.get('r', 0.1)
        su, sv = kw.get('su', 64), kw.get('sv', 16)
        verts = []
        for i in range(su):
            a = 2 * math.pi * i / su
            for j in range(sv):
                b = 2 * math.pi * j / sv
                verts.append(bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b))))
        for i in range(su):
            for j in range(sv):
                a = verts[i * sv + j]; b_ = verts[((i + 1) % su) * sv + j]
                c = verts[((i + 1) % su) * sv + (j + 1) % sv]; d = verts[i * sv + (j + 1) % sv]
                bm.faces.new((a, b_, c, d))
    o = from_bmesh(name, bm, coll, smooth=kw.get('smooth', kind in ('sphere', 'ico', 'torus', 'cylinder', 'cone')))
    o.location = loc
    o.rotation_euler = rot
    o.scale = scale
    return o


def bevel(o, width=0.01, segments=3, angle=35.0, harden=True):
    m = o.modifiers.new("Bevel", 'BEVEL')
    m.width = width
    m.segments = segments
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    m.harden_normals = harden
    m.miter_outer = 'MITER_ARC'
    return m


def subsurf(o, levels=2):
    m = o.modifiers.new("Subsurf", 'SUBSURF')
    m.levels = levels
    m.render_levels = levels
    return m


def apply_mods(o):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    o.modifiers.clear()
    old = o.data
    o.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)


def set_mat(o, mat, slot=None):
    if slot is None:
        o.data.materials.clear()
        o.data.materials.append(mat)
    else:
        while len(o.data.materials) <= slot:
            o.data.materials.append(mat)
        o.data.materials[slot] = mat
    return o


def parent(child, par, keep=True):
    mw = child.matrix_world.copy()
    child.parent = par
    if keep:
        child.matrix_parent_inverse = par.matrix_world.inverted()
    return child


def empty(name, loc=(0, 0, 0), coll=None, kind='PLAIN_AXES'):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = kind
    e.location = loc
    link(e, coll)
    return e

# ----------------------------------------------------------------------------- gears

def gear_profile(teeth, r_pitch, depth, tooth_frac=0.5, pts_per_tooth=8):
    """Radial outline (list of (angle, radius)) of a spur gear with trapezoid teeth."""
    r_root = r_pitch - depth * 0.55
    r_tip = r_pitch + depth * 0.45
    out = []
    step = 2 * math.pi / teeth
    # fractions of a tooth period: root .. rise .. tip .. fall .. root
    tf = tooth_frac
    rise = 0.12
    keys = [(0.0, r_root), ((1 - tf) / 2 - rise / 2, r_root), ((1 - tf) / 2 + rise / 2, r_tip),
            ((1 + tf) / 2 - rise / 2, r_tip), ((1 + tf) / 2 + rise / 2, r_root), (1.0, r_root)]
    for t in range(teeth):
        for (f, r) in keys[:-1]:
            out.append((t * step + f * step, r))
    return out


def make_gear(name="gear", teeth=24, r=1.0, depth=None, thick=0.12, hole=0.12, rim=None, spokes=5,
              spoke_w=None, hub=None, coll=None, mat=None, bevel_w=None, windows='spokes', hub_thick=None):
    """Spur gear built from rings of quads (no booleans). windows: 'spokes' | 'holes' | 'solid'."""
    depth = depth or r * 0.12
    rim = rim or r * 0.78
    hub = hub or r * 0.22
    spoke_w = spoke_w or r * 0.12
    hub_thick = hub_thick or thick * 1.6
    prof = gear_profile(teeth, r, depth)
    bm = bmesh.new()
    n = len(prof)
    inner_r = rim if windows != 'solid' else hole

    def ring(z):
        outer = [bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)) for a, rr in prof]
        inner = [bm.verts.new((inner_r * math.cos(a), inner_r * math.sin(a), z)) for a, rr in prof]
        return outer, inner
    o0, i0 = ring(-thick / 2)
    o1, i1 = ring(thick / 2)
    for k in range(n):
        k2 = (k + 1) % n
        bm.faces.new((o1[k], o1[k2], i1[k2], i1[k]))       # top
        bm.faces.new((o0[k2], o0[k], i0[k], i0[k2]))       # bottom
        bm.faces.new((o0[k], o0[k2], o1[k2], o1[k]))       # outer wall (teeth)
        bm.faces.new((i0[k2], i0[k], i1[k], i1[k2]))       # inner wall
    if windows != 'solid':
        # hub
        hs = 48
        def circ(rad, z):
            return [bm.verts.new((rad * math.cos(2 * math.pi * j / hs), rad * math.sin(2 * math.pi * j / hs), z)) for j in range(hs)]
        ho0, ho1 = circ(hub, -hub_thick / 2), circ(hub, hub_thick / 2)
        hi0, hi1 = circ(hole, -hub_thick / 2), circ(hole, hub_thick / 2)
        for j in range(hs):
            j2 = (j + 1) % hs
            bm.faces.new((ho1[j], ho1[j2], hi1[j2], hi1[j]))
            bm.faces.new((ho0[j2], ho0[j], hi0[j], hi0[j2]))
            bm.faces.new((ho0[j], ho0[j2], ho1[j2], ho1[j]))
            bm.faces.new((hi0[j2], hi0[j], hi1[j], hi1[j2]))
        # spokes as boxes
        st = thick * 0.8
        for s in range(spokes):
            a = 2 * math.pi * s / spokes + math.pi / spokes
            d = Vector((math.cos(a), math.sin(a), 0)); p = Vector((-math.sin(a), math.cos(a), 0))
            r0, r1 = hub * 0.9, rim * 1.02
            corners = []
            for rr in (r0, r1):
                for side in (-1, 1):
                    for z in (-st / 2, st / 2):
                        c = d * rr + p * side * spoke_w / 2 * (1.0 if rr == r0 else 0.75)
                        corners.append(bm.verts.new((c.x, c.y, z)))
            a0, a1, a2, a3, b0, b1, b2, b3 = corners
            for f in ((a0, a2, a3, a1), (b0, b1, b3, b2), (a0, b0, b2, a2), (a1, a3, b3, b1), (a0, a1, b1, b0), (a2, b2, b3, a3)):
                bm.faces.new(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = from_bmesh(name, bm, coll, smooth=True, sharp_angle=40)
    if bevel_w is None:
        bevel_w = min(thick, depth) * 0.12
    bevel(o, width=bevel_w, segments=2, angle=40)
    if mat:
        set_mat(o, mat)
    return o


def spin_gear(o, teeth, start, end, turns_per_sec=0.25, axis=2, phase=0.0, direction=1):
    """Linear rotation keyframes; neighbours mesh when speed ~ 1/teeth."""
    rate = direction * turns_per_sec * 2 * math.pi / FPS
    fc_key(o, 'rotation_euler', axis, [(start, phase + rate * 0), (end, phase + rate * (end - start))], interp='LINEAR')

# ----------------------------------------------------------------------------- animation

def fc_key(o, path, index, pairs, interp='BEZIER', easing='AUTO', handle='AUTO_CLAMPED'):
    """pairs: [(frame, value), ...] on a single channel."""
    for f, v in pairs:
        if index is None:
            setattr(o, path, v)
            o.keyframe_insert(path, frame=f)
        else:
            getattr(o, path)[index] = v
            o.keyframe_insert(path, index=index, frame=f)
    for fc in fcurves(o):
        if fc.data_path == path and (index is None or fc.array_index == index):
            for kp in fc.keyframe_points:
                kp.interpolation = interp
                kp.easing = easing
                kp.handle_left_type = handle
                kp.handle_right_type = handle


def fcurves(idblock):
    ad = idblock.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    if hasattr(act, 'fcurves') and len(getattr(act, 'fcurves', [])):
        return list(act.fcurves)
    out = []
    try:  # layered actions (4.4+ / 5.x)
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out.extend(cb.fcurves)
    except Exception:
        pass
    return out


def key_vec(o, path, pairs, interp='BEZIER', easing='AUTO'):
    """pairs: [(frame, (x,y,z)), ...]"""
    for f, v in pairs:
        setattr(o, path, v)
        o.keyframe_insert(path, frame=f)
    for fc in fcurves(o):
        if fc.data_path == path:
            for kp in fc.keyframe_points:
                kp.interpolation = interp
                kp.easing = easing


def set_interp(o, interp='BEZIER', easing='AUTO', path=None):
    for fc in fcurves(o):
        if path and fc.data_path != path:
            continue
        for kp in fc.keyframe_points:
            kp.interpolation = interp
            kp.easing = easing


def shake(o, amp=0.01, rot_amp=0.004, scale=12.0, seed=0, start=None, end=None):
    """Handheld noise on location/rotation via F-curve noise modifiers (object must have keys or will get them)."""
    have = {(fc.data_path, fc.array_index) for fc in fcurves(o)}
    for path, a in (('location', amp), ('rotation_euler', rot_amp)):
        if a <= 0:
            continue
        for i in range(3):
            # only key channels that are not animated yet: re-keying an animated channel here would
            # overwrite its first key with the current (last-set) value
            if (path, i) not in have:
                o.keyframe_insert(path, index=i, frame=bpy.context.scene.frame_start)
    for fc in fcurves(o):
        if fc.data_path not in ('location', 'rotation_euler'):
            continue
        a = amp if fc.data_path == 'location' else rot_amp
        if a <= 0:
            continue
        m = fc.modifiers.new('NOISE')
        m.scale = scale
        m.strength = a
        m.phase = seed * 13.7 + fc.array_index * 5.1 + (0 if fc.data_path == 'location' else 50)
        if start is not None:
            m.use_restricted_range = True
            m.frame_start = start
            m.frame_end = end


def look_at(o, target):
    t = Vector(target) if not hasattr(target, 'location') else target.matrix_world.translation
    d = t - o.location
    o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def track_to(o, target):
    c = o.constraints.new('TRACK_TO')
    c.target = target
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    return c

# ----------------------------------------------------------------------------- camera & lights

def camera(name="Cam", loc=(0, -5, 1), target=None, lens=50, fstop=None, focus=None, sensor=36.0, clip=(0.01, 500), coll=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = sensor
    cd.clip_start, cd.clip_end = clip
    c = bpy.data.objects.new(name, cd)
    link(c, coll)
    c.location = loc
    if target is not None:
        look_at(c, target)
    if fstop:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
        cd.dof.aperture_blades = 7
        cd.dof.aperture_ratio = 1.0
        if hasattr(focus, 'location'):
            cd.dof.focus_object = focus
        elif focus is not None:
            cd.dof.focus_distance = focus
    bpy.context.scene.camera = c
    return c


def bind_cameras(cuts):
    """cuts: [(frame, cam_obj), ...] -> timeline markers that switch the active camera."""
    sc = bpy.context.scene
    for f, cam in cuts:
        m = sc.timeline_markers.new(f"cut_{f}_{cam.name}", frame=f)
        m.camera = cam
    sc.camera = cuts[0][1]


def light(kind='AREA', name='L', loc=(0, 0, 3), rot=(0, 0, 0), energy=100.0, color=(1, 1, 1), size=1.0, size_y=None,
          spot=45.0, blend=0.3, shadow_soft=0.05, coll=None, target=None, volume=1.0):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    try:
        ld.volume_factor = volume
    except Exception:
        pass
    if kind == 'AREA':
        ld.shape = 'RECTANGLE' if size_y else 'SQUARE'
        ld.size = size
        if size_y:
            ld.size_y = size_y
    elif kind == 'SPOT':
        ld.spot_size = math.radians(spot)
        ld.spot_blend = blend
        ld.shadow_soft_size = shadow_soft
    elif kind in ('POINT',):
        ld.shadow_soft_size = shadow_soft
    elif kind == 'SUN':
        ld.angle = math.radians(size)
    o = bpy.data.objects.new(name, ld)
    link(o, coll)
    o.location = loc
    o.rotation_euler = rot
    if target is not None:
        look_at(o, target)
    return o

# ----------------------------------------------------------------------------- materials

class NB:
    """Tiny node-builder for materials."""

    def __init__(self, name, clear=True):
        self.mat = bpy.data.materials.new(name)
        try:
            self.mat.use_nodes = True
        except Exception:
            pass
        self.nt = self.mat.node_tree
        self.N = self.nt.nodes
        self.L = self.nt.links
        self.bsdf = self.N.get('Principled BSDF')
        self.out = self.N.get('Material Output')
        if self.bsdf is None:
            self.bsdf = self.N.new('ShaderNodeBsdfPrincipled')
        if self.out is None:
            self.out = self.N.new('ShaderNodeOutputMaterial')
            self.L.new(self.bsdf.outputs[0], self.out.inputs['Surface'])

    def n(self, kind, **props):
        node = self.N.new(kind)
        for k, v in props.items():
            if k in node.inputs.keys():
                node.inputs[k].default_value = v
            else:
                setattr(node, k, v)
        return node

    def link(self, a, b):
        self.L.new(a, b)

    def coord(self, kind='Object', scale=1.0):
        tc = self.n('ShaderNodeTexCoord')
        if scale == 1.0:
            return tc.outputs[kind]
        mp = self.n('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (scale, scale, scale) if not isinstance(scale, (tuple, list)) else scale
        self.link(tc.outputs[kind], mp.inputs['Vector'])
        return mp.outputs['Vector']

    def noise(self, vec, scale=5.0, detail=6.0, rough=0.55, dist=0.0, dims='3D', kind=None):
        nz = self.n('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = scale
        nz.inputs['Detail'].default_value = detail
        nz.inputs['Roughness'].default_value = rough
        nz.inputs['Distortion'].default_value = dist
        if kind:
            try:
                nz.noise_type = kind
            except Exception:
                pass
        if vec is not None:
            self.link(vec, nz.inputs['Vector'])
        return nz

    def voronoi(self, vec, scale=5.0, feature='F1', dist='EUCLIDEAN', rand=1.0):
        v = self.n('ShaderNodeTexVoronoi')
        v.feature = feature
        v.distance = dist
        v.inputs['Scale'].default_value = scale
        v.inputs['Randomness'].default_value = rand
        if vec is not None:
            self.link(vec, v.inputs['Vector'])
        return v

    def ramp(self, fac, stops):
        """stops: [(pos, (r,g,b,a) or float)]"""
        r = self.n('ShaderNodeValToRGB')
        cr = r.color_ramp
        els = cr.elements
        while len(els) > 2:
            els.remove(els[-1])
        for i, (p, c) in enumerate(stops):
            if not isinstance(c, (tuple, list)):
                c = (c, c, c, 1)
            elif len(c) == 3:
                c = (*c, 1)
            if i < 2:
                els[i].position = p
                els[i].color = c
            else:
                e = els.new(p)
                e.color = c
        self.link(fac, r.inputs['Fac'])
        return r

    def mix(self, a, b, fac, blend='MIX'):
        m = self.n('ShaderNodeMix')
        m.data_type = 'RGBA'
        m.blend_type = blend
        if isinstance(fac, (int, float)):
            m.inputs['Factor'].default_value = fac
        else:
            self.link(fac, m.inputs['Factor'])
        for idx, v in ((6, a), (7, b)):
            if isinstance(v, (tuple, list)):
                m.inputs[idx].default_value = (*v, 1) if len(v) == 3 else v
            else:
                self.link(v, m.inputs[idx])
        return m.outputs[2]

    def math(self, op, a, b=None, clamp=False):
        m = self.n('ShaderNodeMath')
        m.operation = op
        m.use_clamp = clamp
        for idx, v in ((0, a), (1, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[idx].default_value = v
            else:
                self.link(v, m.inputs[idx])
        return m.outputs[0]

    def maprange(self, val, a0, a1, b0, b1, clamp=True):
        m = self.n('ShaderNodeMapRange')
        m.clamp = clamp
        m.inputs['From Min'].default_value = a0
        m.inputs['From Max'].default_value = a1
        m.inputs['To Min'].default_value = b0
        m.inputs['To Max'].default_value = b1
        self.link(val, m.inputs['Value'])
        return m.outputs['Result']

    def bump(self, height, strength=0.2, distance=0.02, normal=None):
        b = self.n('ShaderNodeBump')
        b.inputs['Strength'].default_value = strength
        b.inputs['Distance'].default_value = distance
        self.link(height, b.inputs['Height'])
        if normal is not None:
            self.link(normal, b.inputs['Normal'])
        return b.outputs['Normal']

    def set(self, name, v):
        if isinstance(v, (int, float)):
            self.bsdf.inputs[name].default_value = v
        elif isinstance(v, (tuple, list)):
            self.bsdf.inputs[name].default_value = (*v, 1) if len(v) == 3 and name.endswith('Color') else v
        else:
            self.link(v, self.bsdf.inputs[name])
        return self


def mat_emission(name='Emit', color=(1, 0.2, 0.1), strength=20.0):
    b = NB(name)
    b.set('Base Color', (0, 0, 0)).set('Emission Color', color).set('Emission Strength', strength)
    b.set('Roughness', 0.4)
    return b.mat


def mat_brass(name='Brass', base=(0.78, 0.53, 0.24), dark=(0.42, 0.26, 0.11), rough=(0.18, 0.5), scale=1.0, worn=0.5):
    b = NB(name)
    v = b.coord('Object', scale)
    n1 = b.noise(v, 3.0, 8, 0.6)
    n2 = b.noise(v, 40.0, 4, 0.7)
    # stretched micro scratches
    vs = b.coord('Object', (scale * 2, scale * 2, scale * 160))
    sc = b.noise(vs, 30.0, 2, 0.5)
    col = b.ramp(n1.outputs['Fac'], [(0.3, dark), (0.65, base)])
    b.set('Base Color', b.mix(col.outputs[0], dark, b.maprange(n2.outputs['Fac'], 0.55, 0.8, 0, worn)))
    b.set('Metallic', 1.0)
    rr = b.maprange(b.math('ADD', n1.outputs['Fac'], b.math('MULTIPLY', sc.outputs['Fac'], 0.4)), 0.35, 0.95, rough[0], rough[1])
    b.set('Roughness', rr)
    b.set('Normal', b.bump(b.math('ADD', n2.outputs['Fac'], sc.outputs['Fac']), 0.08, 0.005))
    try:
        b.set('Anisotropic', 0.3)
    except Exception:
        pass
    return b.mat


def mat_metal(name='Steel', base=(0.56, 0.57, 0.58), rough=(0.12, 0.35), scale=1.0, bump=0.05):
    b = NB(name)
    v = b.coord('Object', scale)
    n1 = b.noise(v, 4.0, 8, 0.6)
    n2 = b.noise(v, 60.0, 3, 0.6)
    b.set('Base Color', b.mix(base, tuple(c * 0.7 for c in base), n1.outputs['Fac']))
    b.set('Metallic', 1.0)
    b.set('Roughness', b.maprange(n1.outputs['Fac'], 0.3, 0.8, rough[0], rough[1]))
    b.set('Normal', b.bump(n2.outputs['Fac'], bump, 0.003))
    return b.mat


def mat_gold(name='Gold', base=(1.0, 0.68, 0.26), rough=(0.12, 0.32), scale=1.0, bump=0.1):
    return mat_brass(name, base=base, dark=(0.6, 0.36, 0.1), rough=rough, scale=scale, worn=0.25)


def mat_carpaint(name='CarPaint', color=(0.02, 0.03, 0.035), metallic=0.6, rough=0.32, flake=0.25, coat=1.0):
    b = NB(name)
    v = b.coord('Object', 1.0)
    fl = b.voronoi(v, 900.0)
    b.set('Base Color', color)
    b.set('Metallic', metallic)
    b.set('Roughness', rough)
    b.set('Coat Weight', coat)
    b.set('Coat Roughness', 0.02)
    b.set('Normal', b.bump(fl.outputs['Color'] if 'Color' in fl.outputs else fl.outputs[0], flake, 0.001))
    return b.mat


def mat_glass(name='Glass', tint=(0.9, 0.95, 1.0), rough=0.0, ior=1.45):
    b = NB(name)
    b.set('Base Color', tint).set('Roughness', rough).set('IOR', ior).set('Transmission Weight', 1.0)
    try:
        b.mat.surface_render_method = 'BLENDED'
        b.mat.use_raytrace_refraction = True
    except Exception:
        pass
    return b.mat


def mat_rubber(name='Rubber', color=(0.012, 0.012, 0.013), rough=0.75):
    b = NB(name)
    v = b.coord('Object', 1.0)
    n = b.noise(v, 80, 3, 0.6)
    b.set('Base Color', color).set('Roughness', b.maprange(n.outputs['Fac'], 0.3, 0.7, rough - 0.1, rough + 0.1))
    b.set('Normal', b.bump(n.outputs['Fac'], 0.1, 0.002))
    return b.mat


def mat_concrete(name='Concrete', base=(0.22, 0.23, 0.24), wet=0.5, scale=1.0, puddle_scale=0.35):
    """Concrete with wet puddles: low roughness + darker where puddle mask is high."""
    b = NB(name)
    v = b.coord('Object', scale)
    n1 = b.noise(v, 2.0, 10, 0.6)
    n2 = b.noise(v, 25.0, 6, 0.65)
    pud = b.noise(b.coord('Object', scale * puddle_scale), 1.5, 4, 0.5)
    mask = b.maprange(pud.outputs['Fac'], 0.5 - wet * 0.1, 0.56 - wet * 0.1, 0.0, 1.0)
    col = b.ramp(n1.outputs['Fac'], [(0.3, tuple(c * 0.55 for c in base)), (0.7, base)])
    b.set('Base Color', b.mix(col.outputs[0], tuple(c * 0.35 for c in base), mask))
    rough = b.maprange(n2.outputs['Fac'], 0.3, 0.7, 0.55, 0.9)
    b.set('Roughness', b.mix(rough, (0.02, 0.02, 0.02), mask))
    b.set('Normal', b.bump(b.math('MULTIPLY', n2.outputs['Fac'], b.math('SUBTRACT', 1.0, mask)), 0.35, 0.01))
    return b.mat


def mat_rock(name='Rock', base=(0.33, 0.11, 0.06), dark=(0.09, 0.035, 0.025), scale=1.0, rough=0.85):
    b = NB(name)
    v = b.coord('Object', scale)
    n1 = b.noise(v, 1.5, 12, 0.62, 0.3)
    vo = b.voronoi(v, 6.0)
    n2 = b.noise(v, 30.0, 6, 0.7)
    col = b.ramp(n1.outputs['Fac'], [(0.35, dark), (0.65, base)])
    b.set('Base Color', b.mix(col.outputs[0], tuple(c * 0.6 for c in base), vo.outputs['Distance']))
    b.set('Roughness', rough)
    b.set('Normal', b.bump(b.math('ADD', n2.outputs['Fac'], vo.outputs['Distance']), 0.6, 0.05))
    return b.mat


def mat_asphalt(name='Asphalt', base=(0.045, 0.045, 0.05), scale=1.0):
    b = NB(name)
    v = b.coord('Object', scale)
    n1 = b.noise(v, 0.6, 6, 0.55)
    g = b.noise(v, 300.0, 2, 0.5)
    col = b.ramp(n1.outputs['Fac'], [(0.3, tuple(c * 0.7 for c in base)), (0.7, tuple(c * 1.4 for c in base))])
    b.set('Base Color', b.mix(col.outputs[0], (0.12, 0.12, 0.12), b.maprange(g.outputs['Fac'], 0.6, 0.75, 0, 0.5)))
    b.set('Roughness', b.maprange(n1.outputs['Fac'], 0.3, 0.7, 0.5, 0.85))
    b.set('Normal', b.bump(g.outputs['Fac'], 0.3, 0.003))
    return b.mat


def mat_principled(name, color=(0.5, 0.5, 0.5), rough=0.5, metal=0.0, coat=0.0, emit=None, emit_strength=0.0):
    b = NB(name)
    b.set('Base Color', color).set('Roughness', rough).set('Metallic', metal)
    if coat:
        b.set('Coat Weight', coat)
    if emit:
        b.set('Emission Color', emit).set('Emission Strength', emit_strength)
    return b.mat


def mat_image(name, path, rough=0.6, emission=0.0, coat=0.0, extension='CLIP'):
    b = NB(name)
    tex = b.n('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(path, check_existing=True)
    tex.extension = extension
    b.link(b.coord('UV'), tex.inputs['Vector'])
    b.set('Base Color', tex.outputs['Color']).set('Roughness', rough)
    if emission:
        b.set('Emission Color', tex.outputs['Color']).set('Emission Strength', emission)
    if coat:
        b.set('Coat Weight', coat)
    return b.mat, tex


def mat_volume(name='Fog', density=0.1, color=(0.8, 0.8, 0.8), anisotropy=0.3, noise_scale=None, noise_contrast=(0.45, 0.7),
               emission=None, emission_strength=0.0):
    """Volume material; with noise_scale, density is modulated by 3D noise (clouds/dust)."""
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    vp = nt.nodes.new('ShaderNodeVolumePrincipled')
    vp.inputs['Color'].default_value = (*color, 1)
    vp.inputs['Anisotropy'].default_value = anisotropy
    if emission:
        vp.inputs['Emission Color'].default_value = (*emission, 1)
        vp.inputs['Emission Strength'].default_value = emission_strength
    if noise_scale:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = noise_scale
        nz.inputs['Detail'].default_value = 8
        nz.inputs['Roughness'].default_value = 0.6
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = noise_contrast[0]
        mr.inputs['From Max'].default_value = noise_contrast[1]
        mr.inputs['To Min'].default_value = 0.0
        mr.inputs['To Max'].default_value = density
        nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
        nt.links.new(mr.outputs['Result'], vp.inputs['Density'])
    else:
        vp.inputs['Density'].default_value = density
    nt.links.new(vp.outputs['Volume'], out.inputs['Volume'])
    return m


def volume_box(name, loc, size, mat, coll=None):
    o = prim('cube', name, loc=loc, scale=size, coll=coll, smooth=False)
    set_mat(o, mat)
    return o

# ----------------------------------------------------------------------------- output

def _argv():
    a = sys.argv
    return a[a.index('--') + 1:] if '--' in a else []


def arg(name, default=None, cast=str):
    a = _argv()
    if name in a:
        i = a.index(name)
        if i + 1 < len(a) and not a[i + 1].startswith('--'):
            return cast(a[i + 1])
        return True
    return default


def finish(shot):
    sc = bpy.context.scene
    samples = arg('--samples', None, int)
    if samples:
        sc.eevee.taa_render_samples = samples
    pct = arg('--pct', 100, int)
    sc.render.resolution_percentage = pct
    if arg('--save'):
        os.makedirs(os.path.join(FILM, 'blend'), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(FILM, 'blend', f'{shot}.blend'))
    stills = arg('--stills', None)
    still = arg('--still', None)
    if still:
        stills = str(still)
    if stills:
        # stills are 8-bit JPEG: 16-bit PNGs look posterized in image viewers/Read
        os.makedirs(os.path.join(FILM, 'tests'), exist_ok=True)
        tag = arg('--tag', '')
        isf = sc.render.image_settings
        fmt, depth = isf.file_format, isf.color_depth
        isf.file_format = 'JPEG'
        isf.quality = 92
        for f in [int(x) for x in str(stills).split(',')]:
            sc.frame_set(f)
            sc.render.filepath = os.path.join(FILM, 'tests', f'{shot}{tag}_f{f:04d}.jpg')
            bpy.ops.render.render(write_still=True)
            print('[still]', sc.render.filepath)
        isf.file_format, isf.color_depth = fmt, depth
    if arg('--anim'):
        a = arg('--from', sc.frame_start, int)
        b = arg('--to', sc.frame_end, int)
        outdir = arg('--outdir', os.path.join(FILM, 'renders', shot))
        if not os.path.isabs(outdir):  # Blender resolves bare relative paths against the drive root
            outdir = os.path.join(FILM, outdir)
        os.makedirs(outdir, exist_ok=True)
        sc.frame_start, sc.frame_end = a, b
        sc.frame_step = arg('--step', 1, int)
        if arg('--jpg'):  # quick motion previews
            sc.render.image_settings.file_format = 'JPEG'
            sc.render.image_settings.quality = 85
        sc.render.filepath = os.path.join(outdir, '')
        sc.render.use_overwrite = bool(arg('--overwrite', False))
        sc.render.use_placeholder = False
        bpy.ops.render.render(animation=True)
        print('[anim] done', outdir)
