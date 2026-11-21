"""
shot_jet_act4.py (JET_04: Bang - 2,000°C Molten Plasma Chamber)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Focal geometry strictly framed in Upper-Middle safe zone (Y: 18% to 58%).
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.08, look='AgX - Punchy')
compositor(bloom=0.45, threshold=0.98, bloom_size=0.6, dispersion=0.007)

w = world_color((0.001, 0.0015, 0.003))
add_world_fog(w, density=0.004, color=(0.14, 0.06, 0.02), anisotropy=0.60)

C = collection("SET_JET_04")
random.seed(303)

# Shaders
mat_flame_core = mat_emission("Mat_PlasmaCore", color=(1.0, 0.72, 0.15), strength=18.0)
mat_flame_vortex = mat_emission("Mat_FlameVortex", color=(1.0, 0.40, 0.05), strength=14.0)
mat_cooling_film = mat_emission("Mat_CoolingFilm", color=(0.08, 0.85, 1.0), strength=12.0)
mat_combustor_liner = mat_principled("Mat_CombustorLiner", color=(0.20, 0.22, 0.28), metal=0.95, rough=0.22,
                                    emit=(0.02, 0.01, 0.01), emit_strength=0.1)

# Upper-middle focal anchor
FOCAL_LOC = Vector((0.0, 0.0, 0.6))

# 1. Annular Combustor Outer Liner (Perforated casing)
bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=2.6, depth=8.0, end_fill_type='NOTHING', location=FOCAL_LOC)
liner = bpy.context.active_object
liner.name = "CombustorLiner"
liner.rotation_euler = (math.radians(90), 0, 0)
liner.data.materials.append(mat_combustor_liner)

# Protective Ice-Blue Cooling Film Ribbons (Hugging the outer liner walls)
for c_i in range(24):
    ang = (c_i / 24.0) * math.tau
    cx = math.cos(ang) * 2.50
    cz = FOCAL_LOC.z + math.sin(ang) * 2.50
    cy = random.uniform(-3.5, 3.5)
    film = prim('cube', name=f"CoolFilm_{c_i}", scale=(0.18, 1.1, 0.02), loc=(cx, cy, cz), coll=C)
    film.rotation_euler = Euler((math.radians(90), 0, ang), 'XYZ')
    film.data.materials.append(mat_cooling_film)

# 2. Central Roaring Plasma Vortex
flame_rig = bpy.data.objects.new("FlameVortexRig", None)
link(flame_rig, C)
flame_rig.location = FOCAL_LOC

# Core Plasma Rings along the combustion center
for fy in [-2.0, -0.5, 1.0, 2.5]:
    bpy.ops.mesh.primitive_torus_add(major_radius=0.45, minor_radius=0.08, location=(0, fy, FOCAL_LOC.z))
    ft = bpy.context.active_object
    ft.rotation_euler = (math.radians(90), 0, 0)
    ft.parent = flame_rig
    ft.data.materials.append(mat_flame_core)

# 40 Turbulent Plasma Flame Streamers
for p_i in range(40):
    ang = (p_i / 40.0) * math.tau + random.uniform(-0.15, 0.15)
    dist = random.uniform(0.2, 1.1)
    px = math.cos(ang) * dist
    pz = FOCAL_LOC.z + math.sin(ang) * dist
    py = random.uniform(-3.5, 3.5)
    rad = random.uniform(0.04, 0.08)
    
    flame = prim('sphere', name=f"Plasma_{p_i}", r=rad, loc=(px, py, pz), coll=C)
    flame.parent = flame_rig
    flame.data.materials.append(mat_flame_core if p_i % 2 == 0 else mat_flame_vortex)
    
    flame.keyframe_insert("location", frame=1)
    flame.location.y += random.uniform(1.8, 3.5)
    flame.scale = Vector((random.uniform(0.8, 1.3), random.uniform(1.2, 2.0), random.uniform(0.8, 1.3)))
    flame.keyframe_insert("location", frame=72)

# High-velocity Flame Vortex Rotation
flame_rig.keyframe_insert("rotation_euler", frame=1)
flame_rig.rotation_euler = Euler((0, math.radians(-1440), 0), 'XYZ')
flame_rig.keyframe_insert("rotation_euler", frame=72)

# 3. Cinematic Lighting
light(kind='POINT', name="Light_Plasma_Core", loc=FOCAL_LOC, energy=850.0, color=(1.0, 0.65, 0.15), coll=C)
light(kind='POINT', name="Light_Front_Ignition", loc=(0, -2.5, FOCAL_LOC.z + 0.3), energy=650.0, color=(1.0, 0.45, 0.05), coll=C)
light(kind='POINT', name="Light_Rear_Burn", loc=(0, 2.5, FOCAL_LOC.z + 0.3), energy=750.0, color=(1.0, 0.75, 0.20), coll=C)
light(kind='SPOT', name="Spot_Cooling_Rim", loc=(-3.8, -1.0, FOCAL_LOC.z + 2.8),
      rot=(math.radians(50), 0, math.radians(-30)), energy=1100.0, color=(0.10, 0.85, 1.0), spot=75.0, coll=C)

# 4. Camera: Smooth tracking sweep maintaining clear focal distance from the flame vortex
cam_start = Vector((0.0, -5.5, FOCAL_LOC.z + 0.4))
cam_mid   = Vector((0.8, -3.4, FOCAL_LOC.z + 0.2))
cam_end   = Vector((0.2, -1.6, FOCAL_LOC.z))

cam = camera(name="Camera", loc=cam_start, target=flame_rig, lens=38.0, fstop=2.2, coll=C)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("JET_04")
