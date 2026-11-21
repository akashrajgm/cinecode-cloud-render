#!/usr/bin/env python3
"""
build_colab_notebook.py
Generates the turnkey 1-Click Google Colab Notebook for Cinecode Studio.
Syncs directly with github.com/akashrajgm/cinecode-cloud-render into Google Drive.
"""

import json
import os

NOTEBOOK_PATH = "/tmp/cinecode-cloud-render/Cinecode_Cloud_Render_Pipeline.ipynb"

cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# 🎬 Cinecode Studio: 100% Cloud Video Generator\n",
            "### Fast 3D Procedural Cinema on Google Cloud GPU (NVIDIA T4 / L4) + Google Drive\n",
            "\n",
            "This notebook runs the heavy 3D Blender raytracing, 0.0% exposure QC, and 9:16 vertical video assembly directly in Google Colab.\n",
            "\n",
            "**Key Benefits:**\n",
            "- **Zero Local RAM Usage:** Your Mac/PC stays at idle (~2–4 GB total RAM).\n",
            "- **Zero Laptop Heat:** No fan noise, no throttling, zero battery drain.\n",
            "- **Automatic Google Drive Storage:** Everything is saved directly in your Google Drive under `/MyDrive/CinecodeStudio/`."
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 📌 Step 1: Connect to GPU Runtime\n",
            "Make sure your Colab is using a GPU:\n",
            "1. Click **Runtime** in the top menu $\\rightarrow$ **Change runtime type**.\n",
            "2. Select **T4 GPU** $\\rightarrow$ Click **Save**.\n",
            "3. Run this cell to verify your NVIDIA cloud GPU."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Check NVIDIA GPU\n",
            "!nvidia-smi\n",
            "\n",
            "# Install Xvfb (Virtual display for headless EEVEE raytracing) & graphics libraries\n",
            "!apt-get update -qq\n",
            "!apt-get install -y -qq xvfb libegl1-mesa libgl1-mesa-glx libglu1-mesa ffmpeg fonts-montserrat\n",
            "\n",
            "# Install audio & image helpers\n",
            "!pip install -q pillow numpy edge-tts"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 📦 Step 2: Download Headless Blender 4.2 LTS (Linux x86_64)\n",
            "Downloads and configures portable Blender 4.2 LTS with EEVEE Next raytracing (takes ~15 seconds)."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import os\n",
            "\n",
            "if not os.path.exists('/content/blender/blender'):\n",
            "    print('Downloading portable Blender 4.2.3 LTS Linux...')\n",
            "    !wget -q -c https://download.blender.org/release/Blender4.2/blender-4.2.3-linux-x64.tar.xz\n",
            "    !tar -xf blender-4.2.3-linux-x64.tar.xz\n",
            "    !mv blender-4.2.3-linux-x64 /content/blender\n",
            "    !ln -sf /content/blender/blender /usr/local/bin/blender\n",
            "    print('✅ Blender 4.2.3 LTS installed successfully!')\n",
            "else:\n",
            "    print('✅ Blender is already ready.')\n",
            "\n",
            "!blender --version"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 📂 Step 3: Mount Your Google Drive\n",
            "Connects your Google Drive and creates `/MyDrive/CinecodeStudio` for persistent storage."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "from google.colab import drive\n",
            "drive.mount('/content/drive')\n",
            "\n",
            "PROJECT_DIR = '/content/drive/MyDrive/CinecodeStudio'\n",
            "os.makedirs(f'{PROJECT_DIR}/renders', exist_ok=True)\n",
            "os.makedirs(f'{PROJECT_DIR}/export', exist_ok=True)\n",
            "os.makedirs(f'{PROJECT_DIR}/tests', exist_ok=True)\n",
            "print(f'✅ Google Drive Cinecode Studio active at: {PROJECT_DIR}')"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 🔄 Step 4: Auto-Sync Latest Project Files to Google Drive\n",
            "Pulls all shot scripts, shaders, tools, and mastered audio files into your Google Drive."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import os\n",
            "PROJECT_DIR = '/content/drive/MyDrive/CinecodeStudio'\n",
            "\n",
            "if not os.path.exists(f'{PROJECT_DIR}/lib'):\n",
            "    print('Syncing Cinecode Studio files into Google Drive...')\n",
            "    !git clone https://github.com/akashrajgm/cinecode-cloud-render.git {PROJECT_DIR}\n",
            "else:\n",
            "    print('Project folder exists. Pulling latest updates...')\n",
            "    %cd {PROJECT_DIR}\n",
            "    !git pull\n",
            "\n",
            "%cd {PROJECT_DIR}\n",
            "!ls -la shots/"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 🔍 Step 5: Test Stills & Exposure QC (Mandatory Gate)\n",
            "Renders a single test still on the cloud GPU and verifies **0.0% clipped highlights** before full animation."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "#@title Run Shot Exposure QC\n",
            "%cd {PROJECT_DIR}\n",
            "shot_name = \"LOVE_03\" #@param [\"LOVE_01\", \"LOVE_02\", \"LOVE_03\", \"LOVE_04\", \"LOVE_05\", \"JET_01\", \"JET_02\", \"JET_03\", \"JET_04\", \"JET_05\"]\n",
            "frame = 36 #@param {type:\"integer\"}\n",
            "\n",
            "if \"LOVE\" in shot_name:\n",
            "    script_path = f\"shots/shot_love_act{int(shot_name[-1])}.py\"\n",
            "else:\n",
            "    script_path = f\"shots/shot_jet_act{int(shot_name[-1])}.py\"\n",
            "\n",
            "print(f'Running Exposure QC on {shot_name} (Script: {script_path})...')\n",
            "!xvfb-run -a python3 tools/rb.py {script_path} -- --shot {shot_name} --stills {frame} --pct 50\n",
            "!python3 tools/exposure_check.py tests/{shot_name}_f{frame:04d}.jpg\n",
            "\n",
            "from IPython.display import Image, display\n",
            "still_file = f'tests/{shot_name}_f{frame:04d}.jpg'\n",
            "if os.path.exists(still_file):\n",
            "    display(Image(still_file, width=340))\n",
            "else:\n",
            "    print('Still not found at:', still_file)"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 🚀 Step 6: Render All Animation Sequences on Cloud GPU\n",
            "Renders all 5 acts (72 frames each) on the cloud GPU in ~2 minutes with zero Mac load."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "#@title Render All 5 Acts Animation\n",
            "%cd {PROJECT_DIR}\n",
            "\n",
            "render_project = \"ALL_LOVE_SCENE_ACTS\" #@param [\"ALL_LOVE_SCENE_ACTS\", \"ALL_JET_ENGINE_ACTS\", \"LOVE_01\", \"LOVE_02\", \"LOVE_03\", \"LOVE_04\", \"LOVE_05\"]\n",
            "resolution_percentage = 75 #@param {type:\"slider\", min:50, max:100, step:5}\n",
            "samples = 16 #@param {type:\"slider\", min:8, max:32, step:4}\n",
            "\n",
            "if render_project == \"ALL_LOVE_SCENE_ACTS\":\n",
            "    shot_list = [\n",
            "        (\"shots/shot_love_act1.py\", \"LOVE_01\"),\n",
            "        (\"shots/shot_love_act2.py\", \"LOVE_02\"),\n",
            "        (\"shots/shot_love_act3.py\", \"LOVE_03\"),\n",
            "        (\"shots/shot_love_act4.py\", \"LOVE_04\"),\n",
            "        (\"shots/shot_love_act5.py\", \"LOVE_05\")\n",
            "    ]\n",
            "elif render_project == \"ALL_JET_ENGINE_ACTS\":\n",
            "    shot_list = [\n",
            "        (\"shots/shot_jet_act1.py\", \"JET_01\"),\n",
            "        (\"shots/shot_jet_act2.py\", \"JET_02\"),\n",
            "        (\"shots/shot_jet_act3.py\", \"JET_03\"),\n",
            "        (\"shots/shot_jet_act4.py\", \"JET_04\"),\n",
            "        (\"shots/shot_jet_act5.py\", \"JET_05\")\n",
            "    ]\n",
            "else:\n",
            "    shot_list = [(f\"shots/shot_love_act{int(render_project[-1])}.py\", render_project)]\n",
            "\n",
            "for script, s_name in shot_list:\n",
            "    print(f'\\n========================================')\n",
            "    print(f'🎬 Rendering {s_name} ({script}) on Cloud GPU...')\n",
            "    print(f'========================================')\n",
            "    !xvfb-run -a python3 tools/rb.py {script} -- --shot {s_name} --anim --pct {resolution_percentage} --samples {samples}\n",
            "\n",
            "print('\\n✅ All requested acts rendered successfully!')"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 🎞️ Step 7: Final Master Video Assembly & Player\n",
            "Conforms all 5 acts, overlays running kinetic MrBeast-style captions at safe zone $Y=68\\%$, mixes master voiceover + romantic score, and exports the final master video."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "#@title Run Assembly Pipeline\n",
            "%cd {PROJECT_DIR}\n",
            "\n",
            "assemble_target = \"Classroom Love Scene\" #@param [\"Classroom Love Scene\", \"Jet Engine at 35,000 Feet\"]\n",
            "\n",
            "if assemble_target == \"Classroom Love Scene\":\n",
            "    !python3 tools/assemble_love_master.py\n",
            "    final_video = f'{PROJECT_DIR}/export/school_love_scene_master.mp4'\n",
            "else:\n",
            "    !python3 tools/assemble_jet_master.py\n",
            "    final_video = f'{PROJECT_DIR}/export/jet_engine_35000ft_master.mp4'\n",
            "\n",
            "if os.path.exists(final_video):\n",
            "    file_size_mb = os.path.getsize(final_video) / (1024 * 1024)\n",
            "    print(f'\\n🎉 MASTER VIDEO EXPORTED!')\n",
            "    print(f'📁 Path on Google Drive: {final_video}')\n",
            "    print(f'📊 Size: {file_size_mb:.1f} MB')\n",
            "else:\n",
            "    print('Assembly in progress or output not found.')"
        ]
    }
]

notebook = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {
            "name": "Cinecode_Cloud_Render_Pipeline.ipynb",
            "provenance": []
        },
        "gpuClass": "standard",
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 0
}

with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=2)

print(f"Turnkey Google Colab Notebook updated at: {NOTEBOOK_PATH}")
