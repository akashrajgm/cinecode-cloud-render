"""ACT III canyon environment toolkit (road, cliffs, scatter, sky, haze, dust, car driving).

Road frame: arc length s along the centerline, lateral offset d (+ = right of travel direction).
Heading theta is measured from +Y turning toward +X (clockwise seen from above), so the car's
yaw is -theta (car forward is +Y).  Cliff rises on the LEFT (d < 0), the canyon drops on the RIGHT.
"""
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector, Matrix, Euler, kdtree
from mathutils import noise as mnoise
from common import *

V = Vector
SUN = V((0.0, 1.0, 0.07)).normalized()   # set per shot with set_sun()
LANE = 1.85


def smooth(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def fbm(x, y, z=0.0, oct=4):
    return mnoise.fractal(V((x, y, z)), 1.0, 2.0, oct, noise_basis='PERLIN_ORIGINAL')


def nz(x, y, z=0.0):
    return mnoise.noise(V((x, y, z)), noise_basis='PERLIN_ORIGINAL')


def set_sun(azimuth_vec, elev_deg=4.5):
    """azimuth_vec: 2D direction (x,y) TOWARD the sun."""
    global SUN
    a = V((azimuth_vec[0], azimuth_vec[1], 0)).normalized()
    e = math.radians(elev_deg)
    SUN = V((a.x * math.cos(e), a.y * math.cos(e), math.sin(e))).normalized()
    return SUN

# ----------------------------------------------------------------------------- road path

DEFAULT_BUMPS = [  # (center s, width, curvature)  k>0 turns right, k<0 turns left
    (-120, 60, 0.006), (40, 50, -0.004), (300, 55, -0.0085), (430, 45, 0.007),
    (545, 26, 0.021), (625, 26, -0.022), (700, 30, 0.012), (900, 60, -0.006),
    (1040, 40, 0.044),   # v11: 3F hairpin (~180 deg right, R ~23 m); downstream of every other shot
]


class Road:
    def __init__(self, s0=-400.0, s1=1300.0, ds=0.5, bumps=DEFAULT_BUMPS):
        n = int(round((s1 - s0) / ds)) + 1
        s = np.linspace(s0, s1, n)
        k = np.zeros(n)
        for c, w, kp in bumps:
            k += kp * np.exp(-((s - c) / w) ** 2)
        th = np.cumsum(k) * ds
        i0 = int(round((0 - s0) / ds))
        th -= th[i0]
        x = np.cumsum(np.sin(th)) * ds
        y = np.cumsum(np.cos(th)) * ds
        x -= x[i0]; y -= y[i0]
        self.s, self.k, self.th, self.x, self.y, self.ds, self.s0 = s, k, th, x, y, ds, s0
        self.z = 0.0
        kd = kdtree.KDTree(n)
        for i in range(n):
            kd.insert((x[i], y[i], 0.0), i)
        kd.balance()
        self.kd = kd

    def at(self, s):
        f = (s - self.s0) / self.ds
        i = int(max(0, min(len(self.s) - 2, math.floor(f))))
        a = f - i
        x = self.x[i] * (1 - a) + self.x[i + 1] * a
        y = self.y[i] * (1 - a) + self.y[i + 1] * a
        th = self.th[i] * (1 - a) + self.th[i + 1] * a
        k = self.k[i] * (1 - a) + self.k[i + 1] * a
        t = V((math.sin(th), math.cos(th), 0))
        r = V((math.cos(th), -math.sin(th), 0))
        return V((x, y, self.z)), t, r, th, k

    def point(self, s, d=0.0, z=0.0):
        P, t, r, th, k = self.at(s)
        return P + r * d + V((0, 0, z))

    def sd(self, x, y):
        """world xy -> (s, signed d)."""
        co, i, dist = self.kd.find((x, y, 0.0))
        s = self.s[i]
        th = self.th[i]
        rx, ry = math.cos(th), -math.sin(th)
        tx, ty = math.sin(th), math.cos(th)
        dx, dy = x - self.x[i], y - self.y[i]
        s += dx * tx + dy * ty
        return s, dx * rx + dy * ry

# ----------------------------------------------------------------------------- cliff / terrain functions

def cliff_H(s):
    return 34.0 + 16.0 * fbm(s * 0.008, 3.1, 0.0, 3) + 4.0 * nz(s * 0.05, 1.7)


# strata bands (shared by every cliff/mesa): list of (z0, z1, inset, hard)
_rng = random.Random(7)
BANDS = []
_z = -60.0
while _z < 200:
    th_ = _rng.uniform(1.2, 5.5)
    BANDS.append((_z, _z + th_, _rng.uniform(-0.4, 1.8), 1.0 if _rng.random() < 0.45 else 0.0))
    _z += th_
_BZ = np.array([b[0] for b in BANDS])


def band_at(z):
    i = int(np.searchsorted(_BZ, z) - 1)
    i = max(0, min(len(BANDS) - 1, i))
    return BANDS[i]


def strata_profile(z, warp):
    """lateral recess (m) of a layered cliff at height z: ledges, undercuts."""
    zw = z + warp
    z0, z1, inset, hard = band_at(zw)
    u = (zw - z0) / max(z1 - z0, 1e-3)
    under = (0.9 if hard else 0.35) * (1.0 - smooth(0.0, 0.22, u))     # undercut below a hard band
    cap = -0.25 * hard * smooth(0.75, 1.0, u)                            # hard band lip
    return inset * (0.5 if hard else 1.0) + under + cap


def cliff_d(s, z):
    """positive distance (m) to the LEFT of the centerline of the cliff face at (s,z)."""
    base = 7.2 + 0.9 * nz(s * 0.06, 0.3) + 3.0 * max(0.0, fbm(s * 0.014, 5.5, 0, 3))
    lean = 0.16 * z + 0.004 * z * z
    warp = 1.6 * nz(s * 0.012, 2.2) + 0.6 * nz(s * 0.05, 9.1)
    gul = 2.2 * max(0.0, nz(s * 0.07, z * 0.015, 4.4)) ** 2 * smooth(2, 10, z)
    rough = 0.35 * fbm(s * 0.35, z * 0.35, 1.0, 3)
    return base + lean + strata_profile(z, warp) + gul + rough


def ground_h(s, d, x, y, H=None):
    n1 = fbm(x * 0.018, y * 0.018, 0.5, 4)
    n2 = nz(x * 0.2, y * 0.2, 1.3)
    if d >= 0:
        if d < 6.8:
            return -0.16 + 0.03 * n2
        t = d - 6.8
        drop = 52.0 * smooth(4.0, 70.0, t + 10.0 * n1)
        # terraces in the slope (strata steps)
        q = drop / 3.5
        terr = (math.floor(q) + smooth(0.55, 1.0, q - math.floor(q))) * 3.5
        drop = drop * 0.45 + terr * 0.55
        floor_roll = 3.0 * fbm(x * 0.01, y * 0.01, 7.0, 3) * smooth(30, 90, t)
        return -0.16 + 0.35 * n2 * min(t / 4, 1) + 1.2 * n1 * min(t / 8, 1) - drop + floor_roll
    dd = -d
    H = cliff_H(s) if H is None else H
    dtop = cliff_d(s, H) + 2.0
    if dd > dtop:
        return H + 1.2 * n1 + 0.25 * n2 - 0.5
    return -0.16 + 0.03 * n2

# ----------------------------------------------------------------------------- mesh helpers

def grid_mesh(name, P, coll=None, smooth_=True, sharp=38.0, uv=None):
    nu, nv = P.shape[0], P.shape[1]
    idx = np.arange(nu * nv).reshape(nu, nv)
    a = idx[:-1, :-1]; b = idx[1:, :-1]; c = idx[1:, 1:]; d = idx[:-1, 1:]
    faces = np.stack([a, b, c, d], -1).reshape(-1, 4)
    me = bpy.data.meshes.new(name)
    me.from_pydata(P.reshape(-1, 3).tolist(), [], faces.tolist())
    if uv is not None:
        lay = me.uv_layers.new(name='UVMap')
        vi = np.zeros(len(me.loops), dtype=np.int64)
        me.loops.foreach_get('vertex_index', vi)
        uvv = uv.reshape(-1, 2)[vi]
        lay.data.foreach_set('uv', uvv.ravel().astype(np.float32))
    me.update()
    o = bpy.data.objects.new(name, me)
    link(o, coll)
    if smooth_:
        shade(o, sharp)
    return o

# ----------------------------------------------------------------------------- materials

def _haze_color_socket(b, base=(0.56, 0.70, 0.66), warm=(1.0, 0.62, 0.36), warm_amt=1.1, strength=1.0):
    """view-direction dependent haze colour (warmer toward the sun)."""
    geo = b.n('ShaderNodeNewGeometry')
    vm = b.n('ShaderNodeVectorMath'); vm.operation = 'DOT_PRODUCT'
    b.link(geo.outputs['Incoming'], vm.inputs[0]); vm.inputs[1].default_value = tuple(-c for c in SUN)
    mu = b.math('MAXIMUM', vm.outputs['Value'], 0.0)
    g = b.math('ADD', b.math('MULTIPLY', b.math('POWER', mu, 5.0), warm_amt),
               b.math('MULTIPLY', b.math('POWER', mu, 40.0), warm_amt * 1.6))
    col = b.mix(base, warm, b.math('MINIMUM', g, 1.0))
    bright = b.math('ADD', strength, b.math('MULTIPLY', g, 0.9))
    m = b.n('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = 'MULTIPLY'
    m.inputs['Factor'].default_value = 1.0
    b.link(col, m.inputs[6])
    cmb = b.n('ShaderNodeCombineColor')
    for ch in ('Red', 'Green', 'Blue'):
        b.link(bright, cmb.inputs[ch])
    b.link(cmb.outputs[0], m.inputs[7])
    return m.outputs[2]


def haze(b, dist=420.0, maxf=0.985, base=None, height_fall=90.0, warm_amt=1.1):
    """Aerial perspective: mix the surface toward a view-dependent haze emission by camera distance."""
    out = b.out
    src = out.inputs['Surface'].links[0].from_socket
    cam = b.n('ShaderNodeCameraData')
    vd = cam.outputs['View Distance']
    geo = b.n('ShaderNodeNewGeometry')
    sep = b.n('ShaderNodeSeparateXYZ'); b.link(geo.outputs['Position'], sep.inputs[0])
    # thinner haze high up (exponential height fog look)
    hf = b.math('EXPONENT', b.math('MULTIPLY', b.math('MAXIMUM', sep.outputs['Z'], 0.0), -1.0 / height_fall))
    dens = b.math('ADD', 0.35, b.math('MULTIPLY', hf, 0.65))
    T = b.math('EXPONENT', b.math('MULTIPLY', b.math('MULTIPLY', vd, dens), -1.0 / dist))
    fac = b.math('MINIMUM', b.math('SUBTRACT', 1.0, T), maxf)
    em = b.n('ShaderNodeEmission')
    b.link(_haze_color_socket(b, base=base or HAZE_BASE, warm_amt=warm_amt), em.inputs['Color'])
    em.inputs['Strength'].default_value = 1.0
    ms = b.n('ShaderNodeMixShader')
    b.link(fac, ms.inputs[0]); b.link(src, ms.inputs[1]); b.link(em.outputs[0], ms.inputs[2])
    b.link(ms.outputs[0], out.inputs['Surface'])
    return b.mat


HAZE_BASE = (0.60, 0.76, 0.69)
HAZE_D = 1000.0


def _pos(b):
    geo = b.n('ShaderNodeNewGeometry')
    return geo.outputs['Position']


def _sep(b, v):
    s = b.n('ShaderNodeSeparateXYZ'); b.link(v, s.inputs[0]); return s


def _scaled(b, v, sc):
    m = b.n('ShaderNodeMapping')
    m.inputs['Scale'].default_value = sc if isinstance(sc, (tuple, list)) else (sc, sc, sc)
    b.link(v, m.inputs['Vector'])
    return m.outputs['Vector']


def strata_color(b, P, z_sock, sat=1.0):
    """1D noise along (warped) height -> layered sandstone/basalt palette."""
    warp = b.noise(_scaled(b, P, 0.03), 1.0, 3, 0.5)
    zw = b.math('ADD', z_sock, b.math('MULTIPLY', b.math('SUBTRACT', warp.outputs['Fac'], 0.5), 5.0))
    n1 = b.n('ShaderNodeTexNoise'); n1.noise_dimensions = '1D'
    n1.inputs['Scale'].default_value = 0.22; n1.inputs['Detail'].default_value = 3.0; n1.inputs['Roughness'].default_value = 0.55
    b.link(zw, n1.inputs['W'])
    n2 = b.n('ShaderNodeTexNoise'); n2.noise_dimensions = '1D'
    n2.inputs['Scale'].default_value = 1.6; n2.inputs['Detail'].default_value = 2.0
    b.link(zw, n2.inputs['W'])
    f = b.math('ADD', b.math('MULTIPLY', n1.outputs['Fac'], 0.8), b.math('MULTIPLY', n2.outputs['Fac'], 0.2))
    # v11: rust/crimson/basalt (v10's bright stops read as peach/flesh rock in a 4-deg dusk)
    ramp = b.ramp(f, [(0.30, (0.035, 0.024, 0.023)), (0.40, (0.13, 0.040, 0.032)), (0.47, (0.23, 0.066, 0.046)),
                      (0.54, (0.31, 0.10, 0.068)), (0.60, (0.38, 0.165, 0.11)), (0.66, (0.25, 0.08, 0.055)),
                      (0.74, (0.08, 0.036, 0.032))])
    return ramp.outputs[0], f


def mat_canyon_rock(name='CanyonRock', scale=1.0, dist=None, steep_only=False, dirt=False, haze_base=None, warm_amt=1.1):
    b = NB(name)
    P = _pos(b)
    if scale != 1.0:
        P = _scaled(b, P, scale)
    sp = _sep(b, P)
    col, f = strata_color(b, P, sp.outputs['Z'])
    vo = b.voronoi(_scaled(b, P, (1.0, 1.0, 0.35)), 1.2)
    vo.feature = 'DISTANCE_TO_EDGE'
    det = b.noise(_scaled(b, P, 1.0), 2.5, 10, 0.62, 0.2)
    # v4: thinner, broken joints (v3 read as a tiled polygon pattern)
    crack = b.math('MULTIPLY', b.maprange(vo.outputs['Distance'], 0.0, 0.022, 1.0, 0.0),
                   b.maprange(det.outputs['Fac'], 0.42, 0.6, 0.0, 1.0))
    fine = b.noise(_scaled(b, P, 1.0), 28.0, 6, 0.7)
    streak = b.noise(_scaled(b, P, (6.0, 6.0, 0.25)), 1.0, 4, 0.6)   # desert varnish streaks
    shade_ = b.maprange(det.outputs['Fac'], 0.3, 0.75, 0.55, 1.15)
    m = b.n('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = 'MULTIPLY'; m.inputs['Factor'].default_value = 1.0
    b.link(col, m.inputs[6])
    cm = b.n('ShaderNodeCombineColor')
    for ch in ('Red', 'Green', 'Blue'):
        b.link(shade_, cm.inputs[ch])
    b.link(cm.outputs[0], m.inputs[7])
    col2 = b.mix(m.outputs[2], (0.03, 0.018, 0.015), b.math('MULTIPLY', b.maprange(streak.outputs['Fac'], 0.55, 0.75, 0, 1), 0.55))
    col3 = b.mix(col2, (0.02, 0.012, 0.01), b.math('MULTIPLY', crack, 0.3))   # v8: joints read as a polygon net up close
    if dirt:
        geo = b.n('ShaderNodeNewGeometry')
        nsep = _sep(b, geo.outputs['Normal'])
        flat = b.maprange(nsep.outputs['Z'], 0.72, 0.9, 0.0, 1.0)
        dn = b.noise(_scaled(b, P, 1.0), 0.35, 6, 0.6)
        dcol = b.ramp(dn.outputs['Fac'], [(0.35, (0.16, 0.055, 0.03)), (0.55, (0.33, 0.12, 0.06)), (0.7, (0.42, 0.20, 0.11))])
        pebv = b.voronoi(_scaled(b, P, 1.0), 9.0)
        dcol2 = b.mix(dcol.outputs[0], (0.07, 0.04, 0.035), b.maprange(pebv.outputs['Distance'], 0.0, 0.25, 0.6, 0.0))
        col3 = b.mix(col3, dcol2, flat)
    b.set('Base Color', col3)
    b.set('Roughness', b.maprange(fine.outputs['Fac'], 0.3, 0.7, 0.78, 0.95))
    h = b.math('ADD', b.math('MULTIPLY', fine.outputs['Fac'], 0.25), b.math('MULTIPLY', crack, -0.25))
    h = b.math('ADD', h, b.math('MULTIPLY', det.outputs['Fac'], 0.8))
    b.set('Normal', b.bump(h, 0.55, 0.12))
    haze(b, dist or HAZE_D, base=haze_base, warm_amt=warm_amt)
    return b.mat


def mat_boulder(name='Boulder'):
    """v4: instanced boulders/pebbles. Object-space (per-instance) colour so they don't inherit the cliff
    strata stripes; dark varnished sandstone/basalt mix, chipped facets, dust settled on top."""
    b = NB(name)
    tc = b.n('ShaderNodeTexCoord')
    oi = b.n('ShaderNodeObjectInfo')
    P = tc.outputs['Object']
    off = b.n('ShaderNodeVectorMath'); off.operation = 'SCALE'
    b.link(oi.outputs['Random'], off.inputs['Scale']); off.inputs[0].default_value = (13.0, 29.0, 7.0)
    Pv = b.n('ShaderNodeVectorMath'); Pv.operation = 'ADD'
    b.link(P, Pv.inputs[0]); b.link(off.outputs['Vector'], Pv.inputs[1])
    P = Pv.outputs[0]
    n1 = b.noise(P, 2.2, 8, 0.62, 0.3)
    n2 = b.noise(P, 14.0, 5, 0.7)
    rn = b.noise(P, 1.5, 3, 0.55, 1.5)   # v11: fracture ridges from |noise-0.5| (no voronoi hex net)
    hue = b.ramp(oi.outputs['Random'], [(0.0, (0.07, 0.03, 0.022)), (0.45, (0.22, 0.075, 0.04)), (0.8, (0.36, 0.14, 0.07)),
                                        (1.0, (0.16, 0.10, 0.08))])
    shade_ = b.maprange(n1.outputs['Fac'], 0.3, 0.75, 0.45, 1.25)
    m = b.n('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = 'MULTIPLY'; m.inputs['Factor'].default_value = 1.0
    b.link(hue.outputs[0], m.inputs[6])
    cm = b.n('ShaderNodeCombineColor')
    for ch in ('Red', 'Green', 'Blue'):
        b.link(shade_, cm.inputs[ch])
    b.link(cm.outputs[0], m.inputs[7])
    col = m.outputs[2]
    # v8: broken, thin fractures (v7 boulders looked like turtle shells)
    crack = b.math('MULTIPLY', b.maprange(b.math('ABSOLUTE', b.math('SUBTRACT', rn.outputs['Fac'], 0.5)), 0.0, 0.012, 1.0, 0.0),
                   b.maprange(n1.outputs['Fac'], 0.42, 0.6, 0.0, 1.0))
    col = b.mix(col, (0.015, 0.01, 0.008), b.math('MULTIPLY', crack, 0.6))
    geo = b.n('ShaderNodeNewGeometry')
    nz_ = _sep(b, geo.outputs['Normal'])
    top = b.maprange(nz_.outputs['Z'], 0.55, 0.9, 0.0, 1.0)
    col = b.mix(col, (0.42, 0.22, 0.12), b.math('MULTIPLY', top, b.maprange(n2.outputs['Fac'], 0.35, 0.65, 0.2, 0.85)))
    b.set('Base Color', col)
    b.set('Roughness', b.maprange(n2.outputs['Fac'], 0.3, 0.7, 0.62, 0.92))
    n3 = b.noise(P, 5.5, 6, 0.6)
    h = b.math('ADD', b.math('MULTIPLY', n2.outputs['Fac'], 0.30), b.math('MULTIPLY', crack, -0.35))
    h = b.math('ADD', h, b.math('ADD', b.math('MULTIPLY', n1.outputs['Fac'], 0.5), b.math('MULTIPLY', n3.outputs['Fac'], 0.35)))
    b.set('Normal', b.bump(h, 0.75, 0.08))
    haze(b, HAZE_D)
    return b.mat


def mat_road(name='Road'):
    b = NB(name)
    tc = b.n('ShaderNodeTexCoord')
    uvs = _sep(b, tc.outputs['UV'])
    u, v = uvs.outputs['X'], uvs.outputs['Y']
    W = _pos(b)
    au = b.math('ABSOLUTE', u)
    # base asphalt + aggregate
    n_large = b.noise(_scaled(b, W, 1.0), 0.12, 5, 0.6)
    agg = b.voronoi(_scaled(b, W, 1.0), 260.0)
    agg_c = b.maprange(agg.outputs['Distance'], 0.05, 0.35, 1.0, 0.0)
    base = b.ramp(n_large.outputs['Fac'], [(0.3, (0.028, 0.027, 0.027)), (0.7, (0.065, 0.06, 0.058))])
    col = b.mix(base.outputs[0], (0.13, 0.115, 0.11), b.math('MULTIPLY', agg_c, 0.45))
    # wheel tracks (polished, lighter)
    lane_off = b.math('ABSOLUTE', b.math('SUBTRACT', au, LANE))
    trk = b.math('EXPONENT', b.math('MULTIPLY', b.math('POWER', b.math('SUBTRACT', lane_off, 0.85), 2.0), -14.0))
    col = b.mix(col, (0.10, 0.095, 0.09), b.math('MULTIPLY', trk, 0.45))
    # oil drip down lane centre
    oil = b.math('EXPONENT', b.math('MULTIPLY', b.math('POWER', lane_off, 2.0), -6.0))
    oiln = b.noise(_scaled(b, W, 1.0), 0.8, 3, 0.5)
    col = b.mix(col, (0.012, 0.012, 0.012), b.math('MULTIPLY', oil, b.maprange(oiln.outputs['Fac'], 0.45, 0.7, 0.0, 0.7)))
    # patches (repair rectangles via voronoi cells)
    pv = b.voronoi(_scaled(b, W, (0.10, 0.06, 0.1)), 1.0)
    pv.inputs['Randomness'].default_value = 1.0
    pr = b.n('ShaderNodeSeparateColor'); b.link(pv.outputs['Color'], pr.inputs[0])
    patch = b.maprange(pr.outputs['Red'], 0.78, 0.8, 0.0, 1.0)
    col = b.mix(col, (0.018, 0.018, 0.019), b.math('MULTIPLY', patch, 0.85))
    # cracks
    cw = b.noise(_scaled(b, W, 1.0), 1.5, 2, 0.5)
    cv = b.voronoi(_scaled(b, W, 1.0), 0.45); cv.feature = 'DISTANCE_TO_EDGE'
    crack = b.math('MULTIPLY', b.maprange(cv.outputs['Distance'], 0.0, 0.025, 1.0, 0.0),
                   b.maprange(cw.outputs['Fac'], 0.48, 0.6, 0.0, 1.0))
    edgecr = b.maprange(au, 3.2, 3.9, 0.0, 1.0)
    crack = b.math('MAXIMUM', crack, b.math('MULTIPLY', edgecr, b.maprange(cv.outputs['Distance'], 0.0, 0.06, 1.0, 0.0)))
    col = b.mix(col, (0.006, 0.006, 0.006), crack)
    # paint: edge lines + dashed centre line, worn
    edge = b.maprange(b.math('ABSOLUTE', b.math('SUBTRACT', au, 3.42)), 0.07, 0.085, 1.0, 0.0)
    dash = b.maprange(b.math('FRACT', b.math('DIVIDE', v, 9.0)), 0.0, 0.35, 1.0, 1.0)
    dashm = b.math('LESS_THAN', b.math('FRACT', b.math('DIVIDE', v, 9.0)), 0.36)
    cen = b.math('MULTIPLY', b.maprange(au, 0.06, 0.075, 1.0, 0.0), dashm)
    wear = b.noise(_scaled(b, W, (1.0, 1.0, 1.0)), 6.0, 6, 0.65)
    wearm = b.maprange(wear.outputs['Fac'], 0.38, 0.6, 0.15, 1.0)
    wear2 = b.math('MULTIPLY', wearm, b.maprange(agg_c, 0.0, 1.0, 1.0, 0.5))
    paint = b.math('MULTIPLY', b.math('MAXIMUM', edge, cen), wear2)
    pcol = b.mix((0.72, 0.68, 0.58), (0.80, 0.56, 0.20), cen)
    col = b.mix(col, pcol, paint)
    # dust film near edges
    dust = b.maprange(au, 2.6, 3.9, 0.0, 0.55)
    col = b.mix(col, (0.30, 0.15, 0.09), b.math('MULTIPLY', dust, b.maprange(n_large.outputs['Fac'], 0.3, 0.7, 0.4, 1.0)))
    b.set('Base Color', col)
    rough = b.maprange(n_large.outputs['Fac'], 0.3, 0.7, 0.62, 0.86)
    rough = b.math('SUBTRACT', rough, b.math('MULTIPLY', trk, 0.22))
    rough = b.math('SUBTRACT', rough, b.math('MULTIPLY', oil, 0.25))
    b.set('Roughness', rough)
    gr = b.noise(_scaled(b, W, 1.0), 150.0, 2, 0.5)
    h = b.math('ADD', b.math('MULTIPLY', agg_c, 0.6), b.math('MULTIPLY', gr.outputs['Fac'], 0.3))
    h = b.math('SUBTRACT', h, b.math('MULTIPLY', crack, 1.5))
    h = b.math('ADD', h, b.math('MULTIPLY', paint, 0.4))
    b.set('Normal', b.bump(h, 0.45, 0.004))
    haze(b, HAZE_D)
    return b.mat


def mat_gravel(name='Gravel'):
    b = NB(name)
    W = _pos(b)
    v1 = b.voronoi(_scaled(b, W, 1.0), 14.0)
    v2 = b.voronoi(_scaled(b, W, 1.0), 45.0)
    n = b.noise(_scaled(b, W, 1.0), 0.5, 5, 0.6)
    pr = b.n('ShaderNodeSeparateColor'); b.link(v1.outputs['Color'], pr.inputs[0])
    base = b.ramp(pr.outputs['Red'], [(0.0, (0.10, 0.05, 0.035)), (0.5, (0.26, 0.13, 0.08)), (0.8, (0.34, 0.20, 0.13)), (1.0, (0.05, 0.04, 0.035))])
    col = b.mix(base.outputs[0], (0.04, 0.025, 0.02), b.maprange(v1.outputs['Distance'], 0.0, 0.3, 0.8, 0.0))
    col = b.mix(col, (0.36, 0.17, 0.09), b.maprange(n.outputs['Fac'], 0.45, 0.7, 0.0, 0.6))
    b.set('Base Color', col)
    b.set('Roughness', 0.9)
    h = b.math('ADD', b.maprange(v1.outputs['Distance'], 0.0, 0.5, 0.0, 1.0), b.math('MULTIPLY', v2.outputs['Distance'], 0.4))
    b.set('Normal', b.bump(h, 0.8, 0.03))
    haze(b, HAZE_D)
    return b.mat


def mat_scrub(name='Scrub'):
    b = NB(name)
    W = _pos(b)
    oi = b.n('ShaderNodeObjectInfo')
    n = b.noise(_scaled(b, W, 1.0), 4.0, 4, 0.6)
    col = b.ramp(b.math('ADD', b.math('MULTIPLY', n.outputs['Fac'], 0.6), b.math('MULTIPLY', oi.outputs['Random'], 0.4)),
                 [(0.25, (0.07, 0.045, 0.03)), (0.5, (0.16, 0.12, 0.06)), (0.7, (0.24, 0.20, 0.10)), (0.9, (0.32, 0.17, 0.08))])
    b.set('Base Color', col.outputs[0]).set('Roughness', 0.8)
    try:
        b.set('Subsurface Weight', 0.15)
        b.set('Subsurface Radius', (0.2, 0.1, 0.05))
    except Exception:
        pass
    haze(b, HAZE_D)
    return b.mat


def mat_post(name='Post'):
    b = NB(name)
    tc = b.n('ShaderNodeTexCoord')
    sp = _sep(b, tc.outputs['Object'])
    band = b.math('MULTIPLY', b.math('GREATER_THAN', sp.outputs['Z'], 0.72), b.math('LESS_THAN', sp.outputs['Z'], 0.86))
    dn = b.noise(tc.outputs['Object'], 12.0, 4, 0.6)
    dirt = b.maprange(sp.outputs['Z'], 0.0, 0.35, 0.8, 0.0)
    col = b.mix((0.62, 0.60, 0.56), (0.02, 0.02, 0.02), band)
    col = b.mix(col, (0.28, 0.13, 0.07), b.math('MULTIPLY', dirt, b.maprange(dn.outputs['Fac'], 0.3, 0.7, 0.4, 1.0)))
    b.set('Base Color', col).set('Roughness', 0.45)
    haze(b, HAZE_D)
    return b.mat


def mat_sky_world(sun=None, strength=1.0, fog=0.0018, fog_col=(0.85, 0.62, 0.45), aniso=0.65):
    sun = sun or SUN
    w = bpy.data.worlds.new('CanyonSky')
    bpy.context.scene.world = w
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    N, L = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputWorld')
    bg = N.new('ShaderNodeBackground')
    tc = N.new('ShaderNodeTexCoord')
    nrm = N.new('ShaderNodeVectorMath'); nrm.operation = 'NORMALIZE'
    L.new(tc.outputs['Generated'], nrm.inputs[0])
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(nrm.outputs['Vector'], sep.inputs[0])
    rmp = N.new('ShaderNodeValToRGB')
    els = rmp.color_ramp.elements
    # v3: mint/teal dusk (refs): bright cream-mint horizon band, saturated teal toward the zenith
    stops = [(0.0, (0.20, 0.13, 0.10)), (0.48, (0.55, 0.45, 0.36)), (0.503, (0.98, 0.92, 0.78)),
             (0.525, (0.70, 0.92, 0.80)), (0.60, (0.36, 0.75, 0.64)), (0.75, (0.16, 0.50, 0.46)), (1.0, (0.06, 0.26, 0.28))]
    while len(els) > 2:
        els.remove(els[-1])
    for i, (p, c) in enumerate(stops):
        e = els[i] if i < 2 else els.new(p)
        e.position = p; e.color = (*c, 1)
    zr = N.new('ShaderNodeMapRange'); zr.inputs['From Min'].default_value = -1; zr.inputs['From Max'].default_value = 1
    zr.inputs['To Min'].default_value = 0; zr.inputs['To Max'].default_value = 1
    L.new(sep.outputs['Z'], zr.inputs['Value']); L.new(zr.outputs['Result'], rmp.inputs['Fac'])
    dot = N.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
    L.new(nrm.outputs['Vector'], dot.inputs[0]); dot.inputs[1].default_value = tuple(sun)
    mu = N.new('ShaderNodeMath'); mu.operation = 'MAXIMUM'; L.new(dot.outputs['Value'], mu.inputs[0]); mu.inputs[1].default_value = 0.0

    def pw(e, k):
        p = N.new('ShaderNodeMath'); p.operation = 'POWER'; L.new(mu.outputs[0], p.inputs[0]); p.inputs[1].default_value = e
        m = N.new('ShaderNodeMath'); m.operation = 'MULTIPLY'; L.new(p.outputs[0], m.inputs[0]); m.inputs[1].default_value = k
        return m.outputs[0]
    glow = N.new('ShaderNodeMath'); glow.operation = 'ADD'
    L.new(pw(4.0, 0.55), glow.inputs[0]); L.new(pw(60.0, 2.2), glow.inputs[1])
    glow2 = N.new('ShaderNodeMath'); glow2.operation = 'ADD'
    L.new(glow.outputs[0], glow2.inputs[0]); L.new(pw(400.0, 6.0), glow2.inputs[1])
    disc = N.new('ShaderNodeMath'); disc.operation = 'GREATER_THAN'; L.new(dot.outputs['Value'], disc.inputs[0])
    disc.inputs[1].default_value = math.cos(math.radians(0.6))
    discm = N.new('ShaderNodeMath'); discm.operation = 'MULTIPLY'; L.new(disc.outputs[0], discm.inputs[0]); discm.inputs[1].default_value = 30.0
    gsum = N.new('ShaderNodeMath'); gsum.operation = 'ADD'; L.new(glow2.outputs[0], gsum.inputs[0]); L.new(discm.outputs[0], gsum.inputs[1])
    # horizon emphasis for glow
    hz = N.new('ShaderNodeMapRange'); hz.inputs['From Min'].default_value = 0.0; hz.inputs['From Max'].default_value = 0.45
    hz.inputs['To Min'].default_value = 1.0; hz.inputs['To Max'].default_value = 0.25
    L.new(sep.outputs['Z'], hz.inputs['Value'])
    gm = N.new('ShaderNodeMath'); gm.operation = 'MULTIPLY'; L.new(gsum.outputs[0], gm.inputs[0]); L.new(hz.outputs['Result'], gm.inputs[1])
    warm = N.new('ShaderNodeMix'); warm.data_type = 'RGBA'; warm.blend_type = 'MULTIPLY'; warm.inputs['Factor'].default_value = 1.0
    warm.inputs[6].default_value = (1.0, 0.58, 0.30, 1)
    cmb = N.new('ShaderNodeCombineColor')
    for ch in ('Red', 'Green', 'Blue'):
        L.new(gm.outputs[0], cmb.inputs[ch])
    L.new(cmb.outputs[0], warm.inputs[7])
    add = N.new('ShaderNodeMix'); add.data_type = 'RGBA'; add.blend_type = 'ADD'; add.inputs['Factor'].default_value = 1.0
    L.new(rmp.outputs['Color'], add.inputs[6]); L.new(warm.outputs[2], add.inputs[7])
    L.new(add.outputs[2], bg.inputs['Color'])
    # v4: the sky stays bright to the camera but lights the scene less (deeper shadows, the sun carves form)
    lp = N.new('ShaderNodeLightPath')
    sm = N.new('ShaderNodeMapRange')
    sm.inputs['From Min'].default_value = 0.0; sm.inputs['From Max'].default_value = 1.0
    sm.inputs['To Min'].default_value = strength * SKY_LIGHT; sm.inputs['To Max'].default_value = strength
    L.new(lp.outputs['Is Camera Ray'], sm.inputs['Value'])
    L.new(sm.outputs['Result'], bg.inputs['Strength'])
    L.new(bg.outputs['Background'], out.inputs['Surface'])
    # NOTE: no world volume. In EEVEE Next a world volume is infinite and absorbs the whole sky
    # (it rendered the sky black). Atmosphere comes from a bounded fog box (fog_box) instead.
    global FOG
    FOG = (fog, fog_col, aniso)
    return w


FOG = (0.0, (0.85, 0.62, 0.45), 0.6)


FOG_BOX_ON = False   # v3: the 400 m fog box caused froxel checkerboarding; haze lives in the surface shaders


def fog_box(center, size, coll=None):
    dens, col, aniso = FOG
    if dens <= 0 or not FOG_BOX_ON:
        return None
    m = bpy.data.materials.new('FogBox')
    nt = m.node_tree
    if nt is None:
        try:
            m.use_nodes = True
        except Exception:
            pass
        nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    N, L = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputMaterial')
    vp = N.new('ShaderNodeVolumePrincipled')
    tc = N.new('ShaderNodeTexCoord')
    sp = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sp.inputs[0])
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -1.0; mr.inputs['From Max'].default_value = 1.0
    mr.inputs['To Min'].default_value = dens * 1.6; mr.inputs['To Max'].default_value = dens * 0.15
    L.new(sp.outputs['Z'], mr.inputs['Value'])
    L.new(mr.outputs['Result'], vp.inputs['Density'])
    vp.inputs['Color'].default_value = (*col, 1)
    vp.inputs['Anisotropy'].default_value = aniso
    L.new(vp.outputs['Volume'], out.inputs['Volume'])
    o = prim('cube', 'FogBox', loc=center, scale=size, coll=coll, smooth=False)
    set_mat(o, m)
    try:
        o.visible_shadow = False
    except Exception:
        pass
    return o


SKY_LIGHT = 0.3    # v11 (was 0.6: pastel afternoon fill); world lighting factor (camera still sees the full-strength sky)
SUN_GAIN = 1.6     # v4: stronger key vs. the dimmer sky fill -> long readable shadows, grazing form


def sun_lamp(strength=4.5, color=(1.0, 0.45, 0.22), angle=0.9):
    o = light('SUN', 'Sun', (0, 0, 50), energy=strength * SUN_GAIN, color=color, size=angle)
    o.rotation_euler = (-SUN).to_track_quat('-Z', 'Y').to_euler()
    try:
        o.data.shadow_maximum_resolution = 0.002
    except Exception:
        pass
    return o

# ----------------------------------------------------------------------------- instancing

_SCATTER_NG = None


def scatter_group():
    global _SCATTER_NG
    if _SCATTER_NG:
        return _SCATTER_NG
    ng = bpy.data.node_groups.new('Scatter', 'GeometryNodeTree')
    ng.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket(name='Collection', in_out='INPUT', socket_type='NodeSocketCollection')
    ng.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, L = ng.nodes, ng.links
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    ci = N.new('GeometryNodeCollectionInfo'); ci.transform_space = 'ORIGINAL'
    ci.inputs['Separate Children'].default_value = True
    ci.inputs['Reset Children'].default_value = True
    L.new(gi.outputs[1], ci.inputs['Collection'])
    iop = N.new('GeometryNodeInstanceOnPoints')
    L.new(gi.outputs[0], iop.inputs['Points'])
    L.new(ci.outputs[0], iop.inputs['Instance'])
    iop.inputs['Pick Instance'].default_value = True
    for nm, dt, sock in (('rot', 'FLOAT_VECTOR', 'Rotation'), ('scale', 'FLOAT_VECTOR', 'Scale'), ('pick', 'INT', 'Instance Index')):
        na = N.new('GeometryNodeInputNamedAttribute'); na.data_type = dt
        na.inputs['Name'].default_value = nm
        L.new(na.outputs[0], iop.inputs[sock])
    L.new(iop.outputs[0], go.inputs[0])
    _SCATTER_NG = ng
    return ng


def src_collection(name, objs):
    c = bpy.data.collections.new(name)   # NOT linked to the scene: only used as instance source
    for o in objs:
        for uc in list(o.users_collection):
            uc.objects.unlink(o)
        c.objects.link(o)
        o.location = (0, 0, 0)
    return c


def scatter(name, pts, rots, scales, picks, src, coll=None):
    n = len(pts)
    me = bpy.data.meshes.new(name)
    me.vertices.add(n)
    me.vertices.foreach_set('co', np.asarray(pts, dtype=np.float32).ravel())
    a = me.attributes.new('rot', 'FLOAT_VECTOR', 'POINT'); a.data.foreach_set('vector', np.asarray(rots, dtype=np.float32).ravel())
    a = me.attributes.new('scale', 'FLOAT_VECTOR', 'POINT'); a.data.foreach_set('vector', np.asarray(scales, dtype=np.float32).ravel())
    a = me.attributes.new('pick', 'INT', 'POINT'); a.data.foreach_set('value', np.asarray(picks, dtype=np.int32).ravel())
    me.update()
    o = bpy.data.objects.new(name, me)
    link(o, coll)
    mod = o.modifiers.new('Scatter', 'NODES')
    ng = scatter_group().copy()
    ng.name = 'Scatter_' + name
    ci = [n for n in ng.nodes if n.bl_idname == 'GeometryNodeCollectionInfo'][0]
    for l in list(ci.inputs['Collection'].links):
        ng.links.remove(l)
    ci.inputs['Collection'].default_value = src
    mod.node_group = ng
    return o

# ----------------------------------------------------------------------------- props

def rock_mesh(name, r=1.0, seed=0, flat=0.6, sub=3, sharp=1.2, planes=7):
    rng = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    off = V((rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50)))
    sc = V((rng.uniform(0.8, 1.3), rng.uniform(0.8, 1.3), flat * rng.uniform(0.8, 1.2)))
    for v in bm.verts:
        p = v.co.normalized()
        n1 = mnoise.fractal(p * 1.3 + off, 1.0, 2.0, 4)
        # facet planes: crude chiselled look
        f = 1.0 + 0.32 * n1
        for k in range(planes):
            pl = V((math.sin(k * 2.1 + seed), math.cos(k * 1.7 + seed), math.sin(k * 0.9 + seed * 0.3))).normalized()
            dd = p.dot(pl)
            thr = 0.5 + 0.1 * math.sin(k * 3.3 + seed)
            if dd > thr:
                f = min(f, 1.0 - (dd - thr) * sharp)
        v.co = V((p.x * sc.x, p.y * sc.y, p.z * sc.z)) * r * f
    for v in bm.verts:
        if v.co.z < -0.2 * r:
            v.co.z = -0.2 * r + (v.co.z + 0.2 * r) * 0.3
    o = from_bmesh(name, bm, smooth=True, sharp_angle=50)
    return o


def scrub_mesh(name, seed=0, h=0.9, n_br=34):
    """dry desert shrub: tapered twiggy branches + small leaf clumps."""
    rng = random.Random(seed)
    bm = bmesh.new()

    def tube(p0, p1, r0, r1, sides=4):
        d = (p1 - p0)
        if d.length < 1e-4:
            return
        z = d.normalized()
        x = z.orthogonal().normalized(); y = z.cross(x)
        ring0, ring1 = [], []
        for i in range(sides):
            a = 2 * math.pi * i / sides
            o = x * math.cos(a) + y * math.sin(a)
            ring0.append(bm.verts.new(p0 + o * r0)); ring1.append(bm.verts.new(p1 + o * r1))
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))

    def branch(p, d, length, r, depth):
        steps = 3
        for _ in range(steps):
            d = (d + V((rng.uniform(-0.35, 0.35), rng.uniform(-0.35, 0.35), rng.uniform(-0.05, 0.25)))).normalized()
            q = p + d * (length / steps)
            tube(p, q, r, r * 0.75)
            p = q; r *= 0.75
        if depth > 0:
            for _ in range(rng.randint(2, 3)):
                branch(p, (d + V((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0, 0.6)))).normalized(),
                       length * 0.6, r, depth - 1)
        else:
            # leaf clump: a few small flat quads
            for _ in range(rng.randint(12, 18)):   # v11: many 1-2 cm leaves (3 big quads read as a flock of birds)
                c = p + V((rng.uniform(-.07, .07), rng.uniform(-.07, .07), rng.uniform(-.04, .05)))
                s_ = rng.uniform(0.006, 0.011)
                a = rng.uniform(0, math.pi)
                vx = V((math.cos(a), math.sin(a), rng.uniform(-.3, .3))) * s_
                vy = V((-math.sin(a), math.cos(a), rng.uniform(-.2, .5))) * s_
                vs = [bm.verts.new(c - vx - vy), bm.verts.new(c + vx - vy), bm.verts.new(c + vx + vy), bm.verts.new(c - vx + vy)]
                bm.faces.new(vs)
    for i in range(rng.randint(5, 8)):
        a = rng.uniform(0, 2 * math.pi)
        d = V((math.cos(a) * 0.6, math.sin(a) * 0.6, 1.0)).normalized()
        branch(V((rng.uniform(-.05, .05), rng.uniform(-.05, .05), 0)), d, h * rng.uniform(0.5, 0.8), 0.018, 2)
    o = from_bmesh(name, bm, smooth=False)
    return o


