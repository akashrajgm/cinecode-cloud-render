"""
shot_love_act1.py (LOVE_01: The Front Bench Trap)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: High school classroom establishing shot. Hero boy seated at the front bench,
heroine girl seated three rows back, afternoon golden sunlight streaming through windows.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
import spiderverse
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.15, look='AgX - Punchy')
compositor(bloom=0.28, threshold=0.94, bloom_size=0.50, dispersion=0.012)

# Classroom atmosphere with golden volumetric sunbeams
w = world_color((0.12, 0.14, 0.18))
add_world_fog(w, density=0.004, color=(0.98, 0.82, 0.50), anisotropy=0.74)

C = collection("SET_LOVE_01")

# Materials
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.58, 0.36, 0.20), rough=0.30)
mat_metal_frame = mat_principled("Mat_MetalFrame", color=(0.20, 0.22, 0.25), metal=0.90, rough=0.25)
mat_blackboard = mat_principled("Mat_Blackboard", color=(0.06, 0.10, 0.08), rough=0.70)
mat_wall = mat_principled("Mat_Wall", color=(0.90, 0.88, 0.84), rough=0.55)

# Blackboard & Classroom Walls
blackboard = prim('cube', name="Blackboard", scale=(3.4, 0.05, 1.3), loc=(0, -2.8, 1.4), coll=C)
blackboard.data.materials.append(mat_blackboard)

floor = prim('cube', name="Floor", scale=(7.0, 12.0, 0.1), loc=(0, 2.0, -0.6), coll=C)
floor.data.materials.append(mat_desk_wood)

wall_back = prim('cube', name="WallBack", scale=(7.0, 0.1, 4.5), loc=(0, 9.0, 1.8), coll=C)
wall_back.data.materials.append(mat_wall)

# Window wall on left with crossbars for volumetric light shafts
win_wall = prim('cube', name="WinWall", scale=(0.1, 10.0, 4.5), loc=(-3.2, 2.0, 1.8), coll=C)
win_wall.data.materials.append(mat_wall)

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
    
    # Bone animation: Nervous glance back toward Row 3, quick snap forward
    bpy.context.view_layer.objects.active = boy_arm
    bpy.ops.object.mode_set(mode='POSE')
    head_bone = boy_arm.pose.bones.get("head 1")
    if head_bone:
        head_bone.rotation_mode = 'XYZ'
        head_bone.rotation_euler = Euler((0, 0, 0))
        head_bone.keyframe_insert("rotation_euler", frame=1)
        head_bone.rotation_euler = Euler((math.radians(4), math.radians(18), math.radians(-10)))
        head_bone.keyframe_insert("rotation_euler", frame=32)
        head_bone.rotation_euler = Euler((math.radians(-2), math.radians(-2), 0))
        head_bone.keyframe_insert("rotation_euler", frame=50)
        head_bone.rotation_euler = Euler((0, 0, 0))
        head_bone.keyframe_insert("rotation_euler", frame=72)
    bpy.ops.object.mode_set(mode='OBJECT')

# Hero Boy Spider-Verse Ink Outline & Psychological Blendshapes
boy_head = bpy.data.objects.get("head")
boy_wear = bpy.data.objects.get("wear")
spiderverse.apply_comic_ink(boy_head, thickness=-0.003)
spiderverse.apply_comic_ink(boy_wear, thickness=-0.003)
spiderverse.animate_hero_boy_emotions(boy_head, boy_arm, shot_act=1)

# 2. LOAD HEROINE GIRL AT ROW 3 (Three Rows Back Center)
girl_path = os.path.join(FILM, "assets", "characters", "heroine_girl.glb")
bpy.ops.import_scene.gltf(filepath=girl_path)

girl_arm = bpy.data.objects.get("Armature")
if girl_arm:
    girl_arm.name = "Armature_HeroineGirl"
    girl_arm.location = Vector((0.0, 5.30, -0.40))
    girl_arm.rotation_euler = Euler((0, 0, math.radians(180)), 'XYZ')

# Heroine Girl Comic Ink
girl_face = bpy.data.objects.get("Face (merged)(Clone)")
girl_body = bpy.data.objects.get("Body (merged)")
spiderverse.apply_comic_ink(girl_face, thickness=-0.003)
spiderverse.apply_comic_ink(girl_body, thickness=-0.003)

# Add other seated student silhouettes to populate the 30-40 student classroom
mat_student_body = mat_principled("Mat_StudentBody", color=(0.18, 0.22, 0.35), rough=0.6)
mat_student_head = mat_principled("Mat_StudentHead", color=(0.90, 0.76, 0.65), rough=0.5)

student_positions = [
    (-1.4, -0.10), (1.4, -0.10),
    (-1.4, 1.70), (0.0, 1.70), (1.4, 1.70),
    (-1.4, 3.50), (0.0, 3.50), (1.4, 3.50),
    (-1.4, 5.30), (1.4, 5.30),
]
for idx, (sx, sy) in enumerate(student_positions):
    s_torso = prim('cube', name=f"Student_Torso_{idx}", scale=(0.38, 0.22, 0.45), loc=(sx, sy + 0.30, 0.20), coll=C)
    s_torso.data.materials.append(mat_student_body)
    s_head = prim('sphere', name=f"Student_Head_{idx}", r=0.12, loc=(sx, sy + 0.30, 0.70), coll=C)
    s_head.data.materials.append(mat_student_head)

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
