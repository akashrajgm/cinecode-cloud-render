"""
shot_love_act4.py (LOVE_04: The Stolen Gaze)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: Close cinematic portrait of heroine seated three rows behind.
Warm golden afternoon sunlight backlights her hair, pen twirling, soft romantic gaze.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.10, look='AgX - Punchy')
compositor(bloom=0.40, threshold=0.98, bloom_size=0.55, dispersion=0.006)

w = world_color((0.002, 0.003, 0.006))
add_world_fog(w, density=0.006, color=(0.95, 0.72, 0.38), anisotropy=0.75)

C = collection("SET_LOVE_04")
random.seed(504)

# Stylized Shaders
mat_skin_girl = mat_principled("Mat_SkinGirl", color=(0.95, 0.78, 0.68), rough=0.28)
mat_hair_girl = mat_principled("Mat_HairGirl", color=(0.14, 0.07, 0.03), rough=0.22)
mat_hair_rim = mat_emission("Mat_HairRim", color=(1.0, 0.85, 0.55), strength=6.0)
mat_uniform_white = mat_principled("Mat_UniformWhite", color=(0.92, 0.94, 0.96), rough=0.50)
mat_uniform_ribbon = mat_principled("Mat_UniformRibbon", color=(0.82, 0.18, 0.22), rough=0.40)
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.48, 0.28, 0.14), rough=0.35)
mat_pen_gold = mat_gold("Mat_PenGold", base=(1.0, 0.75, 0.25), rough=(0.12, 0.28))

# Focal anchor shifted up for 9:16 vertical safe zone
FOCAL_LOC = Vector((0.0, 0.0, 0.6))

# Classroom Desk
desk = prim('cube', name="GirlDesk", scale=(1.4, 0.7, 0.05), loc=(0, 0, FOCAL_LOC.z - 0.25), coll=C)
desk.data.materials.append(mat_desk_wood)

# Heroine Character Rig
girl_rig = bpy.data.objects.new("HeroineRig", None)
link(girl_rig, C)
girl_rig.location = Vector((0.0, 0.35, FOCAL_LOC.z))

# Torso & Shoulders
torso = prim('cylinder', name="Girl_Torso", r=0.20, depth=0.55, loc=(0, 0, 0), coll=C)
torso.parent = girl_rig
torso.data.materials.append(mat_uniform_white)

# Red Uniform Ribbon Tie
ribbon = prim('cube', name="Girl_Ribbon", scale=(0.06, 0.03, 0.12), loc=(0, -0.16, 0.22), coll=C)
ribbon.parent = girl_rig
ribbon.data.materials.append(mat_uniform_ribbon)

# Stylized Head (Slightly tilted, resting chin gently on fingers)
head = prim('sphere', name="Girl_Head", r=0.175, loc=(0, 0, 0.44), coll=C)
head.parent = girl_rig
head.data.materials.append(mat_skin_girl)

# Flowing Long Stylized Hair
hair_main = prim('sphere', name="Girl_HairMain", r=0.19, loc=(0, 0.03, 0.48), coll=C)
hair_main.parent = girl_rig
hair_main.scale = Vector((1.1, 1.25, 0.95))
hair_main.data.materials.append(mat_hair_girl)

# Backlit Golden Hair Strands (Catching afternoon window rays)
hair_strand = prim('torus', name="HairRimGlow", r=0.21, depth=0.025, loc=(0, 0.06, 0.50), coll=C)
hair_strand.parent = girl_rig
hair_strand.rotation_euler = Euler((math.radians(25), 0, 0), 'XYZ')
hair_strand.data.materials.append(mat_hair_rim)

# Heroine's Hand & Pen (Twirling slowly on the desk)
hand = prim('sphere', name="Girl_Hand", r=0.06, loc=(0.22, -0.22, -0.08), coll=C)
hand.parent = girl_rig
hand.data.materials.append(mat_skin_girl)

pen = prim('cylinder', name="Girl_Pen", r=0.015, depth=0.28, loc=(0.22, -0.22, -0.04), coll=C)
pen.parent = girl_rig
pen.rotation_euler = Euler((math.radians(45), math.radians(30), 0), 'XYZ')
pen.data.materials.append(mat_pen_gold)

# Pen twirling & subtle head breathing motion
for f in range(1, 73):
    pen.rotation_euler.rotate(Euler((0, 0, 0.08), 'XYZ'))
    pen.keyframe_insert("rotation_euler", frame=f)
    
    subtle_tilt = math.sin(f * 0.12) * 0.03
    head.rotation_euler = Euler((0.05, subtle_tilt, -0.08), 'XYZ')
    head.keyframe_insert("rotation_euler", frame=f)

# Cinematic Lighting: Heroine Golden Backlight + Soft Beauty Key
light(kind='SUN', name="Sun_Backlight", rot=(math.radians(35), math.radians(-25), math.radians(65)),
      energy=8.5, color=(1.0, 0.85, 0.50), coll=C)
light(kind='SPOT', name="Spot_BeautyKey", loc=(-1.6, -1.2, FOCAL_LOC.z + 1.2),
      rot=(math.radians(50), 0, math.radians(-32)), energy=650.0, color=(1.0, 0.92, 0.80), spot=55.0, coll=C)
light(kind='AREA', name="Light_FillPink", loc=(1.8, 0.2, FOCAL_LOC.z + 0.8), energy=240.0,
      color=(0.95, 0.75, 0.82), coll=C)

# Camera: Beautiful 75mm Portrait Close-up with shallow optical DOF
cam_start = Vector((0.0, -1.8, FOCAL_LOC.z + 0.55))
cam_mid   = Vector((-0.08, -1.4, FOCAL_LOC.z + 0.48))
cam_end   = Vector((0.0, -1.05, FOCAL_LOC.z + 0.42))

cam = camera(name="Camera", loc=cam_start, target=head, lens=70.0, fstop=1.8, coll=C)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("LOVE_04")
