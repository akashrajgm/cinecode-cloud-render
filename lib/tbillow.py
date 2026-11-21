"""Act IV cloudfix (4A/4B): billowy cumulus / stratocumulus deck seen from above.

The old tclouds.cloud_field read as beige SAND DUNES: wide flat domes + smooth fbm ridges on a coarse polar grid
(5-17 m cells), diffuse-lit with hard EEVEE sun self-shadows. billow_field = square-celled log-polar grid (~1.5 m
cells near the focus), round domes at three scales (heads -> puffs -> small puffs = cauliflower crevices), thin lanes
and a few real gaps (ground far below), plus baked per-vertex 'occ' (cavity) and 'shd' (soft heightfield sun shadow)
attributes that the emission-only shader tmat.m_cloud_deck3 uses instead of EEVEE's hard sun shadows.
"""
import math, time
import numpy as np
from mathutils import Vector
from tgeo import *


def _hash2(ix, iy, seed):
    h = (ix * 374761393 + iy * 668265263 + (int(seed) * 1442695041 & 0xffff)) & 0xffffffff
    h = ((h ^ (h >> 13)) * 1274126177) & 0xffffffff
    h = h ^ (h >> 16)
    return (h & 0xffffff).astype(np.float64) / float(0xffffff)


def vnoise(x, y, seed=0):
    """Vectorized 2D value noise in [0, 1]."""
    ix = np.floor(x).astype(np.int64); iy = np.floor(y).astype(np.int64)
    fx = x - ix; fy = y - iy
    ux = fx * fx * (3 - 2 * fx); uy = fy * fy * (3 - 2 * fy)
    a = _hash2(ix, iy, seed); b = _hash2(ix + 1, iy, seed)
    c = _hash2(ix, iy + 1, seed); d = _hash2(ix + 1, iy + 1, seed)
    lo = a + (b - a) * ux
    hi = c + (d - c) * ux
    return lo + (hi - lo) * uy


def vfbm(x, y, octaves=4, seed=0):
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    out = np.zeros_like(x)
    norm = 0.0
    for o in range(octaves):
        f = 2.0 ** o; a = 0.5 ** o
        out += vnoise(x * f + 17.3 * o, y * f - 9.1 * o, seed + 31 * o) * a
        norm += a
    return out / norm


def _sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _box_blur(H, k):
    """Separable box blur, wrap along the angle axis (1), clamp along the radius axis (0)."""
    if k < 1:
        return H.copy()
    P = np.concatenate([H[:, -k:], H, H[:, :k + 1]], 1)
    c = np.cumsum(P, 1)
    A = (c[:, 2 * k + 1:] - c[:, :-(2 * k + 1)]) / (2 * k + 1)
    A = A[:, :H.shape[1]]
    P = np.concatenate([np.repeat(A[:1], k, 0), A, np.repeat(A[-1:], k + 1, 0)], 0)
    c = np.cumsum(P, 0)
    B = (c[2 * k + 1:] - c[:-(2 * k + 1)]) / (2 * k + 1)
    return B[:H.shape[0]]


