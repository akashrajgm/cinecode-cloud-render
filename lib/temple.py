"""ACT IV - THE SANCTUM: the clockwork temple generators.

Layout (meters): plateau top z=0, central axis x=0, the complex faces -Y.
  gate y=-82, reflecting pool y -74..-26, grand stair y -22..-5, main hall y -6..33,
  orrery crown at (0, 13.5, ~40). Sun low from the south-west.
"""
import bpy, math, random
import numpy as np
from mathutils import Vector, Matrix, Euler, noise as mnoise
from common import *
from tgeo import *
import tmat

RNG = np.random.default_rng(7)

# ----------------------------------------------------------------------------- templates

def face_rot(fx):
    """Euler that turns local +Z toward the horizontal facing vector fx."""
    if abs(fx[1]) > 0.5:
        return (-fx[1] * math.pi / 2, 0, 0)
    return (0, fx[0] * math.pi / 2, 0)


def tooth_geo(w0=0.2, w1=0.05, h=0.35, t=0.06):
    V = [(-w0 / 2, -t / 2, 0), (w0 / 2, -t / 2, 0), (w1 / 2, -t / 2, h), (-w1 / 2, -t / 2, h),
         (-w0 / 2, t / 2, 0), (w0 / 2, t / 2, 0), (w1 / 2, t / 2, h), (-w1 / 2, t / 2, h)]
    F = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)]
    return Geo(V, np.array(F).ravel(), [4] * 6)


def flame_geo(h=0.5, w=0.16, t=0.05, curl=0.12, n=6):
    """Tapered curling flame/tooth (gear-tooth crest) in XZ plane."""
    path = [(curl * math.sin(k / n * 2.2) * (k / n) ** 1.2, 0, h * k / n) for k in range(n + 1)]
    scale = [max(0.08, 1 - k / n) for k in range(n + 1)]
    return sweep(path, rect_prof(w, t), scale=scale)


def rosette_geo(r=0.5, teeth=10, depth=0.08):
    prof = [(r * 0.02, 0), (r * 0.98, 0, r * 0.12), (r * 0.98, depth * 0.5, r * 0.12), (r * 0.7, depth * 0.65),
            (r * 0.42, depth * 1.0), (r * 0.02, depth * 1.6)]
    return lathe(prof, teeth=teeth)


def baluster_geo(h=0.75, r=0.11):
    p = [(r * 0.9, 0), (r * 0.9, 0.06 * h), (r * 0.55, 0.1 * h), (r * 0.6, 0.18 * h), (r * 1.0, 0.38 * h), (r * 0.9, 0.55 * h),
         (r * 0.42, 0.78 * h), (r * 0.5, 0.86 * h), (r * 0.8, 0.92 * h), (r * 0.8, h)]
    return lathe(p, seg=12)


def finial_small_geo(h=0.6, r=0.1):
    p = [(r, 0), (r, 0.08 * h), (r * 0.5, 0.14 * h), (r * 1.2, 0.35 * h), (r * 0.4, 0.55 * h), (r * 0.6, 0.62 * h),
         (r * 0.25, 0.7 * h), (r * 0.08, 0.95 * h), (0.001, h)]
    return lathe(p, seg=12)


def ring_mesh_geo(teeth=40, inner=0.62, bead=True):
    p = [(inner, 0.0), (0.9, 0.0, 0.1), (0.9, 0.3, 0.1), (0.97, 0.5, 0.1), (0.9, 0.7, 0.1), (0.9, 1.0, 0.1), (inner, 1.0)]
    return lathe(p, teeth=teeth, closed=True)


def column_geos(h=9.2, r=0.55):
    base = lathe([(r * 1.6, 0), (r * 1.6, 0.25), (r * 1.45, 0.3), (r * 1.35, 0.45), (r * 1.4, 0.52), (r * 1.15, 0.6),
                  (r * 1.1, 0.75)], seg=24)
    sq = box((r * 3.4, r * 3.4, 0.3), (0, 0, -0.15))
    shaft = lathe([(r * 1.05, 0.75), (r * 1.0, 0.9), (r * 0.98, h * 0.5), (r * 0.9, h - 1.25)], teeth=20,
                  tooth_shape=(0.0, 0.2, 0.8, 1.0))
    # flutes: invert - teeth rows have negative depth -> grooves
    shaft = lathe([(r * 1.05, 0.75, -0.05), (r * 1.0, 0.9, -0.05), (r * 0.98, h * 0.5, -0.05), (r * 0.9, h - 1.25, -0.05)],
                  teeth=20, tooth_shape=(0.0, 0.15, 0.85, 1.0))
    cap = lathe([(r * 0.95, h - 1.3), (r * 1.15, h - 1.2), (r * 1.0, h - 1.05), (r * 1.25, h - 0.9, 0.08), (r * 1.25, h - 0.7, 0.08),
                 (r * 1.0, h - 0.62), (r * 1.6, h - 0.35, 0.12), (r * 1.7, h - 0.2, 0.12), (r * 1.7, h)], teeth=24)
    ring_b = lathe([(r * 1.08, 0.78), (r * 1.2, 0.8, 0.04), (r * 1.2, 0.98, 0.04), (r * 1.08, 1.0)], teeth=24, closed=True)
    ring_c = lathe([(r * 1.0, h - 1.62), (r * 1.13, h - 1.6, 0.04), (r * 1.13, h - 1.42, 0.04), (r * 1.0, h - 1.4)], teeth=24, closed=True)
    beads = instances(uvsphere(1.0, 8, 5), [mat4((r * 1.02 * math.cos(a), r * 1.02 * math.sin(a), h - 1.95), scale=r * 0.07)
                                            for a in np.arange(20) / 20 * TAU])
    return merge([base, sq]), shaft, merge([cap, ring_b, ring_c, beads])


def lantern_geos(h=3.2):
    post = lathe([(0.2, 0), (0.2, 0.25), (0.14, 0.32), (0.09, 0.5), (0.07, h - 0.95), (0.12, h - 0.85), (0.08, h - 0.78)], seg=12)
    cage = merge([
        lathe([(0.26, h - 0.8), (0.3, h - 0.72), (0.18, h - 0.68)], seg=16),
        lathe([(0.34, h - 0.2), (0.4, h - 0.12), (0.3, h - 0.05), (0.12, h + 0.12), (0.05, h + 0.35), (0.001, h + 0.5)], teeth=12),
        instances(box((0.035, 0.035, 0.5), (0.27, 0, h - 0.45)), [mat4(rot=(0, 0, k * TAU / 6)) for k in range(6)]),
    ])
    glass = lathe([(0.12, h - 0.68), (0.25, h - 0.55), (0.27, h - 0.4), (0.24, h - 0.22), (0.12, h - 0.18)], seg=12)
    mull = merge([instances(box((0.03, 0.03, 0.5), (0.285, 0, h - 0.43)), [mat4(rot=(0, 0, (k + 0.5) * TAU / 12)) for k in range(12)]),
                  lathe([(0.282, h - 0.5), (0.3, h - 0.49), (0.3, h - 0.47), (0.282, h - 0.46)], seg=24),
                  lathe([(0.29, h - 0.34), (0.305, h - 0.33), (0.305, h - 0.31), (0.29, h - 0.3)], seg=24)])
    return post, cage, glass, mull


def cypress_geo(h=11.0, r=1.4, seed=0):
    rng = np.random.default_rng(seed)
    n = 14
    prof = []
    for k in range(n + 1):
        t = k / n
        rr = r * (math.sin(math.pi * min(1, t * 1.05)) ** 0.7) * (1 - 0.55 * t) + 0.02
        prof.append((rr, t * h))
    prof[0] = (0.25, 0.0)
    g = lathe(prof, seg=14, cap=False)
    # lumpy foliage
    V = g.V
    for i in range(len(V)):
        x, y, z = V[i]
        d = mnoise.noise(Vector((x * 0.9 + seed * 7, y * 0.9, z * 0.5))) * 0.35 + mnoise.noise(Vector((x * 3, y * 3, z * 2))) * 0.12
        rr = math.hypot(x, y)
        if rr > 1e-4:
            V[i, 0] += x / rr * d * min(1, rr)
            V[i, 1] += y / rr * d * min(1, rr)
    return g


def blob_tree_geo(seed=0, h=7.0, r=3.2):
    rng = np.random.default_rng(seed)
    parts = []
    base = ico(1.0, 2)          # sub 3 tried (r2-r3): +800k verts for trees that are tiny in 4B -> back to 2 (render budget);
                                # the finer leafy displacement octave below stays
    for k in range(9):
        a = rng.uniform(0, TAU); rr = rng.uniform(0.2, 1.0) * r * 0.6
        c = (math.cos(a) * rr, math.sin(a) * rr, h * 0.55 + rng.uniform(-0.25, 0.35) * h * 0.4)
        s = r * rng.uniform(0.45, 0.7)
        g = base.xf(mat4(c, (rng.uniform(0, 3), rng.uniform(0, 3), 0), (s, s, s * 0.85)))
        parts.append(g)
    g = merge(parts)
    V = g.V
    for i in range(len(V)):
        p = Vector(V[i])
        d = mnoise.noise(p * 0.7 + Vector((seed, 0, 0))) * 0.5 + mnoise.noise(p * 3.3 + Vector((0, seed, 0))) * 0.15 * r * 0.5
        V[i] += np.array([0, 0, 0]) + (V[i] - np.array([0, 0, h * 0.55])) / (np.linalg.norm(V[i] - np.array([0, 0, h * 0.55])) + 1e-6) * d
    trunk = lathe([(0.35, 0), (0.25, h * 0.35), (0.15, h * 0.55)], seg=8)
    return g, trunk


def horn_curl(base, out_dir, up=(0, 0, 1), size=1.0, turns=1.3, r0=0.16, n=18, seg=8):
    """Spiral horn (gear-curl) path rising from base outward and curling back."""
    b = np.asarray(base, float); o = np.asarray(out_dir, float); o = o / np.linalg.norm(o); u = np.asarray(up, float)
    pts = []
    for k in range(n + 1):
        t = k / n
        th = t * turns * math.pi
        rad = size * (1 - 0.65 * t)
        pts.append(b + o * rad * math.sin(th) * 0.9 + u * (rad * (1 - math.cos(th)) * 0.8 + t * size * 0.3))
    scale = [1 - 0.75 * (k / n) for k in range(n + 1)]
    return sweep(pts, circle_prof(r0, seg), scale=scale, up=tuple(np.cross(o, u)) if abs(np.dot(o, u)) < 0.99 else (0, 1, 0))


# ----------------------------------------------------------------------------- the builder