def grass_mesh(name, seed=0, n=26, h=0.35):
    rng = random.Random(seed)
    bm = bmesh.new()
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0, 0.08)
        base = V((math.cos(a) * r, math.sin(a) * r, 0))
        lean = V((math.cos(a), math.sin(a), 0)) * rng.uniform(0.05, 0.25)
        hh = h * rng.uniform(0.5, 1.2)
        w = 0.006
        side = V((-math.sin(a), math.cos(a), 0)) * w
        tip = base + lean + V((0, 0, hh))
        mid = base + lean * 0.4 + V((0, 0, hh * 0.55))
        v0 = bm.verts.new(base - side); v1 = bm.verts.new(base + side)
        v2 = bm.verts.new(mid + side * 0.6); v3 = bm.verts.new(mid - side * 0.6); v4 = bm.verts.new(tip)
        bm.faces.new((v0, v1, v2, v3)); bm.faces.new((v3, v2, v4))
    return from_bmesh(name, bm, smooth=False)


def post_mesh(name):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.11, 0.11, 1.0), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0, 0.5), verts=bm.verts)
    o = from_bmesh(name, bm, smooth=False)
    bevel(o, 0.012, 2, 40)
    return o


def reflector_mesh(name):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.07, 0.012, 0.13), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, -0.058, 0.79), verts=bm.verts)
    return from_bmesh(name, bm, smooth=False)


