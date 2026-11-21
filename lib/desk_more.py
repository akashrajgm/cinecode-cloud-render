"""Act V - THE DESK: extra set dressing (continuation session): background depth props + parts tray.

All real scale (metres), desk top z = 0.
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler
from common import *
from desk import box, cyl, revolve, make_pencil, inst


def install_lock_fix():
    """Work around a Windows race in tools/gpu_guard.py (not ours to edit): release() can fail to delete the
    lock file while another process has it open for reading -> the file keeps OUR pid, and the next acquire()
    waits on itself forever (deadlocking every agent's renders). Before each render we drop a lock file that
    names our own pid (it is necessarily stale at that point), and after each render we retry the delete."""
    import os, json, time
    lock = os.path.join(FILM, 'tools', '.blender.lock')
    me = os.getpid()

    def _mine():
        try:
            with open(lock) as fh:
                return json.load(fh).get('pid') == me
        except Exception:
            return False

    def _drop(tries=40):
        for _ in range(tries):
            if not _mine():
                return
            try:
                os.remove(lock)
                return
            except Exception:
                time.sleep(0.05)

    guard = None
    for h in list(bpy.app.handlers.render_pre) + list(bpy.app.handlers.render_init):
        if getattr(h, '__name__', '') == '_on_init' and '_held' in getattr(h, '__globals__', {}):
            guard = h.__globals__
            break

    def _guard_holds():
        return bool(guard and guard['_held'][0])

    @bpy.app.handlers.persistent
    def _pre(*_a):
        if not _guard_holds():
            _drop()

    @bpy.app.handlers.persistent
    def _post(*_a):
        if not _guard_holds():
            _drop()
    if guard is None:
        print('[lockfix] gpu_guard handlers not found - not installed')
        return

    for hl in (bpy.app.handlers.render_init, bpy.app.handlers.render_pre):
        hl.insert(0, _pre)
    for hl in (bpy.app.handlers.render_post, bpy.app.handlers.render_complete, bpy.app.handlers.render_cancel):
        hl.append(_post)


def mat_pencil_paint(foil_path, name='PencilPaint', rough=0.22, length=0.165, rh=0.0037):
    """Lacquered pencil paint in the object colour + gold-foil stamped lettering on one hex face
    (the face that is up when the pencil lies on the desk: local normal at 60 deg in Y/Z)."""
    b = NB(name)
    oi = b.n('ShaderNodeObjectInfo')
    tc = b.n('ShaderNodeTexCoord')
    sep = b.n('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Object'], sep.inputs[0])
    X, Y, Z = sep.outputs['X'], sep.outputs['Y'], sep.outputs['Z']
    d = b.math('ADD', b.math('MULTIPLY', Y, 0.5), b.math('MULTIPLY', Z, 0.8660))
    s = b.math('ADD', b.math('MULTIPLY', Y, -0.8660), b.math('MULTIPLY', Z, 0.5))
    onface = b.math('GREATER_THAN', d, rh * 0.8660 * 0.97)
    span = rh * 20.0
    u = b.math('DIVIDE', b.math('SUBTRACT', X, -length / 2 + 0.018), span)
    v = b.math('DIVIDE', b.math('ADD', s, rh / 2), rh)
    cmb = b.n('ShaderNodeCombineXYZ'); b.link(u, cmb.inputs[0]); b.link(v, cmb.inputs[1])
    tex = b.n('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(foil_path, check_existing=True)
    tex.image.colorspace_settings.name = 'Non-Color'
    tex.extension = 'CLIP'; tex.interpolation = 'Cubic'
    b.link(cmb.outputs[0], tex.inputs['Vector'])
    foil = b.math('MULTIPLY', b.math('GREATER_THAN', tex.outputs['Color'], 0.45), onface)
    n = b.noise(b.coord('Object', 1.0), 900.0, 3, 0.6)
    lg = b.noise(b.coord('Object', 1.0), 60.0, 4, 0.6)
    paint = b.mix(oi.outputs['Color'], b.mix(oi.outputs['Color'], (0, 0, 0), 0.3), lg.outputs['Fac'])
    b.set('Base Color', b.mix(paint, (1.0, 0.74, 0.34), foil))
    b.set('Metallic', foil)
    b.set('Roughness', b.mix(b.maprange(n.outputs['Fac'], 0.3, 0.7, rough * 0.7, rough * 1.5), (0.18, 0.18, 0.18), foil))
    b.set('Coat Weight', 0.7).set('Coat Roughness', 0.06)
    b.set('Normal', b.bump(b.math('ADD', n.outputs['Fac'], b.math('MULTIPLY', foil, -1.5)), 0.05, 0.0001))
    return b.mat


def mat_pegboard(name='Pegboard', size=(0.9, 0.5), pitch=0.025):
    """Masonite pegboard: tan hardboard with a hole grid (object coords of an unscaled-unit cube scaled to size)."""
    b = NB(name)
    tc = b.n('ShaderNodeTexCoord')
    sep = b.n('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Object'], sep.inputs[0])
    hx = b.math('SUBTRACT', b.math('FRACT', b.math('MULTIPLY', sep.outputs['X'], size[0] / pitch)), 0.5)
    hz = b.math('SUBTRACT', b.math('FRACT', b.math('MULTIPLY', sep.outputs['Z'], size[1] / pitch)), 0.5)
    d = b.math('SQRT', b.math('ADD', b.math('MULTIPLY', hx, hx), b.math('MULTIPLY', hz, hz)))
    hole = b.math('LESS_THAN', d, 0.13)
    n = b.noise(b.coord('Object', 1.0), 30.0, 5, 0.6)
    base = b.mix((0.20, 0.145, 0.09), (0.13, 0.09, 0.055), n.outputs['Fac'])
    b.set('Base Color', b.mix(base, (0.004, 0.003, 0.002), hole))
    b.set('Roughness', 0.75)
    b.set('Normal', b.bump(b.math('MULTIPLY', hole, -1.0), 0.6, 0.002))
    return b.mat


def mat_cloth(name, color):
    b = NB(name)
    n = b.noise(b.coord('Object', 1.0), 2500.0, 3, 0.6)
    w = b.noise(b.coord('Object', 1.0), 40.0, 4, 0.6)
    b.set('Base Color', b.mix(color, tuple(c * 0.55 for c in color), b.maprange(w.outputs['Fac'], 0.4, 0.75, 0, 1)))
    b.set('Roughness', 0.8)
    b.set('Normal', b.bump(n.outputs['Fac'], 0.25, 0.0002))
    try:
        b.set('Sheen Weight', 0.4)
    except Exception:
        pass
    return b.mat


def mat_pages(name='Pages'):
    """v13: aged page block - darker, yellowed, page striation + grime toward the edges (was 0.78 white: the
    stack read as blank white slabs, the brightest shapes behind the work)."""
    b = NB(name)
    tc = b.n('ShaderNodeTexCoord')
    sep = b.n('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Object'], sep.inputs[0])
    lines = b.math('FRACT', b.math('MULTIPLY', sep.outputs['Z'], 3000.0))
    n = b.noise(b.coord('Object', 1.0), 60.0, 4, 0.6)
    col = b.mix((0.42, 0.38, 0.29), (0.24, 0.21, 0.15), b.maprange(lines, 0.0, 1.0, 0.0, 0.7))
    b.set('Base Color', b.mix(col, (0.12, 0.10, 0.07), b.maprange(n.outputs['Fac'], 0.45, 0.75, 0.0, 0.6)))
    b.set('Roughness', 0.9)
    b.set('Normal', b.bump(lines, 0.3, 0.0001))
    return b.mat


def make_books(name, coll, loc, yaw, specs, mats_cover, mat_pages_):
    """specs: [(w, d, h, cover_index, yaw_jitter), ...] stacked from the bottom.
    v13: real hardcovers - two boards overhanging a recessed page block, a rounded cloth spine facing the work
    (local -Y), gilt bands + title bar on the spine; cloth darker."""
    root = empty(name + 'Root', loc=loc, coll=coll)
    root.rotation_euler = (0, 0, yaw)
    gold = bpy.data.materials.get('CaseGold')
    z = 0.0
    bt = 0.0022
    for i, (w, d, h, ci, yj) in enumerate(specs):
        bk = empty(f'{name}{i}', coll=coll)
        bk.parent = root
        bk.location = (0.004 * (i % 2), -0.003 * i, z)
        bk.rotation_euler = (0, 0, yj)
        for k, zz in enumerate((bt / 2, h - bt / 2)):
            bd = box(f'{name}{i}Board{k}', (w, d, bt), loc=(0, 0, zz), coll=coll, bev=0.0008, seg=2)
            set_mat(bd, mats_cover[ci]); bd.parent = bk
        # rounded spine along X at y = -d/2 (flattened half-tube)
        bm = bmesh.new()
        seg = 12
        rows = []
        for xs in (-w / 2, w / 2):
            row = []
            for s in range(seg + 1):
                a = -math.pi / 2 + math.pi * s / seg
                row.append(bm.verts.new((xs, -d / 2 + 0.0015 - 0.0045 * math.cos(a), h / 2 + (h / 2) * math.sin(a))))
            rows.append(row)
        for s in range(seg):
            bm.faces.new((rows[0][s], rows[1][s], rows[1][s + 1], rows[0][s + 1]))
        sp = from_bmesh(f'{name}{i}Spine', bm, coll, smooth=True)
        set_mat(sp, mats_cover[ci]); sp.parent = bk
        pg = box(f'{name}{i}Pages', (w - 0.004, d - 0.002, h - 2 * bt), loc=(0, -0.0005, h / 2), coll=coll)
        set_mat(pg, mat_pages_); pg.parent = bk
        # gilt spine bands + a title bar, following the spine curve (slightly proud of the cloth)
        bm = bmesh.new()
        for xx, ww, frac in ((-w / 2 + 0.018, 0.0014, 0.85), (-w / 2 + 0.024, 0.0014, 0.85), (w / 2 - 0.022, 0.0014, 0.85),
                             (-0.02 + 0.01 * (i % 3), 0.07, 0.22)):
            rr_ = []
            for xs in (xx - ww / 2, xx + ww / 2):
                row = []
                for s in range(7):
                    a = (-0.5 + s / 6.0) * math.pi * frac
                    row.append(bm.verts.new((xs, -d / 2 + 0.0015 - 0.0045 * math.cos(a) - 0.00025, h / 2 + (h / 2 + 0.0001) * math.sin(a))))
                rr_.append(row)
            for s in range(6):
                bm.faces.new((rr_[0][s], rr_[1][s], rr_[1][s + 1], rr_[0][s + 1]))
        gb = from_bmesh(f'{name}{i}Gilt', bm, coll, smooth=True)
        set_mat(gb, gold); gb.parent = bk
        z += h
    return root


def make_pencil_cup(name, coll, loc, cup_mat, pencil_cols, pmats, rng):
    root = empty(name + 'Root', loc=loc, coll=coll)
    R, H = 0.036, 0.105
    cup = revolve(name + 'Cup', [(0.0, 0.0), (R - 0.002, 0.0), (R, 0.003), (R, H), (R - 0.003, H), (R - 0.003, 0.006), (0.0, 0.006)], 64, coll)
    set_mat(cup, cup_mat); cup.parent = root
    for i, col in enumerate(pencil_cols):
        p = make_pencil(f'{name}P{i}', col, length=0.175, coll=coll, eraser=(i % 2 == 0), sharpen=True, mats=pmats)
        a = 2 * math.pi * i / len(pencil_cols) + rng.uniform(-0.3, 0.3)
        rr = rng.uniform(0.008, 0.02)
        tilt = math.radians(rng.uniform(6, 16))
        p.parent = root
        # pencil axis = local +X; stand it up (tip up) and lean outward
        p.rotation_euler = Euler((0, -math.pi / 2 + tilt, a), 'XYZ')
        p.location = (rr * math.cos(a), rr * math.sin(a), 0.006 + 0.175 / 2 * math.cos(tilt))
    # steel rule standing in the cup
    rule = box(name + 'Rule', (0.0008, 0.016, 0.20), loc=(-0.012, 0.004, 0.10), rot=(0.12, 0.0, 0.3), coll=coll, bev=0.0002)
    set_mat(rule, bpy.data.materials.get('SteelBrushed')); rule.parent = root
    return root


def fast_cubes(name, coll, n, region, size, zfunc, seed=5, keep=None):
    """n tiny random boxes in one mesh, built with numpy + foreach_set (bmesh per-cube ops were ~100 s).
    keep: optional callable(x, y) -> bool; rejected points are dropped (v13: no grit sparkle on the blueprints)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    x = rng.uniform(region[0], region[1], n); y = rng.uniform(region[2], region[3], n)
    if keep is not None:
        m = np.array([bool(keep(float(a), float(b))) for a, b in zip(x, y)])
        x, y = x[m], y[m]
        n = int(m.sum())
    s = rng.uniform(size[0], size[1], n)
    z = np.array([zfunc(float(a), float(b)) for a, b in zip(x, y)]) + s * 0.3
    unit = np.array([[sx, sy, sz] for sx in (-.5, .5) for sy in (-.5, .5) for sz in (-.5, .5)])     # 8 corners
    faces = np.array([[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]])
    ang = rng.uniform(0, 3, (n, 3))
    cx, sx_, cy, sy_, cz, sz_ = np.cos(ang[:, 0]), np.sin(ang[:, 0]), np.cos(ang[:, 1]), np.sin(ang[:, 1]), np.cos(ang[:, 2]), np.sin(ang[:, 2])
    R = np.empty((n, 3, 3))
    R[:, 0, 0] = cy * cz; R[:, 0, 1] = -cy * sz_; R[:, 0, 2] = sy_
    R[:, 1, 0] = sx_ * sy_ * cz + cx * sz_; R[:, 1, 1] = -sx_ * sy_ * sz_ + cx * cz; R[:, 1, 2] = -sx_ * cy
    R[:, 2, 0] = -cx * sy_ * cz + sx_ * sz_; R[:, 2, 1] = cx * sy_ * sz_ + sx_ * cz; R[:, 2, 2] = cx * cy
    scl = np.stack([s * rng.uniform(0.7, 1.6, n), s * rng.uniform(0.5, 1.0, n), s * rng.uniform(0.4, 0.8, n)], -1)
    V = np.einsum('nij,nkj->nki', R, unit[None, :, :] * scl[:, None, :]) + np.stack([x, y, z], -1)[:, None, :]
    F = (faces[None, :, :] + 8 * np.arange(n)[:, None, None]).reshape(-1, 4)
    me = bpy.data.meshes.new(name)
    me.vertices.add(n * 8)
    me.vertices.foreach_set('co', V.reshape(-1).astype(np.float32))
    me.loops.add(F.size)
    me.loops.foreach_set('vertex_index', F.reshape(-1).astype(np.int32))
    me.polygons.add(len(F))
    me.polygons.foreach_set('loop_start', (np.arange(len(F)) * 4).astype(np.int32))
    try:
        me.polygons.foreach_set('loop_total', np.full(len(F), 4, np.int32))
    except Exception:
        pass
    me.update(calc_edges=True)
    me.validate()
    o = bpy.data.objects.new(name, me)
    link(o, coll)
    return o


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
    return (a + ab * t - p).length


def motes_avoid(name, coll, n, box_, size, mat, polylines, clear=0.03, seed=3):
    """Dust motes in the haze, but none within `clear` of the camera paths (a mote 2 mm from a macro lens
    renders as a giant blurred disc)."""
    rng = random.Random(seed)
    bm = bmesh.new()
    P = []
    for pl in polylines:
        cl = clear
        if isinstance(pl, tuple) and len(pl) == 2 and isinstance(pl[1], float):
            pl, cl = pl
        P.append(([Vector(p) for p in pl], cl))
    k = 0
    while k < n:
        x = rng.uniform(box_[0], box_[1]); y = rng.uniform(box_[2], box_[3]); z = rng.uniform(box_[4], box_[5])
        p = Vector((x, y, z))
        if any(seg_dist(p, a, b) < cl for pl, cl in P for a, b in zip(pl[:-1], pl[1:])):
            continue
        s = rng.uniform(size[0], size[1]) * (1 if rng.random() > 0.08 else 3)
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=s, matrix=Matrix.Translation(p))
        k += 1
    o = from_bmesh(name, bm, coll)
    set_mat(o, mat)
    return o


