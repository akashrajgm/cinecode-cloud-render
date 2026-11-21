"""Act II helpers: dark concrete studio, voxel disintegration (geometry nodes), dusk canyon,
spark bursts, flashes, camera impulses."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler
import common as C

# studio extents
SX, SY0, SY1, SH = 13.0, -22.0, 26.0, 6.2     # half-width, front wall y, back wall y, ceiling height
DOOR = (-6.5, 2.0, 3.1)                          # doorway centre x, width, height (in back wall)
STRIP_X = (-3.0, 3.0)                            # r3: 2 sparse rows (was 6)

# ----------------------------------------------------------------------------- materials

def _rest_coord(b):
    at = b.n('ShaderNodeAttribute'); at.attribute_type = 'INSTANCER'; at.attribute_name = 'rest'
    cp = b.n('ShaderNodeAttribute'); cp.attribute_type = 'INSTANCER'; cp.attribute_name = 'cpos'
    geo = b.n('ShaderNodeNewGeometry')
    d = b.n('ShaderNodeVectorMath'); d.operation = 'SUBTRACT'
    b.link(geo.outputs['Position'], d.inputs[0]); b.link(cp.outputs['Vector'], d.inputs[1])
    a = b.n('ShaderNodeVectorMath'); a.operation = 'ADD'
    b.link(at.outputs['Vector'], a.inputs[0]); b.link(d.outputs['Vector'], a.inputs[1])
    return a.outputs['Vector']


def mat_floor(name='floor_wet', rest=False):
    """Dark wet concrete: big glossy puddles, damp roughness elsewhere, stains, cracks, expansion joints."""
    b = C.NB(name)
    if rest:
        v = _rest_coord(b)
    else:
        v = b.coord('Object', 1.0)
    n1 = b.noise(v, 0.35, 8, 0.6)
    n2 = b.noise(v, 6.0, 8, 0.6)
    pud = b.noise(v, 0.22, 5, 0.55, dist=0.4)
    sep = b.n('ShaderNodeSeparateXYZ'); b.link(v, sep.inputs[0])
    # standing water sheet around the car (ragged edge) so car + strips mirror in every studio shot
    rxy0 = b.math('SQRT', b.math('ADD', b.math('MULTIPLY', sep.outputs['X'], sep.outputs['X']),
                                  b.math('MULTIPLY', b.math('MULTIPLY', sep.outputs['Y'], 0.62), b.math('MULTIPLY', sep.outputs['Y'], 0.62))))
    zone_r = b.math('ADD', rxy0, b.math('MULTIPLY', b.math('SUBTRACT', pud.outputs['Fac'], 0.5), 9.0))
    zone = b.maprange(zone_r, 5.2, 4.4, 0.0, 1.0)
    # r3: patchy - standing water only in the low spots + the sheet round the car, ~50% of the rest damp
    mask = b.math('MAXIMUM', b.maprange(pud.outputs['Fac'], 0.55, 0.575, 0.0, 1.0), zone)
    damp = b.math('MAXIMUM', b.maprange(pud.outputs['Fac'], 0.46, 0.53, 0.0, 1.0), b.maprange(zone_r, 7.0, 5.0, 0.0, 1.0))
    # expansion joints every 4 m
    jx = b.math('ABSOLUTE', b.math('SUBTRACT', b.math('FRACT', b.math('MULTIPLY', sep.outputs['X'], 0.25)), 0.5))
    jy = b.math('ABSOLUTE', b.math('SUBTRACT', b.math('FRACT', b.math('MULTIPLY', sep.outputs['Y'], 0.25)), 0.5))
    joint = b.math('MAXIMUM', b.maprange(jx, 0.496, 0.4995, 0, 1), b.maprange(jy, 0.496, 0.4995, 0, 1))
    cr = b.voronoi(v, 1.8, feature='DISTANCE_TO_EDGE')
    crack = b.math('MULTIPLY', b.maprange(cr.outputs['Distance'], 0.012, 0.0, 0, 1), b.maprange(n2.outputs['Fac'], 0.55, 0.62, 0, 1))
    col = b.ramp(n1.outputs['Fac'], [(0.25, (0.02, 0.022, 0.025)), (0.75, (0.07, 0.074, 0.08))])
    c2 = b.mix(col.outputs[0], (0.012, 0.013, 0.015), b.math('MAXIMUM', mask, b.math('MULTIPLY', damp, 0.5)))
    c2 = b.mix(c2, (0.0, 0.0, 0.0), b.math('MAXIMUM', joint, crack))
    # worn painted markings: turntable ring around the car + a dashed lane line
    rxy = b.math('SQRT', b.math('ADD', b.math('MULTIPLY', sep.outputs['X'], sep.outputs['X']),
                                 b.math('MULTIPLY', sep.outputs['Y'], sep.outputs['Y'])))
    ring = b.maprange(b.math('ABSOLUTE', b.math('SUBTRACT', rxy, 3.6)), 0.05, 0.04, 0, 1)
    ring2 = b.maprange(b.math('ABSOLUTE', b.math('SUBTRACT', rxy, 3.82)), 0.015, 0.008, 0, 1)
    lane = b.math('MULTIPLY', b.maprange(b.math('ABSOLUTE', b.math('SUBTRACT', sep.outputs['X'], 7.0)), 0.07, 0.06, 0, 1),
                  b.math('GREATER_THAN', b.math('FRACT', b.math('MULTIPLY', sep.outputs['Y'], 0.4)), 0.45))
    wear = b.math('MULTIPLY', b.maprange(n2.outputs['Fac'], 0.42, 0.56, 0, 1),
                  b.maprange(b.noise(v, 2.2, 4, 0.6).outputs['Fac'], 0.40, 0.6, 0.0, 1.0))     # r3: heavier wear
    paint = b.math('MULTIPLY', b.math('MAXIMUM', b.math('MAXIMUM', ring, ring2), lane), wear)
    c2 = b.mix(c2, (0.11, 0.115, 0.11), paint)          # r3: 0.42 -> 0.11 (paint was the brightest thing on the floor)
    b.set('Base Color', c2)
    rough = b.maprange(n2.outputs['Fac'], 0.3, 0.7, 0.36, 0.66)
    rough = b.mix(rough, (0.16, 0.16, 0.16), damp)
    rough = b.mix(rough, (0.04, 0.04, 0.04), mask)     # r3: not glass (0.0 mirrored hidden lights as hard cards)
    b.set('Roughness', rough)
    bump_h = b.math('MULTIPLY', b.math('ADD', n2.outputs['Fac'], b.math('MULTIPLY', b.math('MAXIMUM', joint, crack), -1.0)),
                    b.math('SUBTRACT', 1.0, mask))
    # fine ripple only on the standing water so remaining reflections break up like water
    rip = b.noise(v, 25.0, 3, 0.5)
    rip_h = b.math('MULTIPLY', rip.outputs['Fac'], mask)
    b.set('Normal', b.bump(rip_h, 0.04, 0.01, normal=b.bump(bump_h, 0.25, 0.01)))
    return b.mat


def mat_wall(name='wall_conc', rest=False, base=(0.055, 0.06, 0.065)):
    b = C.NB(name)
    if rest:
        v = _rest_coord(b)
    else:
        v = b.coord('Object', 1.0)
    n1 = b.noise(v, 0.6, 10, 0.62)
    n2 = b.noise(v, 9.0, 8, 0.65)
    stain = b.noise(v, 0.25, 6, 0.6, dist=1.0)
    # form-work panel lines (1.2 x 2.4 m) + tie holes
    sep = b.n('ShaderNodeSeparateXYZ'); b.link(v, sep.inputs[0])
    hz = b.math('ABSOLUTE', b.math('SUBTRACT', b.math('FRACT', b.math('MULTIPLY', sep.outputs['Z'], 1 / 1.2)), 0.5))
    lines = b.maprange(hz, 0.493, 0.499, 0, 1)
    col = b.ramp(n1.outputs['Fac'], [(0.25, tuple(c * 0.45 for c in base)), (0.75, base)])
    col = b.mix(col.outputs[0], tuple(c * 0.3 for c in base), b.maprange(stain.outputs['Fac'], 0.5, 0.75, 0, 0.8))
    col = b.mix(col, (0.0, 0.0, 0.0), b.math('MULTIPLY', lines, 0.7))
    b.set('Base Color', col)
    b.set('Roughness', b.maprange(n2.outputs['Fac'], 0.3, 0.7, 0.6, 0.95))
    b.set('Normal', b.bump(b.math('SUBTRACT', n2.outputs['Fac'], lines), 0.4, 0.02))
    return b.mat


def mat_voxel(name, base_fn, glint_color=(0.75, 0.95, 1.0)):
    """Concrete material for voxel instances using their rest position + emissive glints."""
    m = base_fn(name, rest=True)
    nt = m.node_tree
    bsdf = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    # r3: once a tile breaks loose it is a rough fractured chunk (wet-mirror shards glinted like confetti)
    ra = nt.nodes.new('ShaderNodeAttribute'); ra.attribute_type = 'INSTANCER'; ra.attribute_name = 'relf'
    rl = bsdf.inputs['Roughness']
    if rl.is_linked:
        src = rl.links[0].from_socket
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'FLOAT'
        nt.links.new(ra.outputs['Fac'], mx.inputs['Factor'])
        nt.links.new(src, mx.inputs[2]); mx.inputs[3].default_value = 0.85
        nt.links.new(mx.outputs[0], rl)
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_type = 'INSTANCER'; at.attribute_name = 'glint'
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 0.0   # client: no emissive bits
    nt.links.new(at.outputs['Fac'], mul.inputs[0])
    bsdf.inputs['Emission Color'].default_value = (*glint_color, 1)
    nt.links.new(mul.outputs[0], bsdf.inputs['Emission Strength'])
    return m

# ----------------------------------------------------------------------------- studio

_TPL = {}


def _ico_tpl(sub):
    """(verts, faces) of a unit-diameter icosphere (cached). Building thousands of small parts with
    bmesh.ops on one growing bmesh is O(n^2) (every op touches every element) - 150 s for 1400 rocks."""
    if sub not in _TPL:
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=0.5)
        bm.verts.index_update()
        _TPL[sub] = ([v.co.copy() for v in bm.verts], [[v.index for v in f.verts] for f in bm.faces])
        bm.free()
    return _TPL[sub]


def inst_mesh(name, coll, items, smooth=False):
    """items: [(template(verts, faces), Matrix)] -> one mesh object via from_pydata (linear time)."""
    verts, faces = [], []
    for (tv, tf), M in items:
        b0 = len(verts)
        verts.extend(M @ v for v in tv)
        faces.extend([b0 + i for i in f] for f in tf)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    C.link(o, coll)
    if smooth:
        C.shade(o, 60)
    return o


def mat_strip(name, color, strength, period=4.0, seg_len=2.4):
    """Fluorescent/LED strip diffuser: brightest along the centre line of the opal cover, falls off to the
    edges and to the tube ends (period = segment spacing along Y), faint LED pitch, per-segment tint drift."""
    b = C.NB(name)
    tc = b.n('ShaderNodeTexCoord')
    sep = b.n('ShaderNodeSeparateXYZ'); b.link(tc.outputs['Object'], sep.inputs[0])
    nrm = b.n('ShaderNodeNewGeometry')
    # position within a segment along Y (segments start at SY0+2 every `period`)
    yy = b.math('FRACT', b.math('DIVIDE', b.math('SUBTRACT', sep.outputs['Y'], SY0 + 2.0), period))
    u = b.math('DIVIDE', b.math('MULTIPLY', yy, period), seg_len)                  # 0..1 along the tube
    ends = b.math('MULTIPLY', b.maprange(u, 0.0, 0.08, 0.35, 1.0), b.maprange(u, 1.0, 0.92, 0.35, 1.0))
    led = b.maprange(b.math('SINE', b.math('MULTIPLY', sep.outputs['Y'], 160.0)), -1, 1, 0.82, 1.0)
    face = b.n('ShaderNodeSeparateXYZ'); b.link(nrm.outputs['Normal'], face.inputs[0])
    down = b.maprange(b.math('ABSOLUTE', face.outputs['Z']), 0.3, 1.0, 0.45, 1.0)    # sides of the cover dimmer
    segid = b.math('FLOOR', b.math('DIVIDE', b.math('SUBTRACT', sep.outputs['Y'], SY0 + 2.0), period))
    wn = b.n('ShaderNodeTexWhiteNoise'); wn.noise_dimensions = '1D'
    b.link(b.math('ADD', segid, b.math('MULTIPLY', sep.outputs['X'], 0.37)), wn.inputs['W'])
    tint = b.mix(color, (color[0] * 1.08, color[1] * 0.98, color[2] * 0.86), wn.outputs['Value'])
    k = b.math('MULTIPLY', b.math('MULTIPLY', ends, led), down)
    b.set('Base Color', (0.6, 0.62, 0.64)).set('Roughness', 0.35)
    b.set('Emission Color', tint)
    em = b.math('MULTIPLY', k, strength)
    sv = b.n('ShaderNodeValue'); sv.name = sv.label = 'Master'; sv.outputs[0].default_value = 1.0
    b.set('Emission Strength', b.math('MULTIPLY', em, sv.outputs[0]))
    return b.mat


def _grid(name, sx, sy, nx, ny, coll):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=0.5)
    for v in bm.verts:
        v.co.x *= sx; v.co.y *= sy
    return C.from_bmesh(name, bm, coll, smooth=False)


def _apply_scale(o):
    o.data.transform(Matrix.Diagonal((*o.scale, 1.0)))
    o.scale = (1, 1, 1)
    return o


def build_studio(coll, voxel=False, cube=0.2):
    """Returns dict with objects and lists of strip lights (for flicker/off)."""
    S = {'strips': [], 'strip_lights': [], 'panels': [], 'voxels': []}
    floor_m = mat_floor()
    wall_m = mat_wall()
    ceil_m = mat_wall('ceil_conc', base=(0.03, 0.033, 0.036))
    S['mats'] = {'floor': floor_m, 'wall': wall_m, 'ceil': ceil_m}
    W, L = 2 * SX, SY1 - SY0
    yc = (SY0 + SY1) / 2
    if not voxel:
        fl = C.prim('plane', 'floor', loc=(0, yc, 0), scale=(W + 40, L + 40, 1), coll=coll, smooth=False)
        C.set_mat(fl, floor_m); _apply_scale(fl)
        S['floor'] = fl
        ce = C.prim('plane', 'ceiling', loc=(0, yc, SH), rot=(math.pi, 0, 0), scale=(W, L, 1), coll=coll, smooth=False)
        C.set_mat(ce, ceil_m); _apply_scale(ce)
        for sx in (-1, 1):
            w = C.prim('plane', f'wall_{sx}', loc=(sx * SX, yc, SH / 2), rot=(0, math.pi / 2, 0), scale=(SH, L, 1), coll=coll, smooth=False)
            C.set_mat(w, wall_m); _apply_scale(w)
        # front wall (behind the car) with the glowing doorway: 3 slabs
        dx, dw, dh = DOOR
        left_w = (dx - dw / 2) - (-SX)
        right_w = SX - (dx + dw / 2)
        for nm, cx, ww, cz, hh in (('fw_l', -SX + left_w / 2, left_w, SH / 2, SH), ('fw_r', SX - right_w / 2, right_w, SH / 2, SH),
                                   ('fw_t', dx, dw, dh + (SH - dh) / 2, SH - dh)):
            o = C.prim('cube', nm, loc=(cx, SY0 - 0.15, cz), scale=(ww, 0.3, hh), coll=coll, smooth=False)
            C.set_mat(o, wall_m); _apply_scale(o)
        bw = C.prim('plane', 'back_wall', loc=(0, SY1, SH / 2), rot=(math.pi / 2, 0, 0), scale=(W, SH, 1), coll=coll, smooth=False)
        C.set_mat(bw, wall_m); _apply_scale(bw)
    else:
        import time as _tm
        _t0 = _tm.time()
        S['voxels'] = build_voxel_room2(coll, cube, avoid=VOX_AVOID)
        print('[studio] voxel room %.1fs' % (_tm.time() - _t0))
    # ceiling beams
    S['beam_list'] = []
    Lb = (SY1V if voxel else SY1) - SY0
    for k in range(int(Lb / 4) + 1):
        y = SY0 + k * 4.0
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((W, 0.35, 0.6, 1)))
        bo_ = C.from_bmesh(f'beam_{k}', bm, coll, smooth=False)
        bo_.location = (0, y, SH - 0.3)
        C.set_mat(bo_, ceil_m)
        C.bevel(bo_, 0.02, 2, 40)
        S['beam_list'].append(bo_)
    S['beams'] = S['beam_list'][0]
    # fluorescent strips: emissive tubes in housings + long area lights. Client rule: practicals are
    # textured, coloured, moderate (strength ~5): opal diffuser gradient across the tube, dim ends,
    # faint LED pitch, slight per-segment colour drift; the AREA lights do the actual lighting.
    # r3: 2 sparse rows (was 6 rows x 11 identical segments = sci-fi tunnel); ~30% of the segments missing,
    # one dead tube, one flickering tube; every segment is its own area light (no continuous light bar
    # reflecting where there is no tube)
    tube_m = mat_strip('strip_emit', (0.55, 0.82, 1.0), 5.0)
    flick_m = mat_strip('strip_flicker', (0.55, 0.82, 1.0), 5.0)
    dead_m = C.mat_principled('strip_dead', (0.30, 0.32, 0.33), 0.3)
    house_m = C.mat_principled('strip_house', (0.05, 0.05, 0.055), 0.35, 0.8)
    S['mats']['tube'] = tube_m
    S['mats']['tube_flicker'] = flick_m
    rng_s = random.Random(17)
    S['segs'] = []
    y_end = (SY1V if voxel else SY1) - 2.5
    for i, x in enumerate(STRIP_X):
        y = SY0 + 2.0
        k = 0
        while y < y_end:
            ln = 2.4
            near = abs(y + ln / 2) < 7.0
            state = 'on'
            if not near and rng_s.random() < 0.32:
                state = 'missing'
            if i == 0 and k == 3:
                state = 'dead'
            if i == 1 and k == 2:
                state = 'flicker'
            k += 1
            if state == 'missing':
                y += 4.0
                continue
            cen = Vector((x, y + ln / 2, SH - 0.74))
            bm_s = bmesh.new()
            mt = Matrix.Translation((0, 0, -0.01)) @ Matrix.Diagonal((0.05, ln, 0.03, 1))
            r_t = bmesh.ops.create_cube(bm_s, size=1.0, matrix=mt)
            mh = Matrix.Translation((0, 0, 0.02)) @ Matrix.Diagonal((0.12, ln + 0.1, 0.05, 1))
            r_h = bmesh.ops.create_cube(bm_s, size=1.0, matrix=mh)
            hfaces = set()
            for v_ in r_h['verts']:
                hfaces.update(v_.link_faces)
            for yy in (-ln / 2 + 0.3, ln / 2 - 0.3):   # hanging wires
                mw = Matrix.Translation((0, yy, 0.39)) @ Matrix.Diagonal((0.006, 0.006, 0.7, 1))
                r_w = bmesh.ops.create_cube(bm_s, size=1.0, matrix=mw)
                for v_ in r_w['verts']:
                    hfaces.update(v_.link_faces)
            for f_ in bm_s.faces:
                f_.material_index = 1 if f_ in hfaces else 0
            so_ = C.from_bmesh(f'strip_{i}_{k}', bm_s, coll, smooth=False)
            so_.data.materials.append({'on': tube_m, 'dead': dead_m, 'flicker': flick_m}[state])
            so_.data.materials.append(house_m)
            so_.location = cen
            S['strips'].append(so_)
            if state in ('on', 'flicker'):
                L_ = C.light('AREA', f'stripL_{i}_{k}', (x, y + ln / 2, SH - 0.8), energy=44, color=(0.74, 0.90, 1.0), size=0.10,
                             size_y=ln - 0.1)
                L_.data.shape = 'RECTANGLE'; L_.data.size = 0.10; L_.data.size_y = ln - 0.1
                L_.data.spread = math.radians(150)
                if state == 'flicker':
                    S['flicker_light'] = L_
                else:
                    S['strip_lights'].append(L_)
                S['segs'].append((so_, L_))
            else:
                S['segs'].append((so_, None))
            y += 4.0
    # the flickering tube: stutters + dies for a frame now and then (keys over 0..200)
    fl = S.get('flicker_light')
    fm = flick_m.node_tree.nodes['Master'].outputs[0]
    rng_f = random.Random(4)
    e_on = fl.data.energy if fl else 44
    f = 1
    while f < 200:
        on = rng_f.random() > 0.22
        v = 1.0 if on else rng_f.choice((0.0, 0.08, 0.3))
        fm.default_value = v; fm.keyframe_insert('default_value', frame=f)
        if fl:
            fl.data.energy = e_on * v; fl.data.keyframe_insert('energy', frame=f)
        f += rng_f.choice((1, 1, 2, 3, 5, 8))
    for idb in ([flick_m.node_tree] + ([fl.data] if fl else [])):
        for fc in C.fcurves(idb):
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT'
    # overhead car softbox (long paint reflections) + cool rim lights
    sb = C.light('AREA', 'softbox', (0, 0, SH - 1.0), energy=600, color=(0.80, 0.91, 1.0), size=1.2, size_y=5.5)
    sb.data.shape = 'RECTANGLE'; sb.data.size = 1.2; sb.data.size_y = 5.5
    sbm = C.prim('plane', 'softbox_face', loc=(0, 0, SH - 0.98), rot=(math.pi, 0, 0), scale=(1.2, 5.5, 1), coll=coll, smooth=False)
    C.set_mat(sbm, C.mat_emission('softbox_emit', (0.78, 0.9, 1.0), 2.0))
    S.setdefault('fixtures', []).append(sbm)
    S['softbox'] = sb
    S['rims'] = []
    for i, (x, y) in enumerate(((-6.5, -6.0), (6.5, 7.0))):
        rl = C.light('AREA', f'rim{i}', (x, y, 2.2), energy=320, color=(0.6, 0.85, 1.0), size=0.5, size_y=3.0, target=(0, 0, 0.5))
        rl.data.shape = 'RECTANGLE'; rl.data.size = 0.5; rl.data.size_y = 3.0
        rl.data.specular_factor = 0.0      # r3: hidden lights mirrored as hard white cards in the wet floor
        rl.data.volume_factor = 0.0        # r3: drew a vertical blue pillar in the studio haze
        S['rims'].append(rl)
    # vertical light panels on the side walls
    # vertical wall panels = warm sodium-amber practicals: warm/cool rhythm against the cool ceiling strips
    # r3: 4 per side at irregular spacing (14 identical panels read as a sci-fi tunnel)
    pan_m = C.mat_emission('panel_emit', (1.0, 0.50, 0.22), 3.0)
    S['mats']['panel'] = pan_m
    for sx in (-1, 1):
        for y in ((-15.5, -4.0, 5.5, 17.0) if sx < 0 else (-11.0, -1.5, 9.0, 21.0)):
            if voxel and y > SY1V - 1.0:
                continue
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((0.04, 0.32, 3.6, 1)))
            pan = C.from_bmesh(f'panel_{sx}_{y}', bm, coll, smooth=False)
            pan.location = (sx * (SX - 0.06), y, 2.6)
            C.set_mat(pan, pan_m)
            S['panels'].append(pan)
    # distant glowing doorway: bright plane behind the hole + soft light spilling in + haze
    dx, dw, dh = DOOR
    # the doorway is WARM (low dusk sun outside): warm key vs the cool strips, and it foreshadows 2G
    # glow card behind the opening: hot low "sun" centre falling off to the edges (reads as depth/light
    # through an opening, not a flat card); 'Master' value node = animatable strength
    b_ = C.NB('door_emit')
    tcg = b_.n('ShaderNodeTexCoord')
    sg = b_.n('ShaderNodeSeparateXYZ'); b_.link(tcg.outputs['Generated'], sg.inputs[0])
    dxx = b_.math('MULTIPLY', b_.math('POWER', b_.math('SUBTRACT', sg.outputs['X'], 0.5), 2.0), 7.0)
    dyy = b_.math('MULTIPLY', b_.math('POWER', b_.math('SUBTRACT', sg.outputs['Y'], 0.32), 2.0), 3.5)
    fall = b_.math('EXPONENT', b_.math('MULTIPLY', b_.math('ADD', dxx, dyy), -1.0))
    b_.set('Base Color', (0, 0, 0)).set('Roughness', 0.5)
    b_.set('Emission Color', b_.mix((0.75, 0.22, 0.06), (1.0, 0.62, 0.30), fall))
    mst = b_.n('ShaderNodeValue'); mst.name = mst.label = 'Master'; mst.outputs[0].default_value = 1.0
    b_.set('Emission Strength', b_.math('MULTIPLY', b_.math('ADD', 0.8, b_.math('MULTIPLY', fall, 6.0)), mst.outputs[0]))
    door_m = b_.mat
    S['mats']['door'] = door_m
    dp = C.prim('plane', 'door_glow', loc=(dx, SY0 - 2.5, dh / 2), rot=(-math.pi / 2, 0, 0), scale=(dw + 2, dh + 2, 1), coll=coll, smooth=False)
    C.set_mat(dp, door_m)
    S['door_glow'] = dp
    dl = C.light('AREA', 'door_light', (dx, SY0 - 0.6, dh / 2), rot=(math.pi / 2, 0, 0), energy=1600, color=(1.0, 0.62, 0.36),
                 size=dw, size_y=dh)
    dl.rotation_euler = (math.pi / 2, 0, 0)    # face +Y (into the room)
    dl.data.spread = math.radians(70)
    S['door_light'] = dl
    # the doorway's warm spill carried to the car (motivated warm rim on the cool-lit graphite paint)
    # (v7-v9: at 1.5 m high this 2x3 m emitter was SEEN by the camera as a flat peach card -> high + hidden)
    sp_ = C.light('AREA', 'door_spill', (-3.6, -7.5, 4.6), energy=520, color=(1.0, 0.55, 0.28), size=2.0, size_y=3.0,
                  target=(0, 0, 0.5))
    sp_.data.shape = 'RECTANGLE'; sp_.data.size = 2.0; sp_.data.size_y = 3.0
    sp_.data.specular_factor = 0.0
    S['door_spill'] = sp_
    # r3: the low dusk sun THROUGH the doorway: a warm spot raking in at ~9 deg -> a light pool on the wet
    # floor + a visible shaft in the studio haze (the door becomes the brightest, most inviting element)
    beam = C.light('SPOT', 'door_beam', (dx + 0.6, SY0 - 7.0, dh * 0.62 + 1.0), energy=9000, color=(1.0, 0.58, 0.30),
                   spot=13.0, blend=0.35, shadow_soft=0.25, target=(dx + 2.2, SY0 + 9.0, 0.0))
    beam.data.volume_factor = 2.2
    beam.data.specular_factor = 0.4
    S['door_beam'] = beam
    # grazing warm wall-washes so the concrete stains/form lines read (dark walls were featureless)
    S['washes'] = []
    for i, (x, y) in enumerate(((-SX + 0.45, -8.0), (SX - 0.45, 4.0), (-SX + 0.45, 12.0))):
        ww = C.light('SPOT', f'wallwash{i}', (x, y, SH - 0.35), energy=380, color=(1.0, 0.66, 0.40), spot=60.0, blend=0.9,
                     shadow_soft=0.1, target=(x + (0.25 if x < 0 else -0.25), y + 0.4, 0.0))
        ww.data.specular_factor = 0.0
        ww.data.volume_factor = 0.3
        S['washes'].append(ww)
    for L_ in [o_ for o_ in bpy.data.objects if o_.type == 'LIGHT']:
        try:
            L_.visible_camera = False
        except Exception:
            pass
    # localised warm haze pool spilling in through the doorway (client: thin local volumes, no global soup)
    # (v8-v10: a 5x9x4 m warm haze box here rendered as a hard-edged flat peach card -> removed)
    S['door_haze'] = None
    # haze volume
    hz = C.mat_volume('studio_haze', density=0.0035, color=(0.55, 0.80, 0.95), anisotropy=0.65, noise_scale=0.12,
                      noise_contrast=(0.3, 0.8))
    vb = C.volume_box('haze', (0, yc, SH / 2), (W, L, SH), hz, coll)
    S['haze'] = vb
    # floor clutter: debris chips + cables + puddle rims (detail density)
    S['debris'] = scatter_debris(coll, 1400) if not voxel else None
    S['motes'] = dust_motes(coll, 130)
    if not voxel:
        S['props'] = studio_props(coll)
    return S


def _tube(bm, pts, r, segs=10):
    secs = []
    for i, p in enumerate(pts):
        p = Vector(p)
        d = (Vector(pts[min(i + 1, len(pts) - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        u = d.cross(up).normalized(); v = d.cross(u).normalized()
        secs.append([p + (u * math.cos(2 * math.pi * k / segs) + v * math.sin(2 * math.pi * k / segs)) * r for k in range(segs)])
    vs = [[bm.verts.new(q) for q in s] for s in secs]
    for i in range(len(vs) - 1):
        for j in range(segs):
            j2 = (j + 1) % segs
            bm.faces.new((vs[i][j], vs[i][j2], vs[i + 1][j2], vs[i + 1][j]))


def studio_props(coll, seed=5):
    """Foreground/midground depth: power cables snaking over the wet floor, a tyre stack,
    light stands with dark flags, a rolling tool chest."""
    rng = random.Random(seed)
    out = []
    rub = C.mat_rubber('prop_rubber', (0.01, 0.01, 0.011), 0.5)
    steel = C.mat_metal('prop_steel', base=(0.25, 0.25, 0.26), rough=(0.25, 0.5), scale=5)
    # cables
    bm = bmesh.new()
    for k in range(0):     # cables read as white polygon outlines on the wet floor -> removed
        p = Vector((rng.uniform(-6, 6), rng.uniform(-8, 10), 0.012))
        ang = rng.uniform(0, 6.28)
        pts = []
        for i in range(70):
            ang += rng.gauss(0, 0.18)
            p = p + Vector((math.cos(ang), math.sin(ang), 0)) * 0.18
            if abs(p.x) < 2.6 and abs(p.y) < 3.4:
                ang += 0.6
            pts.append(Vector((p.x, p.y, 0.0075)))
        _tube(bm, pts, 0.0075, 8)
    cab = C.from_bmesh('cables', bm, coll, smooth=True, sharp_angle=80)
    C.set_mat(cab, rub)
    out.append(cab)
    # tyre stacks
    for (x, y, n) in ((-6.8, 6.2, 4), (7.2, -7.4, 3)):
        for i in range(n):
            t = C.prim('torus', f'tyre_{x}_{i}', loc=(x + rng.uniform(-0.04, 0.04), y + rng.uniform(-0.04, 0.04), 0.14 + i * 0.27),
                       coll=coll, R=0.30, r=0.13, su=48, sv=16)
            t.scale = (1, 1, 1.05)
            C.set_mat(t, rub)
            out.append(t)
    # light stands with black flags (silhouettes against the panels)
    for (x, y, a) in ():
        bm = bmesh.new()
        _tube(bm, [(x, y, 0.0), (x, y, 2.6)], 0.018, 8)
        for k in range(3):
            aa = a + k * 2.094
            _tube(bm, [(x, y, 0.55), (x + 0.55 * math.cos(aa), y + 0.55 * math.sin(aa), 0.01)], 0.012, 6)
        st = C.from_bmesh(f'stand_{x}', bm, coll, smooth=True)
        C.set_mat(st, steel)
        fl = C.prim('cube', f'flag_{x}', loc=(x, y, 2.6), rot=(0, 0, a), scale=(0.9, 0.02, 0.7), coll=coll, smooth=False)
        C.set_mat(fl, C.mat_principled('flag_black', (0.004, 0.004, 0.004), 0.9))
        out += [st, fl]
    # rolling tool chest
    ch = C.prim('cube', 'toolchest', loc=(8.6, -3.2, 0.55), rot=(0, 0, 0.3), scale=(0.7, 1.1, 0.95), coll=coll, smooth=False)
    C.set_mat(ch, C.mat_principled('chest_paint', (0.25, 0.02, 0.015), 0.35, 0.0, coat=1.0))
    C.bevel(ch, 0.015, 2, 40)
    out.append(ch)
    bm = bmesh.new()
    for k in range(6):
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((8.6, -3.2, 0.2 + k * 0.13)) @ Matrix.Rotation(0.3, 4, 'Z')
                              @ Matrix.Translation((0.36, 0, 0)) @ Matrix.Diagonal((0.02, 0.8, 0.015, 1)))
    hd = C.from_bmesh('chest_handles', bm, coll, smooth=False)
    C.set_mat(hd, steel)
    out.append(hd)
    return out


def dust_motes(coll, n, seed=8):
    """Airborne dust: tiny specks that catch the strips/doorway (DOF turns them into soft bokeh)."""
    rng = random.Random(seed)
    tpl = _ico_tpl(0)
    items = []
    for i in range(n):
        # r3: sparse + clustered (700 evenly spread specks read as a starfield): ~60% drift in the doorway
        # sun shaft, the rest hang under the strip rows
        if rng.random() < 0.6:
            t = rng.uniform(0.0, 1.0)
            p = Vector((DOOR[0] + 0.3 + 1.7 * t, SY0 + 0.5 + 15 * t, 1.6 - 1.4 * t)) + Vector((rng.gauss(0, 0.55), rng.gauss(0, 0.8), rng.gauss(0, 0.5)))
        else:
            p = Vector((rng.choice(STRIP_X) + rng.gauss(0, 0.9), rng.uniform(-12, 10), rng.uniform(2.0, 5.2)))
        p.z = max(p.z, 0.08)
        s = rng.uniform(0.0012, 0.0035) * 2
        items.append((tpl, Matrix.Translation(p) @ Matrix.Diagonal((s, s, s, 1))))
    o = inst_mesh('motes', coll, items)
    b = C.NB('mote_m')
    b.set('Base Color', (0.75, 0.72, 0.68)).set('Roughness', 0.5).set('Emission Color', (0.7, 0.85, 1.0)).set('Emission Strength', 0.0)
    C.set_mat(o, b.mat)
    o.visible_shadow = False
    # slow settle + drift
    for f, z in ((1, 0.0), (120, -0.25)):
        o.location = (0.02 * f / 120, 0.03 * f / 120, z)
        o.keyframe_insert('location', frame=f)
    C.set_interp(o, 'LINEAR')
    return o


def scatter_debris(coll, n, seed=3):
    rng = random.Random(seed)
    tpl = _ico_tpl(1)
    items = []
    for i in range(n):
        x = rng.uniform(-SX + 0.5, SX - 0.5); y = rng.uniform(SY0 + 1, SY1 - 1)
        if abs(x) < 4.5 and abs(y) < 6.5:
            continue
        s = rng.uniform(0.006, 0.035) * (1 if rng.random() > 0.05 else 2)
        m = Matrix.Translation((x, y, s * 0.3)) @ Euler((rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 6))).to_matrix().to_4x4() \
            @ Matrix.Diagonal((s, s * rng.uniform(0.5, 1.5), s * 0.5, 1))
        items.append((tpl, m))
    o = inst_mesh('debris', coll, items)
    C.set_mat(o, mat_wall('debris_m', base=(0.12, 0.12, 0.125)))
    return o

# ----------------------------------------------------------------------------- probes

def probes(coll, floor_z=0.0, car_center=(0, 0, 0.6)):
    out = []
    try:
        # DIRECTOR FIX 13:30: PLANE probes disable screen-space reflections in this EEVEE build -> none
        raise RuntimeError('plane probe disabled')
        lp = bpy.data.lightprobes.new('floor_plane', 'PLANE')
        o = bpy.data.objects.new('floor_plane', lp)
        C.link(o, coll)
        o.location = (0, 0, floor_z + 0.002)
        o.scale = (40, 40, 1)
        try:
            lp.influence_distance = 0.05
        except Exception:
            pass
        out.append(o)
    except Exception as e:
        print('[probe] plane failed', e)
    try:
        lp = bpy.data.lightprobes.new('car_sphere', 'SPHERE')
        o = bpy.data.objects.new('car_sphere', lp)
        C.link(o, coll)
        o.location = car_center
        try:
            lp.influence_distance = 9.0
            lp.clip_start = 0.5
        except Exception:
            pass
        out.append(o)
    except Exception as e:
        print('[probe] sphere failed', e)
    return out

# ----------------------------------------------------------------------------- voxel room (GN)

def _gn_voxel_group(name, cube, origin, t0, speed, width, blow, seed=0, keep=None, avoid=None):
    """Geometry nodes: mesh verts -> points -> cube instances; animated spherical wavefront from
    `origin` (radius = speed*(frame-t0)) pushes cubes out (blow vector + noise), spins + shrinks them."""
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, Lk = ng.nodes, ng.links
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')

    def node(t, **kw):
        n = N.new(t)
        for k, v in kw.items():
            if k in n.inputs.keys():
                n.inputs[k].default_value = v
            else:
                setattr(n, k, v)
        return n

    def math_(op, a, b=None):
        n = node('ShaderNodeMath', operation=op)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                Lk.new(v, n.inputs[i])
        return n.outputs[0]

    def node_clamp(sock):
        n = node('ShaderNodeClamp')
        Lk.new(sock, n.inputs['Value'])
        return n.outputs[0]

    def vmath(op, a, b=None, scale=None):
        n = node('ShaderNodeVectorMath', operation=op)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (tuple, list, Vector)):
                n.inputs[i].default_value = v
            else:
                Lk.new(v, n.inputs[i])
        if scale is not None:
            if isinstance(scale, (int, float)):
                n.inputs['Scale'].default_value = scale
            else:
                Lk.new(scale, n.inputs['Scale'])
        return n.outputs['Value'] if op in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE') else n.outputs['Vector']

    m2p = node('GeometryNodeMeshToPoints')
    Lk.new(gi.outputs[0], m2p.inputs['Mesh'])
    pos = node('GeometryNodeInputPosition').outputs[0]
    st = node('GeometryNodeStoreNamedAttribute', data_type='FLOAT_VECTOR', domain='POINT')
    st.inputs['Name'].default_value = 'rest'
    Lk.new(m2p.outputs[0], st.inputs['Geometry']); Lk.new(pos, st.inputs['Value'])
    # time + wavefront
    tnode = node('GeometryNodeInputSceneTime')
    frame = tnode.outputs['Frame']
    R = math_('MULTIPLY', math_('SUBTRACT', frame, float(t0)), float(speed))

    def rand_f(lo, hi, sd):
        n = node('FunctionNodeRandomValue', data_type='FLOAT')
        fl = [s_ for s_ in n.inputs if s_.type == 'VALUE' and s_.name in ('Min', 'Max')]
        if len(fl) >= 2:
            fl[0].default_value = lo; fl[1].default_value = hi
        n.inputs['Seed'].default_value = sd
        outs = [o_ for o_ in n.outputs if o_.type == 'VALUE']
        return outs[0] if outs else n.outputs[1]

    nz = node('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 0.15
    nz.inputs['Detail'].default_value = 3.0
    Lk.new(pos, nz.inputs['Vector'])
    d = vmath('DISTANCE', pos, tuple(origin))
    # ragged front: low-freq noise (+-5 m) + per-cube random delay (0..3 m)
    d = math_('ADD', d, math_('MULTIPLY', math_('SUBTRACT', nz.outputs['Fac'], 0.5), 10.0))
    d = math_('SUBTRACT', d, math_('MULTIPLY', rand_f(0.0, 1.0, seed), 3.0))
    # s: 0 at rest -> 1 gone; `width` = metres of wave travel over a cube's whole flight
    cl = node('ShaderNodeClamp')
    Lk.new(math_('DIVIDE', math_('SUBTRACT', R, d), float(width)), cl.inputs['Value'])
    s = cl.outputs[0]
    s2 = math_('POWER', s, 2.2)
    away = vmath('NORMALIZE', vmath('SUBTRACT', pos, tuple(origin)))
    nzv = node('ShaderNodeTexNoise'); nzv.inputs['Scale'].default_value = 0.8
    Lk.new(pos, nzv.inputs['Vector'])
    turb = vmath('SUBTRACT', nzv.outputs['Color'], (0.5, 0.5, 0.5))
    dirv = vmath('ADD', vmath('ADD', vmath('SCALE', away, None, 2.0), tuple(blow)), vmath('SCALE', turb, None, 8.0))
    off = vmath('SCALE', dirv, None, math_('MULTIPLY', s2, math_('MULTIPLY', rand_f(0.5, 1.6, seed + 7), 3.0)))
    if keep:
        sepk = node('ShaderNodeSeparateXYZ'); Lk.new(pos, sepk.inputs[0])
        kx = math_('LESS_THAN', math_('ABSOLUTE', sepk.outputs['X']), float(keep[0]))
        ky = math_('LESS_THAN', math_('ABSOLUTE', sepk.outputs['Y']), float(keep[1]))
        off = vmath('SCALE', off, None, math_('SUBTRACT', 1.0, math_('MULTIPLY', kx, ky)))
    setp = node('GeometryNodeSetPosition')
    Lk.new(st.outputs[0], setp.inputs['Geometry'])
    Lk.new(off, setp.inputs['Offset'])
    sel = math_('GREATER_THAN', rand_f(0.0, 1.0, seed + 13), 0.92)
    life = math_('MULTIPLY', math_('SUBTRACT', 1.0, s), math_('MINIMUM', math_('MULTIPLY', s, 10.0), 1.0))
    glint = math_('MULTIPLY', sel, life)
    # hairline wavefront: a ragged glowing seam crawls over every surface just as the cubes let go
    fr = math_('SUBTRACT', 1.0, node_clamp(math_('DIVIDE', math_('ABSOLUTE', math_('SUBTRACT', R, d)), 0.45)))
    glint = math_('MAXIMUM', glint, math_('MULTIPLY', math_('POWER', fr, 2.0), 0.3))
    scp = node('GeometryNodeStoreNamedAttribute', data_type='FLOAT_VECTOR', domain='POINT')
    scp.inputs['Name'].default_value = 'cpos'
    Lk.new(setp.outputs[0], scp.inputs['Geometry']); Lk.new(node('GeometryNodeInputPosition').outputs[0], scp.inputs['Value'])
    sg = node('GeometryNodeStoreNamedAttribute', data_type='FLOAT', domain='POINT')
    sg.inputs['Name'].default_value = 'glint'
    Lk.new(scp.outputs[0], sg.inputs['Geometry']); Lk.new(glint, sg.inputs['Value'])
    cb = node('GeometryNodeMeshCube')
    cb.inputs['Size'].default_value = (cube, cube, cube)
    iop = node('GeometryNodeInstanceOnPoints')
    Lk.new(sg.outputs[0], iop.inputs['Points']); Lk.new(cb.outputs[0], iop.inputs['Instance'])
    rr = node('FunctionNodeRandomValue', data_type='FLOAT_VECTOR')
    rr.inputs[0].default_value = (-1, -1, -1); rr.inputs[1].default_value = (1, 1, 1)
    rr.inputs['Seed'].default_value = seed + 21
    rot = vmath('SCALE', rr.outputs[0], None, math_('MULTIPLY', s, 7.0))
    Lk.new(rot, iop.inputs['Rotation'])
    sc = math_('SUBTRACT', 1.0, math_('POWER', s, 2.5))   # exact tiling at rest (no coplanar overlap)
    if avoid is not None:   # keep flying cubes out of the lens: shrink inside a sphere around the camera
        dcam = vmath('DISTANCE', node('GeometryNodeInputPosition').outputs[0], tuple(avoid[0]))
        sc = math_('MULTIPLY', sc, math_('MAXIMUM', math_('LESS_THAN', s, 0.002), node_clamp(math_('DIVIDE', math_('SUBTRACT', dcam, avoid[1]), avoid[1]))))
    # client rule: real material chunks, not toy cubes -> once a voxel breaks loose it becomes a
    # slab/shard of random proportions (still a perfect tile while at rest)
    rv = node('FunctionNodeRandomValue', data_type='FLOAT_VECTOR')
    rv.inputs[0].default_value = (0.35, 0.35, 0.35); rv.inputs[1].default_value = (1.0, 1.0, 1.0)
    rv.inputs['Seed'].default_value = seed + 31
    tb = node_clamp(math_('MULTIPLY', s, 8.0))
    shape = vmath('ADD', vmath('SCALE', (1.0, 1.0, 1.0), None, math_('SUBTRACT', 1.0, tb)), vmath('SCALE', rv.outputs[0], None, tb))
    Lk.new(vmath('SCALE', shape, None, sc), iop.inputs['Scale'])
    # cull fully gone cubes
    dele = node('GeometryNodeDeleteGeometry', domain='INSTANCE')
    Lk.new(iop.outputs[0], dele.inputs['Geometry'])
    Lk.new(math_('GREATER_THAN', s, 0.995), dele.inputs['Selection'])
    Lk.new(dele.outputs[0], go.inputs[0])
    return ng


def voxel_surface(name, coll, mat, center, size, axis, cube, origin, t0, speed, width, blow, seed=0, hole=None, keep=None, avoid=None):
    """A flat surface of cube voxels. axis: 'Z' (floor/ceiling) 'X' (side wall) 'Y' (back wall)."""
    nx = max(1, int(round(size[0] / cube))); ny = max(1, int(round(size[1] / cube)))
    verts = [((i - (nx - 1) / 2) * cube, (j - (ny - 1) / 2) * cube, 0.0) for i in range(nx) for j in range(ny)]
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], []); me.update()
    o = bpy.data.objects.new(name, me); C.link(o, coll)
    if axis == 'X':
        o.rotation_euler = (0, math.pi / 2, 0)
    elif axis == 'Y':
        o.rotation_euler = (math.pi / 2, 0, 0)
    o.location = center
    # bake transform into mesh so GN positions are world-space (origin at 0)
    o.data.transform(o.matrix_basis)
    o.matrix_basis = Matrix.Identity(4)
    if hole:
        bm = bmesh.new(); bm.from_mesh(o.data)
        kill = [v for v in bm.verts if hole[0] < v.co.x < hole[1] and v.co.z < hole[2]]
        bmesh.ops.delete(bm, geom=kill, context='VERTS')
        bm.to_mesh(o.data); bm.free()
    ng = _gn_voxel_group(name + '_gn', cube, origin, t0, speed, width, blow, seed, keep, avoid)
    md = o.modifiers.new('voxels', 'NODES')
    md.node_group = ng
    C.set_mat(o, mat)
    # instances need the material on the cube itself
    nt = ng
    sm = nt.nodes.new('GeometryNodeSetMaterial')
    sm.inputs['Material'].default_value = mat
    cubenode = [n for n in nt.nodes if n.bl_idname == 'GeometryNodeMeshCube'][0]
    iop = [n for n in nt.nodes if n.bl_idname == 'GeometryNodeInstanceOnPoints'][0]
    nt.links.new(cubenode.outputs[0], sm.inputs['Geometry'])
    nt.links.new(sm.outputs[0], iop.inputs['Instance'])
    return o


AVOID = ((-2.2, 7.2, 0.45), 1.6)
VOX_AVOID = ((1.8, 7.6, 0.6), 0.55)     # r3: 2G camera zone (shards entering it are culled)


def build_voxel_room(coll, cube=0.2, origin=(DOOR[0], SY0, 1.5), t0=6, speed=2.5, width=30.0):
    fm = mat_voxel('vox_floor', mat_floor)
    wm = mat_voxel('vox_wall', mat_wall)
    cm = mat_voxel('vox_ceil', lambda n, rest=False: mat_wall(n, rest, base=(0.06, 0.065, 0.07)))
    W, L = 2 * SX, SY1 - SY0
    yc = (SY0 + SY1) / 2
    out = []
    out.append(voxel_surface('vx_floor', coll, fm, (0, yc, -cube / 2), (W, L), 'Z', cube, origin, t0, speed, width, (0, 2.5, 7), 1, keep=(1.35, 2.7), avoid=AVOID))
    out.append(voxel_surface('vx_ceil', coll, cm, (0, yc, SH + cube / 2), (W, L), 'Z', cube, origin, t0, speed * 1.15, width, (0, 2, 8), 2, avoid=AVOID))
    for i, sx in enumerate((-1, 1)):
        out.append(voxel_surface(f'vx_wall{sx}', coll, wm, (sx * (SX + cube / 2), yc, SH / 2), (SH, L), 'X', cube, origin, t0,
                                 speed * 1.08, width, (sx * 6, 2, 4), 3 + i, avoid=AVOID))
    out.append(voxel_surface('vx_back', coll, wm, (0, SY1 + cube / 2, SH / 2), (W, SH), 'Y', cube, origin, t0, speed, width,
                             (0, 2, 6), 6, avoid=AVOID))
    out.append(voxel_surface('vx_front', coll, wm, (0, SY0 - cube / 2, SH / 2), (W, SH), 'Y', cube, origin, t0 - 3, speed, width,
                             (0, 3, 5), 7, hole=(DOOR[0] - DOOR[1] / 2, DOOR[0] + DOOR[1] / 2, DOOR[2])))
    return out

# ----------------------------------------------------------------------------- r3: ballistic debris room
# Director r3: real chunks with mass. Each voxel is a perfect tile at rest; when the (accelerating, ragged)
# wavefront from the doorway reaches it, it becomes one of 5 irregular convex shards (0.5-3x), gets a small
# burst velocity + the "portal draught" (a suction field pulling everything out through the doorway) +
# gravity, tumbles with omega ~ 1/size, skids on the ground, and is culled once it has been sucked out past
# the doorway or fallen below the ground. No shrinking, no glow.

SY1V = 15.0          # 2G room ends ~6 m behind the camera so the +Y view is clear by the whip pan
VOX = dict(t0=10.0, v=1.0, acc=0.07, A=11.0, sink=(DOOR[0] + 1.5, SY0 - 10.0, 1.4))


def _gn_debris_group(name, cube, origin, seed, mat, burst=1.5, up=1.0, turbk=1.2, big=0.15, keep=None, keep_t=20.0,
                     avoid=None, cull_y=SY0 - 6.0, thin=0.0):
    t0, v, acc, A, sink = VOX['t0'], VOX['v'], VOX['acc'], VOX['A'], VOX['sink']
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, Lk = ng.nodes, ng.links
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')

    def node(t, **kw):
        n = N.new(t)
        for k, val in kw.items():
            if k in n.inputs.keys():
                n.inputs[k].default_value = val
            else:
                setattr(n, k, val)
        return n

    def lk(a, b):
        if isinstance(a, (int, float)):
            b.default_value = a
        elif isinstance(a, (tuple, list, Vector)):
            b.default_value = tuple(a)
        else:
            Lk.new(a, b)

    def m(op, a, b=None):
        n = node('ShaderNodeMath', operation=op)
        lk(a, n.inputs[0])
        if b is not None:
            lk(b, n.inputs[1])
        return n.outputs[0]

    def vm(op, a, b=None, scale=None):
        n = node('ShaderNodeVectorMath', operation=op)
        lk(a, n.inputs[0])
        if b is not None:
            lk(b, n.inputs[1])
        if scale is not None:
            lk(scale, n.inputs['Scale'])
        return n.outputs['Value'] if op in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE') else n.outputs['Vector']

    def rnd(lo, hi, sd, kind='FLOAT'):
        n = node('FunctionNodeRandomValue', data_type=kind)
        if kind == 'FLOAT':
            ins = [s_ for s_ in n.inputs if s_.type == 'VALUE' and s_.name in ('Min', 'Max')]
            ins[0].default_value = lo; ins[1].default_value = hi
            outs = [o_ for o_ in n.outputs if o_.type == 'VALUE']
        else:
            n.inputs[0].default_value = lo; n.inputs[1].default_value = hi
            outs = [o_ for o_ in n.outputs if o_.type == 'VECTOR']
        n.inputs['Seed'].default_value = sd
        return outs[0]

    def sep(vec):
        n = node('ShaderNodeSeparateXYZ'); lk(vec, n.inputs[0]); return n.outputs

    def comb(x, y, z):
        n = node('ShaderNodeCombineXYZ'); lk(x, n.inputs[0]); lk(y, n.inputs[1]); lk(z, n.inputs[2]); return n.outputs[0]

    m2p = node('GeometryNodeMeshToPoints'); Lk.new(gi.outputs[0], m2p.inputs['Mesh'])
    pos = node('GeometryNodeInputPosition').outputs[0]
    st = node('GeometryNodeStoreNamedAttribute', data_type='FLOAT_VECTOR', domain='POINT')
    st.inputs['Name'].default_value = 'rest'
    Lk.new(m2p.outputs[0], st.inputs['Geometry']); Lk.new(pos, st.inputs['Value'])
    frame = node('GeometryNodeInputSceneTime').outputs['Frame']
    nz = node('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.15; nz.inputs['Detail'].default_value = 3.0
    Lk.new(pos, nz.inputs['Vector'])
    d = vm('DISTANCE', pos, tuple(origin))
    d = m('ADD', d, m('MULTIPLY', m('SUBTRACT', nz.outputs['Fac'], 0.5), 9.0))
    d = m('MAXIMUM', m('SUBTRACT', d, m('MULTIPLY', rnd(0.0, 1.0, seed), 2.5)), 0.0)
    # accelerating wavefront R(f) = v*(f-t0) + acc/2*(f-t0)^2  ->  release frame
    tw = m('DIVIDE', m('SUBTRACT', m('SQRT', m('ADD', v * v, m('MULTIPLY', d, 2.0 * acc))), v), acc)
    tr = m('ADD', tw, t0)
    pz = sep(pos)
    kk = None
    if keep:
        kx = m('LESS_THAN', m('ABSOLUTE', m('SUBTRACT', pz[0], keep[0])), keep[1])
        ky = m('LESS_THAN', m('ABSOLUTE', m('SUBTRACT', pz[1], keep[2])), keep[3])
        kk = m('MULTIPLY', kx, ky)
        tr = m('ADD', m('MULTIPLY', tr, m('SUBTRACT', 1.0, kk)), m('MULTIPLY', m('ADD', keep_t, rnd(0.0, 3.0, seed + 3)), kk))
    t = m('DIVIDE', m('MAXIMUM', m('SUBTRACT', frame, tr), 0.0), 24.0)
    rel = m('GREATER_THAN', t, 0.0)
    away = vm('NORMALIZE', vm('SUBTRACT', pos, tuple(origin)))
    sd = vm('NORMALIZE', vm('MULTIPLY', vm('SUBTRACT', tuple(sink), pos), (0.35, 1.0, 0.22)))
    nzv = node('ShaderNodeTexNoise'); nzv.inputs['Scale'].default_value = 0.8
    Lk.new(pos, nzv.inputs['Vector'])
    turb = vm('SUBTRACT', nzv.outputs['Color'], (0.5, 0.5, 0.5))
    spd = rnd(0.6, 1.4, seed + 7)
    v0 = vm('ADD', vm('SCALE', away, None, burst), vm('SCALE', sd, None, 2.0))
    v0 = vm('ADD', v0, vm('ADD', (0.0, 0.0, up), vm('SCALE', turb, None, turbk)))
    v0 = vm('SCALE', v0, None, spd)
    acc_v = vm('ADD', vm('SCALE', sd, None, m('MULTIPLY', A, rnd(0.6, 1.25, seed + 9))), (0.0, 0.0, -9.8))
    if keep:   # floor under the car just drops away into the road (no burst into the car)
        notk = m('SUBTRACT', 1.0, kk)
        v0 = vm('SCALE', v0, None, notk)
        acc_v = vm('ADD', vm('SCALE', acc_v, None, notk), vm('SCALE', (0.0, 0.0, -9.8), None, kk))
    off = vm('ADD', vm('SCALE', v0, None, t), vm('SCALE', acc_v, None, m('MULTIPLY', m('MULTIPLY', t, t), 0.5)))
    np_ = vm('ADD', pos, off)
    nps = sep(np_)
    zg = m('MINIMUM', pz[2], 0.0)                       # ground: the chunk's own rest level for floor tiles
    zc = m('MAXIMUM', nps[2], zg)
    if keep:
        zc = m('ADD', m('MULTIPLY', zc, m('SUBTRACT', 1.0, kk)), m('MULTIPLY', nps[2], kk))
    newp = comb(nps[0], nps[1], zc)
    setp = node('GeometryNodeSetPosition')
    Lk.new(st.outputs[0], setp.inputs['Geometry']); Lk.new(newp, setp.inputs['Position'])
    scp0 = node('GeometryNodeStoreNamedAttribute', data_type='FLOAT_VECTOR', domain='POINT')
    scp0.inputs['Name'].default_value = 'cpos'
    Lk.new(setp.outputs[0], scp0.inputs['Geometry']); Lk.new(node('GeometryNodeInputPosition').outputs[0], scp0.inputs['Value'])
    scp = node('GeometryNodeStoreNamedAttribute', data_type='FLOAT', domain='POINT')
    scp.inputs['Name'].default_value = 'relf'
    Lk.new(scp0.outputs[0], scp.inputs['Geometry']); Lk.new(rel, scp.inputs['Value'])
    # rest tiles: exact cubes; released: one of 5 convex shards (separate instancers - multi-input order is
    # not reliable for Pick Instance)
    g2i = node('GeometryNodeGeometryToInstance')
    cb = node('GeometryNodeMeshCube'); cb.inputs['Size'].default_value = (cube, cube, cube)
    smc = node('GeometryNodeSetMaterial'); smc.inputs['Material'].default_value = mat
    Lk.new(cb.outputs[0], smc.inputs['Geometry'])
    props = ((1.6, 1.2, 0.45), (1.4, 0.65, 0.55), (1.0, 0.9, 0.8), (2.0, 0.55, 0.38), (1.25, 1.0, 0.62))
    for k, pr in enumerate(props):
        ico = node('GeometryNodeMeshIcoSphere'); ico.inputs['Radius'].default_value = cube * 0.55
        ico.inputs['Subdivisions'].default_value = 1
        jit = node('FunctionNodeRandomValue', data_type='FLOAT_VECTOR')
        jit.inputs[0].default_value = (-cube * 0.28,) * 3; jit.inputs[1].default_value = (cube * 0.28,) * 3
        jit.inputs['Seed'].default_value = 101 + k * 7 + seed
        spn = node('GeometryNodeSetPosition'); Lk.new(ico.outputs[0], spn.inputs['Geometry'])
        Lk.new([o_ for o_ in jit.outputs if o_.type == 'VECTOR'][0], spn.inputs['Offset'])
        tg = node('GeometryNodeTransform'); Lk.new(spn.outputs[0], tg.inputs['Geometry'])
        tg.inputs['Scale'].default_value = pr
        hull = node('GeometryNodeConvexHull'); Lk.new(tg.outputs[0], hull.inputs['Geometry'])
        ssm = node('GeometryNodeSetShadeSmooth'); Lk.new(hull.outputs[0], ssm.inputs['Geometry'])
        try:
            ssm.inputs['Shade Smooth'].default_value = False
        except Exception:
            pass
        smk = node('GeometryNodeSetMaterial'); smk.inputs['Material'].default_value = mat
        Lk.new(ssm.outputs[0], smk.inputs['Geometry'])
        Lk.new(smk.outputs[0], g2i.inputs[0])
    iop = node('GeometryNodeInstanceOnPoints')
    Lk.new(scp.outputs[0], iop.inputs['Points']); Lk.new(g2i.outputs[0], iop.inputs['Instance'])
    iop.inputs['Pick Instance'].default_value = True
    lk(m('FLOOR', rnd(0.0, 4.999, seed + 17)), iop.inputs['Instance Index'])
    lk(rel, iop.inputs['Selection'])
    iop0 = node('GeometryNodeInstanceOnPoints')
    Lk.new(scp.outputs[0], iop0.inputs['Points']); Lk.new(smc.outputs[0], iop0.inputs['Instance'])
    lk(m('SUBTRACT', 1.0, rel), iop0.inputs['Selection'])
    rb = rnd(0.0, 1.0, seed + 19)
    isbig = m('LESS_THAN', rb, big)
    sizef = m('ADD', m('MULTIPLY', isbig, rnd(1.4, 3.0, seed + 23)), m('MULTIPLY', m('SUBTRACT', 1.0, isbig), rnd(0.55, 1.05, seed + 29)))
    lk(sizef, iop.inputs['Scale'])
    omega = m('DIVIDE', rnd(3.0, 10.0, seed + 31), m('MAXIMUM', sizef, 0.4))
    axis = rnd((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0), seed + 37, 'FLOAT_VECTOR')
    rot0 = rnd((0.0, 0.0, 0.0), (6.283, 6.283, 6.283), seed + 41, 'FLOAT_VECTOR')
    rot = vm('ADD', rot0, vm('SCALE', axis, None, m('MULTIPLY', omega, t)))
    Lk.new(rot, iop.inputs['Rotation'])
    # cull: sucked out past the doorway, fallen through the ground (floor tiles under the car), lens zone
    dele = node('GeometryNodeDeleteGeometry', domain='INSTANCE')
    Lk.new(iop.outputs[0], dele.inputs['Geometry'])
    cy = m('LESS_THAN', nps[1], cull_y)
    cz = m('LESS_THAN', nps[2], -0.25)
    far = m('GREATER_THAN', vm('DISTANCE', np_, pos), 70.0)
    kill = m('MAXIMUM', m('MAXIMUM', cy, cz), far)
    if thin > 0:
        kill = m('MAXIMUM', kill, m('LESS_THAN', rnd(0.0, 1.0, seed + 53), thin))
    if avoid is not None:
        kill = m('MAXIMUM', kill, m('LESS_THAN', vm('DISTANCE', np_, tuple(avoid[0])), avoid[1]))
    Lk.new(m('MULTIPLY', kill, rel), dele.inputs['Selection'])
    jn = node('GeometryNodeJoinGeometry')
    Lk.new(iop0.outputs[0], jn.inputs[0]); Lk.new(dele.outputs[0], jn.inputs[0])
    Lk.new(jn.outputs[0], go.inputs[0])
    return ng


def debris_surface(name, coll, mat, center, size, axis, cube, origin, seed=0, hole=None, **kw):
    nx = max(1, int(round(size[0] / cube))); ny = max(1, int(round(size[1] / cube)))
    verts = [((i - (nx - 1) / 2) * cube, (j - (ny - 1) / 2) * cube, 0.0) for i in range(nx) for j in range(ny)]
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], []); me.update()
    o = bpy.data.objects.new(name, me); C.link(o, coll)
    if axis == 'X':
        o.rotation_euler = (0, math.pi / 2, 0)
    elif axis == 'Y':
        o.rotation_euler = (math.pi / 2, 0, 0)
    o.location = center
    o.data.transform(o.matrix_basis)
    o.matrix_basis = Matrix.Identity(4)
    if hole:
        bm = bmesh.new(); bm.from_mesh(o.data)
        kill = [v for v in bm.verts if hole[0] < v.co.x < hole[1] and v.co.z < hole[2]]
        bmesh.ops.delete(bm, geom=kill, context='VERTS')
        bm.to_mesh(o.data); bm.free()
    ng = _gn_debris_group(name + '_gn', cube, origin, seed, mat, **kw)
    md = o.modifiers.new('voxels', 'NODES')
    md.node_group = ng
    C.set_mat(o, mat)
    return o


def build_voxel_room2(coll, cube=0.14, avoid=None):
    fm = mat_voxel('vox_floor', mat_floor)
    wm = mat_voxel('vox_wall', mat_wall)
    cm = mat_voxel('vox_ceil', lambda n, rest=False: mat_wall(n, rest, base=(0.06, 0.065, 0.07)))
    W, L = 2 * SX, SY1V - SY0
    yc = (SY0 + SY1V) / 2
    origin = (DOOR[0], SY0, 1.5)
    out = []
    # floor: tiles hop and get dragged toward the doorway; the patch under the car + its launch lane just
    # drops away into the road at f19-22
    out.append(debris_surface('vx_floor', coll, fm, (0, yc, -cube / 2), (W, L), 'Z', cube, origin, 1, up=1.3, burst=0.8,
                              keep=(0.9, 2.5, 4.0, 6.9), keep_t=19.0, avoid=avoid, big=0.08, thin=0.35))
    out.append(debris_surface('vx_ceil', coll, cm, (0, yc, SH + cube / 2), (W, L), 'Z', cube, origin, 2, up=-0.5, burst=1.2,
                              avoid=avoid, big=0.2, thin=0.55))
    for i, sx in enumerate((-1, 1)):
        out.append(debris_surface(f'vx_wall{sx}', coll, wm, (sx * (SX + cube / 2), yc, SH / 2), (SH, L), 'X', cube, origin, 3 + i,
                                  up=0.8, burst=1.8, avoid=avoid, big=0.3, thin=0.45))
    out.append(debris_surface('vx_back', coll, wm, (0, SY1V + cube / 2, SH / 2), (W, SH), 'Y', cube, origin, 6, up=0.8,
                              burst=1.5, avoid=avoid, big=0.3, thin=0.45))
    out.append(debris_surface('vx_front', coll, wm, (0, SY0 - cube / 2, SH / 2), (W, SH), 'Y', cube, origin, 7, up=1.0,
                              burst=2.5, big=0.3, cull_y=SY0 - 14.0, thin=0.4,
                              hole=(DOOR[0] - DOOR[1] / 2, DOOR[0] + DOOR[1] / 2, DOOR[2])))
    return out

# ----------------------------------------------------------------------------- canyon (dusk)

def world_dusk(sun_elev=4.0, sun_rot=180.0, strength=1.0, fog=0.006):
    """Art-directed dusk sky: deep teal zenith -> pale teal -> warm peach horizon, hot sun glow at
    azimuth -Y (behind the canyon), elevation `sun_elev`. Optional world fog for haze/god rays."""
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
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
    ramp = N.new('ShaderNodeValToRGB')
    els = ramp.color_ramp.elements
    els[0].position = 0.0; els[0].color = (1.0, 0.50, 0.30, 1)
    els[1].position = 1.0; els[1].color = (0.03, 0.16, 0.19, 1)
    for p, col in ((0.05, (0.95, 0.62, 0.42, 1)), (0.14, (0.62, 0.70, 0.62, 1)), (0.32, (0.24, 0.55, 0.56, 1)), (0.6, (0.08, 0.30, 0.34, 1))):
        e = els.new(p); e.color = col
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -0.02; mr.inputs['From Max'].default_value = 1.0
    L.new(sep.outputs['Z'], mr.inputs['Value']); L.new(mr.outputs[0], ramp.inputs['Fac'])
    # sun glow
    e_ = math.radians(sun_elev)
    sd = (0.0, -math.cos(e_), math.sin(e_))
    dot = N.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
    L.new(nrm.outputs['Vector'], dot.inputs[0]); dot.inputs[1].default_value = sd
    cl = N.new('ShaderNodeMath'); cl.operation = 'MAXIMUM'; cl.inputs[1].default_value = 0.0
    L.new(dot.outputs['Value'], cl.inputs[0])
    p1 = N.new('ShaderNodeMath'); p1.operation = 'POWER'; p1.inputs[1].default_value = 900.0
    L.new(cl.outputs[0], p1.inputs[0])
    p2 = N.new('ShaderNodeMath'); p2.operation = 'POWER'; p2.inputs[1].default_value = 8.0
    L.new(cl.outputs[0], p2.inputs[0])
    m1 = N.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; m1.inputs[1].default_value = 60.0
    L.new(p1.outputs[0], m1.inputs[0])
    m2 = N.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; m2.inputs[1].default_value = 1.6
    L.new(p2.outputs[0], m2.inputs[0])
    g = N.new('ShaderNodeMath'); g.operation = 'ADD'
    L.new(m1.outputs[0], g.inputs[0]); L.new(m2.outputs[0], g.inputs[1])
    glow = N.new('ShaderNodeMix'); glow.data_type = 'RGBA'; glow.blend_type = 'ADD'
    L.new(g.outputs[0], glow.inputs['Factor'])
    L.new(ramp.outputs[0], glow.inputs[6]); glow.inputs[7].default_value = (1.0, 0.58, 0.30, 1)
    L.new(glow.outputs[2], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength
    L.new(bg.outputs['Background'], out.inputs['Surface'])
    if fog:
        C.add_world_fog(w, fog, (0.95, 0.72, 0.55), 0.6)
    return w

def mat_haze_rock(name='mesa', base=(0.36, 0.12, 0.06), haze=(0.85, 0.62, 0.5), k=900.0):
    """Rock with aerial perspective (mix to haze emission by camera distance; volumes stop at 200 m)."""
    m = C.mat_rock(name, base=base, dark=(0.08, 0.03, 0.02), scale=0.05)
    nt = m.node_tree
    out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    bsdf = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    cam = nt.nodes.new('ShaderNodeCameraData')
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 60.0; mr.inputs['From Max'].default_value = k
    mr.inputs['To Min'].default_value = 0.0; mr.inputs['To Max'].default_value = 0.9
    nt.links.new(cam.outputs['View Distance'], mr.inputs['Value'])
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*haze, 1); em.inputs['Strength'].default_value = 0.55
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(mr.outputs[0], mx.inputs[0])
    nt.links.new(bsdf.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs['Surface'])
    return m


def build_canyon(coll, seed=11):
    rng = random.Random(seed)
    o = {}
    # desert ground + road
    gm = C.mat_rock('ground', base=(0.30, 0.12, 0.07), dark=(0.10, 0.045, 0.03), scale=0.6, rough=0.9)
    g = C.prim('plane', 'ground', loc=(0, 0, -0.02), scale=(3000, 3000, 1), coll=coll, smooth=False)
    C.set_mat(g, gm)
    am = C.mat_asphalt('road_asphalt', scale=0.5)
    r = C.prim('plane', 'road', loc=(0, -300, -0.012), scale=(7.5, 1000, 1), coll=coll, smooth=False)
    C.set_mat(r, am)
    lm = C.mat_principled('road_line', (0.8, 0.75, 0.6), 0.5)
    bm = bmesh.new()
    for k in range(120):
        y = 60 - k * 8.0
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, y, -0.011)) @ Matrix.Diagonal((0.14, 3.5, 0.004, 1)))
    for sx in (-1, 1):
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((sx * 3.5, -300, -0.011)) @ Matrix.Diagonal((0.12, 1000, 0.004, 1)))
    ln = C.from_bmesh('road_lines', bm, coll, smooth=False); C.set_mat(ln, lm)
    # mesa silhouettes in layers
    near = mat_haze_rock('mesa_near', k=900)
    far = mat_haze_rock('mesa_far', base=(0.30, 0.13, 0.08), k=600)
    for i in range(16):
        side = -1 if i % 2 == 0 else 1
        dist = rng.uniform(140, 700)
        y = -dist
        x = side * rng.uniform(40, 420) + rng.uniform(-60, 60)
        w = rng.uniform(80, 260); dpt = rng.uniform(60, 160); h = rng.uniform(40, 120) * (dist / 400) ** 0.3
        o[f'mesa{i}'] = mesa(f'mesa{i}', coll, (x, y, 0), (w, dpt, h), near if dist < 380 else far, rng)
    # canyon walls close to the road (rust red, layered)
    for i in range(10):
        side = -1 if i % 2 == 0 else 1
        y = -40 - i * 55 + rng.uniform(-10, 10)
        x = side * rng.uniform(26, 60)
        mesa(f'wall{i}', coll, (x, y, 0), (rng.uniform(30, 70), rng.uniform(30, 60), rng.uniform(18, 45)), near, rng)
    # roadside scatter: rocks + dry shrubs (silhouettes against the low sun), reflector posts
    rk = C.mat_rock('road_rocks', base=(0.32, 0.12, 0.07), dark=(0.08, 0.03, 0.02), scale=4.0)
    bm = bmesh.new(); bm2 = bmesh.new(); bm3 = bmesh.new()
    for i in range(900):
        y = rng.uniform(-260, 30)
        side = -1 if rng.random() < 0.5 else 1
        x = side * (5.0 + abs(rng.gauss(0, 1)) * 14)
        if y > SY0 - 1 and abs(x) < SX + 1:
            continue
        s = rng.uniform(0.08, 0.6) * (1 + abs(y) / 120)
        m = Matrix.Translation((x, y, s * 0.2)) @ Euler((rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 6))).to_matrix().to_4x4() \
            @ Matrix.Diagonal((s, s * rng.uniform(0.6, 1.3), s * rng.uniform(0.4, 0.8), 1))
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.5, matrix=m)
    for i in range(400):
        y = rng.uniform(-200, 25)
        side = -1 if rng.random() < 0.5 else 1
        x = side * (4.5 + abs(rng.gauss(0, 1)) * 10)
        if y > SY0 - 1 and abs(x) < SX + 1:
            continue
        h = rng.uniform(0.3, 1.1)
        for k in range(7):
            a = rng.uniform(0, 6.28); t = rng.uniform(0.3, 1.0)
            tip = Vector((x + math.cos(a) * h * 0.5 * t, y + math.sin(a) * h * 0.5 * t, h * t))
            _tube(bm2, [Vector((x, y, 0)), (Vector((x, y, 0)) + tip) * 0.5 + Vector((0, 0, h * 0.1)), tip], 0.012 * h, 4)
    for k in range(60):
        for side in (-1, 1):
            y = SY0 - 3 - k * 25.0
            bmesh.ops.create_cube(bm3, size=1.0, matrix=Matrix.Translation((side * 4.6, y, 0.45)) @ Matrix.Diagonal((0.08, 0.08, 0.9, 1)))
    rocks = C.from_bmesh('road_rocks', bm, coll, smooth=True); C.set_mat(rocks, rk)
    shrubs = C.from_bmesh('shrubs', bm2, coll, smooth=True); C.set_mat(shrubs, C.mat_principled('shrub', (0.06, 0.035, 0.02), 0.8))
    posts = C.from_bmesh('posts', bm3, coll, smooth=False); C.set_mat(posts, C.mat_principled('post', (0.6, 0.58, 0.55), 0.5, emit=(1.0, 0.25, 0.05), emit_strength=0.0))
    # sun lamp (warm, low, behind the canyon = in front of the camera)
    sun = C.light('SUN', 'dusk_sun', (0, 0, 10), energy=5.0, color=(1.0, 0.6, 0.36), size=1.0)
    sun.rotation_euler = (math.radians(86), 0, 0)   # light travels toward +Y, elevation ~4 deg
    o['sun'] = sun
    return o


def mesa(name, coll, loc, size, mat, rng):
    """Flat-topped butte: displaced subdivided box with eroded strata."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=10, use_grid_fill=True)
    sx, sy, sz = size
    for v in bm.verts:
        x, y, z = v.co
        z01 = z + 0.5
        taper = 1.0 + 0.35 * (1 - z01) ** 2       # wider at the base
        n = math.sin(x * 7 + rng.random()) * 0.04 + math.sin(y * 9) * 0.04
        v.co.x = x * sx * taper * (1 + n)
        v.co.y = y * sy * taper * (1 + n)
        v.co.z = max(0.0, z01) * sz * (1 + 0.05 * math.sin(x * 13 + y * 5))
    o = C.from_bmesh(name, bm, coll, smooth=True, sharp_angle=50)
    o.location = loc
    o.rotation_euler = (0, 0, rng.uniform(0, 3.14))
    dm = o.modifiers.new('disp', 'DISPLACE')
    tex = bpy.data.textures.new(name + '_tx', 'CLOUDS')
    tex.noise_scale = 0.25 * max(sx, sy) / 100
    tex.noise_depth = 4
    dm.texture = tex; dm.strength = sz * 0.12; dm.texture_coords = 'LOCAL'
    C.set_mat(o, mat)
    return o

