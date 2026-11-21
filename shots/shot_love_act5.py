"""
shot_love_act5.py (LOVE_05: The Twist & Secret Smirk)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: The climax reveal. The heroine looks up from her desk, notices the hero
staring into his watch reflection, and breaks into a sweet, playful knowing smirk!
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.15, look='AgX - Punchy')
compositor(bloom=0.35, threshold=0.95, bloom_size=0.5, dispersion=0.005)

# Golden hour classroom atmosphere
w = world_color((0.15, 0.17, 0.22))
add_world_fog(w, density=0.005, color=(0.98, 0.80, 0.50), anisotropy=0.72)

C = collection("SET_LOVE_05")
random.seed(505)

# Shaders
mat_skin_girl = mat_principled("Mat_SkinGirl", color=(0.96, 0.82, 0.72), rough=0.32)
mat_blush = mat_principled("Mat_Blush", color=(0.98, 0.52, 0.58), rough=0.35)
mat_hair_girl = mat_principled("Mat_HairGirl", color=(0.14, 0.08, 0.04), rough=0.26)
mat_eye_dark = mat_principled("Mat_EyeDark", color=(0.06, 0.06, 0.08), rough=0.15)
mat_eye_shine = mat_emission("Mat_EyeShine", color=(1.0, 1.0, 1.0), strength=5.0)
mat_mouth_smirk = mat_principled("Mat_Mouth", color=(0.82, 0.25, 0.32), rough=0.30)
mat_uniform_white = mat_principled("Mat_UniformWhite", color=(0.95, 0.95, 0.96), rough=0.45)
mat_ribbon_red = mat_principled("Mat_RibbonRed", color=(0.85, 0.15, 0.22), rough=0.35)
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.58, 0.36, 0.20), rough=0.30)
mat_sun_spark = mat_emission("Mat_SunSpark", color=(1.0, 0.92, 0.65), strength=12.0)
mat_title_gold = mat_emission("Mat_TitleGold", color=(1.0, 0.82, 0.30), strength=15.0)

# Classroom Floor & Back Wall
floor = prim('cube', name="Floor", scale=(5.0, 8.0, 0.1), loc=(0, 2.0, -0.6), coll=C)
floor.data.materials.append(mat_desk_wood)

# Desk
desk = prim('cube', name="Desk", scale=(1.2, 0.55, 0.04), loc=(0, -0.15, 0.55), coll=C)
desk.data.materials.append(mat_desk_wood)

# Heroine Anchor
girl_anchor = bpy.data.objects.new("GirlAnchor", None)
link(girl_anchor, C)
girl_anchor.location = Vector((0.0, 0.25, 0.6))

# Torso
torso = prim('cylinder', name="Girl_Torso", r=0.18, depth=0.55, loc=(0, 0, 0.0), coll=C)
torso.parent = girl_anchor
torso.data.materials.append(mat_uniform_white)

ribbon = prim('cube', name="Ribbon", scale=(0.08, 0.03, 0.10), loc=(0, -0.16, 0.22), coll=C)
ribbon.parent = girl_anchor
ribbon.data.materials.append(mat_ribbon_red)

# Head
head = prim('sphere', name="Girl_Head", r=0.16, loc=(0, 0, 0.46), coll=C)
head.parent = girl_anchor
head.data.materials.append(mat_skin_girl)

# Hair
hair_top = prim('sphere', name="Hair_Top", r=0.175, loc=(0, 0.02, 0.51), coll=C)
hair_top.parent = girl_anchor
hair_top.scale = Vector((1.05, 1.15, 0.88))
hair_top.data.materials.append(mat_hair_girl)

hair_side_l = prim('cylinder', name="Hair_SideL", r=0.06, depth=0.45, loc=(-0.16, 0.0, 0.32), coll=C)
hair_side_l.parent = girl_anchor
hair_side_l.data.materials.append(mat_hair_girl)

hair_side_r = prim('cylinder', name="Hair_SideR", r=0.06, depth=0.45, loc=(0.16, 0.0, 0.32), coll=C)
hair_side_r.parent = girl_anchor
hair_side_r.data.materials.append(mat_hair_girl)

# Eyes (Twinkling with amusement)
eye_l = prim('sphere', name="Eye_L", r=0.028, loc=(-0.055, -0.142, 0.47), coll=C)
eye_l.parent = girl_anchor
eye_l.data.materials.append(mat_eye_dark)

eye_r = prim('sphere', name="Eye_R", r=0.028, loc=(0.055, -0.142, 0.47), coll=C)
eye_r.parent = girl_anchor
eye_r.data.materials.append(mat_eye_dark)

gleam_l = prim('sphere', name="Gleam_L", r=0.010, loc=(-0.048, -0.164, 0.485), coll=C)
gleam_l.parent = girl_anchor
gleam_l.data.materials.append(mat_eye_shine)

gleam_r = prim('sphere', name="Gleam_R", r=0.010, loc=(0.062, -0.164, 0.485), coll=C)
gleam_r.parent = girl_anchor
gleam_r.data.materials.append(mat_eye_shine)

blush_l = prim('sphere', name="Blush_L", r=0.025, loc=(-0.09, -0.13, 0.43), coll=C)
blush_l.parent = girl_anchor
blush_l.data.materials.append(mat_blush)

blush_r = prim('sphere', name="Blush_R", r=0.025, loc=(0.09, -0.13, 0.43), coll=C)
blush_r.parent = girl_anchor
blush_r.data.materials.append(mat_blush)

# Sweet Knowing Smirk (Subtle tilted smile curve)
smirk = prim('cube', name="Smirk", scale=(0.04, 0.01, 0.012), loc=(0.015, -0.155, 0.39), coll=C)
smirk.parent = girl_anchor
smirk.rotation_euler = Euler((0, 0, math.radians(-14)), 'XYZ')
smirk.data.materials.append(mat_mouth_smirk)

# Expressive Acting: Starts looking down, then glances up playfully right at the watch angle
for f in range(1, 73):
    if f < 24:
        head.rotation_euler = Euler((math.radians(12), 0, math.radians(-4)), 'XYZ')
    else:
        t = min(1.0, (f - 24) / 24.0)
        pitch = math.radians(12 - 16 * t)
        yaw = math.radians(-4 + 10 * t)
        roll = math.radians(6 * math.sin(t * math.pi))
        head.rotation_euler = Euler((pitch, roll, yaw), 'XYZ')
    head.keyframe_insert("rotation_euler", frame=f)

# Sunlight Glint Sparkle from the watch reflection
spark = prim('sphere', name="SunSpark", r=0.04, loc=(-0.12, -0.5, 1.15), coll=C)
spark.data.materials.append(mat_sun_spark)

for f in range(1, 73):
    scale_pulse = 0.8 + 0.4 * math.sin(f * 0.25)
    spark.scale = Vector((scale_pulse * 1.6, scale_pulse * 0.2, scale_pulse * 1.6))
    spark.keyframe_insert("scale", frame=f)

# Cinematic 3D Title in safe zone
def make_title_text(text, name, loc, size=0.20, extrude=0.025, mat=mat_title_gold):
    t_data = bpy.data.curves.new(name=f"{name}_data", type='FONT')
    t_data.body = text
    t_data.size = size
    t_data.extrude = extrude
    t_data.align_x = 'CENTER'
    t_data.align_y = 'CENTER'
    obj = bpy.data.objects.new(name, t_data)
    link(obj, C)
    obj.location = loc
    obj.rotation_euler = (math.radians(85), 0, 0)
    obj.data.materials.append(mat)
    return obj

title = make_title_text("SHE ALREADY KNEW.", "TitleCard", loc=Vector((0.0, -0.5, 1.65)), size=0.18, mat=mat_title_gold)

# Lighting: Romantic Afternoon Sun
light(kind='SUN', name="Sun_Golden", rot=(math.radians(45), math.radians(-25), math.radians(65)),
      energy=7.5, color=(1.0, 0.85, 0.50), coll=C)
light(kind='SPOT', name="Spot_Beauty", loc=(-1.4, -1.4, 1.8),
      rot=(math.radians(45), 0, math.radians(-30)), energy=550.0, color=(1.0, 0.90, 0.75), spot=55.0, coll=C)
light(kind='AREA', name="Light_FillPink", loc=(1.6, -0.8, 1.4), energy=220.0,
      color=(1.0, 0.82, 0.90), coll=C)

# Camera: Romantic push-in on her playful smirk
cam_start = Vector((0.0, -1.80, 1.25))
cam_mid   = Vector((0.0, -1.50, 1.20))
cam_end   = Vector((0.0, -1.25, 1.15))

cam = camera(name="Camera", loc=cam_start, target=head, focus=head, lens=45.0, fstop=3.5, coll=C)
track_to(cam, head)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("LOVE_05")
