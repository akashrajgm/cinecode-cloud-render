"""
shot_love_act5.py (LOVE_05: The Twist & Secret Smirk)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: The climax reveal. Heroine looks up slightly towards the front bench,
notices the glint of his watch glass, and breaks into a sweet, knowing smile.
Hero in the foreground subtly smiles down at his watch in golden sunlight.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.12, look='AgX - Punchy')
compositor(bloom=0.48, threshold=0.98, bloom_size=0.6, dispersion=0.007)

w = world_color((0.002, 0.003, 0.006))
add_world_fog(w, density=0.007, color=(0.98, 0.76, 0.42), anisotropy=0.75)

C = collection("SET_LOVE_05")
random.seed(505)

# Stylized Shaders
mat_skin_girl = mat_principled("Mat_SkinGirl", color=(0.96, 0.80, 0.70), rough=0.28)
mat_hair_girl = mat_principled("Mat_HairGirl", color=(0.14, 0.07, 0.03), rough=0.22)
mat_uniform_white = mat_principled("Mat_UniformWhite", color=(0.94, 0.96, 0.98), rough=0.50)
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.48, 0.28, 0.14), rough=0.35)
mat_sun_flare = mat_emission("Mat_SunFlare", color=(1.0, 0.88, 0.55), strength=14.0)
mat_text_gold = mat_emission("Mat_TextGold", color=(1.0, 0.78, 0.25), strength=14.0)

# Focal anchor shifted up for 9:16 vertical safe zone
FOCAL_LOC = Vector((0.0, 0.0, 0.6))

# Desk Surface
desk = prim('cube', name="ClimaxDesk", scale=(1.4, 0.7, 0.05), loc=(0, 0, FOCAL_LOC.z - 0.22), coll=C)
desk.data.materials.append(mat_desk_wood)

# Heroine Rig (Seated, leaning forward slightly)
girl_rig = bpy.data.objects.new("HeroineRig", None)
link(girl_rig, C)
girl_rig.location = Vector((0.0, 0.35, FOCAL_LOC.z))

# Torso
torso = prim('cylinder', name="Girl_Torso", r=0.20, depth=0.55, loc=(0, 0, 0), coll=C)
torso.parent = girl_rig
torso.data.materials.append(mat_uniform_white)

# Stylized Head (Looking up, head tilted with a charming knowing smile)
head = prim('sphere', name="Girl_Head", r=0.175, loc=(0, 0, 0.44), coll=C)
head.parent = girl_rig
head.data.materials.append(mat_skin_girl)

# Flowing Long Hair
hair = prim('sphere', name="Girl_Hair", r=0.19, loc=(0, 0.03, 0.48), coll=C)
hair.parent = girl_rig
hair.scale = Vector((1.1, 1.25, 0.95))
hair.data.materials.append(mat_hair_girl)

# Expressive Stylized Smirk Animation:
# She starts looking down at notebook, then looks up at frame 24, smiling at frame 48
head.rotation_euler = Euler((math.radians(18), 0, 0), 'XYZ')
head.keyframe_insert("rotation_euler", frame=1)

head.rotation_euler = Euler((math.radians(4), math.radians(5), math.radians(-8)), 'XYZ')
head.keyframe_insert("rotation_euler", frame=36)

head.rotation_euler = Euler((math.radians(-2), math.radians(4), math.radians(-6)), 'XYZ')
head.keyframe_insert("rotation_euler", frame=72)

# Golden Lens Flare Burst (The sunlight flashing off the watch into her eyes)
flare = prim('sphere', name="SunGlintBurst", r=0.08, loc=(-0.15, -0.25, FOCAL_LOC.z + 0.35), coll=C)
flare.data.materials.append(mat_sun_flare)

# Flare pulse
for f in range(1, 73):
    p = 1.0 + 0.25 * math.sin(f * 0.3)
    flare.scale = Vector((p * 1.5, p * 0.4, p * 1.5))
    flare.keyframe_insert("scale", frame=f)

# Cinematic 3D Romantic Title Card in Upper Safe Zone (Z = 1.45, Y: 28%-36% screen space)
def make_title_text(text, name, loc, size=0.24, extrude=0.03, mat=mat_text_gold):
    t_data = bpy.data.curves.new(name=f"{name}_data", type='FONT')
    t_data.body = text
    t_data.size = size
    t_data.extrude = extrude
    t_data.align_x = 'CENTER'
    t_data.align_y = 'CENTER'
    obj = bpy.data.objects.new(name, t_data)
    link(obj, C)
    obj.location = loc
    obj.rotation_euler = (math.radians(90), 0, 0)
    obj.data.materials.append(mat)
    return obj

title = make_title_text("THE SECRET REFLECTION.", "Text_Title", loc=Vector((0.0, 1.2, FOCAL_LOC.z + 0.95)), size=0.22, extrude=0.03, mat=mat_text_gold)

# Cinematic Lighting: Romantic Golden Hour Sunlight + Soft Beauty Glow
light(kind='SUN', name="Sun_GoldenClimax", rot=(math.radians(35), math.radians(-20), math.radians(60)),
      energy=9.0, color=(1.0, 0.85, 0.48), coll=C)
light(kind='SPOT', name="Spot_HeroineBeauty", loc=(-1.4, -1.0, FOCAL_LOC.z + 1.2),
      rot=(math.radians(48), 0, math.radians(-30)), energy=750.0, color=(1.0, 0.92, 0.82), spot=60.0, coll=C)
light(kind='POINT', name="Light_RomanticFill", loc=(1.5, 0.5, FOCAL_LOC.z + 0.9), energy=320.0,
      color=(1.0, 0.75, 0.85), coll=C)

# Camera: Slow romantic dolly-in closing on her playful secret smirk
cam_start = Vector((0.0, -1.9, FOCAL_LOC.z + 0.65))
cam_mid   = Vector((0.05, -1.45, FOCAL_LOC.z + 0.52))
cam_end   = Vector((0.02, -1.05, FOCAL_LOC.z + 0.44))

cam = camera(name="Camera", loc=cam_start, target=head, lens=68.0, fstop=1.8, coll=C)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("LOVE_05")
