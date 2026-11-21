"""
shot_love_act3.py (LOVE_03: The Wristwatch Reflection)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: Macro shot of the wristwatch on the hero's desk.
The curved crystal catches window sunlight and reflects the EXACT 3D heroine girl (heroine_girl.glb).
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.15, look='AgX - Punchy')
compositor(bloom=0.35, threshold=0.96, bloom_size=0.5, dispersion=0.005)

w = world_color((0.15, 0.17, 0.22))
add_world_fog(w, density=0.004, color=(0.96, 0.80, 0.50), anisotropy=0.72)

C = collection("SET_LOVE_03")

# Shaders
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.52, 0.32, 0.18), rough=0.32)
mat_steel = mat_metal("Mat_Steel", base=(0.90, 0.92, 0.96), rough=(0.08, 0.15))
mat_gold = mat_metal("Mat_Gold", base=(1.0, 0.82, 0.35), rough=(0.10, 0.20))
mat_dial = mat_principled("Mat_Dial", color=(0.06, 0.08, 0.12), rough=0.25)
mat_strap = mat_principled("Mat_Strap", color=(0.15, 0.08, 0.05), rough=0.45)

# Desk Plane
desk = prim('cube', name="Desk", scale=(2.0, 2.0, 0.04), loc=(0, 0, 0.0), coll=C)
desk.data.materials.append(mat_desk_wood)

# Watch Assembly
watch = bpy.data.objects.new("Watch", None)
link(watch, C)
watch.location = Vector((0.0, 0.0, 0.08))

# Watch Strap
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

# IMPORT EXACT 3D HEROINE GIRL TO PROJECT REFLECTION ON WATCH
char_path = os.path.join(FILM, "assets", "characters", "heroine_girl.glb")
bpy.ops.import_scene.gltf(filepath=char_path)

girl_armature = bpy.data.objects.get("Armature")
if girl_armature:
    girl_armature.parent = watch
    girl_armature.scale = Vector((0.34, 0.34, 0.34))
    girl_armature.location = Vector((0.0, -0.15, 0.08))
    girl_armature.rotation_euler = Euler((math.radians(-90), 0, 0), 'XYZ')

# Watch tilts subtly to catch the window sunlight
for f in range(1, 73):
    tilt_x = math.radians(18 + math.sin(f * 0.08) * 3)
    tilt_y = math.radians(-8 + math.cos(f * 0.08) * 2)
    watch.rotation_euler = Euler((tilt_x, tilt_y, math.radians(12)), 'XYZ')
    watch.keyframe_insert("rotation_euler", frame=f)

# Lighting: Golden sunlight glinting off the watch
light(kind='SUN', name="Sun_Glint", rot=(math.radians(45), math.radians(-30), math.radians(60)),
      energy=7.5, color=(1.0, 0.88, 0.55), coll=C)
light(kind='SPOT', name="Spot_DialHighlight", loc=(-0.5, -0.8, 1.2),
      rot=(math.radians(50), 0, math.radians(-25)), energy=400.0, color=(1.0, 0.92, 0.70), spot=45.0, coll=C)
light(kind='AREA', name="Light_FillSoft", loc=(0.8, 0.5, 0.9), energy=160.0,
      color=(0.85, 0.90, 1.0), coll=C)

# Camera: High-Angle Macro Close-Up framing the watch & reflection in 9:16 vertical
cam_start = Vector((0.0, -1.05, 1.15))
cam_mid   = Vector((0.0, -0.88, 0.98))
cam_end   = Vector((0.0, -0.72, 0.84))

cam = camera(name="Camera", loc=cam_start, target=dial, focus=dial, lens=48.0, fstop=4.5, coll=C)
track_to(cam, dial)
cam.data.sensor_fit = 'VERTICAL'

cam_positions = [
    (1,  Vector((0.0, -1.05, 1.15))),
    (18, Vector((0.0, -0.96, 1.06))),
    (36, Vector((0.0, -0.88, 0.98))),
    (54, Vector((0.0, -0.80, 0.91))),
    (72, Vector((0.0, -0.72, 0.84))),
]
for f, pos in cam_positions:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("LOVE_03")