# ----------------------------------------------------------------------------- canyon v2 (2G reveal)
# Lessons: a WORLD volume in EEVEE Next is infinite and swallows the sky (v2 rendered a brown night);
# atmosphere now = aerial perspective inside the materials + a big bounded haze box.

def sun_vector(elev_deg=4.0, az_deg=0.0):
    """Unit vector pointing TO the sun; az 0 = -Y (behind the studio doorway), +az rotates toward +X."""
    e, a = math.radians(elev_deg), math.radians(az_deg)
    return Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))


def world_dusk2(sun, strength=1.0):
    """Teal zenith -> pale jade -> cream/peach horizon band, layered sun glow + small hot disc. No volume."""
    w = bpy.data.worlds.new('DuskSky')
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
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
    # r3: Act III (canyon.mat_sky_world) palette, slightly deeper: cream-mint horizon band -> teal zenith
    stops = [(0.0, (0.10, 0.07, 0.06)), (0.49, (0.42, 0.30, 0.24)), (0.502, (0.95, 0.80, 0.62)),
             (0.515, (0.66, 0.84, 0.72)), (0.56, (0.34, 0.66, 0.60)), (0.66, (0.15, 0.46, 0.45)),
             (0.80, (0.06, 0.30, 0.33)), (1.0, (0.03, 0.17, 0.20))]
    while len(els) > 2:
        els.remove(els[-1])
    for i, (p, c) in enumerate(stops):
        e = els[i] if i < 2 else els.new(p)
        e.position = p; e.color = (*c, 1)
    zr = N.new('ShaderNodeMapRange')
    zr.inputs['From Min'].default_value = -1; zr.inputs['From Max'].default_value = 1
    L.new(sep.outputs['Z'], zr.inputs['Value']); L.new(zr.outputs['Result'], rmp.inputs['Fac'])
    dot = N.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
    L.new(nrm.outputs['Vector'], dot.inputs[0]); dot.inputs[1].default_value = tuple(sun)
    mu = N.new('ShaderNodeMath'); mu.operation = 'MAXIMUM'
    L.new(dot.outputs['Value'], mu.inputs[0]); mu.inputs[1].default_value = 0.0

    def pw(e, k):
        p = N.new('ShaderNodeMath'); p.operation = 'POWER'; L.new(mu.outputs[0], p.inputs[0]); p.inputs[1].default_value = e
        m = N.new('ShaderNodeMath'); m.operation = 'MULTIPLY'; L.new(p.outputs[0], m.inputs[0]); m.inputs[1].default_value = k
        return m.outputs[0]

    def add(a, b):
        n = N.new('ShaderNodeMath'); n.operation = 'ADD'; L.new(a, n.inputs[0]); L.new(b, n.inputs[1])
        return n.outputs[0]
    g = add(add(pw(3.0, 0.45), pw(40.0, 1.6)), pw(600.0, 7.0))
    disc = N.new('ShaderNodeMath'); disc.operation = 'GREATER_THAN'
    L.new(dot.outputs['Value'], disc.inputs[0]); disc.inputs[1].default_value = math.cos(math.radians(0.55))
    dm = N.new('ShaderNodeMath'); dm.operation = 'MULTIPLY'; L.new(disc.outputs[0], dm.inputs[0]); dm.inputs[1].default_value = 40.0
    g = add(g, dm.outputs[0])
    # the glow hugs the horizon (flattened, like a real low sun through haze)
    hz = N.new('ShaderNodeMapRange')
    hz.inputs['From Min'].default_value = 0.0; hz.inputs['From Max'].default_value = 0.4
    hz.inputs['To Min'].default_value = 1.0; hz.inputs['To Max'].default_value = 0.2
    L.new(sep.outputs['Z'], hz.inputs['Value'])
    gm = N.new('ShaderNodeMath'); gm.operation = 'MULTIPLY'; L.new(g, gm.inputs[0]); L.new(hz.outputs['Result'], gm.inputs[1])
    cmb = N.new('ShaderNodeCombineColor')
    for ch in ('Red', 'Green', 'Blue'):
        L.new(gm.outputs[0], cmb.inputs[ch])
    warm = N.new('ShaderNodeMix'); warm.data_type = 'RGBA'; warm.blend_type = 'MULTIPLY'; warm.inputs['Factor'].default_value = 1.0
    warm.inputs[6].default_value = (1.0, 0.56, 0.28, 1)
    L.new(cmb.outputs[0], warm.inputs[7])
    addc = N.new('ShaderNodeMix'); addc.data_type = 'RGBA'; addc.blend_type = 'ADD'; addc.inputs['Factor'].default_value = 1.0
    L.new(rmp.outputs['Color'], addc.inputs[6]); L.new(warm.outputs[2], addc.inputs[7])
    L.new(addc.outputs[2], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength
    L.new(bg.outputs['Background'], out.inputs['Surface'])
    return w


def aerial(mat, sun, dist=1400.0, maxf=0.97, base=(0.52, 0.66, 0.62), warm=(1.0, 0.64, 0.40), height_fall=120.0, k=1.0):
    """Aerial perspective: mix the surface toward a view-dependent haze emission by camera distance
    (warmer toward the sun, thinner with altitude)."""
    import sys as _s
    if '--noaerial' in _s.argv:
        return mat
    nt = mat.node_tree
    N, Lk = nt.nodes, nt.links
    out = [n for n in N if n.type == 'OUTPUT_MATERIAL'][0]
    src = out.inputs['Surface'].links[0].from_socket

    def m_(op, a, b=None):
        n = N.new('ShaderNodeMath'); n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                Lk.new(v, n.inputs[i])
        return n.outputs[0]
    cam = N.new('ShaderNodeCameraData')
    geo = N.new('ShaderNodeNewGeometry')
    sep = N.new('ShaderNodeSeparateXYZ'); Lk.new(geo.outputs['Position'], sep.inputs[0])
    hf = m_('EXPONENT', m_('MULTIPLY', m_('MAXIMUM', sep.outputs['Z'], 0.0), -1.0 / height_fall))
    dens = m_('ADD', 0.3, m_('MULTIPLY', hf, 0.7))
    T = m_('EXPONENT', m_('MULTIPLY', m_('MULTIPLY', cam.outputs['View Distance'], dens), -k / dist))
    fac = m_('MINIMUM', m_('SUBTRACT', 1.0, T), maxf)
    vm = N.new('ShaderNodeVectorMath'); vm.operation = 'DOT_PRODUCT'
    Lk.new(geo.outputs['Incoming'], vm.inputs[0]); vm.inputs[1].default_value = tuple(-c for c in sun)
    mu = m_('MAXIMUM', vm.outputs['Value'], 0.0)
    g = m_('ADD', m_('MULTIPLY', m_('POWER', mu, 4.0), 1.0), m_('MULTIPLY', m_('POWER', mu, 40.0), 1.8))
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    Lk.new(m_('MINIMUM', g, 1.0), mx.inputs['Factor'])
    mx.inputs[6].default_value = (*base, 1); mx.inputs[7].default_value = (*warm, 1)
    em = N.new('ShaderNodeEmission')
    Lk.new(mx.outputs[2], em.inputs['Color'])
    Lk.new(m_('ADD', 0.6, m_('MULTIPLY', g, 0.9)), em.inputs['Strength'])
    ms = N.new('ShaderNodeMixShader')
    Lk.new(fac, ms.inputs[0]); Lk.new(src, ms.inputs[1]); Lk.new(em.outputs[0], ms.inputs[2])
    Lk.new(ms.outputs[0], out.inputs['Surface'])
    return mat


def mat_mesa(name, sun, dist=1400.0, base=(0.30, 0.07, 0.03)):
    """Rust sandstone with horizontal strata bands (world Z), streaked desert varnish, aerial haze."""
    b = C.NB(name)
    geo = b.n('ShaderNodeNewGeometry')
    pos = geo.outputs['Position']
    sep = b.n('ShaderNodeSeparateXYZ'); b.link(pos, sep.inputs[0])
    warp = b.noise(pos, 0.02, 4, 0.6)
    zw = b.math('ADD', sep.outputs['Z'], b.math('MULTIPLY', warp.outputs['Fac'], 14.0))
    bands = b.math('FRACT', b.math('MULTIPLY', zw, 1 / 9.0))
    band_col = b.ramp(bands, [(0.0, (0.20, 0.06, 0.035)), (0.22, (0.16, 0.07, 0.09)), (0.35, base), (0.55, (0.46, 0.22, 0.07)),
                              (0.7, (0.30, 0.08, 0.035)), (0.82, (0.13, 0.055, 0.075)), (0.92, (0.38, 0.13, 0.05))])
    st = b.noise(b.coord('Object', (0.08, 0.08, 0.004)), 3.0, 6, 0.6)   # vertical varnish streaks
    col = b.mix(band_col.outputs[0], (0.08, 0.03, 0.02), b.maprange(st.outputs['Fac'], 0.5, 0.75, 0, 0.7))
    b.set('Base Color', col)
    b.set('Roughness', 0.9)
    fine = b.noise(pos, 0.6, 8, 0.65)
    b.set('Normal', b.bump(b.math('ADD', fine.outputs['Fac'], bands), 0.5, 1.0))
    return aerial(b.mat, sun, dist)


def butte(name, coll, center, R, H, seed, mat, nseg=72, nz_=26, aspect=1.0, rot=0.0, tiers=True):
    """Flat-topped butte: talus skirt, vertical strata cliff with ledges/undercuts, eroded rim, flat cap."""
    from mathutils import noise as MN
    rng = random.Random(seed)
    off = Vector((rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50)))
    cx, cy, cz = center
    bm = bmesh.new()
    zs = [-10.0] + [H * (k / nz_) for k in range(nz_ + 1)]
    talus = H * rng.uniform(0.25, 0.45)
    t1, t2 = rng.uniform(0.40, 0.52), rng.uniform(0.68, 0.80)
    if rng.random() < 0.35:
        t2 = 2.0                        # some are two-tier only
    rings = []
    ca_, sa_ = math.cos(rot), math.sin(rot)
    for i in range(nseg):
        a = 2 * math.pi * i / nseg
        ca, sa = math.cos(a), math.sin(a)
        r0 = R * (1 + 0.45 * MN.fractal(Vector((ca * 1.6, sa * 1.6, 0)) + off, 0.6, 2.0, 5))
        ring = []
        for z in zs:
            zz = max(z, 0.0)
            r = r0
            if zz < talus:
                r *= 1 + 0.55 * ((talus - zz) / talus) ** 1.6
            ledge = (zz / (H * 0.17)) % 1.0
            r *= 1 - 0.012 * ledge
            if tiers:      # r3: stepped tiers (was a tin can): benches at ~45% and ~74% of the height
                u_ = zz / H
                r *= 1.0 - 0.18 * min(1.0, max(0.0, (u_ - t1) / 0.05)) - 0.16 * min(1.0, max(0.0, (u_ - t2) / 0.04))
            r *= 1 + 0.07 * MN.noise(Vector((ca * 5, sa * 5, z * 0.04)) + off)
            r *= 1 + 0.045 * MN.noise(Vector((ca * 16, sa * 16, z * 0.012)) + off)     # vertical erosion gullies
            if z > H * 0.93:     # eroded rim notches
                r *= 1 - 0.06 * max(0.0, MN.noise(Vector((ca * 9, sa * 9, 3.0)) + off))
            px, py = ca * r * aspect, sa * r
            ring.append(bm.verts.new((cx + px * ca_ - py * sa_, cy + px * sa_ + py * ca_, cz + z)))
        rings.append(ring)
    n = len(zs)
    for i in range(nseg):
        A_, B_ = rings[i], rings[(i + 1) % nseg]
        for j in range(n - 1):
            bm.faces.new((A_[j], B_[j], B_[j + 1], A_[j + 1]))
    top = bm.verts.new((cx, cy, cz + H + R * 0.01))
    for i in range(nseg):
        bm.faces.new((rings[i][-1], rings[(i + 1) % nseg][-1], top))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = C.from_bmesh(name, bm, coll, smooth=True, sharp_angle=55)
    C.set_mat(o, mat)
    try:
        o.visible_shadow = False
    except Exception:
        pass
    return o


