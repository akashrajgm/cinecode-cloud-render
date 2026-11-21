"""Render-safe Blender runner (v2) - Cross-platform (macOS / Linux / Windows).

Every Blender invocation (tests, stills, final renders) must go through this script:
  <blender python> film/tools/rb.py <script.py> [-- script args...]
  <blender python> film/tools/rb.py --blend file.blend [blender args...]
"""
import os, sys, time, subprocess, json, threading, signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
DEFAULT_BLENDER = "/opt/homebrew/bin/blender" if sys.platform != "win32" else r"E:\experimentswithclaude\tools\blender\blender-5.2.2-windows-x64\blender.exe"
BLENDER = os.environ.get("BLENDER", DEFAULT_BLENDER)
GUARD = os.path.join(TOOLS, "gpu_guard.py")
LOG = os.path.join(TOOLS, "render_log.jsonl")
MAX_SLOTS = 1
TIMEOUT = 60 * 60 * 6

def pid_alive(pid):
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True).stdout
            return str(pid).encode() in out
        except Exception:
            return True
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

def kill_proc(p):
    if p is None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
        else:
            p.terminate()
            time.sleep(0.5)
            if p.poll() is None:
                p.kill()
    except Exception:
        pass

def acquire_slot(tag):
    waited = 0
    names = [str(i) for i in range(MAX_SLOTS)]
    while True:
        for i in names:
            p = os.path.join(TOOLS, f".slot.{i}")
            try:
                fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, json.dumps({"pid": os.getpid(), "tag": tag, "t": time.time()}).encode())
                os.close(fd)
                return p
            except FileExistsError:
                try:
                    info = json.load(open(p))
                    if not pid_alive(info.get("pid", -1)):
                        os.remove(p)
                except Exception:
                    pass
        if waited % 60 == 0:
            print(f"[rb] waiting for a Blender slot ({waited}s)...", flush=True)
        time.sleep(2)
        waited += 2

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    if args[0] == "--blend":
        cmd = [BLENDER, "-b", args[1], "--python", GUARD] + args[2:]
        tag = os.path.basename(args[1])
    else:
        script, rest = args[0], args[1:]
        cmd = [BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "--python", GUARD, "--python", script] + rest
        tag = os.path.basename(script)
    slot = acquire_slot(tag)
    t0 = time.time()
    rc = -1
    box = {"p": None}
    limit = TIMEOUT if "--anim" in args else 60 * 60

    def _watchdog():
        while box["p"] is None or box["p"].poll() is None:
            time.sleep(5)
            p = box["p"]
            if p is not None and p.poll() is None and time.time() - t0 > limit:
                print(f"[rb] TIMEOUT after {limit}s, killing Blender", flush=True)
                kill_proc(p)
                return
    threading.Thread(target=_watchdog, daemon=True).start()
    try:
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x00004000
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", **kwargs)
        box["p"] = p
        for line in p.stdout:
            if "Rendering" in line and "/" in line and "sample" in line.lower():
                continue
            sys.stdout.write(line)
        rc = p.wait()
    finally:
        p = box["p"]
        kill_proc(p)
        try:
            os.remove(slot)
        except FileNotFoundError:
            pass
        lk = os.path.join(TOOLS, ".blender.lock")
        try:
            info = json.load(open(lk))
            if p is not None and info.get("pid") == p.pid:
                os.remove(lk)
        except Exception:
            pass
        dt = time.time() - t0
        with open(LOG, "a") as f:
            f.write(json.dumps({"tag": tag, "cmd": cmd[3:], "rc": rc, "sec": round(dt, 1), "t": time.time()}) + "\n")
        print(f"[rb] done rc={rc} in {dt:.1f}s", flush=True)
    sys.exit(rc)

if __name__ == "__main__":
    main()
