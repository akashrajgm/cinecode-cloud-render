"""
shot_love_act1.py (LOVE_01: The Front Bench Trap)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: High school classroom establishing shot. Hero boy seated at the front bench,
heroine girl seated three rows back, afternoon golden sunlight streaming through windows.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.15, look='AgX - Punchy')
compositor(bloom=0.25, threshold=0.96, bloom_size=0.45, dispersion=0.004)

# Classroom atmosphere
w = world_color((0.15, 0.17, 0.22))
add_world_fog(w, density=0.003, color=(0.96, 0.80, 0.50), anisotropy=0.70)

C = collection("SET_LOVE_01")

# Materials
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.58, 0.36, 0.20), rough=0.30)
mat_metal_frame = mat_principled("Mat_MetalFrame", color=(0.20, 0.22, 0.25), metal=0.90, rough=0.25)
mat_blackboard = mat_principled("Mat_Blackboard", color=(0.06, 0.10, 0.08), rough=0.70)
mat_wall = mat_principled("Mat_Wall", color=(0.90, 0.88, 0.84), rough=0.55)

# Blackboard & Classroom Walls
blackboard = prim('cube', name="Blackboard", scale=(3.2, 0.05, 1.2), loc=(0, -2.8, 1.4), coll=C)
blackboard.data.materials.append(mat_blackboard)

floor = prim('cube', name="Floor", scale=(6.0, 10.0, 0.1), loc=(0, 2.0, -0.6), coll=C)
floor.data.materials.append(mat_desk_wood)

wall = prim('cube', name="Wall", scale=(6.0, 0.1, 4.0), loc=(0, 8.0, 1.8), coll=C)
wall.data.materials.append(mat_wall)

# 4 Rows of Wooden Student Desks
for r in range(4):
    y_pos = -0.5 + r * 1.8
    for col_x in [-1.4, 0.0, 1.4]:
        desk = prim('cube', name=f"Desk_R{r}_{col_x}", scale=(1.1, 0.50, 0.04), loc=(col_x, y_pos, 0.55), coll=C)
        desk.data.materials.append(mat_desk_wood)

# 1. LOAD HERO BOY AT ROW 0 (Front Bench Center)
boy_path = os.path.join(FILM, "assets", "characters", "hero_boy.glb")
bpy.ops.import_scene.gltf(filepath=boy_path)

for name in ['robo_arm', 'hair_tail']:
    o = bpy.data.objects.get(name)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)

boy_arm = bpy.data.objects.get("Armature")
if boy_arm:
    boy_arm.name = "Armature_HeroBoy"
    boy_arm.location = Vector((0.0, -0.10, -0.42))
    boy_arm.rotation_euler = Euler((0, 0, math.radians(180)), 'XYZ')

# 2. LOAD HEROINE GIRL AT ROW 3 (Three Rows Back Center)
girl_path = os.path.join(FILM, "assets", "characters", "heroine_girl.glb")
bpy.ops.import_scene.gltf(filepath=girl_path)

girl_arm = bpy.data.objects.get("Armature")
if girl_arm:
    girl_arm.name = "Armature_HeroineGirl"
    girl_arm.location = Vector((0.0, 5.30, -0.40))
    girl_arm.rotation_euler = Euler((0, 0, math.radians(180)), 'XYZ')

# Lighting: Warm Golden Afternoon Sun
light(kind='SUN', name="Sun_Golden", rot=(math.radians(45), math.radians(-25), math.radians(65)),
      energy=7.5, color=(1.0, 0.85, 0.50), coll=C)
light(kind='SPOT', name="Spot_ClassroomKey", loc=(-2.0, -1.0, 2.5),
      rot=(math.radians(45), 0, math.radians(-30)), energy=550.0, color=(1.0, 0.90, 0.75), spot=60.0, coll=C)
light(kind='AREA', name="Light_FillSoft", loc=(2.5, 1.5, 2.0), energy=220.0,
      color=(0.80, 0.88, 1.0), coll=C)

# Camera: High-Angle Vertical Sweep showing the classroom & front-bench hero
cam_target = bpy.data.objects.new("CamTarget", None)
link(cam_target, C)
cam_target.location = Vector((0.0, 1.5, 0.8))

cam_start = Vector((0.8, -3.2, 2.2))
cam_mid   = Vector((0.4, -2.4, 1.8))
cam_end   = Vector((0.1, -1.6, 1.4))

cam = camera(name="Camera", loc=cam_start, target=cam_target, focus=cam_target, lens=38.0, fstop=4.0, coll=C)
track_to(cam, cam_target)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("LOVE_01")
