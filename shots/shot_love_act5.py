"""
shot_love_act5.py (LOVE_05: The Twist & Secret Smirk)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: Climax reveal. 10th-class heroine tilts her head, glances knowingly
toward the front bench reflection, breaking into a sweet, playful smirk!
Uses real 3D rigged teenage student character mesh (heroine_girl.glb).
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
import spiderverse
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.15, look='AgX - Punchy')
compositor(bloom=0.35, threshold=0.92, bloom_size=0.55, dispersion=0.014)

# Golden hour classroom atmosphere
w = world_color((0.15, 0.17, 0.22))
add_world_fog(w, density=0.004, color=(0.98, 0.80, 0.50), anisotropy=0.72)

C = collection("SET_LOVE_05")

# Materials
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.58, 0.36, 0.20), rough=0.30)
mat_sun_spark = mat_emission("Mat_SunSpark", color=(1.0, 0.92, 0.65), strength=12.0)
mat_title_gold = mat_emission("Mat_TitleGold", color=(1.0, 0.82, 0.30), strength=15.0)

# Floor
floor = prim('cube', name="Floor", scale=(6.0, 10.0, 0.1), loc=(0, 2.0, -0.6), coll=C)
floor.data.materials.append(mat_desk_wood)

# Desk
desk = prim('cube', name="Desk", scale=(1.3, 0.60, 0.04), loc=(0, -0.15, 0.55), coll=C)
desk.data.materials.append(mat_desk_wood)

# IMPORT REAL 3D RIGGED 10TH-CLASS TEENAGE GIRL
char_path = os.path.join(FILM, "assets", "characters", "heroine_girl.glb")
bpy.ops.import_scene.gltf(filepath=char_path)

girl_armature = bpy.data.objects.get("Armature")
if girl_armature:
    girl_armature.location = Vector((0.0, 0.28, -0.40))
    girl_armature.rotation_euler = Euler((0, 0, math.radians(180)), 'XYZ')
    
    # Animate living playful head tilt and knowing smirk
    bpy.context.view_layer.objects.active = girl_armature
    bpy.ops.object.mode_set(mode='POSE')
    ghead = girl_armature.pose.bones.get("J_Bip_C_Head")
    if ghead:
        ghead.rotation_mode = 'XYZ'
        ghead.rotation_euler = Euler((0, 0, 0))
        ghead.keyframe_insert("rotation_euler", frame=1)
        ghead.rotation_euler = Euler((math.radians(6), math.radians(14), math.radians(-8)))
        ghead.keyframe_insert("rotation_euler", frame=36)
        ghead.rotation_euler = Euler((math.radians(8), math.radians(18), math.radians(-10)))
        ghead.keyframe_insert("rotation_euler", frame=72)
    bpy.ops.object.mode_set(mode='OBJECT')

# Spider-Verse Comic Ink Outlines & Psychological Blendshapes (The Reveal Smirk)
girl_face = bpy.data.objects.get("Face (merged)(Clone)")
girl_body = bpy.data.objects.get("Body (merged)")
spiderverse.apply_comic_ink(girl_face, thickness=-0.003)
spiderverse.apply_comic_ink(girl_body, thickness=-0.003)
spiderverse.animate_heroine_girl_emotions(girl_face, girl_armature, shot_act=5)

# Focus target
girl_target = bpy.data.objects.new("GirlHeadTarget", None)
link(girl_target, C)
girl_target.location = Vector((0.0, 0.28, 0.86))

# Golden Sun Flare / Sparkle from the watch reflection
spark = prim('sphere', name="SunSpark", r=0.035, loc=(-0.14, -0.30, 0.82), coll=C)
spark.data.materials.append(mat_sun_spark)

for f in range(1, 73):
    p = 0.8 + 0.4 * math.sin(f * 0.3)
    spark.scale = Vector((p * 1.5, p * 0.25, p * 1.5))
    spark.keyframe_insert("scale", frame=f)

# Cinematic 3D Title Card in Upper Safe Zone
def make_title_text(text, name, loc, size=0.18, mat=mat_title_gold):
    t_data = bpy.data.curves.new(name=f"{name}_data", type='FONT')
    t_data.body = text
    t_data.size = size
    t_data.extrude = 0.02
    t_data.align_x = 'CENTER'
    t_data.align_y = 'CENTER'
    obj = bpy.data.objects.new(name, t_data)
    link(obj, C)
    obj.location = loc
    obj.rotation_euler = (math.radians(85), 0, 0)
    obj.data.materials.append(mat)
    return obj

title = make_title_text("SHE ALREADY KNEW.", "TitleCard", loc=Vector((0.0, -0.40, 1.35)), size=0.14, mat=mat_title_gold)

# Lighting: Warm Afternoon Romantic Sun
light(kind='SUN', name="Sun_Golden", rot=(math.radians(45), math.radians(-25), math.radians(65)),
      energy=7.5, color=(1.0, 0.85, 0.50), coll=C)
light(kind='SPOT', name="Spot_Beauty", loc=(-1.4, -1.6, 2.0),
      rot=(math.radians(45), 0, math.radians(-30)), energy=550.0, color=(1.0, 0.90, 0.78), spot=55.0, coll=C)
light(kind='AREA', name="Light_FillPink", loc=(1.6, -0.8, 1.6), energy=220.0,
      color=(1.0, 0.82, 0.90), coll=C)

# Camera: Push-in close-up on her playful knowing smirk
cam_start = Vector((0.0, -1.25, 1.10))
cam_mid   = Vector((0.0, -1.05, 1.02))
cam_end   = Vector((0.0, -0.88, 0.96))

cam = camera(name="Camera", loc=cam_start, target=girl_target, focus=girl_target, lens=48.0, fstop=3.5, coll=C)
track_to(cam, girl_target)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("LOVE_05")
