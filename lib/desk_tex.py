"""Act V texture generator (pure numpy, no Blender needed).

Run with Blender's bundled python (has numpy):
    "$PY" lib/desk_tex.py            -> writes film/tex/act5_*.png
Draws: self-healing cutting mat (grid, rulers, angle lines, numbers, knife marks),
blueprint sheets (watch going-train plan, car elevation), graphite sketch sheets
(exploded gear stack, wheel rim study), placeholder photo for T4.
All lettering is a single-stroke technical font defined below (ISO-3098-ish).
"""
import os, math, zlib, struct
import numpy as np

FILM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(FILM, 'tex')
RNG = np.random.default_rng(7)

# ----------------------------------------------------------------------------- png io

def save_png(path, arr):
    """arr: HxWx{3,4} float 0..1 (top row first)."""
    a = np.clip(arr, 0, 1)
    a = (a * 255 + 0.5).astype(np.uint8)
    h, w, c = a.shape
    raw = np.zeros((h, w * c + 1), np.uint8)
    raw[:, 1:] = a.reshape(h, w * c)
    ct = {3: 2, 4: 6}[c]

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, ct, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw.tobytes(), 6)) + chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)
    print('[tex] wrote', path, w, h)

# ----------------------------------------------------------------------------- noise

def upsample(g, h, w):
    gh, gw = g.shape
    ys = np.linspace(0, gh - 1, h)
    xs = np.linspace(0, gw - 1, w)
    y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int)
    y1 = np.minimum(y0 + 1, gh - 1); x1 = np.minimum(x0 + 1, gw - 1)
    fy = (ys - y0)[:, None]; fx = (xs - x0)[None, :]
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0]; b = g[y0][:, x1]; c = g[y1][:, x0]; d = g[y1][:, x1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(h, w, base=8, octaves=6, rough=0.55, seed=0):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = base * 2 ** o
        g = rng.random((max(2, int(n * h / max(h, w))) + 1, n + 1)).astype(np.float32)
        out += amp * upsample(g, h, w)
        tot += amp
        amp *= rough
    return out / tot

# ----------------------------------------------------------------------------- raster

class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.ink = np.zeros((h, w), np.float32)

    def seg(self, p0, p1, width=2.0, val=1.0, mode='max'):
        x0, y0 = p0; x1, y1 = p1
        r = width / 2 + 1.5
        xa, xb = int(max(0, math.floor(min(x0, x1) - r))), int(min(self.w, math.ceil(max(x0, x1) + r) + 1))
        ya, yb = int(max(0, math.floor(min(y0, y1) - r))), int(min(self.h, math.ceil(max(y0, y1) + r) + 1))
        if xa >= xb or ya >= yb:
            return
        X, Y = np.meshgrid(np.arange(xa, xb) + 0.5, np.arange(ya, yb) + 0.5)
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        if L2 < 1e-9:
            t = 0.0 * X
        else:
            t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L2, 0, 1)
        d = np.hypot(X - (x0 + t * dx), Y - (y0 + t * dy))
        cov = np.clip(width / 2 - d + 0.5, 0, 1) * val
        sub = self.ink[ya:yb, xa:xb]
        if mode == 'max':
            np.maximum(sub, cov, out=sub)
        else:  # screen (graphite builds up)
            sub[...] = 1 - (1 - sub) * (1 - cov)

    def poly(self, pts, width=2.0, val=1.0, closed=False, mode='max', dash=None):
        pts = list(pts)
        if closed:
            pts = pts + [pts[0]]
        if dash:
            # dash pattern in px (on, off, [on2, off2])
            acc = 0.0
            pat = list(dash); period = sum(pat)
            for a, b in zip(pts[:-1], pts[1:]):
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                s = 0.0
                while s < L:
                    ph = (acc + s) % period
                    cum = 0.0
                    for i, p in enumerate(pat):
                        if ph < cum + p:
                            on = (i % 2 == 0)
                            rem = cum + p - ph
                            break
                        cum += p
                    e = min(L, s + rem)
                    if on and L > 0:
                        pa = (a[0] + (b[0] - a[0]) * s / L, a[1] + (b[1] - a[1]) * s / L)
                        pb = (a[0] + (b[0] - a[0]) * e / L, a[1] + (b[1] - a[1]) * e / L)
                        self.seg(pa, pb, width, val, mode)
                    s = e + 1e-6
                acc += L
            return
        for a, b in zip(pts[:-1], pts[1:]):
            self.seg(a, b, width, val, mode)

    def circle(self, c, r, width=2.0, val=1.0, n=None, mode='max', dash=None, a0=0.0, a1=2 * math.pi):
        n = n or max(24, int(r * 0.6))
        pts = [(c[0] + r * math.cos(a0 + (a1 - a0) * i / n), c[1] + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
        self.poly(pts, width, val, mode=mode, dash=dash)

    def disc(self, c, r, val=1.0):
        xa, xb = int(max(0, c[0] - r - 2)), int(min(self.w, c[0] + r + 3))
        ya, yb = int(max(0, c[1] - r - 2)), int(min(self.h, c[1] + r + 3))
        if xa >= xb or ya >= yb:
            return
        X, Y = np.meshgrid(np.arange(xa, xb) + 0.5, np.arange(ya, yb) + 0.5)
        cov = np.clip(r - np.hypot(X - c[0], Y - c[1]) + 0.5, 0, 1) * val
        sub = self.ink[ya:yb, xa:xb]
        np.maximum(sub, cov, out=sub)

    def text(self, s, x, y, size, width=2.0, val=1.0, slant=0.18, mode='max', align='left', rot=0.0, jitter=0.0):
        """size = cap height in px; (x,y) = baseline-left (image coords, y down)."""
        sc = size / 6.0
        adv = 5.6 * sc
        tw = adv * len(s)
        if align == 'center':
            x -= tw / 2
        elif align == 'right':
            x -= tw
        ca, sa = math.cos(rot), math.sin(rot)
        for i, ch in enumerate(s.upper()):
            for stroke in GLYPHS.get(ch, []):
                pts = []
                for (gx, gy) in stroke:
                    lx = i * adv + (gx + gy * slant) * sc
                    ly = -gy * sc
                    if jitter:
                        lx += RNG.normal() * jitter; ly += RNG.normal() * jitter
                    pts.append((x + lx * ca - ly * sa, y + lx * sa + ly * ca))
                if len(pts) == 1:
                    pts = pts * 2
                self.poly(pts, width, val, mode=mode)
        return tw

    def arrow(self, p, d, size=14, width=2.0, val=1.0):
        a = math.atan2(d[1], d[0])
        for s in (-1, 1):
            q = (p[0] - size * math.cos(a + s * 0.3), p[1] - size * math.sin(a + s * 0.3))
            self.seg(p, q, width, val)

    def dim(self, p0, p1, off, label, size=26, width=1.6, val=1.0):
        """Dimension line between p0,p1 offset by `off` px (perpendicular), extension lines, arrows, label."""
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dx, dy)
        nx, ny = -dy / L, dx / L
        a = (p0[0] + nx * off, p0[1] + ny * off); b = (p1[0] + nx * off, p1[1] + ny * off)
        s = 1 if off >= 0 else -1
        self.seg((p0[0] + nx * 6 * s, p0[1] + ny * 6 * s), (a[0] + nx * 12 * s, a[1] + ny * 12 * s), width * 0.8, val)
        self.seg((p1[0] + nx * 6 * s, p1[1] + ny * 6 * s), (b[0] + nx * 12 * s, b[1] + ny * 12 * s), width * 0.8, val)
        self.seg(a, b, width, val)
        self.arrow(a, (-dx, -dy), width=width, val=val); self.arrow(b, (dx, dy), width=width, val=val)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        ang = math.atan2(dy, dx)
        if ang > math.pi / 2 or ang < -math.pi / 2:
            ang += math.pi
        self.text(label, mx - nx * 8 * s, my - ny * 8 * s, size, width, val, align='center', rot=ang)

# ----------------------------------------------------------------------------- stroke font

_O = [[(1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 1), (3, 0), (1, 0)]]
_P = [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)]]
GLYPHS = {
    'A': [[(0, 0), (2, 6), (4, 0)], [(0.7, 2), (3.3, 2)]],
    'B': [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)], [(3, 3), (4, 2), (4, 1), (3, 0), (0, 0)]],
    'C': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1)]],
    'D': [[(0, 0), (0, 6), (2.5, 6), (4, 4.5), (4, 1.5), (2.5, 0), (0, 0)]],
    'E': [[(4, 6), (0, 6), (0, 0), (4, 0)], [(0, 3), (3, 3)]],
    'F': [[(4, 6), (0, 6), (0, 0)], [(0, 3), (3, 3)]],
    'G': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1), (4, 3), (2, 3)]],
    'H': [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    'I': [[(1, 0), (3, 0)], [(2, 0), (2, 6)], [(1, 6), (3, 6)]],
    'J': [[(4, 6), (4, 1), (3, 0), (1, 0), (0, 1)]],
    'K': [[(0, 0), (0, 6)], [(4, 6), (0, 2)], [(1.3, 3.3), (4, 0)]],
    'L': [[(0, 6), (0, 0), (4, 0)]],
    'M': [[(0, 0), (0, 6), (2, 3), (4, 6), (4, 0)]],
    'N': [[(0, 0), (0, 6), (4, 0), (4, 6)]],
    'O': _O,
    'P': _P,
    'Q': _O + [[(2.5, 1.5), (4, 0)]],
    'R': _P + [[(2, 3), (4, 0)]],
    'S': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 4), (1, 3), (3, 3), (4, 2), (4, 1), (3, 0), (1, 0), (0, 1)]],
    'T': [[(0, 6), (4, 6)], [(2, 6), (2, 0)]],
    'U': [[(0, 6), (0, 1), (1, 0), (3, 0), (4, 1), (4, 6)]],
    'V': [[(0, 6), (2, 0), (4, 6)]],
    'W': [[(0, 6), (1, 0), (2, 4), (3, 0), (4, 6)]],
    'X': [[(0, 0), (4, 6)], [(0, 6), (4, 0)]],
    'Y': [[(0, 6), (2, 3), (4, 6)], [(2, 3), (2, 0)]],
    'Z': [[(0, 6), (4, 6), (0, 0), (4, 0)]],
    '0': _O + [[(0.4, 0.8), (3.6, 5.2)]],
    '1': [[(1, 5), (2, 6), (2, 0)], [(1, 0), (3, 0)]],
    '2': [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (0, 0), (4, 0)]],
    '3': [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3), (1.5, 3)], [(3, 3), (4, 2), (4, 1), (3, 0), (1, 0), (0, 1)]],
    '4': [[(3, 0), (3, 6), (0, 2), (4, 2)]],
    '5': [[(4, 6), (0, 6), (0, 3.5), (3, 3.5), (4, 2.5), (4, 1), (3, 0), (1, 0), (0, 1)]],
    '6': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1), (4, 2.5), (3, 3.5), (0, 3.5)]],
    '7': [[(0, 6), (4, 6), (1.5, 0)]],
    '8': [[(1, 3), (0, 4), (0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3), (1, 3), (0, 2), (0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3)]],
    '9': [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 3.5), (1, 2.5), (4, 2.5)]],
    '.': [[(1.8, 0), (2.2, 0), (2.2, 0.4), (1.8, 0.4), (1.8, 0)]],
    ',': [[(2.2, 0.4), (2.2, 0), (1.6, -0.8)]],
    '-': [[(1, 3), (3, 3)]],
    ':': [[(1.8, 0), (2.2, 0), (2.2, 0.4), (1.8, 0.4), (1.8, 0)], [(1.8, 3), (2.2, 3), (2.2, 3.4), (1.8, 3.4), (1.8, 3)]],
    '/': [[(0, 0), (4, 6)]],
    '=': [[(0.5, 2), (3.5, 2)], [(0.5, 4), (3.5, 4)]],
    '+': [[(0.5, 3), (3.5, 3)], [(2, 1.5), (2, 4.5)]],
    '*': [[(0.5, 1), (3.5, 5)], [(0.5, 5), (3.5, 1)]],
    '(': [[(2.5, 6.5), (1.3, 5), (1, 3), (1.3, 1), (2.5, -0.5)]],
    ')': [[(1.5, 6.5), (2.7, 5), (3, 3), (2.7, 1), (1.5, -0.5)]],
    '#': _O + [[(-0.5, -0.5), (4.5, 6.5)]],   # used as diameter sign
    '^': [[(1.3, 6), (1, 5.5), (1.3, 5), (1.9, 5), (2.2, 5.5), (1.9, 6), (1.3, 6)]],  # degree
    "'": [[(2, 6), (2, 4.5)]],
}

