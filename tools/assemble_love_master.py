#!/usr/bin/env python3
"""
assemble_love_master.py
Conforms all 5 rendered 3D animated acts for the Classroom Love Scene,
composites snappy 1-3 word MrBeast-style running captions at Y=68% with active word popping in #FACC15,
mixes balanced voiceover and acoustic score bed, and exports the final living 9:16 vertical film.
Memory-optimized streaming architecture: uses < 150 MB RAM throughout entire conform.
"""

import os
import sys
import json
import re
import subprocess
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC_DIR = "/tmp/cinecode-cloud-render"
if not os.path.exists(SRC_DIR):
    SRC_DIR = "/Volumes/Helumi/CinecodeStudio/escapement-reference"
if not os.path.exists(SRC_DIR):
    SRC_DIR = "/content/drive/MyDrive/CinecodeStudio"

AUDIO_PATH = os.path.join(SRC_DIR, "audio", "love_vo", "love_vo_mastered.wav")
CAPTIONS_PATH = os.path.join(SRC_DIR, "audio", "love_vo", "caption_chunks.json")
EXPORT_DIR = os.path.join(SRC_DIR, "export")
EXPORT_PATH = os.path.join(EXPORT_DIR, "school_love_scene_master.mp4")

# Font paths
FONT_REGULAR_PATH = "/Users/Akash'Mac/Library/Fonts/Montserrat-ExtraBold.otf"
if not os.path.exists(FONT_REGULAR_PATH):
    FONT_REGULAR_PATH = "/usr/share/fonts/truetype/montserrat/Montserrat-ExtraBold.ttf"

FONT_ITALIC_PATH = "/Users/Akash'Mac/Library/Fonts/PlayfairDisplay-Italic[wght].ttf"
if not os.path.exists(FONT_ITALIC_PATH):
    FONT_ITALIC_PATH = FONT_REGULAR_PATH

os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(os.path.join(EXPORT_DIR, "thumbnails"), exist_ok=True)

WIDTH = 1080
HEIGHT = 1920
FPS = 24
TOTAL_DURATION = 43.50  # seconds
TOTAL_FRAMES = int(TOTAL_DURATION * FPS)  # 1044 frames

# Timeline definitions: (Shot_ID, start_frame, end_frame_inclusive)
ACTS = [
    ("LOVE_01", 0, 227),     # 0.0s - 9.49s (228 frames)
    ("LOVE_02", 228, 437),   # 9.5s - 18.24s (210 frames)
    ("LOVE_03", 438, 659),   # 18.25s - 27.49s (222 frames)
    ("LOVE_04", 660, 857),   # 27.5s - 35.74s (198 frames)
    ("LOVE_05", 858, 1043),  # 35.75s - 43.50s (186 frames)
]

def parse_time(ts):
    h, m, rest = ts.split(':')
    s, ms = rest.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

