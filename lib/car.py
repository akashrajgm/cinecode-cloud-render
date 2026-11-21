"""ESCAPEMENT hero car (original design): low, wide mid-engine hypercar.

    import car
    c = car.build_car(coll=None, name='Car')
    c['root']          empty at ground level, centred between the axles, forward +Y, up +Z
    c['wheels']        [FL, FR, RL, RR] spin empties; rotate about local X, positive = forward roll
    c['wheel_radius']  0.35
    c['parts']         name -> object for every separately animatable part (exploded view).
                       'sprung' is the body rig empty (animate it for squat / rock / roll);
                       'corner_FL'.. are the unsprung hub empties (wheel + brake + caliper).
                       Every body piece has its origin at the car origin, so a part's "home"
                       is location (0,0,0) / rotation (0,0,0) in its parent frame.
    c['mats']          'rear_light', 'front_light' (emission; plus 'paint', 'glass', ...)
    c['body']          main body shell object
    car.set_light(c, 'rear'|'front', strength, frame)   keyframes emission strength
    car.set_sweep(c, 'rear', value, frame)               0..1 centre-out ignition sweep of the rear bar

Import-safe: no scene reset, no rendering. Units metres. Wheelbase 2.70, length ~4.5, width ~2.0,
height ~1.1, wheel radius 0.35.
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import common as C

WB = 2.70          # wheelbase
YF, YR = WB / 2, -WB / 2
WR = 0.35          # wheel radius
TRACK_F, TRACK_R = 0.835, 0.855

# ----------------------------------------------------------------------------- materials

def _paint():
    b = C.NB('car_paint')
    v = b.coord('Object', 1.0)
    fl = b.voronoi(v, 1400.0)
    big = b.noise(v, 1.2, 4, 0.5)
    base = b.mix((0.018, 0.020, 0.023), (0.034, 0.037, 0.041), big.outputs['Fac'])
    # one teal accent stripe, off-centre over the top of the car (object coords = car frame)
    tc = b.n('ShaderNodeTexCoord')
    sep = b.n('ShaderNodeSeparateXYZ')
    b.link(tc.outputs['Object'], sep.inputs[0])
    dx = b.math('ABSOLUTE', b.math('SUBTRACT', sep.outputs['X'], 0.23))
    stripe = b.maprange(dx, 0.075, 0.068, 0.0, 1.0)      # r3: wider teal livery stripe (was 7 cm)
    stripe = b.math('MULTIPLY', stripe, b.maprange(sep.outputs['Z'], 0.50, 0.56, 0.0, 1.0))
    pin = b.maprange(b.math('ABSOLUTE', b.math('SUBTRACT', dx, 0.088)), 0.0045, 0.0025, 0.0, 1.0)
    pin = b.math('MULTIPLY', pin, b.maprange(sep.outputs['Z'], 0.50, 0.56, 0.0, 1.0))
    col = b.mix(base, (0.0, 0.42, 0.40), stripe)
    col = b.mix(col, (0.0, 0.42, 0.40), pin)
    b.set('Base Color', col)
    b.set('Metallic', b.maprange(stripe, 0, 1, 0.55, 0.2))
    b.set('Roughness', b.maprange(big.outputs['Fac'], 0.3, 0.7, 0.30, 0.40))
    b.set('Coat Weight', 1.0)
    b.set('Coat Roughness', b.maprange(big.outputs['Fac'], 0.3, 0.7, 0.03, 0.09))
    b.set('Normal', b.bump(fl.outputs['Distance'], 0.08, 0.0005))
    return b.mat


def _carbon(name='car_carbon', gloss=True):
    b = C.NB(name)
    tc = b.n('ShaderNodeTexCoord')
    mp = b.n('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (90, 90, 90)
    b.link(tc.outputs['Object'], mp.inputs['Vector'])
    ch = b.n('ShaderNodeTexChecker')
    ch.inputs['Scale'].default_value = 1.0
    ch.inputs['Color1'].default_value = (0.022, 0.023, 0.026, 1)
    ch.inputs['Color2'].default_value = (0.006, 0.006, 0.007, 1)
    b.link(mp.outputs['Vector'], ch.inputs['Vector'])
    w = b.n('ShaderNodeTexWave')
    w.inputs['Scale'].default_value = 180.0
    w.inputs['Distortion'].default_value = 0.0
    b.link(tc.outputs['Object'], w.inputs['Vector'])
    b.set('Base Color', ch.outputs['Color'])
    b.set('Metallic', 0.3)
    b.set('Roughness', b.maprange(ch.outputs['Fac'], 0, 1, 0.22, 0.38))
    if gloss:
        b.set('Coat Weight', 1.0)
        b.set('Coat Roughness', 0.04)
    b.set('Normal', b.bump(w.outputs['Fac'], 0.05, 0.0005))
    try:
        b.set('Anisotropic', 0.6)
    except Exception:
        pass
    return b.mat


def _glass():
    b = C.NB('car_glass')
    b.set('Base Color', (0.012, 0.016, 0.02)).set('Roughness', 0.02).set('Metallic', 0.0)
    b.set('Specular IOR Level', 0.9)
    b.set('Coat Weight', 1.0).set('Coat Roughness', 0.0)
    return b.mat


def _light_mat(name, color, strength, sweep=False, glass=(0.12, 0.01, 0.01), led=None):
    """Emission material. Emission Strength is the animatable master; for sweep=True a value node
    'Sweep' (0..1) masks the emission from the car centre line outwards (object X)."""
    b = C.NB(name)
    b.set('Base Color', glass).set('Roughness', 0.08).set('Coat Weight', 1.0).set('Coat Roughness', 0.0)
    b.set('Emission Color', color)
    b.set('Emission Strength', strength)
    if led and not sweep:
        # r3: individual LED emitters behind the lens (pitch along object `led[0]`, frequency led[1])
        tc0 = b.n('ShaderNodeTexCoord')
        sp0 = b.n('ShaderNodeSeparateXYZ'); b.link(tc0.outputs['Object'], sp0.inputs[0])
        ax = sp0.outputs[led[0]]
        dots = b.maprange(b.math('SINE', b.math('MULTIPLY', ax, led[1])), -0.2, 0.6, 0.30, 1.0)
        b.set('Emission Color', b.mix((0, 0, 0), color, dots))
    if sweep:
        tc = b.n('ShaderNodeTexCoord')
        sep = b.n('ShaderNodeSeparateXYZ')
        b.link(tc.outputs['Object'], sep.inputs[0])
        sv = b.n('ShaderNodeValue')
        sv.name = sv.label = 'Sweep'
        sv.outputs[0].default_value = 1.0
        ax = b.math('ABSOLUTE', sep.outputs['X'])
        edge = b.math('MULTIPLY', sv.outputs[0], 1.05)
        # mask = 1 where |x| < sweep*1.05 (soft 8 cm leading edge, hot leading edge)
        m = b.math('SUBTRACT', edge, ax)
        mask = b.maprange(m, -0.01, 0.07, 0.0, 1.0)
        hot = b.maprange(m, 0.0, 0.10, 3.0, 1.0)
        em = b.mix((0, 0, 0), color, mask)
        em2 = b.n('ShaderNodeMix'); em2.data_type = 'RGBA'; em2.blend_type = 'MULTIPLY'
        em2.inputs['Factor'].default_value = 1.0
        b.link(em, em2.inputs[6])
        cr = b.n('ShaderNodeCombineXYZ')
        b.link(hot, cr.inputs[0]); b.link(hot, cr.inputs[1]); b.link(hot, cr.inputs[2])
        b.link(cr.outputs[0], em2.inputs[7])
        # LED segmentation: fine pitch along the bar (reads in close-ups, invisible in wides)
        seg = b.maprange(b.math('SINE', b.math('MULTIPLY', sep.outputs['X'], 520.0)), -0.35, 0.35, 0.45, 1.0)
        em3 = b.mix(em2.outputs[2], (0, 0, 0), b.math('SUBTRACT', 1.0, seg))
        b.set('Emission Color', em3)
    return b.mat


def _rim_mat():
    b = C.NB('car_rim')
    v = b.coord('Object', 1.0)
    n = b.noise(v, 30, 4, 0.6)
    b.set('Base Color', b.mix((0.035, 0.036, 0.04), (0.06, 0.062, 0.068), n.outputs['Fac']))
    b.set('Metallic', 1.0).set('Roughness', b.maprange(n.outputs['Fac'], 0.3, 0.7, 0.28, 0.42))
    b.set('Coat Weight', 0.5).set('Coat Roughness', 0.1)
    return b.mat


def _machined():
    b = C.NB('car_machined')
    tc = b.n('ShaderNodeTexCoord')
    # concentric lathe marks around the wheel axis (local X)
    sep = b.n('ShaderNodeSeparateXYZ')
    b.link(tc.outputs['Object'], sep.inputs[0])
    r = b.math('SQRT', b.math('ADD', b.math('MULTIPLY', sep.outputs['Y'], sep.outputs['Y']),
                               b.math('MULTIPLY', sep.outputs['Z'], sep.outputs['Z'])))
    rings = b.math('SINE', b.math('MULTIPLY', r, 3000.0))
    b.set('Base Color', (0.55, 0.56, 0.58)).set('Metallic', 1.0)
    b.set('Roughness', b.maprange(rings, -1, 1, 0.12, 0.2))
    b.set('Normal', b.bump(rings, 0.03, 0.0003))
    try:
        b.set('Anisotropic', 0.7)
    except Exception:
        pass
    return b.mat


def _disc_mat():
    """Cast-iron brake disc with cross-drilled holes (polar voronoi) and heat tint."""
    b = C.NB('car_disc')
    tc = b.n('ShaderNodeTexCoord')
    sep = b.n('ShaderNodeSeparateXYZ')
    b.link(tc.outputs['Object'], sep.inputs[0])
    ang = b.n('ShaderNodeMath'); ang.operation = 'ARCTAN2'
    b.link(sep.outputs['Z'], ang.inputs[0]); b.link(sep.outputs['Y'], ang.inputs[1])
    r = b.math('SQRT', b.math('ADD', b.math('MULTIPLY', sep.outputs['Y'], sep.outputs['Y']),
                               b.math('MULTIPLY', sep.outputs['Z'], sep.outputs['Z'])))
    cx = b.math('MULTIPLY', ang.outputs[0], 30.0 / (2 * math.pi))
    cy = b.math('MULTIPLY', b.math('SUBTRACT', r, 0.112), 1.0 / 0.024)
    cxy = b.n('ShaderNodeCombineXYZ')
    b.link(b.math('ADD', cx, b.math('MULTIPLY', b.math('FLOOR', cy), 0.37)), cxy.inputs[0])
    b.link(cy, cxy.inputs[1])
    vor = b.n('ShaderNodeTexVoronoi'); vor.voronoi_dimensions = '2D'
    vor.inputs['Scale'].default_value = 1.0; vor.inputs['Randomness'].default_value = 0.0
    b.link(cxy.outputs[0], vor.inputs['Vector'])
    band = b.math('MULTIPLY', b.maprange(r, 0.112, 0.118, 0, 1), b.maprange(r, 0.182, 0.176, 0, 1))
    hole = b.math('MULTIPLY', b.maprange(vor.outputs['Distance'], 0.17, 0.14, 0, 1), band)
    grooves = b.math('SINE', b.math('MULTIPLY', r, 2500.0))
    col = b.mix((0.30, 0.30, 0.31), (0.12, 0.10, 0.10), b.maprange(r, 0.12, 0.19, 0, 1))
    col = b.mix(col, (0.0, 0.0, 0.0), hole)
    b.set('Base Color', col).set('Metallic', b.maprange(hole, 0, 1, 1.0, 0.0))
    b.set('Roughness', b.maprange(grooves, -1, 1, 0.22, 0.4))
    b.set('Normal', b.bump(b.math('ADD', b.math('MULTIPLY', grooves, 0.2), b.math('MULTIPLY', hole, -1.0)), 0.3, 0.003))
    return b.mat


def _tire_mat():
    b = C.NB('car_tire')
    tc = b.n('ShaderNodeTexCoord')
    sep = b.n('ShaderNodeSeparateXYZ')
    b.link(tc.outputs['Object'], sep.inputs[0])
    r = b.math('SQRT', b.math('ADD', b.math('MULTIPLY', sep.outputs['Y'], sep.outputs['Y']),
                               b.math('MULTIPLY', sep.outputs['Z'], sep.outputs['Z'])))
    ang = b.n('ShaderNodeMath'); ang.operation = 'ARCTAN2'
    b.link(sep.outputs['Z'], ang.inputs[0]); b.link(sep.outputs['Y'], ang.inputs[1])
    # sidewall: fine radial ribs + a raised "lettering" band (blocky noise) on the sidewall
    ribs = b.math('SINE', b.math('MULTIPLY', r, 1400.0))
    cxy = b.n('ShaderNodeCombineXYZ')
    b.link(b.math('MULTIPLY', ang.outputs[0], 40.0), cxy.inputs[0]); b.link(b.math('MULTIPLY', r, 300.0), cxy.inputs[1])
    vor = b.n('ShaderNodeTexVoronoi'); vor.voronoi_dimensions = '2D'; vor.distance = 'CHEBYCHEV'
    vor.inputs['Scale'].default_value = 1.0
    b.link(cxy.outputs[0], vor.inputs['Vector'])
    band = b.math('MULTIPLY', b.maprange(r, 0.288, 0.292, 0, 1), b.maprange(r, 0.312, 0.308, 0, 1))
    letters = b.math('MULTIPLY', band, b.math('GREATER_THAN', vor.outputs['Distance'], 0.32))
    wear = b.noise(b.coord('Object', 1.0), 60, 3, 0.6)
    b.set('Base Color', b.mix((0.014, 0.014, 0.015), (0.05, 0.05, 0.052), letters))
    b.set('Roughness', b.maprange(wear.outputs['Fac'], 0.3, 0.7, 0.62, 0.85))
    b.set('Normal', b.bump(b.math('ADD', b.math('MULTIPLY', ribs, 0.15), letters), 0.25, 0.001))
    return b.mat


def materials():
    m = {}
    m['paint'] = _paint()
    m['carbon'] = _carbon()
    m['carbon_matte'] = _carbon('car_carbon_matte', gloss=False)
    m['glass'] = _glass()
    m['well'] = C.mat_principled('car_well', (0.008, 0.008, 0.009), 0.8)
    m['rim'] = _rim_mat()
    m['machined'] = _machined()
    m['brass'] = C.mat_brass('car_brass', scale=20.0)
    m['disc'] = _disc_mat()
    m['tire'] = _tire_mat()
    m['caliper'] = C.mat_principled('car_caliper', (0.0, 0.33, 0.31), 0.28, 0.0, coat=1.0)
    m['steel'] = C.mat_metal('car_steel', base=(0.5, 0.5, 0.52), rough=(0.15, 0.35), scale=6.0)
    m['titanium'] = C.mat_metal('car_titanium', base=(0.42, 0.38, 0.36), rough=(0.18, 0.32), scale=8.0)
    m['black'] = C.mat_principled('car_black', (0.006, 0.006, 0.007), 0.45)
    m['grille'] = _grille_mat()
    m['mirror'] = C.mat_principled('car_mirror', (0.9, 0.92, 0.95), 0.0, 1.0)
    m['rear_light'] = _light_mat('car_rear_light', (1.0, 0.015, 0.008), 60.0, sweep=True)
    m['front_light'] = _light_mat('car_front_light', (0.62, 0.92, 1.0), 40.0, glass=(0.05, 0.06, 0.07), led=('Y', 620.0))
    m['engine'] = C.mat_metal('car_engine', base=(0.13, 0.13, 0.14), rough=(0.3, 0.55), scale=5.0, bump=0.1)
    # r3: teal aero livery (splitter lip, canards, wing endplates, mirror caps)
    m['accent'] = C.mat_principled('car_accent', (0.0, 0.40, 0.38), 0.24, 0.35, coat=1.0)
    # recessed light channel: matte black bezel
    m['bezel'] = C.mat_principled('car_bezel', (0.004, 0.004, 0.0045), 0.55)
    return m


def _grille_mat():
    """Dark hex mesh grille (procedural holes)."""
    b = C.NB('car_grille')
    v = b.coord('Object', 1.0)
    vor = b.voronoi(v, 140.0, rand=0.0)
    holes = b.maprange(vor.outputs['Distance'], 0.30, 0.38, 1.0, 0.0)
    b.set('Base Color', b.mix((0.002, 0.002, 0.002), (0.04, 0.04, 0.045), holes))
    b.set('Metallic', b.maprange(holes, 0, 1, 0, 0.8))
    b.set('Roughness', 0.35)
    b.set('Normal', b.bump(holes, 0.6, 0.002))
    return b.mat

# ----------------------------------------------------------------------------- body shell

# station table: y, zb, w, zw, ws, zs, wf, zf, wc, zc, wr, zr, zt
STATIONS = [
    (-2.25, 0.34, 0.90, 0.55, 0.88, 0.73, 0.80, 0.79, 0.55, 0.80, 0.30, 0.81, 0.81),
    (-2.08, 0.22, 0.96, 0.52, 0.94, 0.77, 0.86, 0.85, 0.55, 0.81, 0.30, 0.83, 0.83),
    (-1.75, 0.13, 1.00, 0.50, 0.98, 0.80, 0.89, 0.89, 0.50, 0.83, 0.28, 0.86, 0.87),
    (-1.35, 0.11, 1.00, 0.50, 0.985, 0.81, 0.89, 0.91, 0.48, 0.84, 0.26, 0.88, 0.89),
    (-1.00, 0.10, 0.99, 0.48, 0.96, 0.79, 0.87, 0.87, 0.46, 0.86, 0.26, 0.93, 0.94),
    (-0.65, 0.10, 0.96, 0.46, 0.93, 0.76, 0.81, 0.80, 0.56, 0.84, 0.34, 1.02, 1.03),
    (-0.30, 0.10, 0.95, 0.45, 0.92, 0.74, 0.78, 0.78, 0.62, 0.82, 0.42, 1.08, 1.10),
    (0.10, 0.10, 0.95, 0.45, 0.92, 0.73, 0.78, 0.77, 0.63, 0.80, 0.43, 1.07, 1.09),
    (0.50, 0.10, 0.95, 0.44, 0.92, 0.72, 0.80, 0.76, 0.62, 0.77, 0.45, 0.98, 1.00),
    (0.85, 0.10, 0.96, 0.44, 0.93, 0.72, 0.83, 0.77, 0.58, 0.74, 0.45, 0.82, 0.83),
    (1.15, 0.11, 0.97, 0.44, 0.95, 0.73, 0.85, 0.80, 0.55, 0.67, 0.30, 0.635, 0.635),
    (1.35, 0.11, 0.975, 0.43, 0.955, 0.73, 0.85, 0.81, 0.55, 0.65, 0.30, 0.615, 0.615),
    (1.60, 0.12, 0.955, 0.40, 0.935, 0.67, 0.81, 0.745, 0.52, 0.58, 0.30, 0.55, 0.55),
    (1.90, 0.13, 0.90, 0.34, 0.88, 0.52, 0.76, 0.56, 0.48, 0.46, 0.30, 0.44, 0.44),
    (2.12, 0.14, 0.82, 0.27, 0.80, 0.37, 0.70, 0.385, 0.44, 0.335, 0.28, 0.32, 0.32),
    (2.25, 0.15, 0.72, 0.22, 0.70, 0.28, 0.62, 0.285, 0.40, 0.265, 0.25, 0.255, 0.255),
    (2.31, 0.165, 0.62, 0.185, 0.60, 0.205, 0.54, 0.21, 0.36, 0.21, 0.22, 0.21, 0.21),
]
CANOPY_Y = (-0.66, 0.86)


def _profile(st):
    y, zb, w, zw, ws, zs, wf, zf, wc, zc, wr, zr, zt = st
    # sculpted side intake ahead of the rear wheel: pull the mid-side inwards
    k = math.exp(-((y + 0.72) / 0.26) ** 2)
    scoop = 0.11 * k
    return [(0.0, zb), (w - 0.10, zb), (w - 0.025, zb + 0.06), (w - scoop, zw), (ws - scoop * 0.3, zs),
            (wf, zf), (wc, zc), (wr, zr), (0.0, zt)]


def _body_cage():
    """Closed quad cage: ring per station (bottom centre -> right side -> top centre -> left side)."""
    bm = bmesh.new()
    cl = bm.edges.layers.float.get('crease_edge') or bm.edges.layers.float.new('crease_edge')
    rings = []
    K = 9
    for st in STATIONS:
        p = _profile(st)
        y = st[0]
        right = [Vector((x, y, z)) for x, z in p]                     # 0..8
        left = [Vector((-x, y, z)) for x, z in reversed(p[1:-1])]      # 7..1 mirrored
        ring = [bm.verts.new(v) for v in right + left]
        rings.append(ring)
    n = len(rings[0])
    canopy_faces = []
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        yc = (STATIONS[i][0] + STATIONS[i + 1][0]) / 2
        for j in range(n):
            j2 = (j + 1) % n
            f = bm.faces.new((a[j], a[j2], b[j2], b[j]))
            # canopy: profile segments 6-7, 7-8 (right) and mirrored (left)
            seg = j  # right side segs 0..7 ; left side j>=8
            is_can = (seg in (6, 7)) or (seg in (8, 9))
            if is_can and CANOPY_Y[0] < yc < CANOPY_Y[1]:
                f.material_index = 1
                canopy_faces.append(f)
    # end caps
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.edges.ensure_lookup_table()
    # creases: longitudinal character lines + cap rims
    crease_idx = {1: 1.0, n - 1: 1.0, 4: 0.75, n - 4: 0.75, 6: 0.5, n - 6: 0.5}
    for i in range(len(rings) - 1):
        for j, c in crease_idx.items():
            e = bm.edges.get((rings[i][j], rings[i + 1][j]))
            if e:
                e[cl] = c
    for ring, c in ((rings[0], 0.85), (rings[-1], 1.0)):
        for j in range(n):
            e = bm.edges.get((ring[j], ring[(j + 1) % n]))
            if e:
                e[cl] = c
    return bm


def _cutter(name, y, coll, r=WR + 0.055, mat=None):
    o = C.prim('cylinder', name, loc=(0, y, WR), rot=(0, math.pi / 2, 0), coll=coll, r=r, depth=3.0, segments=64)
    # keep the cutter out of the centre tub: two cylinders (left/right) via a box intersect is overkill;
    # instead cut the full width and rely on the hood/deck being higher than the cutter top.
    if mat:
        C.set_mat(o, mat)
    o.hide_render = True
    return o


def _cutters(coll, mats):
    cs = []
    for y in (YF, YR):
        for sx in (-1, 1):
            o = C.prim('cylinder', f'cut{y}{sx}', loc=(sx * 0.95, y, WR), rot=(0, math.pi / 2, 0), coll=coll,
                       r=WR + 0.04, depth=0.8, segments=64)
            C.set_mat(o, mats['well'])
            cs.append(o)
    return cs


def _split(bm, planes, gap=0.0035):
    """planes: list of (co, no) whose positive side is 'inside'. Returns (inside_bm, outside_bm).
    Faces in the 2*gap strip on a boundary are dropped -> real panel gaps."""
    for co, no in planes:
        for off in (-gap, gap):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=Vector(co) + Vector(no).normalized() * off,
                                   plane_no=no)
    ins, outs = [], []
    bm.faces.index_update()
    for f in bm.faces:
        c = f.calc_center_median()
        ds = [(c - Vector(co)).dot(Vector(no).normalized()) for co, no in planes]
        if all(d > gap for d in ds):
            ins.append(f.index)
        elif any(d < -gap for d in ds):
            outs.append(f.index)
    res = []
    for keep in (set(ins), set(outs)):
        b2 = bm.copy()
        b2.faces.ensure_lookup_table()
        b2.faces.index_update()
        kill = [f for f in b2.faces if f.index not in keep]
        bmesh.ops.delete(b2, geom=kill, context='FACES')
        res.append(b2)
    bm.free()
    return res


def _mesh_from_bm(name, bm, coll, mats_list, smooth=True, angle=40):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    C.link(o, coll)
    for m in mats_list:
        me.materials.append(m)
    if smooth:
        C.shade(o, angle)
    return o


def build_body(coll, mats, parent_obj):
    bm = _body_cage()
    tmp = _mesh_from_bm('body_tmp', bm, coll, [mats['paint'], mats['glass'], mats['well'], mats['carbon']], smooth=True)
    sub = tmp.modifiers.new('sub', 'SUBSURF'); sub.levels = 3; sub.render_levels = 3
    cs = _cutters(coll, mats)
    for c in cs:
        bo = tmp.modifiers.new('arch', 'BOOLEAN')
        bo.operation = 'DIFFERENCE'; bo.solver = 'EXACT'; bo.object = c
        try:
            bo.material_mode = 'TRANSFER'
        except Exception:
            pass
    bpy.context.view_layer.update()
    C.apply_mods(tmp)
    for c in cs:
        bpy.data.objects.remove(c, do_unlink=True)
    # material fix-up: lower skirts -> carbon, arch faces keep 'well'
    me = tmp.data
    slot = {m.name: i for i, m in enumerate(me.materials)}
    iw = slot.get('car_well', 2); ic = slot.get('car_carbon', 3); ig = slot.get('car_glass', 1)
    for p in me.polygons:
        c = p.center
        if p.material_index in (iw, ig):
            continue
        if c.z < 0.165 or (p.normal.z < -0.6 and c.z < 0.3):
            p.material_index = ic
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.objects.remove(tmp, do_unlink=True)
    # BVH for detail placement
    bvh = BVHTree.FromBMesh(bm)
    # matte black inner hull 14 mm under the skin: the real 7 mm panel gaps showed the bright studio
    # straight through the car (dotted white seams)
    hb = bm.copy()
    hb.normal_update()
    for v in hb.verts:
        v.co -= v.normal * 0.014
    for f in hb.faces:
        f.material_index = 0
    hull = _mesh_from_bm('inner_hull', hb, coll, [mats['well']], smooth=True)
    # canopy -> its own object
    bm.faces.ensure_lookup_table()
    bc = bm.copy()
    bmesh.ops.delete(bc, geom=[f for f in bc.faces if f.material_index != ig], context='FACES')
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == ig], context='FACES')
    pieces = {}
    mlist = [mats['paint'], mats['glass'], mats['well'], mats['carbon'], mats['carbon_matte'], mats['carbon_matte'], mats['carbon_matte']]
    can = _mesh_from_bm('canopy', bc, coll, mlist, angle=60)
    pieces['canopy'] = can
    # nose / tail / centre
    nose, rest = _split(bm, [((0, 1.0, 0), (0, 1, 0))])
    tail, centre = _split(rest, [((0, -0.95, 0), (0, -1, 0))])
    pieces['nose'] = _mesh_from_bm('nose', nose, coll, mlist)
    pieces['tail'] = _mesh_from_bm('tail', tail, coll, mlist)
    # doors
    for side, sx in (('L', -1), ('R', 1)):
        door, centre = _split(centre, [((sx * 0.66, 0, 0), (sx, 0, 0)), ((0, 0, 0.24), (0, 0, 1)),
                                       ((0, 0.86, 0), (0, -1, 0)), ((0, -0.70, 0), (0, 1, 0))])
        pieces['door_' + side] = _mesh_from_bm('door_' + side, door, coll, mlist)
    pieces['body'] = _mesh_from_bm('body', centre, coll, mlist)
    hull.parent = parent_obj
    for k, o in pieces.items():
        if k != 'canopy':
            so = o.modifiers.new('thick', 'SOLIDIFY'); so.thickness = 0.008; so.offset = -1.0
            # even offset exploded on bisect slivers at the nose tip (a 140 m spike through the floor)
            # inner skin + cut edges = dark matte 'well' (glossy carbon rims sparkled along every seam)
            so.use_even_offset = False; so.material_offset = 2; so.material_offset_rim = 2
            try:
                so.thickness_clamp = 1.0
            except Exception:
                pass
        else:
            so = o.modifiers.new('thick', 'SOLIDIFY'); so.thickness = 0.006; so.offset = -1.0
            try:
                so.thickness_clamp = 1.0
            except Exception:
                pass
        o.parent = parent_obj
    pieces['inner_hull'] = hull
    return pieces, bvh

# ----------------------------------------------------------------------------- helpers

def _revolve(name, prof, segs, coll, mats=None, mat_idx=None, smooth=True, angle=35):
    """prof: [(x, r), ...] revolved around the X axis (closed ring of segs)."""
    bm = bmesh.new()
    rings = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((x, r * ca, r * sa)) for x, r in prof])
    n = len(prof)
    for k in range(segs):
        A, B = rings[k], rings[(k + 1) % segs]
        for j in range(n - 1):
            f = bm.faces.new((A[j], A[j + 1], B[j + 1], B[j]))
            if mat_idx:
                f.material_index = mat_idx[j]
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _mesh_from_bm(name, bm, coll, mats or [], smooth=smooth, angle=angle)


def _loft(bm, sections, cap=True):
    """sections: list of lists of Vector (same length, closed loops)."""
    vs = [[bm.verts.new(p) for p in s] for s in sections]
    n = len(sections[0])
    for i in range(len(vs) - 1):
        for j in range(n):
            j2 = (j + 1) % n
            bm.faces.new((vs[i][j], vs[i][j2], vs[i + 1][j2], vs[i + 1][j]))
    if cap:
        bm.faces.new(list(reversed(vs[0])))
        bm.faces.new(vs[-1])
    return vs


def _box(bm, center, size, rot=None):
    m = Matrix.Translation(center)
    if rot is not None:
        m = m @ rot.to_4x4()
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=m @ Matrix.Diagonal((*size, 1.0)))
    return res['verts']


def _tube(bm, pts, r, segs=10):
    """Tube along a polyline."""
    secs = []
    for i, p in enumerate(pts):
        p = Vector(p)
        d = (Vector(pts[min(i + 1, len(pts) - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        u = d.cross(up).normalized(); v = d.cross(u).normalized()
        secs.append([p + (u * math.cos(2 * math.pi * k / segs) + v * math.sin(2 * math.pi * k / segs)) * r for k in range(segs)])
    _loft(bm, secs, cap=True)


def _obj(name, bm, coll, mat, par, bevel_w=0.0, angle=35):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _mesh_from_bm(name, bm, coll, [mat] if not isinstance(mat, (list, tuple)) else list(mat), angle=angle)
    if bevel_w:
        C.bevel(o, bevel_w, 2, 35)
    if par is not None:
        o.parent = par
    return o


def _surface_z(bvh, x, y, z0=2.0):
    hit = bvh.ray_cast(Vector((x, y, z0)), Vector((0, 0, -1)))
    return hit[0].z if hit[0] is not None else None

# ----------------------------------------------------------------------------- wheels

_WHEEL_MESHES = {}


def _wheel_meshes(coll, mats, rear=False):
    key = 'R' if rear else 'F'
    if key in _WHEEL_MESHES:
        return _WHEEL_MESHES[key]
    s = 1.12 if rear else 1.0   # tyre width scale
    out = {}
    # tyre: low profile, tread with 3 grooves, rounded shoulders, sidewall rib
    hw = 0.150 * s
    prof = [(-hw + 0.01, 0.252), (-hw - 0.004, 0.268), (-hw - 0.006, 0.30), (-hw - 0.004, 0.322), (-hw + 0.004, 0.338),
            (-hw + 0.018, 0.347), (-hw + 0.04, 0.35)]
    gx = [-0.5 * hw, 0.0, 0.5 * hw]
    tread = []
    for g in gx:
        tread += [(g - 0.012, 0.35), (g - 0.008, 0.341), (g + 0.008, 0.341), (g + 0.012, 0.35)]
    prof += tread
    prof += [(hw - 0.04, 0.35), (hw - 0.018, 0.347), (hw - 0.004, 0.338), (hw + 0.004, 0.322), (hw + 0.006, 0.30),
             (hw + 0.004, 0.268), (hw - 0.01, 0.252)]
    out['tire'] = _revolve(f'tire_{key}', prof, 120, coll, [mats['tire']], smooth=True, angle=50).data
    # rim barrel + machined lip
    lipx = hw - 0.005
    rp = [(-hw + 0.005, 0.228), (lipx - 0.03, 0.228), (lipx - 0.012, 0.232), (lipx, 0.244), (lipx + 0.004, 0.256),
          (lipx - 0.002, 0.266), (lipx - 0.016, 0.262), (lipx - 0.03, 0.255), (-hw + 0.02, 0.255), (-hw + 0.01, 0.262),
          (-hw, 0.258), (-hw + 0.005, 0.228)]
    midx = [0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0]
    out['barrel'] = _revolve(f'rimbarrel_{key}', rp, 128, coll, [mats['rim'], mats['machined']], mat_idx=midx, angle=40).data
    # spokes (6, gear-rhyme: tapered with a ridge, diamond-cut faces), hub
    bm = bmesh.new()
    fx_hub, fx_rim = lipx - 0.075, lipx - 0.022     # concave dish
    for i in range(6):
        ph = 2 * math.pi * i / 6 + math.pi / 6
        d = Vector((0, math.cos(ph), math.sin(ph))); t = Vector((0, -math.sin(ph), math.cos(ph)))
        secs = []
        N = 9
        for k in range(N):
            u = k / (N - 1)
            r = 0.055 + u * (0.232 - 0.055)
            w = 0.060 - 0.026 * u + 0.030 * max(0, u - 0.8) ** 2 / 0.04  # taper, flare into rim
            fx = fx_hub + (fx_rim - fx_hub) * (u ** 0.8)
            th = 0.042 - 0.012 * u
            c = d * r
            sec = [Vector((fx - th, 0, 0)) + c + t * (-w / 2), Vector((fx - 0.006, 0, 0)) + c + t * (-w / 2),
                   Vector((fx, 0, 0)) + c + t * (-w * 0.18), Vector((fx, 0, 0)) + c + t * (w * 0.18),
                   Vector((fx - 0.006, 0, 0)) + c + t * (w / 2), Vector((fx - th, 0, 0)) + c + t * (w / 2)]
            secs.append(sec)
        vs = _loft(bm, secs, cap=True)
    for f in bm.faces:
        if f.calc_center_median().x > 0 and f.normal.x > 0.85:
            f.material_index = 1
    out['spokes'] = _obj(f'spokes_{key}', bm, coll, [mats['rim'], mats['machined']], None, angle=30).data
    # hub + brass centre-lock nut (12-point, with ears) + cap
    hp = [(fx_hub - 0.05, 0.0), (fx_hub - 0.05, 0.075), (fx_hub - 0.002, 0.075), (fx_hub + 0.004, 0.068), (fx_hub + 0.006, 0.0)]
    out['hub'] = _revolve(f'hub_{key}', hp, 48, coll, [mats['rim']], angle=40).data
    bm = bmesh.new()
    star = []
    for k in range(24):
        a = 2 * math.pi * k / 24
        rr = 0.056 if k % 2 == 0 else 0.046
        star.append((rr * math.cos(a), rr * math.sin(a)))
    x0, x1 = fx_hub, fx_hub + 0.038
    secs = [[Vector((x, yy * sc, zz * sc)) for yy, zz in star] for x, sc in ((x0, 1.0), (x1 - 0.006, 1.0), (x1, 0.9))]
    _loft(bm, secs, cap=True)
    cap = [(x1 - 0.002, 0.0), (x1 - 0.002, 0.036), (x1 + 0.010, 0.034), (x1 + 0.018, 0.026), (x1 + 0.022, 0.012), (x1 + 0.023, 0.0)]
    out['nut'] = _obj(f'nut_{key}', bm, coll, mats['brass'], None, angle=30).data
    out['cap'] = _revolve(f'nutcap_{key}', cap, 48, coll, [mats['brass']], angle=50).data
    # brake disc (drilled via material) + bell
    dp = [(-0.055, 0.110), (-0.055, 0.190), (-0.022, 0.190), (-0.022, 0.110)]
    out['disc'] = _revolve(f'disc_{key}', dp + [dp[0]], 96, coll, [mats['disc']], angle=40).data
    bp = [(-0.04, 0.0), (-0.04, 0.112), (-0.01, 0.112), (fx_hub - 0.05, 0.08), (fx_hub - 0.05, 0.0)]
    out['bell'] = _revolve(f'bell_{key}', bp, 48, coll, [mats['black']], angle=40).data
    _WHEEL_MESHES[key] = out
    # remove the template objects (keep mesh data)
    for k, me in out.items():
        for o in list(bpy.data.objects):
            if o.data == me:
                bpy.data.objects.remove(o, do_unlink=True)
    return out


def _caliper_mesh(coll, mats):
    bm = bmesh.new()
    secs = []
    a0, a1 = math.radians(20), math.radians(85)
    N = 10
    for k in range(N):
        a = a0 + (a1 - a0) * k / (N - 1)
        d = Vector((0, math.cos(a), math.sin(a)))
        sec = []
        for x, r in ((-0.075, 0.165), (-0.075, 0.205), (-0.06, 0.215), (0.012, 0.215), (0.02, 0.205), (0.02, 0.165)):
            sec.append(Vector((x, 0, 0)) + d * r)
        secs.append(sec)
    _loft(bm, secs, cap=True)
    o = _obj('caliper_tmp', bm, coll, mats['caliper'], None, angle=30)
    me = o.data
    bpy.data.objects.remove(o, do_unlink=True)
    return me


def _add_child(name, me, par, coll, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), bevel_w=0.0):
    o = bpy.data.objects.new(name, me)
    C.link(o, coll)
    o.parent = par
    o.location, o.rotation_euler, o.scale = loc, rot, scale
    if bevel_w:
        C.bevel(o, bevel_w, 2, 35)
    return o

# ----------------------------------------------------------------------------- mechanical parts

def _suspension(coll, mats, name, hub_pos, sx, front):
    bm = bmesh.new()
    hx, hy, hz = hub_pos
    inner = sx * 0.42
    for dz, dy in ((0.13, 0.0), (-0.12, 0.0)):
        z = hz + dz
        p_out = (hx - sx * 0.12, hy, z)
        _tube(bm, [p_out, (inner, hy + 0.22, z + 0.02)], 0.016, 8)
        _tube(bm, [p_out, (inner, hy - 0.22, z + 0.02)], 0.016, 8)
    # upright
    _tube(bm, [(hx - sx * 0.11, hy, hz - 0.14), (hx - sx * 0.12, hy, hz + 0.15)], 0.03, 10)
    o = _obj(name, bm, coll, mats['steel'], None)
    # coil-over: spring helix + damper body
    bm2 = bmesh.new()
    top = Vector((sx * 0.40, hy + (0.05 if front else -0.05), hz + (0.20 if front else 0.34)))
    bot = Vector((hx - sx * 0.14, hy, hz - 0.08))
    d = (top - bot)
    pts = []
    turns, steps = 7, 140
    u = d.normalized().cross(Vector((0, 1, 0))).normalized(); v = d.normalized().cross(u)
    for k in range(steps + 1):
        t = k / steps
        a = 2 * math.pi * turns * t
        pts.append(bot + d * (0.15 + 0.7 * t) + (u * math.cos(a) + v * math.sin(a)) * 0.05)
    _tube(bm2, pts, 0.008, 6)
    spring = _obj(name + '_spring', bm2, coll, mats['caliper'], None, angle=60)
    bm3 = bmesh.new()
    _tube(bm3, [bot, bot + d * 0.6], 0.022, 12)
    _tube(bm3, [bot + d * 0.55, top], 0.012, 10)
    damper = _obj(name + '_damper', bm3, coll, mats['brass'], None)
    for c in (spring, damper):
        c.parent = o
    return o


def _engine(coll, mats):
    """Mid V-engine with exposed timing gear train (Act I rhyme), trumpets, headers."""
    bm = bmesh.new()
    y0 = YR + 0.1
    _box(bm, Vector((0, y0, 0.36)), (0.42, 0.75, 0.30))
    for sx in (-1, 1):
        rot = Matrix.Rotation(sx * math.radians(32), 3, 'Y')
        _box(bm, Vector((sx * 0.17, y0, 0.55)), (0.20, 0.72, 0.14), rot)
    o = _obj('engine', bm, coll, mats['engine'], None, bevel_w=0.012)
    bm = bmesh.new()
    for sx in (-1, 1):
        for k in range(4):
            y = y0 - 0.27 + k * 0.18
            base = Vector((sx * 0.08, y, 0.62))
            secs = []
            for i in range(6):
                t = i / 5
                r = 0.026 + 0.018 * t ** 2.5
                c = base + Vector((0, 0, 0.16 * t))
                secs.append([c + Vector((r * math.cos(2 * math.pi * q / 16), r * math.sin(2 * math.pi * q / 16), 0)) for q in range(16)])
            _loft(bm, secs, cap=False)
    tr = _obj('engine_trumpets', bm, coll, mats['titanium'], o, angle=50)
    # headers
    bm = bmesh.new()
    for sx in (-1, 1):
        for k in range(4):
            y = y0 - 0.27 + k * 0.18
            pts = [(sx * 0.33, y, 0.42), (sx * 0.40, y - 0.05, 0.34), (sx * 0.36, y - 0.25, 0.26),
                   (sx * (0.10 + 0.05 * k), YR - 0.75, 0.30), (sx * 0.12, -2.05, 0.40)]
            _tube(bm, pts, 0.021, 10)
    hd = _obj('engine_headers', bm, coll, mats['titanium'], o, angle=50)
    # timing gear train on the rear face
    gears = []
    gspec = [(30, 0.13, 0.0, 0.40, mats['brass']), (18, 0.08, 0.20, 0.47, mats['steel']), (18, 0.08, -0.20, 0.47, mats['steel']),
             (12, 0.055, 0.0, 0.62, mats['brass']), (24, 0.10, 0.27, 0.30, mats['brass']), (24, 0.10, -0.27, 0.30, mats['brass'])]
    for i, (t, r, x, z, m) in enumerate(gspec):
        g = C.make_gear(f'engine_gear{i}', teeth=t, r=r, thick=0.022, spokes=6, coll=coll, mat=m)
        g.rotation_euler = (math.pi / 2, 0, 0)
        g.location = (x, y0 - 0.39, z)
        g.parent = o
        gears.append(g)
    return o, gears


def _tub(coll, mats):
    bm = bmesh.new()
    secs = []
    for y, w, zb, zt in ((-0.85, 0.60, 0.11, 0.70), (-0.4, 0.70, 0.105, 0.72), (0.4, 0.68, 0.105, 0.66), (1.0, 0.45, 0.12, 0.52),
                         (1.55, 0.28, 0.14, 0.40)):
        sec = []
        for k in range(16):
            a = 2 * math.pi * k / 16
            ca, sa = math.cos(a), math.sin(a)
            x = w * math.copysign(abs(ca) ** 0.4, ca)
            z = (zb + zt) / 2 + (zt - zb) / 2 * math.copysign(abs(sa) ** 0.4, sa)
            sec.append(Vector((x, y, z)))
        secs.append(sec)
    _loft(bm, secs)
    o = _obj('tub', bm, coll, mats['carbon'], None, angle=50)
    C.subsurf(o, 1)
    # seats
    bm = bmesh.new()
    for sx in (-1, 1):
        _box(bm, Vector((sx * 0.28, -0.25, 0.33)), (0.40, 0.45, 0.10))
        _box(bm, Vector((sx * 0.28, -0.48, 0.58)), (0.40, 0.10, 0.55), Matrix.Rotation(math.radians(-18), 3, 'X'))
    seats = _obj('tub_seats', bm, coll, mats['carbon_matte'], o, bevel_w=0.03)
    return o


def _screws(bm, pts, r=0.006, h=0.004):
    """Tiny hex screw heads; pts: [(pos, normal)]."""
    for p, nrm in pts:
        nrm = Vector(nrm).normalized()
        u = nrm.cross(Vector((0, 0, 1)) if abs(nrm.z) < 0.9 else Vector((1, 0, 0))).normalized()
        v = nrm.cross(u)
        base = [Vector(p) + (u * math.cos(2 * math.pi * k / 6) + v * math.sin(2 * math.pi * k / 6)) * r for k in range(6)]
        top = [q + nrm * h for q in base]
        top2 = [Vector(p) + nrm * (h * 1.3) + (q - Vector(p)) * 0.6 for q in base]
        _loft(bm, [base, top, top2], cap=True)

# ----------------------------------------------------------------------------- build

def build_car(coll=None, name='Car'):
    coll = coll or bpy.context.scene.collection
    mats = materials()
    root = C.empty(name, (0, 0, 0), coll)
    sprung = C.empty(name + '_sprung', (0, 0, 0), coll)
    sprung.parent = root
    parts = {'sprung': sprung}

    pieces, bvh = build_body(coll, mats, sprung)
    for k, o in pieces.items():
        o.name = f'{name}_{k}'
        parts[k] = o
    body = pieces['body']

    # ---------------- aero / trim
    # front splitter (carbon blade) + canards
    bm = bmesh.new()
    sec = []
    for x in [i / 20 * 1.9 - 0.95 for i in range(21)]:
        y = 2.30 - 0.25 * (abs(x) / 0.95) ** 2.2
        sec.append((x, y))
    top = [Vector((x, y, 0.105)) for x, y in sec] + [Vector((x, 1.55, 0.105)) for x, y in reversed(sec)]
    bot = [v - Vector((0, 0, 0.018)) for v in top]
    _loft(bm, [bot, top], cap=True)
    parts['splitter'] = _obj(f'{name}_splitter', bm, coll, mats['carbon'], sprung, bevel_w=0.004)
    bm = bmesh.new()      # r3: teal lip along the splitter's leading edge
    lip_pts = [Vector((x, y + 0.004, 0.096)) for x, y in sec]
    _tube(bm, lip_pts, 0.0075, 8)
    _obj(f'{name}_splitter_lip', bm, coll, mats['accent'], parts['splitter'], angle=60)
    # nose intake grille (lower, central) + side intakes
    bm = bmesh.new()
    for sx in (-1, 1):
        for k in range(3):   # canards
            y = 1.88 + k * 0.1
            x0 = sx * 0.90
            z = 0.20 + k * 0.05
            _box(bm, Vector((x0 + sx * 0.03, y, z)), (0.12, 0.16, 0.008), Matrix.Rotation(sx * math.radians(-8), 3, 'Y') @ Matrix.Rotation(math.radians(-12), 3, 'X'))
    parts['canards'] = _obj(f'{name}_canards', bm, coll, mats['accent'], sprung, bevel_w=0.002)

    bm = bmesh.new()
    _box(bm, Vector((0, 2.17, 0.20)), (1.1, 0.04, 0.09))
    parts['grille'] = _obj(f'{name}_grille', bm, coll, mats['grille'], sprung, bevel_w=0.01)

    # side intake slats (instanced look: one mesh, many slats)
    bm = bmesh.new()
    for sx in (-1, 1):
        for k in range(9):
            z = 0.32 + k * 0.032
            y0, y1 = -0.98, -0.47
            hit = bvh.ray_cast(Vector((sx * 1.3, (y0 + y1) / 2, z)), Vector((-sx, 0, 0)))
            x = hit[0].x if hit[0] else sx * 0.88
            _box(bm, Vector((x - sx * 0.02, (y0 + y1) / 2, z)), (0.06, y1 - y0, 0.006), Matrix.Rotation(sx * math.radians(25), 3, 'Y'))
    parts['side_vents'] = _obj(f'{name}_side_vents', bm, coll, mats['carbon'], sprung, bevel_w=0.0015)
    bm = bmesh.new()
    for sx in (-1, 1):
        hit = bvh.ray_cast(Vector((sx * 1.3, -0.72, 0.45)), Vector((-sx, 0, 0)))
        x = hit[0].x if hit[0] else sx * 0.86
        _box(bm, Vector((x - sx * 0.05, -0.72, 0.45)), (0.02, 0.55, 0.32))
    parts['side_intake_backs'] = _obj(f'{name}_intake_backs', bm, coll, mats['grille'], sprung)

    # engine cover louvres between the buttresses
    bm = bmesh.new()
    for k in range(12):
        y = -1.05 - k * 0.075
        z = _surface_z(bvh, 0.0, y) or 0.88
        _box(bm, Vector((0, y, z + 0.012)), (0.44, 0.012, 0.03), Matrix.Rotation(math.radians(-35), 3, 'X'))
    parts['louvres'] = _obj(f'{name}_louvres', bm, coll, mats['carbon'], sprung, bevel_w=0.002)

    # hood vents: dark recessed plates + slats following the hood surface
    bm = bmesh.new(); bm2 = bmesh.new()
    for sx in (-1, 1):
        x0, x1, y0_, y1_ = sx * 0.17, sx * 0.43, 1.14, 1.50
        nu, nv = 8, 10
        grid = []
        for i in range(nu + 1):
            row = []
            for j in range(nv + 1):
                x = x0 + (x1 - x0) * i / nu; y = y0_ + (y1_ - y0_) * j / nv
                z = _surface_z(bvh, x, y) or 0.6
                row.append(bm.verts.new((x, y, z + 0.002)))
            grid.append(row)
        for i in range(nu):
            for j in range(nv):
                f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
        for k in range(7):
            y = y0_ + 0.03 + k * (y1_ - y0_ - 0.06) / 6
            xm = (x0 + x1) / 2
            z = _surface_z(bvh, xm, y) or 0.6
            _box(bm2, Vector((xm, y, z + 0.008)), (abs(x1 - x0) - 0.02, 0.008, 0.016), Matrix.Rotation(math.radians(30), 3, 'X'))
    if sx:
        parts['hood_vents'] = _obj(f'{name}_hood_vents', bm, coll, mats['grille'], sprung)
        _obj(f'{name}_hood_slats', bm2, coll, mats['carbon'], parts['hood_vents'], bevel_w=0.0015)

    # shark fin down the engine cover (canopy -> wing)
    bm = bmesh.new()
    secs = []
    N = 16
    for k in range(N):
        t = k / (N - 1)
        y = -0.62 - 1.38 * t
        zs_ = (_surface_z(bvh, 0.0, y) or 0.88) - 0.01
        ztop = 1.045 + 0.02 * t - 0.02 * math.sin(math.pi * t)
        th = 0.004 + 0.003 * math.sin(math.pi * t)
        secs.append([Vector((-th, y, zs_)), Vector((-th * 0.4, y, ztop)), Vector((th * 0.4, y, ztop)), Vector((th, y, zs_))])
    _loft(bm, secs, cap=True)
    parts['fin'] = _obj(f'{name}_fin', bm, coll, mats['carbon'], sprung, bevel_w=0.002)

    # carbon side skirts with an outboard flick
    bm = bmesh.new()
    for sx in (-1, 1):
        secs = []
        for k in range(14):
            t = k / 13
            y = -0.95 + 1.85 * t
            hit = bvh.ray_cast(Vector((sx * 1.4, y, 0.17)), Vector((-sx, 0, 0)))
            x = hit[0].x if hit[0] else sx * 0.93
            fl = 0.045 + 0.02 * math.sin(math.pi * t)
            secs.append([Vector((x - sx * 0.04, y, 0.105)), Vector((x + sx * fl, y, 0.112)), Vector((x + sx * fl, y, 0.126)),
                         Vector((x - sx * 0.04, y, 0.13))])
        _loft(bm, secs, cap=True)
    parts['skirts'] = _obj(f'{name}_skirts', bm, coll, mats['carbon'], sprung, bevel_w=0.002)

    # flying buttresses
    bm = bmesh.new()
    for sx in (-1, 1):
        secs = []
        N = 14
        for k in range(N):
            t = k / (N - 1)
            y = -0.50 - 1.62 * t
            x = sx * (0.40 + 0.40 * t ** 1.3)
            ztop = (_surface_z(bvh, x, y) or 0.85)
            z = 1.04 * (1 - t) ** 1.6 + ztop * (1 - (1 - t) ** 1.6) + 0.02 * math.sin(math.pi * t)
            z = max(z, ztop + 0.015 * (1 - t))
            w = 0.07 + 0.04 * math.sin(math.pi * t)
            th = 0.025
            n = Vector((sx * 0.9, 0, 0.45)).normalized()
            c = Vector((x, y, z))
            secs.append([c + Vector((-w, 0, 0)), c + Vector((-w, 0, th)), c + Vector((w, 0, th)), c + Vector((w, 0, 0))])
        _loft(bm, secs, cap=True)
    parts['buttresses'] = _obj(f'{name}_buttresses', bm, coll, mats['paint'], sprung, bevel_w=0.006)

    # rear wing on swan-neck pylons
    bm = bmesh.new()
    foil = []
    for k in range(16):
        a = 2 * math.pi * k / 16
        foil.append((0.16 * math.cos(a), 0.022 * math.sin(a) * (1.0 + 0.4 * math.cos(a))))
    secs = []
    for x in (-0.86, -0.8, 0.8, 0.86):
        twist = 0.02 * abs(x)
        secs.append([Vector((x, -2.02 + fy + (0.01 if abs(x) > 0.82 else 0), 1.06 + fz - fy * 0.18)) for fy, fz in foil])
    _loft(bm, secs, cap=True)
    wing = _obj(f'{name}_wing', bm, coll, mats['carbon'], sprung, bevel_w=0.003)
    bm = bmesh.new()
    for sx in (-1, 1):  # endplates (r3: teal livery)
        _box(bm, Vector((sx * 0.875, -2.03, 1.03)), (0.012, 0.42, 0.16))
    _obj(f'{name}_wing_endplates', bm, coll, mats['accent'], wing, bevel_w=0.003)
    bm = bmesh.new()
    for sx in (-1, 1):
        pts = [(sx * 0.32, -1.98, 1.06), (sx * 0.32, -2.10, 1.0), (sx * 0.32, -2.12, 0.92), (sx * 0.32, -2.05, 0.82)]
        secs = [[Vector(p) + Vector((dx, 0, dz)) for dx, dz in ((-0.008, -0.03), (-0.008, 0.03), (0.008, 0.03), (0.008, -0.03))] for p in pts]
        _loft(bm, secs, cap=True)
    pyl = _obj(f'{name}_wing_pylons', bm, coll, mats['titanium'], wing, bevel_w=0.003)
    parts['wing'] = wing

    # diffuser with fins
    bm = bmesh.new()
    _box(bm, Vector((0, -1.95, 0.17)), (1.6, 0.62, 0.012), Matrix.Rotation(math.radians(-22), 3, 'X'))
    for k in range(7):
        x = -0.66 + k * 0.22
        _box(bm, Vector((x, -1.96, 0.215)), (0.008, 0.6, 0.075), Matrix.Rotation(math.radians(-22), 3, 'X'))
    parts['diffuser'] = _obj(f'{name}_diffuser', bm, coll, mats['carbon'], sprung, bevel_w=0.002)

    # quad exhaust (centre cluster)
    bm = bmesh.new()
    for x in (-0.24, -0.08, 0.08, 0.24):
        for z in (0.43,):
            secs = []
            for (yy, r) in ((-2.0, 0.040), (-2.262, 0.040), (-2.272, 0.046), (-2.268, 0.034), (-2.16, 0.034)):
                secs.append([Vector((x + r * math.cos(2 * math.pi * q / 24), yy, z + r * math.sin(2 * math.pi * q / 24))) for q in range(24)])
            _loft(bm, secs, cap=False)
    parts['exhaust'] = _obj(f'{name}_exhaust', bm, coll, mats['titanium'], sprung, angle=60)
    bm = bmesh.new()
    _box(bm, Vector((0, -2.21, 0.43)), (0.66, 0.10, 0.13))
    parts['exhaust_surround'] = _obj(f'{name}_exhaust_bay', bm, coll, mats['carbon_matte'], sprung, bevel_w=0.01)
    bm = bmesh.new()   # dark throats inside the tips
    for x in (-0.24, -0.08, 0.08, 0.24):
        bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=0.034, matrix=Matrix.Translation((x, -2.20, 0.43)) @ Matrix.Rotation(math.pi / 2, 4, 'X'))
    _obj(f'{name}_exhaust_throats', bm, coll, mats['black'], parts['exhaust'])

    # rear light (r3): a 45 mm tall bar in THREE segments (gaps at x=+-0.30) set 7 mm back inside a
    # 75 mm matte-black bezel channel that follows the tail, + vertical fin blades at the corners
    bm = bmesh.new(); bmz = bmesh.new()
    def _tail_y(x, z):
        hit = bvh.ray_cast(Vector((x, -3.0, z)), Vector((0, 1, 0)))
        return hit[0].y if hit[0] else -2.24
    ZB = 0.70
    for x0, x1 in ((-0.88, -0.32), (-0.28, 0.28), (0.32, 0.88)):
        n = 16
        pts = []
        for k in range(n + 1):
            x = x0 + (x1 - x0) * k / n
            pts.append(Vector((x, _tail_y(x, ZB) - 0.002, ZB)))
        sec_shape = [(-0.006, -0.0225), (0.006, -0.0225), (0.006, 0.0225), (-0.006, 0.0225)]
        _loft(bm, [[p + Vector((0, dy, dz)) for dy, dz in sec_shape] for p in pts], cap=True)
    # bezel channel: top lip, bottom lip, back plate, end caps (proud of the tail by ~9 mm)
    n = 40
    pts = [Vector((x, _tail_y(x, ZB), ZB)) for x in [-0.90 + 1.80 * k / n for k in range(n + 1)]]
    for dz0, dz1, dy0, dy1 in ((0.0225, 0.0375, 0.004, -0.011), (-0.0375, -0.0225, 0.004, -0.011), (-0.0375, 0.0375, 0.006, 0.002)):
        _loft(bmz, [[p + Vector((0, dy, dz)) for dy, dz in ((dy0, dz0), (dy1, dz0), (dy1, dz1), (dy0, dz1))] for p in pts], cap=True)
    for sx in (-1, 1):
        x = sx * 0.885
        y = _tail_y(x, 0.62)
        # vertical fin blade standing proud of the tail corner
        _box(bm, Vector((x, y - 0.015, 0.585)), (0.014, 0.07, 0.25))
        _box(bmz, Vector((x - sx * 0.012, y - 0.012, 0.585)), (0.008, 0.06, 0.27))
    parts['rear_light'] = _obj(f'{name}_rear_light', bm, coll, mats['rear_light'], sprung)
    _obj(f'{name}_rear_light_bezel', bmz, coll, mats['bezel'], parts['rear_light'], angle=50)
    # red spill: a thin area light on the bar so the floor / diffuser / exhaust pick up red. Energy stays 0
    # unless set_light(..., spill=W) keys it (other acts keep their look).
    rs = C.light('AREA', f'{name}_rear_spill', (0, _tail_y(0.0, ZB) - 0.03, ZB), rot=(-math.pi / 2, 0, 0), energy=0.0,
                 color=(1.0, 0.035, 0.015), size=1.7, size_y=0.045, coll=coll)
    rs.parent = parts['rear_light']
    try:
        rs.visible_camera = False
        rs.data.use_soft_falloff = True
    except Exception:
        pass
    parts['rear_spill'] = rs
    # rear fascia mesh grille (hex mesh band between light bar and exhaust bay) + carbon surround lip
    bm = bmesh.new(); bm2 = bmesh.new()
    rows = []
    for zz in (0.515, 0.555, 0.60, 0.645):
        row = []
        for k in range(33):
            x = -0.76 + 1.52 * k / 32
            hit = bvh.ray_cast(Vector((x, -3.0, zz)), Vector((0, 1, 0)))
            y = hit[0].y if hit[0] else -2.24
            row.append(Vector((x, y - 0.006, zz)))
        rows.append(row)
    vs = [[bm.verts.new(p) for p in r_] for r_ in rows]
    for i in range(len(vs) - 1):
        for k in range(32):
            bm.faces.new((vs[i][k], vs[i][k + 1], vs[i + 1][k + 1], vs[i + 1][k]))
    for r_ in (rows[0], rows[-1]):
        _tube(bm2, [p - Vector((0, 0.002, 0)) for p in r_], 0.006, 6)
    parts['rear_grille'] = _obj(f'{name}_rear_grille', bm, coll, mats['grille'], sprung)
    _obj(f'{name}_rear_grille_lip', bm2, coll, mats['carbon'], parts['rear_grille'], angle=60)
    # front light strips: thin swept slashes along the nose edge
    bm = bmesh.new()
    for sx in (-1, 1):
        pts = []
        for k in range(16):
            t = k / 15
            y = 2.05 - 0.38 * t
            x = sx * (0.52 + 0.36 * t)
            hit = bvh.ray_cast(Vector((x, y, 2.0)), Vector((0, 0, -1)))
            z = hit[0].z if hit[0] else 0.5
            pts.append(Vector((x, y, z + 0.002)))
        _tube(bm, [p + Vector((0, 0, 0.004)) for p in pts], 0.0065, 8)
        # second vertical slash in the bumper corner
        y2 = 2.10
        hit = bvh.ray_cast(Vector((sx * 0.62, 3.0, 0.24)), Vector((0, -1, 0)))
        yy = hit[0].y if hit[0] else 2.2
        _box(bm, Vector((sx * 0.60, yy + 0.004, 0.24)), (0.16, 0.008, 0.012), Matrix.Rotation(sx * math.radians(18), 3, 'Y'))
    sm = bmesh.ops.solidify(bm, geom=[f for f in bm.faces], thickness=0.004) if False else None
    parts['front_light'] = _obj(f'{name}_front_light', bm, coll, mats['front_light'], sprung)
    # cool spill per strip (energy 0 unless set_light(..., spill=W))
    fsp = []
    for sx in (-1, 1):
        x, y = sx * 0.70, 1.86
        z = (_surface_z(bvh, x, y) or 0.5) + 0.03
        fl_ = C.light('AREA', f'{name}_front_spill_{"L" if sx < 0 else "R"}', (x, y + 0.02, z),
                      rot=(math.radians(45), 0, sx * math.radians(-46.5)), energy=0.0, color=(0.62, 0.88, 1.0), size=0.40,
                      size_y=0.02, coll=coll)
        fl_.parent = parts['front_light']
        try:
            fl_.visible_camera = False
        except Exception:
            pass
        fsp.append(fl_)
    parts['front_spill'] = fsp

    # mirrors on stalks
    for side, sx in (('L', -1), ('R', 1)):
        bm = bmesh.new()
        c = Vector((sx * 0.98, 0.62, 0.86))
        secs = []
        for k in range(8):
            t = k / 7
            rr = 0.012 + 0.05 * math.sin(math.pi * min(1, t * 1.1)) ** 0.6
            sec = [c + Vector((0, -0.10 + 0.14 * t, 0)) + Vector((rr * 1.6 * math.cos(2 * math.pi * q / 12), 0, rr * 0.75 * math.sin(2 * math.pi * q / 12))) for q in range(12)]
            secs.append(sec)
        _loft(bm, secs)
        _tube(bm, [c + Vector((-sx * 0.05, 0.0, -0.01)), c + Vector((-sx * 0.16, 0.06, -0.08))], 0.01, 8)
        mo = _obj(f'{name}_mirror_{side}', bm, coll, mats['accent'], sprung, angle=50)
        bm = bmesh.new()
        q = [c + Vector((sx * 1.5 * dx, -0.097, dz)) for dx, dz in ((-0.065, -0.03), (0.065, -0.03), (0.065, 0.03), (-0.065, 0.03))]
        vv = [bm.verts.new(p) for p in q]
        bm.faces.new(vv if sx < 0 else list(reversed(vv)))
        glass = _obj(f'{name}_mirror_glass_{side}', bm, coll, mats['mirror'], mo)
        parts['mirror_' + side] = mo

    # screws along the splitter and diffuser edges (macro detail)
    bm = bmesh.new()
    sp = []
    for k in range(40):
        x = -0.85 + 1.7 * k / 39
        y = 2.30 - 0.25 * (abs(x) / 0.95) ** 2.2 - 0.03
        sp.append(((x, y, 0.105), (0, 0, 1)))
    for k in range(24):
        x = -0.78 + 1.56 * k / 23
        sp.append(((x, -2.235, 0.30), (0, -0.3, -1)))
    _screws(bm, sp)
    parts['screws'] = _obj(f'{name}_screws', bm, coll, mats['titanium'], sprung, angle=60)

    # ---------------- mechanicals (visible in the exploded view)
    tub = _tub(coll, mats)
    tub.name = f'{name}_tub'; tub.parent = sprung; parts['tub'] = tub
    eng, gears = _engine(coll, mats)
    eng.name = f'{name}_engine'; eng.parent = sprung; parts['engine'] = eng
    parts['engine_gears'] = gears

    # ---------------- corners / wheels
    wheels = []
    cal_me = _caliper_mesh(coll, mats)
    for tag, y, sx in (('FL', YF, -1), ('FR', YF, 1), ('RL', YR, -1), ('RR', YR, 1)):
        rear = tag[0] == 'R'
        tr = TRACK_R if rear else TRACK_F
        hub = C.empty(f'{name}_corner_{tag}', (sx * tr, y, WR), coll)
        hub.parent = root
        hub.rotation_euler = (0, 0, math.pi)        # hub local X = world -X
        w = C.empty(f'{name}_wheel_{tag}', (0, 0, 0), coll, kind='CIRCLE')
        w.parent = hub
        w.empty_display_size = WR
        meshes = _wheel_meshes(coll, mats, rear)
        rz = 0.0 if sx < 0 else math.pi             # outer face: left -> local +X, right -> local -X
        for k, me in meshes.items():
            o = _add_child(f'{name}_{k}_{tag}', me, w, coll, rot=(0, 0, rz),
                           bevel_w=0.003 if k in ('spokes', 'nut') else 0.0)
        cal = _add_child(f'{name}_caliper_{tag}', cal_me, hub, coll, rot=(0, 0, rz), bevel_w=0.004)
        susp = _suspension(coll, mats, f'{name}_susp_{tag}', (sx * tr, y, WR), sx, not rear)
        susp.parent = sprung
        parts['corner_' + tag] = hub
        parts['susp_' + tag] = susp
        wheels.append(w)
    # wheel mesh template data stay cached per blend; clear cache for re-imports into a new file
    _WHEEL_MESHES.clear()
    return {'root': root, 'wheels': wheels, 'wheel_radius': WR, 'parts': parts, 'mats': mats, 'body': body,
            'sprung': sprung}


# ----------------------------------------------------------------------------- animation helpers

def _emit_socket(mat):
    nt = mat.node_tree
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n.inputs['Emission Strength']
    return None


def set_light(car, which, strength, frame, interp='LINEAR', spill=None):
    """Keyframe emission strength of 'rear' / 'front' light material ('rear_light' also accepted).
    spill=W also keys the bar's own area light(s) (red floor spill / cool splitter spill) to W watts."""
    key = which if which.endswith('_light') else which + '_light'
    mat = car['mats'][key]
    s = _emit_socket(mat)
    s.default_value = strength
    s.keyframe_insert('default_value', frame=frame)
    for fc in C.fcurves(mat.node_tree):
        for kp in fc.keyframe_points:
            if kp.co[0] == frame:
                kp.interpolation = interp
    if spill is not None:
        lp = car.get('parts', {}).get('rear_spill' if key.startswith('rear') else 'front_spill')
        for L_ in (lp if isinstance(lp, (list, tuple)) else [lp] if lp is not None else []):
            L_.data.energy = spill
            L_.data.keyframe_insert('energy', frame=frame)
            for fc in C.fcurves(L_.data):
                for kp in fc.keyframe_points:
                    if kp.co[0] == frame:
                        kp.interpolation = interp


def set_sweep(car, which, value, frame, interp='BEZIER'):
    mat = car['mats']['rear_light' if which.startswith('rear') else which]
    n = mat.node_tree.nodes.get('Sweep')
    if n is None:
        return
    n.outputs[0].default_value = value
    n.outputs[0].keyframe_insert('default_value', frame=frame)


def spin_wheels(car, f0, f1, dist0, dist1):
    """Roll the wheels for a car travelling from dist0 to dist1 metres (keys at f0,f1, linear)."""
    for w in car['wheels']:
        C.fc_key(w, 'rotation_euler', 0, [(f0, dist0 / WR), (f1, dist1 / WR)], interp='LINEAR')
