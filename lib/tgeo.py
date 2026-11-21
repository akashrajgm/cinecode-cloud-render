"""Act IV geometry kernel: numpy mesh templates (Geo) + merged mesh builder (MB).

Everything static is generated as numpy arrays and merged into a few big meshes
(one per material group) -> fast build, cheap draw calls, thousands of ornaments.
"""
import bpy, math
import numpy as np
from mathutils import Matrix, Euler, Vector

TAU = 2 * math.pi


class Geo:
    __slots__ = ('V', 'I', 'L', 'UV')

    def __init__(self, V, I, L, UV=None):
        self.V = np.asarray(V, np.float64).reshape(-1, 3)
        self.I = np.asarray(I, np.int64).ravel()
        self.L = np.asarray(L, np.int64).ravel()
        self.UV = np.zeros((len(self.I), 2)) if UV is None else np.asarray(UV, np.float64).reshape(-1, 2)

    def copy(self):
        return Geo(self.V.copy(), self.I.copy(), self.L.copy(), self.UV.copy())

    def xf(self, M):
        g = self.copy()
        g.V = xform(g.V, M)
        return g


def mat4(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), order='XYZ'):
    if not isinstance(scale, (tuple, list)):
        scale = (scale, scale, scale)
    M = Matrix.LocRotScale(Vector(loc), Euler(rot, order), Vector(scale))
    return np.array(M)


def frame_mat(origin, x, y, z, scale=1.0):
    """4x4 from explicit axes (columns)."""
    M = np.eye(4)
    M[:3, 0] = np.asarray(x) * scale
    M[:3, 1] = np.asarray(y) * scale
    M[:3, 2] = np.asarray(z) * scale
    M[:3, 3] = origin
    return M


def xform(V, M):
    M = np.asarray(M)
    return V @ M[:3, :3].T + M[:3, 3]


def merge(geos):
    Vs, Is, Ls, UVs = [], [], [], []
    n = 0
    for g in geos:
        Vs.append(g.V); Is.append(g.I + n); Ls.append(g.L); UVs.append(g.UV)
        n += len(g.V)
    return Geo(np.concatenate(Vs), np.concatenate(Is), np.concatenate(Ls), np.concatenate(UVs))


def _quads(rows, cols, closed_cols=False, closed_rows=False):
    """Quad faces for a rows x cols vertex grid (row-major)."""
    cc = cols if closed_cols else cols - 1
    rr = rows if closed_rows else rows - 1
    i, j = np.meshgrid(np.arange(rr), np.arange(cc), indexing='ij')
    i = i.ravel(); j = j.ravel()
    i2 = (i + 1) % rows; j2 = (j + 1) % cols
    a = i * cols + j; b = i * cols + j2; c = i2 * cols + j2; d = i2 * cols + j
    F = np.stack([a, b, c, d], 1)
    return F


# ----------------------------------------------------------------------------- primitives

