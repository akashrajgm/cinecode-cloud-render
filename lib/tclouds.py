"""Act IV clouds: vectorized cloud-sea heightfields, cumulus towers, volume blobs, birds, god-ray casters."""
import bpy, math
import numpy as np
from mathutils import Vector, noise as mnoise
from common import prim, set_mat, fc_key, fcurves
from tgeo import *


def _fbm2(X, Y, scale, octaves=4, seed=0.0):
    """Cheap vectorized value-ish noise via mathutils noise on a coarse lattice + bilinear upsample is
    overkill here; grids are ~30k verts, so just loop in python over flattened arrays (fast enough)."""
    out = np.zeros(X.size)
    xs, ys = X.ravel() * scale, Y.ravel() * scale
    for o in range(octaves):
        f = 2.0 ** o
        a = 0.5 ** o
        for i in range(X.size):
            out[i] += mnoise.noise(Vector((xs[i] * f + seed, ys[i] * f - seed, 0.37 * o))) * a
    return out.reshape(X.shape)


def cloud_field(coll, mat, center=(0, 0), z0=0.0, rmin=4.0, rmax=7000.0, n_ang=280, n_rad=120, heads=1600,
                head_r=(20.0, 150.0), height=(0.3, 0.6), seed=1, bumps=None, holes=None, name='CloudField',
                noise_amp=(22.0, 7.0), grow=1500.0, head_rmin=None, small=None, clamp=None):
    """Polar heightfield (fine near the centre) of flattened cumulus domes + fbm.
    bumps: [(x, y, r, h)] extra domes (absolute xy) e.g. a head under a dive volume.
    holes: [(x, y, r, depth)] carved dips (clear corridors)."""
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 1, n_rad)
    radii = rmin * (rmax / rmin) ** (t ** 1.1)
    ang = np.linspace(0, TAU, n_ang, endpoint=False)
    Rr, A = np.meshgrid(radii, ang, indexing='ij')
    X = center[0] + Rr * np.cos(A)
    Y = center[1] + Rr * np.sin(A)
    H = np.zeros_like(X)
    h0 = rmin * 8 if head_rmin is None else head_rmin
    hr = h0 + (rmax * 0.9) * (rng.uniform(0, 1, heads) ** 2.2)
    ha = rng.uniform(0, TAU, heads)
    hx = center[0] + hr * np.cos(ha)
    hy = center[1] + hr * np.sin(ha)
    hs = rng.uniform(head_r[0], head_r[1], heads) * (1 + hr / grow)
    hh = hs * rng.uniform(height[0], height[1], heads)
    extra = list(bumps or [])
    for (bx, by, br, bh) in extra:
        hx = np.append(hx, bx); hy = np.append(hy, by); hs = np.append(hs, br); hh = np.append(hh, bh)
    for k in range(len(hx)):
        d2 = (X - hx[k]) ** 2 + (Y - hy[k]) ** 2
        m = d2 < hs[k] ** 2
        if not m.any():
            continue
        cap = hh[k] * np.clip(1 - d2[m] / hs[k] ** 2, 0, None) ** 0.6
        H[m] = np.maximum(H[m], cap)
    # cauliflower: small round bulges riding on top of the big domes (crevices between them = shadow detail)
    if small:
        ns, sr = small
        Hb = H.copy()
        sr_ = rmin * 4 + (rmax * 0.5) * (rng.uniform(0, 1, ns) ** 2.6)
        sa_ = rng.uniform(0, TAU, ns)
        sx_ = center[0] + sr_ * np.cos(sa_); sy_ = center[1] + sr_ * np.sin(sa_)
        ss_ = rng.uniform(sr[0], sr[1], ns) * (1 + sr_ / (grow * 1.5))
        # base height of each bulge = big-dome height at the nearest grid vertex
        ri = np.clip(np.searchsorted(radii, sr_), 0, n_rad - 1)
        ai = np.round(sa_ / TAU * n_ang).astype(int) % n_ang
        base = Hb[ri, ai]
        for k in range(ns):
            if base[k] < 2.0:
                continue
            d2 = (X - sx_[k]) ** 2 + (Y - sy_[k]) ** 2
            m = d2 < ss_[k] ** 2
            if not m.any():
                continue
            cap = base[k] * 0.9 + ss_[k] * 0.55 * np.clip(1 - d2[m] / ss_[k] ** 2, 0, None) ** 0.5
            H[m] = np.maximum(H[m], cap)
    H += _fbm2(X, Y, 1 / 260.0, 3, seed * 3.1) * noise_amp[0] + _fbm2(X, Y, 1 / 55.0, 2, seed * 1.7) * noise_amp[1]
    for (cx, cy, r, dep) in (holes or []):
        d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        H -= dep * np.clip(1 - d / r, 0, 1) ** 2
    if clamp is not None:
        H = clamp(X, Y, H)
    P = np.stack([X, Y, z0 + H], -1)
    return geo_mesh(name, surface(P, closed_u=True, flip=True), [mat], coll, smooth=True, sharp=89)


