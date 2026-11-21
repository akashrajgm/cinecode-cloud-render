"""ACT III v11: 3H slot canyon builder (uses the canyon toolkit; own path, no main road)."""
import bpy, math, random
import numpy as np
from common import *
import canyon as C
from canyon import smooth, fbm, nz, NB

SLOT_BUMPS = [(30, 22, 0.034), (95, 22, -0.040), (160, 24, 0.036), (230, 26, -0.032), (300, 30, 0.02)]


def slot_half_w(s, side):
    return 3.1 + 0.7 * nz(s * 0.045, 2.0 + side, 1.0) + 0.35 * nz(s * 0.17, 5.0 + side, 2.0)


def slot_notch(s, period=34.0, ph=9.0, width=4.5):
    """1 inside a side-canyon gap on the sun side (the low sun streams through horizontally)."""
    u = ((s - ph) % period) - period / 2
    return 1.0 - smooth(width * 0.5, width * 0.5 + 1.8, abs(u))


def slot_wall_d(s, z, side, notch=0.0):
    """distance of the wall from the slot centre line at (s, z); side -1 left / +1 right."""
    w = slot_half_w(s, side)
    flow = 0.55 * math.sin(z * 0.42 + 2.5 * nz(s * 0.03, side * 3.0, 0.5)) + 0.35 * fbm(s * 0.11, z * 0.13, side * 7.0, 3)
    warp = 1.2 * nz(s * 0.02, side * 1.3, 4.0)
    strat = 0.45 * C.strata_profile(z + 30.0, warp)
    taper = -0.035 * z + 0.0022 * z * z          # pinches a little, then opens toward the rim
    return max(1.45, w + flow + strat + taper) + notch * 9.0


