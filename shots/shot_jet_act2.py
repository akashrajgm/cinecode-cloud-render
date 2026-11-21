"""
shot_jet_act2.py (JET_02: Suck - The Sub-Zero Titanium Fan)
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

w = world_color((0.0015, 0.003, 0.008))
add_world_fog(w, density=0.016, color=(0.06, 0.32, 0.75), anisotropy=0.60)

C = collection("SET_JET_02")
random.seed(101)

# Shaders
mat_titanium = mat_principled("Mat_FanTitanium", color=(0.42, 0.46, 0.52), metal=0.98, rough=0.18,
                              emit=(0.04, 0.10, 0.22), emit_strength=0.6)
mat_gold_edge = mat_gold("Mat_BladeGoldEdge", base=(1.0, 0.72, 0.22), rough=(0.10, 0.25))
mat_cone = mat_principled("Mat_SpinnerCone", color=(0.10, 0.12, 0.16), metal=0.85, rough=0.25)
mat_cowl = mat_principled("Mat_EngineCowl", color=(0.28, 0.32, 0.40), metal=0.92, rough=0.22,
                          emit=(0.02, 0.06, 0.16), emit_strength=0.5)
mat_spiral = mat_emission("Mat_ConeSpiral", color=(1.0, 1.0, 1.0), strength=12.0)
mat_ice_ribbon = mat_emission("Mat_IceRibbon", color=(0.06, 0.78, 1.0), strength=12.0)
mat_frozen_mist = mat_emission("Mat_FrozenMist", color=(0.40, 0.90, 1.0), strength=7.0)

# Focal anchor shifted up for 9:16 vertical safe zone
FOCAL_LOC = Vector((0.0, 0.0, 0.6))

# 1. Aerodynamic Central Spinner Cone
cone_hub = prim('cone', name="FanHub", r=0.75, depth=1.6, segments=48, loc=FOCAL_LOC, coll=C)
cone_hub.rotation_euler = (math.radians(-90), 0, 0)
cone_hub.data.materials.append(mat_cone)

# Iconic Spiral on Spinner Cone
bpy.ops.mesh.primitive_torus_add(major_radius=0.45, minor_radius=0.035, location=(0, -0.4, FOCAL_LOC.z))
spiral = bpy.context.active_object
spiral.name = "SpinnerSpiral"
spiral.rotation_euler = (math.radians(-75), 0, math.radians(25))
spiral.data.materials.append(mat_spiral)

# 2. 24 Wide-Chord Swept Titanium Fan Blades
fan_rig = bpy.data.objects.new("FanBladesRig", None)
link(fan_rig, C)
fan_rig.location = FOCAL_LOC

num_blades = 24
for b_i in range(num_blades):
    ang = (b_i / num_blades) * math.tau
    # Main curved titanium blade
    blade = prim('cube', name=f"Blade_{b_i:02d}", scale=(0.22, 0.035, 1.4), loc=(0, 0, 0.9), coll=C)
    blade.parent = fan_rig
    blade.rotation_euler = Euler((0.35, math.radians(24), 0), 'XYZ')
    blade.location = Vector((math.cos(ang) * 0.45, math.sin(ang) * 0.45, 0))
    blade.rotation_euler.rotate(Euler((0, 0, ang), 'XYZ'))
    blade.data.materials.append(mat_titanium)
    
    # Gold leading edge strip
    edge = prim('cube', name=f"GoldEdge_{b_i:02d}", scale=(0.025, 0.015, 1.35), loc=(0, 0, 0.92), coll=C)
    edge.parent = fan_rig
    edge.location = blade.location + Vector((math.cos(ang + 0.1) * 0.12, math.sin(ang + 0.1) * 0.12, 0))
    edge.rotation_euler = blade.rotation_euler
    edge.data.materials.append(mat_gold_edge)

# High-speed Fan Rotation Animation
fan_rig.keyframe_insert("rotation_euler", frame=1)
fan_rig.rotation_euler = Euler((0, math.radians(-1440), 0), 'XYZ') # 4 full rotations over 72 frames
fan_rig.keyframe_insert("rotation_euler", frame=72)

# 3. Outer Nacelle Cowling (Open cylindrical frame)
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=2.65, depth=4.5, end_fill_type='NOTHING', location=FOCAL_LOC)
cowl = bpy.context.active_object
cowl.name = "NacelleCowl"
cowl.rotation_euler = (math.radians(90), 0, 0)
cowl.data.materials.append(mat_cowl)

# Intake Lip Bevel Ring
bpy.ops.mesh.primitive_torus_add(major_radius=2.65, minor_radius=0.12, location=(0, -2.1, FOCAL_LOC.z))
lip = bpy.context.active_object
lip.rotation_euler = (math.radians(90), 0, 0)
lip.data.materials.append(mat_cowl)

# 4. Swirling Sub-Zero Ice-Blue Air Streamlines
for r_i in range(32):
    ang = (r_i / 32.0) * math.tau + random.uniform(-0.1, 0.1)
    dist = random.uniform(1.1, 2.4)
    px = math.cos(ang) * dist
    pz = FOCAL_LOC.z + math.sin(ang) * dist
    py = random.uniform(-3.5, 1.5)
    
    rib = prim('cylinder', name=f"IceStream_{r_i}", r=0.028, depth=random.uniform(0.8, 1.8), loc=(px, py, pz), coll=C)
    rib.rotation_euler = Euler((math.radians(80), 0.3, ang + 0.5), 'XYZ')
    rib.data.materials.append(mat_ice_ribbon if r_i % 2 == 0 else mat_frozen_mist)
    
    rib.keyframe_insert("location", frame=1)
    rib.location.y += random.uniform(1.5, 2.8) # Rushing backward into the fan
    rib.rotation_euler.rotate(Euler((0, 0, 1.2), 'XYZ'))
    rib.keyframe_insert("location", frame=72)

# 5. Cinematic Lighting
light(kind='POINT', name="Light_HubCore", loc=FOCAL_LOC + Vector((0, -0.6, 0)), energy=750.0, color=(0.10, 0.85, 1.0), coll=C)
light(kind='SPOT', name="Spot_Key_Cyan", loc=(-3.8, -6.5, FOCAL_LOC.z + 3.2),
      rot=(math.radians(55), 0, math.radians(-32)), energy=1250.0, color=(0.12, 0.82, 1.0), spot=72.0, coll=C)
light(kind='SPOT', name="Spot_Gold_Rim", loc=(4.0, -5.0, FOCAL_LOC.z - 2.0),
      rot=(math.radians(60), 0, math.radians(45)), energy=950.0, color=(1.0, 0.72, 0.22), spot=65.0, coll=C)
light(kind='AREA', name="Light_TopSky", loc=(0.0, -2.5, FOCAL_LOC.z + 4.0), energy=350.0, color=(0.4, 0.75, 1.0), coll=C)

# 6. Camera (Dynamic 28mm wide forward dive toward fan hub)
cam_start = Vector((0.0, -7.5, FOCAL_LOC.z + 0.4))
cam_mid   = Vector((0.3, -4.8, FOCAL_LOC.z + 0.2))
cam_end   = Vector((0.0, -2.8, FOCAL_LOC.z))

cam = camera(name="Camera", loc=cam_start, target=cone_hub, lens=32.0, fstop=2.2, coll=C)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("JET_02")
