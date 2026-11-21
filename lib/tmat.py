"""Act IV materials, sky world and clouds."""
import bpy, math
from common import NB

PI = math.pi


def _sep(b, vec):
    s = b.n('ShaderNodeSeparateXYZ')
    b.link(vec, s.inputs[0])
    return s.outputs


def _comb(b, x, y, z):
    c = b.n('ShaderNodeCombineXYZ')
    for i, v in enumerate((x, y, z)):
        if isinstance(v, (int, float)):
            c.inputs[i].default_value = v
        else:
            b.link(v, c.inputs[i])
    return c.outputs[0]


def _ao(b, dist=0.4):
    ao = b.n('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = dist
    ao.samples = 8
    return ao.outputs['AO']


def m_gold(name='T_Gold', base=(1.0, 0.71, 0.3), dark=(0.5, 0.28, 0.07), rough=(0.1, 0.32), scale=1.0, ao=True, emit=0.0):
    b = NB(name)
    v = b.coord('Object', scale)
    n1 = b.noise(v, 1.5, 6, 0.6)
    n2 = b.noise(v, 30.0, 4, 0.6)
    n3 = b.noise(v, 6.0, 5, 0.6)
    col = b.mix(base, (0.96, 0.6, 0.2), b.maprange(n1.outputs['Fac'], 0.35, 0.75, 0.0, 0.7))
    if ao:
        a = _ao(b, 0.35)
        col = b.mix(dark, col, b.maprange(a, 0.15, 0.9, 0.0, 1.0))
    b.set('Base Color', col)
    b.set('Metallic', 1.0)
    b.set('Roughness', b.maprange(b.math('ADD', n2.outputs['Fac'], b.math('MULTIPLY', n3.outputs['Fac'], 0.6)), 0.6, 1.3, rough[0], rough[1]))
    b.set('Normal', b.bump(n2.outputs['Fac'], 0.05, 0.004))
    if emit:
        b.set('Emission Color', base).set('Emission Strength', emit)
    return b.mat


def m_marble(name='T_Marble', base=(0.86, 0.84, 0.8), joints=True, jw=1.6, jh=0.55, ao=True):
    b = NB(name)
    v = b.coord('Object', 1.0)
    n = b.noise(v, 0.35, 8, 0.62, dist=4.0)
    vein = b.ramp(n.outputs['Fac'], [(0.47, (1, 1, 1, 1)), (0.5, (0.62, 0.62, 0.66, 1)), (0.53, (1, 1, 1, 1))])
    n2 = b.noise(v, 2.5, 6, 0.6)
    col = b.mix(base, tuple(c * 0.86 for c in base), n2.outputs['Fac'])
    col = b.mix(col, vein.outputs[0], 1.0, 'MULTIPLY')
    rough = b.maprange(n2.outputs['Fac'], 0.3, 0.7, 0.22, 0.42)
    height = None
    if joints:
        s = _sep(b, v)
        vec = _comb(b, b.math('ADD', s[0], s[1]), s[2], 0.0)
        br = b.n('ShaderNodeTexBrick')
        br.inputs['Scale'].default_value = 1.0
        br.inputs['Mortar Size'].default_value = 0.012
        br.inputs['Mortar Smooth'].default_value = 0.3
        br.inputs['Brick Width'].default_value = jw
        br.inputs['Row Height'].default_value = jh
        br.inputs['Color1'].default_value = (1, 1, 1, 1)
        br.inputs['Color2'].default_value = (0.92, 0.92, 0.92, 1)
        b.link(vec, br.inputs['Vector'])
        fac = br.outputs['Fac']
        col = b.mix(b.mix(col, br.outputs['Color'], 1.0, 'MULTIPLY'), (0.35, 0.33, 0.3), fac)
        height = b.math('SUBTRACT', 1.0, fac)
    if ao:
        a = _ao(b, 0.5)
        col = b.mix(tuple(c * 0.45 for c in base), col, b.maprange(a, 0.1, 0.9, 0.0, 1.0))
    b.set('Base Color', col)
    b.set('Roughness', rough)
    try:
        b.set('Subsurface Weight', 0.08)
        b.set('Subsurface Radius', (0.4, 0.3, 0.2))
    except Exception:
        pass
    hb = b.math('ADD', b.math('MULTIPLY', n2.outputs['Fac'], 0.3), height if height is not None else 0.0)
    b.set('Normal', b.bump(hb, 0.25, 0.01))
    return b.mat


def m_enamel(name='T_Enamel', base=(0.0, 0.085, 0.1), alt=(0.005, 0.05, 0.085), rough=0.14):
    """Deep teal cloisonne enamel for pediment fields / globe: glossy, slightly mottled."""
    b = NB(name)
    v = b.coord('Object', 1.0)
    n1 = b.noise(v, 2.0, 6, 0.6)
    n2 = b.noise(v, 45.0, 3, 0.6)
    col = b.mix(base, alt, b.maprange(n1.outputs['Fac'], 0.35, 0.7, 0, 1))
    a = _ao(b, 0.3)
    col = b.mix((0.0, 0.01, 0.012), col, b.maprange(a, 0.1, 0.9, 0.0, 1.0))
    b.set('Base Color', col)
    b.set('Roughness', b.maprange(n2.outputs['Fac'], 0.3, 0.7, rough * 0.6, rough * 1.6))
    b.set('Coat Weight', 1.0)
    b.set('Coat Roughness', 0.05)
    b.set('Normal', b.bump(n2.outputs['Fac'], 0.05, 0.003))
    return b.mat


def m_lacquer(name='T_Verm', base=(0.36, 0.028, 0.006), rough=0.32, ao=True):
    b = NB(name)
    v = b.coord('Object', 1.0)
    n1 = b.noise(v, 3.0, 6, 0.6)
    n2 = b.noise(v, 40.0, 3, 0.6)
    col = b.mix(base, tuple(c * 0.6 for c in base), b.maprange(n1.outputs['Fac'], 0.35, 0.75, 0, 0.8))
    if ao:
        a = _ao(b, 0.3)
        col = b.mix(tuple(c * 0.25 for c in base), col, b.maprange(a, 0.1, 0.9, 0.0, 1.0))
    b.set('Base Color', col)
    b.set('Roughness', b.maprange(n2.outputs['Fac'], 0.3, 0.7, rough * 0.7, rough * 1.4))
    b.set('Coat Weight', 0.45)
    b.set('Coat Roughness', 0.12)
    b.set('Normal', b.bump(n2.outputs['Fac'], 0.04, 0.003))
    return b.mat


def m_tiles(name='T_Tiles', base=(0.0, 0.42, 0.40), alt=(0.01, 0.30, 0.36), tw=0.42, tl=0.5, var=0.35, ao=True,
            hi=(0.05, 0.62, 0.55)):
    """Glazed barrel tiles from UV (u across slope, v up slope, meters)."""
    b = NB(name)
    uv = b.coord('UV')
    s = _sep(b, uv)
    U = b.math('DIVIDE', s[0], tw)
    V = b.math('DIVIDE', s[1], tl)
    row = b.math('FLOOR', V)
    off = b.math('MULTIPLY', b.math('FLOORED_MODULO', row, 2.0), 0.5)
    U2 = b.math('ADD', U, off)
    col_i = b.math('FLOOR', U2)
    fu = b.math('FRACT', U2)
    fv = b.math('FRACT', V)
    barrel = b.math('POWER', b.math('SINE', b.math('MULTIPLY', fu, PI)), 0.6)
    lip = b.math('SUBTRACT', 1.0, b.math('MULTIPLY', fv, 0.55))
    gap = b.maprange(fv, 0.0, 0.07, 0.25, 1.0)
    h = b.math('MULTIPLY', b.math('MULTIPLY', barrel, lip), gap)
    wn = b.n('ShaderNodeTexWhiteNoise')
    wn.noise_dimensions = '3D'
    b.link(_comb(b, col_i, row, 0.0), wn.inputs['Vector'])
    rid = wn.outputs['Value']
    c = b.mix(base, alt, b.math('POWER', rid, 1.5))
    c = b.mix(c, hi, b.maprange(rid, 0.9, 1.0, 0.0, 0.8))
    # glaze pooling: lighter on crowns, dark in channels
    shade = b.maprange(h, 0.0, 1.0, 0.25, 1.15)
    c = b.mix(c, _comb(b, shade, shade, shade), 1.0, 'MULTIPLY')
    if ao:
        a = _ao(b, 0.6)
        c = b.mix((0.0, 0.03, 0.03), c, b.maprange(a, 0.05, 0.9, 0.0, 1.0))
    b.set('Base Color', c)
    nz = b.noise(b.coord('Object', 1.0), 12.0, 4, 0.6)
    b.set('Roughness', b.maprange(b.math('ADD', nz.outputs['Fac'], b.math('MULTIPLY', rid, 0.5)), 0.4, 1.3, 0.05, 0.3))
    b.set('Coat Weight', 1.0)
    b.set('Coat Roughness', 0.04)
    b.set('Normal', b.bump(h, 0.9, 0.06))
    return b.mat


def m_glazed(name='T_Glaze', base=(0.0, 0.4, 0.38), rough=0.12):
    """Glazed ceramic for real tile geometry: per-object color variation via Random."""
    b = NB(name)
    oi = b.n('ShaderNodeObjectInfo')
    v = b.coord('Object', 1.0)
    n1 = b.noise(v, 8.0, 5, 0.6)
    col = b.mix(base, (0.02, 0.3, 0.36), b.maprange(n1.outputs['Fac'], 0.35, 0.7, 0, 1))
    b.set('Base Color', col)
    b.set('Roughness', rough)
    b.set('Coat Weight', 1.0)
    b.set('Coat Roughness', 0.03)
    b.set('Normal', b.bump(n1.outputs['Fac'], 0.05, 0.002))
    return b.mat


def m_attr_tiles(name='T_TileAttr', base=(0.0, 0.42, 0.40), alt=(0.01, 0.28, 0.36), hi=(0.08, 0.6, 0.52)):
    """Real tile geometry: random per tile from UV.x (tile id stored in uv.x integer part)."""
    b = NB(name)
    uv = b.coord('UV')
    s = _sep(b, uv)
    wn = b.n('ShaderNodeTexWhiteNoise')
    wn.noise_dimensions = '1D'
    b.link(b.math('FLOOR', s[0]), wn.inputs['W'])
    rid = wn.outputs['Value']
    c = b.mix(base, alt, rid)
    c = b.mix(c, hi, b.maprange(rid, 0.88, 1.0, 0.0, 0.9))
    c = b.mix(c, (0.004, 0.12, 0.13), b.maprange(rid, 0.0, 0.1, 0.8, 0.0))     # a few deep, dark tiles
    # border tiles (uv.y offset by 10 in the generator) are vermilion-orange glaze, like the ref's roof edges
    red = b.mix((0.52, 0.07, 0.015), (0.62, 0.16, 0.02), rid)
    c = b.mix(c, red, b.math('GREATER_THAN', s[1], 5.0))
    a = _ao(b, 0.15)          # r1: cavity term - near-black line between pan and cover rows
    c = b.mix((0.0, 0.008, 0.01), c, b.maprange(a, 0.2, 0.95, 0.0, 1.0))
    v = b.coord('Object', 1.0)
    n1 = b.noise(v, 30.0, 4, 0.6)
    b.set('Base Color', c)
    b.set('Roughness', b.maprange(b.math('ADD', n1.outputs['Fac'], b.math('MULTIPLY', rid, 0.4)), 0.3, 1.1, 0.16, 0.38))
    b.set('Coat Weight', 0.6)
    b.set('Coat Roughness', b.maprange(rid, 0.0, 1.0, 0.1, 0.22))
    b.set('Normal', b.bump(n1.outputs['Fac'], 0.06, 0.001))
    return b.mat


def m_wood(name='T_Wood', base=(0.16, 0.035, 0.02)):
    b = NB(name)
    v = b.coord('Object', (1, 1, 1))
    n = b.noise(v, 3.0, 6, 0.6)
    b.set('Base Color', b.mix(base, tuple(c * 0.5 for c in base), n.outputs['Fac']))
    b.set('Roughness', 0.55)
    return b.mat


def m_water(name='T_Water'):
    b = NB(name)
    v = b.coord('Object', 1.0)
    n = b.noise(v, 0.8, 4, 0.5)
    n2 = b.noise(v, 6.0, 3, 0.5)
    b.set('Base Color', (0.004, 0.018, 0.022))
    b.set('Roughness', 0.006)
    b.set('IOR', 1.8)
    b.set('Specular IOR Level', 0.9)
    b.set('Normal', b.bump(b.math('ADD', n.outputs['Fac'], b.math('MULTIPLY', n2.outputs['Fac'], 0.3)), 0.012, 0.02))
    return b.mat


def m_foliage(name='T_Leaf', base=(0.05, 0.16, 0.03), dark=(0.012, 0.05, 0.012), scale=1.0, tip=(0.22, 0.32, 0.06)):
    b = NB(name)
    v = b.coord('Object', scale)
    vo = b.voronoi(v, 9.0)
    n = b.noise(v, 1.2, 6, 0.6)
    n2 = b.noise(v, 18.0, 4, 0.7)
    c = b.mix(dark, base, b.maprange(n.outputs['Fac'], 0.3, 0.7, 0, 1))
    c = b.mix(c, tip, b.maprange(n2.outputs['Fac'], 0.62, 0.8, 0, 0.6))
    a = _ao(b, 1.0)
    c = b.mix(tuple(x * 0.25 for x in dark), c, b.maprange(a, 0.0, 0.9, 0.0, 1.0))
    b.set('Base Color', c)
    b.set('Roughness', 0.62)
    try:
        b.set('Subsurface Weight', 0.25)
        b.set('Subsurface Radius', (0.2, 0.4, 0.1))
    except Exception:
        pass
    b.set('Normal', b.bump(b.math('ADD', vo.outputs['Distance'], n2.outputs['Fac']), 0.9, 0.12))
    return b.mat


def m_grass(name='T_Grass'):
    b = NB(name)
    v = b.coord('Object', 1.0)
    n = b.noise(v, 0.08, 6, 0.6)
    n2 = b.noise(v, 2.0, 6, 0.6)
    n3 = b.noise(v, 120.0, 3, 0.6)
    c = b.mix((0.05, 0.14, 0.02), (0.14, 0.24, 0.035), b.maprange(n.outputs['Fac'], 0.35, 0.65, 0, 1))
    c = b.mix(c, (0.03, 0.08, 0.015), b.maprange(n2.outputs['Fac'], 0.5, 0.75, 0, 0.6))
    # mowing stripes along axis
    s = _sep(b, v)
    stripe = b.math('GREATER_THAN', b.math('SINE', b.math('MULTIPLY', s[0], 0.9)), 0.0)
    c = b.mix(c, (0.09, 0.2, 0.03), b.math('MULTIPLY', stripe, 0.35))
    b.set('Base Color', c)
    b.set('Roughness', 0.8)
    b.set('Normal', b.bump(n3.outputs['Fac'], 0.4, 0.01))
    return b.mat


def m_terrain(name='T_Terrain'):
    """Grass on flats, layered warm rock on cliffs (by normal Z)."""
    b = NB(name)
    v = b.coord('Object', 1.0)
    geo = b.n('ShaderNodeNewGeometry')
    nz = _sep(b, geo.outputs['Normal'])[2]
    s = _sep(b, v)
    strata = b.noise(_comb(b, b.math('MULTIPLY', s[0], 0.02), b.math('MULTIPLY', s[1], 0.02), b.math('MULTIPLY', s[2], 0.6)), 1.0, 6, 0.6, dist=1.5)
    n1 = b.noise(v, 0.05, 8, 0.6)
    n2 = b.noise(v, 0.6, 8, 0.65)
    rock = b.ramp(strata.outputs['Fac'], [(0.3, (0.16, 0.12, 0.09)), (0.5, (0.42, 0.34, 0.26)), (0.7, (0.6, 0.5, 0.4))])
    rockc = b.mix(rock.outputs[0], (0.1, 0.08, 0.07), b.maprange(n2.outputs['Fac'], 0.5, 0.75, 0, 0.7))
    grass = b.mix((0.06, 0.15, 0.025), (0.16, 0.25, 0.05), n1.outputs['Fac'])
    # r4: meadow variation readable from the 4B altitude (was a flat uniform green): dry ochre drifts + dark clover
    nb1 = b.noise(v, 0.011, 5, 0.6)
    nb2 = b.noise(_comb(b, b.math('ADD', s[0], 300.0), s[1], s[2]), 0.017, 5, 0.6)
    grass = b.mix(grass, (0.2, 0.19, 0.055), b.maprange(nb1.outputs['Fac'], 0.56, 0.7, 0.0, 0.65))
    grass = b.mix(grass, (0.022, 0.065, 0.016), b.maprange(nb2.outputs['Fac'], 0.55, 0.68, 0.0, 0.55))
    m = b.maprange(b.math('ADD', nz, b.math('MULTIPLY', n2.outputs['Fac'], 0.3)), 0.82, 0.92, 0, 1)
    b.set('Base Color', b.mix(rockc, grass, m))
    b.set('Roughness', 0.85)
    b.set('Normal', b.bump(b.math('ADD', strata.outputs['Fac'], n2.outputs['Fac']), 0.8, 1.2))
    return b.mat


def m_paving(name='T_Paving', base=(0.78, 0.76, 0.72), size=1.2):
    b = NB(name)
    v = b.coord('Object', 1.0)
    br = b.n('ShaderNodeTexBrick')
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Mortar Size'].default_value = 0.01
    br.inputs['Brick Width'].default_value = size
    br.inputs['Row Height'].default_value = size * 0.5
    br.inputs['Color1'].default_value = (*base, 1)
    br.inputs['Color2'].default_value = (*[c * 0.85 for c in base], 1)
    br.inputs['Mortar'].default_value = (0.2, 0.19, 0.17, 1)
    b.link(v, br.inputs['Vector'])
    n = b.noise(v, 1.5, 6, 0.6)
    c = b.mix(br.outputs['Color'], (0.45, 0.42, 0.38), b.maprange(n.outputs['Fac'], 0.5, 0.8, 0, 0.5))
    b.set('Base Color', c)
    b.set('Roughness', b.maprange(n.outputs['Fac'], 0.3, 0.7, 0.18, 0.45))
    b.set('Normal', b.bump(b.math('SUBTRACT', 1.0, br.outputs['Fac']), 0.3, 0.01))
    return b.mat


def m_emit_glass(name='T_LampGlass', color=(1.0, 0.42, 0.12), strength=0.7):
    b = NB(name)
    v = b.coord('Object', 1.0)
    n = b.noise(v, 20.0, 3, 0.5)
    b.set('Base Color', color).set('Roughness', 0.2)
    b.set('Emission Color', color)
    b.set('Emission Strength', b.maprange(n.outputs['Fac'], 0.3, 0.7, strength * 0.7, strength * 1.2))
    return b.mat


def m_dark(name='T_Dark', color=(0.02, 0.012, 0.008), rough=0.6):
    b = NB(name)
    b.set('Base Color', color).set('Roughness', rough)
    return b.mat


def m_bronze(name='T_Bronze'):
    b = NB(name)
    v = b.coord('Object', 1.0)
    n1 = b.noise(v, 2.0, 8, 0.6)
    n2 = b.noise(v, 25.0, 5, 0.65)
    pat = b.maprange(n1.outputs['Fac'], 0.55, 0.7, 0.0, 1.0)
    c = b.mix((0.45, 0.25, 0.1), (0.08, 0.32, 0.26), pat)
    a = _ao(b, 0.3)
    c = b.mix((0.05, 0.03, 0.02), c, b.maprange(a, 0.1, 0.9, 0, 1))
    b.set('Base Color', c)
    b.set('Metallic', b.math('SUBTRACT', 1.0, pat))
    b.set('Roughness', b.maprange(n2.outputs['Fac'], 0.3, 0.7, 0.2, 0.55))
    b.set('Normal', b.bump(n2.outputs['Fac'], 0.1, 0.004))
    return b.mat


# ----------------------------------------------------------------------------- clouds

def m_cloud_surface(name='T_CloudSurf', lit=(1.0, 0.9, 0.78), shadow=(0.42, 0.5, 0.66), haze=(0.62, 0.72, 0.86),
                    haze_r=(800.0, 2600.0), emit=0.35, scale=1.0, center=(0, 0)):
    """Opaque-ish billowy cloud surface: diffuse + translucency, cauliflower bump,
    blue ambient emission in shadows, fades to horizon haze color with distance."""
    b = NB(name)
    v = b.coord('Object', scale)
    n1 = b.noise(v, 0.025, 6, 0.62)
    n2 = b.noise(v, 0.12, 6, 0.65)
    n3 = b.noise(v, 0.6, 4, 0.6)
    h = b.math('ADD', b.math('ADD', n1.outputs['Fac'], b.math('MULTIPLY', n2.outputs['Fac'], 0.5)), b.math('MULTIPLY', n3.outputs['Fac'], 0.25))
    s = _sep(b, v)
    dist = b.math('SQRT', b.math('ADD', b.math('POWER', b.math('SUBTRACT', s[0], center[0]), 2.0), b.math('POWER', b.math('SUBTRACT', s[1], center[1]), 2.0)))
    hz = b.maprange(dist, haze_r[0], haze_r[1], 0.0, 1.0)
    base = b.mix(lit, haze, b.math('MULTIPLY', hz, 0.6))
    diff = b.n('ShaderNodeBsdfDiffuse')
    b.link(base, diff.inputs['Color'])
    diff.inputs['Roughness'].default_value = 1.0
    nb = b.bump(h, 1.0, 6.0)
    b.link(nb, diff.inputs['Normal'])
    tr = b.n('ShaderNodeBsdfTranslucent')
    b.link(base, tr.inputs['Color'])
    em = b.n('ShaderNodeEmission')
    b.link(b.mix(shadow, haze, hz), em.inputs['Color'])
    em.inputs['Strength'].default_value = emit
    mx = b.n('ShaderNodeMixShader')
    mx.inputs['Fac'].default_value = 0.15
    b.link(diff.outputs[0], mx.inputs[1])
    b.link(tr.outputs[0], mx.inputs[2])
    ad = b.n('ShaderNodeAddShader')
    b.link(mx.outputs[0], ad.inputs[0])
    b.link(em.outputs[0], ad.inputs[1])
    b.link(ad.outputs[0], b.out.inputs['Surface'])
    return b.mat


def m_cloud_volume(name='T_CloudVol', density=0.08, color=(1.0, 0.97, 0.93), scale=3.0, contrast=(0.42, 0.62),
                   aniso=0.45, falloff=True, emit=(1.0, 0.86, 0.7), emit_s=0.0, detail=3.0):
    """Cumulus-ish volume: noise thresholded by a radial falloff in object space (cube of size 1)."""
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    N, L = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputMaterial')
    vp = N.new('ShaderNodeVolumePrincipled')
    vp.inputs['Color'].default_value = (*color, 1)
    vp.inputs['Anisotropy'].default_value = aniso
    if emit_s:
        vp.inputs['Emission Color'].default_value = (*emit, 1)
        vp.inputs['Emission Strength'].default_value = emit_s
    tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 1.0
    nz.inputs['Detail'].default_value = detail
    nz.inputs['Roughness'].default_value = 0.6
    nz.inputs['Distortion'].default_value = 0.4
    L.new(mp.outputs['Vector'], nz.inputs['Vector'])
    fac = nz.outputs['Fac']
    if falloff:
        ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'
        L.new(tc.outputs['Object'], ln.inputs[0])
        fm = N.new('ShaderNodeMath'); fm.operation = 'MULTIPLY'; fm.inputs[1].default_value = 0.45
        L.new(ln.outputs['Value'], fm.inputs[0])
        sub = N.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'
        L.new(fac, sub.inputs[0]); L.new(fm.outputs[0], sub.inputs[1])
        fac = sub.outputs[0]
    mr = N.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = contrast[0]
    mr.inputs['From Max'].default_value = contrast[1]
    mr.inputs['To Min'].default_value = 0.0
    mr.inputs['To Max'].default_value = density
    L.new(fac, mr.inputs['Value'])
    L.new(mr.outputs['Result'], vp.inputs['Density'])
    L.new(vp.outputs['Volume'], out.inputs['Volume'])
    return m


def m_cloud_vol2(name='T_CloudV2', density=0.5, color=(1.0, 0.97, 0.93), scale=2.5, detail=4.0, aniso=0.5,
                 emit=(1.0, 0.9, 0.78), emit_s=0.0, shape_k=1.8, noise_k=1.4, thr=0.45, stretch=(1.0, 1.0, 1.0), seed=0.0):
    """Cloud volume for a unit cube object (+-0.5): ellipsoid falloff (zero before the box faces, so no
    rectangles), billowy noise, emission multiplied by the density field (EEVEE's Principled Volume emission
    is NOT density-weighted - an emissive box glows uniformly otherwise)."""
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
    vp.inputs['Color'].default_value = (*color, 1)
    vp.inputs['Anisotropy'].default_value = aniso
    tc = N.new('ShaderNodeTexCoord')
    q = N.new('ShaderNodeVectorMath'); q.operation = 'MULTIPLY'; q.inputs[1].default_value = (2.0, 2.0, 2.0)
    L.new(tc.outputs['Object'], q.inputs[0])
    ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'
    L.new(q.outputs[0], ln.inputs[0])
    shape = M('SUBTRACT', 1.0, ln.outputs['Value'], clamp=True)
    mp = N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale * stretch[0], scale * stretch[1], scale * stretch[2])
    mp.inputs['Location'].default_value = (seed, seed * 0.37, seed * 0.71)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 1.0
    nz.inputs['Detail'].default_value = detail
    nz.inputs['Roughness'].default_value = 0.62
    nz.inputs['Distortion'].default_value = 0.3
    L.new(mp.outputs['Vector'], nz.inputs['Vector'])
    f = M('ADD', M('MULTIPLY', shape, shape_k), M('MULTIPLY', M('SUBTRACT', nz.outputs['Fac'], 0.5), noise_k))
    f = M('SUBTRACT', f, thr)
    f01 = M('MULTIPLY', f, 2.0, clamp=True)
    L.new(M('MULTIPLY', f01, density), vp.inputs['Density'])
    if emit_s:
        vp.inputs['Emission Color'].default_value = (*emit, 1)
        L.new(M('MULTIPLY', f01, emit_s), vp.inputs['Emission Strength'])
    L.new(vp.outputs['Volume'], out.inputs['Volume'])
    return m