def mat_desert(name, sun, dist=1400.0):
    b = C.NB(name)
    v = b.coord('Object', 1.0)
    n1 = b.noise(v, 0.08, 6, 0.6)
    n2 = b.noise(v, 3.0, 6, 0.6)
    g = b.noise(v, 90.0, 2, 0.5)
    col = b.ramp(n1.outputs['Fac'], [(0.3, (0.16, 0.055, 0.03)), (0.55, (0.34, 0.13, 0.065)), (0.75, (0.42, 0.19, 0.10))])
    col = b.mix(col.outputs[0], (0.08, 0.03, 0.02), b.maprange(n2.outputs['Fac'], 0.55, 0.75, 0, 0.6))
    b.set('Base Color', b.mix(col, (0.55, 0.36, 0.24), b.maprange(g.outputs['Fac'], 0.62, 0.72, 0, 0.5)))
    b.set('Roughness', 0.92)
    b.set('Normal', b.bump(b.math('ADD', n2.outputs['Fac'], g.outputs['Fac']), 0.6, 0.02))
    return aerial(b.mat, sun, dist)


def mat_road2(name, sun, dist=1400.0):
    """Sun-bleached asphalt with tar seams, worn edges, slightly glossy so the sky glints in it."""
    b = C.NB(name)
    v = b.coord('Object', 1.0)
    n1 = b.noise(v, 0.3, 6, 0.55)
    g = b.noise(v, 260.0, 2, 0.5)
    # sparse longitudinal crack-sealant squiggles (stretched + noise-masked voronoi edges)
    # dark tar patches + oil drip line down the lane centre (no cell patterns: they read as tiles/arrows)
    patch = b.noise(b.coord('Object', (0.6, 0.15, 1.0)), 1.5, 4, 0.6)
    sepr = b.n('ShaderNodeSeparateXYZ'); b.link(v, sepr.inputs[0])
    drip = b.maprange(b.math('ABSOLUTE', b.math('SUBTRACT', b.math('ABSOLUTE', sepr.outputs['X']), 1.85)), 0.5, 0.0, 0, 0.5)
    seam = b.math('MAXIMUM', b.maprange(patch.outputs['Fac'], 0.62, 0.68, 0, 0.8), drip)
    col = b.ramp(n1.outputs['Fac'], [(0.3, (0.035, 0.034, 0.036)), (0.7, (0.075, 0.07, 0.068))])
    col = b.mix(col.outputs[0], (0.16, 0.15, 0.14), b.maprange(g.outputs['Fac'], 0.6, 0.72, 0, 0.6))
    col = b.mix(col, (0.008, 0.008, 0.009), seam)
    b.set('Base Color', col)
    b.set('Roughness', b.mix(b.maprange(n1.outputs['Fac'], 0.3, 0.7, 0.55, 0.8), (0.25, 0.25, 0.25), seam))
    b.set('Normal', b.bump(b.math('SUBTRACT', g.outputs['Fac'], seam), 0.25, 0.004))
    return aerial(b.mat, sun, dist)