def mat_sand(name='SlotSand'):
    b = NB(name)
    W = C._pos(b)
    wv = b.n('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 1.6; wv.inputs['Distortion'].default_value = 6.0
    wv.inputs['Detail'].default_value = 3.0
    b.link(C._scaled(b, W, (0.6, 1.0, 1.0)), wv.inputs['Vector'])
    n = b.noise(C._scaled(b, W, 1.0), 0.6, 5, 0.6)
    g = b.voronoi(C._scaled(b, W, 1.0), 38.0)
    col = b.ramp(n.outputs['Fac'], [(0.3, (0.15, 0.055, 0.03)), (0.55, (0.27, 0.11, 0.06)), (0.75, (0.34, 0.16, 0.09))])
    col = b.mix(col.outputs[0], (0.06, 0.035, 0.025), b.maprange(g.outputs['Distance'], 0.0, 0.2, 0.35, 0.0))
    b.set('Base Color', col).set('Roughness', 0.92)
    h = b.math('ADD', b.math('MULTIPLY', wv.outputs['Fac'], 0.5), b.math('MULTIPLY', g.outputs['Distance'], 0.3))
    b.set('Normal', b.bump(h, 0.5, 0.02))
    return b.mat


def fog_mat(name='SlotFog', fog=0.015, color=(0.86, 0.66, 0.5), aniso=0.6):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt_ = m.node_tree
    for n in list(nt_.nodes):
        nt_.nodes.remove(n)
    out = nt_.nodes.new('ShaderNodeOutputMaterial')
    vp = nt_.nodes.new('ShaderNodeVolumePrincipled')
    tc = nt_.nodes.new('ShaderNodeTexCoord')
    sp = nt_.nodes.new('ShaderNodeSeparateXYZ'); nt_.links.new(tc.outputs['Object'], sp.inputs[0])
    mr = nt_.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = -1.0; mr.inputs['From Max'].default_value = 1.0
    mr.inputs['To Min'].default_value = fog * 1.2; mr.inputs['To Max'].default_value = fog * 0.8
    nt_.links.new(sp.outputs['Z'], mr.inputs['Value'])
    nt_.links.new(mr.outputs['Result'], vp.inputs['Density'])
    vp.inputs['Color'].default_value = (*color, 1)
    vp.inputs['Anisotropy'].default_value = aniso
    nt_.links.new(vp.outputs['Volume'], out.inputs['Volume'])
    return m


def build_slot(road, s_a, s_b, coll=None, sun_side=-1, fog=0.015, seed=3):
    """Narrow sinuous slot canyon along `road` (its centre line = slot axis): two strata walls
    (flowing, undercut), side-canyon gaps on the sun side, sandy floor, chockstones/rubble,
    and short local fog boxes inside the slot only."""
    import time as _t
    t0 = _t.time()
    coll = coll or collection('Slot')
    rng = random.Random(seed)
    rock = C.mat_canyon_rock('SlotRock', scale=1.0, dist=2500.0)
    sand = mat_sand()
    ds = 0.5
    ss = np.arange(s_a, s_b + ds, ds)
    zz = np.arange(-0.6, 32.0, 0.3)
    walls = []
    for side in (-1, 1):
        Hs = np.array([19.0 + 6.0 * fbm(s * 0.01, 3.0 + side, 0.0, 3) for s in ss])
        if side == sun_side:   # erosional saddles: the low sun cuts down into the slot through them
            Hs = np.array([H * (1.0 - 0.88 * slot_notch(s, period=24.0, ph=11.0, width=7.0)) for s, H in zip(ss, Hs)])
        P = np.zeros((len(ss), len(zz) + 3, 3))
        for i, s in enumerate(ss):
            Cc, t, r, th, k = road.at(s)
            H = Hs[i]
            for j, z in enumerate(zz):
                zc = min(z, H)
                d = slot_wall_d(s, zc, side)
                p = Cc + r * (side * d)
                P[i, j] = (p.x, p.y, zc)
            dtop = slot_wall_d(s, H, side)
            for k_, extra in enumerate((1.0, 4.0, 12.0)):
                p = Cc + r * (side * (dtop + extra))
                P[i, len(zz) + k_] = (p.x, p.y, H + 0.4 * nz(p.x * 0.2, p.y * 0.2))
        if side > 0:
            P = P[::-1, :, :]    # flip winding so normals face the slot axis
        o = C.grid_mesh(f'SlotWall{"L" if side < 0 else "R"}', P, coll, sharp=45)
        set_mat(o, rock)
        walls.append(o)
    # floor
    dd = np.linspace(-7.0, 7.0, 29)
    P = np.zeros((len(dd), len(ss), 3))
    for j, s in enumerate(ss):
        Cc, t, r, th, k = road.at(s)
        for i, d in enumerate(dd):
            p = Cc + r * d
            P[i, j] = (p.x, p.y, 0.04 * nz(p.x * 0.5, p.y * 0.5, 2.0) + 0.08 * (abs(d) / 7.0) ** 2)
    fl = C.grid_mesh('SlotFloor', P, coll, sharp=60)
    set_mat(fl, sand)
    # rubble + chockstones along the wall feet, pebbles on the floor
    rocks = [C.rock_mesh(f'SlotRockSrc{i}', 1.0, seed=40 + i, flat=rng.uniform(0.5, 0.8)) for i in range(5)]
    bm_ = C.mat_boulder('SlotBoulder')
    for o in rocks:
        set_mat(o, bm_)
    src = C.src_collection('SlotRockSrc', rocks)
    pts, rots, scs, picks = [], [], [], []
    for _ in range(int((s_b - s_a) * 8)):
        s = rng.uniform(s_a, s_b); side = rng.choice((-1, 1))
        dw = slot_wall_d(s, 0.3, side)
        if rng.random() < 0.75:
            d = side * (dw - rng.uniform(0.0, 0.7)); sc_ = rng.uniform(0.05, 0.4)
        else:
            d = rng.uniform(-2.6, 2.6); sc_ = rng.uniform(0.015, 0.06)
        p = road.point(s, d)
        pts.append((p.x, p.y, -0.05 * sc_)); rots.append((rng.uniform(-.3, .3), rng.uniform(-.3, .3), rng.uniform(0, 6.3)))
        scs.append((sc_, sc_ * rng.uniform(0.8, 1.3), sc_ * 0.8)); picks.append(rng.randrange(len(rocks)))
    # chockstones wedged high between the walls
    for s in np.arange(s_a + 15, s_b, 41.0):
        z = rng.uniform(8, 13)
        dl, dr = slot_wall_d(s, z, -1), slot_wall_d(s, z, 1)
        p = road.point(s, (dr - dl) / 2)
        sc_ = (dl + dr) / 2 * 0.62
        pts.append((p.x, p.y, z)); rots.append((rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0, 6.3)))
        scs.append((sc_, sc_ * 0.8, sc_ * 0.7)); picks.append(rng.randrange(len(rocks)))
    C.scatter('SlotRubble', pts, rots, scs, picks, src, coll)
    # fog: short local boxes riding the slot (NOT one huge box: that checkerboarded)
    if fog > 0:
        m = fog_mat('SlotFog', fog)
        for s in np.arange(s_a, s_b, 20.0):
            Cc, t, r, th, k = road.at(s + 10)
            o = prim('cube', f'SlotFog{int(s)}', loc=(Cc.x, Cc.y, 9.0), scale=(14.0, 21.0, 18.0), coll=coll, smooth=False)
            o.rotation_euler = (0, 0, -th)
            set_mat(o, m)
            o.visible_shadow = False
    print(f'[canyon] slot built {_t.time() - t0:.1f}s', flush=True)
    return {'coll': coll, 'walls': walls, 'floor': fl}