def m_cloud_surface2(name='T_CloudS2', sun_dir=(0, -1, 0.25), lit=(1.0, 0.82, 0.6), shadow=(0.3, 0.36, 0.55),
                     haze_cool=(0.55, 0.66, 0.85), haze_warm=(1.0, 0.75, 0.5), fog_d=2500.0, emit=0.12, soft=True,
                     bump=1.0, rim=1.6, scale=1.0, fog_max=0.85, wrap=0.0, wrap_col=(1.0, 0.78, 0.55), base_dark=None):
    """Mesh cloud: bumped diffuse + translucency, blue sky-fill emission in shadow, forward-scatter rim glow
    toward the sun, distance haze from the camera (warm toward the sun), soft see-through silhouettes."""
    b = NB(name)
    N, L = b.N, b.L
    v = b.coord('Object', scale)
    n1 = b.noise(v, 0.02, 6, 0.62)
    n2 = b.noise(v, 0.09, 6, 0.65)
    n3 = b.noise(v, 0.45, 4, 0.6)
    h = b.math('ADD', b.math('ADD', n1.outputs['Fac'], b.math('MULTIPLY', n2.outputs['Fac'], 0.45)), b.math('MULTIPLY', n3.outputs['Fac'], 0.06))
    geo = b.n('ShaderNodeNewGeometry')
    sd = b.n('ShaderNodeVectorMath'); sd.operation = 'DOT_PRODUCT'; sd.name = 'CloudSunDot'
    sd.inputs[1].default_value = tuple(-x for x in sun_dir)     # Incoming points to the camera
    b.link(geo.outputs['Incoming'], sd.inputs[0])
    tow = b.math('MAXIMUM', sd.outputs['Value'], 0.0)       # 1 when looking straight at the sun
    cam = b.n('ShaderNodeCameraData')
    fog = b.math('MULTIPLY', b.math('SUBTRACT', 1.0, b.math('EXPONENT', b.math('DIVIDE', cam.outputs['View Distance'], -fog_d))), fog_max)
    hazec = b.mix(haze_cool, haze_warm, b.math('POWER', tow, 3.0))
    diff = b.n('ShaderNodeBsdfDiffuse')
    diff.inputs['Color'].default_value = (*lit, 1)
    dk = None
    if base_dark is not None:
        # flat dark bases: the lowest part of every cloud (object z in [zlo, zhi]) is darker/greyer (self-shadowed)
        k_, zlo, zhi = base_dark
        dk = b.math('POWER', b.maprange(_sep(b, b.coord('Object', 1.0))[2], zlo, zhi, k_, 1.0), 1.0)
        b.link(b.mix(_comb(b, dk, dk, dk), lit, 0.0, 'MIX') if False else b.mix((lit[0] * k_, lit[1] * k_, lit[2] * k_ * 1.15), lit,
                                                                                   b.maprange(dk, k_, 1.0, 0.0, 1.0)), diff.inputs['Color'])
    b.link(b.bump(h, bump, 5.0), diff.inputs['Normal'])
    tr = b.n('ShaderNodeBsdfTranslucent')
    tr.inputs['Color'].default_value = (*lit, 1)
    mx = b.n('ShaderNodeMixShader'); mx.inputs['Fac'].default_value = 0.0   # EEVEE screen-traces translucency -> mirrored ghost of the island in the sea
    b.link(diff.outputs[0], mx.inputs[1]); b.link(tr.outputs[0], mx.inputs[2])
    lw = b.n('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
    facing = lw.outputs['Facing']
    # sky-fill + forward-scatter silver lining at grazing edges when looking toward the sun
    em = b.n('ShaderNodeEmission')
    emc = b.mix(shadow, (1.6 * lit[0], 1.3 * lit[1], 0.9 * lit[2]), b.math('MULTIPLY', b.math('POWER', tow, 6.0), facing))
    b.link(emc, em.inputs['Color'])
    b.link(b.math('ADD', emit, b.math('MULTIPLY', b.math('MULTIPLY', b.math('POWER', tow, 6.0), facing), rim)), em.inputs['Strength'])
    ad = b.n('ShaderNodeAddShader')
    b.link(mx.outputs[0], ad.inputs[0]); b.link(em.outputs[0], ad.inputs[1])
    if wrap > 0:
        # multiple-scattering fake: clouds stay bright even where the low sun grazes -> wrapped N.L glow, sun-tinted
        sn = b.n('ShaderNodeVectorMath'); sn.operation = 'DOT_PRODUCT'; sn.name = 'CloudSunN'
        sn.inputs[1].default_value = tuple(sun_dir)
        b.link(geo.outputs['Normal'], sn.inputs[0])
        wr = b.math('POWER', b.maprange(sn.outputs['Value'], -0.35, 1.0, 0.0, 1.0), 1.5)
        ew = b.n('ShaderNodeEmission'); ew.inputs['Color'].default_value = (*wrap_col, 1)
        wstr = b.math('MULTIPLY', wr, wrap)
        if dk is not None:
            wstr = b.math('MULTIPLY', wstr, dk)
        b.link(wstr, ew.inputs['Strength'])
        ad2 = b.n('ShaderNodeAddShader')
        b.link(ad.outputs[0], ad2.inputs[0]); b.link(ew.outputs[0], ad2.inputs[1])
        ad = ad2
    # distance haze (aerial perspective)
    hz = b.n('ShaderNodeEmission'); b.link(hazec, hz.inputs['Color']); hz.inputs['Strength'].default_value = 1.0
    mf = b.n('ShaderNodeMixShader'); b.link(fog, mf.inputs['Fac'])
    b.link(ad.outputs[0], mf.inputs[1]); b.link(hz.outputs[0], mf.inputs[2])
    final = mf.outputs[0]
    if soft:
        tp = b.n('ShaderNodeBsdfTransparent')
        ms = b.n('ShaderNodeMixShader')
        b.link(b.maprange(facing, 0.62, 0.96, 0.0, 1.0), ms.inputs['Fac'])     # r1: only the very rim frays (fractal bulges punched holes)
        b.link(final, ms.inputs[1]); b.link(tp.outputs[0], ms.inputs[2])
        final = ms.outputs[0]
        try:
            b.mat.surface_render_method = 'DITHERED'
        except Exception:
            pass
    b.link(final, b.out.inputs['Surface'])
    return b.mat


# ----------------------------------------------------------------------------- world

def world_sky_clouds(sun_elev=15.0, sun_az=0.0, strength=0.3, cloud_cover=0.55, cloud_scale=1.6, fog=None,
                     sky_rot_offset=0.0, sun_dir=(0, -1, 0.3), altitude=600.0, haze=0.0, gradient=None,
                     cloud_gain=6.0):
    """Physical sky + procedural cumulus layer projected on a plane, lit from the sun azimuth."""
    w = bpy.data.worlds.new('SkyT')
    bpy.context.scene.world = w
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    N, L = nt.nodes, nt.links
    out = N.new('ShaderNodeOutputWorld')
    bg = N.new('ShaderNodeBackground')
    sky = N.new('ShaderNodeTexSky')
    for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING', 'HOSEK_WILKIE'):
        try:
            sky.sky_type = t
            break
        except Exception:
            continue
    for attr, val in (('sun_elevation', math.radians(sun_elev)), ('sun_rotation', math.radians(sun_az + sky_rot_offset)),
                      ('altitude', altitude), ('air_density', 1.0), ('dust_density', 0.6), ('aerosol_density', 0.6),
                      ('ozone_density', 1.2), ('sun_disc', False), ('sun_intensity', 1.0)):
        try:
            setattr(sky, attr, val)
        except Exception:
            pass

    def M(op, a, b_=None, clamp=False):
        m = N.new('ShaderNodeMath'); m.operation = op; m.use_clamp = clamp
        for i, x in enumerate((a, b_)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                m.inputs[i].default_value = x
            else:
                L.new(x, m.inputs[i])
        return m.outputs[0]

    def MR(x, a0, a1, b0, b1):
        m = N.new('ShaderNodeMapRange'); m.clamp = True
        m.inputs['From Min'].default_value = a0; m.inputs['From Max'].default_value = a1
        m.inputs['To Min'].default_value = b0; m.inputs['To Max'].default_value = b1
        L.new(x, m.inputs['Value'])
        return m.outputs['Result']

    def MIX(a, b_, f):
        m = N.new('ShaderNodeMix'); m.data_type = 'RGBA'
        if isinstance(f, (int, float)):
            m.inputs['Factor'].default_value = f
        else:
            L.new(f, m.inputs['Factor'])
        for idx, v in ((6, a), (7, b_)):
            if isinstance(v, (tuple, list)):
                m.inputs[idx].default_value = (*v, 1)
            else:
                L.new(v, m.inputs[idx])
        return m.outputs[2]

    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ')
    L.new(tc.outputs['Generated'], sep.inputs[0])
    dz = M('MAXIMUM', sep.outputs[2], 0.03)
    px = M('DIVIDE', sep.outputs[0], dz)
    py = M('DIVIDE', sep.outputs[1], dz)
    comb = N.new('ShaderNodeCombineXYZ')
    L.new(px, comb.inputs[0]); L.new(py, comb.inputs[1])
    comb2 = N.new('ShaderNodeCombineXYZ')  # offset toward sun for fake lighting
    sx, sy = sun_dir[0], sun_dir[1]
    nrm = math.hypot(sx, sy) or 1.0
    ox_ = M('ADD', px, 0.06 * sx / nrm); oy_ = M('ADD', py, 0.06 * sy / nrm)
    ox_.node.name = 'SunOffX'; oy_.node.name = 'SunOffY'
    L.new(ox_, comb2.inputs[0]); L.new(oy_, comb2.inputs[1])

    def cnoise(vec, sc):
        nz = N.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = sc
        nz.inputs['Detail'].default_value = 10
        nz.inputs['Roughness'].default_value = 0.62
        nz.inputs['Distortion'].default_value = 0.25
        L.new(vec, nz.inputs['Vector'])
        return nz.outputs['Fac']
    n0 = cnoise(comb.outputs[0], cloud_scale)
    n1 = cnoise(comb2.outputs[0], cloud_scale)
    thr = 0.66 - cloud_cover * 0.2
    mask = MR(n0, thr, thr + 0.12, 0.0, 1.0)
    mask.node.name = 'CloudMask'
    # thin near horizon gets denser (perspective), fade out right at horizon and below
    hfade = MR(sep.outputs[2], 0.0, 0.06, 0.0, 1.0)
    mask = M('MULTIPLY', mask, hfade)
    lit = MR(M('SUBTRACT', n0, n1), -0.03, 0.05, 0.0, 1.0)
    ccol = MIX((0.42, 0.48, 0.6), (1.6, 1.25, 0.9), lit)
    # thicker parts darker underside
    ccol = MIX(ccol, (0.3, 0.33, 0.42), MR(n0, thr + 0.12, thr + 0.3, 0.0, 0.35))
    skyc = sky.outputs['Color']
    if gradient:
        # art-directed sky: deep zenith blue -> pale warm horizon + sun glow (values pre-strength)
        zen, hor, glow = gradient
        zf = MR(sep.outputs[2], -0.05, 0.6, 0.0, 1.0)
        zf = M('POWER', zf, 0.55)
        g = MIX(hor, zen, zf)
        dp = N.new('ShaderNodeVectorMath'); dp.operation = 'DOT_PRODUCT'; dp.name = 'SunDot'
        L.new(tc.outputs['Generated'], dp.inputs[0]); dp.inputs[1].default_value = tuple(sun_dir)
        sg = M('POWER', M('MAXIMUM', dp.outputs['Value'], 0.0), 4.0)
        sg2 = M('POWER', M('MAXIMUM', dp.outputs['Value'], 0.0), 200.0)
        add = N.new('ShaderNodeMix'); add.data_type = 'RGBA'; add.blend_type = 'ADD'
        sg3 = M('POWER', M('MAXIMUM', dp.outputs['Value'], 0.0), 4000.0)
        gw = M('MULTIPLY', sg, 0.6)
        gw.node.name = 'GlowWide'
        L.new(M('ADD', M('ADD', gw, M('MULTIPLY', sg2, 6.0)), M('MULTIPLY', sg3, 80.0)), add.inputs['Factor'])
        L.new(g, add.inputs[6]); add.inputs[7].default_value = (*glow, 1)
        # below horizon: hazy cloud-sea color
        below = MR(sep.outputs[2], -0.08, 0.0, 0.0, 1.0)
        skyc = MIX(hor, add.outputs[2], below)
    skys = N.new('ShaderNodeMix'); skys.data_type = 'RGBA'; skys.blend_type = 'MULTIPLY'
    skys.inputs['Factor'].default_value = 1.0
    L.new(skyc, skys.inputs[6]); skys.inputs[7].default_value = (1, 1, 1, 1)
    # cloud color scaled to sky brightness level
    cl = N.new('ShaderNodeMix'); cl.data_type = 'RGBA'; cl.blend_type = 'MULTIPLY'
    cl.inputs['Factor'].default_value = 1.0
    L.new(ccol, cl.inputs[6]); cl.inputs[7].default_value = (cloud_gain, cloud_gain, cloud_gain, 1)
    final = MIX(skys.outputs[2], cl.outputs[2], mask)
    if haze:
        final = MIX(final, (3.2, 3.5, 4.0), MR(sep.outputs[2], -0.02, 0.12, haze, 0.0))
    L.new(final, bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength
    L.new(bg.outputs['Background'], out.inputs['Surface'])
    if fog:
        vs = N.new('ShaderNodeVolumePrincipled')
        vs.inputs['Density'].default_value = fog[0]
        vs.inputs['Color'].default_value = (*fog[1], 1)
        vs.inputs['Anisotropy'].default_value = fog[2]
        L.new(vs.outputs['Volume'], out.inputs['Volume'])
    return w, sky, bg