def towers(coll, mat, specs, seed=21, name='Towers', blobs=28, sub=3, gens=True):
    """Cauliflower cumulus towers: clusters of displaced icospheres. specs: [(x, y, z_base, R, H)]
    r1: three generations of bulges (lobes -> children 0.3-0.5x on the exposed side of each lobe -> grandchildren),
    so the silhouettes are fractal instead of 'stacked cotton balls'; bases clamped hard flat at z_base."""
    rng = np.random.default_rng(seed)
    base = ico(1.0, sub)
    parts = []
    lobes = []
    for (x, y, zb, R, H) in specs:
        # envelope radius along the height: wide skirt, swelling body, cauliflower crown
        def env(t):
            return R * (0.95 - 0.5 * t + 0.25 * math.sin(math.pi * min(1, t * 1.3)))
        n_in = max(6, blobs // 4)
        for k in range(n_in):                      # core fill (no holes)
            t = (k + 0.5) / n_in
            s = env(t) * 0.8
            parts.append(base.xf(mat4((x, y, zb + t * H * 0.85), (0, 0, rng.uniform(0, 6)), (s, s, s * 0.7))))
        for k in range(blobs * 3):                 # surface bulges = the cauliflower read
            t = rng.uniform(0, 1) ** 0.8
            a = rng.uniform(0, TAU)
            e = env(t)
            s = e * rng.uniform(0.14, 0.34) * (1.25 if t > 0.75 else 1.0)
            rr = e * rng.uniform(0.55, 0.85)
            c = (x + math.cos(a) * rr, y + math.sin(a) * rr, zb + t * H * 0.9 + s * 0.3)
            parts.append(base.xf(mat4(c, (0, 0, rng.uniform(0, 6)), (s, s, s * 0.85))))
            if t > 0.18:
                lobes.append((np.array(c), s, np.array([math.cos(a), math.sin(a), 0.0])))
    g = merge(parts)
    V = g.V
    Rm = max(sp[3] for sp in specs)
    f1 = 2.5 / Rm

    def disp(v):
        p = Vector(v) * f1
        q = p * 3.1 + Vector((1.7, 2.9, 0.3))
        r = p * 9.0 + Vector((4.1, 0.6, 2.2))
        w = p * 21.0 + Vector((0.3, 5.2, 1.4))
        hi = (mnoise.noise(r) * 0.03 + mnoise.noise(w) * 0.015) * Rm
        return ((mnoise.noise(p * 2.3 + Vector((5, 0, 0))) * 0.1 + mnoise.noise(q + Vector((3, 0, 0))) * 0.04) * Rm + hi,
                (mnoise.noise(p * 2.3 + Vector((0, 7, 0))) * 0.1 + mnoise.noise(q + Vector((0, 5, 0))) * 0.04) * Rm - hi,
                (mnoise.noise(p) * 0.1 + mnoise.noise(q) * 0.04) * Rm + hi)
    for i in range(len(V)):
        dx, dy, dz = disp(V[i])
        V[i, 0] += dx; V[i, 1] += dy; V[i, 2] += dz
    if gens and lobes:
        ch = ico(1.0, 2)
        gc = ico(1.0, 1)
        extra = []
        for (cc, ss, outw) in lobes:
            for k in range(2):
                d = outw * 0.85 + np.array([0, 0, 0.75]) + rng.normal(0, 0.55, 3)
                d /= np.linalg.norm(d)
                cs = ss * rng.uniform(0.36, 0.52)
                pc = cc + d * ss * 0.9
                pc = pc + np.array(disp(pc))
                extra.append(ch.xf(mat4(tuple(pc), (0, 0, rng.uniform(0, 6)), (cs, cs, cs * 0.85))))
                for m in range(1):
                    d2 = d * 1.2 + rng.normal(0, 0.45, 3)
                    d2 /= np.linalg.norm(d2)
                    gs = cs * rng.uniform(0.3, 0.45)
                    extra.append(gc.xf(mat4(tuple(pc + d2 * cs * 0.92), (0, 0, rng.uniform(0, 6)), (gs, gs, gs * 0.9))))
        g = merge([g] + extra)
        V = g.V
    # hard flat bases (cumulus sit on a condensation level)
    zbs = min(sp[2] for sp in specs)
    V[:, 2] = np.maximum(V[:, 2], zbs)
    return geo_mesh(name, g, [mat], coll, smooth=True, sharp=89)


def vol_blob(coll, name, loc, size, mat, rot=(0, 0, 0)):
    o = prim('cube', name, loc=tuple(loc), scale=tuple(size), rot=rot, coll=coll, smooth=False)
    set_mat(o, mat)
    try:
        o.visible_shadow = False
    except Exception:
        pass
    return o


def ray_casters(coll, mat, specs, seed=3, name='RayCasters'):
    """Camera-invisible flat blobs that only cast shadows -> god-ray shafts in the haze.
    specs: [(x, y, z, rx, ry)]"""
    rng = np.random.default_rng(seed)
    base = ico(1.0, 2)
    parts = []
    for (x, y, z, rx, ry) in specs:
        for k in range(5):
            c = (x + rng.uniform(-0.5, 0.5) * rx, y + rng.uniform(-0.5, 0.5) * ry, z + rng.uniform(-8, 8))
            parts.append(base.xf(mat4(c, (0, 0, rng.uniform(0, 6)), (rx * rng.uniform(0.35, 0.6), ry * rng.uniform(0.35, 0.6), 6.0))))
    o = geo_mesh(name, merge(parts), [mat], coll, smooth=False)
    for attr in ('visible_camera', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter'):
        try:
            setattr(o, attr, False)
        except Exception:
            pass
    return o


def birds(coll, mat, n=36, center=(0, 0, 0), spread=(60, 40, 12), heading=(1, 0, 0), speed=0.6, frames=(1, 80),
          size=0.45, seed=5, name='Birds'):
    """A loose flock: each bird = body + two wing objects (flap keyframes), all moving along heading."""
    rng = np.random.default_rng(seed)
    hd = np.asarray(heading, float); hd /= np.linalg.norm(hd)
    yaw = math.atan2(hd[1], hd[0])
    wing = Geo(np.array([(0, 0, 0), (-0.25, 0.0, 0), (-0.1, 1.0, 0.0), (0.12, 0.9, 0)]), [0, 1, 2, 3], [4])
    body = lathe([(0.0001, -0.35), (0.06, -0.2), (0.07, 0.0), (0.04, 0.25), (0.0001, 0.38)], seg=6)
    body = body.xf(mat4(rot=(0, math.pi / 2, 0)))
    objs = []
    root = bpy.data.objects.new(name, None)
    (coll or bpy.context.scene.collection).objects.link(root)
    bm = MB().add(body).build(name + '_body', [mat], coll, smooth=True)
    wm_l = MB().add(wing).build(name + '_wl', [mat], coll, smooth=False)
    wm_r = MB().add(wing.xf(mat4(scale=(1, -1, 1)))).build(name + '_wr', [mat], coll, smooth=False)
    protos = (bm, wm_l, wm_r)
    for k in range(n):
        p = np.asarray(center) + rng.uniform(-1, 1, 3) * np.asarray(spread)
        s = size * rng.uniform(0.8, 1.2)
        ph = rng.uniform(0, 6.28)
        fr = rng.uniform(0.32, 0.42)       # flaps per frame*2pi/...
        for j, pr in enumerate(protos):
            o = bpy.data.objects.new(f'{name}_{k}_{j}', pr.data)
            (coll or bpy.context.scene.collection).objects.link(o)
            o.scale = (s, s, s)
            o.rotation_euler = (0, 0, yaw + rng.uniform(-0.12, 0.12))
            f0, f1 = frames
            p0 = p; p1 = p + hd * speed * (f1 - f0) * rng.uniform(0.9, 1.1)
            o.location = tuple(p0); o.keyframe_insert('location', frame=f0)
            o.location = tuple(p1); o.keyframe_insert('location', frame=f1)
            for fc in fcurves(o):
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
            if j > 0:
                sgn = 1 if j == 1 else -1
                for f in range(f0, f1 + 1, 2):
                    o.rotation_euler = (sgn * 0.75 * math.sin(f * fr + ph), 0, yaw)
                    o.keyframe_insert('rotation_euler', frame=f)
            objs.append(o)
    for pr in protos:
        bpy.data.objects.remove(pr)
    return objs


def beam_material(name='T_Beam', color=(1.0, 0.78, 0.5), strength=0.012):
    """Pure-emission volume for faked god-ray shafts on a unit cube: soft round cross-section, faded ends,
    streaky noise. Density 0 -> additive glow only (cheap, art-directable)."""
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    N, L = nt.nodes, nt.links

    def M(op, a, b_=None, clamp=False):
        x = N.new('ShaderNodeMath'); x.operation = op; x.use_clamp = clamp
        for i, v in enumerate((a, b_)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                x.inputs[i].default_value = v
            else:
                L.new(v, x.inputs[i])
        return x.outputs[0]
    out = N.new('ShaderNodeOutputMaterial')
    vp = N.new('ShaderNodeVolumePrincipled')
    vp.inputs['Density'].default_value = 0.0
    vp.inputs['Emission Color'].default_value = (*color, 1)
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    r = M('SQRT', M('ADD', M('POWER', sep.outputs[1], 2.0), M('POWER', sep.outputs[2], 2.0)))
    # gaussian cross-section (no hard plank edge) that reaches ~0 before the box faces
    soft = M('MULTIPLY', M('EXPONENT', M('MULTIPLY', M('POWER', r, 2.0), -14.0)),
             M('SUBTRACT', 1.0, M('MULTIPLY', r, 2.0), clamp=True))
    # long soft fade at both ends (starts under the deck, dies into the ground haze)
    ends = M('POWER', M('MULTIPLY', M('SUBTRACT', 0.5, M('ABSOLUTE', sep.outputs[0])), 2.6, clamp=True), 1.5)
    oi = N.new('ShaderNodeObjectInfo')
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (6.0, 7.0, 7.0)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    ad = N.new('ShaderNodeVectorMath'); ad.operation = 'ADD'
    L.new(mp.outputs[0], ad.inputs[0]); L.new(oi.outputs['Location'], ad.inputs[1])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0; nz.inputs['Detail'].default_value = 3.0
    L.new(ad.outputs[0], nz.inputs['Vector'])
    var = M('ADD', 0.25, M('MULTIPLY', nz.outputs['Fac'], 1.3))
    L.new(M('MULTIPLY', M('MULTIPLY', M('MULTIPLY', soft, ends), var), strength), vp.inputs['Emission Strength'])
    L.new(vp.outputs['Volume'], out.inputs['Volume'])
    return m


def light_beams(coll, mat, light_dir, specs, name='Beam'):
    """specs: [(center xyz, length, width)] -> unit cubes stretched along light_dir (direction light travels)."""
    d = Vector(light_dir).normalized()
    q = Vector((1, 0, 0)).rotation_difference(d)
    objs = []
    for k, (c, Ln, w) in enumerate(specs):
        o = prim('cube', f'{name}{k}', loc=tuple(c), scale=(Ln, w, w * 0.8), coll=coll, smooth=False)
        o.rotation_mode = 'QUATERNION'
        o.rotation_quaternion = q
        set_mat(o, mat)
        try:
            o.visible_shadow = False
        except Exception:
            pass
        objs.append(o)
    return objs


def pinnacles(coll, mat_rock, mat_top, specs, seed=7, name='Pinnacles'):
    """Sheer rock pillars rising out of the cloud sea (scale cues). specs: [(x, y, z_base, r, h)].
    Vertical fluting + strata ledges via displacement; a grassy cap with a few blob trees on top."""
    rng = np.random.default_rng(seed)
    R, Tp = [], []
    for k, (x, y, zb, r, h) in enumerate(specs):
        nseg, nz = 40, 34
        A = np.linspace(0, TAU, nseg, endpoint=False)
        prof = []
        for i in range(nz + 1):
            t = i / nz
            rr = r * (1.25 - 0.35 * t + 0.08 * math.sin(t * 9 + k))
            prof.append((rr, zb + h * t))
        g = lathe(prof, seg=nseg, cap=False)
        V = g.V
        for i in range(len(V)):
            px, py, pz = V[i]
            a = math.atan2(py - 0, px - 0)
            fl = mnoise.noise(Vector((math.cos(a) * 3.0 + k, math.sin(a) * 3.0, pz * 0.004))) * 0.22
            st = mnoise.noise(Vector((px * 0.02, py * 0.02, pz * 0.09 + k))) * 0.1
            s = 1 + fl + st
            V[i, 0] *= s; V[i, 1] *= s
        R.append(g.xf(mat4((x, y, 0))))
        # cap: slightly domed disc
        top = lathe([(0.001, zb + h + r * 0.12), (r * 0.6, zb + h + r * 0.08), (r * 0.98, zb + h)], seg=nseg)
        Tp.append(top.xf(mat4((x, y, 0))))
    o1 = geo_mesh(name, merge(R), [mat_rock], coll, smooth=True, sharp=70)
    o2 = geo_mesh(name + 'Top', merge(Tp), [mat_top], coll, smooth=True, sharp=70)
    return o1, o2