def billow_field(coll, mat, center=(0, 0), z0=0.0, rmin=150.0, rmax=7000.0, n_ang=1280, seed=1, name='Billows',
                 head_r=(30.0, 120.0), head_h=(0.3, 0.55), grow=1800.0, cover=2.2, head_rmin=None,
                 puffs=((0.2, 0.4, 0.6, 2600.0, 3.0), (0.07, 0.15, 0.65, 1000.0, 3.0)),
                 base=6.0, undulate=7.0, gaps=None, bumps=None, clamp=None, taper=None, sun=None, max_heads=9000):
    """Billowy cumulus/stratocumulus deck (heightfield on a log-polar grid with square cells).
    puffs: [(s_min, s_max, h_ratio, r_max, coverage)] puff radii relative to the local head scale.
    gaps: (scale_m, thr, depth, r_min): large-scale mask where the base layer drops below z0 (shader fades h<0 out).
    taper: (r0, r1, k): relief multiplied by k near the centre (island breach) -> 1 beyond r1.
    sun: unit vector toward the sun for the baked soft self-shadow attribute 'shd'."""
    t0 = time.time()
    rng = np.random.default_rng(seed)
    cx, cy = center
    dth = TAU / n_ang
    n_rad = int(math.log(rmax / rmin) / dth) + 2
    radii = rmin * np.exp(np.arange(n_rad) * dth)
    ang = np.arange(n_ang) * dth
    Rr, A = np.meshgrid(radii, ang, indexing='ij')
    X = cx + Rr * np.cos(A); Y = cy + Rr * np.sin(A)
    smean = 0.5 * (head_r[0] + head_r[1])
    # base layer: gentle undulation (NOT the dominant shape any more)
    H = base + (vfbm(X / 900.0, Y / 900.0, 3, seed) - 0.5) * 2 * undulate
    if gaps:
        gsc, gthr, gdep, grmin = gaps
        H -= _sstep(gthr, gthr + 0.07, vfbm(X / gsc, Y / gsc, 3, seed + 7)) * _sstep(grmin, grmin * 1.4, Rr) * gdep

    def gm_at(px, py):
        if not gaps:
            return np.zeros_like(px)
        rr = np.hypot(px - cx, py - cy)
        return _sstep(gthr, gthr + 0.07, vfbm(px / gsc, py / gsc, 3, seed + 7)) * _sstep(grmin, grmin * 1.4, rr)

    def idx(px, py):
        rr = np.maximum(np.hypot(px - cx, py - cy), rmin)
        i = np.clip(np.round(np.log(rr / rmin) / dth).astype(int), 0, n_rad - 1)
        j = np.round((np.arctan2(py - cy, px - cx) % TAU) / dth).astype(int) % n_ang
        return i, j

    def stamp(px, py, s, top, depth, prof=0.5):
        """max-union a round dome of radius s: crown at `top`, rim at top - depth."""
        rc = math.hypot(px - cx, py - cy)
        if rc + s < rmin:
            return
        i0 = max(0, int(math.log(max(rc - s, rmin) / rmin) / dth) - 1)
        i1 = min(n_rad, int(math.log(max(rc + s, rmin) / rmin) / dth) + 2)
        if i1 <= i0:
            return
        if rc > s * 1.05:
            w = math.asin(min(1.0, s / rc)) * 1.1
            a0 = math.atan2(py - cy, px - cx)
            js = np.arange(int(math.floor((a0 - w) / dth)) - 1, int(math.ceil((a0 + w) / dth)) + 2) % n_ang
        else:
            js = np.arange(n_ang)
        sx = X[i0:i1][:, js]; sy = Y[i0:i1][:, js]
        q = ((sx - px) ** 2 + (sy - py) ** 2) / (s * s)
        m = q < 1.0
        if not m.any():
            return
        sub = H[i0:i1][:, js]
        dome = top - depth + depth * np.clip(1 - q, 0, None) ** prof
        H[i0:i1, js] = np.where(m, np.maximum(sub, dome), sub)

    # ---- heads: radius pdf ~ r / s(r)^2 (even coverage relative to the local scale), fewer in the gaps
    h0 = rmin if head_rmin is None else head_rmin
    rg = np.linspace(h0, rmax, 4000)
    pdf = rg / (smean * (1 + rg / grow)) ** 2
    tot = float(np.sum(pdf) * (rg[1] - rg[0]))
    cdf = np.cumsum(pdf); cdf /= cdf[-1]
    n_heads = int(min(max_heads, cover * 2 * tot))
    hr_ = np.interp(rng.uniform(0, 1, n_heads), cdf, rg)
    ha_ = rng.uniform(0, TAU, n_heads)
    hx = cx + hr_ * np.cos(ha_); hy = cy + hr_ * np.sin(ha_)
    gmh = gm_at(hx, hy)
    keep = rng.uniform(0, 1, n_heads) > gmh * 0.8
    hx, hy, hr_, gmh = hx[keep], hy[keep], hr_[keep], gmh[keep]
    hs = rng.uniform(head_r[0], head_r[1], len(hx)) * (1 + hr_ / grow)
    hh = hs * rng.uniform(head_h[0], head_h[1], len(hx))
    tap = np.ones_like(hr_)
    if taper:
        tap = taper[2] + (1 - taper[2]) * _sstep(taper[0], taper[1], hr_)
    for k in np.argsort(-hs):
        b0 = base - gmh[k] * (gaps[2] if gaps else 0) * 0.6
        stamp(hx[k], hy[k], hs[k], b0 + hh[k] * tap[k], hh[k] * tap[k] + 4.0)
    for (bx, by, br, bh) in (bumps or []):
        stamp(bx, by, br, base + bh, bh + 4.0)
    nh = len(hx)
    # ---- puffs on puffs (cauliflower): each level rides on the current surface
    npf = 0
    for (s0, s1, hrat, rmx, cov) in puffs:
        rg2 = np.linspace(rmin, min(rmx, rmax), 3000)
        sm2 = smean * 0.5 * (s0 + s1)
        pdf2 = rg2 / (sm2 * (1 + rg2 / grow)) ** 2
        t2 = float(np.sum(pdf2) * (rg2[1] - rg2[0]))
        c2 = np.cumsum(pdf2); c2 /= c2[-1]
        n2 = int(min(40000, cov * 2 * t2))
        pr = np.interp(rng.uniform(0, 1, n2), c2, rg2)
        pa = rng.uniform(0, TAU, n2)
        px_ = cx + pr * np.cos(pa); py_ = cy + pr * np.sin(pa)
        ps = rng.uniform(s0, s1, n2) * smean * (1 + pr / grow)
        ii, jj = idx(px_, py_)
        Hc = H[ii, jj].copy()
        tp2 = np.ones_like(pr)
        if taper:
            tp2 = taper[2] + (1 - taper[2]) * _sstep(taper[0], taper[1], pr)
        hv = rng.uniform(0.7, 1.1, n2)
        for k in range(n2):
            if Hc[k] < base + 1.5:          # puffs only grow on clouds, not in the lanes / gaps
                continue
            hgt = ps[k] * hrat * hv[k] * tp2[k]
            stamp(px_[k], py_[k], ps[k], Hc[k] + hgt * 0.75, hgt * 1.05)
            npf += 1
    # fine organic wobble (keeps the domes from looking like perfect spheres)
    H += (vfbm(X / 23.0, Y / 23.0, 2, seed + 3) - 0.5) * 2.2
    if clamp is not None:
        H = np.where(H > 0, clamp(X, Y, np.maximum(H, 0.0)), H)
    # ---- baked shading attributes
    cell = Rr * dth
    Hb1 = _box_blur(H, 3); Hb2 = _box_blur(H, 10)
    cav1 = np.clip((Hb1 - H) / (2.2 * cell + 0.5), 0, 1)
    cav2 = np.clip((Hb2 - H) / (9.0 * cell + 2.0), 0, 1)
    low = _sstep(-4.0, base + 14.0, H)
    occ = np.clip(1.0 - 0.6 * cav1 - 0.55 * cav2, 0.06, 1.0) * (0.45 + 0.55 * low)   # v5: deeper crevices
    shd = np.ones_like(H)
    if sun is not None:
        L = Vector(sun).normalized()
        lh = math.hypot(L.x, L.y) or 1e-6
        ux, uy, tanE = L.x / lh, L.y / lh, L.z / lh
        sh = np.zeros_like(H)
        for m_ in (1.5, 3.0, 5.0, 8.0, 12.0, 18.0, 27.0, 40.0, 60.0, 90.0):
            d = cell * m_
            qx = X + ux * d; qy = Y + uy * d
            rr = np.hypot(qx - cx, qy - cy)
            fi = np.log(np.maximum(rr, rmin) / rmin) / dth
            fj = (np.arctan2(qy - cy, qx - cx) % TAU) / dth
            i0 = np.clip(np.floor(fi).astype(int), 0, n_rad - 2); ti = np.clip(fi - i0, 0, 1)
            j0 = np.floor(fj).astype(int) % n_ang; tj = fj - np.floor(fj); j1 = (j0 + 1) % n_ang
            Hs = (H[i0, j0] * (1 - ti) * (1 - tj) + H[i0 + 1, j0] * ti * (1 - tj) + H[i0, j1] * (1 - ti) * tj +
                  H[i0 + 1, j1] * ti * tj)
            Hs = np.where((rr < rmin) | (rr > radii[-1]), base, Hs)
            ex = Hs - (H + d * tanE)
            sh = np.maximum(sh, np.clip(ex / (0.35 * d + 2.5), 0, 1))
        shd = 1.0 - 0.8 * _box_blur(sh, 2)       # v4: light scatters into the shadowed flanks (never black)
    P = np.stack([X, Y, z0 + H], -1)
    o = geo_mesh(name, surface(P, closed_u=True, flip=True), [mat], coll, smooth=True, sharp=179)
    me = o.data
    for nm, arr in (('occ', occ), ('shd', shd)):
        at = me.attributes.new(nm, 'FLOAT', 'POINT')
        at.data.foreach_set('value', arr.astype(np.float32).ravel())
    print(f'[billow] {name}: {X.size} verts, {nh} heads, {npf} puffs, H {H.min():.0f}..{H.max():.0f}, '
          f'{time.time() - t0:.1f}s', flush=True)
    return o