# ----------------------------------------------------------------------------- gear geometry

def gear_pts(teeth, r, depth=None, c=(0, 0), rot=0.0, tooth_frac=0.5, style='spur'):
    depth = depth or r * 0.12
    r_root, r_tip = r - depth * 0.55, r + depth * 0.45
    pts = []
    step = 2 * math.pi / teeth
    for t in range(teeth):
        if style == 'escape':  # ratchet / club teeth
            keys = [(0.0, r_root), (0.55, r_root), (0.92, r_tip), (1.0, r_tip * 0.985)]
        else:
            rise = 0.12; tf = tooth_frac
            keys = [(0.0, r_root), ((1 - tf) / 2 - rise / 2, r_root), ((1 - tf) / 2 + rise / 2, r_tip),
                    ((1 + tf) / 2 - rise / 2, r_tip), ((1 + tf) / 2 + rise / 2, r_root)]
        for f, rr in keys:
            a = rot + (t + f) * step
            pts.append((c[0] + rr * math.cos(a), c[1] + rr * math.sin(a)))
    return pts


def proj(pts3, M, off, sc):
    """pts3: Nx3 -> 2D via 3x3 rotation M (rows), orthographic, y down."""
    P = np.asarray(pts3) @ np.asarray(M).T
    return [(off[0] + p[0] * sc, off[1] - p[1] * sc) for p in P]


