"""Act V - THE DESK: materials + props for the craftsman's walnut workbench (real scale, meters).

Desk top surface is z = 0. +y = away from the front edge, x = left/right.
build_desk() returns a dict of key positions used by shots/act5_desk.py.
"""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix, Euler
from common import *

TEXD = os.path.join(FILM, 'tex')
PHOTO = os.path.join(FILM, 'renders', 'photo_temple.png')          # T4 handoff image (4F last frame)
PHOTO_FALLBACK = os.path.join(TEXD, 'act5_photo_placeholder.png')
try:  # until the director copies the real 4F frame: newest 4F hold-frame test still is a far better stand-in
    import glob as _glob
    _c = sorted(_glob.glob(os.path.join(FILM, 'tests', '4F_*f0072.jpg')), key=os.path.getmtime)
    if _c:
        PHOTO_FALLBACK = _c[-1]
except Exception:
    pass
R = random.Random(5)

# ----------------------------------------------------------------------------- helpers

def revolve(name, prof, segs=96, coll=None, smooth=True, sharp=35):
    """prof: [(r, z), ...] open profile revolved around Z."""
    bm = bmesh.new()
    rings = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((r * ca, r * sa, z)) for r, z in prof])
    for i in range(segs):
        A, B = rings[i], rings[(i + 1) % segs]
        for j in range(len(prof) - 1):
            try:
                bm.faces.new((A[j], B[j], B[j + 1], A[j + 1]))
            except Exception:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return from_bmesh(name, bm, coll, smooth=smooth, sharp_angle=sharp)


def box(name, size, loc=(0, 0, 0), rot=(0, 0, 0), coll=None, bev=None, seg=2):
    o = prim('cube', name, loc=loc, rot=rot, scale=size, coll=coll, smooth=False)
    if bev:
        bevel(o, bev, seg, 30)
    return o


def cyl(name, r, depth, loc=(0, 0, 0), rot=(0, 0, 0), segs=32, coll=None, bev=None):
    o = prim('cylinder', name, loc=loc, rot=rot, coll=coll, r=r, depth=depth, segments=segs)
    if bev:
        bevel(o, bev, 2, 30)
    return o


def extrude_poly(name, pts2, thick, coll=None, z0=0.0):
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for x, y in pts2]
    top = [bm.verts.new((x, y, z0 + thick)) for x, y in pts2]
    bm.faces.new(bot[::-1]); bm.faces.new(top)
    n = len(pts2)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return from_bmesh(name, bm, coll, smooth=True, sharp_angle=30)


def place(o, loc, yaw=0.0, rot=None):
    o.location = loc
    o.rotation_euler = rot if rot else (0, 0, yaw)
    return o


def inst(src, name, loc, rot=(0, 0, 0), scale=1.0, coll=None):
    o = bpy.data.objects.new(name, src.data)
    link(o, coll)
    o.location = loc
    o.rotation_euler = rot
    o.scale = (scale, scale, scale)
    for m in src.modifiers:
        if m.type == 'BEVEL':
            b = o.modifiers.new('Bevel', 'BEVEL')
            b.width, b.segments, b.limit_method, b.angle_limit, b.harden_normals = m.width, m.segments, m.limit_method, m.angle_limit, m.harden_normals
    return o

# ----------------------------------------------------------------------------- materials

def mat_walnut(name='Walnut', plank=0.125):
    """v4: glued-up walnut planks along X (12.5 cm boards, dark glue seams, per-board tone + figure),
    fine straight grain instead of the old large wavy bands."""
    b = NB(name)
    tc = b.n('ShaderNodeTexCoord')
    sep = b.n('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Object'], sep.inputs[0])
    yb = b.math('DIVIDE', sep.outputs['Y'], plank)
    board = b.math('FLOOR', yb)
    fy = b.math('FRACT', yb)
    seam = b.math('MULTIPLY', b.math('LESS_THAN', fy, 0.006), 1.0)
    seam = b.math('MAXIMUM', seam, b.math('GREATER_THAN', fy, 0.994))
    # per-board offset so the figure does not continue across seams
    cmb = b.n('ShaderNodeCombineXYZ')
    b.link(sep.outputs['X'], cmb.inputs[0])
    b.link(b.math('ADD', sep.outputs['Y'], b.math('MULTIPLY', board, 3.17)), cmb.inputs[1])
    b.link(b.math('ADD', sep.outputs['Z'], b.math('MULTIPLY', board, 1.31)), cmb.inputs[2])
    v = cmb.outputs[0]
    vmap = b.n('ShaderNodeMapping')
    b.link(v, vmap.inputs['Vector'])
    vmap.inputs['Scale'].default_value = (0.35, 1.0, 1.0)      # grain stretched along X
    wave = b.n('ShaderNodeTexWave', wave_type='BANDS', bands_direction='Y')
    wave.inputs['Scale'].default_value = 26.0
    wave.inputs['Distortion'].default_value = 5.0
    wave.inputs['Detail'].default_value = 6.0
    wave.inputs['Detail Scale'].default_value = 2.0
    b.link(vmap.outputs[0], wave.inputs['Vector'])
    vsf = b.n('ShaderNodeMapping'); b.link(v, vsf.inputs['Vector']); vsf.inputs['Scale'].default_value = (6.0, 260.0, 260.0)
    fine = b.noise(vsf.outputs[0], 5.0, 5, 0.6)
    vsp = b.n('ShaderNodeMapping'); b.link(v, vsp.inputs['Vector']); vsp.inputs['Scale'].default_value = (60.0, 1400.0, 1400.0)
    pores = b.noise(vsp.outputs[0], 6.0, 2, 0.5)
    blot = b.noise(v, 2.5, 6, 0.6)
    btone = b.n('ShaderNodeTexWhiteNoise'); btone.noise_dimensions = '1D'
    b.link(board, btone.inputs['W'])
    g = b.math('ADD', b.math('MULTIPLY', wave.outputs['Fac'], 0.45), b.math('MULTIPLY', fine.outputs['Fac'], 0.6))
    col = b.ramp(g, [(0.30, (0.022, 0.010, 0.0045)), (0.55, (0.055, 0.026, 0.011)), (0.80, (0.095, 0.048, 0.022))])
    c1 = b.mix(col.outputs[0], b.mix(col.outputs[0], (0.13, 0.07, 0.035), 0.35), b.maprange(btone.outputs['Value'], 0.0, 1.0, 0.0, 1.0))
    c2 = b.mix(c1, (0.010, 0.005, 0.0025), b.maprange(blot.outputs['Fac'], 0.45, 0.75, 0.0, 0.45))
    c3 = b.mix(c2, (0.004, 0.002, 0.001), seam)
    b.set('Base Color', c3)
    # oiled finish: coat with worn patches + fine scratches
    scr = b.noise(b.coord('Object', (2.0, 2.0, 2.0)), 40.0, 3, 0.7)
    b.set('Roughness', b.maprange(blot.outputs['Fac'], 0.3, 0.7, 0.26, 0.5))
    b.set('Coat Weight', b.maprange(scr.outputs['Fac'], 0.4, 0.7, 0.6, 0.2))
    b.set('Coat Roughness', 0.1)
    h = b.math('ADD', b.math('ADD', pores.outputs['Fac'], b.math('MULTIPLY', fine.outputs['Fac'], 0.5)), b.math('MULTIPLY', seam, -2.0))
    b.set('Normal', b.bump(h, 0.2, 0.0004))
    return b.mat


