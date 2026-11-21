"""
shot_love_act4.py (LOVE_04: The Stolen Gaze)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: Cinematic portrait of the heroine seated 3 rows behind the hero.
Soft afternoon sunlight illuminates her hair while she twirls her golden pen.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.15, look='AgX - Punchy')
compositor(bloom=0.25, threshold=0.95, bloom_size=0.45, dispersion=0.004)

# Warm daylight classroom
w = world_color((0.14, 0.16, 0.20))
add_world_fog(w, density=0.004, color=(0.96, 0.78, 0.45), anisotropy=0.70)

C = collection("SET_LOVE_04")
random.seed(504)

# Shaders
mat_skin_girl = mat_principled("Mat_SkinGirl", color=(0.96, 0.82, 0.72), rough=0.32)
mat_blush = mat_principled("Mat_Blush", color=(0.95, 0.55, 0.60), rough=0.40)
mat_hair_girl = mat_principled("Mat_HairGirl", color=(0.14, 0.08, 0.04), rough=0.26)
mat_eye_dark = mat_principled("Mat_EyeDark", color=(0.06, 0.06, 0.08), rough=0.15)
mat_eye_shine = mat_emission("Mat_EyeShine", color=(1.0, 1.0, 1.0), strength=4.0)
mat_uniform_white = mat_principled("Mat_UniformWhite", color=(0.95, 0.95, 0.96), rough=0.45)
mat_ribbon_red = mat_principled("Mat_RibbonRed", color=(0.85, 0.15, 0.22), rough=0.35)
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.58, 0.36, 0.20), rough=0.30)
mat_pen_gold = mat_metal("Mat_PenGold", base=(1.0, 0.82, 0.35), rough=(0.10, 0.22))
mat_wall = mat_principled("Mat_Wall", color=(0.88, 0.86, 0.80), rough=0.60)

# Classroom Floor & Back Wall
floor = prim('cube', name="Floor", scale=(5.0, 8.0, 0.1), loc=(0, 2.0, -0.6), coll=C)
floor.data.materials.append(mat_desk_wood)

wall = prim('cube', name="Wall", scale=(5.0, 0.1, 3.0), loc=(0, 7.0, 1.5), coll=C)
wall.data.materials.append(mat_wall)

# Heroine's Desk
desk = prim('cube', name="GirlDesk", scale=(1.2, 0.55, 0.04), loc=(0, -0.15, 0.55), coll=C)
desk.data.materials.append(mat_desk_wood)

# Heroine Character Anchor
girl_anchor = bpy.data.objects.new("GirlAnchor", None)
link(girl_anchor, C)
girl_anchor.location = Vector((0.0, 0.25, 0.6))

# Torso (White school uniform blouse)
torso = prim('cylinder', name="Girl_Torso", r=0.18, depth=0.55, loc=(0, 0, 0.0), coll=C)
torso.parent = girl_anchor
torso.data.materials.append(mat_uniform_white)

# Red Sailor Collar / Ribbon
ribbon = prim('cube', name="Ribbon", scale=(0.08, 0.03, 0.10), loc=(0, -0.16, 0.22), coll=C)
ribbon.parent = girl_anchor
ribbon.data.materials.append(mat_ribbon_red)

# Stylized Head
head = prim('sphere', name="Girl_Head", r=0.16, loc=(0, 0, 0.46), coll=C)
head.parent = girl_anchor
head.data.materials.append(mat_skin_girl)

# Flowing Stylized Hair
hair_top = prim('sphere', name="Hair_Top", r=0.175, loc=(0, 0.02, 0.51), coll=C)
hair_top.parent = girl_anchor
hair_top.scale = Vector((1.05, 1.15, 0.88))
hair_top.data.materials.append(mat_hair_girl)

# Hair back/sides
hair_side_l = prim('cylinder', name="Hair_SideL", r=0.06, depth=0.45, loc=(-0.16, 0.0, 0.32), coll=C)
hair_side_l.parent = girl_anchor
hair_side_l.data.materials.append(mat_hair_girl)

hair_side_r = prim('cylinder', name="Hair_SideR", r=0.06, depth=0.45, loc=(0.16, 0.0, 0.32), coll=C)
hair_side_r.parent = girl_anchor
hair_side_r.data.materials.append(mat_hair_girl)

# Expressive Anime Cartoon Eyes
eye_l = prim('sphere', name="Eye_L", r=0.028, loc=(-0.055, -0.142, 0.47), coll=C)
eye_l.parent = girl_anchor
eye_l.data.materials.append(mat_eye_dark)

eye_r = prim('sphere', name="Eye_R", r=0.028, loc=(0.055, -0.142, 0.47), coll=C)
eye_r.parent = girl_anchor
eye_r.data.materials.append(mat_eye_dark)

# Eye highlights (bright anime gleam)
gleam_l = prim('sphere', name="Gleam_L", r=0.009, loc=(-0.048, -0.164, 0.485), coll=C)
gleam_l.parent = girl_anchor
gleam_l.data.materials.append(mat_eye_shine)

gleam_r = prim('sphere', name="Gleam_R", r=0.009, loc=(0.062, -0.164, 0.485), coll=C)
gleam_r.parent = girl_anchor
gleam_r.data.materials.append(mat_eye_shine)

# Cute Blushing Cheeks
blush_l = prim('sphere', name="Blush_L", r=0.022, loc=(-0.09, -0.13, 0.43), coll=C)
blush_l.parent = girl_anchor
blush_l.data.materials.append(mat_blush)

blush_r = prim('sphere', name="Blush_R", r=0.022, loc=(0.09, -0.13, 0.43), coll=C)
blush_r.parent = girl_anchor
blush_r.data.materials.append(mat_blush)

# Hand & Pen (Twirling on desk)
hand = prim('sphere', name="Girl_Hand", r=0.055, loc=(0.18, -0.22, 0.02), coll=C)
hand.parent = girl_anchor
hand.data.materials.append(mat_skin_girl)

pen = prim('cylinder', name="Girl_Pen", r=0.012, depth=0.26, loc=(0.18, -0.22, 0.06), coll=C)
pen.parent = girl_anchor
pen.rotation_euler = Euler((math.radians(35), math.radians(20), 0), 'XYZ')
pen.data.materials.append(mat_pen_gold)

# Pen twirling and head breathing animation
for f in range(1, 73):
    pen.rotation_euler.rotate(Euler((0, 0, 0.10), 'XYZ'))
    pen.keyframe_insert("rotation_euler", frame=f)
    
    subtle_tilt = math.sin(f * 0.12) * 0.03
    head.rotation_euler = Euler((math.radians(4), subtle_tilt, math.radians(-5)), 'XYZ')
    head.keyframe_insert("rotation_euler", frame=f)

# Other students blurred in background
for row in [1, 2]:
    for col in [-1.2, 1.2]:
        bg_torso = prim('cylinder', name=f"BG_Torso_{row}_{col}", r=0.16, depth=0.45, loc=(col, 0.3 + row * 1.5, 0.6), coll=C)
        bg_torso.data.materials.append(mat_uniform_white)

# Lighting: Warm Golden Sunlight rim on hair + soft beauty key
light(kind='SUN', name="Sun_GoldenHair", rot=(math.radians(45), math.radians(-25), math.radians(65)),
      energy=7.0, color=(1.0, 0.85, 0.50), coll=C)
light(kind='SPOT', name="Spot_BeautyKey", loc=(-1.4, -1.4, 1.8),
      rot=(math.radians(45), 0, math.radians(-30)), energy=500.0, color=(1.0, 0.90, 0.75), spot=55.0, coll=C)
light(kind='AREA', name="Light_FillSoft", loc=(1.6, -0.8, 1.4), energy=200.0,
      color=(0.95, 0.80, 0.88), coll=C)

# Camera: Front Portrait Medium Close-Up (9:16 Vertical)
cam_start = Vector((0.0, -1.80, 1.25))
cam_mid   = Vector((0.0, -1.50, 1.20))
cam_end   = Vector((0.0, -1.30, 1.15))

cam = camera(name="Camera", loc=cam_start, target=head, focus=head, lens=45.0, fstop=3.5, coll=C)
track_to(cam, head)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("LOVE_04")