def rotm(ax, ay, az):
    cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rx @ Ry @ Rz

# ----------------------------------------------------------------------------- paper finishes

def finish_blueprint(cv, seed=1):
    h, w = cv.ink.shape
    ink = cv.ink
    # line bleed: cheap blur by shifted maxima average
    bl = (np.roll(ink, 1, 0) + np.roll(ink, -1, 0) + np.roll(ink, 1, 1) + np.roll(ink, -1, 1)) * 0.25
    ink = np.clip(ink * 0.85 + bl * 0.35, 0, 1)
    n1 = fbm(h, w, 6, 6, 0.6, seed)
    fib = fbm(h, w, 160, 3, 0.6, seed + 3)
    fade = upsample(np.random.default_rng(seed).random((5, 7)), h, w)
    base = np.stack([0.035 + 0.03 * n1, 0.17 + 0.07 * n1 + 0.03 * fade, 0.42 + 0.12 * n1 + 0.05 * fade], -1)
    base *= (0.92 + 0.12 * fib)[..., None]
    # edge darkening
    yy, xx = np.mgrid[0:h, 0:w]
    e = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) / (0.05 * min(h, w))
    base *= (0.75 + 0.25 * np.clip(e, 0, 1))[..., None]
    line = np.array([0.86, 0.93, 1.0])[None, None, :] * (0.85 + 0.15 * fib[..., None])
    a = (ink * (0.75 + 0.25 * n1))[..., None]
    out = base * (1 - a) + line * a
    red = getattr(cv, 'red', None)
    if red is not None:  # red-pencil markup on top of the print
        r = (red * np.clip((fib - 0.25) * 2.0, 0.4, 1.0))[..., None]
        out = out * (1 - r * 0.9) + np.array([0.95, 0.30, 0.16])[None, None, :] * r * 0.9
    return out


def markup(cv, shapes, seed=0):
    """Hand-drawn red pencil circles / arrows / notes. shapes: list of ('circle', c, r) | ('arrow', p0, p1) | ('text', s, x, y, size)."""
    rr = np.random.default_rng(seed)
    red = Canvas(cv.w, cv.h)
    for sh in shapes:
        if sh[0] == 'circle':
            _, c, r = sh
            for p in range(2):
                a0 = rr.uniform(0, 6.28); n = 90
                pts = []
                for i in range(n + 8):
                    a = a0 + 2 * math.pi * i / n
                    rad = r * (1 + 0.05 * math.sin(a * 2 + p) + 0.01 * rr.normal())
                    pts.append((c[0] + rad * math.cos(a) * 1.08, c[1] + rad * math.sin(a)))
                red.poly(pts, 4.5, 0.85, mode='screen')
        elif sh[0] == 'arrow':
            _, p0, p1 = sh
            mid = ((p0[0] + p1[0]) / 2 + 30, (p0[1] + p1[1]) / 2 - 30)
            pts = [(p0[0] + (2 * (1 - t) * t) * (mid[0] - (p0[0] + p1[0]) / 2) + (p1[0] - p0[0]) * t,
                    p0[1] + (2 * (1 - t) * t) * (mid[1] - (p0[1] + p1[1]) / 2) + (p1[1] - p0[1]) * t) for t in np.linspace(0, 1, 40)]
            red.poly(pts, 4.5, 0.85, mode='screen')
            red.arrow(pts[-1], (pts[-1][0] - pts[-4][0], pts[-1][1] - pts[-4][1]), size=34, width=4.5, val=0.85)
        elif sh[0] == 'text':
            _, s, x, y, size = sh
            red.text(s, x, y, size, 4.0, 0.85, mode='screen', jitter=1.6)
    cv.red = red.ink


def finish_graphite(cv, seed=2, tint=(0.93, 0.89, 0.80)):
    h, w = cv.ink.shape
    n1 = fbm(h, w, 5, 6, 0.6, seed)
    fib = fbm(h, w, 220, 3, 0.6, seed + 5)
    base = np.array(tint)[None, None, :] * (0.9 + 0.08 * n1[..., None] + 0.04 * fib[..., None])
    yy, xx = np.mgrid[0:h, 0:w]
    e = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) / (0.04 * min(h, w))
    base *= (0.88 + 0.12 * np.clip(e, 0, 1))[..., None]
    # graphite: tooth of paper breaks up the stroke
    grain = np.clip((fib - 0.35) * 2.5, 0.35, 1.0)
    a = (cv.ink * grain)[..., None]
    graphite = np.array([0.16, 0.16, 0.18])[None, None, :]
    return base * (1 - a * 0.92) + graphite * a * 0.92 * 0.6


def coffee_ring(img, c, r, strength=0.5, seed=4):
    h, w, _ = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ang = np.arctan2(yy - c[1], xx - c[0])
    wob = 1 + 0.02 * np.sin(ang * 3 + 1) + 0.012 * np.sin(ang * 7 + 2)
    d = np.hypot(xx - c[0], yy - c[1]) / (r * wob)
    ring = np.exp(-((d - 1.0) / 0.018) ** 2) * (0.6 + 0.4 * np.sin(ang * 2 + 0.5) ** 2)
    inner = np.clip(1 - d, 0, 1) ** 0.5 * 0.05 * (d < 1)
    gap = (np.sin(ang + 0.7) > -0.85).astype(np.float32)  # ring not quite closed
    m = (ring * gap + inner) * strength
    stain = np.array([0.42, 0.24, 0.10])[None, None, :]
    return img * (1 - m[..., None]) + img * stain * m[..., None]

# ----------------------------------------------------------------------------- sheets

