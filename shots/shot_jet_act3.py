"""
shot_jet_act3.py (JET_03: Squeeze - 40x Axial Compressor)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Focal geometry strictly framed in Upper-Middle safe zone (Y: 18% to 58%).
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.42, look='AgX - Punchy')
compositor(bloom=0.45, threshold=0.98, bloom_size=0.6, dispersion=0.007)

w = world_color((0.001, 0.001, 0.002))
add_world_fog(w, density=0.002, color=(0.04, 0.03, 0.12), anisotropy=0.55)

C = collection("SET_JET_03")
random.seed(202)

# Shaders
mat_titanium = mat_principled("Mat_BliskTitanium", color=(0.28, 0.32, 0.42), metal=0.98, rough=0.18,
                              emit=(0.02, 0.06, 0.15), emit_strength=0.25)
mat_casing = mat_principled("Mat_CompressorCasing", color=(0.10, 0.12, 0.16), metal=0.90, rough=0.25)

# Staged thermal colors: Stage 1 (Ice Blue) -> Stage 5 (Electric Violet) -> Stage 10 (Molten Amber)
mat_cool_glow = mat_emission("Mat_CoolGlow", color=(0.08, 0.75, 1.0), strength=36.0)
mat_violet_glow = mat_emission("Mat_VioletGlow", color=(0.65, 0.20, 1.0), strength=38.0)
mat_amber_glow = mat_emission("Mat_AmberGlow", color=(1.0, 0.58, 0.10), strength=42.0)

# Focal anchor shifted up for 9:16 vertical safe zone
FOCAL_LOC = Vector((0.0, 0.0, 0.6))

# Central Drive Shaft running through compressor
shaft = prim('cylinder', name="CentralShaft", r=0.42, depth=14.0, segments=36, loc=FOCAL_LOC, coll=C)
shaft.rotation_euler = (math.radians(90), 0, 0)
shaft.data.materials.append(mat_titanium)

# 10 Consecutive Compressor Stages narrowing along Y (from Y = -5.0 to +5.0)
stages_rig = bpy.data.objects.new("CompressorStagesRig", None)
link(stages_rig, C)
stages_rig.location = FOCAL_LOC

num_stages = 10
for s_idx in range(num_stages):
    t_stage = s_idx / (num_stages - 1) # 0.0 to 1.0
    s_y = -4.5 + t_stage * 9.0
    # Narrowing radius from 2.2 down to 0.9
    s_rad = 2.2 - t_stage * 1.25
    
    # Material interpolation based on stage thermal compression
    if t_stage < 0.35:
        stage_mat = mat_cool_glow
    elif t_stage < 0.70:
        stage_mat = mat_violet_glow
    else:
        stage_mat = mat_amber_glow
        
    # Rotor Blade Disc (Blisk)
    blades_per_stage = 16 + int(t_stage * 12)
    stage_disc = bpy.data.objects.new(f"BliskStage_{s_idx}", None)
    link(stage_disc, C)
    stage_disc.parent = stages_rig
    stage_disc.location = Vector((0, s_y, 0))
    
    for b_i in range(blades_per_stage):
        ang = (b_i / blades_per_stage) * math.tau
        bx = math.cos(ang) * (shaft.scale.x * 0.42 + s_rad * 0.5)
        bz = math.sin(ang) * (shaft.scale.x * 0.42 + s_rad * 0.5)
        b = prim('cube', name=f"Stage_{s_idx}_Blade_{b_i}", scale=(0.08, 0.04, s_rad * 0.48), loc=(bx, 0, bz), coll=C)
        b.parent = stage_disc
        b.rotation_euler = Euler((0.45, 0, ang), 'XYZ')
        b.data.materials.append(mat_titanium)
    
    # Outer stator compression ring with thermal glow
    bpy.ops.mesh.primitive_torus_add(major_radius=s_rad, minor_radius=0.035, location=(0, s_y, FOCAL_LOC.z))
    t_ring = bpy.context.active_object
    t_ring.rotation_euler = (math.radians(90), 0, 0)
    t_ring.data.materials.append(stage_mat)

# Compressor Rotation Animation (Spinning at high speed)
stages_rig.keyframe_insert("rotation_euler", frame=1)
stages_rig.rotation_euler = Euler((0, math.radians(-1080), 0), 'XYZ') # 3 full rotations
stages_rig.keyframe_insert("rotation_euler", frame=72)

# Compressed Air Plasma Ribbons (Spiraling through the compressor blades)
for p_i in range(36):
    ang = (p_i / 36.0) * math.tau
    t_p = random.uniform(0.1, 0.9)
    py = -4.5 + t_p * 9.0
    prad = (2.2 - t_p * 1.25) * random.uniform(0.6, 0.95)
    px = math.cos(ang) * prad
    pz = FOCAL_LOC.z + math.sin(ang) * prad
    
    spark = prim('sphere', name=f"AirSpark_{p_i}", r=random.uniform(0.025, 0.05), loc=(px, py, pz), coll=C)
    if t_p < 0.4:
        spark.data.materials.append(mat_cool_glow)
    elif t_p < 0.7:
        spark.data.materials.append(mat_violet_glow)
    else:
        spark.data.materials.append(mat_amber_glow)
        
    spark.keyframe_insert("location", frame=1)
    spark.location.y += random.uniform(2.2, 4.0) # High-velocity air compression flow
    spark.rotation_euler.rotate(Euler((0, 0, 2.5), 'XYZ'))
    spark.keyframe_insert("location", frame=72)

# Cinematic Lighting
light(kind='SPOT', name="Spot_CamHeadlight", loc=(0.0, -1.2, FOCAL_LOC.z + 0.3),
      rot=(math.radians(90), 0, 0), energy=3400.0, color=(0.4, 0.75, 1.0), spot=65.0, coll=C)
light(kind='POINT', name="Light_Front_Cyan", loc=(0.0, -4.5, FOCAL_LOC.z + 1.0), energy=1400.0, color=(0.10, 0.85, 1.0), coll=C)
light(kind='POINT', name="Light_Rear_Amber", loc=(0.0, 4.5, FOCAL_LOC.z + 0.8), energy=1800.0, color=(1.0, 0.65, 0.15), coll=C)
light(kind='SPOT', name="Spot_Side_Rim", loc=(-3.5, -1.0, FOCAL_LOC.z + 2.5),
      rot=(math.radians(50), 0, math.radians(-30)), energy=1100.0, color=(0.75, 0.25, 1.0), spot=75.0, coll=C)

# Camera: High-speed tracking shot flying down the compressor corridor
cam_start = Vector((0.0, -5.8, FOCAL_LOC.z + 0.4))
cam_mid   = Vector((0.15, -1.5, FOCAL_LOC.z + 0.2))
cam_end   = Vector((0.0, 2.8, FOCAL_LOC.z))

cam = camera(name="Camera", loc=cam_start, target=shaft, lens=28.0, fstop=2.2, coll=C)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("JET_03")