def stud_mesh(name):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.1, 0.1, 0.03), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0, 0.012), verts=bm.verts)
    o = from_bmesh(name, bm, smooth=False)
    bevel(o, 0.008, 1, 40)
    return o


def chevron_sign(name, coll=None):
    """black plate with red/white chevrons on a post."""
    b = NB(name + 'M')
    tc = b.n('ShaderNodeTexCoord')
    sp = _sep(b, tc.outputs['Object'])
    x = sp.outputs['X']; z = sp.outputs['Z']
    ch = b.math('FRACT', b.math('ADD', b.math('MULTIPLY', x, 2.2), b.math('MULTIPLY', b.math('ABSOLUTE', b.math('SUBTRACT', z, 1.3)), 2.2)))
    m = b.math('LESS_THAN', ch, 0.45)
    col = b.mix((0.5, 0.012, 0.01), (0.75, 0.72, 0.68), m)
    b.set('Base Color', col).set('Roughness', 0.35)
    b.set('Emission Color', col).set('Emission Strength', 0.25)
    haze(b, HAZE_D)
    plate = prim('cube', name, loc=(0, 0, 1.3), scale=(0.6, 0.03, 0.42), coll=coll, smooth=False)
    set_mat(plate, b.mat)
    bevel(plate, 0.01, 2, 40)
    pole = prim('cylinder', name + 'Pole', loc=(0, 0.04, 0.55), r=0.035, depth=1.1, coll=coll, segments=10)
    set_mat(pole, mat_metal(name + 'Steel', (0.35, 0.34, 0.33), (0.4, 0.7)))
    parent(pole, plate)
    return plate

