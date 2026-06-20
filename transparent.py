#!/usr/bin/env python3
"""
Make a TRANSPARENT looping video from a checkerboard-background clip, fully local
and free: ffmpeg splits frames -> rembg keys each frame -> ffmpeg restitches with
alpha (VP9-alpha webm for Chrome/Firefox, HEVC-alpha mov for Safari) plus a cream
composited mp4 as a universal fallback.

Run:  uv run python transparent.py output/video/video.mp4 [--model isnet-general-use] [--limit N]
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from rembg import remove, new_session

CREAM = (244, 236, 215)


def sh(*cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?", default="output/video/video.mp4")
    ap.add_argument("--model", default="isnet-general-use")
    ap.add_argument("--limit", type=int, default=0, help="process only first N frames (test)")
    ap.add_argument("--fps", default="24")
    ap.add_argument("--erode", type=int, default=1, help="contract alpha N px to kill halo")
    args = ap.parse_args()

    video = Path(args.video)
    work = Path("output/video/_work");
    raw = work / "raw"; cut = work / "cut"
    for d in (raw, cut):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    print("splitting frames...")
    sh("ffmpeg", "-y", "-i", str(video), str(raw / "%04d.png"))
    frames = sorted(raw.glob("*.png"))
    if args.limit:
        frames = frames[:args.limit]
    print(f"{len(frames)} frames -> keying with {args.model}")

    sess = new_session(args.model)
    t0 = time.time()
    from scipy import ndimage
    for i, f in enumerate(frames):
        rgba = remove(Image.open(f).convert("RGB"), session=sess, post_process_mask=True)
        a = np.array(rgba)
        alpha = a[..., 3]
        if args.erode:
            binm = alpha > 128
            binm = ndimage.binary_erosion(binm, iterations=args.erode)
            alpha = np.where(binm, alpha, 0)
        a[..., 3] = alpha
        # zero the RGB of fully-transparent px so no dark/grey fringe bleeds in scaling
        a[..., :3][alpha == 0] = 0
        Image.fromarray(a, "RGBA").save(cut / f.name)
        if (i + 1) % 30 == 0 or i + 1 == len(frames):
            print(f"  {i+1}/{len(frames)}  ({(time.time()-t0)/(i+1):.2f}s/frame)")

    inp = str(cut / "%04d.png")
    OUT = Path("output/video")
    webm = OUT / "transparent.webm"
    mov = OUT / "transparent.mov"
    cream_mp4 = OUT / "cream.mp4"

    print("encoding alpha webm (VP9)...")
    sh("ffmpeg", "-y", "-framerate", args.fps, "-i", inp,
       "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "28",
       "-an", str(webm))

    print("encoding alpha mov (HEVC/VideoToolbox for Safari)...")
    try:
        sh("ffmpeg", "-y", "-framerate", args.fps, "-i", inp,
           "-c:v", "hevc_videotoolbox", "-allow_sw", "1", "-alpha_quality", "0.9",
           "-vtag", "hvc1", "-pix_fmt", "bgra", "-an", str(mov))
    except subprocess.CalledProcessError as e:
        print("  HEVC-alpha failed (Safari fallback skipped):", e.stderr.decode()[-300:])

    print("encoding cream-composited mp4 (universal fallback)...")
    cr = "#%02x%02x%02x" % CREAM
    sh("ffmpeg", "-y", "-framerate", args.fps, "-i", inp,
       "-filter_complex", f"color={cr}:s=960x960[bg];[bg][0]overlay=format=auto,format=yuv420p",
       "-an", "-movflags", "+faststart", str(cream_mp4))

    for p in (webm, mov, cream_mp4):
        if p.exists():
            print(f"  {p}  ({p.stat().st_size//1024} KB)")

    # preview with a background switcher to prove transparency
    (OUT / "transparent.html").write_text(PREVIEW)
    print("\nopen output/video/transparent.html")


PREVIEW = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>transparent mascot</title>
<style>
  body{margin:0;font:14px system-ui;}
  .stage{min-height:100vh;display:flex;flex-direction:column;gap:14px;
         align-items:center;justify-content:center;transition:background .3s;}
  video{width:360px;height:auto;}
  .bar{position:fixed;top:12px;left:50%;transform:translateX(-50%);display:flex;gap:8px;}
  .bar button{border:1px solid #0003;border-radius:6px;padding:6px 10px;cursor:pointer;}
</style></head><body>
<div class="bar">
  <button onclick="bg('#F4ECD7')">cream</button>
  <button onclick="bg('#ffffff')">white</button>
  <button onclick="bg('#1A1A1A')">dark</button>
  <button onclick="bg('#3B82F6')">blue</button>
  <button onclick="checker()">checker</button>
</div>
<div class="stage" id="s">
  <video autoplay loop muted playsinline>
    <source src="transparent.webm" type="video/webm">
    <source src="transparent.mov"  type="video/quicktime">
  </video>
  <div>transparent video on a live background &mdash; webm (Chrome/FF) + mov/HEVC (Safari)</div>
</div>
<script>
  const s=document.getElementById('s');
  function bg(c){s.style.background=c;s.style.backgroundImage='none';}
  function checker(){s.style.background='#fff';
    s.style.backgroundImage='repeating-conic-gradient(#ccc 0 25%,#fff 0 50%)';
    s.style.backgroundSize='32px 32px';}
  bg('#F4ECD7');
</script>
</body></html>"""


if __name__ == "__main__":
    main()
