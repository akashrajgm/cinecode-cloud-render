"""
shot_jet_act1.py (JET_01: The 1mm Fuel Droplet Hook)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Focal geometry strictly framed in Upper-Middle safe zone (Y: 18% to 58%).
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.15, look='AgX - Punchy')
compositor(bloom=0.45, threshold=0.98, bloom_size=0.6, dispersion=0.007)

w = world_color((0.0015, 0.0025, 0.005))
add_world_fog(w, density=0.015, color=(0.08, 0.28, 0.65), anisotropy=0.55)

C = collection("SET_JET_01")
random.seed(42)

# Shaders
mat_droplet = mat_glass("Mat_FuelDroplet", tint=(1.0, 0.75, 0.18), rough=0.02, ior=1.44)
mat_core = mat_emission("Mat_DropletCore", color=(1.0, 0.68, 0.12), strength=14.0)
mat_titanium = mat_principled("Mat_Titanium", color=(0.20, 0.24, 0.32), metal=0.95, rough=0.20,
                              emit=(0.02, 0.08, 0.18), emit_strength=0.8)
mat_conduit = mat_emission("Mat_Conduit", color=(0.0, 0.90, 1.0), strength=16.0)
mat_mist = mat_emission("Mat_Mist", color=(0.08, 0.85, 1.0), strength=10.0)
mat_spray = mat_emission("Mat_Spray", color=(1.0, 0.60, 0.10), strength=10.0)

# Upper-middle focal anchor (Z = 0.6)
FOCAL_LOC = Vector((0.0, 0.0, 0.6))

# 1. Suspended Fuel Droplet
droplet = prim('sphere', name="FuelDroplet", r=0.55, loc=FOCAL_LOC, coll=C)
droplet.data.materials.append(mat_droplet)

core = prim('sphere', name="DropletCore", r=0.28, loc=FOCAL_LOC, coll=C)
core.data.materials.append(mat_core)

# Pulsation
for f in range(1, 73):
    p = 1.0 + 0.08 * math.sin(f * 0.2)
    droplet.scale = Vector((p, p, 1.0 / (p * p)))
    droplet.keyframe_insert("scale", frame=f)

# 2. Titanium Injector Nozzle Architecture
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=2.4, depth=8.0, end_fill_type='NOTHING', location=FOCAL_LOC)
nozzle = bpy.context.active_object
nozzle.name = "InjectorNozzle"
nozzle.rotation_euler = (math.radians(90), 0, 0)
nozzle.data.materials.append(mat_titanium)

# Emissive conduit rings on inner wall
for ry in [-3.0, -1.5, 0.0, 1.5, 3.0]:
    bpy.ops.mesh.primitive_torus_add(major_radius=2.35, minor_radius=0.04, location=(0, ry, FOCAL_LOC.z))
    cr = bpy.context.active_object
    cr.rotation_euler = (math.radians(90), 0, 0)
    cr.data.materials.append(mat_conduit)

# 8 Aerodynamic Swirl Vanes along the nozzle interior
for v_i in range(8):
    ang = (v_i / 8.0) * math.tau
    vx = math.cos(ang) * 1.5
    vz = FOCAL_LOC.z + math.sin(ang) * 1.5
    v = prim('cube', name=f"Vane_{v_i}", scale=(0.8, 0.06, 0.15), loc=(vx, 1.2, vz), coll=C)
    v.rotation_euler = Euler((0.45, 0.35, ang), 'XYZ')
    v.data.materials.append(mat_titanium)

# 3. Spray and Mist Particles
for i in range(50):
    ang = random.uniform(0, math.tau)
    dist = random.uniform(0.65, 2.1)
    px = math.cos(ang) * dist
    pz = FOCAL_LOC.z + math.sin(ang) * dist
    py = random.uniform(-3.5, 3.5)
    r = random.uniform(0.025, 0.06)
    p = prim('sphere', name=f"Particle_{i}", r=r, loc=(px, py, pz), coll=C)
    p.data.materials.append(mat_spray if i % 2 == 0 else mat_mist)
    p.keyframe_insert("location", frame=1)
    p.location.y += random.uniform(-1.2, -0.4)
    p.keyframe_insert("location", frame=72)

# 4. Cinematic Lighting
light(kind='POINT', name="Light_Core", loc=FOCAL_LOC, energy=700.0, color=(1.0, 0.65, 0.15), coll=C)
light(kind='SPOT', name="Spot_Key_Cyan", loc=(-3.5, -5.5, FOCAL_LOC.z + 2.5),
      rot=(math.radians(55), 0, math.radians(-35)), energy=1100.0, color=(0.10, 0.85, 1.0), spot=70.0, coll=C)
light(kind='SPOT', name="Spot_Rim_Cyan", loc=(3.5, -4.5, FOCAL_LOC.z - 1.5),
      rot=(math.radians(65), 0, math.radians(40)), energy=850.0, color=(0.08, 0.75, 1.0), spot=60.0, coll=C)
light(kind='POINT', name="Light_Back_Amber", loc=(0.0, 4.0, FOCAL_LOC.z + 0.5), energy=650.0, color=(1.0, 0.55, 0.10), coll=C)

# 5. Camera (9:16 Vertical framing)
cam_start = Vector((0.0, -3.2, FOCAL_LOC.z))
cam_mid   = Vector((0.2, -4.8, FOCAL_LOC.z + 0.1))
cam_end   = Vector((0.0, -7.2, FOCAL_LOC.z + 0.2))

cam = camera(name="Camera", loc=cam_start, target=droplet, lens=42.0, fstop=2.0, coll=C)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("JET_01")