# ----------------------------------------------------------------------------- environment build

def build_environment(road, s_a, s_b, coll=None, res=1.6, left=90.0, right=230.0, seed=1, scatter_mult=1.0,
                      mesas=True, cam_hint=None):
    """Build road, shoulders, cliff wall, terrain, scatter and distant mesas for s in [s_a, s_b]."""
    t0 = __import__('time').time()
    coll = coll or collection('Canyon')
    rng = random.Random(seed)
    M = {'rock': mat_canyon_rock('CanyonRock'), 'ground': mat_canyon_rock('Ground', dirt=True),
         'road': mat_road(), 'gravel': mat_gravel(), 'scrub': mat_scrub(), 'post': mat_post(),
         'boulder': mat_boulder('Boulder'),
         'far': mat_canyon_rock('FarRock', dist=1400.0, haze_base=(0.17, 0.28, 0.30), warm_amt=0.45)}
    refl = mat_emission('Reflector', (1.0, 0.03, 0.01), 6.0)
    studm = mat_emission('Stud', (1.0, 0.25, 0.04), 3.0)
    # --- road ribbon (u across, v along so normals face up)
    ds = 0.5
    ss = np.arange(s_a, s_b + ds, ds)
    dd = np.array([-3.9, -3.6, -2.4, -1.2, -0.3, 0.0, 0.3, 1.2, 2.4, 3.6, 3.9])
    P = np.zeros((len(dd), len(ss), 3)); UV = np.zeros((len(dd), len(ss), 2))
    for j, s in enumerate(ss):
        C, t, r, th, k = road.at(s)
        for i, d in enumerate(dd):
            p = C + r * d
            crown = 0.06 * (1 - (abs(d) / 3.9) ** 2) - (0.02 if abs(d) > 3.7 else 0.0)
            P[i, j] = (p.x, p.y, p.z + crown + 0.01 * nz(p.x * 0.3, p.y * 0.3))
            UV[i, j] = (d, s)
    road_o = grid_mesh('Road', P, coll, uv=UV, sharp=60)
    set_mat(road_o, M['road'])
    # --- gravel shoulders
    for side, dlist in (('L', [-7.2, -6.2, -5.2, -4.4, -3.75]), ('R', [3.75, 4.6, 5.6, 6.6, 7.4])):
        P = np.zeros((len(dlist), len(ss), 3))
        for j, s in enumerate(ss):
            C, t, r, th, k = road.at(s)
            for i, d in enumerate(dlist):
                p = C + r * d
                e = abs(abs(d) - 3.75)
                P[i, j] = (p.x, p.y, -0.02 - 0.05 * min(e, 1.0) - 0.08 * smooth(2.5, 3.6, e) + 0.03 * nz(p.x * 0.7, p.y * 0.7, 3))
        o = grid_mesh('Shoulder' + side, P, coll, sharp=60)
        set_mat(o, M['gravel'])
    # --- cliff wall (left), param (s, z); u along s, v along z -> normals face the road
    ssw = np.arange(s_a - 10, s_b + 10, 0.7)
    Hs = [cliff_H(s) for s in ssw]
    Hmax = max(Hs)
    zz = np.arange(-1.0, Hmax + 0.001, 0.4)
    P = np.zeros((len(ssw), len(zz) + 4, 3))
    for i, s in enumerate(ssw):
        C, t, r, th, k = road.at(s)
        H = Hs[i]
        for j, z in enumerate(zz):
            zc = min(z, H)
            d = cliff_d(s, zc)
            p = C - r * d
            P[i, j] = (p.x, p.y, zc + (0 if z <= H else 0.0))
        dtop = cliff_d(s, H)
        for k_, extra in enumerate((0.6, 2.0, 5.0, 9.0)):
            p = C - r * (dtop + extra)
            P[i, len(zz) + k_] = (p.x, p.y, H + 0.25 * nz(p.x * 0.2, p.y * 0.2) - 0.1 * k_)
    wall = grid_mesh('CliffWall', P, coll, sharp=40)
    set_mat(wall, M['rock'])
    # --- terrain heightfield (world grid)
    pts = [road.point(s, d) for s in (s_a, (s_a + s_b) / 2, s_b) for d in (-left, right)]
    pts += [road.point(s, 0) for s in np.linspace(s_a, s_b, 12)]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]
    x0, x1 = min(xs) - 20, max(xs) + 20
    y0, y1 = min(ys) - 20, max(ys) + 20
    nx = int((x1 - x0) / res) + 1; ny = int((y1 - y0) / res) + 1
    print(f'[canyon] terrain grid {nx}x{ny}')
    gx = np.linspace(x0, x1, nx); gy = np.linspace(y0, y1, ny)
    P = np.zeros((nx, ny, 3))
    Hcache = {}
    for i, x in enumerate(gx):
        for j, y in enumerate(gy):
            s, d = road.sd(x, y)
            sk = round(s)
            if sk not in Hcache:
                Hcache[sk] = cliff_H(sk)
            P[i, j] = (x, y, ground_h(s, d, x, y, Hcache[sk]))
    terr = grid_mesh('Terrain', P, coll, sharp=50)
    set_mat(terr, M['ground'])
    print(f'[canyon] geometry built {__import__("time").time() - t0:.1f}s')

    def H_at(s):
        sk = round(s)
        if sk not in Hcache:
            Hcache[sk] = cliff_H(sk)
        return Hcache[sk]

    def ground_at(x, y):
        s, d = road.sd(x, y)
        return ground_h(s, d, x, y, H_at(s)), s, d

    # --- scatter sources
    rocks = [rock_mesh(f'RockSrc{i}', 1.0, seed=i, flat=rng.uniform(0.45, 0.8)) for i in range(7)]
    for o in rocks:
        set_mat(o, M['boulder'])
    rock_src = src_collection('RockSrc', rocks)
    peb = [rock_mesh(f'PebSrc{i}', 1.0, seed=20 + i, flat=0.6, sub=1, sharp=0.8) for i in range(5)]
    for o in peb:
        set_mat(o, M['boulder'])
    peb_src = src_collection('PebSrc', peb)
    shr = [scrub_mesh(f'ScrubSrc{i}', seed=i, h=rng.uniform(0.6, 1.1)) for i in range(5)]
    for o in shr:
        set_mat(o, M['scrub'])
    shr_src = src_collection('ScrubSrc', shr)
    grs = [grass_mesh(f'GrassSrc{i}', seed=i) for i in range(4)]
    for o in grs:
        set_mat(o, M['scrub'])
    grs_src = src_collection('GrassSrc', grs)
    post = post_mesh('PostSrc'); set_mat(post, M['post'])
    rf = reflector_mesh('ReflSrc'); set_mat(rf, refl)
    post_src = src_collection('PostSrc', [post, rf])
    stud = stud_mesh('StudSrc'); set_mat(stud, studm)
    stud_src = src_collection('StudSrc', [stud])

    def sample(count, dmin, dmax, smin=s_a, smax=s_b, bias=1.0):
        out = []
        tries = 0
        while len(out) < count and tries < count * 6:
            tries += 1
            s = rng.uniform(smin, smax)
            u = rng.random() ** bias
            d = dmin + (dmax - dmin) * u
            p = road.point(s, d)
            h, s2, d2 = ground_at(p.x, p.y)
            if abs(d2) < 3.95:
                continue
            out.append((p.x, p.y, h, s2, d2))
        return out

    m = scatter_mult
    # boulders: talus at cliff base, verge, slope, canyon floor, plateau
    B = []
    B += [(q, rng.uniform(0.25, 1.1)) for q in sample(int(260 * m), -10.0, -7.0)]
    B += [(q, rng.uniform(0.15, 0.6)) for q in sample(int(180 * m), 4.5, 12.0)]
    B += [(q, rng.uniform(0.6, 3.5)) for q in sample(int(420 * m), 12.0, right, bias=1.6)]
    B += [(q, rng.uniform(0.5, 2.5)) for q in sample(int(160 * m), -left, -20.0)]
    pts, rots, scs, picks = [], [], [], []
    for (x, y, h, s, d), sc in B:
        if -20 < d < -6.9:   # talus must sit in front of the wall
            pass
        pts.append((x, y, h - 0.15 * sc)); rots.append((rng.uniform(-.2, .2), rng.uniform(-.2, .2), rng.uniform(0, 6.3)))
        scs.append((sc, sc * rng.uniform(0.8, 1.2), sc)); picks.append(rng.randrange(len(rocks)))
    scatter('Boulders', pts, rots, scs, picks, rock_src, coll)
    # v5: rubble + scrub on the cliff's up-facing ledges (the wall read as smooth sandstone from above)
    wm = wall.data
    nP = len(wm.polygons)
    nrm = np.zeros(nP * 3, dtype=np.float32); wm.polygons.foreach_get('normal', nrm); nrm = nrm.reshape(-1, 3)
    cen = np.zeros(nP * 3, dtype=np.float32); wm.polygons.foreach_get('center', cen); cen = cen.reshape(-1, 3)
    ledge = np.where((nrm[:, 2] > 0.55) & (cen[:, 2] > 1.5))[0]
    pts, rots, scs, picks = [], [], [], []
    spts, srots, sscs, spicks = [], [], [], []
    for idx in ledge:
        u = rng.random()
        if u < 0.45 * m:
            x, y, z = cen[idx]
            sc_ = rng.uniform(0.12, 0.55) if rng.random() < 0.85 else rng.uniform(0.6, 1.3)
            pts.append((x + rng.uniform(-.3, .3), y + rng.uniform(-.3, .3), z - 0.1 * sc_))
            rots.append((rng.uniform(-.3, .3), rng.uniform(-.3, .3), rng.uniform(0, 6.3)))
            scs.append((sc_, sc_ * rng.uniform(0.8, 1.2), sc_ * 0.8)); picks.append(rng.randrange(len(rocks)))
        elif u < 0.53 * m:
            x, y, z = cen[idx]
            sc_ = rng.uniform(0.5, 1.1)
            spts.append((x, y, z - 0.05)); srots.append((0, 0, rng.uniform(0, 6.3)))
            sscs.append((sc_, sc_, sc_)); spicks.append(rng.randrange(len(shr)))
    if pts:
        scatter('LedgeRubble', pts, rots, scs, picks, rock_src, coll)
    if spts:
        scatter('LedgeScrub', spts, srots, sscs, spicks, shr_src, coll)
    print(f'[canyon] ledges {len(ledge)} -> rubble {len(pts)} scrub {len(spts)}')
    # pebbles: dense on shoulders and verges
    pts, rots, scs, picks = [], [], [], []
    for (x, y, h, s, d) in sample(int(9000 * m), -7.5, 9.0) + sample(int(3000 * m), 9.0, 40.0):
        if abs(d) < 3.9:
            continue
        sc = rng.uniform(0.02, 0.09) * (1.6 if abs(d) > 7 else 1.0)
        pts.append((x, y, h + (0.0 if abs(d) > 7.3 else -0.02))); rots.append((rng.uniform(0, 6.3), rng.uniform(0, 6.3), rng.uniform(0, 6.3)))
        scs.append((sc, sc, sc)); picks.append(rng.randrange(len(peb)))
    # road debris: a few pebbles ON the asphalt near the edges
    for _ in range(int(500 * m)):
        s = rng.uniform(s_a, s_b); d = rng.choice((-1, 1)) * rng.uniform(2.9, 3.85)
        p = road.point(s, d)
        sc = rng.uniform(0.012, 0.04)
        pts.append((p.x, p.y, 0.035)); rots.append((rng.uniform(0, 6.3), 0, rng.uniform(0, 6.3))); scs.append((sc, sc, sc)); picks.append(rng.randrange(len(peb)))
    scatter('Pebbles', pts, rots, scs, picks, peb_src, coll)
    # scrub + grass
    pts, rots, scs, picks = [], [], [], []
    for (x, y, h, s, d) in sample(int(380 * m), 6.0, right * 0.6, bias=1.8) + sample(int(120 * m), -left, -16) + sample(int(60 * m), -7.8, -6.5):
        sc = rng.uniform(0.6, 1.6)
        pts.append((x, y, h - 0.05)); rots.append((rng.uniform(-.15, .15), rng.uniform(-.15, .15), rng.uniform(0, 6.3)))
        scs.append((sc, sc, sc * rng.uniform(0.7, 1.2))); picks.append(rng.randrange(len(shr)))
    scatter('Scrub', pts, rots, scs, picks, shr_src, coll)
    pts, rots, scs, picks = [], [], [], []
    for (x, y, h, s, d) in sample(int(3200 * m), 5.0, 45.0, bias=1.5) + sample(int(500 * m), -7.6, -4.6):
        sc = rng.uniform(0.6, 1.5)
        pts.append((x, y, h - 0.02)); rots.append((rng.uniform(-.2, .2), rng.uniform(-.2, .2), rng.uniform(0, 6.3)))
        scs.append((sc, sc, sc)); picks.append(rng.randrange(len(grs)))
    scatter('Grass', pts, rots, scs, picks, grs_src, coll)
    # guard posts on the drop side + reflectors, studs on the edge lines
    pts, rots, scs, picks = [], [], [], []
    s = s_a - (s_a % 12.0)
    while s < s_b:
        C, t, r, th, k = road.at(s)
        p = C + r * 6.9
        for pk in (0, 1):
            pts.append((p.x, p.y, -0.12)); rots.append((rng.uniform(-.03, .03), rng.uniform(-.03, .03), -th + rng.uniform(-.05, .05)))
            scs.append((1, 1, 1)); picks.append(pk)
        s += 12.0 if abs(k) < 0.01 else 8.0
    scatter('Posts', pts, rots, scs, picks, post_src, coll)
    pts, rots, scs, picks = [], [], [], []
    s = s_a - (s_a % 8.0)
    while s < s_b:
        C, t, r, th, k = road.at(s)
        for d in (-3.42, 3.42):
            p = C + r * d
            pts.append((p.x, p.y, 0.0)); rots.append((0, 0, -th)); scs.append((1, 1, 1)); picks.append(0)
        s += 8.0
    scatter('Studs', pts, rots, scs, picks, stud_src, coll)
    # chevron signs on the outside of tight curves (right side)
    for sc_ in np.arange(s_a, s_b, 16.0):
        C, t, r, th, k = road.at(sc_)
        if abs(k) > 0.012:
            side = 1 if k < 0 else -1   # outside of the curve
            if side < 0:
                continue  # cliff side, no signs
            p = C + r * 7.6
            sg = chevron_sign(f'Chevron{int(sc_)}', coll)
            sg.location = (p.x, p.y, -0.15)
            sg.rotation_euler = (0, 0, -th + (math.pi if k > 0 else 0))
    if mesas:
        build_mesas(road, s_a, s_b, coll, M['far'], rng, cam_hint=cam_hint)
    fc_ = road.point((s_a + s_b) / 2, 20.0, 18.0)
    fog_box((fc_.x, fc_.y, fc_.z), ((s_b - s_a) / 2 + 160, (s_b - s_a) / 2 + 160, 34.0), coll)
    print(f'[canyon] environment total {__import__("time").time() - t0:.1f}s')
    return {'coll': coll, 'mats': M, 'ground_at': ground_at, 'H_at': H_at}