def make_mat(W=4096, H=3072, cm=60.0):
    ppc = W / cm  # px per cm
    cv = Canvas(W, H)
    m = 0.9 * ppc  # margin
    nx, ny = int((W - 2 * m) / ppc), int((H - 2 * m) / ppc)
    x0, y0 = m, m
    for i in range(nx + 1):
        x = x0 + i * ppc
        wd, v = (5.0, 0.95) if i % 5 == 0 else (3.4, 0.62)
        cv.seg((x, y0), (x, y0 + ny * ppc), wd, v)
    for j in range(ny + 1):
        y = y0 + j * ppc
        wd, v = (5.0, 0.95) if j % 5 == 0 else (3.4, 0.62)
        cv.seg((x0, y), (x0 + nx * ppc, y), wd, v)
    # rulers: mm ticks along top and left edge, numbers every cm
    for i in range(nx * 10 + 1):
        x = x0 + i * ppc / 10
        L = 0.45 * ppc if i % 10 == 0 else (0.3 * ppc if i % 5 == 0 else 0.18 * ppc)
        cv.seg((x, y0 - L), (x, y0), 1.2, 0.85)
    for j in range(ny * 10 + 1):
        y = y0 + j * ppc / 10
        L = 0.45 * ppc if j % 10 == 0 else (0.3 * ppc if j % 5 == 0 else 0.18 * ppc)
        cv.seg((x0 - L, y), (x0, y), 1.2, 0.85)
    for i in range(1, nx + 1):
        cv.text(str(i), x0 + i * ppc, y0 - 0.52 * ppc, 0.26 * ppc, 2.2, 0.9, slant=0, align='center')
    for j in range(1, ny + 1):
        cv.text(str(j), x0 - 0.5 * ppc, y0 + j * ppc + 0.1 * ppc, 0.24 * ppc, 2.0, 0.9, slant=0, align='right')
    # angle lines from bottom-left grid corner
    ox, oy = x0, y0 + ny * ppc
    for deg in (15, 30, 45, 60, 75):
        a = math.radians(deg)
        L = 80 * ppc
        p1 = (ox + L * math.cos(a), oy - L * math.sin(a))
        cv.seg((ox, oy), p1, 4.0, 0.95)
        # circled label at ~24 cm
        for rr in (22, 44):
            c = (ox + rr * ppc * math.cos(a), oy - rr * ppc * math.sin(a))
            if 0 < c[0] < W - m and m < c[1] < H:
                cv.disc(c, 0.36 * ppc, 0.0)
                sub = cv.ink
                # punch a hole then draw ring + text
                xa, xb = int(c[0] - 0.4 * ppc), int(c[0] + 0.4 * ppc)
                ya, yb = int(c[1] - 0.4 * ppc), int(c[1] + 0.4 * ppc)
                X, Y = np.meshgrid(np.arange(xa, xb) + 0.5, np.arange(ya, yb) + 0.5)
                hole = np.hypot(X - c[0], Y - c[1]) < 0.36 * ppc
                sub[ya:yb, xa:xb][hole] = 0.0
                cv.circle(c, 0.36 * ppc, 1.8, 0.9)
                cv.text(f"{deg}^", c[0] + 0.03 * ppc, c[1] + 0.12 * ppc, 0.24 * ppc, 2.0, 0.95, slant=0, align='center')
    # border + logo text
    cv.poly([(x0, y0), (x0 + nx * ppc, y0), (x0 + nx * ppc, y0 + ny * ppc), (x0, y0 + ny * ppc)], 3.0, 1.0, closed=True)
    cv.text("SELF-HEALING CUTTING MAT   A2   ESC-60", W - m - 0.2 * ppc, H - 0.3 * ppc, 0.22 * ppc, 1.8, 0.7, align='right')
    ink = cv.ink
    h, w = ink.shape
    n1 = fbm(h, w, 4, 6, 0.6, 11)
    base = np.stack([0.030 + 0.012 * n1, 0.036 + 0.012 * n1, 0.036 + 0.014 * n1], -1)
    wear = fbm(h, w, 12, 5, 0.6, 12)
    a = (ink * np.clip(0.55 + 0.6 * wear, 0, 1))[..., None]
    col = base * (1 - a) + np.array([0.70, 0.74, 0.72])[None, None, :] * a
    # knife marks (alpha channel: 1 = surface, 0 = cut)
    cuts = Canvas(W, H)
    for k in range(260):
        p = (RNG.uniform(0, W), RNG.uniform(0, H))
        if RNG.random() < 0.6:  # ruler-straight cuts
            ang = RNG.choice([0, math.pi / 2]) + RNG.normal() * 0.02
        else:
            ang = RNG.uniform(0, math.pi)
        L = RNG.uniform(0.5, 9) * ppc
        cuts.seg(p, (p[0] + L * math.cos(ang), p[1] + L * math.sin(ang)), RNG.uniform(0.8, 1.6), RNG.uniform(0.3, 0.9))
    col *= (1 - 0.35 * cuts.ink)[..., None]
    alpha = 1 - cuts.ink
    return np.concatenate([col, alpha[..., None]], -1)


def title_block(cv, x, y, w, h, lines, val=1.0, size=30):
    cv.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], 3.0, val, closed=True)
    rh = h / len(lines)
    for i, (k, v) in enumerate(lines):
        yy = y + i * rh
        if i:
            cv.seg((x, yy), (x + w, yy), 1.6, val)
        cv.text(k, x + 14, yy + rh * 0.42, size * 0.45, 1.4, val * 0.8)
        cv.text(v, x + 14, yy + rh * 0.86, size * (1.2 if i == 0 else 0.8), 2.6 if i == 0 else 2.0, val)
    cv.seg((x + w * 0.62, y + rh), (x + w * 0.62, y + h), 1.6, val)


def sheet_border(cv, m, val=1.0, zones=True):
    W, H = cv.w, cv.h
    cv.poly([(m, m), (W - m, m), (W - m, H - m), (m, H - m)], 4.0, val, closed=True)
    cv.poly([(m - 18, m - 18), (W - m + 18, m - 18), (W - m + 18, H - m + 18), (m - 18, H - m + 18)], 1.6, val, closed=True)
    if zones:
        for i in range(1, 8):
            x = m + (W - 2 * m) * i / 8
            cv.seg((x, m - 18), (x, m), 1.6, val); cv.seg((x, H - m), (x, H - m + 18), 1.6, val)
        for i in range(8):
            x = m + (W - 2 * m) * (i + 0.5) / 8
            cv.text(str(i + 1), x, m - 4, 13, 1.4, val, slant=0, align='center')
        for j in range(1, 6):
            y = m + (H - 2 * m) * j / 6
            cv.seg((m - 18, y), (m, y), 1.6, val); cv.seg((W - m, y), (W - m + 18, y), 1.6, val)
        for j in range(6):
            y = m + (H - 2 * m) * (j + 0.5) / 6
            cv.text("ABCDEF"[j], m - 9, y + 7, 13, 1.4, val, slant=0, align='center')


def centre_mark(cv, c, r, val=1.0):
    cv.poly([(c[0] - r, c[1]), (c[0] + r, c[1])], 1.3, val, dash=(28, 7, 4, 7))
    cv.poly([(c[0], c[1] - r), (c[0], c[1] + r)], 1.3, val, dash=(28, 7, 4, 7))


