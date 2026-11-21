"""
shot_love_act2.py (LOVE_02: The Dilemma)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: 10th-class hero boy seated at the front bench of a sunlit high-school classroom.
Tense expressions, eyes glancing, looking down at his desk and wristwatch.
Uses real 3D rigged teenage student character mesh (hero_boy.glb).
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
import spiderverse
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.15, look='AgX - Punchy')
compositor(bloom=0.28, threshold=0.94, bloom_size=0.50, dispersion=0.012)

# Classroom daylight atmosphere
w = world_color((0.15, 0.17, 0.22))
add_world_fog(w, density=0.003, color=(0.96, 0.80, 0.50), anisotropy=0.70)

C = collection("SET_LOVE_02")

# Classroom Environment Materials
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.58, 0.36, 0.20), rough=0.30)
mat_metal = mat_metal("Mat_Metal", base=(0.88, 0.90, 0.94), rough=(0.12, 0.20))
mat_wall = mat_principled("Mat_Wall", color=(0.90, 0.88, 0.84), rough=0.55)
mat_paper = mat_principled("Mat_Paper", color=(0.96, 0.96, 0.94), rough=0.40)

# Floor & Back Wall
floor = prim('cube', name="Floor", scale=(6.0, 10.0, 0.1), loc=(0, 2.0, -0.6), coll=C)
floor.data.materials.append(mat_desk_wood)

wall = prim('cube', name="Wall", scale=(6.0, 0.1, 4.0), loc=(0, 8.0, 1.8), coll=C)
wall.data.materials.append(mat_wall)

# Hero's Wooden Desk
desk = prim('cube', name="Desk", scale=(1.3, 0.60, 0.04), loc=(0, -0.15, 0.55), coll=C)
desk.data.materials.append(mat_desk_wood)

# Notebook & Pen on desk
nb = prim('cube', name="Notebook", scale=(0.35, 0.25, 0.015), loc=(-0.15, -0.15, 0.575), coll=C)
nb.rotation_euler = Euler((0, 0, math.radians(-10)), 'XYZ')
nb.data.materials.append(mat_paper)

# Steel Wristwatch on hero's desk
watch = prim('cylinder', name="Watch", r=0.045, depth=0.015, loc=(0.18, -0.22, 0.575), coll=C)
watch.rotation_euler = Euler((math.radians(20), math.radians(-15), math.radians(10)), 'XYZ')
watch.data.materials.append(mat_metal)

# IMPORT REAL 3D RIGGED 10TH-CLASS TEENAGE BOY
char_path = os.path.join(FILM, "assets", "characters", "hero_boy.glb")
bpy.ops.import_scene.gltf(filepath=char_path)

# Remove non-student accessories
for name in ['robo_arm', 'hair_tail']:
    o = bpy.data.objects.get(name)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)

# Position hero boy seated at the desk
boy_armature = bpy.data.objects.get("Armature")
if boy_armature:
    boy_armature.location = Vector((0.0, 0.28, -0.42))
    boy_armature.rotation_euler = Euler((0, 0, math.radians(180)), 'XYZ')
    
    # Animate living character motion: breathing + tense nervous glance down at wrist
    bpy.context.view_layer.objects.active = boy_armature
    bpy.ops.object.mode_set(mode='POSE')
    
    # Head glance
    h_bone = boy_armature.pose.bones.get("head 1")
    if h_bone:
        h_bone.rotation_mode = 'XYZ'
        h_bone.rotation_euler = Euler((0, 0, 0))
        h_bone.keyframe_insert("rotation_euler", frame=1)
        # Glances sideways/down towards his wrist
        h_bone.rotation_euler = Euler((math.radians(14), math.radians(-12), math.radians(-6)))
        h_bone.keyframe_insert("rotation_euler", frame=30)
        # Holds tense gaze
        h_bone.rotation_euler = Euler((math.radians(16), math.radians(-10), math.radians(-4)))
        h_bone.keyframe_insert("rotation_euler", frame=54)
        # Glances slightly up
        h_bone.rotation_euler = Euler((math.radians(8), math.radians(-4), 0))
        h_bone.keyframe_insert("rotation_euler", frame=72)
        
    # Subtle breathing motion on chest
    c_bone = boy_armature.pose.bones.get("chest")
    if c_bone:
        c_bone.rotation_mode = 'XYZ'
        for f in range(1, 73):
            b_rot = math.sin(f * 0.12) * math.radians(1.5)
            c_bone.rotation_euler = Euler((b_rot, 0, 0))
            c_bone.keyframe_insert("rotation_euler", frame=f)
            
    bpy.ops.object.mode_set(mode='OBJECT')

# Spider-Verse Comic Ink Outlines & Psychological Blendshapes
boy_head = bpy.data.objects.get("head")
boy_wear = bpy.data.objects.get("wear")
spiderverse.apply_comic_ink(boy_head, thickness=-0.003)
spiderverse.apply_comic_ink(boy_wear, thickness=-0.003)
spiderverse.animate_hero_boy_emotions(boy_head, boy_armature, shot_act=2)

# Head position is at Z = 1.05 when armature is at Z = -0.42
head_target = bpy.data.objects.new("HeadTarget", None)
link(head_target, C)
head_target.location = Vector((0.0, 0.28, 1.05))

# Lighting: Warm golden afternoon sunlight through left window + soft beauty fill
light(kind='SUN', name="Sun_Golden", rot=(math.radians(45), math.radians(-25), math.radians(65)),
      energy=7.0, color=(1.0, 0.86, 0.52), coll=C)
light(kind='SPOT', name="Spot_HeroFill", loc=(-1.4, -1.6, 2.0),
      rot=(math.radians(45), 0, math.radians(-30)), energy=450.0, color=(1.0, 0.90, 0.72), spot=55.0, coll=C)
light(kind='AREA', name="Light_FillSoft", loc=(1.6, -0.8, 1.6), energy=180.0,
      color=(0.80, 0.88, 1.0), coll=C)

# Camera: Front Cinematic Portrait (9:16 Vertical Framing)
cam_start = Vector((0.0, -1.25, 1.25))
cam_mid   = Vector((0.0, -1.05, 1.18))
cam_end   = Vector((0.0, -0.90, 1.12))

cam = camera(name="Camera", loc=cam_start, target=head_target, focus=head_target, lens=48.0, fstop=3.5, coll=C)
track_to(cam, head_target)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("LOVE_02")