def mesa_mesh(name, center, R, H, seed, coll, nseg=96, dz=1.2):
    rng = random.Random(seed)
    zz = np.arange(-60.0, H + 0.01, dz)
    P = np.zeros((nseg + 1, len(zz) + 3, 3))
    off = rng.uniform(0, 100)
    for i in range(nseg + 1):
        a = 2 * math.pi * (i % nseg) / nseg
        ca, sa = math.cos(a), math.sin(a)
        rr0 = R * (1 + 0.45 * fbm(ca * 1.2 + off, sa * 1.2, 0, 3) + 0.12 * nz(ca * 6 + off, sa * 6))
        # v6: stepped, eroded skyline (v5 read as white boxes): per-angle top height + steeper talus lean
        Hi = H * (0.55 + 0.45 * smooth(-0.35, 0.35, fbm(ca * 1.6 + off, sa * 1.6, 3.3, 3)))
        Hi = Hi - 0.30 * H * max(0.0, nz(ca * 5 + off, sa * 5, 7.7)) + 0.10 * H * nz(ca * 17 + off, sa * 17, 2.2)
        for j, z in enumerate(zz):
            zc = min(z, Hi)
            lean = 0.55 * max(0.0, zc) + (0.0 if zc > 0 else -zc * 0.8)   # v8: talus slopes
            rr = rr0 - lean - strata_profile(zc, 2.0 * nz(a * 2 + off, 0.5)) * 3.0
            rr = rr + 9.0 * nz(ca * 3 + off, sa * 3, zc * 0.03)
            P[i, j] = (center[0] + ca * rr, center[1] + sa * rr, zc + center[2])
        for k_, f in enumerate((0.9, 0.5, 0.0)):
            rr = max(rr0 - 0.55 * Hi, 0.25 * rr0) * f
            P[i, len(zz) + k_] = (center[0] + ca * rr, center[1] + sa * rr, Hi + center[2] + 1.0 * k_ * (1 - f))
    # u = angle, v = height: angle CCW x up -> outward normals
    o = grid_mesh(name, P, coll, sharp=40)
    # v11: weld the angle-0 seam (it shaded as a dark vertical crease = 'telegraph pole' in 3B)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.05)
    bm.to_mesh(o.data); bm.free()
    shade(o, 40)
    return o