def mat_sheet(name, img, rough=0.75, bump=0.25, sheen=0.0, albedo=0.72, tint=None, folds=()):
    """tint: per-channel albedo multiply (v13 cyanotype: keeps the Prussian ground saturated under tungsten, where
    the old scalar 0.32 read lavender-grey). folds: local-X / local-Y positions (m) of fold creases (ridge bump)."""
    b = NB(name)
    tex = b.n('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(img, check_existing=True)
    tex.interpolation = 'Cubic'
    b.link(b.coord('UV'), tex.inputs['Vector'])
    fib = b.noise(b.coord('Object', 1.0), 4000.0 if tint else 2400.0, 4, 0.6)
    crease = b.noise(b.coord('Object', 1.0), 18.0, 3, 0.5)
    if tint == 'cyan':
        # cyanotype: separate lines from ground by the green channel, re-colour both, keep the red-pencil markup
        sc_ = b.n('ShaderNodeSeparateColor'); b.link(tex.outputs['Color'], sc_.inputs[0])
        R_, G_, B_ = sc_.outputs[0], sc_.outputs[1], sc_.outputs[2]
        line = b.maprange(G_, 0.07, 0.55, 0.0, 1.0)
        var = b.maprange(B_, 0.08, 0.32, 0.70, 1.0)
        ground = b.mix((0.0, 0.0, 0.0), (0.010, 0.040, 0.150), var)
        col = b.mix(ground, (0.46, 0.53, 0.64), line)
        red = b.maprange(b.math('SUBTRACT', R_, G_), 0.12, 0.35, 0.0, 1.0)
        col = b.mix(col, b.mix(tex.outputs['Color'], (0, 0, 0), 0.35), red)
        b.set('Base Color', col)
        try:
            b.set('Specular IOR Level', 0.25)
        except Exception:
            pass
    elif tint:
        b.set('Base Color', b.mix(tex.outputs['Color'], tuple(tint), 1.0, blend='MULTIPLY'))
    else:
        b.set('Base Color', b.mix(tex.outputs['Color'], (0, 0, 0), 1.0 - albedo))
    b.set('Roughness', b.maprange(fib.outputs['Fac'], 0.3, 0.7, rough - 0.08, rough + 0.08))
    h = b.math('ADD', b.math('MULTIPLY', fib.outputs['Fac'], 0.6 if tint else 1.0), b.math('MULTIPLY', crease.outputs['Fac'], 0.6))
    if folds:
        sep = b.n('ShaderNodeSeparateXYZ'); b.link(b.coord('Object', 1.0), sep.inputs[0])
        for ax, pos in folds:
            d = b.math('ABSOLUTE', b.math('SUBTRACT', sep.outputs[ax], pos))
            ridge = b.math('MAXIMUM', b.math('SUBTRACT', 1.0, b.math('DIVIDE', d, 0.0035)), 0.0)
            h = b.math('ADD', h, b.math('MULTIPLY', b.math('POWER', ridge, 2.0), 6.0))
    b.set('Normal', b.bump(h, bump, 0.00015))
    try:
        b.set('Sheen Weight', sheen)
        b.set('Subsurface Weight', 0.05)
    except Exception:
        pass
    return b.mat


def mat_cutmat(name='CutMat'):
    b = NB(name)
    tex = b.n('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(os.path.join(TEXD, 'act5_mat.png'), check_existing=True)
    tex.image.alpha_mode = 'CHANNEL_PACKED'
    tex.interpolation = 'Cubic'
    b.link(b.coord('UV'), tex.inputs['Vector'])
    grain = b.noise(b.coord('Object', 1.0), 1500.0, 3, 0.6)
    b.set('Base Color', tex.outputs['Color'])
    b.set('Roughness', b.maprange(grain.outputs['Fac'], 0.3, 0.7, 0.42, 0.62))
    b.set('Normal', b.bump(b.math('ADD', b.math('MULTIPLY', tex.outputs['Alpha'], 1.0), b.math('MULTIPLY', grain.outputs['Fac'], 0.2)), 0.35, 0.0003))
    return b.mat


def mat_photo(name='Photo', path=None):
    """Glossy print: image area + white border, emission boost driven by a value for the T4 handoff."""
    b = NB(name)
    tex = b.n('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(path, check_existing=True)
    tex.extension = 'EXTEND'
    tex.interpolation = 'Cubic'
    b.link(b.coord('UV'), tex.inputs['Vector'])
    b.set('Base Color', tex.outputs['Color'])
    b.set('Roughness', 0.32)
    b.set('Coat Weight', 0.6)
    b.set('Coat Roughness', 0.08)
    b.set('Emission Color', tex.outputs['Color'])
    em = b.bsdf.inputs['Emission Strength']
    em.default_value = 0.0
    return b.mat, em


def mat_paint(name, color, rough=0.22):
    b = NB(name)
    n = b.noise(b.coord('Object', 1.0), 900.0, 3, 0.6)
    lg = b.noise(b.coord('Object', 1.0), 60.0, 4, 0.6)
    b.set('Base Color', b.mix(color, tuple(c * 0.75 for c in color), lg.outputs['Fac']))
    b.set('Roughness', b.maprange(n.outputs['Fac'], 0.3, 0.7, rough * 0.7, rough * 1.5))
    b.set('Coat Weight', 0.7).set('Coat Roughness', 0.06)
    b.set('Normal', b.bump(n.outputs['Fac'], 0.05, 0.0001))
    return b.mat


def mat_paint_obj(name, rough=0.22):
    b = NB(name)
    oi = b.n('ShaderNodeObjectInfo')
    n = b.noise(b.coord('Object', 1.0), 900.0, 3, 0.6)
    lg = b.noise(b.coord('Object', 1.0), 60.0, 4, 0.6)
    b.set('Base Color', b.mix(oi.outputs['Color'], b.mix(oi.outputs['Color'], (0, 0, 0), 0.3), lg.outputs['Fac']))
    b.set('Roughness', b.maprange(n.outputs['Fac'], 0.3, 0.7, rough * 0.7, rough * 1.5))
    b.set('Coat Weight', 0.7).set('Coat Roughness', 0.06)
    b.set('Normal', b.bump(n.outputs['Fac'], 0.05, 0.0001))
    return b.mat


def mat_cedar(name='Cedar', scallop=True, rh=0.0037):
    """v13: yellow-olive incense cedar with straight grain along the pencil (annual rings around an off-axis pith,
    seen as long stripes on the cone) + the scalloped paint edge where the cone cuts the hex faces (6 arches).
    v8-v12 (smooth salmon/tan, isotropic noise) read as a finger under the tungsten lamp."""
    b = NB(name)
    tc = b.n('ShaderNodeTexCoord')
    sep = b.n('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Object'], sep.inputs[0])
    X, Y, Z = sep.outputs['X'], sep.outputs['Y'], sep.outputs['Z']
    dn = b.noise(b.coord('Object', (60.0, 900.0, 900.0)), 1.0, 3, 0.5)
    py = b.math('SUBTRACT', Y, 0.021); pz = b.math('ADD', Z, 0.013)
    R = b.math('SQRT', b.math('ADD', b.math('MULTIPLY', py, py), b.math('MULTIPLY', pz, pz)))
    R = b.math('ADD', R, b.math('MULTIPLY', dn.outputs['Fac'], 0.00025))
    ring = b.math('FRACT', b.math('MULTIPLY', R, 900.0))
    late = b.math('POWER', ring, 4.0)                       # dark latewood band at the end of each ring
    fine = b.noise(b.coord('Object', (40.0, 3000.0, 3000.0)), 1.0, 4, 0.6)
    col = b.ramp(b.math('ADD', b.math('MULTIPLY', ring, 0.5), b.math('MULTIPLY', fine.outputs['Fac'], 0.5)),
                 [(0.25, (0.24, 0.165, 0.075)), (0.75, (0.42, 0.31, 0.15))])
    col = b.mix(col.outputs[0], (0.11, 0.065, 0.028), b.math('MULTIPLY', late, 0.9))
    rough = b.maprange(b.math('ADD', b.math('MULTIPLY', late, 0.6), b.math('MULTIPLY', fine.outputs['Fac'], 0.5)), 0.0, 1.0, 0.55, 0.85)
    if scallop:
        oi = b.n('ShaderNodeObjectInfo')
        r = b.math('SQRT', b.math('ADD', b.math('MULTIPLY', Y, Y), b.math('MULTIPLY', Z, Z)))
        a = b.math('ARCTAN2', Z, Y)
        sector = b.math('MODULO', b.math('ADD', a, 4 * math.pi - math.pi / 6), math.pi / 3)
        hr = b.math('DIVIDE', rh * math.cos(math.pi / 6), b.math('COSINE', b.math('SUBTRACT', sector, math.pi / 6)))
        painted = b.math('GREATER_THAN', b.math('DIVIDE', r, hr), 0.905)
        col = b.mix(col, oi.outputs['Color'], painted)
        rough = b.mix(rough, (0.2, 0.2, 0.2), painted)
    b.set('Base Color', col).set('Roughness', rough)
    b.set('Normal', b.bump(b.math('ADD', late, b.math('MULTIPLY', fine.outputs['Fac'], 0.4)), 0.25, 0.00012))
    return b.mat


def mat_graphite(name='Graphite'):
    b = NB(name)
    n = b.noise(b.coord('Object', 1.0), 4000.0, 3, 0.6)
    b.set('Base Color', (0.035, 0.035, 0.04)).set('Metallic', 0.6)
    b.set('Roughness', b.maprange(n.outputs['Fac'], 0.3, 0.7, 0.25, 0.5))
    b.set('Normal', b.bump(n.outputs['Fac'], 0.3, 0.0001))
    return b.mat


def mat_blued(name='Blued'):
    b = NB(name)
    n = b.noise(b.coord('Object', 1.0), 900.0, 4, 0.6)
    b.set('Base Color', b.mix((0.04, 0.10, 0.42), (0.10, 0.03, 0.30), n.outputs['Fac']))
    b.set('Metallic', 1.0).set('Roughness', 0.16)
    return b.mat


def mat_ruby(name='Ruby'):
    b = NB(name)
    b.set('Base Color', (0.9, 0.03, 0.06)).set('Roughness', 0.03).set('Transmission Weight', 0.6)
    b.set('Emission Color', (1.0, 0.05, 0.08)).set('Emission Strength', 0.4)
    b.set('IOR', 1.76)
    return b.mat


def mat_enamel(name='Enamel'):
    b = NB(name)
    n = b.noise(b.coord('Object', 1.0), 600.0, 4, 0.6)
    # v13: ivory, not paper-white (the chapter ring was the brightest thing in 5C f16 and a white smear mid-dive)
    b.set('Base Color', b.mix((0.70, 0.67, 0.58), (0.58, 0.54, 0.45), b.maprange(n.outputs['Fac'], 0.5, 0.8, 0, 1)))
    b.set('Roughness', 0.18).set('Coat Weight', 1.0).set('Coat Roughness', 0.03)
    return b.mat


def mat_steel_brushed(name='SteelBrushed', base=(0.62, 0.63, 0.64), dir_scale=(3000.0, 6.0, 6.0), rough=(0.18, 0.38)):
    b = NB(name)
    v = b.coord('Object', dir_scale)
    n = b.noise(v, 4.0, 4, 0.6)
    big = b.noise(b.coord('Object', 1.0), 90.0, 4, 0.6)
    b.set('Base Color', b.mix(base, tuple(c * 0.72 for c in base), big.outputs['Fac']))
    b.set('Metallic', 1.0)
    b.set('Roughness', b.maprange(b.math('ADD', n.outputs['Fac'], b.math('MULTIPLY', big.outputs['Fac'], 0.4)), 0.4, 1.1, rough[0], rough[1]))
    b.set('Normal', b.bump(n.outputs['Fac'], 0.12, 0.0001))
    try:
        b.set('Anisotropic', 0.6)
    except Exception:
        pass
    return b.mat


def mat_caliper(name='Caliper', band_y=0.0068, face_z=0.0012, x0=0.0, x1=0.15):
    """Brushed steel with an etched mm scale along local X (beam)."""
    b = NB(name)
    tc = b.n('ShaderNodeTexCoord')
    sep = b.n('ShaderNodeSeparateXYZ')
    b.link(tc.outputs['Object'], sep.inputs[0])
    x = sep.outputs['X']; y = sep.outputs['Y']; z = sep.outputs['Z']
    mm = b.math('FRACT', b.math('MULTIPLY', x, 1000.0))
    tick = b.math('LESS_THAN', mm, 0.16)
    five = b.math('LESS_THAN', b.math('FRACT', b.math('MULTIPLY', x, 200.0)), 0.032)
    ten = b.math('LESS_THAN', b.math('FRACT', b.math('MULTIPLY', x, 100.0)), 0.016)
    ylen = b.math('ADD', 0.0012, b.math('ADD', b.math('MULTIPLY', five, 0.0010), b.math('MULTIPLY', ten, 0.0012)))
    inband = b.math('LESS_THAN', b.math('SUBTRACT', band_y, y), ylen)
    upper = b.math('GREATER_THAN', y, 0.0)
    onface = b.math('GREATER_THAN', z, face_z)
    inrange = b.math('MULTIPLY', b.math('GREATER_THAN', x, x0), b.math('LESS_THAN', x, x1))
    m = b.math('MULTIPLY', b.math('MULTIPLY', b.math('MULTIPLY', tick, inband), b.math('MULTIPLY', upper, onface)), inrange)
    n = b.noise(b.coord('Object', (2500.0, 10.0, 10.0)), 4.0, 4, 0.6)
    b.set('Base Color', b.mix((0.66, 0.67, 0.68), (0.02, 0.02, 0.02), m))
    b.set('Metallic', b.maprange(m, 0, 1, 1.0, 0.0))
    b.set('Roughness', b.maprange(n.outputs['Fac'], 0.3, 0.7, 0.16, 0.34))
    b.set('Normal', b.bump(b.math('ADD', n.outputs['Fac'], b.math('MULTIPLY', m, -0.6)), 0.15, 0.0001))
    try:
        b.set('Anisotropic', 0.6)
    except Exception:
        pass
    return b.mat


def mat_perlage(name='Perlage', base=(0.80, 0.58, 0.28)):
    """v13: fine perlage - 0.4 mm overlapping spots, each finely circular-grained (55 rings per cell unit, very
    low bump) + per-spot reflectance jitter. v12 (3.5 rings, bump 0.25) read as soap bubbles / leopard cells."""
    b = NB(name)
    v = b.coord('Object', 1.0)
    vo = b.voronoi(v, 2600.0)
    ring = b.math('FRACT', b.math('MULTIPLY', vo.outputs['Distance'], 9.0))
    cellv = b.n('ShaderNodeSeparateColor'); b.link(vo.outputs['Color'], cellv.inputs[0])
    n = b.noise(v, 300.0, 4, 0.6)
    col = b.mix(base, tuple(c * 0.62 for c in base), b.maprange(n.outputs['Fac'], 0.4, 0.8, 0, 1))
    b.set('Base Color', b.mix(col, tuple(c * 0.86 for c in base), b.maprange(cellv.outputs[0], 0, 1, 0, 0.5)))
    b.set('Metallic', 1.0)
    rr = b.math('ADD', b.maprange(ring, 0, 1, 0.18, 0.26), b.maprange(cellv.outputs[1], 0, 1, -0.03, 0.04))
    b.set('Roughness', rr)
    b.set('Normal', b.bump(ring, 0.05, 0.00002))
    try:
        b.set('Anisotropic', 0.6)
    except Exception:
        pass
    return b.mat


def mat_wheel(name='WheelBrass', base=(0.92, 0.57, 0.19)):
    """v13: gilt watch-wheel brass with circular graining (anisotropic, tangent radial around the wheel axis): faces
    mirror the dark case and only streak where they meet a light; bevelled teeth edges catch the rims. The generic
    worn-brass noise read as sand/concrete at 5 mm."""
    b = NB(name)
    tg = b.n('ShaderNodeTangent'); tg.direction_type = 'RADIAL'; tg.axis = 'Z'
    n = b.noise(b.coord('Object', 1.0), 900.0, 3, 0.5)
    big = b.noise(b.coord('Object', 1.0), 120.0, 3, 0.5)
    b.set('Base Color', b.mix(base, tuple(c * 0.78 for c in base), b.maprange(big.outputs['Fac'], 0.35, 0.75, 0.0, 1.0)))
    b.set('Metallic', 1.0)
    b.set('Roughness', b.maprange(n.outputs['Fac'], 0.3, 0.7, 0.10, 0.20))
    try:
        b.set('Anisotropic', 0.5)
        b.link(tg.outputs['Tangent'], b.bsdf.inputs['Tangent'])
    except Exception as e:
        print('[desk] wheel aniso', e)
    return b.mat


def mat_cotes(name='Cotes', base=(0.60, 0.62, 0.66)):
    """v13: Cotes de Geneve on the bridges (slightly arced parallel stripes, 2.1 mm pitch) - bridges now read
    differently from the perlage plate."""
    b = NB(name)
    tc = b.n('ShaderNodeTexCoord')
    sep = b.n('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Object'], sep.inputs[0])
    x, y = sep.outputs['X'], sep.outputs['Y']
    u = b.math('ADD', b.math('MULTIPLY', x, 0.6), b.math('MULTIPLY', y, 0.8))
    w = b.math('ADD', b.math('MULTIPLY', x, -0.8), b.math('MULTIPLY', y, 0.6))
    wm = b.math('FRACT', b.math('MULTIPLY', w, 1.0 / 0.012))          # arcs restart every 12 mm (one cutter pass)
    wc = b.math('MULTIPLY', b.math('SUBTRACT', wm, 0.5), 0.012)
    s = b.math('FRACT', b.math('DIVIDE', b.math('ADD', u, b.math('MULTIPLY', b.math('MULTIPLY', wc, wc), 33.0)), 0.0021))
    stripe = b.math('ABSOLUTE', b.math('MULTIPLY', b.math('SUBTRACT', s, 0.5), 2.0))
    n = b.noise(b.coord('Object', 1.0), 400.0, 4, 0.6)
    b.set('Base Color', b.mix(tuple(c * 0.94 for c in base), base, stripe))
    b.set('Metallic', 1.0)
    b.set('Roughness', b.math('ADD', b.maprange(stripe, 0, 1, 0.24, 0.18), b.maprange(n.outputs['Fac'], 0.3, 0.7, -0.03, 0.04)))
    b.set('Normal', b.bump(stripe, 0.03, 0.00003))
    try:
        b.set('Anisotropic', 0.5)
    except Exception:
        pass
    return b.mat


def mat_guilloche(name='Guilloche', base=(0.75, 0.52, 0.25)):
    """Engine-turned gold: concentric rings + wavy sunburst, engraved monogram ring.
    v13: polished (rough 0.04-0.12) darker gold, 900 rings/m (2600 moired into a cream 'golf ball' disc in 5B):
    the lid now mirrors the dark room with one crisp lamp highlight."""
    b = NB(name)
    tc = b.n('ShaderNodeTexCoord')
    sep = b.n('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Object'], sep.inputs[0])
    x, y = sep.outputs['X'], sep.outputs['Y']
    r = b.math('SQRT', b.math('ADD', b.math('MULTIPLY', x, x), b.math('MULTIPLY', y, y)))
    ang = b.math('ARCTAN2', y, x)
    wav = b.math('MULTIPLY', b.math('SINE', b.math('MULTIPLY', ang, 36.0)), 0.00035)
    rings = b.math('FRACT', b.math('MULTIPLY', b.math('ADD', r, wav), 900.0))
    rays = b.math('FRACT', b.math('MULTIPLY', ang, 120.0 / 6.2832))
    band = b.math('MULTIPLY', b.math('GREATER_THAN', r, 0.0175), b.math('LESS_THAN', r, 0.0195))
    pat = b.mix(rings, rays, band)
    b.set('Base Color', b.mix(base, tuple(c * 0.70 for c in base), b.maprange(pat, 0.0, 1.0, 0.0, 0.5)))
    b.set('Metallic', 1.0)
    b.set('Roughness', b.maprange(pat, 0, 1, 0.04, 0.12))
    b.set('Normal', b.bump(pat, 0.15, 0.00003))
    try:
        b.set('Anisotropic', 0.8)
    except Exception:
        pass
    return b.mat