class Temple:
    def __init__(self, coll=None, detail=1.0):
        self.coll = coll
        self.B = {k: MB() for k in ('gold', 'marble', 'verm', 'tile', 'tile_r', 'wood', 'dark', 'paving', 'glaze',
                                     'glass', 'bronze', 'leaf', 'leaf2', 'hedge', 'trunk', 'water', 'grass', 'gold2',
                                     'flower_r', 'flower_w', 'flower_y', 'enamel')}
        self.rings = []      # (obj, rad/s)
        self.anim = []
        self.detail = detail
        self.T = {
            'tooth': tooth_geo(), 'flame': flame_geo(), 'rosette': rosette_geo(), 'baluster': baluster_geo(),
            'finial': finial_small_geo(), 'bead': uvsphere(1.0, 10, 6),
            'bell': merge([lathe([(0.09, -0.01), (0.105, 0.0), (0.1, 0.04), (0.06, 0.18), (0.05, 0.3), (0.03, 0.34),
                                  (0.012, 0.36)], seg=12),
                           lathe([(0.008, 0.34), (0.008, 0.5)], seg=6),
                           uvsphere(0.03, 8, 5).xf(mat4((0, 0, -0.03)))]),
        }
        self.ring_mesh = None

    # ---------------------------------------------------------------- roofs
    def gable(self, xc, yf, yb, hw, ze, za, ov=1.4, upturn=1.6, ped='clock', ridge=True, back_face=False, crest=True,
              tiles='tile', pedmat='enamel'):
        B, T = self.B, self.T
        Lr = yb - yf
        hwe = hw + ov
        ns, nt = 12, max(4, int(Lr / 0.9))
        s = np.linspace(0, 1, ns); t = np.linspace(0, 1, nt)
        S, Tt = np.meshgrid(s, t, indexing='ij')
        edges = {}
        for side in (-1, 1):
            X = xc + side * S * hwe
            Y = yf + Tt * Lr
            Z = ze + (za - ze) * (1 - S) ** 1.35
            w = S ** 3 * (np.clip(1 - (Tt * Lr) / 3.5, 0, 1) ** 2 + np.clip(1 - ((1 - Tt) * Lr) / 3.5, 0, 1) ** 2 * (1 if back_face else 0))
            Z = Z + upturn * w
            Y = Y - 0.5 * S ** 2 * np.clip(1 - (Tt * Lr) / 4, 0, 1) ** 2   # front corners flare forward
            P = np.stack([X, Y, Z], -1)
            dv = np.linalg.norm(np.diff(P, axis=0), axis=-1)
            arc = np.concatenate([np.zeros((1, nt)), np.cumsum(dv, 0)], 0)
            Vv = arc[-1:] - arc
            UV = np.stack([Y - yf, Vv], -1)
            B[tiles].add(surface(P, UV, flip=(side > 0)))
            B['wood'].add(surface(P - (0, 0, 0.32), None, flip=(side < 0)))
            # vermilion tile band along the front edge
            nb = max(2, int(1.6 / (Lr / (nt - 1))) + 1)
            band = P[:, :nb].copy() + (0, 0, 0.04)
            band[:, -1] = P[:, min(nb - 1, nt - 1)] + (0, 0, 0.04)
            B['tile_r'].add(surface(band, UV[:, :nb], flip=(side > 0)))
            edges[side] = P
        # barge boards + teeth + horns
        for side in (-1, 1):
            P = edges[side]
            front = P[:, 0] + (0, -0.12, 0.22)
            B['gold'].add(sweep(front, rect_prof(0.32, 0.5)))
            top = front + (0, 0, 0.27)
            frames = along(top[::-1] if side > 0 else top, 0.38, 0.2, up=(0, -0.3, 1))
            B['gold'].inst(T['flame'], [f @ mat4(scale=(1.0, 1.0, 1.1)) for f in frames])
            # small rosettes on the board face
            fr = along(front if side > 0 else front[::-1], 0.9, 0.45)
            B['gold2'].inst(T['rosette'], [f @ mat4((0, -0.17, 0), (math.pi / 2, 0, 0), 0.16) for f in fr])
            # eave fascia and hanging teeth
            eave = P[-1] + (0, 0, -0.18)
            B['gold'].add(sweep(eave, rect_prof(0.2, 0.42)))
            fr = along(eave, 0.5, 0.25)
            B['gold'].inst(T['tooth'], [f @ mat4((0, 0, -0.18), (math.pi, 0, 0), (0.9, 1, 0.9)) for f in fr])
            # horn at front eave corner
            B['gold'].add(horn_curl(P[-1, 0] + (0, -0.1, 0.25), (side * 0.6, -0.5, 0.2), size=1.3, r0=0.17))
            if back_face:
                B['gold'].add(horn_curl(P[-1, -1] + (0, 0.1, 0.25), (side * 0.6, 0.5, 0.2), size=1.3, r0=0.17))
        if ridge:
            rp = np.array([(xc, yf - 0.2, za + 0.15), (xc, yb, za + 0.15)])
            B['gold'].add(sweep(rp, circle_prof(0.22, 10)))
            fr = along(rp, 0.7, 0.6)
            B['gold'].inst(T['flame'], [f @ mat4((0, 0, 0.15), (0, 0, 0), (1.2, 1.2, 1.3)) for f in fr])
        # pediment (gable face)
        zb = ze + (za - ze) * (1 - hw / hwe) ** 1.35
        yp = yf + 0.55
        ss = np.linspace(-1, 1, 41)
        top = [(xc + v * hw * 0.98, yp, ze + (za - ze) * (1 - abs(v) * hw / hwe) ** 1.35 - 0.25) for v in ss]
        poly = top + [(xc + hw * 0.98, yp, zb - 0.9), (xc - hw * 0.98, yp, zb - 0.9)]
        n = len(poly)
        g = Geo(poly, list(range(n))[::-1], [n])
        B[pedmat].add(g)
        # vermilion + gold bands following the rake under the barge boards (ref: orange roof borders)
        tp = np.array(top) + (0, -0.08, 0)
        B['verm'].add(sweep(tp, rect_prof(0.14, 0.55, 0.0, -0.32)))
        B['gold'].add(sweep(tp + (0, -0.04, 0), rect_prof(0.12, 0.09, 0.0, -0.66)))
        fr = along(tp + (0, -0.12, -0.05), 0.42, 0.21)
        B['gold'].inst(T['bead'], [f @ mat4((0, 0, -0.85), scale=0.07) for f in fr])
        hgt = za - zb
        B['gold'].add(sweep(np.array([(xc - hw * 0.98, yp - 0.1, zb - 0.6), (xc + hw * 0.98, yp - 0.1, zb - 0.6)]), rect_prof(0.35, 0.5)))
        if ped == 'clock':
            R = min(hgt * 0.36, hw * 0.42)
            self.clock(np.array([xc, yp - 0.05, zb + hgt * 0.38]), R)
        # ornament field: rosettes in triangle grid
        mats = []
        cz = zb + hgt * 0.38
        Rc = min(hgt * 0.36, hw * 0.42) if ped == 'clock' else 0.6

        def inside(xx, zz, m=0.35):
            if zz < zb + m or zz > za - 0.6:
                return False
            frac = (zz - zb) / max(hgt, 1e-3)
            return abs(xx) < hw * (1 - frac) * 0.92 - m
        for k in range(-12, 13):
            th = math.pi / 2 + k * math.radians(15.0)
            for j, rr in enumerate(np.arange(Rc + 0.55, hw * 1.6, 0.62)):
                xx, zz = rr * math.cos(th), cz + rr * math.sin(th)
                if not inside(xx, zz):
                    continue
                sc_ = (0.3, 0.2, 0.24)[j % 3] * (1.0 if k % 2 == 0 else 0.8)
                mats.append(mat4((xc + xx, yp - 0.02, zz), (math.pi / 2, 0, 0), sc_))
        B['gold2'].inst(T['rosette'], mats)
        # gold rays along the radial lines (filigree spokes between the rosettes)
        for k in range(-12, 13, 2):
            th = math.pi / 2 + k * math.radians(15.0)
            pts = [(xc + rr * math.cos(th), yp - 0.04, cz + rr * math.sin(th)) for rr in np.linspace(Rc + 0.3, hw * 1.6, 24)
                   if inside(rr * math.cos(th), cz + rr * math.sin(th), 0.25)]
            if len(pts) >= 2:
                B['gold'].add(sweep(np.array(pts), rect_prof(0.05, 0.05), up=(0, -1, 0)))
        if crest:
            self.gear_crest(np.array([xc, yf - 0.2, za + 0.3]), 1.0 + hw * 0.04)

    def clock(self, c, R, facing=(0, -1, 0)):
        """Pediment clock rosette: toothed gold rim, white dial, numerals, hands, sunburst."""
        B = self.B
        Mf = mat4(c, (math.pi / 2, 0, 0))   # local +Z -> -Y (facing)
        rim = lathe([(R * 0.86, -0.1), (R, -0.1, R * 0.07), (R, 0.25, R * 0.07), (R * 0.93, 0.35), (R * 0.86, 0.3)], teeth=48, closed=True)
        B['gold'].add(rim, M=Mf)
        dial = lathe([(0.001, 0.05), (R * 0.87, 0.05), (R * 0.87, 0.12)], seg=64)
        B['marble'].add(dial, M=Mf)
        ring2 = lathe([(R * 0.55, 0.1), (R * 0.6, 0.1), (R * 0.6, 0.22), (R * 0.55, 0.22)], seg=64, closed=True)
        B['gold'].add(ring2, M=Mf)
        # numerals as bars, minute ticks
        for k in range(60):
            a = k / 60 * TAU
            big = k % 5 == 0
            L_ = R * (0.16 if big else 0.06)
            g = box((R * (0.045 if big else 0.015), L_, 0.08), (0, R * 0.78 - L_ / 2, 0.16))
            B['gold'].add(g, M=Mf @ mat4(rot=(0, 0, a)))
        # sunburst spokes inside
        for k in range(24):
            a = k / 24 * TAU
            g = box((R * 0.03, R * 0.42, 0.05), (0, R * 0.3, 0.14))
            B['gold'].add(g, M=Mf @ mat4(rot=(0, 0, a)))
        # hands
        B['dark'].add(box((R * 0.06, R * 0.62, 0.06), (0, R * 0.28, 0.32)), M=Mf @ mat4(rot=(0, 0, 0.6)))
        B['dark'].add(box((R * 0.08, R * 0.45, 0.06), (0, R * 0.2, 0.38)), M=Mf @ mat4(rot=(0, 0, -2.1)))
        B['gold'].add(lathe([(R * 0.12, 0.1), (R * 0.12, 0.35), (R * 0.06, 0.5), (0.001, 0.55)], seg=24), M=Mf)
        # outer beads
        B['gold'].inst(self.T['bead'], [Mf @ mat4((R * 1.12 * math.cos(k / 36 * TAU), R * 1.12 * math.sin(k / 36 * TAU), 0.1), scale=R * 0.035) for k in range(36)])

    def gear_crest(self, c, s=1.0):
        """Apex crest: a toothed half-halo standing in the XZ plane + spike + orb."""
        B = self.B
        Mf = mat4(c, (math.pi / 2, 0, 0))
        halo = lathe([(0.75 * s, -0.08 * s), (1.0 * s, -0.08 * s, 0.16 * s), (1.0 * s, 0.08 * s, 0.16 * s), (0.75 * s, 0.08 * s)],
                     teeth=24, closed=True)
        B['gold'].add(halo, M=Mf @ mat4((0, 0.55 * s, 0)))
        B['gold'].add(lathe([(0.25 * s, 0), (0.3 * s, 0.2 * s), (0.12 * s, 0.6 * s), (0.2 * s, 0.9 * s), (0.05 * s, 1.4 * s),
                             (0.08 * s, 1.6 * s), (0.001, 2.6 * s)], seg=16), M=mat4(c))
        B['gold'].add(uvsphere(0.18 * s, 16, 8), M=mat4(c + (0, 0, 1.75 * s)))

    def skirt(self, cx, cy, ox, oy, ix, iy, z0, z1, upturn=1.2, flare=0.9, nt=7, fringe=True, tiles='tile', hips=True):
        B, T = self.B, self.T
        C = [(1, -1), (1, 1), (-1, 1), (-1, -1)]
        po, pi_, wts, diag = [], [], [], []
        for k in range(4):
            a, b_ = C[k], C[(k + 1) % 4]
            Lside = abs(a[0] - b_[0]) * ox + abs(a[1] - b_[1]) * oy
            m = max(3, int(Lside / 0.8))
            for j in range(m):
                f = j / m
                sx = a[0] + (b_[0] - a[0]) * f; sy = a[1] + (b_[1] - a[1]) * f
                po.append((cx + sx * ox, cy + sy * oy)); pi_.append((cx + sx * ix, cy + sy * iy))
                d = min(f * Lside, (1 - f) * Lside)
                wts.append(max(0.0, 1 - d / 3.0) ** 2)
                cn = a if f < 0.5 else b_
                diag.append((cn[0] / math.sqrt(2), cn[1] / math.sqrt(2)))
        po, pi_, wts, diag = map(np.array, (po, pi_, wts, diag))
        t = np.linspace(0, 1, nt)[:, None]
        X = po[None, :, 0] * (1 - t) + pi_[None, :, 0] * t + diag[None, :, 0] * flare * wts[None] * (1 - t) ** 2
        Y = po[None, :, 1] * (1 - t) + pi_[None, :, 1] * t + diag[None, :, 1] * flare * wts[None] * (1 - t) ** 2
        Z = z0 + (z1 - z0) * t ** 1.5 + upturn * wts[None] * (1 - t) ** 2.5 + 0 * X
        P = np.stack([X, Y, Z], -1)
        per = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(po, axis=0), axis=1))])
        dv = np.linalg.norm(np.diff(P, axis=0), axis=-1)
        arc = np.concatenate([np.zeros((1, P.shape[1])), np.cumsum(dv, 0)], 0)
        UV = np.stack([np.broadcast_to(per[None], X.shape), arc], -1)
        B[tiles].add(surface(P, UV, closed_u=True))
        B['wood'].add(surface(P - (0, 0, 0.3), None, closed_u=True, flip=True))
        eave = P[0] + (0, 0, -0.15)
        B['gold'].add(sweep(eave, rect_prof(0.22, 0.4), closed_path=True))
        if fringe:
            fr = along(np.concatenate([eave, eave[:1]]), 0.5, 0.2)
            B['gold'].inst(T['tooth'], [f @ mat4((0, 0, -0.15), (math.pi, 0, 0), (0.9, 1, 0.9)) for f in fr])
            # little hanging gold bells under the eave (sparkle + density)
            fr = along(np.concatenate([eave, eave[:1]]), 1.7, 0.85)
            B['gold'].inst(T['bell'], [f @ mat4((0, 0, -0.5)) for f in fr])
        top = P[-1] + (0, 0, 0.1)
        B['gold'].add(sweep(top, circle_prof(0.16, 8), closed_path=True))
        if hips:
            idx = [int(np.argmax(wts[i0:i0 + 999] if False else 0)) for i0 in range(0)]
            corners = np.where(wts > 0.999)[0]
            for ci in corners:
                hp = P[:, ci] + (0, 0, 0.12)
                B['gold'].add(sweep(hp, circle_prof(0.14, 8)))
                fr = along(hp, 0.55, 0.3)
                B['gold'].inst(T['flame'], [f @ mat4(scale=0.8) for f in fr])
                d = diag[ci]
                B['gold'].add(horn_curl(P[0, ci] + (0, 0, 0.2), (d[0], d[1], 0.1), size=1.0, r0=0.14))
        return P

    # ---------------------------------------------------------------- spires & rings
    def gear_spire(self, x, y, z0, r0=2.4, n=9, ring_h=1.3, needle=8.0, name='spire', plinth=True):
        B = self.B
        if self.ring_mesh is None:
            g = ring_mesh_geo()
            self.ring_mesh = MB().add(g).build('RingMesh', [self.mats['gold']], self.coll, sharp=30, bevel_w=0.012).data
            bpy.data.objects.remove(bpy.data.objects['RingMesh'])
        z = z0
        if plinth:
            for k, (hw, hh) in enumerate(((r0 * 1.35, 1.2), (r0 * 1.2, 1.0), (r0 * 1.05, 0.8))):
                B['marble'].add(box_mm(x - hw, y - hw, z, x + hw, y + hw, z + hh))
                B['gold'].add(box_mm(x - hw - 0.05, y - hw - 0.05, z + hh - 0.12, x + hw + 0.05, y + hw + 0.05, z + hh))
                z += hh
        zz = z
        core = []
        for i in range(n):
            f = i / max(1, n - 1)
            r = r0 * (1 - 0.68 * f)
            h = ring_h * (1 - 0.45 * f)
            core += [(r * 0.63, zz), (r * 0.58, zz + h * 1.32)]
            zz += h * 1.32
        core.append((r0 * 0.2, zz + 0.4))
        B['glaze'].add(lathe(core, seg=24), M=mat4((x, y, 0)))
        zz = z
        for i in range(n):
            f = i / max(1, n - 1)
            r = r0 * (1 - 0.68 * f)
            h = ring_h * (1 - 0.45 * f)
            o = bpy.data.objects.new(f'{name}_ring{i}', self.ring_mesh)
            (self.coll or bpy.context.scene.collection).objects.link(o)
            bv = o.modifiers.new('Bevel', 'BEVEL')
            bv.width = 0.012; bv.segments = 2; bv.limit_method = 'ANGLE'; bv.angle_limit = math.radians(30)
            o.location = (x, y, zz)
            o.scale = (r, r, h)
            o.rotation_euler[2] = random.uniform(0, 6.28)
            speed = (0.25 + 0.35 * f) * (1 if i % 2 == 0 else -1)
            self.rings.append((o, speed))
            # collar (glazed bead between rings)
            B['gold'].add(lathe([(r * 0.66, zz + h), (r * 0.74, zz + h + 0.12 * h), (r * 0.66, zz + h + 0.3 * h)], seg=24), M=mat4((x, y, 0)))
            zz += h * 1.32
        # needle
        nd = [(r0 * 0.3, zz), (r0 * 0.38, zz + 0.3), (r0 * 0.2, zz + 0.7), (r0 * 0.28, zz + 1.1), (r0 * 0.12, zz + 1.6),
              (r0 * 0.09, zz + needle * 0.55), (r0 * 0.14, zz + needle * 0.6), (r0 * 0.06, zz + needle * 0.66), (0.001, zz + needle)]
        B['gold'].add(lathe(nd, seg=16), M=mat4((x, y, 0)))
        for k, fz in enumerate((0.35, 0.5, 0.72)):
            B['gold'].add(uvsphere(r0 * (0.16 - 0.03 * k), 14, 8), M=mat4((x, y, zz + needle * fz)))
        return zz + needle

    # ---------------------------------------------------------------- orrery
    def orrery(self, c, R=8.0, name='orrery'):
        B = self.B
        c = np.asarray(c, float)
        # pedestal (static)
        B['gold'].add(lathe([(R * 0.35, -R * 0.95), (R * 0.3, -R * 0.85), (R * 0.12, -R * 0.75), (R * 0.08, -R * 0.2), (R * 0.12, -R * 0.12),
                             (R * 0.04, 0)], seg=32), M=mat4(c))
        for k in range(4):
            a = k / 4 * TAU + math.pi / 4
            pts = [c + (math.cos(a) * R * rr, math.sin(a) * R * rr, -R * zz) for rr, zz in
                   ((0.33, 0.9), (0.6, 0.85), (0.85, 0.65), (1.02, 0.35), (1.08, 0.0))]
            B['gold'].add(sweep(pts, circle_prof(R * 0.022, 8)))
        sets = [  # radius, width, tilt, heading, speed rad/s, teeth
            (1.05, 0.06, 0.0, 0.0, 0.12, 120), (0.93, 0.05, math.radians(23.4), 0.3, -0.22, 108),
            (0.82, 0.05, math.radians(65), 1.1, 0.3, 96), (0.7, 0.045, math.radians(90), 0.0, -0.4, 84),
            (0.58, 0.04, math.radians(40), 2.0, 0.55, 72), (0.46, 0.035, math.radians(110), 0.7, -0.7, 60)]
        objs = []
        for k, (rr, w, tilt, head, sp, teeth) in enumerate(sets):
            rad = R * rr
            ww = R * w
            th = ww * 0.45
            prof = [(rad - ww, -th), (rad, -th, ww * 0.25), (rad, th, ww * 0.25), (rad - ww, th)]
            g = lathe(prof, teeth=teeth, closed=True)
            # graduation marks + jewels on top face
            nm = 72
            marks = instances(box((ww * 0.06, ww * 0.5, th * 0.6), (0, 0, 0)),
                              [mat4((math.cos(a) * (rad - ww * 0.5), math.sin(a) * (rad - ww * 0.5), th), (0, 0, a + math.pi / 2)) for a in np.arange(nm) / nm * TAU])
            g = merge([g, marks])
            o = MB().add(g).build(f'{name}_ring{k}', [self.mats['gold']], self.coll, sharp=30, bevel_w=ww * 0.04)
            o.location = c
            o.rotation_mode = 'ZXY'
            o.rotation_euler = (tilt, head, 0.0)
            objs.append(o)
            self.rings.append((o, sp))
            # a planet on this ring
            if k >= 1:
                p = MB().add(uvsphere(R * (0.05 + 0.012 * k), 20, 10)).build(f'{name}_pl{k}', [self.mats['gold'] if k % 2 else self.mats['glaze']], self.coll)
                p.parent = o
                p.location = (rad + R * 0.08, 0, 0)
        sun = self.orrery_heart(c, R)
        self.orrery_c, self.orrery_R = c, R
        return objs

    def orrery_heart(self, c, R):
        """Centre of the orrery: teal enamel globe in a gold armillary cage, wrapped by a sunburst of
        gear-tooth flames (replaces the old plain sun orb that read as a light bulb)."""
        mats = self.mats
        G, E = MB(), MB()
        r = R * 0.13
        # enamel globe with gold latitude bands
        E.add(uvsphere(r, 48, 24), M=mat4(c))
        for lat in (-0.6, -0.3, 0.0, 0.3, 0.6):
            rr = r * math.cos(math.asin(lat)) * 1.01
            G.add(lathe([(rr - 0.03, r * lat - 0.035), (rr + 0.035, r * lat - 0.035, 0.01), (rr + 0.035, r * lat + 0.035, 0.01),
                         (rr - 0.03, r * lat + 0.035)], teeth=int(2.5 * (36 + 30 * math.cos(lat))), closed=True), M=mat4(c))
        # gold star studs on the enamel
        rng = np.random.default_rng(17)
        dirs = rng.normal(size=(140, 3)); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
        G.inst(uvsphere(1.0, 8, 5), [mat4(tuple(np.asarray(c) + d * r * 1.005), scale=r * rng.uniform(0.012, 0.03)) for d in dirs])
        # armillary meridians (static, toothed)
        for k, (rx, rz) in enumerate(((math.pi / 2, 0.0), (math.pi / 2, math.pi / 2), (math.radians(23.4), 0.3))):
            rm = r * (1.22 + 0.06 * k)
            G.add(lathe([(rm - 0.06, -0.05), (rm, -0.05, 0.022), (rm, 0.05, 0.022), (rm - 0.06, 0.05)], teeth=160, closed=True),
                  M=mat4(c, (rx, 0, rz)))
        # sunburst: tapered flame rays on a fibonacci sphere, alternating long / short
        # sunburst crown: flame rays in the equatorial band (+ shorter tilted rows), polar finials
        # flat halo of blades in the equatorial plane: long straight rays alternating with short wavy flames
        ray = flame_geo(h=1.0, w=0.26, t=0.04, curl=0.3, n=10)      # long curling flame blade
        fl = flame_geo(h=1.0, w=0.3, t=0.04, curl=-0.3, n=8)          # short flame, curling the other way
        Ms, Mr = [], []
        nrr = 32
        for i in range(nrr):
            th = i / nrr * TAU
            d = np.array([math.cos(th), math.sin(th), 0.0])
            z = d; x = np.array([0, 0, 1.0]); yv = np.cross(z, x)
            if i % 2 == 0:
                Mr.append(frame_mat(np.asarray(c) + d * r * 1.3, yv * r * 0.9, -x * r * 0.9, z * r * 0.58))
            else:
                Ms.append(frame_mat(np.asarray(c) + d * r * 1.3, yv * r * 0.7, -x * r * 0.7, z * r * 0.32))
        G.inst(ray, Mr)
        G.inst(fl, Ms)
        # a toothed halo ring carrying the rays
        G.add(lathe([(r * 1.26, -0.06), (r * 1.4, -0.06, 0.05), (r * 1.4, 0.06, 0.05), (r * 1.26, 0.06)], teeth=96, closed=True), M=mat4(c))
        for sz in (1, -1):
            G.add(lathe([(r * 0.22, 0), (r * 0.3, r * 0.12), (r * 0.1, r * 0.3), (r * 0.14, r * 0.45), (r * 0.04, r * 0.75),
                         (0.001, r * 1.1)], seg=24), M=mat4(tuple(np.asarray(c) + (0, 0, sz * r * 0.98)), (0 if sz > 0 else math.pi, 0, 0)))
        heart = G.build('OrreryHeartGold', [mats['gold']], self.coll, sharp=30, bevel_w=0.01)
        globe = E.build('OrreryGlobe', [mats['enamel'] if 'enamel' in mats else mats['glaze']], self.coll)
        return heart

    # ---------------------------------------------------------------- small architecture
    def balustrade(self, p0, p1, z, h=1.0, spacing=0.34, post=3.2):
        B, T = self.B, self.T
        p0 = np.array([p0[0], p0[1], z]); p1 = np.array([p1[0], p1[1], z])
        B['marble'].add(sweep(np.array([p0 + (0, 0, 0.08), p1 + (0, 0, 0.08)]), rect_prof(0.34, 0.16)))
        B['marble'].add(sweep(np.array([p0 + (0, 0, h - 0.07), p1 + (0, 0, h - 0.07)]), rect_prof(0.4, 0.14)))
        B['gold'].add(sweep(np.array([p0 + (0, 0, h + 0.01), p1 + (0, 0, h + 0.01)]), rect_prof(0.2, 0.04)))
        fr = along(np.array([p0, p1]), spacing, spacing / 2)
        B['marble'].inst(T['baluster'], [f @ mat4((0, 0, 0.16), scale=(1, 1, (h - 0.3) / 0.75)) for f in fr])
        fr = along(np.array([p0, p1]), post, 0.0)
        for f in fr:
            B['marble'].add(box((0.42, 0.42, h + 0.12), (0, 0, (h + 0.12) / 2)), M=f)
            B['gold'].add(T['finial'], M=f @ mat4((0, 0, h + 0.12), scale=1.0))

    def column_row(self, pts, z0, h, r):
        base, shaft, cap = column_geos(h, r)
        mats = [mat4((x, y, z0)) for x, y in pts]
        self.B['marble'].inst(base, mats)
        self.B['verm'].inst(shaft, mats)
        self.B['gold'].inst(cap, mats)

    def window(self, c, w, h, facing=(0, -1, 0), depth=0.4):
        """Gold pointed window frame with dark lattice, facing -Y (or +/-X)."""
        B = self.B
        fx = np.array(facing, float)
        side = np.cross((0, 0, 1), fx)
        c = np.asarray(c, float)
        pts = []
        for v in np.linspace(0, 1, 6):
            pts.append(c + side * (-w / 2) + (0, 0, h * 0.75 * v))
        for v in np.linspace(0, 1, 13):
            a = v * math.pi
            pts.append(c + side * (-w / 2 * math.cos(a)) + (0, 0, h * 0.75 + h * 0.25 * math.sin(a) ** 0.7 + 0.18 * h * (1 - abs(math.cos(a))) ** 3))
        for v in np.linspace(1, 0, 6):
            pts.append(c + side * (w / 2) + (0, 0, h * 0.75 * v))
        pts = np.array(pts) + fx * 0.05
        B['gold'].add(sweep(pts, rect_prof(0.28, 0.3), up=tuple(fx)))
        B['dark'].add(box_mm(*(np.minimum(c - side * w / 2, c + side * w / 2) + (0, 0, 0) - (0, 0, 0)), 0, 0, 0) if False else
                      box((abs(side[0]) * w + abs(fx[0]) * 0.1, abs(side[1]) * w + abs(fx[1]) * 0.1, h), c + (0, 0, h / 2) + fx * 0.01))
        # lattice bars
        for k in range(1, 4):
            B['gold'].add(box((abs(side[0]) * 0.06 + abs(fx[0]) * 0.08, abs(side[1]) * 0.06 + abs(fx[1]) * 0.08, h * 0.95),
                              c + side * (-w / 2 + w * k / 4) + (0, 0, h * 0.47) + fx * 0.06))
        for k in range(1, 5):
            B['gold'].add(box((abs(side[0]) * w + abs(fx[0]) * 0.08, abs(side[1]) * w + abs(fx[1]) * 0.08, 0.06),
                              c + (0, 0, h * 0.75 * k / 4) + fx * 0.06))
        # crest above
        rz = math.pi / 2 if abs(fx[0]) > 0.5 else 0.0
        B['gold'].inst(self.T['flame'], [mat4(c + (0, 0, h * 1.02) + fx * 0.1 + side * (dx * w * 0.5), (0, 0, rz), (1.4, 1.4, 1.6 - abs(dx)))
                                        for dx in (-0.6, -0.3, 0, 0.3, 0.6)])
        B['gold'].add(rosette_geo(0.35), M=mat4(c + (0, 0, h * 0.86) + fx * 0.12, face_rot(fx)))

    def relief_panel(self, c, w, h, facing=(0, -1, 0), pitch=0.42):
        """Teal enamel tile panel in a gold frame, subdivided by gold muntins, a gold rosette in each cell."""
        B = self.B
        fx = np.array(facing, float)
        side = np.cross((0, 0, 1), fx)
        c = np.asarray(c, float)
        ax_ = np.abs(side); af = np.abs(fx)

        def slab(wd, hh, dz, depth, off):
            return box((ax_[0] * wd + af[0] * depth, ax_[1] * wd + af[1] * depth, hh), c + (0, 0, dz) + fx * off)
        B['gold'].add(slab(w, h, h / 2, 0.12, 0.02))
        B['enamel'].add(slab(w - 0.24, h - 0.24, h / 2, 0.14, 0.03))
        cell = max(0.7, pitch * 2.2)
        nx = max(1, int(round((w - 0.24) / cell))); nz = max(1, int(round((h - 0.24) / cell)))
        cw = (w - 0.24) / nx; ch = (h - 0.24) / nz
        for i in range(1, nx):
            B['gold'].add(box((ax_[0] * 0.07 + af[0] * 0.05, ax_[1] * 0.07 + af[1] * 0.05, h - 0.24),
                              c + side * (-(w - 0.24) / 2 + i * cw) + (0, 0, h / 2) + fx * 0.11))
        for j in range(1, nz):
            B['gold'].add(box((ax_[0] * (w - 0.24) + af[0] * 0.05, ax_[1] * (w - 0.24) + af[1] * 0.05, 0.07),
                              c + (0, 0, 0.12 + j * ch) + fx * 0.11))
        mats = []
        for i in range(nx):
            for j in range(nz):
                p = c + side * (-(w - 0.24) / 2 + (i + 0.5) * cw) + (0, 0, 0.12 + (j + 0.5) * ch) + fx * 0.1
                mats.append(mat4(tuple(p), face_rot(fx), min(cw, ch) * 0.36))
        B['gold2'].inst(self.T['rosette'], mats)

    def lanterns(self, pts, h=3.2, z0=0.0):
        post, cage, glass, mull = lantern_geos(h)
        mats = [mat4((x, y, z0)) for x, y in pts]
        self.B['bronze'].inst(post, mats)
        self.B['bronze'].inst(mull, mats)
        self.B['gold'].inst(cage, mats)
        self.B['glass'].inst(glass, mats)

    def stairs(self, x0, x1, y0, y1, z0, z1, n):
        B = self.B
        for k in range(n):
            ya = y0 + (y1 - y0) * k / n
            za = z0 + (z1 - z0) * (k + 1) / n
            B['marble'].add(box_mm(x0, ya, z0, x1, y1, za))
            B['gold'].add(box_mm(x0, ya - 0.03, za - 0.06, x1, ya + 0.05, za))

    def podium(self, tiers, z0=0.0, gold_trim=True):
        B = self.B
        z = z0
        for (x0, y0, x1, y1, h) in tiers:
            B['marble'].add(box_mm(x0, y0, z, x1, y1, z + h))
            # cornice + gold band + small dentils
            B['marble'].add(box_mm(x0 - 0.15, y0 - 0.15, z + h - 0.2, x1 + 0.15, y1 + 0.15, z + h))
            if gold_trim:
                B['gold'].add(box_mm(x0 - 0.03, y0 - 0.03, z + h - 0.38, x1 + 0.03, y1 + 0.03, z + h - 0.26))
            per = np.array([(x0, y0 - 0.02, z + h - 0.5), (x1, y0 - 0.02, z + h - 0.5)])
            fr = along(per, 0.6, 0.3)
            B['gold2'].inst(self.T['rosette'], [f @ mat4((0, 0, 0), (math.pi / 2, 0, 0), 0.12) for f in fr])
            z += h
        return z

    # ---------------------------------------------------------------- foliage
    def cypresses(self, pts, z0=0.0, scale=1.0):
        g = cypress_geo(seed=3)
        g2 = cypress_geo(seed=11, h=12.5, r=1.5)
        m1, m2 = [], []
        for i, (x, y) in enumerate(pts):
            # symmetric about the axis: variation keyed on |x|, y only
            hsh = (math.sin(y * 12.9898 + abs(x) * 78.233) * 43758.5453) % 1.0
            s = (0.88 + 0.24 * hsh) * scale
            M = mat4((x, y, z0), (0, 0, hsh * 6.28), (s, s, s * (0.95 + 0.1 * hsh)))
            (m1 if int(hsh * 10) % 2 else m2).append(M)
        self.B['leaf'].inst(g, m1)
        self.B['leaf'].inst(g2, m2)

    def blob_trees(self, pts, z0=0.0):
        variants = [blob_tree_geo(seed=s) for s in (1, 2, 3)]
        for i, (x, y) in enumerate(pts):
            hsh = (math.sin(y * 12.9898 + abs(x) * 78.233) * 43758.5453) % 1.0
            g, tr = variants[int(hsh * 3) % 3]
            s = 0.75 + 0.55 * hsh
            M = mat4((x, y, z0), (0, 0, hsh * 6.28), s)
            self.B['leaf2'].add(g, M=M)
            self.B['trunk'].add(tr, M=M)

    def hedge(self, x0, y0, x1, y1, h=1.1, z0=0.0):
        self.B['hedge'].add(box_mm(x0, y0, z0, x1, y1, z0 + h))

    # ---------------------------------------------------------------- finalize
    def build(self, mats):
        self.mats = mats
        return self

    def finalize(self):
        mats = self.mats
        spec = {  # key: (material, bevel width, sharp angle)
            'gold': (mats['gold'], 0.02, 35), 'gold2': (mats['gold2'], 0.0, 35), 'marble': (mats['marble'], 0.025, 35),
            'verm': (mats['verm'], 0.012, 35), 'tile': (mats['tile'], 0.0, 60), 'tile_r': (mats['tile_r'], 0.0, 60),
            'wood': (mats['wood'], 0.0, 60), 'dark': (mats['dark'], 0.0, 40), 'paving': (mats['paving'], 0.0, 40),
            'glaze': (mats['glaze'], 0.0, 35), 'glass': (mats['glass'], 0.0, 40), 'bronze': (mats['bronze'], 0.0, 40),
            'leaf': (mats['leaf'], 0.0, 89), 'leaf2': (mats['leaf2'], 0.0, 89), 'hedge': (mats['hedge'], 0.12, 35),
            'trunk': (mats['wood'], 0.0, 60), 'water': (mats['water'], 0.0, 40), 'grass': (mats['grass'], 0.0, 60),
            'flower_r': (mats['flower_r'], 0.0, 89), 'flower_w': (mats['flower_w'], 0.0, 89), 'flower_y': (mats['flower_y'], 0.0, 89), 'enamel': (mats['enamel'], 0.0, 35)}
        out = {}
        for k, mb in self.B.items():
            if not mb.parts:
                continue
            m, bw, sh = spec[k]
            out[k] = mb.build(f'T_{k}', [m], self.coll, sharp=sh, bevel_w=bw, bevel_seg=2 if bw < 0.05 else 3)
        return out


