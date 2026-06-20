#!/usr/bin/env python3
"""
Chroma-key a GREEN-SCREEN clip to transparent (local, exact). Green appears
nowhere in the character, so keying is unambiguous -- no SAM, no grey heuristics.

  key:     green-excess gn = G - max(R,B);  background where gn is high
  despill: G = min(G, max(R,B))   -> neutralizes green fringe, leaves other colors
  edge:    1px erosion + slight feather

Run:  uv run python greenkey.py "output/video/video(1).mp4" [--lo 45 --hi 120 --erode 1 --feather 0.6]
"""
import argparse, shutil, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

V = Path("output/video")


def sh(*c): subprocess.run(c, check=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?", default="output/video/video(1).mp4")
    ap.add_argument("--lo", type=int, default=45, help="green-excess fully OPAQUE below this")
    ap.add_argument("--hi", type=int, default=120, help="green-excess fully TRANSPARENT above this")
    ap.add_argument("--erode", type=int, default=1)
    ap.add_argument("--feather", type=float, default=0.6)
    ap.add_argument("--fps", default="24")
    args = ap.parse_args()

    work = V / "_gk"; raw, cut = work / "raw", work / "cut"
    for d in (raw, cut):
        if d.exists(): shutil.rmtree(d)
        d.mkdir(parents=True)

    print("splitting frames...")
    sh("ffmpeg", "-y", "-i", args.video, str(raw / "%04d.png"))
    frames = sorted(raw.glob("*.png"))
    print(f"{len(frames)} frames  (lo={args.lo} hi={args.hi} erode={args.erode})")

    for f in frames:
        rgb = np.array(Image.open(f).convert("RGB")).astype(np.int16)
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        gn = g - np.maximum(r, b)                         # green excess
        alpha = np.clip((args.hi - gn) / (args.hi - args.lo), 0, 1)
        keep = alpha > 0.04
        if args.erode:
            keep = ndimage.binary_erosion(keep, iterations=args.erode)
        # largest blob only (drop stray keyed specks)
        lab, n = ndimage.label(keep)
        if n > 1:
            keep = lab == (int(np.argmax(ndimage.sum(keep, lab, range(1, n + 1)))) + 1)
        alpha = np.where(keep, alpha, 0)
        out = rgb.copy()
        out[..., 1] = np.minimum(g, np.maximum(r, b))     # despill green fringe
        A = (np.clip(alpha, 0, 1) * 255).astype(np.uint8)
        if args.feather:
            A = np.array(Image.fromarray(A).filter(ImageFilter.GaussianBlur(args.feather)))
        rgba = np.dstack([out.astype(np.uint8), A])
        rgba[..., :3][A == 0] = 0
        Image.fromarray(rgba, "RGBA").save(cut / f.name)

    inp = str(cut / "%04d.png")
    webm, mov, cream = V / "transparent.webm", V / "transparent.mov", V / "cream.mp4"
    print("alpha webm (VP9)..."); sh("ffmpeg", "-y", "-framerate", args.fps, "-i", inp,
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "24", "-an", str(webm))
    print("alpha mov (HEVC/Safari)...")
    try:
        sh("ffmpeg", "-y", "-framerate", args.fps, "-i", inp, "-c:v", "hevc_videotoolbox",
           "-allow_sw", "1", "-alpha_quality", "0.9", "-vtag", "hvc1", "-an", str(mov))
    except subprocess.CalledProcessError as e:
        print("  mov failed:", e.stderr.decode()[-200:])
    print("cream fallback...")
    sh("ffmpeg", "-y", "-f", "lavfi", "-i", "color=0xF4ECD7:s=960x960", "-framerate", args.fps,
       "-i", inp, "-filter_complex", "[0][1]overlay=shortest=1,format=yuv420p[o]", "-map", "[o]",
       "-c:v", "libx264", "-crf", "23", "-movflags", "+faststart", str(cream))
    for p in (webm, mov, cream):
        if p.exists(): print(f"  {p.name}  {p.stat().st_size//1024} KB")
    shutil.rmtree(work)


if __name__ == "__main__":
    main()