def mat_lens_glass(name='LensGlass'):
    b = NB(name)
    b.set('Base Color', (0.97, 0.99, 1.0)).set('Roughness', 0.0).set('IOR', 1.52).set('Transmission Weight', 1.0)
    try:
        b.mat.surface_render_method = 'DITHERED'
        b.mat.use_raytrace_refraction = True
        b.mat.thickness_mode = 'SPHERE'
    except Exception as e:
        print('[desk] lens glass opts', e)
    return b.mat


def mat_crystal(name='Crystal'):
    """v7: thin watch glass as transparent + Fresnel glossy (no refraction). The refractive version fell back to
    the light probe through the dome and laid a milky veil over the movement in every 5C frame."""
    b = NB(name)
    nt = b.nt
    for n in list(nt.nodes):
        if n.type == 'BSDF_PRINCIPLED':
            nt.nodes.remove(n)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    gl = nt.nodes.new('ShaderNodeBsdfGlossy')
    gl.inputs['Roughness'].default_value = 0.07
    gl.inputs['Color'].default_value = (0.45, 0.46, 0.48, 1)
    fr = nt.nodes.new('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.5
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 0.30   # v13: 0.85 -> 0.30 (white 'card' = moonlit window mirrored)
    nt.links.new(fr.outputs[0], mul.inputs[0])
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(mul.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], b.out.inputs['Surface'])
    try:
        b.mat.surface_render_method = 'BLENDED'
    except Exception:
        pass
    return b.mat


