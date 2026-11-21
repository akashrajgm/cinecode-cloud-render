"""Act I kit (ESCAPEMENT): clockwork parts, horology materials, motes, camera helpers.
Blender 5.2 / EEVEE. Used by shots/act1_gears.py. Units: meters (big-scale macro, faked with long lens + wide aperture).
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler, Quaternion
from common import *

TAU = math.tau
cos, sin = math.cos, math.sin


# ============================================================================ mesh builder
class MB:
    """Collect verts/faces as python lists, build once (much faster than many bmesh calls)."""

    def __init__(self):
        self.v, self.f = [], []

    def loop(self, pts):
        i0 = len(self.v)
        self.v.extend([tuple(p) for p in pts])
        return list(range(i0, i0 + len(pts)))

    def bridge(self, a, b, closed=True):
        n = len(a)
        for k in range(n if closed else n - 1):
            k2 = (k + 1) % n
            self.f.append((a[k], a[k2], b[k2], b[k]))

    def cap(self, a, rev=False):
        self.f.append(tuple(reversed(a)) if rev else tuple(a))

    def build(self, name, coll=None, sharp=40, smooth=True):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name, me)
        link(o, coll)
        if smooth:
            shade(o, sharp)
        return o


def finalize(o, mat=None, bev=None, seg=2, angle=35):
    if bev:
        bevel(o, bev, seg, angle)
    if mat:
        set_mat(o, mat)
    return o


# ============================================================================ gears
def tooth_pts(style, nt=9):
    """(fraction of tooth period, normalised radius 0=root 1=tip). Tooth centred at frac .5, gap at 0."""
    if style in ('round', 'pinion'):
        hw = 0.2 if style == 'round' else 0.24
        fl = 0.5 if style == 'round' else 0.42
        pts = [(0.0, 0.0), (0.5 - hw - 0.08, 0.0), (0.5 - hw - 0.025, 0.07), (0.5 - hw, 0.25)]
        for k in range(nt):
            th = -math.pi / 2 + math.pi * k / (nt - 1)
            pts.append((0.5 + hw * sin(th), fl + (1 - fl) * cos(th)))
        pts += [(0.5 + hw, 0.25), (0.5 + hw + 0.025, 0.07), (0.5 + hw + 0.08, 0.0)]
        return pts
    if style == 'club':  # Swiss lever escape wheel: long back slope, club head, radial locking face
        return [(0.0, 0.0), (0.10, 0.0), (0.2, 0.2), (0.3, 0.45), (0.38, 0.68), (0.44, 0.86), (0.49, 0.96),
                (0.53, 1.0), (0.60, 0.985), (0.645, 0.95), (0.655, 0.86), (0.66, 0.5), (0.665, 0.1), (0.70, 0.0)]
    if style == 'trap':  # chunky industrial teeth (wall of teeth)
        return [(0.0, 0.0), (0.16, 0.0), (0.2, 0.08), (0.27, 0.85), (0.31, 0.97), (0.36, 1.0), (0.64, 1.0),
                (0.69, 0.97), (0.73, 0.85), (0.8, 0.08), (0.84, 0.0)]
    raise ValueError(style)


ADD = {'round': 0.95, 'pinion': 0.8, 'club': 2.6, 'trap': 1.0}
DED = {'round': 1.3, 'pinion': 1.15, 'club': 1.0, 'trap': 1.25}


def gear(name, teeth, rp, thick, style='round', body='spokes', spokes=5, spoke_w=None, bend=0.0,
         rim_w=None, hub=None, hole=None, hub_thick=None, mat=None, coll=None, bev=None, groove=True):
    """Horological wheel built from quad rings (no booleans). Axis = local Z, tooth k centred at (k+.5)*2pi/teeth.
    body: 'spokes' (crossings) | 'disk' (solid with hub boss)."""
    m = 2.0 * rp / teeth
    add, ded = ADD[style] * m, DED[style] * m
    r_tip, r_root = rp + add, rp - ded
    prof = tooth_pts(style)
    ang_r = [((t + f) * TAU / teeth, r_root + rn * (r_tip - r_root)) for t in range(teeth) for f, rn in prof]
    # inner rings use EVENLY spaced angles: the tooth profile has consecutive points at equal angles, which on an
    # inner ring at the same angles gave zero-length edges -> degenerate faces -> radial shading streaks.
    nA = len(ang_r)
    ang_r_in = [(TAU * i / nA, r) for i, (a, r) in enumerate(ang_r)]
    mb = MB()
    if body == 'spokes':
        rim_w = rim_w or max(2.6 * m, 0.1 * rp)
        inner = r_root - rim_w
    else:
        inner = hole or max(rp * 0.05, 0.003)
    z0, z1 = -thick / 2, thick / 2
    o0 = mb.loop([(r * cos(a), r * sin(a), z0) for a, r in ang_r])
    o1 = mb.loop([(r * cos(a), r * sin(a), z1) for a, r in ang_r])
    if body == 'spokes' or not groove:
        i0 = mb.loop([(inner * cos(a), inner * sin(a), z0) for a, r in ang_r_in])
        i1 = mb.loop([(inner * cos(a), inner * sin(a), z1) for a, r in ang_r_in])
        mb.bridge(o1, i1); mb.bridge(o0, i0); mb.bridge(o0, o1); mb.bridge(i0, i1)
    else:
        # solid disk with a sunk annular step (catches a second highlight ring)
        rs = r_root - max(2.0 * m, 0.08 * rp)
        dz = thick * 0.18
        s1 = mb.loop([(rs * cos(a), rs * sin(a), z1) for a, r in ang_r_in])
        s1d = mb.loop([(rs * cos(a), rs * sin(a), z1 - dz) for a, r in ang_r_in])
        s0 = mb.loop([(rs * cos(a), rs * sin(a), z0) for a, r in ang_r_in])
        s0d = mb.loop([(rs * cos(a), rs * sin(a), z0 + dz) for a, r in ang_r_in])
        i0 = mb.loop([(inner * cos(a), inner * sin(a), z0 + dz) for a, r in ang_r_in])
        i1 = mb.loop([(inner * cos(a), inner * sin(a), z1 - dz) for a, r in ang_r_in])
        mb.bridge(o1, s1); mb.bridge(s1, s1d); mb.bridge(s1d, i1)
        mb.bridge(o0, s0); mb.bridge(s0, s0d); mb.bridge(s0d, i0)
        mb.bridge(o0, o1); mb.bridge(i0, i1)
    # hub boss
    hub = hub or rp * 0.17
    hole = hole or max(rp * 0.045, 0.003)
    ht = hub_thick or thick * 1.5
    hs = 40
    circ = lambda r, z: [(r * cos(TAU * j / hs), r * sin(TAU * j / hs), z) for j in range(hs)]
    a0, a1 = mb.loop(circ(hub, -ht / 2)), mb.loop(circ(hub, ht / 2))
    b0, b1 = mb.loop(circ(hole, -ht / 2)), mb.loop(circ(hole, ht / 2))
    mb.bridge(a1, b1); mb.bridge(a0, b0); mb.bridge(a0, a1); mb.bridge(b0, b1)
    if body == 'spokes':
        st = thick * 0.8
        sw = spoke_w or rp * 0.11
        n = 10
        for s in range(spokes):
            ang = TAU * s / spokes + math.pi / spokes
            rings = []
            for k in range(n + 1):
                t = k / n
                rho = hub * 0.8 + (inner + rim_w * 0.25 - hub * 0.8) * t
                a = ang + bend * sin(math.pi * t) * (0.6 * rp / max(rho, 1e-3)) * 0.35
                w = sw * (1.0 - 0.4 * t) * (1 + 0.9 * max(0.0, 1 - t * 5) + 0.9 * max(0.0, (t - 0.86) / 0.14))
                c = Vector((rho * cos(a), rho * sin(a), 0))
                p = Vector((-sin(a), cos(a), 0)) * (w / 2)
                rings.append(mb.loop([c + p + Vector((0, 0, st / 2)), c - p + Vector((0, 0, st / 2)),
                                      c - p - Vector((0, 0, st / 2)), c + p - Vector((0, 0, st / 2))]))
            for k in range(n):
                mb.bridge(rings[k], rings[k + 1])
            mb.cap(rings[0]); mb.cap(rings[-1], rev=True)
    o = mb.build(name, coll, sharp=38)
    bev = bev if bev is not None else min(thick, m) * 0.14
    finalize(o, mat, bev, 2, 35)
    o['r_tip'] = r_tip
    o['rp'] = rp
    return o


def gear_ring_teeth(name, teeth, rp, thick, coll=None, mat=None):
    """Thin toothed ring only (for huge background wheels -> fewer polys)."""
    return gear(name, teeth, rp, thick, 'trap', 'spokes', spokes=0, rim_w=2.0 * 2 * rp / teeth, coll=coll, mat=mat)


def phase_tooth_to(direction_angle, teeth):
    """local rotation so a tooth centre points along direction_angle (rad)."""
    return direction_angle - 0.5 * TAU / teeth


def phase_gap_to(direction_angle, teeth):
    return direction_angle


# ============================================================================ small parts (shared meshes)
_CACHE = {}


def screw_mesh():
    """Slotted cheese/dome head screw, radius 1, height .4, axis +Z (base at z=0). Bevelled & applied once."""
    if 'screw' in _CACHE:
        return _CACHE['screw']
    mb = MB()
    sw, h, n = 0.09, 0.42, 20
    zs = [0.0, h * 0.5, h * 0.78, h * 0.93, h]
    rs = [1.0, 1.0, 0.93, 0.74, 0.42]
    for side in (1, -1):
        loops = []
        for z, r in zip(zs, rs):
            a0 = math.asin(min(0.95, sw / r))
            loops.append(mb.loop([(r * cos(a0 + (math.pi - 2 * a0) * k / n), side * r * sin(a0 + (math.pi - 2 * a0) * k / n), z)
                                  for k in range(n + 1)]))
        for k in range(len(loops) - 1):
            mb.bridge(loops[k], loops[k + 1])
        mb.cap(loops[0]); mb.cap(loops[-1])
    fz = h * 0.42
    bx = [(-0.97, -sw, 0), (0.97, -sw, 0), (0.97, sw, 0), (-0.97, sw, 0)]
    lo = mb.loop(bx); hi = mb.loop([(x, y, fz) for x, y, _ in bx])
    mb.bridge(lo, hi); mb.cap(lo); mb.cap(hi)
    o = mb.build('_screw', None, sharp=30)
    bevel(o, 0.035, 2, 30)
    apply_mods(o)
    me = o.data
    bpy.data.objects.remove(o)
    _CACHE['screw'] = me
    return me


def jewel_meshes():
    """(ruby dome, chaton ring) radius ~1, base at z=0."""
    if 'jewel' in _CACHE:
        return _CACHE['jewel']
    mb = MB()
    loops = []
    n = 40
    # domed jewel with a polished concave oil sink and a pin-sized pivot hole (~10% radius) - no "eye pupil"
    prof = [(1.0, 0.05), (0.97, 0.13), (0.88, 0.22), (0.74, 0.30), (0.56, 0.36), (0.40, 0.385), (0.30, 0.39),
            (0.22, 0.372), (0.15, 0.35), (0.10, 0.335)]
    for r, z in prof:
        loops.append(mb.loop([(r * cos(TAU * k / n), r * sin(TAU * k / n), z) for k in range(n)]))
    for i in range(len(loops) - 1):
        mb.bridge(loops[i], loops[i + 1])
    hole = mb.loop([(0.10 * cos(TAU * k / n), 0.10 * sin(TAU * k / n), 0.22) for k in range(n)])
    mb.bridge(loops[-1], hole); mb.cap(hole)
    base = mb.loop([(cos(TAU * k / n), sin(TAU * k / n), 0.0) for k in range(n)])
    mb.bridge(base, loops[0]); mb.cap(base)
    ruby = mb.build('_ruby', None, sharp=60)
    me_r = ruby.data
    bpy.data.objects.remove(ruby)
    # chaton (polished sink / gold setting): flat torus
    mb = MB()
    su, sv = 40, 10
    R, r = 1.22, 0.3
    rings = []
    for i in range(su):
        a = TAU * i / su
        rings.append(mb.loop([((R + r * cos(TAU * j / sv)) * cos(a), (R + r * cos(TAU * j / sv)) * sin(a),
                               0.45 * r * sin(TAU * j / sv) + 0.08) for j in range(sv)]))
    for i in range(su):
        mb.bridge(rings[i], rings[(i + 1) % su])
    ch = mb.build('_chaton', None, sharp=80)
    me_c = ch.data
    bpy.data.objects.remove(ch)
    _CACHE['jewel'] = (me_r, me_c)
    return me_r, me_c


def place(me, name, loc, rot=(0, 0, 0), scale=1.0, coll=None, mat=None):
    o = bpy.data.objects.new(name, me)
    link(o, coll)
    o.location = loc
    o.rotation_euler = rot
    o.scale = (scale, scale, scale) if isinstance(scale, (int, float)) else scale
    if mat is not None:
        o.material_slots and None
        if len(o.data.materials) == 0:
            o.data.materials.append(mat)
        else:
            o.material_slots[0].link = 'OBJECT'
            o.material_slots[0].material = mat
    return o


def screw(loc, size, coll, mat, rot_z=None, normal_rot=(0, 0, 0), name='screw'):
    me = screw_mesh()
    rz = random.uniform(0, TAU) if rot_z is None else rot_z
    e = Euler(normal_rot, 'XYZ').to_matrix() @ Euler((0, 0, rz), 'XYZ').to_matrix()
    o = place(me, name, loc, e.to_euler(), size, coll)
    _objmat(o, mat)
    return o


def jewel(loc, size, coll, M, ruby_mat=None, normal_rot=(0, 0, 0), name='jewel'):
    mr, mc = jewel_meshes()
    a = place(mr, name + '_r', loc, normal_rot, size, coll)
    _objmat(a, ruby_mat or M['ruby'])
    b = place(mc, name + '_c', loc, normal_rot, size, coll)
    _objmat(b, M.get('chaton', M['gold_pol']))
    return a, b


def _objmat(o, mat):
    if len(o.data.materials) == 0:
        o.data.materials.append(mat)
    o.material_slots[0].link = 'OBJECT'
    o.material_slots[0].material = mat


def cyl(name, r, depth, loc, rot=(0, 0, 0), coll=None, mat=None, bev=None, seg=32):
    o = prim('cylinder', name, loc=loc, rot=rot, coll=coll, r=r, depth=depth, segments=seg)
    shade(o, 40)
    finalize(o, mat, bev if bev is not None else min(r, depth) * 0.12, 2, 40)
    return o


def arbor(name, x, y, z0, z1, r, coll, M):
    """Polished steel arbor with conical pivots."""
    L = z1 - z0
    o = cyl(name, r, L, (x, y, (z0 + z1) / 2), coll=coll, mat=M['steel_pol'], seg=24)
    return o


# ============================================================================ plates / bridges
def stadium(p0, p1, r0, r1, n=14):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    ang = math.atan2(d.y, d.x)
    beta = math.acos(max(-1.0, min(1.0, (r0 - r1) / L)))
    pts = []
    for k in range(n + 1):
        a = ang - beta + 2 * beta * k / n
        pts.append((p1.x + r1 * cos(a), p1.y + r1 * sin(a)))
    for k in range(n + 1):
        a = ang + beta + (TAU - 2 * beta) * k / n
        pts.append((p0.x + r0 * cos(a), p0.y + r0 * sin(a)))
    return pts


def band(p0, pm, p1, w0, w1, n=16, cap=8):
    """Closed outline of a curved arm: quadratic Bezier centre line p0 -> pm -> p1, width w0 -> w1, round caps."""
    p0, pm, p1 = Vector((*p0[:2], 0)), Vector((*pm[:2], 0)), Vector((*p1[:2], 0))
    cs, ws, ts = [], [], []
    for k in range(n + 1):
        t = k / n
        c = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * pm + t * t * p1
        d = (2 * (1 - t) * (pm - p0) + 2 * t * (p1 - pm)).normalized()
        cs.append(c); ws.append(w0 + (w1 - w0) * t); ts.append(d)
    left = [cs[k] + Vector((-ts[k].y, ts[k].x, 0)) * ws[k] for k in range(n + 1)]
    right = [cs[k] - Vector((-ts[k].y, ts[k].x, 0)) * ws[k] for k in range(n + 1)]
    pts = [(v.x, v.y) for v in right]
    a1 = math.atan2(ts[-1].y, ts[-1].x)
    for j in range(1, cap):
        a = a1 - math.pi / 2 + math.pi * j / cap
        pts.append((cs[-1].x + ws[-1] * cos(a), cs[-1].y + ws[-1] * sin(a)))
    pts += [(v.x, v.y) for v in reversed(left)]
    a0 = math.atan2(ts[0].y, ts[0].x)
    for j in range(1, cap):
        a = a0 + math.pi / 2 + math.pi * j / cap
        pts.append((cs[0].x + ws[0] * cos(a), cs[0].y + ws[0] * sin(a)))
    return pts


def slab(name, outline, z0, z1, coll=None, mat=None, bev=0.01, seg=2):
    mb = MB()
    a = mb.loop([(x, y, z0) for x, y in outline])
    b = mb.loop([(x, y, z1) for x, y in outline])
    mb.bridge(a, b); mb.cap(a, rev=True); mb.cap(b)
    o = mb.build(name, coll, sharp=35)
    return finalize(o, mat, bev, seg, 35)


def bridge_plate(name, p0, p1, r0, r1, z, thick, coll, M, mat=None, screws=True, jewels=(), jsize=0.03, ssize=None):
    o = slab(name, stadium(p0, p1, r0, r1), z, z + thick, coll, mat or M['geneve'], bev=min(thick * 0.18, 0.02))
    ss = ssize or min(r0, r1) * 0.42
    if screws:
        for p, r, q in ((p0, r0, p1), (p1, r1, p0)):
            p = Vector((p[0], p[1]))
            if any((Vector((j[0], j[1])) - p).length < r * 0.6 for j in jewels) or (name.startswith('cock') and p == Vector(p0[:2])):
                p = p + (Vector((q[0], q[1])) - p).normalized() * (r * 1.3)      # keep the jewel clear
            screw((p.x, p.y, z + thick - ss * 0.05), ss, coll, M['blued'])
    for j in jewels:
        jewel((j[0], j[1], z + thick - jsize * 0.02), jsize, coll, M)
    return o


def ring_obj(name, r_in, r_out, z0, z1, coll, mat, n=96, bev=0.004):
    mb = MB()
    c = lambda r, z: [(r * cos(TAU * k / n), r * sin(TAU * k / n), z) for k in range(n)]
    a0, a1, b0, b1 = mb.loop(c(r_out, z0)), mb.loop(c(r_out, z1)), mb.loop(c(r_in, z0)), mb.loop(c(r_in, z1))
    mb.bridge(a1, b1); mb.bridge(a0, b0); mb.bridge(a0, a1); mb.bridge(b0, b1)
    o = mb.build(name, coll, sharp=40)
    return finalize(o, mat, bev, 2, 40)


def hairspring(name, r0, r1, coils, height, thick, coll, mat, pts_per_coil=72, shape_angles=None):
    """Archimedean spiral ribbon. shape_angles: list of inner-end rotations (rad) -> shape keys 'a{i}'."""
    N = int(coils * pts_per_coil)
    Phi = coils * TAU

    def build_pts(theta):
        out = []
        for i in range(N + 1):
            s = i / N
            phi = s * Phi
            r = r0 + (r1 - r0) * s
            a = phi + theta * (1 - s)
            out.append((r, a))
        return out

    def verts(theta):
        vs = []
        for r, a in build_pts(theta):
            ri, ro = r - thick / 2, r + thick / 2
            ca, sa = cos(a), sin(a)
            vs += [(ri * ca, ri * sa, height / 2), (ro * ca, ro * sa, height / 2), (ro * ca, ro * sa, -height / 2), (ri * ca, ri * sa, -height / 2)]
        return vs
    mb = MB()
    vs = verts(0.0)
    mb.v = vs
    for i in range(N):
        a = [4 * i + k for k in range(4)]
        b = [4 * (i + 1) + k for k in range(4)]
        mb.bridge(a, b)
    mb.cap([0, 1, 2, 3]); mb.cap([4 * N + k for k in range(4)], rev=True)
    o = mb.build(name, coll, sharp=60)
    set_mat(o, mat)
    if shape_angles:
        o.shape_key_add(name='Basis', from_mix=False)
        for i, th in enumerate(shape_angles):
            kb = o.shape_key_add(name=f'a{i}', from_mix=False)
            vv = verts(th)
            flat = [c for p in vv for c in p]
            kb.data.foreach_set('co', flat)
    return o


def key_hairspring(o, shape_angles, frames_thetas):
    """Animate shape keys so the inner end follows theta(frame) (piecewise-linear blend of neighbours)."""
    kbs = o.data.shape_keys.key_blocks
    angs = shape_angles
    for f, th in frames_thetas:
        th = max(angs[0], min(angs[-1], th))
        j = 0
        while j < len(angs) - 2 and th > angs[j + 1]:
            j += 1
        t = (th - angs[j]) / (angs[j + 1] - angs[j])
        for i in range(len(angs)):
            w = (1 - t) if i == j else (t if i == j + 1 else 0.0)
            kb = kbs[f'a{i}']
            kb.value = w
            kb.keyframe_insert('value', frame=f)
    ad = o.data.shape_keys.animation_data
    if ad and ad.action:
        for fc in fcurves(o.data.shape_keys):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'


# ============================================================================ materials
def _rough_rings(b, vec, freq, amt):
    w = b.n('ShaderNodeTexWave')
    w.wave_type = 'RINGS'
    w.inputs['Scale'].default_value = freq
    w.inputs['Distortion'].default_value = 1.5
    w.inputs['Detail'].default_value = 2.0
    b.link(vec, w.inputs['Vector'])
    return w


def scratches(b, scale=1.0, width=0.012, sparsity=0.55):
    """Sparse long fine scratches: iso-lines of strongly stretched noise along two OBLIQUE (non-orthogonal)
    directions, masked by a low-frequency patch noise -> random scuffs, never a woven grid."""
    out = None
    for rot, sc in (((0.35, 0.8, 0.25), 7.0), ((1.2, -0.5, 0.95), 5.5)):
        tc = b.n('ShaderNodeTexCoord')
        mp = b.n('ShaderNodeMapping')
        mp.inputs['Rotation'].default_value = rot
        mp.inputs['Scale'].default_value = (scale * 0.6, scale * 0.6, scale * 40.0)
        b.link(tc.outputs['Object'], mp.inputs['Vector'])
        nz = b.noise(mp.outputs['Vector'], sc, 1.0, 0.5)
        line = b.maprange(b.math('ABSOLUTE', b.math('SUBTRACT', nz.outputs['Fac'], 0.5)), 0.0, width, 1.0, 0.0)
        out = line if out is None else b.math('MAXIMUM', out, line)
    patch = b.noise(b.coord('Object', scale), 1.3, 2, 0.5)
    return b.math('MULTIPLY', out, b.maprange(patch.outputs['Fac'], sparsity, sparsity + 0.12, 0.0, 1.0))


def edge_mask(b, lo=0.70, width=0.24):
    """Bevel-strip detector for prismatic parts whose axis is local Z (wheels, plates, bridges, arbors): the
    harden-normals bevel strips are the only faces whose object normal sits around |nz|~0.7 (caps = 1, flanks = 0).
    EEVEE has no Pointiness, so this is how worn/polished edges are found in the shader."""
    tc = b.n('ShaderNodeTexCoord')
    sp = b.n('ShaderNodeSeparateXYZ')
    b.link(tc.outputs['Normal'], sp.inputs['Vector'])
    az = b.math('ABSOLUTE', sp.outputs['Z'])
    return b.maprange(b.math('ABSOLUTE', b.math('SUBTRACT', az, lo)), 0.0, width, 1.0, 0.0)


def mat_brass_x(name, base, dark, rough=(0.16, 0.42), scale=1.0, worn=0.45, rings=0.0, scratch=0.6, grime=(0.08, 0.05, 0.025), ao=True,
                cell=0.0, cell_amt=0.0, edge=0.0, flank=0.0, flank_freq=45.0):
    """Worn brass / gilt: tarnish noise, grime in crevices (AO), sparse fine scratches, optional circular graining.
    cell/cell_amt: per-tooth (voronoi cell, object space) hue/value variation.  edge: polished, brighter bevel
    edges (wear).  flank: fine machining marks (bands along object Z) in the bump."""
    b = NB(name)
    v = b.coord('Object', scale)
    n1 = b.noise(v, 2.2, 8, 0.6)
    n2 = b.noise(v, 30.0, 5, 0.65)
    scr = scratches(b, scale)
    col = b.ramp(n1.outputs['Fac'], [(0.3, dark), (0.68, base)])
    c = b.mix(col.outputs[0], grime, b.maprange(n2.outputs['Fac'], 0.52, 0.78, 0, worn))
    if cell:
        vo = b.voronoi(b.coord('Object', 1.0), cell, 'F1', 'EUCLIDEAN', 1.0)
        sp = b.n('ShaderNodeSeparateColor')
        b.link(vo.outputs['Color'], sp.inputs['Color'])
        c = b.mix(c, (1.0, 0.80, 0.58), b.math('MULTIPLY', sp.outputs['Red'], cell_amt * 2.0), 'MULTIPLY')       # deeper amber
        c = b.mix(c, (0.70, 0.70, 0.66), b.math('MULTIPLY', sp.outputs['Green'], cell_amt * 1.6), 'MULTIPLY')    # darker tooth
    if ao:
        aon = b.n('ShaderNodeAmbientOcclusion')
        aon.inputs['Distance'].default_value = 0.15 / max(scale, 0.2)
        c = b.mix(c, grime, b.maprange(aon.outputs['AO'], 0.25, 0.9, 0.85, 0.0))
    c = b.mix(c, tuple(min(1, x * 1.2) for x in base), b.math('MULTIPLY', scr, scratch * 0.5))
    em = None
    if edge:
        em = edge_mask(b)
        c = b.mix(c, tuple(min(1, x * 1.25) for x in base), b.math('MULTIPLY', em, edge))
    b.set('Base Color', c)
    b.set('Metallic', 1.0)
    r = b.maprange(n1.outputs['Fac'], 0.3, 0.75, rough[0], rough[1])
    if rings:
        w = _rough_rings(b, b.coord('Object', scale), 40.0, 0)
        r = b.math('ADD', r, b.math('MULTIPLY', w.outputs['Fac'], rings))
    r = b.math('ADD', r, b.math('MULTIPLY', scr, 0.12 * scratch))
    if em is not None:
        r = b.math('SUBTRACT', r, b.math('MULTIPLY', em, 0.12 * edge), clamp=True)
    b.set('Roughness', r)
    h = b.math('ADD', n2.outputs['Fac'], b.math('MULTIPLY', scr, 0.15 * scratch))
    if flank:
        wv = b.n('ShaderNodeTexWave')
        wv.wave_type = 'BANDS'
        try:
            wv.bands_direction = 'Z'
        except Exception:
            pass
        wv.inputs['Scale'].default_value = flank_freq
        wv.inputs['Distortion'].default_value = 0.6
        wv.inputs['Detail'].default_value = 1.0
        b.link(b.coord('Object', 1.0), wv.inputs['Vector'])
        h = b.math('ADD', h, b.math('MULTIPLY', wv.outputs['Fac'], flank))
    b.set('Normal', b.bump(h, 0.05, 0.003))
    return b.mat


def mat_steel_x(name, base=(0.62, 0.63, 0.66), rough=(0.06, 0.2), scale=1.0, bump=0.03, tint_dark=0.6):
    b = NB(name)
    v = b.coord('Object', scale)
    n1 = b.noise(v, 3.0, 8, 0.6)
    n2 = b.noise(b.coord('Object', (scale * 2, scale * 2, scale * 120)), 25.0, 3, 0.6)
    b.set('Base Color', b.mix(base, tuple(c * tint_dark for c in base), n1.outputs['Fac']))
    b.set('Metallic', 1.0)
    b.set('Roughness', b.maprange(b.math('ADD', n1.outputs['Fac'], b.math('MULTIPLY', n2.outputs['Fac'], 0.3)), 0.3, 1.0, rough[0], rough[1]))
    b.set('Normal', b.bump(n2.outputs['Fac'], bump, 0.002))
    return b.mat


def mat_blued(name='Blued'):
    b = NB(name)
    v = b.coord('Object', 1.0)
    n1 = b.noise(v, 6.0, 6, 0.6)
    # peacock blue (revision: the old mix drifted violet and read as a purple Slinky)
    b.set('Base Color', b.mix((0.02, 0.07, 0.30), (0.03, 0.12, 0.38), n1.outputs['Fac']))
    b.set('Metallic', 1.0)
    b.set('Roughness', b.maprange(n1.outputs['Fac'], 0.3, 0.7, 0.12, 0.25))
    # no clear-coat: a 2nd ray-traced closure on the half-frame hairspring made 1C cost ~60 s/frame
    return b.mat


def mat_ruby(name='Ruby', glow=0.03):
    """Synthetic ruby: translucent pink-red, IOR 1.77, refracts what is behind it (ray-traced refraction),
    bright internal edges from the fresnel; only a whisper of emission so it never reads as an LED."""
    b = NB(name)
    lw = b.n('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.35
    b.set('Base Color', (0.85, 0.06, 0.10))
    b.set('Roughness', 0.02)
    b.set('IOR', 1.77)
    try:
        b.set('Transmission Weight', 1.0)
    except Exception as e:
        print('[kit] ruby transmission', e)
    b.set('Subsurface Weight', 0.0)
    b.set('Emission Color', (1.0, 0.08, 0.08))
    em = b.maprange(lw.outputs['Facing'], 0.0, 1.0, glow, glow * 0.2)
    b.set('Emission Strength', em)
    b.mat['glow_node'] = em.node.name
    m = b.mat
    for attr, val in (('surface_render_method', 'DITHERED'), ('use_raytrace_refraction', True), ('use_screen_refraction', True)):
        try:
            setattr(m, attr, val)
        except Exception:
            pass
    return m


def mat_geneve(name, base=(0.80, 0.62, 0.38), stripe=0.09, angle=0.45, scale=1.0, rough=(0.1, 0.34)):
    """Cotes de Geneve: parallel bands, each brushed with repeating arcs; band borders form ridges."""
    b = NB(name)
    tc = b.n('ShaderNodeTexCoord')
    mp = b.n('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (0, 0, angle)
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    b.link(tc.outputs['Object'], mp.inputs['Vector'])
    sp = b.n('ShaderNodeSeparateXYZ')
    b.link(mp.outputs['Vector'], sp.inputs['Vector'])
    # stripes are slightly curved (the brushing wheel's arc) -> u bends with y^2 inside each repeat
    vy = b.math('DIVIDE', sp.outputs['Y'], stripe * 4.0)
    fy = b.math('SUBTRACT', b.math('FRACT', vy), 0.5)
    u = b.math('ADD', b.math('DIVIDE', sp.outputs['X'], stripe), b.math('MULTIPLY', b.math('MULTIPLY', fy, fy), 0.35))
    fu = b.math('FRACT', u)
    # sawtooth across each band: surface tilts -> each band catches light as a soft gradient, hard step at the edge
    saw = b.math('POWER', fu, 1.6)
    n1 = b.noise(b.coord('Object', scale), 3.0, 6, 0.6)
    fine = b.noise(b.coord('Object', (scale * 3, scale * 3, scale * 3)), 60.0, 2, 0.5)
    b.set('Base Color', b.mix(tuple(c * 0.62 for c in base), base, b.math('ADD', b.math('MULTIPLY', saw, 0.7), b.math('MULTIPLY', n1.outputs['Fac'], 0.3))))
    b.set('Metallic', 1.0)
    rr = b.maprange(b.math('ADD', b.math('MULTIPLY', saw, -0.6), b.math('MULTIPLY', fine.outputs['Fac'], 0.4)), -0.6, 0.4, rough[0], rough[1])
    b.set('Roughness', rr)
    b.set('Normal', b.bump(saw, 0.35, stripe * 0.06))
    try:
        b.set('Anisotropic', 0.5)
    except Exception:
        pass
    return b.mat


def mat_perlage(name, base=(0.7, 0.7, 0.72), cell=0.05, scale=1.0, rough=(0.14, 0.42)):
    """Perlage: overlapping circular graining spots (voronoi rings)."""
    b = NB(name)
    v = b.coord('Object', scale)
    # revision: low-contrast swirl that only shows in reflection. Flat base (+-5% noise), a per-spot roughness
    # offset and a very shallow dome per spot (crescent where the light mirrors) - no dark rings, no bubble-wrap.
    vo = b.voronoi(v, 1.0 / cell, 'F1', 'EUCLIDEAN', 1.0)
    d = vo.outputs['Distance']
    sp = b.n('ShaderNodeSeparateColor')
    b.link(vo.outputs['Color'], sp.inputs['Color'])
    n1 = b.noise(v, 2.0, 6, 0.6)
    b.set('Base Color', b.mix(tuple(c * 0.92 for c in base), base, n1.outputs['Fac']))
    b.set('Metallic', 1.0)
    b.set('Roughness', b.maprange(b.math('ADD', b.math('MULTIPLY', sp.outputs['Red'], 0.25), b.math('MULTIPLY', n1.outputs['Fac'], 0.75)),
                                  0.0, 1.0, rough[0], rough[0] + (rough[1] - rough[0]) * 0.3))
    b.set('Normal', b.bump(d, 0.02, cell * 0.1))
    return b.mat


def mat_mote(name='Mote', warm=(1.0, 0.62, 0.28), cool=(0.55, 0.85, 1.0), strength=22.0):
    b = NB(name)
    at = b.n('ShaderNodeAttribute')
    at.attribute_name = 'mote'
    at.attribute_type = 'GEOMETRY'
    hue = b.n('ShaderNodeAttribute')
    hue.attribute_name = 'tint'
    hue.attribute_type = 'GEOMETRY'
    b.set('Base Color', (0, 0, 0))
    b.set('Roughness', 1.0)
    b.set('Emission Color', b.mix(warm, cool, hue.outputs['Fac']))
    em = b.math('MULTIPLY', at.outputs['Fac'], strength)
    b.set('Emission Strength', em)
    b.mat['strength_node'] = em.node.name if hasattr(em, 'node') else ''
    return b.mat


def mat_dust(name='Dust'):
    """Real dust (client rule): NOT emissive. Pale fibrous diffuse + translucency, so a speck only shows where a
    light actually hits it, and glows when backlit (forward scatter) like dust in a beam."""
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'mote'; at.attribute_type = 'GEOMETRY'
    tn = nt.nodes.new('ShaderNodeAttribute'); tn.attribute_name = 'tint'; tn.attribute_type = 'GEOMETRY'
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    mx.inputs[6].default_value = (0.95, 0.86, 0.72, 1); mx.inputs[7].default_value = (0.8, 0.86, 0.92, 1)
    nt.links.new(tn.outputs['Fac'], mx.inputs['Factor'])
    alb = nt.nodes.new('ShaderNodeMix'); alb.data_type = 'RGBA'; alb.blend_type = 'MULTIPLY'
    alb.inputs['Factor'].default_value = 1.0
    nt.links.new(mx.outputs[2], alb.inputs[6])
    nt.links.new(at.outputs['Color'], alb.inputs[7])
    df = nt.nodes.new('ShaderNodeBsdfDiffuse')
    tr = nt.nodes.new('ShaderNodeBsdfTranslucent')
    nt.links.new(alb.outputs[2], df.inputs['Color'])
    nt.links.new(alb.outputs[2], tr.inputs['Color'])
    ms = nt.nodes.new('ShaderNodeMixShader'); ms.inputs['Fac'].default_value = 0.6
    nt.links.new(df.outputs[0], ms.inputs[1]); nt.links.new(tr.outputs[0], ms.inputs[2])
    nt.links.new(ms.outputs[0], out.inputs['Surface'])
    return m


def mat_black(name='Black', rough=0.6):
    return mat_principled(name, (0.01, 0.01, 0.012), rough, 0.6)


def materials():
    M = {}
    M['brass'] = mat_brass_x('BrassWorn', (0.80, 0.58, 0.28), (0.36, 0.22, 0.09), (0.18, 0.46), 1.0, 0.55, cell=9.0, cell_amt=0.08, edge=0.8)
    # big wheel brass: yellow brass (not copper-orange), per-tooth hue/value variation, polished worn edges, tool marks
    M['brass_big'] = mat_brass_x('BrassBig', (0.80, 0.60, 0.28), (0.30, 0.19, 0.08), (0.2, 0.5), 0.6, 0.7, scratch=0.8,
                                 cell=6.0, cell_amt=0.10, edge=1.0, flank=0.25, flank_freq=40.0)
    M['gold'] = mat_brass_x('GoldPlated', (1.0, 0.70, 0.30), (0.66, 0.40, 0.13), (0.1, 0.26), 1.5, 0.12, rings=0.08, scratch=0.25, edge=0.7)
    M['gold_pol'] = mat_brass_x('GoldPolished', (1.0, 0.74, 0.36), (0.8, 0.5, 0.2), (0.05, 0.12), 2.0, 0.0, scratch=0.1, ao=False)
    M['chaton'] = mat_brass_x('Chaton', (0.62, 0.46, 0.24), (0.42, 0.28, 0.12), (0.12, 0.22), 2.0, 0.0, scratch=0.1, ao=False)
    M['rust'] = mat_brass_x('BrassRust', (0.62, 0.36, 0.15), (0.20, 0.08, 0.03), (0.3, 0.65), 0.8, 0.9, scratch=0.5, edge=0.6)
    M['black_steel'] = mat_steel_x('BlackenedSteel', (0.06, 0.057, 0.055), (0.3, 0.5), 1.0, 0.04, 0.55)
    M['steel_pol'] = mat_steel_x('SteelPolished', (0.70, 0.71, 0.74), (0.04, 0.14), 2.0)
    M['steel'] = mat_steel_x('Steel', (0.55, 0.56, 0.58), (0.12, 0.32), 1.0, 0.05)
    M['steel_dark'] = mat_steel_x('SteelDark', (0.22, 0.23, 0.25), (0.2, 0.42), 1.0, 0.08, 0.5)
    M['blued'] = mat_blued()
    M['ruby'] = mat_ruby()
    M['geneve'] = mat_geneve('Geneve', (0.82, 0.64, 0.40))
    M['geneve_rh'] = mat_geneve('GeneveRhodium', (0.66, 0.67, 0.70))
    M['perlage'] = mat_perlage('Perlage', (0.27, 0.22, 0.16), 0.03, rough=(0.3, 0.55))      # dark: it mirrors the haze
    M['perlage_dark'] = mat_perlage('PerlageDark', (0.18, 0.18, 0.2), 0.04)
    M['mote'] = mat_dust()          # client rule: real, light-catching dust (old emissive mat_mote retired)
    M['black'] = mat_black()
    return M


# ============================================================================ atmosphere / light rigs
def haze(name, loc, size, density, color=(0.5, 0.72, 0.95), aniso=0.55, noise=2.5, contrast=(0.3, 0.8), coll=None):
    """Local noisy haze volume (box). Keeps the foreground clean & black while the background glows."""
    m = mat_volume(name + 'M', density, color, aniso, noise_scale=noise, noise_contrast=contrast)
    o = volume_box(name, loc, size, m, coll)
    try:
        o.visible_shadow = False
    except Exception:
        pass
    return o


def haze_glow(name, loc, size, density, color=(0.45, 0.7, 0.95), emit=0.3, noise=2.2, coll=None):
    """Noisy haze box that also glows faintly (light scattered in from the whole mechanism around it). Density and
    glow share one noise field and fade out spherically toward the box faces, so no box edge ever shows."""
    m = bpy.data.materials.new(name + 'M')
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
    vp.inputs['Anisotropy'].default_value = 0.5
    vp.inputs['Emission Color'].default_value = (*color, 1)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = noise
    nz.inputs['Detail'].default_value = 6
    nz.inputs['Roughness'].default_value = 0.6
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.3
    mr.inputs['From Max'].default_value = 0.75
    nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
    ln = nt.nodes.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'
    nt.links.new(tc.outputs['Object'], ln.inputs[0])
    fo = nt.nodes.new('ShaderNodeMapRange')
    fo.inputs['From Min'].default_value = 0.45
    fo.inputs['From Max'].default_value = 1.0
    fo.inputs['To Min'].default_value = 1.0
    fo.inputs['To Max'].default_value = 0.0
    try:
        fo.interpolation_type = 'SMOOTHSTEP'
    except Exception:
        pass
    nt.links.new(ln.outputs['Value'], fo.inputs['Value'])
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
    nt.links.new(mr.outputs['Result'], mul.inputs[0]); nt.links.new(fo.outputs['Result'], mul.inputs[1])
    dn = nt.nodes.new('ShaderNodeMath'); dn.operation = 'MULTIPLY'; dn.inputs[1].default_value = density
    nt.links.new(mul.outputs[0], dn.inputs[0]); nt.links.new(dn.outputs[0], vp.inputs['Density'])
    em = nt.nodes.new('ShaderNodeMath'); em.operation = 'MULTIPLY'; em.inputs[1].default_value = emit
    nt.links.new(mul.outputs[0], em.inputs[0]); nt.links.new(em.outputs[0], vp.inputs['Emission Strength'])
    nt.links.new(vp.outputs['Volume'], out.inputs['Volume'])
    o = volume_box(name, loc, size, m, coll)
    try:
        o.visible_shadow = False
    except Exception:
        pass
    return o


def vol(lt, f):
    try:
        lt.data.volume_factor = f
    except Exception:
        pass
    return lt


def vol_only(lt):
    """Light that only illuminates the participating media (shafts/glow), never surfaces."""
    for attr in ('diffuse_factor', 'specular_factor', 'transmission_factor'):
        try:
            setattr(lt.data, attr, 0.0)
        except Exception:
            pass
    vol(lt, 1.0)
    return lt


def sheen_card(cam_loc, tgt, dist, size, energy, color=(1.0, 0.78, 0.55), coll=None, size_y=None, name='Sheen', normal=(0, 0, 1)):
    """Area light at the camera's mirror direction about the surface normal through tgt, aimed at tgt:
    flat metal faces (plates, wheel tops, Geneve stripes) then show a broad sheen instead of reflecting black."""
    tgt = Vector(tgt)
    n = Vector(normal).normalized()
    v = (Vector(cam_loc) - tgt).normalized()
    r = (2 * v.dot(n) * n - v).normalized()
    lt = light('AREA', name, tuple(tgt + r * dist), energy=energy, color=color, size=size, size_y=size_y, coll=coll, target=tuple(tgt))
    vol(lt, 0.0)
    return lt


def cam_basis(cam_loc, tgt):
    f = (Vector(tgt) - Vector(cam_loc)).normalized()
    r = f.cross(Vector((0, 0, 1))).normalized()
    u = r.cross(f)
    return f, r, u


def orbit_pos(tgt, az_deg, elev_deg, dist):
    """camera position around tgt: azimuth measured from -Y toward +X, elevation above horizon."""
    a, e = math.radians(az_deg), math.radians(elev_deg)
    return Vector(tgt) + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist


def gear_wall(name, M, f0, f1, center, size, count, seed=1, facing=(math.radians(90), 0, 0), coll=None, radii=(0.35, 1.4), mats=None):
    """Dense deep-background layer: a handful of gear meshes reused as linked duplicates (cheap), random sizes,
    slight tilts, slow spins with alternating directions. Mesh data is shared, so 60+ wheels cost little."""
    rnd = random.Random(seed)
    mats = mats or [M['brass'], M['gold'], M['steel'], M['rust'], M['brass_big']]
    protos = []
    for k, (t, st, sp, body) in enumerate(((60, 'round', 5, 'spokes'), (36, 'round', 4, 'spokes'), (90, 'trap', 6, 'spokes'),
                                           (24, 'round', 0, 'disk'), (48, 'round', 6, 'spokes'), (72, 'round', 5, 'spokes'))):
        g = gear(f'_{name}_proto{k}', t, 1.0, 0.09, st, body, spokes=max(sp, 1), bend=rnd.choice([0, 0.8]), coll=coll)
        apply_mods(g)
        protos.append((g.data, t))
        bpy.data.objects.remove(g)
    cx, cy, cz = center
    sx, sy, sz = size
    base = Euler(facing).to_matrix()
    out = []
    for i in range(count):
        me, t = rnd.choice(protos)
        r = rnd.uniform(*radii)
        e = bpy.data.objects.new(f'{name}{i}_ax', None)
        link(e, coll)
        e.location = (cx + rnd.uniform(-sx / 2, sx / 2), cy + rnd.uniform(-sy / 2, sy / 2), cz + rnd.uniform(-sz / 2, sz / 2))
        tilt = Euler((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0)).to_matrix()
        e.rotation_euler = (base @ tilt).to_euler()
        o = bpy.data.objects.new(f'{name}{i}', me)
        link(o, coll)
        o.parent = e
        o.scale = (r, r, r * rnd.uniform(0.8, 1.6))
        _objmat(o, rnd.choice(mats))
        w = rnd.choice([-1, 1]) * rnd.uniform(0.6, 1.6) * 0.01 / (t / 48)
        spin_linear(o, 2, f0, f1, rnd.uniform(0, TAU), w)
        out.append(o)
    return out


# ============================================================================ motes
DUST_SCALE = 0.5      # client rule: dust must be sparse


def motes(name, n, center, size, rad=(0.0015, 0.005), seed=1, coll=None, mat=None, cool_frac=0.35, bright_pow=3.0):
    """n tiny octahedra in a box; per-point attributes 'mote' (brightness) and 'tint' (0 warm .. 1 cool)."""
    from mathutils import noise as _nz
    n = max(8, int(n * DUST_SCALE))
    rnd = random.Random(seed)
    verts, faces, br, tn = [], [], [], []
    cx, cy, cz = center
    sx, sy, sz = size
    # clustered, not evenly spread: rejection-sample against a turbulent noise density (drifting wisps/clumps)
    off = Vector((seed * 3.17, seed * 1.91, seed * 2.53))
    freq = 2.2 / max(0.3, min(sx, sy, sz) if min(sx, sy, sz) > 0 else 1.0)
    pts, tries = [], 0
    while len(pts) < n and tries < n * 60:
        tries += 1
        p = Vector((cx + rnd.uniform(-sx / 2, sx / 2), cy + rnd.uniform(-sy / 2, sy / 2), cz + rnd.uniform(-sz / 2, sz / 2)))
        d = _nz.turbulence(p * freq + off, 3, False)
        if rnd.random() < max(0.0, d - 0.35) * 2.2:
            pts.append(p)
    for p in pts:
        r = rnd.uniform(*rad)
        b = 0.35 + rnd.random() ** bright_pow * 0.65
        t = 1.0 if rnd.random() < cool_frac else rnd.uniform(0.0, 0.25)
        i0 = len(verts)
        for d in ((r, 0, 0), (-r, 0, 0), (0, r, 0), (0, -r, 0), (0, 0, r), (0, 0, -r)):
            verts.append((p[0] + d[0], p[1] + d[1], p[2] + d[2]))
            br.append(b); tn.append(t)
        X, x, Y, y, Z, z = range(i0, i0 + 6)
        faces += [(X, Y, Z), (Y, x, Z), (x, y, Z), (y, X, Z), (Y, X, z), (x, Y, z), (y, x, z), (X, y, z)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    a = me.attributes.new('mote', 'FLOAT', 'POINT'); a.data.foreach_set('value', br)
    a = me.attributes.new('tint', 'FLOAT', 'POINT'); a.data.foreach_set('value', tn)
    o = bpy.data.objects.new(name, me)
    link(o, coll)
    if mat:
        set_mat(o, mat)
    try:
        o.visible_shadow = False
    except Exception:
        pass
    return o


def drift(o, f0, f1, vel=(0.0, 0.0, 0.01), spin=0.02):
    """Slow linear drift of a mote cloud (units per frame) + gentle rotation."""
    p0 = Vector(o.location)
    key_vec(o, 'location', [(f0, tuple(p0)), (f1, tuple(p0 + Vector(vel) * (f1 - f0)))], interp='LINEAR')
    fc_key(o, 'rotation_euler', 2, [(f0, 0.0), (f1, spin * (f1 - f0) * 0.05)], interp='LINEAR')


# ============================================================================ animation helpers
def rot_keys(o, axis, fv, interp='LINEAR'):
    fc_key(o, 'rotation_euler', axis, fv, interp=interp)


def spin_linear(o, axis, f0, f1, angle0, rate):
    """rate in rad / frame; keys a bit beyond the range for motion blur."""
    fc_key(o, 'rotation_euler', axis, [(f0 - 2, angle0 - rate * 2), (f1 + 2, angle0 + rate * (f1 - f0 + 2))], interp='LINEAR')


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def look_quat(loc, target, roll=0.0, up=(0, 0, 1)):
    d = (Vector(target) - Vector(loc)).normalized()
    q = d.to_track_quat('-Z', 'Y')
    if roll:
        q = Quaternion(d, roll) @ q
    return q


def key_cam_path(cam, frames, fn):
    """fn(frame) -> (loc Vector, quat). Linear keys per frame (+ half frames for clean motion blur)."""
    cam.rotation_mode = 'QUATERNION'
    prev = None
    for f in frames:
        loc, q = fn(f)
        if prev is not None and prev.dot(q) < 0:
            q.negate()
        cam.location = loc
        cam.rotation_quaternion = q
        cam.keyframe_insert('location', frame=f)
        cam.keyframe_insert('rotation_quaternion', frame=f)
        prev = q.copy()
    set_interp(cam, 'LINEAR')


def catmull(pts, t):
    """uniform Catmull-Rom over list of Vectors, t in [0, len-1]."""
    n = len(pts)
    i = max(0, min(n - 2, int(math.floor(t))))
    u = t - i
    p0 = pts[max(0, i - 1)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(n - 1, i + 2)]
    u2, u3 = u * u, u * u * u
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u3)


def dof_settings(max_px=120.0, jitter=False, overblur=5.0):  # 200 px gather made 1A/1C cost 33-56 s/frame at full res
    """jitter=True: EEVEE jittered DOF (true lens samples) - removes the blocky stair-stepped edges where blurred
    foreground overlaps sharp background (1D/1B), at the cost of some noise that the TAA samples clean up."""
    ee = bpy.context.scene.eevee
    for attr, val in (('bokeh_max_size', max_px), ('bokeh_threshold', 0.8), ('bokeh_neighbor_max', 10.0),
                      ('use_bokeh_jittered', jitter), ('bokeh_overblur', overblur), ('motion_blur_max', 96),
                      ('motion_blur_depth_scale', 100.0)):
        try:
            setattr(ee, attr, val)
        except Exception as e:
            print('[kit] dof attr', attr, e)


def view_dir(cam_loc, tgt, lens, nx, ny, sensor=36.0, aspect=16 / 9):
    """World direction of the ray through normalised screen coords (nx, ny in -1..1) of a camera at cam_loc
    looking at tgt (no roll)."""
    f, r, u = cam_basis(cam_loc, tgt)
    hx = (sensor / 2) / lens
    hy = hx / aspect
    return (f + r * (nx * hx) + u * (ny * hy)).normalized()


def facing_euler(d):
    """Euler that turns local +Z to face back along direction d (wheel faces toward the viewer)."""
    return (-Vector(d)).to_track_quat('Z', 'Y').to_euler()


def haze_window(name, M, N, cam_loc, tgt, lens, coll, ny=0.62, dist=(5.5, 9.0), width=9.0, height=3.5, count=34,
                density=0.2, energy=40000.0, seed=91, radii=(0.35, 1.1), color=(0.45, 0.72, 1.0), light_from=(1, 1), glow=0.1):
    """Cyan 'haze window' seen through the top third of the frame: a deep layer of wheels (dark silhouettes)
    standing in a noisy cyan haze box that is lit by a volume-only spot - the img_gears signature (dark brass
    against a luminous blue haze)."""
    d = view_dir(cam_loc, tgt, lens, 0.0, ny)
    c0 = Vector(cam_loc) + d * ((dist[0] + dist[1]) / 2)
    depth = dist[1] - dist[0]
    f, r, u = cam_basis(cam_loc, tgt)
    fe = facing_euler(d)
    # gear wall: build it axis aligned around the centre, then orient the parents to face the camera ray
    walls = gear_wall(name + 'W', M, 1, N, (0, 0, 0), (width, height, depth * 0.6), count, seed=seed, coll=coll, radii=radii,
                      facing=(0, 0, 0))
    root = bpy.data.objects.new(name + '_root', None)
    link(root, coll)
    root.location = c0
    root.rotation_euler = fe
    for o in walls:
        o.parent.parent = root
    hb = haze_glow(name + 'Haze', tuple(c0), (width * 1.4, depth * 1.6, height * 1.6), density, (0.3, 0.62, 1.0), glow, coll=coll)
    hb.rotation_euler = (Vector(d).to_track_quat('Y', 'Z')).to_euler()
    lp = c0 + r * (light_from[0] * 6.0) + u * (light_from[1] * 5.0) + d * 1.5
    lt = light('SPOT', name + 'Shaft', tuple(lp), energy=energy, color=color, spot=34, blend=0.6, coll=coll, target=tuple(c0))
    vol_only(lt)
    return root, hb, lt


def castle_nut(name, r_out, r_in, h, notches, coll, mat, notch_depth=0.35, bev=None):
    """Castellated / knurled centre lock nut (axis +Z, base z=0): polygonal ring with `notches` slots in the top."""
    mb = MB()
    n = notches * 6
    pts_o, pts_i = [], []
    for k in range(n):
        a = TAU * k / n
        pts_o.append((r_out * cos(a), r_out * sin(a)))
        pts_i.append((r_in * cos(a), r_in * sin(a)))
    top = lambda k: h * (1.0 - notch_depth) if (k % 6) in (1, 2) else h
    o0 = mb.loop([(x, y, 0) for x, y in pts_o]); o1 = mb.loop([(x, y, top(k)) for k, (x, y) in enumerate(pts_o)])
    i0 = mb.loop([(x, y, 0) for x, y in pts_i]); i1 = mb.loop([(x, y, top(k)) for k, (x, y) in enumerate(pts_i)])
    mb.bridge(o0, o1); mb.bridge(i1, i0); mb.bridge(o1, i1); mb.bridge(i0, o0)
    o = mb.build(name, coll, sharp=30)
    return finalize(o, mat, bev if bev is not None else r_out * 0.03, 2, 30)


def key_focus(cam, fv, interp='BEZIER'):
    d = cam.data.dof
    for f, v in fv:
        d.focus_distance = v
        d.keyframe_insert('focus_distance', frame=f)
    for fc in fcurves(cam.data):
        for kp in fc.keyframe_points:
            kp.interpolation = interp


def key_energy(lt, fv, interp='BEZIER'):
    for f, v in fv:
        lt.data.energy = v
        lt.data.keyframe_insert('energy', frame=f)
    for fc in fcurves(lt.data):
        for kp in fc.keyframe_points:
            kp.interpolation = interp