def far_ground(coll, mat, z, center=(0, 0), size=60000.0, name='GroundFar'):
    """The ground ~1 km under the deck, seen through the gaps (scale cue)."""
    h = size / 2
    xs = np.array([center[0] - h, center[0] + h]); ys = np.array([center[1] - h, center[1] + h])
    Xg, Yg = np.meshgrid(xs, ys, indexing='ij')
    P = np.stack([Xg, Yg, np.full_like(Xg, z)], -1)
    o = geo_mesh(name, surface(P, flip=True), [mat], coll, smooth=False)
    try:
        o.visible_shadow = False
    except Exception:
        pass
    return o


def tower_twin(coll, src, mat, name):
    """A second object sharing src's mesh with an OBJECT-linked material override (4B-only re-shade of the towers
    that 4C-4F also use, so those shots are untouched)."""
    import bpy
    me = src.data.copy()          # v3: own mesh copy (the shared-mesh + OBJECT-slot twin hung the render in v1/v2)
    me.materials.clear()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    o.matrix_world = src.matrix_world.copy()
    return o


def wisp_cards(coll, mat, specs, name='Wisps'):
    """Thin horizontal stratus veils (soft alpha cards) floating over the deck. specs: [(x, y, z, sx, sy, rot)].
    UV 0..1 per card drives the soft elliptical falloff in tmat.m_wisp."""
    parts = []
    for (x, y, z, sx, sy, rot) in specs:
        u = np.linspace(0, 1, 2)
        U, V = np.meshgrid(u, u, indexing='ij')
        lx = (U - 0.5) * sx; ly = (V - 0.5) * sy
        c, s = math.cos(rot), math.sin(rot)
        P = np.stack([x + lx * c - ly * s, y + lx * s + ly * c, np.full_like(U, z)], -1)
        parts.append(surface(P, UVg=np.stack([U, V], -1), flip=True))
    o = geo_mesh(name, merge(parts), [mat], coll, smooth=False)
    try:
        o.visible_shadow = False
    except Exception:
        pass
    return o