def make_materials():
    M = {
        'gold': tmat.m_gold('T_Gold'),

        'marble': tmat.m_marble('T_Marble'),
        'verm': tmat.m_lacquer('T_Verm'),
        'tile': tmat.m_tiles('T_Tiles'),
        'tile_r': tmat.m_tiles('T_TilesRed', base=(0.55, 0.06, 0.02), alt=(0.42, 0.1, 0.02), hi=(0.8, 0.35, 0.05)),
        'wood': tmat.m_wood('T_Wood'),
        'dark': tmat.m_dark('T_Dark', (0.012, 0.03, 0.035), 0.25),
        'paving': tmat.m_paving('T_Paving'),
        'glaze': tmat.m_glazed('T_Glaze'),
        'glass': tmat.m_emit_glass('T_LampGlass'),
        'bronze': tmat.m_bronze('T_Bronze'),
        'leaf': tmat.m_foliage('T_Cypress', base=(0.035, 0.11, 0.03), dark=(0.008, 0.035, 0.012), tip=(0.12, 0.2, 0.05)),
        'leaf2': tmat.m_foliage('T_Leaf', base=(0.07, 0.19, 0.035), dark=(0.015, 0.05, 0.012)),
        'hedge': tmat.m_foliage('T_Hedge', base=(0.05, 0.15, 0.03), dark=(0.012, 0.045, 0.012), scale=2.0),
        'water': tmat.m_water('T_Water'),
        'grass': tmat.m_grass('T_Grass'),
        'terrain': tmat.m_terrain('T_Terrain'),
        'flower_r': mat_principled('T_FlowerR', (0.6, 0.02, 0.025), 0.5),
        'flower_w': mat_principled('T_FlowerW', (0.85, 0.82, 0.78), 0.5),
        'flower_y': mat_principled('T_FlowerY', (0.9, 0.55, 0.05), 0.5),
        'enamel': tmat.m_enamel('T_Enamel'),
    }
    M['gold2'] = M['gold']   # one shader for all gold (compile time)
    return M