def mat_ceramic(name, color, rough=0.12):
    b = NB(name)
    n = b.noise(b.coord('Object', 1.0), 200.0, 4, 0.6)
    b.set('Base Color', b.mix(color, tuple(c * 0.6 for c in color), b.maprange(n.outputs['Fac'], 0.4, 0.8, 0, 1)))
    b.set('Roughness', rough).set('Coat Weight', 0.8).set('Coat Roughness', 0.03)
    return b.mat


def mat_plaster(name='Wall'):
    b = NB(name)
    n = b.noise(b.coord('Object', 1.0), 4.0, 8, 0.65)
    n2 = b.noise(b.coord('Object', 1.0), 80.0, 4, 0.6)
    b.set('Base Color', b.mix((0.17, 0.18, 0.19), (0.10, 0.105, 0.11), n.outputs['Fac']))   # v5: was ~5 % albedo - moon patch never showed
    b.set('Roughness', 0.85)
    b.set('Normal', b.bump(n2.outputs['Fac'], 0.3, 0.002))
    return b.mat

# ----------------------------------------------------------------------------- props

def make_sheet(name, img, w, h, loc, yaw, coll, curl=0.004, lift=0.0, seed=0, mat=None):
    rr = random.Random(seed)
    bm = bmesh.new()
    nx, ny = 30, int(30 * h / w) + 1
    uvl = bm.loops.layers.uv.new('UV')
    vs = []
    k1, k2 = rr.uniform(0.5, 1.0), rr.uniform(0.5, 1.0)
    ph = rr.uniform(0, 6)
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            x, y = (u - 0.5) * w, (v - 0.5) * h
            # edge curl + gentle undulation
            e = max(abs(u - 0.5) * 2, abs(v - 0.5) * 2)
            z = curl * max(0.0, e - 0.7) ** 2 / 0.09 * (0.6 + 0.4 * math.sin(u * 5 + ph))
            # v7: undulation kept >= 0 - the old +-0.6 mm dipped the sheet under the cutting mat, and the mat showed
            # through as a big round "hole" (the mystery disc in 5B f8-16)
            z += 0.00025 * (1.0 + math.sin(u * 7.0 * k1 + ph) * math.sin(v * 5.0 * k2)) + lift
            row.append((bm.verts.new((x, y, z)), (u, v)))
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((vs[j][i][0], vs[j][i + 1][0], vs[j + 1][i + 1][0], vs[j + 1][i][0]))
            for l, (jj, ii) in zip(f.loops, ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i))):
                l[uvl].uv = vs[jj][ii][1]
    o = from_bmesh(name, bm, coll, smooth=True)
    sol = o.modifiers.new('Solid', 'SOLIDIFY')
    sol.thickness = 0.00025
    sol.offset = -1
    set_mat(o, mat or mat_sheet(name + 'M', img))
    place(o, loc, yaw)
    return o


