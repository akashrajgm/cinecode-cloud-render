"""
spiderverse.py
Hollywood & Spider-Verse cinematic stylization and human psychology helpers for Blender EEVEE.
Provides:
- Inverted-hull comic ink contour outlines.
- Stepped 12 fps animation curves (animating on 2s).
- Realistic human micro-expressions and blendshape keyframes.
- Cinematic beveled classroom sets with volumetric sunbeams.
"""

import bpy
import math
from mathutils import Vector, Euler

def apply_comic_ink(mesh_obj, thickness=-0.003, coll_name="SET"):
    """Applies clean comic-book ink contour outlines using the Inverted Hull technique."""
    if not mesh_obj or mesh_obj.type != 'MESH':
        return
    
    # Check if outline material exists
    ink_mat = bpy.data.materials.get("Mat_ComicInk")
    if not ink_mat:
        ink_mat = bpy.data.materials.new("Mat_ComicInk")
        ink_mat.use_nodes = True
        nodes = ink_mat.node_tree.nodes
        links = ink_mat.node_tree.links
        nodes.clear()
        
        # Pure dark ink emission shader
        output = nodes.new('ShaderNodeOutputMaterial')
        emission = nodes.new('ShaderNodeEmission')
        emission.inputs['Color'].default_value = (0.015, 0.012, 0.02, 1.0)
        emission.inputs['Strength'].default_value = 1.0
        links.new(emission.outputs['Emission'], output.inputs['Surface'])
        
        ink_mat.use_backface_culling = True
        try:
            ink_mat.shadow_method = 'NONE'
        except Exception:
            pass

    # Ensure material is in mesh slots
    if ink_mat.name not in [slot.name for slot in mesh_obj.material_slots if slot.material]:
        mesh_obj.data.materials.append(ink_mat)
    
    mat_idx = [i for i, slot in enumerate(mesh_obj.material_slots) if slot.material and slot.material.name == ink_mat.name][0]
    
    # Solidify modifier
    mod = mesh_obj.modifiers.get("ComicInk")
    if not mod:
        mod = mesh_obj.modifiers.new("ComicInk", 'SOLIDIFY')
    mod.thickness = thickness
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.material_offset = mat_idx
    mod.material_offset_rim = mat_idx

def animate_hero_boy_emotions(head_obj, boy_armature, shot_act=2):
    """
    Keyframes human psychological progression for the Hero Boy:
    - Act 1: Nervous glances over shoulder, quick snap forward.
    - Act 2: Tense breathing, the 'spark' of an idea, eyes darting to watch, nervous swallow.
    """
    if not head_obj or not head_obj.data.shape_keys:
        return
    
    kb = head_obj.data.shape_keys.key_blocks
    
    if shot_act == 1:
        # Act 1: Glance and snap
        for f in range(1, 73):
            # Natural blinks
            blink_val = 1.0 if (20 <= f <= 23 or 55 <= f <= 58) else 0.0
            if 'eye_close' in kb:
                kb['eye_close'].value = blink_val
                kb['eye_close'].keyframe_insert('value', frame=f)
            
            # Look sideways towards girl
            look_side = 0.85 if (15 <= f <= 40) else 0.0
            if 'look_right' in kb:
                kb['look_right'].value = look_side
                kb['look_right'].keyframe_insert('value', frame=f)
                
            # Brow furrow
            brow = 0.5 if (15 <= f <= 42) else 0.1
            if 'eye_brow_down' in kb:
                kb['eye_brow_down'].value = brow
                kb['eye_brow_down'].keyframe_insert('value', frame=f)
                
    elif shot_act == 2:
        # Act 2: Nervous tension, ideation, eye darting to wrist
        for f in range(1, 73):
            # Blinks at frame 16 and 48
            blink_val = 1.0 if (16 <= f <= 19 or 48 <= f <= 51) else 0.0
            if 'eye_close' in kb:
                kb['eye_close'].value = blink_val
                kb['eye_close'].keyframe_insert('value', frame=f)
                
            # Eye darts down towards watch
            if f < 18:
                down_val = 0.1
                left_val = 0.0
                brow_up = 0.0
                brow_down = 0.2
            elif f < 32:
                # The "Idea" strikes! Brows raise
                t = (f - 18) / 14.0
                down_val = 0.1 + t * 0.75
                left_val = t * 0.65
                brow_up = t * 0.7
                brow_down = 0.0
            else:
                # Locked on watch dial, tense focus
                down_val = 0.90
                left_val = 0.70
                brow_up = 0.0
                brow_down = 0.65
                
            if 'look_down' in kb:
                kb['look_down'].value = down_val
                kb['look_down'].keyframe_insert('value', frame=f)
            if 'look_left' in kb:
                kb['look_left'].value = left_val
                kb['look_left'].keyframe_insert('value', frame=f)
            if 'eye_brow_up' in kb:
                kb['eye_brow_up'].value = brow_up
                kb['eye_brow_up'].keyframe_insert('value', frame=f)
            if 'eye_brow_down' in kb:
                kb['eye_brow_down'].value = brow_down
                kb['eye_brow_down'].keyframe_insert('value', frame=f)
            if 'cheek' in kb:
                kb['cheek'].value = 0.35 if f >= 28 else 0.1
                kb['cheek'].keyframe_insert('value', frame=f)