def make_bp_watch(W=3508, H=2480):
    cv = Canvas(W, H)
    sheet_border(cv, 70)
    C = (1250, 1230)
    S = 26.0  # px per mm (5:1)
    R = 20.5 * S
    cv.circle(C, R, 3.2, 1.0, n=400)
    cv.circle(C, R - 0.9 * S, 1.6, 0.9, n=400)
    cv.circle(C, R + 2.6 * S, 1.4, 0.8, n=400, dash=(30, 10))
    centre_mark(cv, C, R + 4 * S)
    # going train
    train = [  # name, teeth, r_mm, angle_deg, dist_mm, style
        ('CENTRE WHEEL', 80, 8.6, 0, 0, 'spur'),
        ('THIRD WHEEL', 75, 7.0, -35, 13.6, 'spur'),
        ('FOURTH WHEEL', 70, 6.2, -78, 21.0 * 0.0 + 13.0, 'spur'),
        ('ESCAPE WHEEL', 15, 4.3, -120, 9.6, 'escape'),
    ]
    pos = C
    centres = []
    for i, (nm, z, r, ang, dist, st) in enumerate(train):
        if i:
            a = math.radians(ang)
            pos = (pos[0] + dist * S * math.cos(a), pos[1] - dist * S * math.sin(a))
        centres.append(pos)
        pts = gear_pts(z, r * S, c=pos, rot=i * 0.3, style=st)
        cv.poly(pts, 2.6, 1.0, closed=True)
        cv.circle(pos, r * S, 1.2, 0.75, dash=(26, 8, 4, 8))           # pitch circle
        if st == 'spur':
            cv.circle(pos, r * S * 0.76, 2.0, 0.95)                     # rim
            cv.circle(pos, r * S * 0.2, 2.0, 0.95)
            for k in range(4):
                a = k * math.pi / 2 + 0.3 * i + math.pi / 4
                for s in (-1, 1):
                    p = (pos[0] + math.cos(a) * r * S * 0.2 + s * math.sin(a) * 0.5 * S, pos[1] + math.sin(a) * r * S * 0.2 - s * math.cos(a) * 0.5 * S)
                    q = (pos[0] + math.cos(a) * r * S * 0.76 + s * math.sin(a) * 0.35 * S, pos[1] + math.sin(a) * r * S * 0.76 - s * math.cos(a) * 0.35 * S)
                    cv.seg(p, q, 1.8, 0.95)
        cv.circle(pos, 0.6 * S, 1.6, 1.0)
        centre_mark(cv, pos, r * S + 1.6 * S, 0.8)
        # pinion
        if i:
            cv.poly(gear_pts(8 if i < 3 else 7, 1.2 * S, c=pos), 1.6, 0.9, closed=True)
        # leader + label
        lx = pos[0] + (r + 4) * S * (1 if i % 2 == 0 else -1) * 0.7
        ly = pos[1] - (r + 3) * S * 0.7
        cv.seg((pos[0] + r * S * 0.5 * (1 if i % 2 == 0 else -1), pos[1] - r * S * 0.5), (lx, ly), 1.4, 0.9)
        cv.seg((lx, ly), (lx + (260 if i % 2 == 0 else -260), ly), 1.4, 0.9)
        tx = lx + 8 if i % 2 == 0 else lx - 252
        cv.text(nm, tx, ly - 10, 22, 2.0, 1.0)
        cv.text(f"Z={z}  M=0.11  #{2 * r:.1f}", tx, ly + 30, 17, 1.6, 0.9)
    # pallet fork + balance
    esc = centres[-1]
    pf = (esc[0] - 6.5 * S, esc[1] + 4.0 * S)
    cv.poly([(esc[0] - 3.5 * S, esc[1] - 1.0 * S), pf, (esc[0] - 1.5 * S, esc[1] + 4.4 * S)], 2.4, 1.0)
    cv.seg(pf, (pf[0] - 7 * S, pf[1] + 3.0 * S), 2.4, 1.0)
    bal = (pf[0] - 9.5 * S, pf[1] + 4.2 * S)
    cv.circle(bal, 5.4 * S, 2.6, 1.0); cv.circle(bal, 4.8 * S, 1.8, 0.95)
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.4
        cv.seg(bal, (bal[0] + 4.8 * S * math.cos(a), bal[1] + 4.8 * S * math.sin(a)), 2.0, 1.0)
    for k in range(18):  # timing screws
        a = k * 2 * math.pi / 18
        cv.circle((bal[0] + 5.6 * S * math.cos(a), bal[1] + 5.6 * S * math.sin(a)), 0.3 * S, 1.4, 1.0)
    # hairspring spiral
    sp = []
    for t in np.linspace(0, 13 * 2 * math.pi, 1400):
        rr = (0.9 + 3.2 * t / (13 * 2 * math.pi)) * S
        sp.append((bal[0] + rr * math.cos(t), bal[1] + rr * math.sin(t)))
    cv.poly(sp, 1.2, 0.85)
    centre_mark(cv, bal, 7 * S, 0.8)
    # dimensions
    cv.dim((C[0] - R, C[1] + R + 1.2 * S), (C[0] + R, C[1] + R + 1.2 * S), 70, "41.00")
    cv.dim(centres[0], centres[1], -90, "13.60")
    cv.dim(centres[1], centres[2], 90, "13.00")
    # detail A: enlarged escape tooth
    D = (2780, 900)
    cv.circle(D, 430, 2.2, 1.0, dash=(40, 12))
    cv.text("DETAIL A  (20:1)", D[0], D[1] - 470, 30, 2.6, 1.0, align='center')
    ept = gear_pts(15, 22 * S, c=(D[0], D[1] + 22 * S * 0.98), rot=-math.pi / 2 - 0.3, style='escape')
    clip = [(x, y) for (x, y) in ept if math.hypot(x - D[0], y - D[1]) < 410]
    if len(clip) > 1:
        cv.poly(clip, 3.0, 1.0)
    cv.text("IMPULSE FACE 6^", D[0] - 300, D[1] + 300, 20, 1.8, 0.9)
    cv.text("LOCK 1.5^  DROP 0.04", D[0] - 300, D[1] + 340, 20, 1.8, 0.9)
    # notes
    notes = ["NOTES:", "1. ALL WHEELS CUSIN 2N HARD BRASS", "2. PINIONS HARDENED + POLISHED",
             "3. JEWELS: 17 SYNTH. RUBY", "4. BEAT 18000 A/H", "5. TOLERANCES +-0.005 UNLESS NOTED"]
    for i, s in enumerate(notes):
        cv.text(s, 2380, 1560 + i * 46, 22, 2.0, 0.95)
    title_block(cv, W - 70 - 1050, H - 70 - 330, 1050, 330,
                [("TITLE", "ESCAPEMENT"), ("DRAWING", "CAL.07 GOING TRAIN - PLAN"),
                 ("SCALE  5:1      SHEET 2/7", "DWG E-0507   REV C")], 1.0, 44)
    esc = centres[-1]
    markup(cv, [('circle', esc, 6.2 * S), ('arrow', (esc[0] + 7 * S, esc[1] + 5 * S), (D[0] - 440, D[1] + 120)),
                ('text', "CHECK DROP", esc[0] - 3 * S, esc[1] + 9.5 * S, 46), ('circle', (2600, 1560 + 2 * 46 - 12), 260)], seed=3)
    return finish_blueprint(cv, 21)


