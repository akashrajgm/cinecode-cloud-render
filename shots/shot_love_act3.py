"""
shot_love_act3.py (LOVE_03: The Wristwatch Reflection)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: Extreme macro cinema on the metal wristwatch resting on wooden desk.
Curved sapphire crystal catches golden window sunlight and reveals the girl's reflection.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.10, look='AgX - Punchy')
compositor(bloom=0.45, threshold=0.98, bloom_size=0.55, dispersion=0.007)

w = world_color((0.002, 0.003, 0.006))
add_world_fog(w, density=0.008, color=(0.96, 0.75, 0.38), anisotropy=0.75)

C = collection("SET_LOVE_03")

# Stylized Shaders
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.42, 0.24, 0.12), rough=0.28)
mat_watch_case = mat_metal("Mat_WatchCase", base=(0.92, 0.94, 0.98), rough=(0.08, 0.18))
mat_watch_dial = mat_principled("Mat_WatchDial", color=(0.08, 0.10, 0.14), metal=0.5, rough=0.3)
mat_watch_glass = mat_glass("Mat_SapphireGlass", tint=(0.95, 0.98, 1.0), rough=0.01, ior=1.52)
mat_girl_reflection = mat_principled("Mat_GirlReflection", color=(0.95, 0.78, 0.68), rough=0.2,
                                     emit=(1.0, 0.82, 0.55), emit_strength=1.8)
mat_girl_hair_ref = mat_principled("Mat_GirlHairRef", color=(0.14, 0.07, 0.03), rough=0.25)
mat_sun_glint = mat_emission("Mat_SunGlint", color=(1.0, 0.95, 0.75), strength=18.0)

# Focal anchor shifted up for 9:16 vertical safe zone
FOCAL_LOC = Vector((0.0, 0.0, 0.6))

# Wooden Desk macro plane
desk = prim('cube', name="DeskPlane", scale=(2.5, 2.5, 0.05), loc=(0, 0, FOCAL_LOC.z - 0.25), coll=C)
desk.data.materials.append(mat_desk_wood)

# 1. Stylized Wristwatch Assembly
watch_rig = bpy.data.objects.new("WatchRig", None)
link(watch_rig, C)
watch_rig.location = FOCAL_LOC

# Steel Watch Case Bezel
case = prim('cylinder', name="WatchCase", r=0.48, depth=0.12, segments=64, loc=(0, 0, 0), coll=C)
case.parent = watch_rig
case.data.materials.append(mat_watch_case)

# Steel Watch Crown & Lugs
crown = prim('cylinder', name="Crown", r=0.07, depth=0.15, loc=(0.52, 0, 0), coll=C)
crown.parent = watch_rig
crown.rotation_euler = Euler((0, math.radians(90), 0), 'XYZ')
crown.data.materials.append(mat_watch_case)

# Watch Dial
dial = prim('cylinder', name="Dial", r=0.42, depth=0.04, segments=48, loc=(0, 0, 0.045), coll=C)
dial.parent = watch_rig
dial.data.materials.append(mat_watch_dial)

# Curved Sapphire Crystal Face (Convex lens capturing reflection)
glass = prim('sphere', name="SapphireCrystal", r=0.44, loc=(0, 0, 0.05), coll=C)
glass.parent = watch_rig
glass.scale = Vector((1.0, 1.0, 0.18))
glass.data.materials.append(mat_watch_glass)

# 2. Reflected Image of Heroine (Stylized mini silhouette in the curved glass)
ref_rig = bpy.data.objects.new("ReflectionRig", None)
link(ref_rig, C)
ref_rig.parent = watch_rig
ref_rig.location = Vector((0.0, 0.08, 0.06))

# Reflected head & shoulders of the girl
ref_head = prim('sphere', name="Ref_GirlHead", r=0.12, loc=(0, 0, 0), coll=C)
ref_head.parent = ref_rig
ref_head.data.materials.append(mat_girl_reflection)

ref_hair = prim('sphere', name="Ref_GirlHair", r=0.135, loc=(0, 0.02, 0.03), coll=C)
ref_hair.parent = ref_rig
ref_hair.scale = Vector((1.1, 1.15, 0.9))
ref_hair.data.materials.append(mat_girl_hair_ref)

# Subtle Tilt of the Watch Rig: Tilting to catch the window sunlight and reveal the reflection
watch_rig.rotation_euler = Euler((math.radians(18), math.radians(-12), math.radians(5)), 'XYZ')
watch_rig.keyframe_insert("rotation_euler", frame=1)

watch_rig.rotation_euler = Euler((math.radians(32), math.radians(-5), math.radians(14)), 'XYZ')
watch_rig.keyframe_insert("rotation_euler", frame=48)

watch_rig.rotation_euler = Euler((math.radians(28), math.radians(-4), math.radians(12)), 'XYZ')
watch_rig.keyframe_insert("rotation_euler", frame=72)

# Sun Glint Flare Ring on the glass edge
glint = prim('torus', name="SunGlint", r=0.43, depth=0.015, loc=(0, 0, 0.075), coll=C)
glint.parent = watch_rig
glint.data.materials.append(mat_sun_glint)

# 3. Cinematic Lighting: High-Contrast Window Sunlight Ray
light(kind='SUN', name="Sun_MacroGlint", rot=(math.radians(40), math.radians(-20), math.radians(55)),
      energy=9.0, color=(1.0, 0.85, 0.48), coll=C)
light(kind='SPOT', name="Spot_GlassRim", loc=(-1.4, -1.0, FOCAL_LOC.z + 1.2),
      rot=(math.radians(50), 0, math.radians(-35)), energy=850.0, color=(1.0, 0.90, 0.60), spot=55.0, coll=C)
light(kind='AREA', name="Light_FillWarm", loc=(1.2, 0.8, FOCAL_LOC.z + 1.0), energy=220.0,
      color=(0.70, 0.78, 0.95), coll=C)

# 4. Camera: 85mm Macro Optical Track diving toward the watch glass reflection
cam_start = Vector((0.0, -1.6, FOCAL_LOC.z + 0.85))
cam_mid   = Vector((0.05, -1.15, FOCAL_LOC.z + 0.65))
cam_end   = Vector((0.02, -0.75, FOCAL_LOC.z + 0.48))

cam = camera(name="Camera", loc=cam_start, target=glass, lens=85.0, fstop=1.8, coll=C)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("LOVE_03")