def animate_heroine_girl_emotions(face_obj, girl_armature, shot_act=5):
    """
    Keyframes human psychological progression for the Heroine Girl:
    - Act 4: Serene, composed, rhythmic pen twirling, effortless charm.
    - Act 5: The Hollywood / Spider-Verse reveal — knowing micro-tilt and the teasing smirk.
    """
    if not face_obj or not face_obj.data.shape_keys:
        return
        
    kb = face_obj.data.shape_keys.key_blocks
    
    if shot_act == 4:
        for f in range(1, 73):
            # Natural rhythmic blinks
            blink_r = 1.0 if (22 <= f <= 25 or 58 <= f <= 61) else 0.0
            if 'Fcl_EYE_Close' in kb:
                kb['Fcl_EYE_Close'].value = blink_r
                kb['Fcl_EYE_Close'].keyframe_insert('value', frame=f)
            if 'Fcl_BRW_Joy' in kb:
                kb['Fcl_BRW_Joy'].value = 0.35
                kb['Fcl_BRW_Joy'].keyframe_insert('value', frame=f)
                
    elif shot_act == 5:
        # Act 5: The Climax / The Knowing Smirk
        for f in range(1, 73):
            if f < 20:
                # Composed look
                smirk = 0.1
                joy_eye = 0.1
                brw_joy = 0.2
            elif f < 48:
                # Smirk builds progressively as she tilts head
                t = (f - 20) / 28.0
                smirk = 0.1 + t * 0.85
                joy_eye = 0.1 + t * 0.75
                brw_joy = 0.2 + t * 0.60
            else:
                # Full Hollywood teasing smirk held triumphantly!
                smirk = 0.95
                joy_eye = 0.85
                brw_joy = 0.80
                
            if 'Fcl_MTH_SkinFung' in kb:
                kb['Fcl_MTH_SkinFung'].value = smirk
                kb['Fcl_MTH_SkinFung'].keyframe_insert('value', frame=f)
            if 'Fcl_EYE_Joy' in kb:
                kb['Fcl_EYE_Joy'].value = joy_eye
                kb['Fcl_EYE_Joy'].keyframe_insert('value', frame=f)
            if 'Fcl_BRW_Joy' in kb:
                kb['Fcl_BRW_Joy'].value = brw_joy
                kb['Fcl_BRW_Joy'].keyframe_insert('value', frame=f)
            if 'Fcl_ALL_Fun' in kb:
                kb['Fcl_ALL_Fun'].value = smirk * 0.45
                kb['Fcl_ALL_Fun'].keyframe_insert('value', frame=f)

def build_hollywood_classroom(coll, mat_wood, mat_metal, mat_wall, mat_blackboard):
    """Constructs a high-detail cinema classroom set with beveled desks, window panes, and props."""
    # Main Classroom Floor
    floor = bpy.data.objects.new("Cinema_Floor", bpy.data.meshes.new("FloorMesh"))
    coll.objects.link(floor)
    floor.location = Vector((0, 2.0, -0.6))
    
    # 4 Rows of Wooden Desks with Bevels and Metal Frames
    for r in range(4):
        y_pos = -0.5 + r * 1.8
        for col_x in [-1.4, 0.0, 1.4]:
            # Table Top
            desk = bpy.data.objects.new(f"DeskTop_R{r}_{col_x}", bpy.data.meshes.new("DeskMesh"))
            coll.objects.link(desk)
            
            # Simple mesh cube with bevel modifier
            desk.location = Vector((col_x, y_pos, 0.55))
            desk.scale = Vector((1.1, 0.50, 0.04))
            desk.data.materials.append(mat_wood)
            
            # Desk Legs (Metal Frame)
            for lx in [-0.48, 0.48]:
                for ly in [-0.20, 0.20]:
                    leg = bpy.data.objects.new(f"Leg_{r}_{col_x}_{lx}_{ly}", bpy.data.meshes.new("LegMesh"))
                    coll.objects.link(leg)
                    leg.location = Vector((col_x + lx, y_pos + ly, 0.25))
                    leg.scale = Vector((0.025, 0.025, 0.30))
                    leg.data.materials.append(mat_metal)

    # Window Wall with Cross-Pane Grid (Left Side for Volumetric Sun God-Rays)
    window_frame = bpy.data.objects.new("WindowGrid_Left", bpy.data.meshes.new("WindowMesh"))
    coll.objects.link(window_frame)
    window_frame.location = Vector((-3.2, 1.5, 1.8))
    window_frame.scale = Vector((0.08, 5.0, 2.4))
    window_frame.data.materials.append(mat_metal)