# ----------------------------------------------------------------------------- the complex

def build_complex(coll, mats, hero=True):
    T = Temple(coll).build(mats)
    B = T.B
    # ---------------- ground: courtyard paving + lawns
    PY0, PY1 = -74.0, -32.0   # pool extent
    B['paving'].add(box_mm(-10.5, -100, -0.3, -5.3, -26, 0.0))    # walks either side of the pool
    B['paving'].add(box_mm(5.3, -100, -0.3, 10.5, -26, 0.0))
    B['paving'].add(box_mm(-5.3, -100, -0.3, 5.3, PY0 - 0.3, 0.0))
    B['paving'].add(box_mm(-30, PY1 + 0.3, -0.3, 30, -12, 0.03))  # plaza before stair
    B['grass'].add(box_mm(-58, -82, -0.3, -10.5, 70, 0.02))
    B['grass'].add(box_mm(10.5, -82, -0.3, 58, 70, 0.02))
    # ---------------- reflecting pool
    B['water'].add(box_mm(-5, PY0, -0.6, 5, PY1, -0.12))
    rim = np.array([(-5.3, PY0 - 0.3, 0.1), (5.3, PY0 - 0.3, 0.1), (5.3, PY1 + 0.3, 0.1), (-5.3, PY1 + 0.3, 0.1)])
    B['marble'].add(sweep(rim, rect_prof(0.7, 0.3), closed_path=True, up=(0, 0, 1)))
    B['gold'].add(sweep(rim * (1, 1, 1) + (0, 0, 0.17), rect_prof(0.2, 0.06), closed_path=True))
    # floating gold lotus lamps along both pool edges (warm points that also double in the reflection)
    lotus = lathe([(0.02, 0.0), (0.16, 0.02), (0.24, 0.1, 0.06), (0.27, 0.18, 0.08), (0.2, 0.2), (0.06, 0.08)], teeth=10)
    flame = lathe([(0.001, 0.08), (0.045, 0.13), (0.03, 0.2), (0.001, 0.27)], seg=10)
    lm = [mat4((sx * 3.9, y, -0.12), (0, 0, (y * 7.3) % 6.28)) for sx in (-1, 1) for y in np.arange(PY0 + 3.0, PY1 - 1.0, 3.6)]
    B['gold'].inst(lotus, lm)
    B['glass'].inst(flame, lm)
    # small fountains/urns at pool ends
    for y in ():   # urns removed: they blocked the axial reflection
        B['gold'].add(lathe([(0.5, 0), (0.6, 0.1), (0.3, 0.3), (0.25, 0.7), (0.7, 1.0), (0.75, 1.15), (0.55, 1.2)], seg=24), M=mat4((0, y, -0.15)))
    # ---------------- lanterns, hedges, cypress rows
    ys = np.arange(PY0 + 4, PY1, 8.0)
    T.lanterns([(sx * 7.0, y) for sx in (-1, 1) for y in ys])
    for sx in (-1, 1):
        for y0 in np.arange(PY0, PY1 - 1, 6.0):
            T.hedge(sx * 9.6 - 0.45, y0 + 0.6, sx * 9.6 + 0.45, y0 + 5.4, 1.0)
    # flower beds between hedges and walks (red / white / gold accents)
    fl = ico(1.0, 1)
    rngf = np.random.default_rng(11)
    for key, n in (('flower_r', 2600), ('flower_w', 1600), ('flower_y', 900)):
        mats_f = []
        for k in range(n):
            sx = rngf.choice([-1, 1])
            x = sx * rngf.uniform(8.1, 9.05) if rngf.uniform() < 0.7 else sx * rngf.uniform(10.15, 11.2)
            y = rngf.uniform(PY0, PY1)
            s = rngf.uniform(0.05, 0.11)
            mats_f.append(mat4((x, y, 0.12 + rngf.uniform(0, 0.25)), (rngf.uniform(0, 3), 0, 0), (s, s, s * 0.7)))
        B[key].inst(fl, mats_f)
        B['hedge'].inst(fl, [m @ mat4(scale=(1.6, 1.6, 2.2)) for m in mats_f[:n // 3]])
    T.cypresses([(sx * 13.0, y) for sx in (-1, 1) for y in np.arange(PY0 + 1, PY1 + 2, 6.0)], scale=0.62)
    T.cypresses([(sx * 19.5, y) for sx in (-1, 1) for y in np.arange(PY0 + 4, PY1 + 2, 9.0)])
    # topiary trees beyond
    pts = []
    rng = np.random.default_rng(3)
    for k in range(16):
        xx, yy = rng.uniform(24, 54), rng.uniform(-78, 60)
        pts += [(-xx, yy), (xx, yy)]
    pts = [p for p in pts if not (abs(p[0]) < 46 and -60 < p[1] < -30 and abs(abs(p[0]) - 34) < 9)]
    # groves on the plateau outside the walls (mirrored for the axial symmetry)
    for k in range(75):
        a = rng.uniform(-math.pi / 2, math.pi / 2)
        r = rng.uniform(75, 150)
        xx, yy = abs(math.cos(a) * r) + 2, math.sin(a) * r * 1.1
        if xx < 24 and yy < -80:
            continue
        if xx < 62 and -88 < yy < 74:
            continue
        pts += [(-xx, yy), (xx, yy)]
    T.blob_trees(pts)
    # ---------------- gate + approach outside it
    gate(T, mats)
    T.lanterns([(sx * 6.6, y) for sx in (-1, 1) for y in (-99.0, -93.0)], h=4.2)
    for sx in (-1, 1):
        T.gear_spire(sx * 14.0, -93.0, 0.0, r0=1.1, n=7, ring_h=0.7, needle=4.0, name=f'approach_obelisk{sx}', plinth=True)
    # processional avenue south of the gate: a leading line for the 4B descent
    B['paving'].add(box_mm(-5.5, -150, -0.4, 5.5, -100, 0.02))
    T.lanterns([(sx * 6.4, y) for sx in (-1, 1) for y in np.arange(-146, -103, 10.5)], h=3.6)
    for sx in (-1, 1):
        T.hedge(sx * 8.4 - 0.45, -150, sx * 8.4 + 0.45, -102, 0.9)
        for y in (-122.0, -146.0):
            T.gear_spire(sx * 10.5, y, 0.0, r0=0.8, n=5, ring_h=0.55, needle=2.6, name=f'avenue_ob{sx}_{int(-y)}', plinth=True)
    for k in range(8):
        a_ = math.radians(22.5 + 45 * k)
        xx, yy = 98 * math.cos(a_), 92 * math.sin(a_) + 2
        T.gear_spire(xx, yy, 0.0, r0=1.7, n=8, ring_h=1.05, needle=6.5, name=f'outer_spire{k}', plinth=True)
    for sx in (-1, 1):
        for yy in (-116.0, -140.0):
            pavilion(T, sx * 24.0, yy)
    # ---------------- courtyard walls
    for sx in (-1, 1):
        wall_run(T, (sx * 58, -82), (sx * 58, 70))
        wall_run(T, (sx * 11.5, -82), (sx * 58, -82))
    wall_run(T, (-58, 70), (58, 70))
    # ---------------- main hall
    main_hall(T, mats)
    # ---------------- side pavilions with gear spires
    for sx in (-1, 1):
        pavilion(T, sx * 34, -45, hero=(sx < 0 and hero))
    # ---------------- rear towers
    for sx in (-1, 1):
        tower(T, sx * 34, 46)
    objs = T.finalize()
    return T, objs


def wall_run(T, a, b, h=5.0, t=1.4):
    B = T.B
    a = np.array(a, float); b = np.array(b, float)
    d = b - a; L = np.linalg.norm(d); u = d / L
    n = np.array([-u[1], u[0]])
    c = (a + b) / 2
    ang = math.atan2(u[1], u[0])
    B['marble'].add(box((L, t, h), (0, 0, h / 2)), M=mat4((c[0], c[1], 0), (0, 0, ang)))
    B['verm'].add(box((L, t + 0.1, 0.5), (0, 0, h - 0.6)), M=mat4((c[0], c[1], 0), (0, 0, ang)))
    B['gold'].add(box((L, t + 0.16, 0.12), (0, 0, h - 0.3)), M=mat4((c[0], c[1], 0), (0, 0, ang)))
    # coping: little glazed gable
    pr = np.array([(-t / 2 - 0.3, 0), (t / 2 + 0.3, 0), (0, 0.7)])
    path = np.array([(a[0], a[1], h), (b[0], b[1], h)])
    B['glaze'].add(sweep(path, pr))
    fr = along(path + (0, 0, 0.7), 2.5, 1.25)
    T.B['gold'].inst(T.T['finial'], [f @ mat4(scale=1.4) for f in fr])
    # buttress piers every 8 m
    fr = along(np.array([(a[0], a[1], 0), (b[0], b[1], 0)]), 8.0, 0.0)
    B['marble'].inst(box((1.0, t + 0.8, h + 0.6), (0, 0, (h + 0.6) / 2)), fr)
    B['gold'].inst(T.T['finial'], [f @ mat4((0, 0, h + 0.6), scale=2.0) for f in fr])


def gate(T, mats):
    B = T.B
    y0, y1 = -86.0, -78.0
    # pylons
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 4.2, sx * 11.5))
        z = 0
        for k, (inset, hh) in enumerate(((0, 6.0), (0.4, 5.0), (0.8, 4.5))):
            B['marble'].add(box_mm(x0 + inset, y0 + inset, z, x1 - inset, y1 - inset, z + hh))
            B['gold'].add(box_mm(x0 + inset - 0.06, y0 + inset - 0.06, z + hh - 0.35, x1 - inset + 0.06, y1 - inset + 0.06, z + hh - 0.2))
            B['verm'].add(box_mm(x0 + inset - 0.04, y0 + inset - 0.04, z + hh - 0.85, x1 - inset + 0.04, y1 - inset + 0.04, z + hh - 0.4))
            z += hh
        cx = (x0 + x1) / 2
        for fy, fdir in ((y0, -1), (y1, 1)):
            T.relief_panel((cx, fy + fdir * 0.0, 1.0), 4.6, 3.6, facing=(0, fdir, 0))
            T.window((cx, fy, 7.0), 2.4, 3.6, facing=(0, fdir, 0))
        T.skirt(cx, (y0 + y1) / 2, 4.6, 4.9, 2.4, 2.6, 15.5, 17.6, upturn=0.8, flare=0.5, nt=5)
        T.gear_spire(cx, (y0 + y1) / 2, 17.4, r0=1.8, n=8, ring_h=1.0, needle=6.0, name=f'gate_spire{sx}', plinth=False)
    # arch
    arch = []
    for v in np.linspace(0, 1, 25):
        a = math.pi * v
        arch.append((-4.2 * math.cos(a), 0, 8.0 + 3.0 * math.sin(a)))
    arch = np.array([(-4.2, 0, 0)] + arch + [(4.2, 0, 0)])
    for yy in (y0 + 0.4, y1 - 0.4):
        B['gold'].add(sweep(arch + (0, yy, 0), rect_prof(0.5, 0.6), up=(0, 1, 0)))
    # attic over arch with clock
    B['marble'].add(box_mm(-4.2, y0, 11.2, 4.2, y1, 15.5))
    B['verm'].add(box_mm(-4.25, y0 - 0.05, 14.4, 4.25, y1 + 0.05, 15.0))
    T.clock(np.array([0, y0 - 0.15, 13.0]), 1.5)
    T.gable(0, y0 - 1.0, y1 + 1.0, 6.5, 15.4, 21.5, ov=1.0, upturn=1.2, ped='none', back_face=True, crest=False)
    # arch soffit (barrel vault)
    vault = []
    for v in np.linspace(0, 1, 17):
        a = math.pi * v
        vault.append((-4.2 * math.cos(a), 8.0 + 3.0 * math.sin(a)))
    yy = np.array([y0, y1])
    P = np.array([[(x, y, z) for (x, z) in vault] for y in yy])
    B['verm'].add(surface(P))
    # coffers in the vault
    for v in np.linspace(0.06, 0.94, 9):
        a = math.pi * v
        for y in np.arange(y0 + 0.8, y1 - 0.5, 1.3):
            B['gold2'].add(rosette_geo(0.3), M=mat4((-4.1 * math.cos(a), y, 8.0 + 2.9 * math.sin(a)), (0, math.atan2(math.cos(a), -math.sin(a)), 0)))
    # inner jambs
    for sx in (-1, 1):
        B['marble'].add(box_mm(min(sx * 4.2, sx * 4.4), y0, 0, max(sx * 4.2, sx * 4.4), y1, 8.0))
        # passage walls: gold relief panels, pilasters, a frieze of teeth (the glide passes right by them)
        T.relief_panel((sx * 4.2, (y0 + y1) / 2, 0.7), 5.6, 4.6, facing=(-sx, 0, 0), pitch=0.46)
        T.window((sx * 4.2, (y0 + y1) / 2, 5.6), 1.6, 1.9, facing=(-sx, 0, 0))
        for yy in (y0 + 0.45, y1 - 0.45):
            B['gold'].add(box_mm(sx * 4.2 - 0.25, yy - 0.3, 0.0, sx * 4.2 + 0.25, yy + 0.3, 8.0))
            B['gold'].add(lathe([(0.45, 0), (0.45, 0.4), (0.32, 0.55), (0.36, 0.8)], seg=16), M=mat4((sx * 4.0, yy, 0)))
        fr = along(np.array([(sx * 4.05, y0, 7.75), (sx * 4.05, y1, 7.75)]), 0.38, 0.19)
        B['gold'].inst(T.T['tooth'], [f @ mat4((0, 0, 0), (math.pi, 0, 0), (0.7, 1, 0.8)) for f in fr])


def main_hall(T, mats):
    B = T.B
    tiers = [(-28, -14, 28, 40, 1.2), (-25, -11, 25, 37, 1.2), (-22, -8, 22, 34, 1.2)]
    ztop = T.podium(tiers)
    # balustrades on podium edges (front, leaving the stair gap)
    for (x0, y0, x1, y1, _), z in zip(tiers, (1.2, 2.4, 3.6)):
        e = 0.35
        T.balustrade((x0 + e, y0 + e), (-6.6, y0 + e), z, h=0.95)
        T.balustrade((6.6, y0 + e), (x1 - e, y0 + e), z, h=0.95)
        T.balustrade((x0 + e, y0 + e), (x0 + e, y1 - e), z, h=0.95)
        T.balustrade((x1 - e, y0 + e), (x1 - e, y1 - e), z, h=0.95)
    # grand stair
    T.stairs(-6, 6, -26, -8, 0, 3.6, 22)
    for sx in (-1, 1):
        x = sx * 6.3
        B['marble'].add(sweep(np.array([(x, -26.5, 0.6), (x, -8.0, 4.2)]), rect_prof(0.6, 1.2)))
        B['gold'].add(sweep(np.array([(x, -26.5, 1.25), (x, -8.0, 4.85)]), rect_prof(0.35, 0.1)))
        B['gold'].add(T.T['finial'], M=mat4((x, -26.5, 1.2), scale=2.2))
        # gear obelisks flanking the stair
        T.gear_spire(sx * 9.0, -28.0, 0.0, r0=0.9, n=6, ring_h=0.6, needle=3.0, name=f'stair_obelisk{sx}', plinth=True)
    # hall body
    x0, x1, y0, y1, z0, z1 = -16, 16, -1, 30, ztop, 13.6
    B['marble'].add(box_mm(x0, y0, z0, x1, y1, z1))
    B['verm'].add(box_mm(x0 - 0.1, y0 - 0.1, z1 - 1.6, x1 + 0.1, y1 + 0.1, z1 - 0.8))
    B['gold'].add(box_mm(x0 - 0.15, y0 - 0.15, z1 - 0.8, x1 + 0.15, y1 + 0.15, z1 - 0.65))
    B['gold'].add(box_mm(x0 - 0.15, y0 - 0.15, z1 - 1.75, x1 + 0.15, y1 + 0.15, z1 - 1.6))
    # frieze of small rosettes all around
    for path in (np.array([(x0, y0 - 0.12, z1 - 1.2), (x1, y0 - 0.12, z1 - 1.2)]),):
        fr = along(path, 0.55, 0.27)
        B['gold2'].inst(T.T['rosette'], [f @ mat4((0, 0, 0), (math.pi / 2, 0, 0), 0.22) for f in fr])
    # front wall: door + windows + relief panels
    door_c = np.array([0, y0 - 0.02, z0])
    T.window(door_c, 4.2, 7.2, facing=(0, -1, 0))
    B['verm'].add(box_mm(-2.05, y0 - 0.05, z0, 2.05, y0 + 0.02, z0 + 5.4))
    B['gold'].add(box_mm(-0.05, y0 - 0.09, z0, 0.05, y0 - 0.04, z0 + 5.4))
    B['gold2'].inst(T.T['rosette'], [mat4((xx, y0 - 0.07, zz), (math.pi / 2, 0, 0), 0.16)
                                     for xx in np.arange(-1.75, 1.8, 0.5) if abs(xx) > 0.2 for zz in np.arange(0.5, 5.2, 0.5) + z0])
    T.relief_panel((0, y0 - 0.25, z0 + 7.9), 5.5, 1.6, facing=(0, -1, 0))
    for xx in (-11.5, -6.8, 6.8, 11.5):
        T.window((xx, y0 - 0.02, z0 + 2.6), 2.2, 4.0, facing=(0, -1, 0))
        T.relief_panel((xx, y0 - 0.02, z0 + 0.3), 2.6, 1.9, facing=(0, -1, 0))
    for sx in (-1, 1):
        for yy in np.arange(4, 28, 6.0):
            T.window((sx * 16.02, yy, z0 + 2.6), 2.2, 4.0, facing=(sx, 0, 0))
    # colonnade
    YC = -6.0   # front colonnade line
    front = [(x, YC) for x in np.arange(-16.5, 16.6, 3.0)]
    sides = [(sx * 18.5, y) for sx in (-1, 1) for y in np.arange(YC, 31, 3.5)]
    T.column_row(front + sides, z0, 13.6 - z0 - 0.9, 0.5)
    # architrave on columns
    B['verm'].add(box_mm(-19.3, YC - 0.8, 12.7, 19.3, YC + 0.8, 13.6))
    B['gold'].add(box_mm(-19.4, YC - 0.9, 12.62, 19.4, YC + 0.9, 12.78))
    B['gold'].add(box_mm(-19.4, YC - 0.9, 13.55, 19.4, YC + 0.9, 13.7))
    for sx in (-1, 1):
        B['verm'].add(box_mm(sx * 18.5 - 0.8, YC - 0.8, 12.7, sx * 18.5 + 0.8, 31.0, 13.6))
    fr = along(np.array([(-19, YC - 0.85, 13.15), (19, YC - 0.85, 13.15)]), 0.62, 0.31)
    B['gold2'].inst(T.T['rosette'], [f @ mat4((0, 0, 0), (math.pi / 2, 0, 0), 0.26) for f in fr])
    # hanging gold teeth under architrave
    fr = along(np.array([(-19, YC, 12.6), (19, YC, 12.6)]), 0.45, 0.2)
    B['gold'].inst(T.T['tooth'], [f @ mat4((0, 0, 0), (math.pi, 0, 0), (0.8, 1.0, 1.2)) for f in fr])
    # porch ceiling
    B['wood'].add(box_mm(-18.5, YC, 12.9, 18.5, y0, 13.3))
    # roofs: skirts
    T.skirt(0, 13.0, 20.5, 20.0, 13.0, 12.5, 13.4, 19.0, upturn=1.4, flare=1.2, nt=8)
    T.skirt(0, 13.5, 14.0, 13.0, 8.5, 8.0, 19.4, 24.0, upturn=1.2, flare=1.0, nt=7)
    # layered front gables
    # narrow, steep stacked gables so the teal hip slopes of the skirts stay visible on both sides (ref look)
    T.gable(0, -8.0, 9.0, 10.5, 13.2, 24.0, ov=1.4, upturn=1.6, ped='clock')
    T.gable(0, -4.6, 11.0, 7.6, 19.4, 29.6, ov=1.2, upturn=1.4, ped='clock')
    T.gable(0, -1.2, 13.0, 5.2, 24.2, 33.6, ov=1.0, upturn=1.2, ped='none')
    # central drum + dome + orrery
    cx, cy = 0.0, 16.0
    zd = 24.0
    B['marble'].add(lathe([(7.5, zd), (7.5, zd + 1.0), (7.0, zd + 1.0), (7.0, zd + 6.0), (7.8, zd + 6.2), (7.8, zd + 6.8)], seg=16), M=mat4((cx, cy, 0)))
    B['gold'].add(lathe([(7.85, zd + 6.8), (7.9, zd + 7.0), (6.8, zd + 7.4), (5.0, zd + 8.6, 0.25), (2.5, zd + 9.6, 0.2), (1.2, zd + 9.9)], teeth=32), M=mat4((cx, cy, 0)))
    for k in range(16):
        a = k / 16 * TAU
        B['gold'].add(box((0.5, 0.5, 5.0), (7.05 * math.cos(a), 7.05 * math.sin(a), zd + 3.5)), M=mat4((cx, cy, 0), (0, 0, 0)))
        B['dark'].add(box((0.1, 1.4, 3.2), (6.98 * math.cos(a + TAU / 32), 6.98 * math.sin(a + TAU / 32), zd + 3.6)), M=mat4((cx, cy, 0), (0, 0, a + TAU / 32)))
    T.orrery((cx, cy, zd + 9.9 + 7.0), R=7.5)
    # big rear spires and front spires
    for sx in (-1, 1):
        T.gear_spire(sx * 24.5, 31.0, 2.4, r0=2.6, n=11, ring_h=1.5, needle=10.0, name=f'hall_spire_b{sx}')
        T.gear_spire(sx * 24.0, -10.0, 2.4, r0=2.2, n=10, ring_h=1.35, needle=9.0, name=f'hall_spire_f{sx}')


def pavilion(T, x, y, hero=False):
    B = T.B
    z = T.podium([(x - 7, y - 7, x + 7, y + 7, 1.0), (x - 6, y - 6, x + 6, y + 6, 0.8)])
    B['marble'].add(box_mm(x - 4.2, y - 4.2, z, x + 4.2, y + 4.2, z + 5.5))
    pts = [(x + sx * 5.0, y + sy * 5.0) for sx in (-1, 1) for sy in (-1, 1)] + [(x + sx * 1.7, y - 5.0) for sx in (-1, 1)]
    T.column_row(pts, z, 5.2, 0.32)
    B['verm'].add(box_mm(x - 5.5, y - 5.5, z + 5.2, x + 5.5, y + 5.5, z + 6.0))
    B['gold'].add(box_mm(x - 5.6, y - 5.6, z + 6.0, x + 5.6, y + 5.6, z + 6.12))
    T.window((x, y - 4.22, z), 1.8, 3.6, facing=(0, -1, 0))
    if hero:
        hero_tile_roof(T, x, y, z + 6.0)
    else:
        T.gable(x, y - 6.6, y + 6.6, 5.6, z + 6.0, z + 11.0, ov=1.0, upturn=1.1, ped='clock', back_face=True)
    T.gear_spire(x, y, z + 10.2, r0=0.9, n=6, ring_h=0.6, needle=3.5, name=f'pav_spire{int(x)}', plinth=False)


def tower(T, x, y):
    B = T.B
    z = T.podium([(x - 9, y - 9, x + 9, y + 9, 1.4)])
    for k in range(4):
        hw = 6.0 - k * 1.2
        hh = 4.5 - k * 0.5
        B['marble'].add(box_mm(x - hw, y - hw, z, x + hw, y + hw, z + hh))
        B['verm'].add(box_mm(x - hw - 0.05, y - hw - 0.05, z + hh - 0.9, x + hw + 0.05, y + hw + 0.05, z + hh - 0.4))
        for f in ((0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 1, 0)):
            T.window((x + f[0] * (hw + 0.02), y + f[1] * (hw + 0.02), z + 0.6), 1.2 + 0.2 * (3 - k), hh * 0.55, facing=f)
        z += hh
        T.skirt(x, y, hw + 2.0, hw + 2.0, hw - 0.6, hw - 0.6, z - 0.2, z + 1.4, upturn=0.9, flare=0.7, nt=5)
        z += 1.3
    T.gear_spire(x, y, z, r0=1.6, n=9, ring_h=1.0, needle=7.0, name=f'tower_spire{int(x)}', plinth=False)


def hero_tile_roof(T, x, y, ze, hw=5.6, Lh=6.6, za_off=5.0):
    """Gable roof with REAL barrel-tile geometry (for the 4D macro), both slopes."""
    B = T.B
    za = ze + za_off
    T.gable(x, y - Lh, y + Lh, hw, ze, za, ov=1.0, upturn=1.1, ped='clock', back_face=True, tiles='glaze')
    # tile geometry on top of the slope surfaces
    hwe = hw + 1.0
    tw, tl = 0.3, 0.38
    prof = []
    for k in range(9):
        a = math.pi * k / 8
        prof.append((0.135 * math.cos(a), 0.11 * math.sin(a)))
    for k in range(8, -1, -1):
        a = math.pi * k / 8
        prof.append((0.105 * math.cos(a), 0.08 * math.sin(a)))
    prof = np.array(prof)
    # orient CCW
    tile = sweep(np.array([(0, 0, 0), (tl * 1.08, 0, 0)]), prof, up=(0, 0, 1), scale=[1.0, 0.92])
    # pan tile: a shallow trough (concave up), wider, slipping under the neighbouring covers
    pprof = []
    for k in range(9):
        a = math.pi * k / 8
        pprof.append((-0.19 * math.cos(a), 0.045 - 0.04 * math.sin(a)))
    for k in range(8, -1, -1):
        a = math.pi * k / 8
        pprof.append((-0.19 * math.cos(a), 0.015 - 0.04 * math.sin(a)))
    pan = sweep(np.array([(0, 0, 0), (tl * 1.06, 0, 0)]), np.array(pprof)[::-1], up=(0, 0, 1), scale=[1.0, 0.95])
    mats_pan, ids_pan = [], []
    mats_all, ids, ant = [], [], []
    jr = np.random.default_rng(23)
    tid = 0
    for side in (-1, 1):
        ns = int(math.hypot(hwe, za - ze) / tl) + 1
        nt = int((2 * Lh) / tw)
        for i in range(ns):
            s = 1 - (i + 0.5) / ns       # from eave (s=1) upward
            for j in range(nt):
                tt = (j + 0.5 + 0.5 * (i % 2) * 0) / nt
                yy = y - Lh + tt * 2 * Lh
                Lr = 2 * Lh
                def P(s_, t_):
                    X = x + side * s_ * hwe
                    Z = ze + (za - ze) * (1 - s_) ** 1.35
                    w = s_ ** 3 * (max(0, 1 - (t_ * Lr) / 3.5) ** 2 + max(0, 1 - ((1 - t_) * Lr) / 3.5) ** 2)
                    Z += 1.1 * w
                    Y = y - Lh + t_ * Lr - 0.5 * s_ ** 2 * max(0, 1 - (t_ * Lr) / 4) ** 2
                    return np.array([X, Y, Z])
                p0 = P(s, tt)
                p1 = P(max(0, s - 1.0 / ns), tt)
                dx = p1 - p0
                dx /= np.linalg.norm(dx)
                e2 = P(s, min(1, tt + 0.01)) - p0
                e2 /= np.linalg.norm(e2)
                nz = np.cross(dx, e2) * (-side)
                nz /= np.linalg.norm(nz)
                ey = np.cross(nz, dx)
                # hand-laid irregularity: tiny roll / pitch / lift per tile breaks the highlight grid
                ra, pa = jr.normal(0, 0.035), jr.normal(0, 0.02)
                ey2 = ey * math.cos(ra) + nz * math.sin(ra); nz2 = np.cross(dx, ey2)
                dx2 = dx * math.cos(pa) + nz2 * math.sin(pa); nz2 = np.cross(dx2, ey2)
                border = (i == 0) or (j == 0) or (j == nt - 1)
                if j % 2 == 1 and not border:      # pan row: sits low in the channel between two cover rows
                    mats_pan.append(frame_mat(p0 + nz * (0.0 + jr.uniform(0, 0.006)), dx2, ey2, nz2))
                    ids_pan.append(tid); tid += 1
                    continue
                M = frame_mat(p0 + nz * (0.09 + jr.uniform(0, 0.012)), dx2, ey2, nz2)
                mats_all.append(M)
                ids.append(tid + (100000 if border else 0)); tid += 1
                if i == 0:
                    # gold antefix (gear-toothed end disc) at every eave tile end
                    ant.append(frame_mat(p0 - dx * 0.02 + nz * 0.07, nz, ey, -dx))
    g = instances(tile, mats_all)
    ida = np.array(ids, float)
    g.UV[:, 0] = np.repeat(ida % 100000, len(tile.I)) + 0.5
    g.UV[:, 1] += np.repeat((ida >= 100000) * 10.0, len(tile.I))
    if mats_pan:
        gp = instances(pan, mats_pan)
        gp.UV[:, 0] = np.repeat(np.array(ids_pan, float), len(pan.I)) + 0.5
        g = merge([g, gp])
    T.B['gold'].inst(lathe([(0.001, 0.0), (0.085, 0.0, 0.02), (0.085, 0.025, 0.02), (0.05, 0.04), (0.02, 0.05)], teeth=12), ant)
    T.hero_tiles = MB().add(g).build('T_HeroTiles', [T.mats['htile']], T.coll, sharp=50, bevel_w=0.0)


# ----------------------------------------------------------------------------- plateau & clouds

def plateau(coll, mat, R=175.0, size=900.0, res=4.0, seed=5):
    n = int(size / res) + 1
    xs = np.linspace(-size / 2, size / 2, n)
    X, Y = np.meshgrid(xs, xs, indexing='ij')
    ang = np.arctan2(Y, X)
    r = np.hypot(X, Y)
    rng = np.random.default_rng(seed)
    edge = R + 18 * np.sin(ang * 3 + 1.0) + 10 * np.sin(ang * 7 + 2.0) + 5 * np.sin(ang * 13)
    Z = np.zeros_like(X)
    d = r - edge
    drop = np.clip(d, 0, None)
    Z = -np.where(d > 0, 220 * (1 - np.exp(-drop / 22.0)) + drop * 0.25, 0)
    # terraces/strata noise
    for i in range(n):
        for j in range(n):
            if d[i, j] > -25:
                v = Vector((X[i, j] * 0.02, Y[i, j] * 0.02, Z[i, j] * 0.02))
                Z[i, j] += mnoise.noise(v) * 10 * min(1, max(0, (d[i, j] + 25) / 25)) + mnoise.noise(v * 4) * 3 * min(1, max(0, (d[i, j] + 25) / 25))
            else:
                Z[i, j] += mnoise.noise(Vector((X[i, j] * 0.01, Y[i, j] * 0.01, 0))) * 0.3 - 0.35
    P = np.stack([X, Y, Z], -1)
    o = geo_mesh('Plateau', surface(P, flip=True), [mat], coll, smooth=True, sharp=80)
    return o


def cloud_sea(coll, mat, z=-60.0, rmin=150.0, rmax=5000.0, n_ang=220, n_rad=90, heads=900, seed=2, center=(0, 0),
              head_r=(25, 110), name='CloudSea', clamp=None):
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 1, n_rad)
    radii = rmin * (rmax / rmin) ** (t ** 1.15)
    ang = np.linspace(0, TAU, n_ang, endpoint=False)
    Rr, A = np.meshgrid(radii, ang, indexing='ij')
    X = center[0] + Rr * np.cos(A); Y = center[1] + Rr * np.sin(A)
    H = np.zeros_like(X)
    # cumulus heads distributed with density falling with radius
    hr = rmin * (rmax / rmin) ** (rng.uniform(0, 1, heads) ** 1.6)
    ha = rng.uniform(0, TAU, heads)
    hx = center[0] + hr * np.cos(ha); hy = center[1] + hr * np.sin(ha)
    hs = rng.uniform(head_r[0], head_r[1], heads) * (1 + hr / 1500.0)
    hh = hs * rng.uniform(0.35, 0.7, heads)
    for k in range(heads):
        d2 = (X - hx[k]) ** 2 + (Y - hy[k]) ** 2
        cap = hh[k] * np.sqrt(np.clip(1 - d2 / hs[k] ** 2, 0, None))
        H = np.maximum(H, cap)
    for i in range(n_rad):
        for j in range(n_ang):
            v = Vector((X[i, j] * 0.004, Y[i, j] * 0.004, 0))
            H[i, j] += mnoise.noise(v) * 18 + mnoise.noise(v * 3.1) * 7
    if clamp is not None:
        H = clamp(X, Y, H)
    P = np.stack([X, Y, z + H], -1)
    return geo_mesh(name, surface(P, closed_u=True, flip=True), [mat], coll, smooth=True, sharp=89)