def build_canyon2(coll, sun, seed=11):
    """Dusk desert vista down the -Y axis: road to the vanishing point, layered rust buttes that stay
    LOW in frame (sky owns the upper half), roadside rocks/scrub/posts, warm low sun lamp."""
    import time as _tm
    _t0 = _tm.time()
    rng = random.Random(seed)
    o = {}
    g = C.prim('plane', 'ground', loc=(0, -1500, -0.02), scale=(9000, 9000, 1), coll=coll, smooth=False)
    C.set_mat(g, mat_desert('desert', sun)); _apply_scale(g)
    # r3: the road is Act III's (lib/canyon.mat_road: worn amber dashes, worn edge lines, dust film) along the
    # whole +-3 km so the 2G ending cuts to 3A on the same road (built in build_canyon_plus)
    # buttes: (distance, lateral, R, H)  -- elevations kept under ~7 deg from a 0.4 m camera
    near_m = mat_mesa('mesa_near', sun, 1400)
    far_m = mat_mesa('mesa_far', sun, 900, base=(0.36, 0.14, 0.08))
    specs = [(420, -230, 70, 34), (980, 430, 130, 58), (760, -520, 150, 70), (900, 170, 90, 62), (1150, 620, 220, 95),
             (1350, -150, 120, 80), (1700, -900, 300, 120), (2100, 420, 260, 130), (2600, -380, 380, 150),
             (3100, 1100, 420, 170), (3400, -1600, 500, 180), (3900, 150, 520, 160), (650, -330, 60, 26), (300, 140, 40, 14)]
    for i, (d, x, R, H) in enumerate(specs):
        butte(f'butte{i}', coll, (x + rng.uniform(-30, 30), -d, -1.0), R, H, 50 + i, near_m if d < 1200 else far_m,
              aspect=rng.uniform(0.8, 1.6), rot=rng.uniform(0, 3.14))
    # low rock outcrops closer to the road (dark rust silhouettes against the bright horizon)
    for i in range(12):
        side = -1 if i % 2 == 0 else 1
        d = 45 + i * 22 + rng.uniform(-8, 8)
        x = side * rng.uniform(18, 60)
        butte(f'outcrop{i}', coll, (x, -d, -0.5), rng.uniform(5, 14), rng.uniform(2.5, 7.0), 200 + i, near_m, nseg=40, nz_=14,
              aspect=rng.uniform(0.7, 2.2), rot=rng.uniform(0, 3.14), tiers=False)
    # r3: low noise ridges at 150 / 400 / 900 m = layered depth with progressive aerial haze
    from mathutils import noise as MN
    for k, (dd, hh) in enumerate(((150.0, 9.0), (400.0, 16.0), (900.0, 26.0))):
        bmr = bmesh.new()
        prev = None
        for i in range(161):
            x = -1600 + 3200 * i / 160
            if abs(x) < 6 + dd * 0.012:
                x = math.copysign(6 + dd * 0.012, x) if x != 0 else 6.0
            h = hh * (0.35 + 0.65 * (0.5 + 0.5 * MN.fractal(Vector((x * 0.004, k * 3.1, 0.0)), 0.6, 2.0, 5)))
            if abs(x) < 40 + dd * 0.05:    # the road cut: the ridge dips where the road passes through
                h *= 0.25 + 0.75 * (abs(x) / (40 + dd * 0.05)) ** 2
            y = -dd - 20 * MN.noise(Vector((x * 0.01, k, 1.0)))
            col = [bmr.verts.new((x, y, -1.0)), bmr.verts.new((x, y - 6.0, h * 0.85)), bmr.verts.new((x, y - 14.0, h)),
                   bmr.verts.new((x, y - 40.0, h * 0.7))]
            if prev is not None:
                for j in range(3):
                    bmr.faces.new((prev[j], col[j], col[j + 1], prev[j + 1]))
            prev = col
        ro = C.from_bmesh(f'ridge{k}', bmr, coll, smooth=True, sharp_angle=60)
        C.set_mat(ro, near_m if dd < 500 else far_m)
        ro.visible_shadow = False
    print('[canyon2] buttes %.1fs' % (_tm.time() - _t0))
    # roadside scatter: rocks + dry scrub + reflector posts (red reflectors catch the car light)
    rk = aerial(C.mat_rock('road_rocks2', base=(0.34, 0.13, 0.07), dark=(0.08, 0.03, 0.02), scale=4.0), sun)
    bm2 = bmesh.new(); bm3 = bmesh.new(); bm4 = bmesh.new()
    items = []
    t1, t2 = _ico_tpl(1), _ico_tpl(2)
    for i in range(1400):
        y = rng.uniform(-420, -24)
        side = -1 if rng.random() < 0.5 else 1
        x = side * (4.6 + abs(rng.gauss(0, 1)) * 16)
        s = rng.uniform(0.05, 0.5) * (1 + abs(y) / 90) * (1 if rng.random() > 0.08 else 2.5)
        m = Matrix.Translation((x, y, s * 0.15)) @ Euler((rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 6))).to_matrix().to_4x4() \
            @ Matrix.Diagonal((s, s * rng.uniform(0.6, 1.3), s * rng.uniform(0.35, 0.7), 1))
        items.append((t2 if s > 0.4 else t1, m))
    for i in range(520):
        y = rng.uniform(-300, -24)
        side = -1 if rng.random() < 0.5 else 1
        x = side * (4.4 + abs(rng.gauss(0, 1)) * 12)
        h = rng.uniform(0.25, 1.0) * (1 + abs(y) / 200)
        for k in range(9):
            a = rng.uniform(0, 6.28); t = rng.uniform(0.35, 1.0)
            base_ = Vector((x, y, 0))
            tip = Vector((x + math.cos(a) * h * 0.55 * t, y + math.sin(a) * h * 0.55 * t, h * t))
            _tube(bm2, [base_, (base_ + tip) * 0.5 + Vector((0, 0, h * 0.12)), tip], 0.010 * h + 0.004, 4)
    for k in range(70):
        for side in (-1, 1):
            y = -30 - k * 20.0
            bmesh.ops.create_cube(bm3, size=1.0, matrix=Matrix.Translation((side * 4.7, y, 0.45)) @ Matrix.Diagonal((0.07, 0.07, 0.9, 1)))
            bmesh.ops.create_cube(bm4, size=1.0, matrix=Matrix.Translation((side * 4.7, y + 0.04, 0.78)) @ Matrix.Diagonal((0.05, 0.012, 0.12, 1)))
    print('[canyon2] scatter loops %.1fs' % (_tm.time() - _t0))
    rocks = inst_mesh('road_rocks', coll, items, smooth=True); C.set_mat(rocks, rk)
    shrubs = C.from_bmesh('shrubs', bm2, coll, smooth=True)
    C.set_mat(shrubs, aerial(C.mat_principled('shrub2', (0.05, 0.03, 0.018), 0.85), sun))
    posts = C.from_bmesh('posts', bm3, coll, smooth=False)
    C.set_mat(posts, aerial(C.mat_principled('post2', (0.55, 0.53, 0.5), 0.5), sun))
    refl = C.from_bmesh('reflectors', bm4, coll, smooth=False)
    C.set_mat(refl, C.mat_principled('reflector', (0.6, 0.02, 0.01), 0.15, emit=(1.0, 0.05, 0.02), emit_strength=6.0))
    # sun lamp (warm, grazing): light travels along -sun
    sun_l = C.light('SUN', 'dusk_sun', (0, 0, 10), energy=4.5, color=(1.0, 0.62, 0.38), size=0.8)
    sun_l.rotation_euler = (-Vector(sun)).to_track_quat('-Z', 'Y').to_euler()
    o['sun'] = sun_l
    build_canyon_plus(coll, sun)
    print('[canyon2] +Y canyon %.1fs' % (_tm.time() - _t0))
    print('[canyon2] total %.1fs' % (_tm.time() - _t0))
    return o