def car_profile():
    """Side elevation of a low mid-engine coupe (mm). x forward->right, y up."""
    body = [(-2210, 420), (-2240, 560), (-2190, 760), (-2050, 900), (-1800, 980), (-1250, 1040),
            (-700, 1150), (-250, 1205), (250, 1190), (700, 1080), (1200, 900), (1700, 790), (2050, 700),
            (2200, 560), (2230, 420), (2150, 300), (1900, 260), (1650, 250)]
    return body


def catmull(pts, n=10, closed=False):
    P = list(pts)
    if closed:
        P = [P[-1]] + P + [P[0], P[1]]
    else:
        P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = map(np.array, (P[i - 1], P[i], P[i + 1], P[i + 2]))
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)))
    out.append(tuple(P[-2]))
    return out


def draw_wheel(cv, c, r, val=1.0, width=2.4, spokes=6, mode='max', rot=0.0):
    cv.circle(c, r, width * 1.2, val, mode=mode)
    cv.circle(c, r * 0.72, width, val, mode=mode)
    cv.circle(c, r * 0.68, width * 0.7, val * 0.8, mode=mode)
    cv.circle(c, r * 0.16, width, val, mode=mode)
    for k in range(spokes):
        a = rot + k * 2 * math.pi / spokes
        for s in (-1, 1):
            p = (c[0] + math.cos(a + s * 0.25) * r * 0.17, c[1] + math.sin(a + s * 0.25) * r * 0.17)
            q = (c[0] + math.cos(a + s * 0.09) * r * 0.66, c[1] + math.sin(a + s * 0.09) * r * 0.66)
            cv.seg(p, q, width * 0.9, val, mode=mode)
    for k in range(5):
        a = rot + k * 2 * math.pi / 5 + 0.3
        cv.circle((c[0] + math.cos(a) * r * 0.1, c[1] + math.sin(a) * r * 0.1), r * 0.018, width * 0.6, val, mode=mode)


def draw_car_side(cv, ox, oy, sc, val=1.0, width=2.6, mode='max', jitter=0.0, passes=1):
    def T(p):
        return (ox + p[0] * sc, oy - p[1] * sc)
    wheels = [(-1330, 345), (1330, 345)]
    R = 345
    for ps in range(passes):
        jx = (lambda: RNG.normal() * jitter) if jitter else (lambda: 0.0)
        body = catmull(car_profile(), 12)
        # cut wheel arches out of body line by splitting into segments away from wheels
        segs = []
        cur = []
        for p in body:
            inside = any(math.hypot(p[0] - w[0], p[1] - w[1]) < R * 1.13 for w in wheels)
            if inside:
                if len(cur) > 1:
                    segs.append(cur)
                cur = []
            else:
                cur.append((T(p)[0] + jx(), T(p)[1] + jx()))
        if len(cur) > 1:
            segs.append(cur)
        for s in segs:
            cv.poly(s, width, val, mode=mode)
        for w in wheels:
            cv.circle(T(w), R * 1.13 * sc, width, val, mode=mode, a0=math.pi * 1.04, a1=math.pi * 1.96)
            draw_wheel(cv, T(w), R * sc, val, width * 0.9, mode=mode)
        # sill line
        cv.poly([T((-950, 300)), T((950, 300))], width, val, mode=mode)
        # greenhouse
        gh = catmull([(-1150, 1000), (-700, 1110), (-250, 1160), (250, 1145), (650, 1040), (950, 930), (600, 920), (-200, 930), (-1000, 960), (-1150, 1000)], 10)
        cv.poly([T(p) for p in gh], width * 0.8, val, mode=mode)
        cv.poly([T((-250, 1150)), T((-200, 935))], width * 0.7, val, mode=mode)
        # door + intake
        cv.poly([T(p) for p in catmull([(-900, 940), (-950, 700), (-900, 330), (300, 330), (380, 600), (620, 1020)], 8)], width * 0.7, val, mode=mode)
        cv.poly([T(p) for p in catmull([(450, 520), (800, 700), (1150, 760), (1100, 600), (750, 480), (450, 520)], 8)], width * 0.7, val, mode=mode)
        for k in range(6):
            cv.poly([T((560 + k * 90, 540 + k * 25)), T((620 + k * 90, 650 + k * 20))], width * 0.5, val * 0.9, mode=mode)
        # light bar + front strip
        cv.poly([T((2050, 690)), T((2190, 620)), T((2215, 560))], width * 1.4, val, mode=mode)
        cv.poly([T((-2050, 880)), T((-2180, 760))], width * 1.4, val, mode=mode)
        # mirror
        cv.poly([T(p) for p in [(-850, 1000), (-760, 1050), (-640, 1040), (-700, 990), (-850, 1000)]], width * 0.7, val, mode=mode)
    return T