def build_mesas(road, s_a, s_b, coll, mat, rng, n=22, cam_hint=None):
    """distant mesas in a ring around the section (validated to stay clear of the road) + far floor."""
    sm = (s_a + s_b) / 2
    cen = road.point(sm, 60.0)
    half = max(150.0, (s_b - s_a) / 2)
    placed = 0
    tries = 0
    while placed < n and tries < 600:
        tries += 1
        a = rng.uniform(0, 2 * math.pi)
        # v4: bigger, taller, farther buttes in layers -> hazy layered silhouettes like the refs
        dist = rng.uniform(half + 520, half + 2800)
        R = rng.uniform(160, 420) * (0.6 + 0.6 * dist / (half + 2800))
        c = cen + V((math.cos(a), math.sin(a), 0)) * dist
        # v7: keep the sun's horizon clear (backlit far buttes read as pale floating boxes there)
        sa_ = math.atan2(SUN.y, SUN.x)
        if abs((a - sa_ + math.pi) % (2 * math.pi) - math.pi) < math.radians(45):
            continue
        if cam_hint is not None:   # v11: keep given view cones clear (3E's pale box at the right edge)
            hints = cam_hint if isinstance(cam_hint, list) else [cam_hint]
            bad = False
            for cp_, cf_, ca_ in hints:
                ac = math.atan2(c.y - cp_[1], c.x - cp_[0]); af = math.atan2(cf_[1], cf_[0])
                bad = bad or abs((ac - af + math.pi) % (2 * math.pi) - math.pi) < math.radians(ca_)
            if bad:
                continue
        co, i, dmin = road.kd.find((c.x, c.y, 0.0))
        if dmin < R * 1.35 + 260:
            continue
        H = rng.uniform(80, 170) * (0.6 + 0.7 * dist / (half + 2800))   # v8: lower ridges, not pale towers
        o = mesa_mesh(f'Mesa{placed}', (c.x, c.y, -52.0), R, H, 100 + placed, coll, nseg=72, dz=2.0)
        set_mat(o, mat)
        try:
            o.visible_shadow = False      # a 4-deg sun must never be blocked by a far mesa
        except Exception:
            pass
        placed += 1
    # far canyon floor: huge hazed plane at the canyon-floor level
    b = NB('FarFloor')
    W = _pos(b)
    nn = b.noise(_scaled(b, W, 1.0), 0.01, 6, 0.6)
    b.set('Base Color', b.ramp(nn.outputs['Fac'], [(0.35, (0.12, 0.04, 0.025)), (0.65, (0.32, 0.12, 0.06))]).outputs[0])
    b.set('Roughness', 0.95)
    haze(b, 900.0)
    fl = prim('plane', 'FarFloor', loc=(cen.x, cen.y, -54.0), scale=(9000, 9000, 1), coll=coll, xs=4, ys=4)
    set_mat(fl, b.mat)
    try:
        fl.visible_shadow = False
    except Exception:
        pass

# ----------------------------------------------------------------------------- driving

def drive(car, road, s_fn, f0, f1, lane=LANE, roll_k=0.0042, pitch_k=0.004, vib=0.004, seed=3, yaw_fn=None,
          lane_fn=None, bump=1.0, steer=True, lift_fn=None):
    """v11: hypercar dynamics. Root follows the road (wheels planted); the sprung body gets
    weight transfer (pitch from longitudinal accel: squat / dive), roll from lateral accel, road-driven
    heave + pitch from per-axle bump profiles (front at s, rear at s - wheelbase), high-freq chatter.
    Front hubs steer atan(WB*k) (+ counter-steer 0.7*slip when yaw_fn gives a drift slip angle).
    yaw_fn(f) -> extra yaw (rad, + = nose left) ; lane_fn(f) -> lateral offset ; lift_fn(f) -> extra body z."""
    root = car['root']
    sprung = car.get('sprung') or car.get('parts', {}).get('sprung')
    root.rotation_mode = 'XYZ'
    R = car.get('wheel_radius', 0.34)
    WB = 2.7
    wsign = -1.0 if car.get('proxy') else 1.0     # car.py: positive X rotation = forward roll
    parts = car.get('parts', {})
    hubs_f = [parts.get('corner_FL'), parts.get('corner_FR')]
    hubs_f = [h for h in hubs_f if h is not None]
    base_rz = {h.name: h.rotation_euler[2] for h in hubs_f}

    def road_bump(s):
        return 0.012 * fbm(s * 0.6, 3.7, seed, 3) + 0.004 * nz(s * 2.3, 1.9, seed)
    for f in range(f0, f1 + 1):
        s = s_fn(f)
        P, t, r, th, k = road.at(s)
        v = (s_fn(f + 0.5) - s_fn(f - 0.5)) * FPS
        acc = (s_fn(f + 1) - 2 * s + s_fn(f - 1)) * FPS * FPS
        a_lat = v * v * k
        roll = max(-0.06, min(0.06, -a_lat * roll_k))
        pitch = max(-0.03, min(0.03, acc * pitch_k))          # + = nose up (squat under power, dive braking)
        ln = lane + (lane_fn(f) if lane_fn else 0.0)
        pos = P + r * ln
        hf, hr = road_bump(s + 1.35) * bump, road_bump(s - 1.35) * bump
        heave = 0.5 * (hf + hr) + vib * (nz(f * 0.9, 0.3, seed) + 0.5 * nz(f * 2.7, 1.1, seed))
        pitch += math.atan2(hf - hr, WB) + vib * 0.5 * nz(f * 1.3, 4.0, seed)
        roll += vib * 0.6 * nz(f * 1.1, 5.0, seed)
        slip = yaw_fn(f) if yaw_fn else 0.0
        lift = lift_fn(f) if lift_fn else 0.0
        if sprung is not None:
            root.location = (pos.x, pos.y, pos.z)
            root.rotation_euler = (0, 0, -th + slip)
            sprung.rotation_mode = 'XYZ'
            sprung.location = (0, 0, heave + lift)
            sprung.rotation_euler = (pitch, roll, 0)
            sprung.keyframe_insert('location', frame=f)
            sprung.keyframe_insert('rotation_euler', frame=f)
        else:
            root.location = (pos.x, pos.y, pos.z + heave)
            root.rotation_euler = (pitch, roll, -th + slip)
        root.keyframe_insert('location', frame=f)
        root.keyframe_insert('rotation_euler', frame=f)
        for w in car['wheels']:
            w.rotation_mode = 'XYZ'
            w.rotation_euler[0] = wsign * (s - s_fn(f0)) / R
            w.keyframe_insert('rotation_euler', index=0, frame=f)
        if steer:
            ang = -math.atan(WB * road.at(s + 2.0)[4]) - 0.7 * slip   # right turn (k>0) = clockwise; drift: counter-steer
            ang = max(-0.6, min(0.6, ang))
            for h in hubs_f:
                h.rotation_euler[2] = base_rz[h.name] + ang
                h.keyframe_insert('rotation_euler', index=2, frame=f)
    set_interp(root, 'LINEAR')
    if sprung is not None:
        set_interp(sprung, 'BEZIER')
    for w in car['wheels']:
        set_interp(w, 'LINEAR')
    for h in hubs_f:
        set_interp(h, 'BEZIER')


def speed_curve(s_ref, f_ref, vkeys, f0=-80, f1=200):
    """s(f) from a speed profile: vkeys [(frame, m/s), ...] smoothstep-eased between keys;
    anchored so that s(f_ref) = s_ref. Returns a callable accepting float frames."""
    vkeys = sorted(vkeys)

    def vel(f):
        if f <= vkeys[0][0]:
            return vkeys[0][1]
        for (fa, va), (fb, vb) in zip(vkeys, vkeys[1:]):
            if f <= fb:
                return va + (vb - va) * smooth(fa, fb, f)
        return vkeys[-1][1]
    step = 0.05
    fs = np.arange(f0, f1 + step, step)
    vs = np.array([vel(f) for f in fs]) / FPS
    cs = np.concatenate([[0.0], np.cumsum((vs[1:] + vs[:-1]) * 0.5 * step)])
    off = s_ref - float(np.interp(f_ref, fs, cs))

    def s_fn(f):
        return float(np.interp(f, fs, cs)) + off
    s_fn.vel = vel
    return s_fn


def car_pose(road, s, lane=LANE):
    P, t, r, th, k = road.at(s)
    return P + r * lane, t, r, th, k

# ----------------------------------------------------------------------------- dust

def mat_dust(name='Dust', density=1.0, color=(0.80, 0.60, 0.42), aniso=0.5, emit=0.04, time_speed=0.35, f0=-60, f1=200):
    m = bpy.data.materials.new(name)
    nt = m.node_tree if m.node_tree else None
    if nt is None:
        try:
            m.use_nodes = True
        except Exception:
            pass
        nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    N, L = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputMaterial')
    vp = N.new('ShaderNodeVolumePrincipled')
    tc = N.new('ShaderNodeTexCoord')
    oi = N.new('ShaderNodeObjectInfo')
    ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; L.new(tc.outputs['Object'], ln.inputs[0])
    fall = N.new('ShaderNodeMapRange'); fall.inputs['From Min'].default_value = 0.15; fall.inputs['From Max'].default_value = 1.0
    fall.inputs['To Min'].default_value = 1.0; fall.inputs['To Max'].default_value = 0.0
    L.new(ln.outputs['Value'], fall.inputs['Value'])
    # flatten bottom (dust hugs the ground)
    off = N.new('ShaderNodeVectorMath'); off.operation = 'SCALE'
    L.new(oi.outputs['Random'], off.inputs['Scale']); off.inputs[0].default_value = (37.0, 53.0, 71.0)
    add = N.new('ShaderNodeVectorMath'); add.operation = 'ADD'
    L.new(tc.outputs['Object'], add.inputs[0]); L.new(off.outputs['Vector'], add.inputs[1])
    tv = N.new('ShaderNodeValue'); tv.name = 'Time'
    tv.outputs[0].default_value = f0 / FPS * time_speed
    tv.outputs[0].keyframe_insert('default_value', frame=f0)
    tv.outputs[0].default_value = f1 / FPS * time_speed
    tv.outputs[0].keyframe_insert('default_value', frame=f1)
    for fc in fcurves(nt):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    n1 = N.new('ShaderNodeTexNoise'); n1.noise_dimensions = '4D'
    n1.inputs['Scale'].default_value = 1.3; n1.inputs['Detail'].default_value = 7.0; n1.inputs['Roughness'].default_value = 0.62
    n1.inputs['Distortion'].default_value = 0.4
    L.new(add.outputs['Vector'], n1.inputs['Vector']); L.new(tv.outputs[0], n1.inputs['W'])
    sh = N.new('ShaderNodeMath'); sh.operation = 'MULTIPLY_ADD'
    L.new(fall.outputs['Result'], sh.inputs[0]); sh.inputs[1].default_value = 0.25; L.new(n1.outputs['Fac'], sh.inputs[2])
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.52; mr.inputs['From Max'].default_value = 0.85
    mr.inputs['To Min'].default_value = 0.0; mr.inputs['To Max'].default_value = 1.0
    L.new(sh.outputs[0], mr.inputs['Value'])
    msk = N.new('ShaderNodeMath'); msk.operation = 'MULTIPLY'
    L.new(mr.outputs['Result'], msk.inputs[0]); L.new(fall.outputs['Result'], msk.inputs[1])
    sc = N.new('ShaderNodeSeparateColor'); L.new(oi.outputs['Color'], sc.inputs[0])
    dm = N.new('ShaderNodeMath'); dm.operation = 'MULTIPLY'
    L.new(msk.outputs[0], dm.inputs[0]); L.new(sc.outputs['Red'], dm.inputs[1])
    dm2 = N.new('ShaderNodeMath'); dm2.operation = 'MULTIPLY'
    L.new(dm.outputs[0], dm2.inputs[0]); dm2.inputs[1].default_value = density
    L.new(dm2.outputs[0], vp.inputs['Density'])
    vp.inputs['Color'].default_value = (*color, 1)
    vp.inputs['Anisotropy'].default_value = aniso
    # self-illumination proxy for multiple scattering (scaled by object colour G)
    em = N.new('ShaderNodeMath'); em.operation = 'MULTIPLY'
    L.new(dm.outputs[0], em.inputs[0]); L.new(sc.outputs['Green'], em.inputs[1])
    em2 = N.new('ShaderNodeMath'); em2.operation = 'MULTIPLY'; L.new(em.outputs[0], em2.inputs[0]); em2.inputs[1].default_value = emit
    vp.inputs['Emission Color'].default_value = (1.0, 0.72, 0.48, 1)
    L.new(em2.outputs[0], vp.inputs['Emission Strength'])
    L.new(vp.outputs['Volume'], out.inputs['Volume'])
    return m