# ============================================================================ materials

def _nb():
    from common import NB
    return NB


def _vsock(b, v):
    """constant (r,g,b) -> RGB node output; socket passes through."""
    if isinstance(v, (tuple, list)):
        n = b.n('ShaderNodeRGB')
        n.outputs[0].default_value = (*v[:3], 1.0)
        return n.outputs[0]
    return v


def _scale_col(b, col, s):
    m = b.n('ShaderNodeVectorMath'); m.operation = 'SCALE'
    b.link(_vsock(b, col), m.inputs[0])
    if isinstance(s, (int, float)):
        m.inputs['Scale'].default_value = s
    else:
        b.link(s, m.inputs['Scale'])
    return m.outputs[0]


def _add(b, a, c):
    m = b.n('ShaderNodeVectorMath'); m.operation = 'ADD'
    b.link(_vsock(b, a), m.inputs[0]); b.link(_vsock(b, c), m.inputs[1])
    return m.outputs[0]


def _dome(b, vec, scale, seed=0.0):
    """Round dome per Voronoi cell (0 at the cell border, 1 at the feature point) -> cauliflower bumps."""
    mp = b.n('ShaderNodeMapping')
    mp.inputs['Location'].default_value = (seed, seed * 0.61, seed * 0.37)
    b.link(vec, mp.inputs['Vector'])
    v = b.voronoi(mp.outputs['Vector'], 1.0 / scale)
    d = b.math('MULTIPLY', v.outputs['Distance'], 1.25)
    return b.math('SQRT', b.math('SUBTRACT', 1.0, b.math('MULTIPLY', d, d), clamp=True))