def cumulus_towers(coll, mat, specs, seed=21, name='Cumulus'):
    """specs: [(x, y, z_base, radius, height)] -> cauliflower towers from displaced blob clusters."""
    rng = np.random.default_rng(seed)
    base = ico(1.0, 3)
    parts = []
    for (x, y, zb, R, H) in specs:
        nb = 26
        for k in range(nb):
            t = rng.uniform(0, 1) ** 0.8
            rr = R * (1 - 0.55 * t) * rng.uniform(0.0, 0.75)
            a = rng.uniform(0, TAU)
            s = R * (0.55 - 0.3 * t) * rng.uniform(0.7, 1.15)
            c = (x + math.cos(a) * rr, y + math.sin(a) * rr, zb + t * H)
            parts.append(base.xf(mat4(c, (0, 0, rng.uniform(0, 6)), (s, s, s * 0.85))))
    g = merge(parts)
    V = g.V
    for i in range(len(V)):
        p = Vector(V[i]) * 0.012
        V[i, 2] += mnoise.noise(p) * 12.0
        V[i, 0] += mnoise.noise(p * 2.0 + Vector((5, 0, 0))) * 10.0
        V[i, 1] += mnoise.noise(p * 2.0 + Vector((0, 7, 0))) * 10.0
    return geo_mesh(name, g, [mat], coll, smooth=True, sharp=89)


def far_peaks(coll, mat, n=14, seed=4, rmin=900, rmax=2600, base_z=-120):
    rng = np.random.default_rng(seed)
    parts = []
    for k in range(n):
        a = rng.uniform(0, TAU)
        if abs(math.sin(a)) < 0.4 and math.cos(a) < 0:
            pass
        r = rng.uniform(rmin, rmax)
        h = rng.uniform(150, 420)
        w = rng.uniform(0.6, 1.2) * h
        prof = [(w, 0), (w * 0.7, h * 0.3), (w * 0.4, h * 0.65), (w * 0.12, h * 0.95), (0.001, h)]
        g = lathe(prof, seg=20, cap=False)
        V = g.V
        for i in range(len(V)):
            v = Vector(V[i] * 0.006 + (k, 0, 0))
            dd = mnoise.noise(v) * 0.35 + mnoise.noise(v * 3) * 0.12
            V[i, 0] *= (1 + dd); V[i, 1] *= (1 + dd)
        parts.append(g.xf(mat4((math.cos(a) * r, math.sin(a) * r, base_z), (0, 0, rng.uniform(0, 6)))))
    return geo_mesh('FarPeaks', merge(parts), [mat], coll, smooth=True, sharp=70)