def make_pencil(name, color, length=0.165, coll=None, eraser=False, sharpen=True, mats=None):
    """Hexagonal pencil along +X, tip at x = +length/2 (unless unsharpened)."""
    cedar, graph, ferrule, rubber = mats
    paint = bpy.data.materials.get('PencilPaint') or mat_paint_obj('PencilPaint')
    rh = 0.0037                    # corner radius of the hex
    bm = bmesh.new()
    body_end = length / 2 - (0.022 if sharpen else 0.0)
    x0 = -length / 2 + (0.012 if eraser else 0.0)
    hexv = [(rh * math.cos(math.pi / 6 + k * math.pi / 3), rh * math.sin(math.pi / 6 + k * math.pi / 3)) for k in range(6)]
    # body (hex prism)
    ringA = [bm.verts.new((x0, y, z)) for y, z in hexv]
    ringB = [bm.verts.new((body_end, y, z)) for y, z in hexv]
    bm.faces.new(ringA[::-1])
    for k in range(6):
        f = bm.faces.new((ringA[k], ringA[(k + 1) % 6], ringB[(k + 1) % 6], ringB[k]))
        f.material_index = 0
    if sharpen:
        # cone: hex ring -> round ring of wood -> graphite tip, scalloped paint edge via vertex position
        n = 36
        def ring_at(x, rad, hexmix):
            out = []
            for i in range(n):
                a = 2 * math.pi * i / n
                # point on hex boundary at angle a
                sector = (a - math.pi / 6) % (math.pi / 3)
                hr = rh * math.cos(math.pi / 6) / math.cos(sector - math.pi / 6)
                rr = rad * (hexmix * hr / rh + (1 - hexmix))
                out.append(bm.verts.new((x, rr * math.cos(a), rr * math.sin(a))))
            return out
        # bridge hex end to 36-ring
        r0 = ring_at(body_end, rh, 1.0)
        for i in range(n):
            a = 2 * math.pi * i / n
            k = int(((a - math.pi / 6) % (2 * math.pi)) // (math.pi / 3))
        # connect body end hex ring to r0 via fan of tris
        for i in range(n):
            a = 2 * math.pi * (i + 0.5) / n
            k = int(((a - math.pi / 6) % (2 * math.pi)) // (math.pi / 3))
            k = (k + 0) % 6
        rings = [r0]
        steps = [(0.004, 0.86, 0.6), (0.010, 0.55, 0.0), (0.0175, 0.24, 0.0), (0.0185, 0.20, 0.0), (0.0215, 0.035, 0.0), (0.022, 0.0, 0.0)]
        for dx, rad, hm in steps:
            rings.append(ring_at(body_end + dx, rh * rad if rad > 0 else 0.00001, hm))
        for ri in range(len(rings) - 1):
            A, B = rings[ri], rings[ri + 1]
            for i in range(n):
                f = bm.faces.new((A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]))
                f.material_index = 1 if ri < 3 else 2
        bm.faces.new(rings[-1])
        # stitch hex ring to round ring (hidden seam, same position) - close gap with faces
        for i in range(n):
            pass
    else:
        bm.faces.new(ringB)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = from_bmesh(name, bm, coll, smooth=True, sharp_angle=40)
    o.color = (*color, 1.0)
    o.data.materials.append(paint); o.data.materials.append(cedar); o.data.materials.append(graph)
    bevel(o, 0.00035, 2, 40)
    parts = [o]
    if eraser:
        fer = cyl(name + 'Fer', rh * 1.02, 0.011, loc=(-length / 2 + 0.0065, 0, 0), rot=(0, math.pi / 2, 0), segs=36, coll=coll)
        set_mat(fer, ferrule)
        for k in range(3):
            rg = prim('torus', name + f'Rib{k}', loc=(-length / 2 + 0.003 + k * 0.0035, 0, 0), rot=(0, math.pi / 2, 0), coll=coll, R=rh * 1.03, r=0.00028, su=36, sv=6)
            set_mat(rg, ferrule); parts.append(rg)
        er = cyl(name + 'Eraser', rh * 0.95, 0.007, loc=(-length / 2 - 0.0025, 0, 0), rot=(0, math.pi / 2, 0), segs=36, coll=coll, bev=0.0008)
        set_mat(er, rubber)
        parts += [fer, er]
    root = empty(name + 'Root', coll=coll)
    for p in parts:
        p.parent = root
    return root


def make_mech_pencil(name, coll, mats):
    steel, black, chrome = mats
    root = empty(name + 'Root', coll=coll)
    L = 0.145
    body = revolve(name + 'Body', [(0.0, -L / 2), (0.0040, -L / 2), (0.0042, -L / 2 + 0.002), (0.0042, 0.02), (0.0040, 0.024),
                                    (0.0040, 0.05), (0.0030, 0.062), (0.0010, 0.066), (0.00045, 0.066), (0.00045, 0.0715), (0.00025, 0.0715), (0.00025, 0.0745), (0.0, 0.0745)], 40, coll)
    body.rotation_euler = (0, math.pi / 2, 0)
    set_mat(body, steel)
    grip = cyl(name + 'Grip', 0.00435, 0.026, loc=(0.037, 0, 0), rot=(0, math.pi / 2, 0), segs=48, coll=coll)
    set_mat(grip, black)
    cap = cyl(name + 'Cap', 0.0036, 0.012, loc=(-L / 2 - 0.006, 0, 0), rot=(0, math.pi / 2, 0), segs=32, coll=coll, bev=0.0006)
    set_mat(cap, chrome)
    clip = box(name + 'Clip', (0.045, 0.002, 0.0008), loc=(-0.045, 0, 0.0049), coll=coll, bev=0.0003)
    set_mat(clip, chrome)
    for p in (body, grip, cap, clip):
        p.parent = root
    return root


def make_calipers(name, coll, steel, dark):
    root = empty(name + 'Root', coll=coll)
    beam = box(name + 'Beam', (0.19, 0.016, 0.0034), loc=(0.07, 0.0, 0.0017), coll=coll, bev=0.0004)
    set_mat(beam, steel)
    # fixed jaw (pointing -Y) + small upper jaw (+Y)
    jaw = extrude_poly(name + 'Jaw', [(-0.025, 0.008), (-0.006, 0.008), (-0.006, -0.008), (-0.010, -0.040), (-0.014, -0.046), (-0.017, -0.040), (-0.025, -0.008)], 0.0034, coll)
    set_mat(jaw, steel); bevel(jaw, 0.0004, 2, 30)
    ujaw = extrude_poly(name + 'UJaw', [(-0.016, 0.008), (-0.010, 0.008), (-0.011, 0.020), (-0.013, 0.021), (-0.016, 0.012)], 0.0026, coll, z0=0.0004)
    set_mat(ujaw, steel)
    # slider
    sx = 0.012
    sl = extrude_poly(name + 'Slider', [(sx, 0.0095), (sx + 0.045, 0.0095), (sx + 0.045, -0.0095), (sx + 0.004, -0.0095), (sx + 0.0045, -0.040),
                                         (sx + 0.0005, -0.046), (sx - 0.0025, -0.040), (sx - 0.0005, -0.0095), (sx - 0.002, -0.0095)], 0.0058, coll, z0=-0.0006)
    set_mat(sl, steel); bevel(sl, 0.0004, 2, 30)
    win = box(name + 'Vernier', (0.03, 0.006, 0.0002), loc=(sx + 0.022, 0.006, 0.0053), coll=coll)
    set_mat(win, dark)
    screw = cyl(name + 'Lock', 0.0025, 0.004, loc=(sx + 0.022, 0.0, 0.0069), segs=24, coll=coll, bev=0.0004)
    set_mat(screw, steel)
    wheel = cyl(name + 'Thumb', 0.004, 0.003, loc=(sx + 0.040, -0.012, 0.0017), segs=24, coll=coll)
    set_mat(wheel, dark)
    rod = box(name + 'Depth', (0.06, 0.0015, 0.0012), loc=(0.19, 0.0, 0.0005), coll=coll)
    set_mat(rod, steel)
    for p in (beam, jaw, ujaw, sl, win, screw, wheel, rod):
        p.parent = root
    return root


def make_tweezers(name, coll, steel):
    root = empty(name + 'Root', coll=coll)
    for s in (-1, 1):
        bm = bmesh.new()
        n = 24
        prof = []
        for i in range(n + 1):
            t = i / n
            x = -0.06 + 0.12 * t
            w = 0.0045 * (1 - t) + 0.0007 * t
            y = s * (0.0016 + 0.0042 * math.sin(math.pi * min(1, t * 1.2)) ** 0.8 * (1 - t ** 4) + 0.0008 * (1 - t))
            prof.append((x, y, w))
        top, bot = [], []
        for x, y, w in prof:
            top.append([bm.verts.new((x, y - 0.0004, 0.0012 + w * 0 - 0.0)), bm.verts.new((x, y + 0.0004, 0.0012))])
        for (x, y, w) in prof:
            pass
        bm.free()
        # simpler: a tapered thin box per blade, bent with rotation
        blade = box(name + f'Blade{s}', (0.12, 0.0045, 0.0007), loc=(0, s * 0.0028, 0.0012), coll=coll, bev=0.0002)
        sd = blade.modifiers.new('Taper', 'SIMPLE_DEFORM')
        sd.deform_method = 'TAPER'; sd.factor = -1.2; sd.deform_axis = 'X'
        blade.rotation_euler = (0, 0, -s * 0.03)
        set_mat(blade, steel)
        blade.parent = root
    return root


def make_screw(name, coll, head_mat, slot_mat, r=0.0009, L=0.0035):
    head = cyl(name, r, r * 0.6, loc=(0, 0, 0), segs=24, coll=coll, bev=r * 0.15)
    set_mat(head, head_mat)
    return head


def make_loupe(name, coll, brass, glass, black):
    """Folding linen tester: square base frame, two side legs, round lens on top. Opening along local X."""
    root = empty(name + 'Root', coll=coll)
    A, a = 0.050, 0.036          # outer/inner square
    H = 0.046
    parts = []
    # base frame (4 bars)
    t = 0.0025
    for (sx, sy, lx, ly) in ((A, (A - a) / 2, 0, (A + a) / 4), (A, (A - a) / 2, 0, -(A + a) / 4),
                             ((A - a) / 2, a, (A + a) / 4, 0), ((A - a) / 2, a, -(A + a) / 4, 0)):
        parts.append(box(name + 'Base', (sx, sy, t), loc=(lx, ly, t / 2), coll=coll, bev=0.0004))
    # reticle scale on base (thin dark ticks)
    for k in range(13):
        parts.append(box(name + 'Tick', (0.0004, 0.002 if k % 5 else 0.0035, 0.0002), loc=(-0.015 + k * 0.0025, -(A + a) / 4 + 0.001, t + 0.0001), coll=coll))
    # side legs (at +-Y), with window cut as frame of 4 bars
    for s in (-1, 1):
        y = s * (A / 2 - 0.0008)
        leg = extrude_poly(name + 'Leg', [(-A / 2, 0.0025), (A / 2, 0.0025), (A / 2 - 0.006, H - 0.002), (-A / 2 + 0.006, H - 0.002)], 0.0016, coll)
        leg.rotation_euler = (math.pi / 2, 0, 0); leg.location = (0, y + 0.0008, 0)
        bevel(leg, 0.0004, 2, 30)
        parts.append(leg)
        # hinge pins
        for lx in (-A / 2 + 0.002, A / 2 - 0.002):
            parts.append(cyl(name + 'Pin', 0.0012, 0.0035, loc=(lx, y, 0.003), rot=(math.pi / 2, 0, 0), segs=16, coll=coll))
    # top plate with round hole: ring + 4 corner fillers
    ring = revolve(name + 'LensRing', [(0.0185, H - 0.001), (0.0245, H - 0.001), (0.0250, H + 0.0035), (0.0185, H + 0.0035), (0.0185, H - 0.001)], 96, coll)
    parts.append(ring)
    # v13: knurled focusing ring (180 ridges) - the slab-built loupe needed edges that catch light
    bm = bmesh.new()
    for k in range(180):
        a = 2 * math.pi * k / 180
        m = Matrix.Translation((0.02505 * math.cos(a), 0.02505 * math.sin(a), H + 0.0013)) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Diagonal((0.0005, 0.00045, 0.0034, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    parts.append(from_bmesh(name + 'Knurl', bm, coll, smooth=False))
    for s in (-1, 1):   # top plate wings joining ring to the legs
        parts.append(box(name + 'Top', (A - 0.012, 0.010, 0.0016), loc=(0, s * (A / 2 - 0.005), H - 0.001), coll=coll, bev=0.0004))
    lens = revolve(name + 'Lens', [(0.0, H - 0.0035), (0.010, H - 0.0028), (0.0188, H - 0.0006), (0.0190, H + 0.001), (0.0188, H + 0.0026),
                                   (0.010, H + 0.0048), (0.0, H + 0.0055)], 96, coll, sharp=80)
    set_mat(lens, glass)
    lens.visible_shadow = False
    for p in parts:
        set_mat(p, brass)
        p.parent = root
    lens.parent = root
    return root


def make_lamp(name, coll, enamel, steel, bulb_mat, inner):
    """Architect lamp: returns (root, head_empty). Head aims along its local -Z."""
    root = empty(name + 'Root', coll=coll)
    base = revolve(name + 'Base', [(0.0, 0.0), (0.075, 0.0), (0.078, 0.006), (0.07, 0.016), (0.02, 0.02), (0.012, 0.03), (0.0, 0.03)], 64, coll)
    set_mat(base, enamel)
    base.parent = root
    head = empty(name + 'Head', coll=coll)
    shade = revolve(name + 'Shade', [(0.0, 0.07), (0.018, 0.07), (0.022, 0.064), (0.030, 0.05), (0.068, 0.0), (0.071, -0.004), (0.0695, -0.004),
                                     (0.066, 0.0), (0.028, 0.048), (0.0, 0.066)], 72, coll)
    set_mat(shade, enamel)
    shade.parent = head
    liner = revolve(name + 'Liner', [(0.0275, 0.047), (0.0655, 0.0005)], 72, coll)
    set_mat(liner, inner)
    liner.parent = head
    bulb = prim('sphere', name + 'Bulb', loc=(0, 0, 0.030), coll=coll, r=0.017, u=32, v=16)
    bulb.visible_shadow = False
    set_mat(bulb, bulb_mat)
    bulb.parent = head
    return root, head


def make_watch(name, coll, M, rng, lid_angle=30.0, lid_mat=None):
    """Open-face skeleton pocket watch at origin, 12 o'clock = +Y. Returns (root, gears[], spec)."""
    root = empty(name + 'Root', coll=coll)
    gold, brass, perl, steel, blued, ruby, enamel, crystal, dark = (M['gold'], M.get('wheel', M['wbrass']), M['perlage'], M['wsteel'], M['blued'], M['ruby'], M['enamel'], M['crystal'], M['dark'])
    Rc = 0.0250
    case = revolve(name + 'Case', [(0.0, 0.0005), (0.019, 0.0), (0.0232, 0.0012), (0.0250, 0.0045), (0.0252, 0.0065), (0.0244, 0.0088),
                                   (0.0236, 0.0099), (0.0222, 0.0101), (0.0217, 0.0094), (0.0215, 0.0030), (0.0, 0.0030)], 128, coll, sharp=30)
    set_mat(case, gold); bevel(case, 0.00012, 2, 30)
    # reeded bezel band (knurl) as many tiny boxes
    bm = bmesh.new()
    for k in range(180):
        a = 2 * math.pi * k / 180
        m = Matrix.Translation((0.02405 * math.cos(a), 0.02405 * math.sin(a), 0.0090)) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Diagonal((0.00025, 0.0007, 0.0012, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    kn_o = from_bmesh(name + 'Knurl', bm, coll, smooth=False)
    set_mat(kn_o, gold)
    knurl = [kn_o]
    plate = cyl(name + 'Plate', 0.0213, 0.0013, loc=(0, 0, 0.0037), segs=128, coll=coll, bev=0.0002)
    set_mat(plate, perl)
    parts = [case, plate] + knurl
    gears = []      # (obj, teeth, turns/s, direction, phase)
    # v13: a REAL centre/third mesh for the T5 hero frame. Chunky 48-tooth centre wheel (module 0.3 mm) at z 6.0 mm;
    # the third pinion (8 leaves, pitch r 1.2 mm) sits at r_c + r_p = 8.4 mm from the centre arbor at the centre
    # wheel's height, its leaves phased into the wheel's gaps; the third wheel is coaxial BELOW it (z 4.9 mm) so
    # nothing covers the engagement from above. Rates by tooth ratio (pinion = centre * 48 / 8). Rounded tooth tips
    # (bevel ~0.15 x thickness) instead of the flat lands that caught the lamp as 'LED dashes'.
    TH3 = math.radians(-39.0)
    rc, zc, mod = 0.0072, 0.0060, 0.0003
    rp = mod * 8 / 2
    p3 = ((rc + rp) * math.cos(TH3), (rc + rp) * math.sin(TH3))
    c_rate = 0.05
    stc, stp = 2 * math.pi / 48, 2 * math.pi / 8
    ph_c = TH3 % stc                                        # a wheel gap on the centre->third line
    ph_p = (TH3 + math.pi - 0.5 * stp) % stp                # a pinion leaf pointing back into that gap
    g = make_gear(name + 'Centre', teeth=48, r=rc, depth=mod * 2.5, thick=0.0008, hole=0.00035, rim=rc * 0.78, spokes=4, spoke_w=rc * 0.11,
                  hub=rc * 0.2, coll=coll, mat=brass, bevel_w=0.00012, windows='spokes', hub_thick=0.0012)
    g.location = (0, 0, zc)
    gears.append((g, 48, c_rate, 1, ph_c))
    pin = make_gear(name + 'ThirdPin', teeth=8, r=rp, depth=mod * 2.5, thick=0.0017, hole=0.0001, windows='solid', coll=coll, mat=steel, bevel_w=0.00008)
    pin.location = (p3[0], p3[1], zc - 0.00035)
    gears.append((pin, 8, c_rate * 48 / 8, -1, ph_p))
    g3 = make_gear(name + 'Third', teeth=60, r=0.0060, depth=0.0002 * 2.5, thick=0.0006, hole=0.00035, rim=0.0060 * 0.80, spokes=5, spoke_w=0.0006,
                   hub=0.0012, coll=coll, mat=brass, bevel_w=0.0001, windows='spokes', hub_thick=0.0009)
    g3.location = (p3[0], p3[1], 0.0049)
    gears.append((g3, 60, c_rate * 48 / 8, -1, 0.0))
    for nm_, (x, y) in (('Centre', (0, 0)), ('Third', p3)):
        arb = cyl(name + nm_ + 'Arbor', 0.00028, 0.0055 if nm_ == 'Centre' else 0.0024, loc=(x, y, 0.0068 if nm_ == 'Centre' else 0.00555), segs=16, coll=coll)
        set_mat(arb, steel); parts.append(arb)
    parts += [g, pin, g3]
    train = [('Fourth', 70, 0.0052, (0.0012, -0.0150), 0.00045, 5, 1, 0.0058), ('Escape', 15, 0.0034, (-0.0085, -0.0122), 0.00040, 0, -1, 0.0057),
             ('Barrel', 90, 0.0088, (-0.0085, 0.0098), 0.00060, 0, 1, 0.0050)]
    for k, (nm, z, r, (x, y), th, sp, d, zz) in enumerate(train):
        mat = steel if nm == 'Barrel' else brass
        g = make_gear(name + nm, teeth=z, r=r, depth=r * 0.09, thick=th, hole=0.00035, rim=r * 0.80, spokes=max(sp, 4), spoke_w=r * 0.10,
                      hub=r * 0.2, coll=coll, mat=mat, bevel_w=th * 0.12, windows='spokes' if nm != 'Barrel' else 'solid', hub_thick=th * 1.6)
        g.location = (x, y, zz)
        rate = {'Fourth': 0.5, 'Escape': 1.6, 'Barrel': 0.02}[nm]
        gears.append((g, z, rate, d, 0.0))
        pin = make_gear(name + nm + 'Pin', teeth=8, r=0.0011, depth=0.0003, thick=0.0016, hole=0.0001, windows='solid', coll=coll, mat=steel, bevel_w=0.00006)
        pin.location = (x, y, zz + 0.0010)
        gears.append((pin, 8, rate, d, 0.0))
        arb = cyl(name + nm + 'Arbor', 0.00028, 0.006, loc=(x, y, 0.0070), segs=16, coll=coll)
        set_mat(arb, steel)
        parts += [g, pin, arb]
    # v13: ratchet + crown wheel on the barrel bridge, click spring (density at the 5C rise)
    rat = make_gear(name + 'Ratchet', teeth=30, r=0.0040, depth=0.0006, thick=0.0006, hole=0.0006, windows='solid', coll=coll, mat=steel, bevel_w=0.00008)
    rat.location = (-0.0085, 0.0098, 0.0085)
    gears.append((rat, 30, 0.02, 1, 0.0))
    cw = make_gear(name + 'CrownWheel', teeth=24, r=0.0026, depth=0.0004, thick=0.0005, hole=0.0003, windows='solid', coll=coll, mat=steel, bevel_w=0.00007)
    cw.location = (-0.0028, 0.01311, 0.0085)
    gears.append((cw, 24, 0.025, -1, 0.0))
    click = extrude_poly(name + 'Click', [(-0.0150, 0.0040), (-0.0138, 0.0046), (-0.0128, 0.0052), (-0.0127, 0.0058), (-0.0134, 0.0055),
                                          (-0.0146, 0.0050), (-0.0156, 0.0046)], 0.00045, coll, z0=0.0083)
    set_mat(click, steel); bevel(click, 0.00006, 2, 30)
    parts += [rat, cw, click]
    for (x, y) in ((-0.0085, 0.0098), (-0.0028, 0.01311)):
        s = cyl(name + 'RatScrew', 0.0011, 0.0004, loc=(x, y, 0.0090), segs=24, coll=coll, bev=0.00012)
        set_mat(s, blued)
        sl = box(name + 'RatSlot', (0.0021, 0.00025, 0.0002), loc=(x, y, 0.0092), rot=(0, 0, rng.uniform(0, 3.14)), coll=coll)
        set_mat(sl, dark)
        parts += [s, sl]
    cotes = mat_cotes(name + 'Cotes')
    # bridges with screws + jewels
    def bridge(nm, pts, z0, th=0.0011):
        br = extrude_poly(name + nm, pts, th, coll, z0=z0)
        set_mat(br, cotes); bevel(br, 0.00018, 2, 30)
        return br
    b1 = bridge('TrainBridge', [(-0.0118, -0.0140), (0.0010, -0.0178), (0.0128, -0.0098), (0.0130, -0.0064), (0.0090, -0.0062),
                                (0.0012, -0.0122), (-0.0085, -0.0096), (-0.0118, -0.0108)], 0.0068)
    b2 = bridge('BarrelBridge', [(-0.019, 0.004), (-0.012, 0.0005), (-0.002, 0.004), (0.001, 0.012), (-0.006, 0.019), (-0.015, 0.016)], 0.0071)
    parts += [b1, b2]
    jewel_pos = [(0.0012, -0.0150, 0.0079), (-0.0085, -0.0122, 0.0079), (-0.0085, 0.0098, 0.0082), (0.0112, 0.0098, 0.0081)]
    for (x, y, z) in jewel_pos:
        chaton = cyl(name + 'Chaton', 0.0011, 0.0004, loc=(x, y, z), segs=32, coll=coll, bev=0.00008)
        set_mat(chaton, gold)
        j = cyl(name + 'Jewel', 0.0006, 0.0003, loc=(x, y, z + 0.00025), segs=24, coll=coll, bev=0.0001)
        set_mat(j, ruby)
        parts += [chaton, j]
    screw_pos = [(0.0058, -0.0118, 0.0079), (-0.0040, -0.0132, 0.0079), (0.0122, -0.0076, 0.0079), (-0.0108, -0.0124, 0.0079), (-0.016, 0.0085, 0.0082), (-0.004, 0.0165, 0.0082), (-0.0005, 0.006, 0.0082)]
    for (x, y, z) in screw_pos:
        s = cyl(name + 'Screw', 0.00075, 0.0005, loc=(x, y, z), segs=24, coll=coll, bev=0.0001)
        set_mat(s, blued)
        sl = box(name + 'Slot', (0.0016, 0.00022, 0.00025), loc=(x, y, z + 0.00018), rot=(0, 0, rng.uniform(0, 3.14)), coll=coll)
        set_mat(sl, dark)
        parts += [s, sl]
    # balance wheel (right side, 3 o'clock) + cock
    bx, by = 0.0112, 0.0098
    bal = empty(name + 'BalanceE', loc=(bx, by, 0.0062), coll=coll)
    rim = prim('torus', name + 'BalRim', coll=coll, R=0.0060, r=0.00032, su=96, sv=8)
    set_mat(rim, brass); rim.parent = bal; rim.location = (0, 0, 0)
    for k in range(3):
        a = k * 2 * math.pi / 3
        arm = box(name + 'BalArm', (0.0118, 0.0006, 0.0004), loc=(0.0059 * math.cos(a) * 0.5, 0.0059 * math.sin(a) * 0.5, 0), rot=(0, 0, a), coll=coll)
        set_mat(arm, brass); arm.parent = bal
    for k in range(16):
        a = k * 2 * math.pi / 16
        sc_ = cyl(name + 'BalScrew', 0.00028, 0.0006, loc=(0.0066 * math.cos(a), 0.0066 * math.sin(a), 0), rot=(0, math.pi / 2, a), segs=12, coll=coll)
        set_mat(sc_, gold); sc_.parent = bal
    # hairspring (flat spiral)
    bm = bmesh.new()
    prev = None
    turns = 11
    nseg = 900
    pts = []
    for i in range(nseg):
        t = i / (nseg - 1)
        a = t * turns * 2 * math.pi
        rr = 0.0008 + 0.0042 * t
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) or 1e-9
        nx_, ny_ = -dy / L * 0.00006, dx / L * 0.00006
        v = [bm.verts.new((x0 + nx_, y0 + ny_, -0.0008)), bm.verts.new((x0 - nx_, y0 - ny_, -0.0008)),
             bm.verts.new((x1 - nx_, y1 - ny_, -0.0008)), bm.verts.new((x1 + nx_, y1 + ny_, -0.0008))]
        bm.faces.new(v)
        v2 = [bm.verts.new((p.co.x, p.co.y, -0.0006)) for p in v]
        bm.faces.new(v2[::-1])
    hs = from_bmesh(name + 'Hairspring', bm, coll)
    set_mat(hs, blued); hs.parent = bal
    cock = bridge('Cock', [(bx - 0.003, by + 0.0035), (bx + 0.0025, by + 0.0015), (bx + 0.012, by + 0.004), (bx + 0.012, by - 0.002), (bx + 0.003, by - 0.003), (bx - 0.003, by - 0.0015)], 0.0074)
    parts.append(cock)
    # escape fork (pallet) between escape wheel and balance
    fork = extrude_poly(name + 'Pallet', [(-0.0085 + 0.003, -0.0122 + 0.0038), (0.0045, 0.0045), (0.0052, 0.0038), (-0.0085 + 0.0034, -0.0122 + 0.0031)], 0.0004, coll, z0=0.0067)
    set_mat(fork, steel); parts.append(fork)
    # skeleton chapter ring (dial) + indices
    dial = revolve(name + 'Dial', [(0.0172, 0.0086), (0.0213, 0.0086), (0.0213, 0.0090), (0.0172, 0.0090), (0.0172, 0.0086)], 128, coll)
    set_mat(dial, enamel); parts.append(dial)
    bms = {True: bmesh.new(), False: bmesh.new()}
    for k in range(60):
        a = math.pi / 2 - k * 2 * math.pi / 60
        big = (k % 5 == 0)
        ln = 0.0026 if big else 0.0011
        rr = 0.0205 - ln / 2
        m = Matrix.Translation((rr * math.cos(a), rr * math.sin(a), 0.00905 + (0.00004 if big else 0))) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Diagonal((ln, 0.00045 if big else 0.00016, 0.00008 if not big else 0.00022, 1))
        bmesh.ops.create_cube(bms[big], size=1.0, matrix=m)
    for big, bmi in bms.items():
        t_ = from_bmesh(name + ('IdxH' if big else 'IdxM'), bmi, coll, smooth=False)
        set_mat(t_, gold if big else dark); parts.append(t_)
    # hands at 10:08 (blued steel)
    hands = empty(name + 'Hands', loc=(0, 0, 0.0094), coll=coll)
    hh = extrude_poly(name + 'HourHand', [(0, -0.0006), (0.0095, -0.0004), (0.0115, 0.0), (0.0095, 0.0004), (0, 0.0006), (-0.0025, 0.0008), (-0.0025, -0.0008)], 0.00012, coll)
    mh = extrude_poly(name + 'MinHand', [(0, -0.0004), (0.0170, -0.0002), (0.0185, 0.0), (0.0170, 0.0002), (0, 0.0004), (-0.0035, 0.0006), (-0.0035, -0.0006)], 0.00012, coll, z0=0.0002)
    # v5: 10:50 instead of 10:08 - the 5C dive lands just above the centre wheel at ~70 deg looking toward -39 deg,
    # where the old minute hand passed 0.7 mm under the lens (a giant blurred blue blob)
    hh.rotation_euler = (0, 0, math.radians(125)); mh.rotation_euler = (0, 0, math.radians(150))
    for h_ in (hh, mh):
        set_mat(h_, blued); h_.parent = hands
    cap = cyl(name + 'HandCap', 0.0009, 0.0006, loc=(0, 0, 0.0005), segs=24, coll=coll, bev=0.0001)
    set_mat(cap, blued); cap.parent = hands
    # crystal (thin dome)
    cr = revolve(name + 'Crystal', [(0.0, 0.0124), (0.008, 0.0121), (0.015, 0.0113), (0.0222, 0.0099), (0.0221, 0.0097), (0.015, 0.0111), (0.008, 0.0119), (0.0, 0.0122)], 96, coll, sharp=80)
    set_mat(cr, crystal); parts.append(cr)
    cr.visible_shadow = False
    # pendant, crown, bow at 12
    pend = cyl(name + 'Pendant', 0.0028, 0.005, loc=(0, Rc + 0.002, 0.0052), rot=(math.pi / 2, 0, 0), segs=32, coll=coll, bev=0.0003)
    crown = cyl(name + 'Crown', 0.0036, 0.0042, loc=(0, Rc + 0.0058, 0.0052), rot=(math.pi / 2, 0, 0), segs=48, coll=coll, bev=0.0004)
    bm = bmesh.new()
    for k in range(40):
        a = 2 * math.pi * k / 40
        m = Matrix.Translation((0.0036 * math.cos(a), Rc + 0.0058, 0.0052 + 0.0036 * math.sin(a))) @ Matrix.Rotation(-a, 4, 'Y') @ Matrix.Diagonal((0.00035, 0.0042, 0.0005, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    kn = from_bmesh(name + 'CrownKnurl', bm, coll, smooth=False)
    set_mat(kn, gold); parts.append(kn)
    bow = prim('torus', name + 'Bow', loc=(0, Rc + 0.0138, 0.0016), rot=(math.radians(12), 0, 0), coll=coll, R=0.0075, r=0.0009, su=64, sv=12)
    for p in (pend, crown, bow):
        set_mat(p, gold); parts.append(p)
    # hinged hunter lid (hinge at 9 o'clock, opened ~108 deg)
    lid_h = empty(name + 'LidHinge', loc=(-Rc - 0.0006, 0, 0.0075), coll=coll)
    lid = revolve(name + 'Lid', [(0.0, 0.0), (0.0235, 0.0), (0.0248, 0.0008), (0.0244, 0.0018), (0.022, 0.0026), (0.0, 0.0032)], 128, coll)
    set_mat(lid, gold)
    lid.parent = lid_h
    lid.location = (Rc + 0.0006, 0, 0)
    lid_h.rotation_euler = (0, math.radians(-132), 0)     # v13: laid back further (was 104: a disc facing 5B = 'golf ball')
    hinge = cyl(name + 'Hinge', 0.0012, 0.012, loc=(-Rc - 0.0006, 0, 0.0075), rot=(math.pi / 2, 0, 0), segs=24, coll=coll, bev=0.0002)
    set_mat(hinge, gold)
    lid_p = empty(name + 'LidPivot', coll=coll)
    lid_h.parent = lid_p; hinge.parent = lid_p
    lid_p.rotation_euler = (0, 0, math.radians(lid_angle - 180))
    lid_in = revolve(name + 'LidInner', [(0.0, -0.00005), (0.0232, -0.00005)], 128, coll)
    set_mat(lid_in, mat_guilloche(name + 'Guilloche')); lid_in.parent = lid
    for p in parts + [lid_p, hands, bal]:
        if p.parent is None:
            p.parent = root
    return root, gears, bal


def make_chain(name, coll, pts, mat, link_R=0.0019, link_r=0.00045):
    src = prim('torus', name + 'LinkSrc', coll=coll, R=link_R, r=link_r, su=20, sv=8)
    src.scale = (1.35, 1.0, 1.0)
    set_mat(src, mat)
    objs = [src]
    # resample polyline at link spacing
    P = [Vector(p) for p in pts]
    step = link_R * 1.75
    out = []
    acc = 0.0
    for a, b in zip(P[:-1], P[1:]):
        L = (b - a).length
        s = 0.0 if not out else step - acc
        while s < L:
            out.append((a + (b - a) * (s / L), (b - a).normalized()))
            s += step
        acc = L - (s - step)
    for i, (p, d) in enumerate(out):
        o = src if i == 0 else bpy.data.objects.new(name + f'L{i}', src.data)
        if i:
            link(o, coll)
            o.scale = (1.35, 1.0, 1.0)
        yaw = math.atan2(d.y, d.x)
        o.location = p + Vector((0, 0, link_R * 0.75 if i % 2 else 0.0))
        o.rotation_euler = (math.pi / 2 if i % 2 else 0.0, 0, yaw)
        objs.append(o)
    return objs


def scatter_mesh(name, coll, n, region, size, z, mat, seed=1, kind='crumb', avoid=None):
    """One mesh with n small blobs (crumbs/dust/filings). region=(x0,x1,y0,y1) or callable."""
    rng = random.Random(seed)
    bm = bmesh.new()
    for i in range(n):
        if callable(region):
            x, y = region(rng)
        else:
            x, y = rng.uniform(region[0], region[1]), rng.uniform(region[2], region[3])
        s = rng.uniform(size[0], size[1])
        zz = z(x, y) if callable(z) else z
        m = Matrix.Translation((x, y, zz + s * 0.3)) @ Euler((rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))).to_matrix().to_4x4() \
            @ Matrix.Diagonal((s * rng.uniform(0.7, 1.6), s * rng.uniform(0.5, 1.0), s * rng.uniform(0.4, 0.8), 1))
        if kind == 'crumb':
            bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0, matrix=m)
        else:
            bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    return from_bmesh(name, bm, coll, smooth=(kind == 'crumb'))


def make_shaving(name, coll, paint, cedar, seed=0):
    """Curly pencil-sharpener shaving: conical spiral ribbon, painted scalloped outer rim."""
    rr = random.Random(seed)
    bm = bmesh.new()
    n = 70
    turns = rr.uniform(0.8, 1.3)
    rows = []
    for i in range(n + 1):
        t = i / n
        a = t * turns * 2 * math.pi
        r_in = 0.0006 + 0.0012 * t
        r_out = 0.0042 + 0.0035 * t + 0.0004 * math.sin(a * 6)
        z_in = 0.0011 + 0.0007 * t
        z_out = 0.0004 * (1 - t) + 0.0001
        row = []
        # v13: wavy (ruffled) cross-section + a wider painted rim band (was a flat salmon disc = "ham slice")
        for k, f in enumerate((0.0, 0.35, 0.62, 0.76, 0.80, 1.0)):
            r = r_in + (r_out - r_in) * f
            z = z_in + (z_out - z_in) * f + 0.0003 * math.sin(t * 9 + f * 3) + 0.00035 * math.sin(a * 14 + f * 2) * f
            row.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rows.append(row)
    for i in range(n):
        for k in range(5):
            f = bm.faces.new((rows[i][k], rows[i + 1][k], rows[i + 1][k + 1], rows[i][k + 1]))
            f.material_index = 1 if k >= 3 else 0
    o = from_bmesh(name, bm, coll, smooth=True)
    s = o.modifiers.new('Solid', 'SOLIDIFY'); s.thickness = 0.00015
    o.data.materials.append(cedar); o.data.materials.append(paint)
    return o


def motes(name, coll, n, box_, size, mat, seed=3):
    rng = random.Random(seed)
    bm = bmesh.new()
    for i in range(n):
        x = rng.uniform(box_[0], box_[1]); y = rng.uniform(box_[2], box_[3]); z = rng.uniform(box_[4], box_[5])
        s = rng.uniform(size[0], size[1]) * (1 if rng.random() > 0.08 else 3)
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=s, matrix=Matrix.Translation((x, y, z)))
    o = from_bmesh(name, bm, coll)
    set_mat(o, mat)
    return o