# ----------------------------------------------------------------------------- r3: +Y canyon (2G ending / T2)
# The car launches toward +Y and the shot ends looking +Y, so the world must exist there too and match 3A:
# lib/canyon.mat_road (worn amber dashed centre line, worn edge lines at +-3.42 m, dust film), rust strata
# cliff walls (canyon.mat_canyon_rock) 25-40 m off the road, Act III haze colour.

def road_uv_plane(name, coll, mat, y0, y1, half=4.6):
    """Road quad strip with UV = (lateral metres, along metres) for canyon.mat_road."""
    import numpy as np
    ys = np.linspace(y0, y1, 61)
    xs = np.array([-half, -half * 0.5, 0.0, half * 0.5, half])
    P = np.zeros((len(ys), len(xs), 3))
    UV = np.zeros((len(ys), len(xs), 2))
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            P[i, j] = (x, y, -0.012)
            UV[i, j] = (x, y)
    import canyon as CY
    o = CY.grid_mesh(name, P, coll, smooth_=False, uv=UV)
    C.set_mat(o, mat)
    return o


def cliff_wall(name, coll, mat, side, y0, y1, seed=3, d0=30.0, H0=45.0, ny=260, nzr=26):
    """Rust strata cliff wall facing the road (x = side * ~d0), ragged rim, ledges, gullies, base talus."""
    import numpy as np
    from mathutils import noise as MN
    off = Vector((seed * 13.1, seed * 7.7, 0.0))
    ys = np.linspace(y0, y1, ny)
    P = np.zeros((ny, nzr + 2, 3))
    for i, y in enumerate(ys):
        dn = MN.fractal(Vector((y * 0.012, 0.3, 0.0)) + off, 0.6, 2.0, 4)
        d = d0 + 9.0 * dn
        H = H0 * (1.0 + 0.35 * MN.fractal(Vector((y * 0.006, 1.7, 0.0)) + off, 0.6, 2.0, 3))
        rim = H * (1.0 + 0.10 * MN.noise(Vector((y * 0.05, 4.0, 0.0)) + off))
        for j in range(nzr + 2):
            if j == nzr + 1:          # flat-ish cap going back from the rim
                z = rim + 2.0
                dd = d + 60.0
            else:
                u = j / nzr
                z = rim * u
                # talus at the base, near-vertical face above with ledges + gullies
                talus = 7.0 * max(0.0, 1.0 - u * 4.0) ** 1.5
                ledge = 1.2 * (((z / 6.5) % 1.0) - 0.5)
                gully = 2.2 * MN.noise(Vector((y * 0.09, z * 0.02, 2.0)) + off)
                lean = -0.10 * z
                dd = d - talus + ledge + gully + lean + 1.4 * MN.noise(Vector((y * 0.3, z * 0.3, 5.0)) + off)
            P[i, j] = (side * dd, y, z - 0.5)
    import canyon as CY
    o = CY.grid_mesh(name, P, coll, smooth_=True, sharp=50.0)
    if side > 0:
        o.data.flip_normals()
    C.set_mat(o, mat)
    try:
        o.visible_shadow = True
    except Exception:
        pass
    return o