def mat_dust2(name='Dust2', density=1.0, color=(0.82, 0.62, 0.44), aniso=0.45, emit=0.12, f0=-60, f1=200,
              time_speed=0.45, nscale=1.9, detail=5.0, soft=(0.28, 0.68), emit_col=(1.0, 0.70, 0.46), contrast=2.3):
    """Soft billowing dust for a unit ICOSPHERE puff: density is exactly 0 at the mesh surface
    (warped radial smoothstep x 4D fbm), so no box edges and much less froxel aliasing.
    Object colour R = density multiplier, G = emission multiplier (keyframed per puff)."""
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    N, L = nt.nodes, nt.links

    def M(op, a, b=None):
        x = N.new('ShaderNodeMath'); x.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                x.inputs[i].default_value = v
            else:
                L.new(v, x.inputs[i])
        return x.outputs[0]

    def MR(v, a0, a1, b0, b1, smooth=False):
        x = N.new('ShaderNodeMapRange'); x.clamp = True
        if smooth:
            x.interpolation_type = 'SMOOTHSTEP'
        x.inputs['From Min'].default_value = a0; x.inputs['From Max'].default_value = a1
        x.inputs['To Min'].default_value = b0; x.inputs['To Max'].default_value = b1
        L.new(v, x.inputs['Value'])
        return x.outputs['Result']
    out = N.new('ShaderNodeOutputMaterial')
    vp = N.new('ShaderNodeVolumePrincipled')
    tc = N.new('ShaderNodeTexCoord')
    oi = N.new('ShaderNodeObjectInfo')
    tv = N.new('ShaderNodeValue'); tv.name = 'Time'
    tv.outputs[0].default_value = f0 / FPS * time_speed
    tv.outputs[0].keyframe_insert('default_value', frame=f0)
    tv.outputs[0].default_value = f1 / FPS * time_speed
    tv.outputs[0].keyframe_insert('default_value', frame=f1)
    for fc in fcurves(nt):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    off = N.new('ShaderNodeVectorMath'); off.operation = 'SCALE'
    L.new(oi.outputs['Random'], off.inputs['Scale']); off.inputs[0].default_value = (37.0, 53.0, 71.0)
    P = N.new('ShaderNodeVectorMath'); P.operation = 'ADD'
    L.new(tc.outputs['Object'], P.inputs[0]); L.new(off.outputs['Vector'], P.inputs[1])
    # low-frequency warp of the silhouette (billows)
    w = N.new('ShaderNodeTexNoise'); w.noise_dimensions = '4D'
    w.inputs['Scale'].default_value = 0.9; w.inputs['Detail'].default_value = 2.0
    L.new(P.outputs[0], w.inputs['Vector']); L.new(tv.outputs[0], w.inputs['W'])
    wc = N.new('ShaderNodeVectorMath'); wc.operation = 'SUBTRACT'
    L.new(w.outputs['Color'], wc.inputs[0]); wc.inputs[1].default_value = (0.5, 0.5, 0.5)
    ws = N.new('ShaderNodeVectorMath'); ws.operation = 'SCALE'; L.new(wc.outputs[0], ws.inputs[0]); ws.inputs['Scale'].default_value = 1.3
    Q = N.new('ShaderNodeVectorMath'); Q.operation = 'ADD'
    L.new(tc.outputs['Object'], Q.inputs[0]); L.new(ws.outputs[0], Q.inputs[1])
    ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; L.new(Q.outputs[0], ln.inputs[0])
    fall = MR(ln.outputs['Value'], 0.95, 0.15, 0.0, 1.0, smooth=True)
    # hard zero at the mesh surface whatever the warp does
    shell = MR(_len_obj(N, L, tc), 1.0, 0.8, 0.0, 1.0, smooth=True)
    # detail fbm
    PQ = N.new('ShaderNodeVectorMath'); PQ.operation = 'ADD'
    L.new(P.outputs[0], PQ.inputs[0]); L.new(ws.outputs[0], PQ.inputs[1])
    n1 = N.new('ShaderNodeTexNoise'); n1.noise_dimensions = '4D'
    n1.inputs['Scale'].default_value = nscale; n1.inputs['Detail'].default_value = detail
    n1.inputs['Roughness'].default_value = 0.58; n1.inputs['Distortion'].default_value = 0.25
    L.new(PQ.outputs[0], n1.inputs['Vector']); L.new(tv.outputs[0], n1.inputs['W'])
    # combine: fall pushes the threshold, noise carves wisps
    comb = M('ADD', M('MULTIPLY', fall, 0.8), M('MULTIPLY', M('SUBTRACT', n1.outputs['Fac'], 0.5), contrast))
    d = MR(comb, soft[0], soft[1], 0.0, 1.0, smooth=True)
    d = M('MULTIPLY', d, shell)
    sc = N.new('ShaderNodeSeparateColor'); L.new(oi.outputs['Color'], sc.inputs[0])
    dR = M('MULTIPLY', d, sc.outputs['Red'])
    L.new(M('MULTIPLY', dR, density), vp.inputs['Density'])
    vp.inputs['Color'].default_value = (*color, 1)
    vp.inputs['Anisotropy'].default_value = aniso
    vp.inputs['Emission Color'].default_value = (*emit_col, 1)
    L.new(M('MULTIPLY', M('MULTIPLY', dR, sc.outputs['Green']), emit), vp.inputs['Emission Strength'])
    L.new(vp.outputs['Volume'], out.inputs['Volume'])
    return m


def _len_obj(N, L, tc):
    ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'
    L.new(tc.outputs['Object'], ln.inputs[0])
    return ln.outputs['Value']


_PUFF_ME = {}


def puff(name, mat, coll=None):
    """unit icosphere volume container (radius 1): pairs with mat_dust2 (and the old mat_dust)."""
    me = _PUFF_ME.get('m')
    if me is None or me.name not in bpy.data.meshes:
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        me = bpy.data.meshes.new('PuffMesh')
        bm.to_mesh(me); bm.free()
        _PUFF_ME['m'] = me
    o = bpy.data.objects.new(name, me)
    link(o, coll)
    if not o.data.materials:
        o.data.materials.append(mat)
    o.material_slots[0].link = 'OBJECT'
    o.material_slots[0].material = mat
    try:
        o.visible_shadow = True
    except Exception:
        pass
    o.color = (0, 1, 0, 1)
    return o


def dust_trail(road, s_fn, f_spawn0, f_spawn1, mat, coll=None, every=2, life=110, lane=LANE, wind=(0.0, 0.0),
               grow=(4.5, 7.0, 3.2), rise=2.6, skip=None, dens=1.0, seed=11, emis=1.0, lateral=0.0,
               sides=(-1, 1), spread=(-1.5, 2.5)):
    """Spawn volume puffs behind the rear wheels; each puff grows, rises, drifts and fades."""
    """grow = final RADII (lateral, along, up) of the unit-icosphere puffs."""
    rng = random.Random(seed)
    puffs = []
    f = f_spawn0
    i = 0
    while f <= f_spawn1:
        s = s_fn(f) - 2.1
        if skip and skip(s, f):
            f += every
            continue
        P, t, r, th, k = road.at(s)
        lat = lateral(f) if callable(lateral) else lateral
        base = P + r * (lane + rng.choice(sides) * 0.85 * rng.uniform(0.6, 1.1) + lat)
        o = puff(f'Dust{i:03d}', mat, coll)
        o.rotation_euler = (0, 0, -th + rng.uniform(-0.3, 0.3))
        gx, gy, gz = grow[0] * rng.uniform(0.75, 1.25), grow[1] * rng.uniform(0.75, 1.3), grow[2] * rng.uniform(0.7, 1.3)
        wx, wy = wind
        drag = t * rng.uniform(4.0, 8.0)   # pulled along by the car wake
        side = r * rng.uniform(*spread)  # spreads toward the open (canyon) side by default
        keys = [(f - 1, 0.0), (f, 0.02), (f + 3, 0.2), (f + 8, 0.42), (f + 18, 0.65), (f + 36, 0.82), (f + life * 0.6, 0.94), (f + life, 1.0)]
        for fk, u in keys:
            g = 1 - (1 - u) ** 2
            o.location = base + drag * g * 0.6 + side * g + V((wx, wy, 0)) * (fk - f) / FPS + V((0, 0, 0.25 + (gz + rise) * g * 0.75))
            o.scale = (0.35 + gx * g, 0.6 + gy * g, 0.3 + gz * g)
            o.keyframe_insert('location', frame=fk); o.keyframe_insert('scale', frame=fk)
        for fk, dv in ((f - 1, 0.0), (f, 0.0), (f + 2, 1.0 * dens), (f + life * 0.4, 0.7 * dens), (f + life, 0.25 * dens), (f + life * 1.6, 0.0)):
            o.color = (dv, emis, 0, 1)
            o.keyframe_insert('color', frame=fk)
        puffs.append(o)
        f += every
        i += 1
    return puffs


def lens_dust(cam, keys, color=(0.80, 0.60, 0.42), strength=1.0, name='LensDust', layers=2, seed=0, stream=(0.0, 0.0), f_end=120,
              method='BLENDED'):
    """Camera-glued dust sheets (transparent <-> warm emissive, animated fbm alpha).
    keys: [(frame, opacity 0..1)] ; at opacity 1 every layer is solid -> featureless warm tan frame."""
    out = []
    cd = cam.data
    for li in range(layers):
        d = 0.06 + 0.05 * li
        hw = cd.sensor_width / cd.lens * d / 2 * 1.35
        o = prim('plane', f'{name}{li}')
        o.parent = cam; o.matrix_parent_inverse = Matrix.Identity(4)
        o.location = (0, 0, -d)
        o.scale = (hw * 2, hw * 2, 1)
        b = NB(f'{name}M{li}')
        tc = b.n('ShaderNodeTexCoord')
        tv = b.n('ShaderNodeValue')
        tv.outputs[0].default_value = 0.0; tv.outputs[0].keyframe_insert('default_value', frame=0)
        tv.outputs[0].default_value = 3.0 + li; tv.outputs[0].keyframe_insert('default_value', frame=120)
        ov = b.n('ShaderNodeValue')
        for f, v in keys:
            ov.outputs[0].default_value = v
            ov.outputs[0].keyframe_insert('default_value', frame=f)
        mp = b.n('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (3.0 + li, 3.0 + li, 3.0)
        mp.inputs['Location'].default_value = (seed * 3.1 + li * 7.7, li * 2.3, 0)
        if any(stream):   # v11: turbulence streams across the lens along the wind (not a static card)
            mp.inputs['Location'].keyframe_insert('default_value', frame=0)
            mp.inputs['Location'].default_value = (seed * 3.1 + li * 7.7 + stream[0] * (1 + 0.5 * li),
                                                   li * 2.3 + stream[1] * (1 + 0.5 * li), 0)
            mp.inputs['Location'].keyframe_insert('default_value', frame=f_end)
        b.link(tc.outputs['Object'], mp.inputs['Vector'])
        nz_ = b.n('ShaderNodeTexNoise'); nz_.noise_dimensions = '4D'
        nz_.inputs['Scale'].default_value = 1.2; nz_.inputs['Detail'].default_value = 5.0; nz_.inputs['Roughness'].default_value = 0.6
        b.link(mp.outputs['Vector'], nz_.inputs['Vector']); b.link(tv.outputs[0], nz_.inputs['W'])
        for fc in fcurves(b.mat.node_tree):
            lin = ('Mapping' in fc.data_path) or (fc.data_path.startswith('nodes["Value"]'))
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR' if lin else 'BEZIER'
        # alpha = smooth threshold that sweeps from "none" to "all" with opacity
        thr = b.math('SUBTRACT', b.math('ADD', nz_.outputs['Fac'], b.math('MULTIPLY', ov.outputs[0], 1.25)), 0.72)
        a = b.maprange(thr, 0.0, 0.35, 0.0, 1.0)
        a = b.math('MINIMUM', a, b.math('MULTIPLY', ov.outputs[0], 1.6))
        em = b.n('ShaderNodeEmission'); em.inputs['Color'].default_value = (*color, 1)
        shade_ = b.maprange(nz_.outputs['Fac'], 0.3, 0.7, 0.8, 1.15)
        b.link(b.math('MULTIPLY', shade_, strength), em.inputs['Strength'])
        tr = b.n('ShaderNodeBsdfTransparent')
        ms = b.n('ShaderNodeMixShader')
        b.link(a, ms.inputs[0]); b.link(tr.outputs[0], ms.inputs[1]); b.link(em.outputs[0], ms.inputs[2])
        b.link(ms.outputs[0], b.out.inputs['Surface'])
        try:
            b.mat.surface_render_method = method
        except Exception:
            pass
        set_mat(o, b.mat)
        _lens_only(o)
        out.append(o)
    return out


def _lens_only(o):
    """camera-glued FX cards: never in shadows, reflections or light probes (v7: the 3B mirror reflected
    the light-leak card at the lens as a black disc in the middle of the glass)."""
    for a in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter',
              'hide_probe_volume', 'hide_probe_sphere', 'hide_probe_plane'):
        try:
            setattr(o, a, a.startswith('hide'))
        except Exception:
            pass