def make_bp_car(W=3508, H=2480):
    cv = Canvas(W, H)
    # v4: faint drafting grid (5 mm / 25 mm) -> lines rush under the lens anywhere on the sheet in 5B
    # v13: grid at ~25 % contrast + wider strokes so it survives mip filtering at FPV height (was 0.13 / 1.3 px)
    for i in range(0, W, 59):
        cv.seg((i, 70), (i, H - 70), 2.2 if i % 295 else 3.0, 0.26 if i % 295 else 0.42)
    for j in range(0, H, 59):
        cv.seg((70, j), (W - 70, j), 2.2 if j % 295 else 3.0, 0.26 if j % 295 else 0.42)
    sheet_border(cv, 70)
    sc = 0.5
    ox, oy = 1350, 1050
    T = draw_car_side(cv, ox, oy, sc)
    cv.poly([T((-2600, 0)), T((2600, 0))], 1.6, 0.9, dash=(40, 10, 6, 10))  # ground
    for w in (-1330, 1330):
        centre_mark(cv, T((w, 345)), 345 * sc * 1.35, 0.8)
    cv.dim(T((-2240, 0)), T((2230, 0)), 120, "4470")
    cv.dim(T((-1330, 345)), T((1330, 345)), 430, "2660")
    # section hatching inside the body side (sill + rocker), station lines
    for k in range(-9, 10):
        x = k * 230
        cv.poly([T((x, 300)), T((x, 330))], 1.2, 0.7)
        cv.text(str(k + 10), T((x, 260))[0], T((x, 260))[1], 16, 1.2, 0.6, align='center')
    for k in range(60):
        x0 = -900 + k * 30
        cv.seg(T((x0, 300)), T((x0 + 40, 250)), 1.0, 0.45)
    # DETAIL A: wheel / hub section, 1:4
    dc = (2950, 1665)
    draw_wheel(cv, dc, 300, 1.0, 2.6)
    cv.circle(dc, 360, 3.0, 1.0)
    cv.circle(dc, 340, 1.4, 0.7, dash=(20, 8))
    for k in range(40):  # tyre tread blocks
        a = k * 2 * math.pi / 40
        p = (dc[0] + 340 * math.cos(a), dc[1] + 340 * math.sin(a)); q = (dc[0] + 362 * math.cos(a + 0.03), dc[1] + 362 * math.sin(a + 0.03))
        cv.seg(p, q, 1.6, 0.8)
    for k in range(6):  # brake disc vents
        cv.circle(dc, 120 + k * 22, 1.0, 0.5, dash=(14, 10))
    cv.text("DETAIL A - WHEEL / HUB", dc[0], dc[1] - 415, 30, 2.4, 1.0, align='center')
    cv.text("SCALE 1:4    #720", dc[0], dc[1] - 378, 22, 1.8, 0.8, align='center')
    # notes block
    notes = ["NOTES:", "1. ALL DIMENSIONS IN MM", "2. BODY SURFACES TO CLASS A", "3. WHEEL BEARING PRELOAD 22 NM",
             "4. CENTRE LOCK - LH THREAD ON RH SIDE", "5. RIDE HEIGHT 95 +/- 3", "6. DO NOT SCALE"]
    for i, s in enumerate(notes):
        cv.text(s, 170, 190 + i * 42, 24, 1.8, 0.85)
    cv.dim(T((2400, 0)), T((2400, 1205)), -1, "1205")
    # top view
    oy2 = 1900
    top = catmull([(-2210, 0), (-2150, 700), (-1700, 960), (-900, 990), (0, 960), (900, 1000), (1700, 1010), (2150, 760), (2230, 0)], 10)
    topm = [(x, -y) for (x, y) in reversed(top)]
    cv.poly([(ox + x * sc, oy2 - y * sc * 0.38) for (x, y) in top + topm], 2.6, 1.0)
    cab = catmull([(-1100, 0), (-950, 560), (-200, 700), (600, 620), (950, 420), (1000, 0)], 10)
    cabm = [(x, -y) for (x, y) in reversed(cab)]
    cv.poly([(ox + x * sc, oy2 - y * sc * 0.38) for (x, y) in cab + cabm], 2.0, 1.0)
    cv.poly([(ox - 2500 * sc, oy2), (ox + 2500 * sc, oy2)], 1.3, 0.8, dash=(30, 8, 4, 8))
    # front view (right)
    fx, fy = 2950, 1050
    fr = catmull([(0, 1205), (420, 1190), (700, 1080), (930, 800), (990, 500), (960, 300), (900, 120)], 10)
    frm = [(-x, y) for (x, y) in reversed(fr)]
    cv.poly([(fx + x * 0.3, fy - y * 0.3) for (x, y) in frm + fr], 2.4, 1.0)
    for s in (-1, 1):
        cv.poly([(fx + s * 720 * 0.3, fy - 0), (fx + s * 720 * 0.3, fy - 690 * 0.3)], 9, 0.9)
        cv.poly([(fx + s * 300 * 0.3, fy - 640 * 0.3), (fx + s * 860 * 0.3, fy - 700 * 0.3)], 3.0, 1.0)
    cv.poly([(fx - 1000 * 0.3, fy), (fx + 1000 * 0.3, fy)], 1.3, 0.8, dash=(30, 8, 4, 8))
    cv.dim((fx - 990 * 0.3, fy + 30), (fx + 990 * 0.3, fy + 30), 80, "1980")
    cv.text("ELEVATION", ox, 470, 34, 3.0, 1.0, align='center')
    cv.text("PLAN", ox, 1620, 34, 3.0, 1.0, align='center')
    cv.text("FRONT", fx, 560, 34, 3.0, 1.0, align='center')
    title_block(cv, W - 70 - 1050, H - 70 - 330, 1050, 330,
                [("TITLE", "ESCAPEMENT"), ("DRAWING", "CHASSIS 01 - GENERAL ARRANGEMENT"),
                 ("SCALE  1:10     SHEET 1/7", "DWG C-0101   REV F")], 1.0, 44)
    return finish_blueprint(cv, 31)