def build_canyon_plus(coll, sun, seed=23):
    """+Y half of the 2G world (where the car drives off): 3A road paint, cliff walls, buttes, scrub, posts."""
    import canyon as CY
    rng = random.Random(seed)
    CY.SUN = Vector(sun)
    road_m = CY.mat_road('road3A')
    road_uv_plane('road_3A', coll, road_m, -3000.0, 3000.0)
    rock_m = CY.mat_canyon_rock('cliff3A', dist=CY.HAZE_D)
    for side, d0, H0, sd in ((-1, 27.0, 42.0, 5), (1, 33.0, 52.0, 9)):
        cliff_wall(f'cliff_{side}', coll, rock_m, side, 24.0, 1400.0, seed=sd, d0=d0, H0=H0)
    # mirrored far buttes beyond the cliffs (they show in the gap at the vanishing point)
    near_m = mat_mesa('mesa_nearP', sun, 1400)
    far_m = mat_mesa('mesa_farP', sun, 900, base=(0.36, 0.14, 0.08))
    for i, (d, x, R, H) in enumerate(((1600, -260, 220, 95), (2100, 380, 300, 130), (2600, -60, 380, 150), (3200, 700, 420, 170))):
        butte(f'butteP{i}', coll, (x + rng.uniform(-30, 30), d, -1.0), R, H, 300 + i, near_m if d < 1200 else far_m,
              aspect=rng.uniform(0.8, 1.6), rot=rng.uniform(0, 3.14))
    # talus boulders along both cliff bases + roadside rocks/scrub/posts on +Y
    bmat = CY.mat_boulder('boulder3A')
    items = []
    t1, t2 = _ico_tpl(1), _ico_tpl(2)
    for i in range(900):
        y = rng.uniform(20, 700)
        side = -1 if rng.random() < 0.5 else 1
        if rng.random() < 0.55:
            x = side * rng.uniform(18, 30)          # cliff talus
            s = rng.uniform(0.3, 2.2)
        else:
            x = side * (4.6 + abs(rng.gauss(0, 1)) * 9)   # roadside
            s = rng.uniform(0.05, 0.45)
        m = Matrix.Translation((x, y, s * 0.12)) @ Euler((rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 6))).to_matrix().to_4x4() \
            @ Matrix.Diagonal((s, s * rng.uniform(0.6, 1.3), s * rng.uniform(0.35, 0.7), 1))
        items.append((t2 if s > 0.4 else t1, m))
    rocks = inst_mesh('road_rocksP', coll, items, smooth=True); C.set_mat(rocks, bmat)
    bm2 = bmesh.new(); bm3 = bmesh.new(); bm4 = bmesh.new()
    for i in range(420):
        y = rng.uniform(17, 400)
        side = -1 if rng.random() < 0.5 else 1
        x = side * (4.4 + abs(rng.gauss(0, 1)) * 10)
        h = rng.uniform(0.25, 0.9)
        cx = x + rng.gauss(0, 0.6)
        for k in range(9):
            a = rng.uniform(0, 6.28); t = rng.uniform(0.35, 1.0)
            base_ = Vector((cx, y, 0))
            tip = Vector((cx + math.cos(a) * h * 0.55 * t, y + math.sin(a) * h * 0.55 * t, h * t))
            _tube(bm2, [base_, (base_ + tip) * 0.5 + Vector((0, 0, h * 0.12)), tip], 0.010 * h + 0.004, 4)
    for k in range(60):
        for side in (-1, 1):
            y = 20 + k * 20.0
            bmesh.ops.create_cube(bm3, size=1.0, matrix=Matrix.Translation((side * 4.7, y, 0.45)) @ Matrix.Diagonal((0.07, 0.07, 0.9, 1)))
            bmesh.ops.create_cube(bm4, size=1.0, matrix=Matrix.Translation((side * 4.7, y - 0.04, 0.78)) @ Matrix.Diagonal((0.05, 0.012, 0.12, 1)))
    shrubs = C.from_bmesh('shrubsP', bm2, coll, smooth=True)
    C.set_mat(shrubs, aerial(C.mat_principled('shrubP', (0.05, 0.03, 0.018), 0.85), sun))
    posts = C.from_bmesh('postsP', bm3, coll, smooth=False)
    C.set_mat(posts, aerial(C.mat_principled('postP', (0.55, 0.53, 0.5), 0.5), sun))
    refl = C.from_bmesh('reflectorsP', bm4, coll, smooth=False)
    C.set_mat(refl, C.mat_principled('reflectorP', (0.6, 0.02, 0.01), 0.15, emit=(1.0, 0.05, 0.02), emit_strength=6.0))
    # faint high cirrus streaks, lit warm (the sky was an empty gradient over half the frame)
    b = C.NB('cirrus')
    v = b.coord('Object', 1.0)
    st_ = b.noise(b.coord('Object', (0.25, 2.5, 1.0)), 1.2, 6, 0.62, dist=0.8)
    br = b.noise(v, 3.0, 4, 0.6)
    a_ = b.math('MULTIPLY', b.maprange(st_.outputs['Fac'], 0.56, 0.72, 0.0, 0.32), b.maprange(br.outputs['Fac'], 0.35, 0.65, 0.3, 1.0))
    em = b.n('ShaderNodeEmission'); em.inputs['Color'].default_value = (1.0, 0.72, 0.52, 1); em.inputs['Strength'].default_value = 0.55
    tr = b.n('ShaderNodeBsdfTransparent')
    mx = b.n('ShaderNodeMixShader')
    b.link(a_, mx.inputs[0]); b.link(tr.outputs[0], mx.inputs[1]); b.link(em.outputs[0], mx.inputs[2])
    b.link(mx.outputs[0], b.out.inputs['Surface'])
    ci = C.prim('plane', 'cirrus', loc=(0, 0, 1500), scale=(16000, 16000, 1), coll=coll, smooth=False)
    ci.rotation_euler = (0, 0, 0.35)
    C.set_mat(ci, b.mat)
    ci.visible_shadow = False
    # a few tall eroded spires near the road for parallax during the launch (both directions)
    near2 = mat_mesa('mesa_spire', sun, 1400)
    for i, (x, y, R, H) in enumerate(((-38, -70, 4.5, 24), (52, -110, 6.0, 31), (-61, -160, 5.0, 19), (44, 90, 5.5, 27),
                                      (-49, 140, 4.0, 22), (66, 210, 7.0, 34))):
        butte(f'spire{i}', coll, (x, y, -0.5), R, H, 400 + i, near2, nseg=36, nz_=22, aspect=rng.uniform(0.7, 1.3),
              rot=rng.uniform(0, 3.1), tiers=True)


