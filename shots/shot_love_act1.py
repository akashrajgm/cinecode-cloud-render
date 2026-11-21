"""
shot_love_act1.py (LOVE_01: The Front Bench Trap)
9:16 Vertical (1080x1920), 24 fps, AgX Color Management.
Scene: High school classroom with 30+ students at wooden benches.
Hero seated at the first bench, sunlight streaming diagonally through tall windows.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from common import *
from mathutils import Vector, Euler

reset()
sc = setup_render(start=1, end=72, res=(1080, 1920), samples=24, exposure=0.10, look='AgX - Punchy')
compositor(bloom=0.35, threshold=0.98, bloom_size=0.5, dispersion=0.005)

# Warm afternoon golden classroom atmosphere
w = world_color((0.003, 0.004, 0.008))
add_world_fog(w, density=0.008, color=(0.95, 0.72, 0.35), anisotropy=0.75)

C = collection("SET_LOVE_01")
random.seed(501)

# Stylized Shaders
mat_skin_boy = mat_principled("Mat_SkinBoy", color=(0.92, 0.74, 0.62), rough=0.32)
mat_skin_girl = mat_principled("Mat_SkinGirl", color=(0.95, 0.78, 0.68), rough=0.30)
mat_hair_boy = mat_principled("Mat_HairBoy", color=(0.08, 0.05, 0.04), rough=0.25)
mat_hair_girl = mat_principled("Mat_HairGirl", color=(0.14, 0.07, 0.03), rough=0.22)
mat_uniform_navy = mat_principled("Mat_UniformNavy", color=(0.08, 0.12, 0.22), rough=0.60)
mat_uniform_white = mat_principled("Mat_UniformWhite", color=(0.92, 0.94, 0.96), rough=0.50)
mat_desk_wood = mat_principled("Mat_DeskWood", color=(0.48, 0.28, 0.14), rough=0.35)
mat_metal_frame = mat_principled("Mat_MetalFrame", color=(0.20, 0.22, 0.25), metal=0.90, rough=0.25)
mat_blackboard = mat_principled("Mat_Blackboard", color=(0.06, 0.10, 0.08), rough=0.70)
mat_sun_dust = mat_emission("Mat_SunDust", color=(1.0, 0.85, 0.45), strength=8.0)

# Anchor classroom center
FOCAL_LOC = Vector((0.0, 0.0, 0.6))

# 1. Classroom Architecture & Blackboard (Front of Class)
blackboard = prim('cube', name="Blackboard", scale=(3.2, 0.05, 1.2), loc=(0, -3.2, FOCAL_LOC.z + 0.8), coll=C)
blackboard.data.materials.append(mat_blackboard)

# Classroom Floor & Left Window Wall
floor = prim('cube', name="Floor", scale=(6.0, 10.0, 0.1), loc=(0, 2.0, -0.6), coll=C)
floor.data.materials.append(mat_desk_wood)

# 2. Wooden Student Desks (4 Rows of Benches, 3 Students per Bench = 36 Students)
def create_desk_row(row_idx, y_pos):
    for col_idx in [-1.5, 0.0, 1.5]:
        # Desk surface
        desk = prim('cube', name=f"Desk_R{row_idx}_C{col_idx}", scale=(1.2, 0.5, 0.04), loc=(col_idx, y_pos, FOCAL_LOC.z - 0.1), coll=C)
        desk.data.materials.append(mat_desk_wood)
        # 3 Students at this bench
        for seat_i in [-0.35, 0.0, 0.35]:
            is_hero = (row_idx == 0 and col_idx == 0.0 and seat_i == 0.0)
            is_heroine = (row_idx == 3 and col_idx == 0.0 and seat_i == 0.0)
            
            sx = col_idx + seat_i
            sy = y_pos + 0.35
            sz = FOCAL_LOC.z
            
            # Stylized Torso
            torso = prim('cylinder', name=f"Student_R{row_idx}_S{seat_i}", r=0.14, depth=0.45, loc=(sx, sy, sz), coll=C)
            torso.data.materials.append(mat_uniform_navy if not is_heroine else mat_uniform_white)
            
            # Stylized Head
            skin_m = mat_skin_girl if is_heroine else mat_skin_boy
            head = prim('sphere', name=f"Head_R{row_idx}_S{seat_i}", r=0.11, loc=(sx, sy, sz + 0.35), coll=C)
            head.data.materials.append(skin_m)
            
            # Stylized Hair
            hair_m = mat_hair_girl if is_heroine else mat_hair_boy
            hair = prim('sphere', name=f"Hair_R{row_idx}_S{seat_i}", r=0.12, loc=(sx, sy - 0.02, sz + 0.40), coll=C)
            hair.scale = Vector((1.05, 1.1, 0.7))
            hair.data.materials.append(hair_m)
            
            if is_hero:
                head.name = "Hero_Head"
            elif is_heroine:
                head.name = "Heroine_Head"

for r in range(4):
    create_desk_row(r, y_pos=-1.4 + r * 1.8)

# 3. Floating Golden Sunlight Dust Motes
for d_i in range(45):
    dx = random.uniform(-2.5, 2.5)
    dy = random.uniform(-2.5, 5.0)
    dz = FOCAL_LOC.z + random.uniform(-0.5, 1.5)
    mote = prim('sphere', name=f"Mote_{d_i}", r=random.uniform(0.015, 0.035), loc=(dx, dy, dz), coll=C)
    mote.data.materials.append(mat_sun_dust)
    mote.keyframe_insert("location", frame=1)
    mote.location.z += random.uniform(-0.2, 0.2)
    mote.location.y += random.uniform(-0.3, 0.3)
    mote.keyframe_insert("location", frame=72)

# 4. Cinematic Golden Afternoon Window Sunlight
# Powerful Key Window Sunlight from high left
light(kind='SUN', name="Sun_GoldenWindow", rot=(math.radians(45), math.radians(-25), math.radians(65)),
      energy=7.5, color=(1.0, 0.82, 0.45), coll=C)

# Soft Cool Fill Light from right interior
light(kind='AREA', name="Light_CoolFill", loc=(3.5, 1.0, FOCAL_LOC.z + 2.5), energy=350.0,
      color=(0.60, 0.75, 1.0), coll=C)

# Hero Rim Light
light(kind='SPOT', name="Spot_HeroRim", loc=(-1.5, -0.5, FOCAL_LOC.z + 1.8),
      rot=(math.radians(45), 0, math.radians(-25)), energy=650.0, color=(1.0, 0.78, 0.35), spot=55.0, coll=C)

# 5. Camera: Cinematic Vertical High-Angle Establishing Shot
# Sweeps downward from back of class towards the hero on the first bench
cam_start = Vector((1.2, 4.5, FOCAL_LOC.z + 2.2))
cam_mid   = Vector((0.6, 2.2, FOCAL_LOC.z + 1.6))
cam_end   = Vector((0.1, -0.2, FOCAL_LOC.z + 1.1))

hero_obj = bpy.data.objects.get("Hero_Head")
cam = camera(name="Camera", loc=cam_start, target=hero_obj, lens=38.0, fstop=2.0, coll=C)
cam.data.sensor_fit = 'VERTICAL'

for f, pos in [(1, cam_start), (36, cam_mid), (72, cam_end)]:
    cam.location = pos
    cam.keyframe_insert("location", frame=f)

finish("LOVE_01")