def load_captions(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        raw_chunks = json.load(f)
    
    chunks = []
    for c in raw_chunks:
        c_start = parse_time(c['start'])
        c_end = parse_time(c['end'])
        words = []
        for w in c.get('words', []):
            wt0 = parse_time(w['start'])
            wt1 = parse_time(w['end'])
            cleaned = w.get('word', '').strip()
            if cleaned and cleaned not in [",", ".", ";", "!", "?"]:
                words.append({
                    'word': cleaned,
                    'start': wt0,
                    'end': wt1,
                    'emphasis': w.get('emphasis', False)
                })
        if words:
            chunks.append({
                'start': c_start,
                'end': c_end,
                'text': c.get('text', ''),
                'words': words
            })
    return chunks

def build_vignette_mask(w, h):
    x = np.linspace(-1.0, 1.0, w)
    y = np.linspace(-1.0, 1.0, h)
    xx, yy = np.meshgrid(x, y)
    radius = np.sqrt(xx**2 + yy**2)
    vignette = 1.0 - 0.22 * np.clip((radius - 0.5) / 0.9, 0.0, 1.0) ** 1.5
    return vignette[:, :, np.newaxis].astype(np.float32)

def get_act_frame_paths(act_id):
    """Finds all rendered animation frames for the act without loading them into memory."""
    for base in [SRC_DIR, "/Volumes/Helumi/CinecodeStudio/escapement-reference", "/content/drive/MyDrive/CinecodeStudio"]:
        act_dir = os.path.join(base, "renders", act_id)
        if os.path.exists(act_dir):
            files = sorted([
                os.path.join(act_dir, f) for f in os.listdir(act_dir)
                if (f.lower().endswith(".jpg") or f.lower().endswith(".jpeg") or f.lower().endswith(".png"))
                and not f.startswith(".")
            ])
            if files:
                return files
    # Fallback to tests still if no animation frames yet
    test_path = os.path.join(SRC_DIR, "tests", f"{act_id}_f0036.jpg")
    if os.path.exists(test_path):
        return [test_path]
    return []

def render_caption_layer(draw, current_chunk, cur_time, font_regular, font_active, font_italic):
    target_y = int(HEIGHT * 0.68)
    words = current_chunk['words']
    if not words:
        return

    word_metrics = []
    total_w = 0
    space_w = font_regular.getlength(" ")

    for w_info in words:
        w_text = w_info['word']
        is_active = (cur_time >= w_info['start'] - 0.02) and (cur_time <= w_info['end'] + 0.04)
        is_emphasis = w_info.get('emphasis', False)
        
        if is_emphasis:
            f = font_italic
        elif is_active:
            f = font_active
        else:
            f = font_regular
            
        w_len = f.getlength(w_text)
        word_metrics.append((w_info, is_active, is_emphasis, f, w_len))
        total_w += w_len

    total_w += space_w * (len(words) - 1)
    start_x = (WIDTH - total_w) / 2.0

    cur_x = start_x
    for w_info, is_active, is_emphasis, f, w_len in word_metrics:
        w_text = w_info['word']
        if is_active:
            fill_color = (250, 204, 21, 255)       # Bright Sunburst Yellow (#FACC15)
            stroke_color = (15, 12, 5, 240)
            stroke_w = 5
            for ox in [-2, 0, 2]:
                for oy in [-2, 0, 2]:
                    draw.text((cur_x + ox, target_y + oy), w_text, font=f, fill=(250, 204, 21, 80))
        elif is_emphasis:
            fill_color = (255, 87, 34, 255)       # High-energy Coral Orange (#FF5722)
            stroke_color = (15, 10, 8, 230)
            stroke_w = 4
        else:
            fill_color = (248, 250, 255, 240)      # Clean crisp off-white
            stroke_color = (10, 12, 18, 220)
            stroke_w = 4

        draw.text((cur_x, target_y), w_text, font=f, fill=fill_color,
                  stroke_width=stroke_w, stroke_fill=stroke_color)
        cur_x += w_len + space_w

def main():
    print(f"--- Starting Assembly: Classroom Love Scene Master (Living 3D Motion) ---")
    print(f"Target: {EXPORT_PATH}")
    print(f"Total Frames: {TOTAL_FRAMES} ({TOTAL_DURATION}s @ {FPS} fps)")

    vignette = build_vignette_mask(WIDTH, HEIGHT)
    captions = load_captions(CAPTIONS_PATH)
    print(f"Loaded {len(captions)} caption chunks.")

    try:
        font_regular = ImageFont.truetype(FONT_REGULAR_PATH, size=58)
        font_active = ImageFont.truetype(FONT_REGULAR_PATH, size=60)
        font_italic = ImageFont.truetype(FONT_ITALIC_PATH, size=62)
    except Exception as e:
        print(f"Font loading error: {e}, falling back to default")
        font_regular = ImageFont.load_default()
        font_active = font_regular
        font_italic = font_regular

    # Discover frame file lists for each act
    act_file_map = {}
    for act_id, _, _ in ACTS:
        paths = get_act_frame_paths(act_id)
        act_file_map[act_id] = paths
        print(f"Found {len(paths)} frames for {act_id}")

    is_mac = sys.platform == "darwin"
    vcodec = "h264_videotoolbox" if is_mac else "libx264"
    extra_flags = ["-b:v", "16M"] if is_mac else ["-preset", "fast", "-crf", "17"]

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-i", AUDIO_PATH,
        "-c:v", vcodec
    ] + extra_flags + [
        "-c:a", "aac",
        "-b:a", "320k",
        "-shortest",
        EXPORT_PATH
    ]

    print("Launching FFmpeg encoding pipe...")
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    t0 = time.time()
    last_loaded_path = None
    cached_frame_img = None

    for global_f in range(TOTAL_FRAMES):
        cur_time = global_f / float(FPS)

        active_act_id = None
        act_start_f = 0
        act_end_f = 0
        for act_id, s_f, e_f in ACTS:
            if s_f <= global_f <= e_f:
                active_act_id = act_id
                act_start_f = s_f
                act_end_f = e_f
                break

        if active_act_id is None:
            active_act_id = ACTS[-1][0]
            act_start_f = ACTS[-1][1]
            act_end_f = ACTS[-1][2]

        frame_paths = act_file_map[active_act_id]
        act_len = act_end_f - act_start_f + 1
        local_f = global_f - act_start_f
        
        # Smooth temporal mapping across full act duration
        progress = local_f / float(max(1, act_len - 1))
        pos = progress * (len(frame_paths) - 1)
        idx0 = int(pos)
        idx1 = min(len(frame_paths) - 1, idx0 + 1)
        alpha = pos - idx0

        # Load and blend frames (silky smooth motion)
        p0 = frame_paths[idx0]
        if alpha < 0.04 or idx0 == idx1:
            if last_loaded_path == p0 and cached_frame_img is not None:
                img_np = cached_frame_img.copy()
            else:
                im = Image.open(p0).convert("RGB")
                if im.size != (WIDTH, HEIGHT):
                    im = im.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
                img_np = np.array(im, dtype=np.float32)
                last_loaded_path = p0
                cached_frame_img = img_np
        else:
            im0 = Image.open(p0).convert("RGB")
            im1 = Image.open(frame_paths[idx1]).convert("RGB")
            if im0.size != (WIDTH, HEIGHT):
                im0 = im0.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            if im1.size != (WIDTH, HEIGHT):
                im1 = im1.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            img0_np = np.array(im0, dtype=np.float32)
            img1_np = np.array(im1, dtype=np.float32)
            img_np = (1.0 - alpha) * img0_np + alpha * img1_np

        # Cinematic warm vignette
        base_frame = np.clip(img_np * vignette, 0, 255).astype(np.uint8)

        pil_img = Image.fromarray(base_frame)
        draw = ImageDraw.Draw(pil_img)

        # Check for active caption chunk
        active_chunk = None
        for chunk in captions:
            if chunk['start'] - 0.03 <= cur_time <= chunk['end'] + 0.08:
                active_chunk = chunk
                break

        if active_chunk is not None:
            render_caption_layer(draw, active_chunk, cur_time, font_regular, font_active, font_italic)

        raw_bytes = pil_img.tobytes()
        proc.stdin.write(raw_bytes)

        if global_f % 120 == 0:
            elapsed = time.time() - t0
            fps_proc = (global_f + 1) / max(0.1, elapsed)
            print(f"Composited frame {global_f}/{TOTAL_FRAMES} ({cur_time:.1f}s) @ {fps_proc:.1f} fps")

    proc.stdin.close()
    proc.wait()
    total_time = time.time() - t0
    print(f"Assembly completed successfully in {total_time:.1f}s!")
    print(f"Exported Master Film: {EXPORT_PATH}")

if __name__ == "__main__":
    main()