def m_cloud_deck3(name, sun_dir, z0=0.0, sun_col=(1.0, 0.9, 0.74), gold=(1.0, 0.58, 0.28), sun_s=3.0,
                  sky_col=(0.40, 0.50, 0.76), sky_s=0.28, shadow_floor=0.3, wrap=0.35,
                  haze_cool=(0.3, 0.38, 0.56), haze_warm=(0.95, 0.66, 0.42), fog_d=3600.0, fog_max=0.6, rim=0.8,
                  fine=(9.0, 3.2), fine_h=(1.8, 0.45), fine_fade=(150.0, 900.0), baked=True,
                  low_fade=(-5.0, 3.0), breach=None, sil=(0.8, 0.985)):
    """Emission-only cloud shading (no EEVEE hard sun shadows): wrapped N.L from a cauliflower-bumped normal x baked
    soft self-shadow 'shd', warm-white tops shifting to gold toward the terminator, sky-blue fill x baked cavity 'occ'
    (unbaked: AO node), darker lanes, forward-scatter gold rim toward the sun, aerial perspective, and alpha that thins
    the silhouettes, the low lanes/gaps (h < 0 over z0) and the island breach edge (ragged noise)."""
    b = _nb()(name)
    for n in list(b.N):
        if n.type == 'BSDF_PRINCIPLED':
            b.N.remove(n)
    P = b.coord('Object')
    geo = b.n('ShaderNodeNewGeometry')
    cam = b.n('ShaderNodeCameraData')
    vd = cam.outputs['View Distance']
    # fine billows (puffs on puffs below the mesh resolution), faded out with distance (no shimmer)
    hgt = b.math('ADD', b.math('MULTIPLY', _dome(b, P, fine[0], 3.1), fine_h[0]),
                 b.math('MULTIPLY', _dome(b, P, fine[1], 7.7), fine_h[1]))
    nz = b.noise(P, 1.0 / 2.2, 3, 0.55)
    hgt = b.math('ADD', hgt, b.math('MULTIPLY', nz.outputs['Fac'], 0.2))
    bump = b.n('ShaderNodeBump')
    bump.inputs['Distance'].default_value = 1.0
    b.link(b.maprange(vd, fine_fade[0], fine_fade[1], 0.75, 0.1), bump.inputs['Strength'])
    b.link(hgt, bump.inputs['Height'])
    Nb = bump.outputs['Normal']
    sn = b.n('ShaderNodeVectorMath'); sn.operation = 'DOT_PRODUCT'; sn.name = 'CloudSunN'
    sn.inputs[1].default_value = tuple(sun_dir)
    b.link(Nb, sn.inputs[0])
    ndl = sn.outputs['Value']
    sunlit = b.math('POWER', b.maprange(ndl, -wrap, 1.0, 0.0, 1.0), 1.5)
    if baked:
        at = b.n('ShaderNodeAttribute'); at.attribute_type = 'GEOMETRY'; at.attribute_name = 'shd'
        shd = b.maprange(at.outputs['Fac'], 0.0, 1.0, shadow_floor, 1.0)
        ao = b.n('ShaderNodeAttribute'); ao.attribute_type = 'GEOMETRY'; ao.attribute_name = 'occ'
        occ = ao.outputs['Fac']
    else:
        # towers: no baked attributes (v1 AO node hung the render) -> darker toward the flat base
        spo = b.n('ShaderNodeSeparateXYZ'); b.link(P, spo.inputs[0])
        occ = b.maprange(b.math('SUBTRACT', spo.outputs['Z'], z0), 0.0, 380.0, 0.68, 1.0)
        shd = None
    direct = sunlit if shd is None else b.math('MULTIPLY', sunlit, shd)
    direct = b.math('MULTIPLY', direct, b.maprange(occ, 0.0, 1.0, 0.4, 1.0))
    rimness = b.maprange(ndl, 0.04, 0.6, 0.9, 0.0)
    sunc = b.mix(sun_col, gold, rimness)
    dcol = _scale_col(b, sunc, b.math('MULTIPLY', direct, sun_s))
    sep = b.n('ShaderNodeSeparateXYZ'); b.link(Nb, sep.inputs[0])
    skyk = b.math('MULTIPLY', b.maprange(sep.outputs['Z'], -0.2, 1.0, 0.45, 1.0), occ)
    scol = _scale_col(b, sky_col, b.math('MULTIPLY', skyk, sky_s))
    tot = _add(b, dcol, scol)
    # lower parts of the deck (lanes, flanks) denser / greyer
    sp = b.n('ShaderNodeSeparateXYZ'); b.link(P, sp.inputs[0])
    h = b.math('SUBTRACT', sp.outputs['Z'], z0)
    tot = _scale_col(b, tot, b.maprange(h, -6.0, 26.0, 0.62, 1.0))
    # forward-scatter silver/gold lining when looking toward the sun
    sd = b.n('ShaderNodeVectorMath'); sd.operation = 'DOT_PRODUCT'; sd.name = 'CloudSunDot'
    sd.inputs[1].default_value = tuple(-x for x in sun_dir)
    b.link(geo.outputs['Incoming'], sd.inputs[0])
    tow = b.math('MAXIMUM', sd.outputs['Value'], 0.0)
    lw = b.n('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
    facing = lw.outputs['Facing']
    rimk = b.math('MULTIPLY', b.math('MULTIPLY', b.math('POWER', tow, 4.0), b.math('POWER', facing, 2.0)), rim)
    tot = _add(b, tot, _scale_col(b, gold, rimk))
    # aerial perspective
    fog = b.math('MULTIPLY', b.math('SUBTRACT', 1.0, b.math('EXPONENT', b.math('DIVIDE', vd, -fog_d))), fog_max)
    hazec = b.mix(haze_cool, haze_warm, b.math('POWER', tow, 3.0))
    col = b.mix(tot, hazec, fog)
    em = b.n('ShaderNodeEmission'); b.link(col, em.inputs['Color']); em.inputs['Strength'].default_value = 1.0
    # alpha: soft silhouettes, thin lanes / gaps, ragged breach edge
    alpha = b.maprange(facing, sil[0], sil[1], 1.0, 0.0)
    if low_fade:
        n2 = b.noise(P, 1.0 / 30.0, 4, 0.6)
        hh = b.math('ADD', h, b.math('MULTIPLY', b.math('SUBTRACT', n2.outputs['Fac'], 0.5), 10.0))
        alpha = b.math('MULTIPLY', alpha, b.maprange(hh, low_fade[0], low_fade[1], 0.0, 1.0))
    if breach:
        bx, by, e0, e1, amp = breach
        rx = b.math('SUBTRACT', sp.outputs['X'], bx); ry = b.math('SUBTRACT', sp.outputs['Y'], by)
        r = b.math('SQRT', b.math('ADD', b.math('MULTIPLY', rx, rx), b.math('MULTIPLY', ry, ry)))
        th = b.math('ARCTAN2', ry, rx)
        edge = 175.0
        for (k, a, ph) in ((3, 18.0, 1.0), (7, 10.0, 2.0), (13, 5.0, 0.0)):
            edge = b.math('ADD', edge, b.math('MULTIPLY', b.math('SINE', b.math('ADD', b.math('MULTIPLY', th, k), ph)), a))
        ne = b.noise(P, 1.0 / 26.0, 5, 0.62)
        dr = b.math('ADD', b.math('SUBTRACT', r, edge), b.math('MULTIPLY', b.math('SUBTRACT', ne.outputs['Fac'], 0.5), amp))
        alpha = b.math('MULTIPLY', alpha, b.maprange(dr, e0, e1, 0.0, 1.0))
    tp = b.n('ShaderNodeBsdfTransparent')
    ms = b.n('ShaderNodeMixShader')
    b.link(alpha, ms.inputs['Fac'])
    b.link(tp.outputs[0], ms.inputs[1]); b.link(em.outputs[0], ms.inputs[2])
    b.link(ms.outputs[0], b.out.inputs['Surface'])
    try:
        b.mat.surface_render_method = 'DITHERED'
    except Exception:
        pass
    return b.mat


def m_wisp(name, sun_dir, col=(1.0, 0.93, 0.84), sky=(0.4, 0.5, 0.72), strength=1.6, alpha=0.32, scale=(160.0, 45.0),
           thr=(0.47, 0.72)):
    """Thin stratus veil on a card: streaky stretched noise x soft elliptical UV falloff, lit colour (no shadows)."""
    b = _nb()(name)
    for n in list(b.N):
        if n.type == 'BSDF_PRINCIPLED':
            b.N.remove(n)
    tc = b.n('ShaderNodeTexCoord')
    uv = b.n('ShaderNodeSeparateXYZ'); b.link(tc.outputs['UV'], uv.inputs[0])
    du = b.math('MULTIPLY', b.math('SUBTRACT', uv.outputs['X'], 0.5), 2.0)
    dv = b.math('MULTIPLY', b.math('SUBTRACT', uv.outputs['Y'], 0.5), 2.0)
    d = b.math('SQRT', b.math('ADD', b.math('MULTIPLY', du, du), b.math('MULTIPLY', dv, dv)))
    fall = b.math('POWER', b.maprange(d, 0.3, 1.0, 1.0, 0.0), 1.6)
    mp = b.n('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0 / scale[0], 1.0 / scale[1], 1.0 / 40.0)
    b.link(tc.outputs['Object'], mp.inputs['Vector'])
    nz = b.noise(mp.outputs['Vector'], 1.0, 6, 0.62, dist=0.4)
    w = b.maprange(nz.outputs['Fac'], thr[0], thr[1], 0.0, 1.0)
    cam = b.n('ShaderNodeCameraData')
    near = b.maprange(cam.outputs['View Distance'], 15.0, 60.0, 0.0, 1.0)
    a = b.math('MULTIPLY', b.math('MULTIPLY', b.math('MULTIPLY', fall, w), near), alpha)
    sd = b.n('ShaderNodeVectorMath'); sd.operation = 'DOT_PRODUCT'; sd.name = 'CloudSunDot'
    sd.inputs[1].default_value = tuple(-x for x in sun_dir)
    geo = b.n('ShaderNodeNewGeometry')
    b.link(geo.outputs['Incoming'], sd.inputs[0])
    tow = b.math('POWER', b.math('MAXIMUM', sd.outputs['Value'], 0.0), 3.0)
    c = _add(b, _scale_col(b, b.mix(col, (1.0, 0.7, 0.42), tow), strength), _scale_col(b, sky, 0.3))
    em = b.n('ShaderNodeEmission'); b.link(c, em.inputs['Color'])
    tp = b.n('ShaderNodeBsdfTransparent')
    ms = b.n('ShaderNodeMixShader')
    b.link(a, ms.inputs['Fac'])
    b.link(tp.outputs[0], ms.inputs[1]); b.link(em.outputs[0], ms.inputs[2])
    b.link(ms.outputs[0], b.out.inputs['Surface'])
    try:
        b.mat.surface_render_method = 'DITHERED'
    except Exception:
        pass
    return b.mat


def m_ground_far(name, strength=0.55, haze=(0.17, 0.23, 0.36), haze_d=3200.0, haze_max=0.82):
    """Landscape ~1 km under the deck (fields / forest / river-dark patches), emission only, heavy aerial haze."""
    b = _nb()(name)
    for n in list(b.N):
        if n.type == 'BSDF_PRINCIPLED':
            b.N.remove(n)
    P = b.coord('Object')
    vor = b.voronoi(P, 1.0 / 420.0)
    n1 = b.noise(P, 1.0 / 2600.0, 5, 0.6)
    fields = b.mix((0.10, 0.10, 0.045), (0.05, 0.085, 0.03), vor.outputs['Distance'])
    fields = b.mix(fields, (0.13, 0.11, 0.06), b.maprange(vor.outputs['Color'], 0.6, 0.62, 0.0, 1.0) if False else 0.0)
    forest = (0.018, 0.04, 0.02)
    col = b.mix(fields, forest, b.maprange(n1.outputs['Fac'], 0.45, 0.6, 0.0, 1.0))
    cam = b.n('ShaderNodeCameraData')
    fog = b.math('MULTIPLY', b.math('SUBTRACT', 1.0, b.math('EXPONENT', b.math('DIVIDE', cam.outputs['View Distance'], -haze_d))), haze_max)
    col = b.mix(_scale_col(b, col, strength * 1.0), haze, fog)
    em = b.n('ShaderNodeEmission'); b.link(col, em.inputs['Color']); em.inputs['Strength'].default_value = 1.0
    b.link(em.outputs[0], b.out.inputs['Surface'])
    return b.mat
