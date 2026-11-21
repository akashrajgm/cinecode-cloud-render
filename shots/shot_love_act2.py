"""
shot_love_act2.py (LOVE_02: The Dilemma)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: Close over-the-shoulder / hero perspective on first bench.
Hero looking ahead at notebook, eyes darting, heart thump, nervous school crush tension.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.10, look='AgX - Punchy')
compositor(bloom=0.35, threshold=0.98, bloom_size=0.5, dispersion=0.005)

w = world_color((0.002, 0.003, 0.006))
add_world_fog(w, density=0.006, color=(0.95, 0.70, 0.32), anisotropy=0.70)

C = collection("SET_LOVE_02")
random.seed(502)

# Stylized Shaders
mat_skin_boy = mat_principled("Mat_SkinBoy", color=(0.92, 0.74, 0.62), rough=0.32)
mat_hair_boy = mat_principled("Mat_HairBoy", color=(0.08, 0.05, 0.04), rough=0.25)
mat_uniform_navy = mat_principled("Mat_UniformNavy", color=(0.08, 0.12, 0.22), rough=0.60)
mat_uniform_white = mat_principled("Mat_UniformWhite", color=(0.92, 0.94, 0.96), rough=0.50)
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.48, 0.28, 0.14), rough=0.35)
mat_notebook = mat_principled("Mat_Notebook", color=(0.96, 0.96, 0.94), rough=0.45)
mat_watch_metal = mat_metal("Mat_WatchMetal", base=(0.85, 0.88, 0.92), rough=(0.10, 0.25))

# Anchor first bench center
FOCAL_LOC = Vector((0.0, 0.0, 0.6))

# Desk Surface
desk = prim('cube', name="HeroDesk", scale=(1.4, 0.7, 0.05), loc=(0, 0, FOCAL_LOC.z - 0.15), coll=C)
desk.data.materials.append(mat_desk_wood)

# Open School Notebook on desk
notebook = prim('cube', name="Notebook", scale=(0.45, 0.32, 0.02), loc=(-0.1, 0.05, FOCAL_LOC.z - 0.11), coll=C)
notebook.rotation_euler = Euler((0, 0, math.radians(-12)), 'XYZ')
notebook.data.materials.append(mat_notebook)

# Hero Character: Seated at first bench
hero_rig = bpy.data.objects.new("HeroRig", None)
link(hero_rig, C)
hero_rig.location = Vector((0.0, 0.45, FOCAL_LOC.z))

# Torso & Shoulders
torso = prim('cylinder', name="Hero_Torso", r=0.22, depth=0.6, loc=(0, 0, 0), coll=C)
torso.parent = hero_rig
torso.data.materials.append(mat_uniform_navy)

# White Collar
collar = prim('torus', name="Hero_Collar", r=0.15, depth=0.035, loc=(0, 0, 0.32), coll=C)
collar.parent = hero_rig
collar.data.materials.append(mat_uniform_white)

# Stylized Head
head = prim('sphere', name="Hero_Head", r=0.18, loc=(0, 0, 0.48), coll=C)
head.parent = hero_rig
head.data.materials.append(mat_skin_boy)

# Stylized Hair with fringe
hair = prim('sphere', name="Hero_Hair", r=0.19, loc=(0, -0.02, 0.54), coll=C)
hair.parent = hero_rig
hair.scale = Vector((1.05, 1.15, 0.85))
hair.data.materials.append(mat_hair_boy)

# Hero Arm resting on desk with wristwatch
arm = prim('cylinder', name="Hero_Arm", r=0.065, depth=0.55, loc=(0.28, -0.22, -0.05), coll=C)
arm.parent = hero_rig
arm.rotation_euler = Euler((math.radians(75), math.radians(-25), math.radians(20)), 'XYZ')
arm.data.materials.append(mat_uniform_navy)

# Wristwatch on hero's wrist
watch = prim('cylinder', name="Hero_Watch", r=0.055, depth=0.025, loc=(0.22, -0.38, -0.08), coll=C)
watch.parent = hero_rig
watch.rotation_euler = Euler((math.radians(65), math.radians(-15), 0), 'XYZ')
watch.data.materials.append(mat_watch_metal)

# Nervous micro-movement: hero's head subtly glances left, glances right, tense posture
for f in range(1, 73):
    subtle_glance = math.sin(f * 0.15) * 0.08
    head.rotation_euler = Euler((0, 0, subtle_glance), 'XYZ')
    head.keyframe_insert("rotation_euler", frame=f)

# Cinematic Lighting: Golden Sun Shaft from left window + soft interior fill
light(kind='SUN', name="Sun_Golden", rot=(math.radians(45), math.radians(-25), math.radians(65)),
      energy=8.0, color=(1.0, 0.82, 0.45), coll=C)
light(kind='SPOT', name="Spot_HeroKey", loc=(-1.8, -0.8, FOCAL_LOC.z + 1.2),
      rot=(math.radians(50), 0, math.radians(-35)), energy=750.0, color=(1.0, 0.80, 0.50), spot=60.0, coll=C)
light(kind='AREA', name="Light_FillSoft", loc=(2.0, 0.5, FOCAL_LOC.z + 1.5), energy=280.0,
      color=(0.65, 0.75, 0.95), coll=C)

# Camera: Intimate over-the-shoulder medium close-up
cam_start = Vector((0.35, 1.45, FOCAL_LOC.z + 0.65))
cam_mid   = Vector((0.25, 1.10, FOCAL_LOC.z + 0.55))
cam_end   = Vector((0.15, 0.75, FOCAL_LOC.z + 0.45))

cam = camera(name="Camera", loc=cam_start, target=head, lens=65.0, fstop=1.8, coll=C)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("LOVE_02")