def grit_spray(road, s_fn, f0, f1, coll=None, every=2, lane=LANE, n_per=90, seed=21, life=14, cam=None, cam_r=1.0,
               size=(0.012, 0.03), side_vel=0.0, lateral=0.0, back=(4.0, 9.0), up=(2.5, 4.0)):
    """Ballistic gravel/grit clouds flung back from the rear tyres (instanced chips, motion-blurred)."""
    rng = random.Random(seed)
    chips = [rock_mesh(f'GritSrc{i}', 1.0, seed=60 + i, flat=0.5, sub=1, sharp=0.9) for i in range(3)]
    gm = mat_principled('Grit', (0.10, 0.05, 0.03), 1.0)   # v11: dark matte grit (no glitter)
    for o in chips:
        set_mat(o, gm)
    src = src_collection('GritSrc', chips)
    out = []
    f = f0
    i = 0
    while f <= f1:
        s = s_fn(f) - 2.5
        P, t, r, th, k = road.at(s)
        pts, rots, scs, picks = [], [], [], []
        for _ in range(n_per):
            side = rng.choice((-0.85, 0.85))
            p = V((side + rng.gauss(0, 0.15), rng.gauss(0, 0.5), rng.uniform(0.0, 0.6) ** 2))
            pts.append(p); rots.append((rng.uniform(0, 6.3), rng.uniform(0, 6.3), rng.uniform(0, 6.3)))
            sz = rng.uniform(*size); scs.append((sz, sz, sz)); picks.append(rng.randrange(3))
        o = scatter(f'Grit{i:03d}', pts, rots, scs, picks, src, coll)
        o.rotation_euler = (0, 0, -th)
        lat = lateral(f) if callable(lateral) else lateral
        base = P + r * (lane + lat) + V((0, 0, 0.15))
        vel = t * rng.uniform(*back) + r * side_vel * rng.uniform(0.5, 1.2) + V((0, 0, rng.uniform(*up)))
        for fk in range(int(f) - 1, int(f) + life + 1):
            tt = max(0.0, (fk - f) / FPS)
            p = base + vel * tt + V((0, 0, -4.9 * tt * tt))
            p.z = max(p.z, 0.02)
            o.location = p
            sc_ = 0.0 if fk < f or fk > f + life - 1 else 1.0 + 1.2 * tt
            if cam is not None:   # cam: callable frame -> world position of the lens
                if (p - V(cam(fk))).length < cam_r + 0.5 * (1 + 3 * tt):
                    sc_ = 0.0   # v11: never fling chips into the lens (glitter specks)
            o.scale = (sc_, sc_ * (1 + 2 * tt), sc_ * 0.8 + 0.2 * sc_)
            o.keyframe_insert('location', frame=fk); o.keyframe_insert('scale', frame=fk)
        set_interp(o, 'LINEAR')
        out.append(o)
        f += every
        i += 1
    return out

def motes(center, radius=14.0, n=600, size=(0.004, 0.012), strength=3.0, coll=None, seed=31, zmax=5.0,
          drift=(0.0, 0.0, 0.0), f0=1, f1=100, name='Motes'):
    """Airborne dust specks around a point: tiny warm emissive chips (bokeh / speed streaks)."""
    rng = random.Random(seed)
    src_o = []
    for i in range(2):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        o = from_bmesh(f'{name}Src{i}', bm, smooth=True)
        src_o.append(o)
    m = NB(name + 'M')
    # v11: client rule - no emissive specks; sunlit, translucent dust grains only
    m.set('Base Color', (0.55, 0.40, 0.28)).set('Roughness', 0.6)
    try:
        m.set('Subsurface Weight', 0.3)
    except Exception:
        pass
    for o in src_o:
        set_mat(o, m.mat)
    src = src_collection(name + 'Src', src_o)
    pts, rots, scs, picks = [], [], [], []
    c = V(center)
    while len(pts) < n:
        p = V((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        if p.length > 1:
            continue
        q = c + V((p.x * radius, p.y * radius, 0.0))
        q.z = c.z + rng.uniform(0.05, zmax) ** 1.0 - 0.0
        s_ = rng.uniform(*size)
        pts.append(q - c); rots.append((0, 0, 0)); scs.append((s_, s_, s_)); picks.append(rng.randrange(2))
    o = scatter(name, pts, rots, scs, picks, src, coll)
    o.location = c
    if any(drift):
        key_vec(o, 'location', [(f0, tuple(c)), (f1, tuple(c + V(drift) * (f1 - f0) / FPS))], interp='LINEAR')
    try:
        o.visible_shadow = False
    except Exception:
        pass
    return o


def light_leak(cam, fx=0.95, fy=-0.3, size=0.55, strength=3.0, color=(1.0, 0.07, 0.04), keys=None, name='Leak'):
    """Soft additive crimson light leak glued to the lens. fx, fy in frame half-extents (-1..1)."""
    d = 0.12
    cd = cam.data
    hw = cd.sensor_width / cd.lens * d / 2
    hh = hw * 9 / 16
    o = prim('plane', name)
    o.parent = cam; o.matrix_parent_inverse = Matrix.Identity(4)
    o.location = (fx * hw, fy * hh, -d)
    o.scale = (hw * size * 2.2, hw * size * 2.2, 1)
    b = NB(name + 'M')
    tc = b.n('ShaderNodeTexCoord')
    g = b.n('ShaderNodeTexGradient'); g.gradient_type = 'SPHERICAL'
    mp = b.n('ShaderNodeMapping'); mp.inputs['Location'].default_value = (0, 0, 0)
    mp.inputs['Scale'].default_value = (2.0, 2.0, 2.0)
    b.link(tc.outputs['Object'], mp.inputs['Vector'])
    b.link(mp.outputs['Vector'], g.inputs['Vector'])
    fall = b.math('POWER', g.outputs['Fac'], 2.2)
    em = b.n('ShaderNodeEmission'); em.inputs['Color'].default_value = (*color, 1)
    sv = b.n('ShaderNodeValue'); sv.outputs[0].default_value = strength
    if keys:
        for f, v in keys:
            sv.outputs[0].default_value = v
            sv.outputs[0].keyframe_insert('default_value', frame=f)
    b.link(b.math('MULTIPLY', fall, sv.outputs[0]), em.inputs['Strength'])
    tr = b.n('ShaderNodeBsdfTransparent')
    ad = b.n('ShaderNodeAddShader')
    b.link(tr.outputs[0], ad.inputs[0]); b.link(em.outputs[0], ad.inputs[1])
    b.link(ad.outputs[0], b.out.inputs['Surface'])
    try:
        b.mat.surface_render_method = 'BLENDED'
    except Exception:
        pass
    set_mat(o, b.mat)
    _lens_only(o)
    return o

# ----------------------------------------------------------------------------- compositor

def comp(bloom=0.45, threshold=0.9, size=0.7, dispersion=0.008, streaks=0.0, streak_thr=6.0):
    tree = compositor(bloom=bloom, threshold=threshold, bloom_size=size, dispersion=dispersion)
    if streaks > 0:
        # thin anamorphic streak on the hottest highlights only (sun disc, light bar)
        try:
            g0 = [n for n in tree.nodes if n.bl_idname == 'CompositorNodeGlare'][0]
            links = [l for l in tree.links if l.from_node == g0]
            g = tree.nodes.new('CompositorNodeGlare')
            for nm, v in (('Type', 'Streaks'), ('Quality', 'High'), ('Threshold', streak_thr), ('Strength', streaks),
                          ('Streaks', 2), ('Streaks Angle', 0.0), ('Fade', 0.88), ('Size', 0.9)):
                try:
                    g.inputs[nm].default_value = v
                except Exception:
                    try:
                        setattr(g, nm.lower().replace(' ', '_'), v)
                    except Exception as e:
                        print('[comp] streak param', nm, e)
            tree.links.new(g0.outputs['Image'], g.inputs['Image'])
            for l in links:
                to = l.to_socket
                tree.links.remove(l)
                tree.links.new(g.outputs['Image'], to)
        except Exception as e:
            print('[comp] streaks failed', e)
    return tree

# ----------------------------------------------------------------------------- proxy car

def proxy_car(coll=None):
    root = empty('CarRoot', coll=coll)
    paint = mat_carpaint('ProxyPaint', (0.012, 0.03, 0.03))
    body = prim('cube', 'ProxyBody', loc=(0, 0, 0.62), scale=(1.95, 4.5, 0.62), coll=coll, smooth=False)
    bevel(body, 0.08, 3, 40); set_mat(body, paint); parent(body, root)
    cab = prim('cube', 'ProxyCab', loc=(0, -0.3, 1.08), scale=(1.5, 2.0, 0.42), coll=coll, smooth=False)
    bevel(cab, 0.12, 3, 40); set_mat(cab, mat_glass('ProxyGlass', (0.05, 0.06, 0.06))); parent(cab, root)
    rubber = mat_rubber('ProxyTyre')
    rim_m = mat_metal('ProxyRim', (0.08, 0.08, 0.085), (0.2, 0.4))
    wheels = []
    R = 0.34
    for (x, y) in ((-0.88, 1.4), (0.88, 1.4), (-0.88, -1.45), (0.88, -1.45)):
        piv = empty(f'WheelPivot_{x:+.0f}{y:+.0f}', loc=(x, y, R), coll=coll)
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=R, radius2=R, depth=0.26)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'Y'))
        w = from_bmesh('ProxyWheel', bm, coll)
        set_mat(w, rubber)
        for sp in range(5):
            spoke = prim('cube', 'Spoke', loc=(0.14 * (1 if x > 0 else -1), 0, 0), scale=(0.02, 0.4, 0.05), coll=coll, smooth=False)
            spoke.rotation_euler = (sp * 2 * math.pi / 5, 0, 0)
            set_mat(spoke, rim_m); parent(spoke, piv)
        w.parent = piv
        parent(piv, root)
        wheels.append(piv)
    redm = mat_emission('ProxyRear', (1.0, 0.02, 0.01), 40.0)
    rear = prim('cube', 'ProxyRearBar', loc=(0, -2.26, 0.92), scale=(1.7, 0.03, 0.05), coll=coll, smooth=False)
    set_mat(rear, redm); parent(rear, root)
    whm = mat_emission('ProxyFront', (1.0, 0.95, 0.9), 30.0)
    for x in (-0.7, 0.7):
        fr = prim('cube', 'ProxyFrontStrip', loc=(x, 2.26, 0.78), scale=(0.45, 0.03, 0.03), coll=coll, smooth=False)
        set_mat(fr, whm); parent(fr, root)
    parts = {}
    for side, x in (('L', -1.05), ('R', 1.05)):
        mh = prim('cube', f'Mirror{side}', loc=(x, 0.95, 1.05), scale=(0.24, 0.1, 0.13), coll=coll, smooth=False)
        bevel(mh, 0.03, 3, 30); set_mat(mh, paint); parent(mh, root)
        parts['mirror_' + side] = mh
    return {'root': root, 'wheels': wheels, 'wheel_radius': R, 'parts': parts, 'mats': {'paint': paint, 'rear': redm, 'front': whm},
            'body': body, 'proxy': True}


def get_car(coll=None):
    """Use film/lib/car.py if it imports and builds; else the proxy."""
    try:
        import importlib
        import car as carmod
        importlib.reload(carmod)
        c = carmod.build_car(coll)
        c['module'] = carmod
        c['proxy'] = False
        patch_car_mats(c)
        print('[canyon] using car.py', list(c.keys()), 'parts:', list(c.get('parts', {}).keys())[:60])
        return c
    except Exception as e:
        import traceback
        traceback.print_exc()
        print('[canyon] car.py unavailable -> proxy:', e)
        return proxy_car(coll)


def car_lights(car, rear=1.0, front=1.0, frame=1):
    if car.get('proxy'):
        return
    mod = car.get('module')
    for which, val in (('rear', rear), ('front', front)):
        try:
            mod.set_light(car, which, val, frame)
        except Exception as e:
            print('[canyon] set_light failed', which, e)


def patch_car_mats(c):
    """v11 (Act III only, car.py untouched): black paint with crisp clearcoat (metallic 0.55 / rough 0.3-0.4
    reflected the cream horizon -> the car read WHITE in 3E), carbon weave as sheen, not an albedo chessboard."""
    for key, fn in (('paint', _patch_paint), ('carbon', _patch_carbon), ('carbon_matte', _patch_carbon)):
        m = c.get('mats', {}).get(key)
        if m is None:
            continue
        try:
            fn(m)
        except Exception as e:
            print('[canyon] patch', key, e)


def _principled(m):
    for n in m.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n


def _patch_paint(m):
    p = _principled(m)
    for nm, lo, hi in (('Metallic', 0.15, 0.15), ('Roughness', 0.15, 0.22)):
        sock = p.inputs[nm]
        if sock.links:
            src = sock.links[0].from_node
            if src.type == 'MAP_RANGE':
                if nm == 'Metallic':   # stripe mask 0..1 -> keep the stripe at 0.2
                    src.inputs['To Min'].default_value = 0.15
                    src.inputs['To Max'].default_value = 0.15
                else:
                    src.inputs['To Min'].default_value = lo
                    src.inputs['To Max'].default_value = hi
        else:
            sock.default_value = lo


def _patch_carbon(m):
    for n in m.node_tree.nodes:
        if n.type == 'MAPPING':
            n.inputs['Scale'].default_value = (260, 260, 260)
        if n.type == 'TEX_CHECKER':
            c1 = n.inputs['Color1'].default_value
            n.inputs['Color2'].default_value = (c1[0] * 0.85, c1[1] * 0.85, c1[2] * 0.85, 1)
