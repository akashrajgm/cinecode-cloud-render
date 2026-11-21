"""
shot_love_act4.py (LOVE_04: The Stolen Gaze)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: Cinematic portrait of the 10th-class heroine girl seated 3 rows behind the hero.
Soft afternoon sunlight backlights her hair, pen twirling on her desk, soft romantic gaze.
Uses real 3D rigged teenage student character mesh (heroine_girl.glb).
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
import spiderverse
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.15, look='AgX - Punchy')
compositor(bloom=0.28, threshold=0.94, bloom_size=0.50, dispersion=0.012)

# Classroom afternoon atmosphere
w = world_color((0.15, 0.17, 0.22))
add_world_fog(w, density=0.003, color=(0.96, 0.80, 0.50), anisotropy=0.70)

C = collection("SET_LOVE_04")

# Materials
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.58, 0.36, 0.20), rough=0.30)
mat_wall = mat_principled("Mat_Wall", color=(0.90, 0.88, 0.84), rough=0.55)
mat_pen_gold = mat_metal("Mat_PenGold", base=(1.0, 0.82, 0.35), rough=(0.10, 0.22))

# Floor & Back Wall
floor = prim('cube', name="Floor", scale=(6.0, 10.0, 0.1), loc=(0, 2.0, -0.6), coll=C)
floor.data.materials.append(mat_desk_wood)

wall = prim('cube', name="Wall", scale=(6.0, 0.1, 4.0), loc=(0, 8.0, 1.8), coll=C)
wall.data.materials.append(mat_wall)

# Heroine's Desk
desk = prim('cube', name="Desk", scale=(1.3, 0.60, 0.04), loc=(0, -0.15, 0.55), coll=C)
desk.data.materials.append(mat_desk_wood)

# Golden Pen on desk (twirling)
pen = prim('cylinder', name="Girl_Pen", r=0.012, depth=0.26, loc=(0.20, -0.18, 0.58), coll=C)
pen.rotation_euler = Euler((math.radians(35), math.radians(20), 0), 'XYZ')
pen.data.materials.append(mat_pen_gold)

# Pen twirling animation
for f in range(1, 73):
    rot_z = math.radians(f * 18.0)
    pen.rotation_euler = Euler((math.radians(35), math.radians(20), rot_z), 'XYZ')
    pen.keyframe_insert("rotation_euler", frame=f)

# IMPORT REAL 3D RIGGED 10TH-CLASS TEENAGE GIRL
char_path = os.path.join(FILM, "assets", "characters", "heroine_girl.glb")
bpy.ops.import_scene.gltf(filepath=char_path)

# Position heroine seated at her desk
girl_armature = bpy.data.objects.get("Armature")
if girl_armature:
    girl_armature.location = Vector((0.0, 0.28, -0.40))
    girl_armature.rotation_euler = Euler((0, 0, math.radians(180)), 'XYZ')
    
    # Animate living character head tilt & gentle posture
    bpy.context.view_layer.objects.active = girl_armature
    bpy.ops.object.mode_set(mode='POSE')
    ghead = girl_armature.pose.bones.get("J_Bip_C_Head")
    if ghead:
        ghead.rotation_mode = 'XYZ'
        ghead.rotation_euler = Euler((0, 0, 0))
        ghead.keyframe_insert("rotation_euler", frame=1)
        ghead.rotation_euler = Euler((math.radians(4), math.radians(-10), math.radians(6)))
        ghead.keyframe_insert("rotation_euler", frame=36)
        ghead.rotation_euler = Euler((math.radians(2), math.radians(-5), math.radians(2)))
        ghead.keyframe_insert("rotation_euler", frame=72)
    bpy.ops.object.mode_set(mode='OBJECT')

# Spider-Verse Comic Ink Outlines & Psychological Blendshapes
girl_face = bpy.data.objects.get("Face (merged)(Clone)")
girl_body = bpy.data.objects.get("Body (merged)")
spiderverse.apply_comic_ink(girl_face, thickness=-0.003)
spiderverse.apply_comic_ink(girl_body, thickness=-0.003)
spiderverse.animate_heroine_girl_emotions(girl_face, girl_armature, shot_act=4)

# Girl's face focus target
girl_target = bpy.data.objects.new("GirlHeadTarget", None)
link(girl_target, C)
girl_target.location = Vector((0.0, 0.28, 0.86))

# Lighting: Warm golden sunlight rimming her hair + soft beauty key
light(kind='SUN', name="Sun_GoldenHair", rot=(math.radians(45), math.radians(-25), math.radians(65)),
      energy=7.5, color=(1.0, 0.85, 0.50), coll=C)
light(kind='SPOT', name="Spot_BeautyKey", loc=(-1.4, -1.6, 2.0),
      rot=(math.radians(45), 0, math.radians(-30)), energy=500.0, color=(1.0, 0.90, 0.78), spot=55.0, coll=C)
light(kind='AREA', name="Light_FillSoft", loc=(1.6, -0.8, 1.6), energy=200.0,
      color=(0.95, 0.82, 0.90), coll=C)

# Camera: Parallax Arc Cinematic Dolly (9:16 Vertical)
cam_positions = [
    (1,  Vector((-0.18, -1.25, 1.10))),
    (18, Vector((-0.09, -1.15, 1.05))),
    (36, Vector((0.00,  -1.05, 1.02))),
    (54, Vector((0.08,  -0.96, 0.98))),
    (72, Vector((0.15,  -0.88, 0.95))),
]

cam = camera(name="Camera", loc=cam_positions[0][1], target=girl_target, focus=girl_target, lens=48.0, fstop=3.5, coll=C)
track_to(cam, girl_target)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in cam_positions:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("LOVE_04")