def make_sk_gears(W=2480, H=3508):
    cv = Canvas(W, H)
    M = rotm(math.radians(58), 0, math.radians(18))
    stack = [(0, 0, 0, 40, 420, 'spur'), (0, 0, 380, 12, 120, 'spur'), (0, 0, 780, 60, 560, 'spur'), (0, 0, 1120, 16, 170, 'spur'),
             (0, 0, 1480, 15, 300, 'escape')]
    off = (W * 0.5, H * 0.20)
    sc = 1.15
    for k, (x, y, z, teeth, r, st) in enumerate(stack):
        pts = gear_pts(teeth, r, c=(0, 0), rot=k, style=st)
        for passes in range(2):
            jit = 2.2
            top = proj([(px, py, z + 26) for px, py in pts], M, off, sc)
            bot = proj([(px, py, z - 26) for px, py in pts], M, off, sc)
            top = [(a + RNG.normal() * jit, b + RNG.normal() * jit) for a, b in top]
            cv.poly(top + [top[0]], 2.4, 0.75, mode="screen")
            cv.poly(bot[len(bot) // 2:] + bot[:3], 1.6, 0.35, mode='screen')
        # hub + rim ellipses
        for rr, v in ((r * 0.75, 0.45), (r * 0.18, 0.6), (r * 0.06, 0.7)):
            cpts = [(rr * math.cos(t), rr * math.sin(t), z + 26) for t in np.linspace(0, 2 * math.pi, 120)]
            cv.poly(proj(cpts, M, off, sc), 1.8, v, mode='screen')
        # hatching on lower-left of each gear (shadow side)
        for h in range(18):
            t = h / 18.0
            a = math.pi * (0.85 + 0.6 * t)
            p = proj([(r * 0.8 * math.cos(a), r * 0.8 * math.sin(a), z + 26)], M, off, sc)[0]
            cv.seg((p[0] - 18, p[1] + 26), (p[0] + 14, p[1] - 20), 1.2, 0.22, mode='screen')
    # axle construction line
    a = proj([(0, 0, -300)], M, off, sc)[0]; b = proj([(0, 0, 1900)], M, off, sc)[0]
    cv.poly([a, b], 1.4, 0.35, mode='screen', dash=(40, 14, 6, 14))
    # leader notes with handwriting-ish jitter
    notes = [("CENTRE WHEEL Z40", 0), ("PINION Z12", 380), ("THIRD WHEEL Z60", 780), ("PINION Z16", 1120), ("ESCAPE Z15 - CLUB TOOTH", 1480)]
    for s, z in notes:
        p = proj([(0, 300, z)], M, off, sc)[0]
        q = (W * 0.08 if z % 760 else W * 0.62, p[1] - 30)
        cv.seg(p, (q[0] + (0 if q[0] < W / 2 else 0), q[1]), 1.3, 0.4, mode='screen')
        cv.text(s, q[0] + (10 if q[0] > W / 2 else -10 - 22 * 5.6 * len(s) / 6 * 1.0) if q[0] > W / 2 else 60, q[1] - 10, 30, 2.2, 0.6, mode='screen', jitter=0.6)
    cv.text("EXPLODED - GOING TRAIN", 140, 220, 64, 3.4, 0.7, mode='screen', jitter=1.2)
    cv.text("NOT TO SCALE - CHECK DEPTHING", 140, 300, 34, 2.2, 0.5, mode='screen', jitter=0.8)
    # small side study: tooth form
    for i in range(3):
        c = (W * 0.78, H * 0.13 + i * 8)
        cv.poly(gear_pts(9, 150, c=c, rot=0.2 + i * 0.01), 1.6, 0.35, closed=True, mode='screen')
    img = finish_graphite(cv, 41)
    img = coffee_ring(img, (W * 0.74, H * 0.62), W * 0.16, 0.55)
    return img


def make_sk_car(W=3508, H=2480):
    cv = Canvas(W, H)
    for p in range(3):
        draw_car_side(cv, 1500 + p * 3, 1350 + p * 2, 0.56, val=0.42, width=2.3, mode='screen', jitter=2.0, passes=1)
    # construction lines
    cv.poly([(150, 1350), (3300, 1350)], 1.4, 0.3, mode='screen')
    for x in (1500 - 1330 * 0.56, 1500 + 1330 * 0.56):
        cv.poly([(x, 500), (x, 1450)], 1.2, 0.25, mode='screen')
    # big rim study top-right
    draw_wheel(cv, (2900, 520), 330, 0.5, 2.6, mode='screen')
    draw_wheel(cv, (2903, 522), 330, 0.3, 2.0, mode='screen', rot=0.02)
    cv.text("6-SPOKE - CENTRE LOCK", 2650, 940, 34, 2.4, 0.55, mode='screen', jitter=0.8)
    cv.text("PROPORTION STUDY 03", 160, 240, 70, 3.6, 0.65, mode='screen', jitter=1.2)
    cv.text("LOW - WIDE - CAB FWD", 160, 330, 38, 2.4, 0.5, mode='screen', jitter=0.9)
    # quick hatch under car
    for i in range(80):
        x = 300 + i * 34
        cv.seg((x, 1365), (x + 40, 1395), 1.3, 0.25, mode='screen')
    return finish_graphite(cv, 51, tint=(0.90, 0.88, 0.83))


def make_photo_placeholder(W=1920, H=1080):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = yy / H
    sky = np.stack([0.10 + 0.5 * v, 0.35 + 0.45 * v, 0.85 + 0.1 * v], -1)
    img = sky.copy()
    cx = W / 2
    dx = np.abs(xx - cx)
    def put(mask, col):
        img[mask] = col
    put((yy > H * 0.72), (0.92, 0.90, 0.84))
    for k, (y0, y1, hw0, hw1) in enumerate([(0.52, 0.62, 560, 720), (0.40, 0.50, 420, 560), (0.29, 0.38, 300, 420), (0.20, 0.27, 180, 300)]):
        t = (yy / H - y0) / (y1 - y0)
        m = (t >= 0) & (t <= 1) & (dx < hw0 + (hw1 - hw0) * t)
        put(m, (0.05, 0.45, 0.42))
        put(m & (np.abs(t - 0.96) < 0.04), (1.0, 0.72, 0.25))
        wall = (yy / H > y1) & (yy / H < y1 + 0.03) & (dx < hw1 * 0.8)
        put(wall, (0.95, 0.93, 0.88))
    sp = (yy / H < 0.21) & (yy / H > 0.04) & (dx < (yy / H - 0.04) * 260)
    put(sp, (1.0, 0.70, 0.22))
    gate = (yy / H > 0.62) & (dx < 120) & (yy / H < 0.9)
    put(gate, (0.06, 0.03, 0.02))
    put((yy / H > 0.72) & (dx > 125) & (dx < 140) & (yy / H < 0.92), (0.8, 0.2, 0.08))
    return img


def make_pencil_foil(W=2400, H=120):
    """Gold-foil stamp along a pencil face (u = along the pencil, v = across one hex face). Grey = ink mask."""
    cv = Canvas(W, H)
    cv.text("ESCAPEMENT", 300, 86, 56, 5.0, 1.0, slant=0.0)
    cv.text("No.2   HB   DRAUGHTING   *   1794", 1000, 80, 40, 3.6, 1.0, slant=0.0)
    for x in (230, 260):
        cv.seg((x, 22), (x, 98), 4.0, 1.0)
    cv.poly([(1900, 30), (1960, 30), (1990, 60), (1960, 90), (1900, 90), (1930, 60), (1900, 30)], 3.0, 1.0)
    a = cv.ink
    return np.stack([a, a, a], -1)


if __name__ == '__main__':
    import sys
    os.makedirs(TEX, exist_ok=True)
    which = sys.argv[1:] or ['mat', 'bpw', 'bpc', 'skg', 'skc', 'photo']
    if 'foil' in which:
        save_png(os.path.join(TEX, 'act5_pencil_foil.png'), make_pencil_foil())
    if 'photo' in which:
        save_png(os.path.join(TEX, 'act5_photo_placeholder.png'), make_photo_placeholder())
    if 'mat' in which:
        save_png(os.path.join(TEX, 'act5_mat.png'), make_mat())
    if 'bpw' in which:
        save_png(os.path.join(TEX, 'act5_bp_watch.png'), make_bp_watch())
    if 'bpc' in which:
        save_png(os.path.join(TEX, 'act5_bp_car.png'), make_bp_car())
    if 'skg' in which:
        save_png(os.path.join(TEX, 'act5_sk_gears.png'), make_sk_gears())
    if 'skc' in which:
        save_png(os.path.join(TEX, 'act5_sk_car.png'), make_sk_car())