def make_parts_tray(name, coll, loc, yaw, M, rng, nx=4, ny=3):
    """Watchmaker's parts tray: dark anodised frame with compartments full of tiny screws / wheels / jewels."""
    root = empty(name + 'Root', loc=loc, coll=coll)
    root.rotation_euler = (0, 0, yaw)
    cw, ch, wall, depth = 0.026, 0.026, 0.0015, 0.008
    Wt, Ht = nx * cw + wall, ny * ch + wall
    tray_mat = M.get('tray') or M['dark']
    base = box(name + 'Base', (Wt, Ht, 0.002), loc=(0, 0, 0.001), coll=coll, bev=0.0006)
    set_mat(base, tray_mat); base.parent = root
    for i in range(nx + 1):
        w_ = box(f'{name}WX{i}', (wall, Ht, depth), loc=(-Wt / 2 + wall / 2 + i * cw, 0, depth / 2), coll=coll, bev=0.0004)
        set_mat(w_, tray_mat); w_.parent = root
    for j in range(ny + 1):
        w_ = box(f'{name}WY{j}', (Wt, wall, depth), loc=(0, -Ht / 2 + wall / 2 + j * ch, depth / 2), coll=coll, bev=0.0004)
        set_mat(w_, tray_mat); w_.parent = root
    # contents: per compartment one kind of part, piled
    src_list = M['_tray_src']
    n = 0
    for i in range(nx):
        for j in range(ny):
            kind = (i * ny + j) % len(src_list)
            src, scl = src_list[kind]
            cx = -Wt / 2 + wall + (i + 0.5) * cw - wall / 2
            cy = -Ht / 2 + wall + (j + 0.5) * ch - wall / 2
            cnt = rng.randint(8, 22)
            for k in range(cnt):
                x = cx + rng.uniform(-0.0095, 0.0095)
                y = cy + rng.uniform(-0.0095, 0.0095)
                z = 0.0022 + 0.0006 * (k // 8)
                o = inst(src, f'{name}I{n}', (x, y, z), (rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), rng.uniform(0, 6.28)), scale=scl, coll=coll)
                o.parent = root
                n += 1
    return root, n