def _is_sunvec(v):
    return abs(abs(v[1]) - 0.995) < 0.02 and 0.02 < abs(v[2]) < 0.15


def flip_sun(frame, az_deg=180.0, extra=()):
    """Rotate every baked sun vector (world glow, aerial haze dot products, canyon haze) about Z by az_deg,
    switching at `frame` (CONSTANT keys) - hidden inside the whip pan's motion blur."""
    ca, sa = math.cos(math.radians(az_deg)), math.sin(math.radians(az_deg))
    trees = [m.node_tree for m in bpy.data.materials if m.node_tree] + [w.node_tree for w in bpy.data.worlds if w.node_tree]
    n_ = 0
    for nt in trees:
        for nd in nt.nodes:
            if nd.bl_idname != 'ShaderNodeVectorMath' or nd.operation != 'DOT_PRODUCT':
                continue
            sock = nd.inputs[1]
            if sock.is_linked:
                continue
            v = tuple(sock.default_value)
            if not _is_sunvec(v):
                continue
            sock.keyframe_insert('default_value', frame=frame - 1)
            sock.default_value = (v[0] * ca - v[1] * sa, v[0] * sa + v[1] * ca, v[2])
            sock.keyframe_insert('default_value', frame=frame)
            for fc in C.fcurves(nt):
                for kp in fc.keyframe_points:
                    kp.interpolation = 'CONSTANT'
            n_ += 1
    for o in extra:      # sun lamps
        o.keyframe_insert('rotation_euler', frame=frame - 1)
        o.rotation_euler = (Matrix.Rotation(math.radians(az_deg), 3, 'Z') @ o.rotation_euler.to_matrix()).to_euler()
        o.keyframe_insert('rotation_euler', frame=frame)
        C.set_interp(o, 'CONSTANT', path='rotation_euler')
    print('[sun] flipped %d sun vectors at f%d' % (n_, frame))
    return n_


