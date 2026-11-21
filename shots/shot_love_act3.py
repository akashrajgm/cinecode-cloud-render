"""
shot_love_act3.py (LOVE_03: The Wristwatch Reflection)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: Hero places his metal wristwatch on the desk at an angle.
The curved crystal catches the sunlight, reflecting the girl seated 3 rows behind him!
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.12, look='AgX - Punchy')
compositor(bloom=0.35, threshold=0.96, bloom_size=0.5, dispersion=0.005)

w = world_color((0.12, 0.14, 0.18))
add_world_fog(w, density=0.005, color=(0.96, 0.76, 0.40), anisotropy=0.72)

C = collection("SET_LOVE_03")

# Shaders
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.52, 0.32, 0.18), rough=0.32)
mat_steel = mat_metal("Mat_Steel", base=(0.90, 0.92, 0.96), rough=(0.08, 0.15))
mat_gold = mat_metal("Mat_Gold", base=(1.0, 0.82, 0.35), rough=(0.10, 0.20))
mat_dial = mat_principled("Mat_Dial", color=(0.06, 0.08, 0.12), rough=0.25)
mat_strap = mat_principled("Mat_Strap", color=(0.15, 0.08, 0.05), rough=0.45)
mat_skin_girl = mat_principled("Mat_SkinGirl", color=(0.96, 0.80, 0.70), rough=0.25, emit=(0.95, 0.78, 0.65), emit_strength=0.8)
mat_hair_girl = mat_principled("Mat_HairGirl", color=(0.14, 0.07, 0.04), rough=0.25)
mat_eye_girl = mat_principled("Mat_EyeGirl", color=(0.10, 0.18, 0.28), rough=0.1)

# Desk Plane
desk = prim('cube', name="Desk", scale=(2.0, 2.0, 0.04), loc=(0, 0, 0.0), coll=C)
desk.data.materials.append(mat_desk_wood)

# Watch Assembly
watch = bpy.data.objects.new("Watch", None)
link(watch, C)
watch.location = Vector((0.0, 0.0, 0.08))

# Watch Strap (leather band stretching across desk)
strap = prim('cube', name="Strap", scale=(0.22, 1.2, 0.02), loc=(0, 0, 0.01), coll=C)
strap.parent = watch
strap.data.materials.append(mat_strap)

# Steel Case Bezel
case = prim('cylinder', name="Case", r=0.28, depth=0.06, segments=64, loc=(0, 0, 0.04), coll=C)
case.parent = watch
case.data.materials.append(mat_steel)

# Dial Face
dial = prim('cylinder', name="Dial", r=0.25, depth=0.015, segments=48, loc=(0, 0, 0.065), coll=C)
dial.parent = watch
dial.data.materials.append(mat_dial)

# Watch Hands (Gold)
hand_h = prim('cube', name="HandH", scale=(0.015, 0.10, 0.005), loc=(0, 0.04, 0.075), coll=C)
hand_h.parent = watch
hand_h.rotation_euler = Euler((0, 0, math.radians(45)), 'XYZ')
hand_h.data.materials.append(mat_gold)

hand_m = prim('cube', name="HandM", scale=(0.012, 0.16, 0.005), loc=(0, -0.06, 0.076), coll=C)
hand_m.parent = watch
hand_m.rotation_euler = Euler((0, 0, math.radians(-70)), 'XYZ')
hand_m.data.materials.append(mat_gold)

# The Heroine's 3D Reflection on the Watch Face!
ref = bpy.data.objects.new("GirlReflection", None)
link(ref, C)
ref.parent = watch
ref.location = Vector((0.0, 0.02, 0.08))

# Girl's face visible in the reflection
ref_face = prim('sphere', name="Ref_Face", r=0.11, loc=(0, 0, 0.0), coll=C)
ref_face.parent = ref
ref_face.scale = Vector((1.0, 0.9, 0.15)) # Flat projected onto watch
ref_face.data.materials.append(mat_skin_girl)

# Girl's hair framing the reflection
ref_hair = prim('sphere', name="Ref_Hair", r=0.125, loc=(0, 0.03, 0.01), coll=C)
ref_hair.parent = ref
ref_hair.scale = Vector((1.05, 1.1, 0.16))
ref_hair.data.materials.append(mat_hair_girl)

# Girl's eyes in reflection
eye_l = prim('sphere', name="Ref_EyeL", r=0.018, loc=(-0.038, -0.015, 0.02), coll=C)
eye_l.parent = ref
eye_l.data.materials.append(mat_eye_girl)

eye_r = prim('sphere', name="Ref_EyeR", r=0.018, loc=(0.038, -0.015, 0.02), coll=C)
eye_r.parent = ref
eye_r.data.materials.append(mat_eye_girl)

# Watch tilts subtly to catch the angle
for f in range(1, 73):
    tilt_x = math.radians(22 + math.sin(f * 0.08) * 4)
    tilt_y = math.radians(-10 + math.cos(f * 0.08) * 3)
    watch.rotation_euler = Euler((tilt_x, tilt_y, math.radians(15)), 'XYZ')
    watch.keyframe_insert("rotation_euler", frame=f)

# Cinematic Lighting: Golden sunlight glinting off watch glass
light(kind='SUN', name="Sun_Glint", rot=(math.radians(45), math.radians(-30), math.radians(60)),
      energy=7.5, color=(1.0, 0.88, 0.55), coll=C)
light(kind='SPOT', name="Spot_DialHighlight", loc=(-0.5, -0.8, 1.2),
      rot=(math.radians(50), 0, math.radians(-25)), energy=350.0, color=(1.0, 0.92, 0.70), spot=45.0, coll=C)
light(kind='AREA', name="Light_FillSoft", loc=(0.8, 0.5, 0.9), energy=140.0,
      color=(0.80, 0.88, 1.0), coll=C)

# Camera: High-Angle Macro Close-Up framing the watch & reflection perfectly in 9:16 vertical
cam_start = Vector((0.0, -1.15, 1.30))
cam_mid   = Vector((0.0, -0.95, 1.10))
cam_end   = Vector((0.0, -0.80, 0.95))

cam = camera(name="Camera", loc=cam_start, target=dial, focus=dial, lens=48.0, fstop=4.5, coll=C)
track_to(cam, dial)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("LOVE_03")
