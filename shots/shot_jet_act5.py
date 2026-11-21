"""
shot_jet_act5.py (JET_05: Blow - 1,000 MPH Thrust & Stratosphere)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Focal geometry strictly framed in Upper-Middle safe zone (Y: 18% to 58%).
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.10, look='AgX - Punchy')
compositor(bloom=0.40, threshold=0.98, bloom_size=0.6, dispersion=0.007)

# Stratosphere dark twilight horizon
w = world_color((0.001, 0.0015, 0.003))
add_world_fog(w, density=0.005, color=(0.04, 0.08, 0.22), anisotropy=0.60)

C = collection("SET_JET_05")
random.seed(404)

# Shaders
mat_nozzle = mat_principled("Mat_ExhaustNozzle", color=(0.20, 0.22, 0.28), metal=0.95, rough=0.20,
                            emit=(0.02, 0.06, 0.16), emit_strength=0.3)
mat_mach_diamond = mat_emission("Mat_MachDiamond", color=(1.0, 0.75, 0.20), strength=20.0)
mat_shock_violet = mat_emission("Mat_ShockViolet", color=(0.60, 0.30, 1.0), strength=14.0)
mat_exhaust_plume = mat_emission("Mat_ExhaustPlume", color=(1.0, 0.42, 0.05), strength=10.0)
mat_text_white = mat_emission("Mat_TextWhite", color=(0.95, 0.98, 1.0), strength=12.0)
mat_text_gold = mat_emission("Mat_TextGold", color=(1.0, 0.75, 0.20), strength=16.0)

# Upper-middle focal anchor
FOCAL_LOC = Vector((0.0, 0.0, 0.6))

# 1. Exhaust Nozzle Cone & Cowl
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=2.2, depth=4.0, end_fill_type='NOTHING', location=(0, -2.0, FOCAL_LOC.z))
nozzle = bpy.context.active_object
nozzle.name = "ExhaustNozzle"
nozzle.rotation_euler = (math.radians(90), 0, 0)
nozzle.data.materials.append(mat_nozzle)

# Central Turbine Exhaust Cone (Aerodynamic tail plug)
tail_plug = prim('cone', name="TailPlug", r=0.75, depth=2.4, segments=48, loc=(0, -1.0, FOCAL_LOC.z), coll=C)
tail_plug.rotation_euler = (math.radians(90), 0, 0)
tail_plug.data.materials.append(mat_nozzle)

# 2. Supersonic Exhaust Jet Plume with Mach Shock Diamonds
plume_rig = bpy.data.objects.new("PlumeRig", None)
link(plume_rig, C)
plume_rig.location = FOCAL_LOC

# 5 Consecutive Mach Shock Diamond Nodes expanding along Y (+0.5 to +6.5)
for m_i in range(5):
    my = 0.5 + m_i * 1.2
    m_scale = 1.0 - m_i * 0.12
    # Diamond diamond cone pair
    d1 = prim('cone', name=f"MachCone1_{m_i}", r=0.40 * m_scale, depth=0.55 * m_scale, segments=32, loc=(0, my - 0.25, FOCAL_LOC.z), coll=C)
    d1.rotation_euler = (math.radians(-90), 0, 0)
    d1.parent = plume_rig
    d1.data.materials.append(mat_mach_diamond)
    
    d2 = prim('cone', name=f"MachCone2_{m_i}", r=0.40 * m_scale, depth=0.55 * m_scale, segments=32, loc=(0, my + 0.25, FOCAL_LOC.z), coll=C)
    d2.rotation_euler = (math.radians(90), 0, 0)
    d2.parent = plume_rig
    d2.data.materials.append(mat_shock_violet)
    
    # Expanding shockwave ring
    bpy.ops.mesh.primitive_torus_add(major_radius=0.70 * m_scale, minor_radius=0.035, location=(0, my, FOCAL_LOC.z))
    s_ring = bpy.context.active_object
    s_ring.rotation_euler = (math.radians(90), 0, 0)
    s_ring.parent = plume_rig
    s_ring.data.materials.append(mat_exhaust_plume)

# Pulsation of the Mach diamonds
for f in range(1, 73):
    pulse = 1.0 + 0.05 * math.sin(f * 0.4)
    plume_rig.scale = Vector((pulse, 1.0, pulse))
    plume_rig.keyframe_insert("scale", frame=f)

# High-velocity exhaust particles blasting into stratosphere
for p_i in range(35):
    ang = (p_i / 35.0) * math.tau + random.uniform(-0.1, 0.1)
    dist = random.uniform(0.15, 1.2)
    px = math.cos(ang) * dist
    pz = FOCAL_LOC.z + math.sin(ang) * dist
    py = random.uniform(0.2, 7.0)
    
    thrust_p = prim('sphere', name=f"ThrustP_{p_i}", r=random.uniform(0.03, 0.07), loc=(px, py, pz), coll=C)
    thrust_p.data.materials.append(mat_mach_diamond if p_i % 2 == 0 else mat_exhaust_plume)
    thrust_p.keyframe_insert("location", frame=1)
    thrust_p.location.y += random.uniform(3.0, 5.5)
    thrust_p.keyframe_insert("location", frame=72)

# 3. Cinematic 3D Typography in Upper-Middle Safe Zone (Z = 1.5, Y: 28%-36% screen space)
def make_title_text(text, name, loc, size=0.28, extrude=0.04, mat=mat_text_white):
    t_data = bpy.data.curves.new(name=f"{name}_data", type='FONT')
    t_data.body = text
    t_data.size = size
    t_data.extrude = extrude
    t_data.align_x = 'CENTER'
    t_data.align_y = 'CENTER'
    obj = bpy.data.objects.new(name, t_data)
    link(obj, C)
    obj.location = loc
    obj.rotation_euler = (math.radians(90), 0, 0)
    obj.data.materials.append(mat)
    return obj

title_1 = make_title_text("35,000 FEET. 1,000 MPH.", "Text_Stats", loc=Vector((0.0, 1.5, FOCAL_LOC.z + 1.15)), size=0.26, extrude=0.03, mat=mat_text_white)
title_2 = make_title_text("PURE, CONTROLLED FLIGHT.", "Text_Climax", loc=Vector((0.0, 1.5, FOCAL_LOC.z + 0.75)), size=0.24, extrude=0.03, mat=mat_text_gold)

# 4. Cinematic Lighting (Three-quarter rim setup)
light(kind='POINT', name="Light_PlumeCore", loc=(0, 2.5, FOCAL_LOC.z), energy=950.0, color=(1.0, 0.72, 0.20), coll=C)
light(kind='SPOT', name="Spot_Twilight_Cyan", loc=(-4.5, 2.0, FOCAL_LOC.z + 3.5),
      rot=(math.radians(50), 0, math.radians(-35)), energy=1200.0, color=(0.10, 0.85, 1.0), spot=70.0, coll=C)
light(kind='SPOT', name="Spot_Nozzle_Rim", loc=(4.0, -3.0, FOCAL_LOC.z + 2.0),
      rot=(math.radians(60), 0, math.radians(45)), energy=900.0, color=(0.8, 0.6, 1.0), spot=65.0, coll=C)

# 5. Camera: Three-quarter cinematic sweep revealing supersonic thrust plume
cam_start = Vector((3.2, 1.0, FOCAL_LOC.z + 0.8))
cam_mid   = Vector((4.8, 3.2, FOCAL_LOC.z + 1.2))
cam_end   = Vector((7.2, 5.5, FOCAL_LOC.z + 1.8))

cam = camera(name="Camera", loc=cam_start, target=plume_rig, lens=36.0, fstop=2.2, coll=C)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("JET_05")