def launch_dust(coll, car_root_fn, f0, f1, n=36, seed=4, color=(0.80, 0.58, 0.40), spawn=12):
    """r3: tyre smoke / sand rooster tails: a puff spawns EVERY frame at BOTH rear contact patches for `spawn`
    frames after launch, each grows 0.8 -> ~6 m, drifts back/out with +-2 m lateral spread, thins out;
    strongly forward-scattering (anisotropy 0.7) so the low sun backlights it."""
    rng = random.Random(seed)
    m = C.mat_volume('launch_dust', density=1.0, color=color, anisotropy=0.7, noise_scale=1.6, noise_contrast=(0.40, 0.78))
    out = []
    i = 0
    for k in range(spawn):
        for side in (-1, 1):
            if i >= n:
                break
            fs = f0 + k
            mi = m.copy() if i % 6 == 0 else mi
            if i % 6 == 0:
                mr = [n_ for n_ in mi.node_tree.nodes if n_.type == 'MAP_RANGE'][0]
                for f, d in ((fs - 1, 0.0), (fs, 1.6), (fs + 6, 0.9), (fs + 18, 0.35), (f1 + 10, 0.08)):
                    mr.inputs['To Max'].default_value = d; mr.inputs['To Max'].keyframe_insert('default_value', frame=f)
            base = car_root_fn(fs) + Vector((side * 0.86 + rng.uniform(-0.1, 0.1), -1.35 + rng.uniform(-0.15, 0.15), 0.18))
            o = C.prim('ico', f'dust_{i}', loc=base, coll=coll, r=0.5, sub=2)
            C.set_mat(o, mi)
            o.visible_shadow = False
            drift = Vector((side * rng.uniform(0.6, 2.0), rng.uniform(-2.5, -0.6), rng.uniform(0.25, 0.8)))
            s_end = rng.uniform(4.0, 6.5)
            for f, s_, dp in ((fs - 1, 0.0, 0.0), (fs, 0.8, 0.0), (fs + 4, 2.0, 0.35), (fs + 12, 3.8, 0.75), (f1 + 10, s_end, 1.4)):
                o.scale = (s_, s_ * 1.25, s_ * 0.6); o.keyframe_insert('scale', frame=f)
                o.location = base + drift * dp * 2.2 + Vector((0, 0, s_ * 0.18)); o.keyframe_insert('location', frame=f)
            out.append(o)
            i += 1
    return out

# ----------------------------------------------------------------------------- fx

_SPARK = {}


def spark_mat():
    """r3: hot-metal spark = thin capsule stretched along its velocity; white-yellow core (facing) -> orange rim
    (Layer Weight), multiplied by the per-spark cooling colour (object colour)."""
    if 'm' not in _SPARK:
        b = C.NB('spark')
        oi = b.n('ShaderNodeObjectInfo')
        lw = b.n('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.35
        core = b.mix((1.0, 0.33, 0.05), (1.0, 0.86, 0.55), b.math('POWER', b.math('SUBTRACT', 1.0, lw.outputs['Facing']), 2.0))
        col = b.mix(core, oi.outputs['Color'], 1.0, blend='MULTIPLY')
        b.set('Base Color', (0, 0, 0)).set('Emission Color', col).set('Emission Strength', 20.0)
        _SPARK['m'] = b.mat
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.5)
        for v in bm.verts:            # unit-length capsule along -X: head at 0, tail at -1, radius 0.5
            v.co.x = v.co.x - 0.5
        me = bpy.data.meshes.new('spark_me'); bm.to_mesh(me); bm.free()
        me.materials.append(b.mat)
        for p_ in me.polygons:
            p_.use_smooth = True
        _SPARK['me'] = me
    return _SPARK['m'], _SPARK['me']


def spark_burst(coll, origin, frame, n=40, seed=0, speed=(3.0, 9.0), up=0.6, spread=None, life=(3, 8), floor=0.0, g=9.8, size=1.0,
                bounce_frac=0.15, shutter=0.5, flat=None):
    """Ballistic keyframed sparks: capsules oriented + stretched along the velocity (length ~ |v|*shutter/fps),
    3-8 frame life, a few longer floor bouncers; colour cools white-yellow -> orange -> dull red.
    flat: optional normal of the contact plane - velocities are projected into it (sparks fly ALONG the seam)."""
    rng = random.Random(seed)
    _, me = spark_mat()
    objs = []
    for i in range(n):
        o = bpy.data.objects.new(f'spk_{seed}_{i}', me)
        C.link(o, coll)
        o.visible_shadow = False
        d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), abs(rng.gauss(0, 1)) * up + 0.15))
        if flat is not None:
            nn = Vector(flat).normalized()
            d = d - nn * d.dot(nn) * 0.85
        if spread is not None:
            d = (d.normalized() + Vector(spread)).normalized()
        v = d.normalized() * rng.uniform(*speed)
        bouncer = rng.random() < bounce_frac
        lf = 12 if bouncer else rng.randint(*life)
        p = Vector(origin)
        f0 = frame
        o.scale = (0, 0, 0); o.keyframe_insert('scale', frame=f0 - 1)
        dt = 1.0 / C.FPS
        th = rng.uniform(0.6, 1.3) * size * 0.0032
        for k in range(lf + 1):
            if k > 0:
                v.z -= g * dt
                v *= 0.97                                   # drag
                p = p + v * dt
                if p.z < floor:
                    p.z = floor + 0.002; v.z = -v.z * 0.35; v.x *= 0.6; v.y *= 0.6
            o.location = p
            o.keyframe_insert('location', frame=f0 + k)
            o.rotation_euler = v.normalized().to_track_quat('X', 'Z').to_euler() if v.length > 1e-4 else o.rotation_euler
            o.keyframe_insert('rotation_euler', frame=f0 + k)
            t_ = k / lf
            o.color = (1.0, 0.92 - 0.45 * t_, 0.62 - 0.6 * min(1.0, t_ * 1.6), 1.0) if t_ < 0.6 else (0.95 - 0.35 * t_, 0.45 - 0.33 * t_, 0.03, 1.0)
            o.keyframe_insert('color', frame=f0 + k)
            fade = 1.0 - (k / lf) ** 3
            ln = max(th * 2.5, v.length * shutter / C.FPS * 0.7)
            o.scale = (ln, th * fade, th * fade)
            o.keyframe_insert('scale', frame=f0 + k)
        o.scale = (0, 0, 0); o.keyframe_insert('scale', frame=f0 + lf + 1)
        C.set_interp(o, 'LINEAR')
        objs.append(o)
    return objs


def flash(coll, loc, frame, energy=4000.0, color=(1.0, 0.6, 0.3), radius=0.05, decay=3):
    L = C.light('POINT', f'flash_{frame}', loc, energy=0.0, color=color, shadow_soft=radius)
    d = L.data
    for f, e in ((frame - 1, 0.0), (frame, energy), (frame + 1, energy * 0.35), (frame + decay, 0.0)):
        d.energy = e
        d.keyframe_insert('energy', frame=f)
    return L


def impulse(o, frame, amp=0.04, seed=0, path='location', decay=(1.0, -0.6, 0.3, -0.1, 0.0)):
    """Additive camera-shake impulse via an extra parent empty keyed around `frame`."""
    rng = random.Random(seed)
    v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.5, 1))).normalized() * amp
    base = Vector(getattr(o, path))
    for k, a in enumerate(decay):
        setattr(o, path, base + v * a)
        o.keyframe_insert(path, frame=frame + k)
    setattr(o, path, base)
    o.keyframe_insert(path, frame=frame - 1)