def box(size=(1, 1, 1), center=(0, 0, 0)):
    sx, sy, sz = [s / 2 for s in size]
    cx, cy, cz = center
    V = np.array([(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
                  (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]) + (cx, cy, cz)
    F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return Geo(V, np.array(F).ravel(), [4] * 6)


def box_mm(x0, y0, z0, x1, y1, z1):
    return box((x1 - x0, y1 - y0, z1 - z0), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def lathe(prof, seg=24, teeth=0, closed=False, cap=True, tooth_shape=(0.0, 0.14, 0.42, 0.56), phase=0.0,
          rough=None):
    """Surface of revolution around Z. prof: [(r, z) or (r, z, tooth_depth)] bottom->top.
    teeth>0 -> angular sampling 4 per tooth, rows with tooth_depth get trapezoid teeth.
    closed=True -> profile is a closed loop (rings)."""
    prof = [(p[0], p[1], p[2] if len(p) > 2 else 0.0) for p in prof]
    if teeth:
        ph = np.array(tooth_shape)
        A = ((np.arange(teeth)[:, None] + ph[None, :]) / teeth).ravel() * TAU + phase
        mult = np.tile(np.array([0.0, 1.0, 1.0, 0.0]), teeth)
    else:
        A = np.arange(seg) / seg * TAU + phase
        mult = np.zeros(seg)
    nA = len(A)
    ca, sa = np.cos(A), np.sin(A)
    rows = []
    for r, z, td in prof:
        rr = r + td * mult
        rows.append(np.stack([rr * ca, rr * sa, np.full(nA, z)], 1))
    V = np.concatenate(rows)
    nR = len(prof)
    F = _quads(nR, nA, closed_cols=True, closed_rows=closed)
    I = [F.ravel()]
    L = [np.full(len(F), 4)]
    # uv: u around, v along profile
    vv = np.concatenate([[0], np.cumsum([math.hypot(prof[k + 1][0] - prof[k][0], prof[k + 1][1] - prof[k][1]) for k in range(nR - 1)])])
    uvv = np.stack([np.tile(A / TAU, nR), np.repeat(vv, nA)], 1)
    UV = [uvv[F.ravel()]]
    if not closed and cap:
        if prof[0][0] > 1e-6:
            idx = np.arange(nA)[::-1]
            I.append(idx); L.append([nA]); UV.append(np.zeros((nA, 2)))
        if prof[-1][0] > 1e-6:
            idx = np.arange(nA) + (nR - 1) * nA
            I.append(idx); L.append([nA]); UV.append(np.zeros((nA, 2)))
    g = Geo(V, np.concatenate(I), np.concatenate(L), np.concatenate(UV))
    if rough:
        rng = np.random.default_rng(rough[1])
        g.V += rng.normal(0, rough[0], g.V.shape)
    return g


def sweep(path, prof, closed_path=False, cap=True, up=(0, 0, 1), scale=None, uv_scale=1.0):
    """Sweep closed 2D profile (CCW in (side, up) plane) along 3D path."""
    P = np.asarray(path, np.float64)
    n = len(P)
    pr = np.asarray(prof, np.float64)
    m = len(pr)
    T = np.zeros_like(P)
    if closed_path:
        T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    else:
        T[1:-1] = P[2:] - P[:-2]
        T[0] = P[1] - P[0]
        T[-1] = P[-1] - P[-2]
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    upv = np.asarray(up, np.float64)
    S = np.cross(upv[None, :], T)
    bad = np.linalg.norm(S, axis=1) < 1e-6
    if bad.any():
        S[bad] = np.cross(np.array([0, 1.0, 0])[None, :], T[bad])
    S /= np.linalg.norm(S, axis=1, keepdims=True) + 1e-12
    U = np.cross(T, S)
    sc = np.ones(n) if scale is None else np.asarray(scale, np.float64)
    V = P[:, None, :] + sc[:, None, None] * (pr[None, :, 0:1] * S[:, None, :] + pr[None, :, 1:2] * U[:, None, :])
    V = V.reshape(-1, 3)
    F = _quads(n, m, closed_cols=True, closed_rows=closed_path)
    I = [F.ravel()]; L = [np.full(len(F), 4)]
    seglen = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    uvv = np.stack([np.tile(np.arange(m) / m, n), np.repeat(seglen * uv_scale, m)], 1)
    UV = [uvv[F.ravel()]]
    if cap and not closed_path:
        I.append(np.arange(m)[::-1]); L.append([m]); UV.append(np.zeros((m, 2)))
        I.append(np.arange(m) + (n - 1) * m); L.append([m]); UV.append(np.zeros((m, 2)))
    return Geo(V, np.concatenate(I), np.concatenate(L), np.concatenate(UV))


def surface(P, UVg=None, closed_u=False, flip=False):
    """P: (nr, nc, 3) grid -> quads. UVg: (nr, nc, 2)."""
    nr, nc, _ = P.shape
    F = _quads(nr, nc, closed_cols=closed_u)
    if flip:
        F = F[:, ::-1]
    UV = None
    if UVg is not None:
        UV = UVg.reshape(-1, 2)[F.ravel()]
    return Geo(P.reshape(-1, 3), F.ravel(), np.full(len(F), 4), UV)


def circle_prof(r, n=8):
    a = np.arange(n) / n * TAU
    return np.stack([r * np.cos(a), r * np.sin(a)], 1)


def rect_prof(w, h, cx=0.0, cy=0.0):
    return np.array([(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)])


def ico(r=1.0, sub=2):
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    V = np.array([v.co[:] for v in bm.verts])
    F = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    return Geo(V, np.array(F).ravel(), [3] * len(F))


def uvsphere(r=1.0, u=24, v=12):
    prof = [(r * math.sin(math.pi * k / v) + (1e-4 if k in (0, v) else 0), -r * math.cos(math.pi * k / v)) for k in range(v + 1)]
    return lathe(prof, seg=u, cap=False)


def instances(g, mats):
    """Tile template g by an array of 4x4 matrices (k,4,4) -> merged Geo."""
    M = np.asarray(mats)
    k = len(M)
    n = len(g.V)
    V = np.einsum('kij,nj->kni', M[:, :3, :3], g.V) + M[:, None, :3, 3]
    I = (g.I[None, :] + (np.arange(k) * n)[:, None]).ravel()
    return Geo(V.reshape(-1, 3), I, np.tile(g.L, k), np.tile(g.UV, (k, 1)))


def along(path, spacing, offset=0.0, up=(0, 0, 1)):
    """Matrices of frames placed every `spacing` meters along a polyline.
    local x = tangent, local z = up-ish (orthogonalized), local y = z cross x."""
    P = np.asarray(path, np.float64)
    seg = np.diff(P, axis=0)
    sl = np.linalg.norm(seg, axis=1)
    cum = np.concatenate([[0], np.cumsum(sl)])
    total = cum[-1]
    ds = np.arange(offset, total + 1e-6, spacing)
    out = []
    upv = np.asarray(up, np.float64)
    for d in ds:
        k = min(np.searchsorted(cum, d, side='right') - 1, len(seg) - 1)
        t = (d - cum[k]) / max(sl[k], 1e-9)
        p = P[k] + seg[k] * t
        x = seg[k] / max(sl[k], 1e-9)
        z = upv - x * np.dot(upv, x)
        if np.linalg.norm(z) < 1e-6:
            z = np.array([0, 1.0, 0])
        z /= np.linalg.norm(z)
        y = np.cross(z, x)
        out.append(frame_mat(p, x, y, z))
    return out


# ----------------------------------------------------------------------------- builder

class MB:
    """Accumulates Geo pieces with a material slot each, builds one Blender object."""

    def __init__(self):
        self.parts = []  # (Geo, slot)

    def add(self, g, slot=0, M=None):
        if M is not None:
            g = g.xf(M)
        self.parts.append((g, slot))
        return self

    def inst(self, g, mats, slot=0):
        if len(mats):
            self.parts.append((instances(g, mats), slot))
        return self

    def build(self, name, mats, coll=None, smooth=True, sharp=40.0, bevel_w=0.0, bevel_seg=2, bevel_angle=35.0):
        if not self.parts:
            return None
        Vs, Is, Ls, UVs, Ms = [], [], [], [], []
        n = 0
        for g, s in self.parts:
            Vs.append(g.V); Is.append(g.I + n); Ls.append(g.L); UVs.append(g.UV)
            Ms.append(np.full(len(g.L), s, np.int32))
            n += len(g.V)
        V = np.concatenate(Vs); I = np.concatenate(Is); L = np.concatenate(Ls)
        UV = np.concatenate(UVs); MI = np.concatenate(Ms)
        me = bpy.data.meshes.new(name)
        me.vertices.add(len(V))
        me.vertices.foreach_set('co', V.astype(np.float32).ravel())
        me.loops.add(len(I))
        me.loops.foreach_set('vertex_index', I.astype(np.int32))
        me.polygons.add(len(L))
        starts = np.concatenate([[0], np.cumsum(L)[:-1]]).astype(np.int32)
        me.polygons.foreach_set('loop_start', starts)
        try:
            me.polygons.foreach_set('loop_total', L.astype(np.int32))
        except Exception:
            pass
        me.polygons.foreach_set('material_index', MI)
        uvl = me.uv_layers.new(name='UVMap')
        uvl.data.foreach_set('uv', UV.astype(np.float32).ravel())
        me.update(calc_edges=True)
        me.validate(clean_customdata=False)
        for m in mats:
            me.materials.append(m)
        o = bpy.data.objects.new(name, me)
        (coll or bpy.context.scene.collection).objects.link(o)
        if smooth:
            # Blender 5.x: the API is set_sharp_from_angle (set_sharpness_by_angle does not exist -> the old
            # fallback smoothed EVERYTHING: pillow normals on every box, no pool reflection, soft architecture)
            me.shade_smooth()
            fn = getattr(me, 'set_sharp_from_angle', None) or getattr(me, 'set_sharpness_by_angle', None)
            if fn is not None:
                fn(angle=math.radians(sharp))
            else:
                print('[MB] WARNING no sharp-by-angle API; flat shading', name)
                me.shade_flat()
        if bevel_w > 0:
            b = o.modifiers.new('Bevel', 'BEVEL')
            b.width = bevel_w
            b.segments = bevel_seg
            b.limit_method = 'ANGLE'
            b.angle_limit = math.radians(bevel_angle)
            b.harden_normals = False
            b.miter_outer = 'MITER_ARC'
        print(f'[MB] {name}: {len(V)} verts {len(L)} faces')
        return o


def geo_mesh(name, g, mats, coll=None, smooth=True, sharp=40.0, bevel_w=0.0):
    return MB().add(g).build(name, mats if isinstance(mats, (list, tuple)) else [mats], coll, smooth, sharp, bevel_w)
