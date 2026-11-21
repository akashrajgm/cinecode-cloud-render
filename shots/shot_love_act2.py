"""
shot_love_act2.py (LOVE_02: The Dilemma)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: Hero seated at the first bench. Tense expressions, eyes glancing,
cannot turn back to look at the girl without getting caught by the teacher/class.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.15, look='AgX - Punchy')
compositor(bloom=0.25, threshold=0.95, bloom_size=0.45, dispersion=0.004)

# Classroom daylight atmosphere
w = world_color((0.15, 0.17, 0.22))
add_world_fog(w, density=0.004, color=(0.96, 0.78, 0.45), anisotropy=0.70)

C = collection("SET_LOVE_02")
random.seed(502)

# Stylized Shaders
mat_skin_boy = mat_principled("Mat_SkinBoy", color=(0.94, 0.76, 0.64), rough=0.35)
mat_hair_boy = mat_principled("Mat_HairBoy", color=(0.08, 0.05, 0.04), rough=0.28)
mat_uniform_navy = mat_principled("Mat_UniformNavy", color=(0.10, 0.16, 0.30), rough=0.55)
mat_uniform_white = mat_principled("Mat_UniformWhite", color=(0.95, 0.95, 0.96), rough=0.40)
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.58, 0.36, 0.20), rough=0.30)
mat_metal = mat_metal("Mat_Metal", base=(0.85, 0.88, 0.92), rough=(0.12, 0.20))
mat_blackboard = mat_principled("Mat_Blackboard", color=(0.08, 0.14, 0.10), rough=0.60)
mat_wall = mat_principled("Mat_Wall", color=(0.88, 0.86, 0.80), rough=0.60)

# Classroom Classroom Walls & Floor
floor = prim('cube', name="Floor", scale=(5.0, 8.0, 0.1), loc=(0, 2.0, -0.6), coll=C)
floor.data.materials.append(mat_desk_wood)

back_wall = prim('cube', name="Wall", scale=(5.0, 0.1, 3.0), loc=(0, 7.0, 1.5), coll=C)
back_wall.data.materials.append(mat_wall)

# Hero Desk
desk = prim('cube', name="Desk", scale=(1.2, 0.55, 0.04), loc=(0, -0.15, 0.55), coll=C)
desk.data.materials.append(mat_desk_wood)

# School Notebook & Pen on desk
nb = prim('cube', name="Notebook", scale=(0.35, 0.25, 0.02), loc=(-0.15, -0.15, 0.58), coll=C)
nb.rotation_euler = Euler((0, 0, math.radians(-10)), 'XYZ')
nb.data.materials.append(mat_uniform_white)

# 3D Stylized Hero Character (Seated at front bench, facing -Y / camera)
hero_anchor = bpy.data.objects.new("HeroAnchor", None)
link(hero_anchor, C)
hero_anchor.location = Vector((0.0, 0.25, 0.6))

# Torso & Shoulders
torso = prim('cylinder', name="Hero_Torso", r=0.20, depth=0.55, loc=(0, 0, 0.0), coll=C)
torso.parent = hero_anchor
torso.data.materials.append(mat_uniform_navy)

# Collar
collar = prim('torus', name="Hero_Collar", R=0.18, r=0.03, loc=(0, 0, 0.29), coll=C)
collar.parent = hero_anchor
collar.data.materials.append(mat_uniform_white)

# Head
head = prim('sphere', name="Hero_Head", r=0.16, loc=(0, 0, 0.46), coll=C)
head.parent = hero_anchor
head.data.materials.append(mat_skin_boy)

# Stylized Hair
hair = prim('sphere', name="Hero_Hair", r=0.175, loc=(0, 0.02, 0.51), coll=C)
hair.parent = hero_anchor
hair.scale = Vector((1.05, 1.12, 0.85))
hair.data.materials.append(mat_hair_boy)

# Cartoon Eyes
eye_l = prim('sphere', name="Eye_L", r=0.03, loc=(-0.055, -0.14, 0.48), coll=C)
eye_l.parent = hero_anchor
eye_l.data.materials.append(mat_hair_boy)

eye_r = prim('sphere', name="Eye_R", r=0.03, loc=(0.055, -0.14, 0.48), coll=C)
eye_r.parent = hero_anchor
eye_r.data.materials.append(mat_hair_boy)

# Hero Left Arm resting on desk with Wristwatch
arm = prim('cylinder', name="Hero_Arm", r=0.055, depth=0.45, loc=(0.20, -0.22, 0.0), coll=C)
arm.parent = hero_anchor
arm.rotation_euler = Euler((math.radians(65), math.radians(-20), math.radians(15)), 'XYZ')
arm.data.materials.append(mat_uniform_navy)

# Wristwatch
watch = prim('cylinder', name="Watch", r=0.05, depth=0.02, loc=(0.14, -0.32, -0.04), coll=C)
watch.parent = hero_anchor
watch.rotation_euler = Euler((math.radians(50), math.radians(-10), 0), 'XYZ')
watch.data.materials.append(mat_metal)

# Other students blurred in background behind hero
for row in [1, 2, 3]:
    for col in [-1.2, 0.0, 1.2]:
        bg_torso = prim('cylinder', name=f"BG_Torso_{row}_{col}", r=0.16, depth=0.45, loc=(col, 0.3 + row * 1.5, 0.6), coll=C)
        bg_torso.data.materials.append(mat_uniform_navy)
        bg_head = prim('sphere', name=f"BG_Head_{row}_{col}", r=0.13, loc=(col, 0.3 + row * 1.5, 0.98), coll=C)
        bg_head.data.materials.append(mat_skin_boy)

# Nervous animation: eyes darting and subtle head tilt
for f in range(1, 73):
    tilt = math.sin(f * 0.12) * 0.04
    head.rotation_euler = Euler((math.radians(5), 0, tilt), 'XYZ')
    head.keyframe_insert("rotation_euler", frame=f)

# Cinematic Lighting: Golden afternoon window sunlight from left + soft key
light(kind='SUN', name="Sun_Window", rot=(math.radians(45), math.radians(-25), math.radians(65)),
      energy=6.5, color=(1.0, 0.85, 0.50), coll=C)
light(kind='SPOT', name="Spot_HeroKey", loc=(-1.2, -1.5, 1.8),
      rot=(math.radians(45), 0, math.radians(-30)), energy=450.0, color=(1.0, 0.88, 0.65), spot=55.0, coll=C)
light(kind='AREA', name="Light_Fill", loc=(1.5, -1.0, 1.5), energy=180.0,
      color=(0.75, 0.85, 1.0), coll=C)

# Camera: Front-Three-Quarter Cinematic Portrait (9:16 Vertical Framing)
# Placed in front of desk, looking up slightly at hero's tense face and watch
cam_start = Vector((-0.25, -1.75, 1.30))
cam_mid   = Vector((-0.18, -1.45, 1.25))
cam_end   = Vector((-0.12, -1.25, 1.20))

cam = camera(name="Camera", loc=cam_start, target=head, focus=head, lens=45.0, fstop=3.5, coll=C)
track_to(cam, head)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("LOVE_02")
