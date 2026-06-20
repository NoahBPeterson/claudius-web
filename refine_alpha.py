#!/usr/bin/env python3
"""
Refine the transparent matte so the black OUTLINE and shoes never drop out.

Instead of trusting SAM's exact (wobbly, slightly-tight) edge, we use SAM only
to locate the character REGION, then define the precise edge by color:

    alpha = dilate(SAM_matte, --dilate)  AND  not(bright neutral-grey)

The black outline is dark (kept), the colors are chromatic (kept), the warm disc
is warm not neutral (kept) -- only the grey checkerboard background is dropped.
Because the edge is now a deterministic per-pixel color test inside a generous
region, the outline stops flickering.

Run:  uv run python refine_alpha.py [--dilate 3] [--neutral 8] [--bright 95] [--feather 0.8]
"""
import argparse, shutil, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

V = Path("output/video")


def sh(*c): subprocess.run(c, check=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=str(V / "video.mp4"))
    ap.add_argument("--matte", default=str(V / "matte.mp4"))
    ap.add_argument("--dilate", type=int, default=3, help="grow SAM region (px) to cover the outline")
    ap.add_argument("--neutral", type=int, default=8, help="max |R-G|,|G-B| to call a pixel grey")
    ap.add_argument("--bright", type=int, default=95, help="min brightness for a grey pixel to be background")
    ap.add_argument("--feather", type=float, default=0.8, help="alpha edge softening (px)")
    ap.add_argument("--fps", default="24")
    args = ap.parse_args()

    work = V / "_ref"
    raw, mat, cut = work / "raw", work / "mat", work / "cut"
    for d in (raw, mat, cut):
        if d.exists(): shutil.rmtree(d)
        d.mkdir(parents=True)

    print("splitting frames + matte...")
    sh("ffmpeg", "-y", "-i", args.video, str(raw / "%04d.png"))
    sh("ffmpeg", "-y", "-i", args.matte, str(mat / "%04d.png"))
    frames = sorted(raw.glob("*.png"))
    print(f"{len(frames)} frames  (dilate={args.dilate} neutral={args.neutral} bright={args.bright})")

    for f in frames:
        src = np.array(Image.open(f).convert("RGB"))
        rgb = src.astype(np.int16)
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        bright_grey = ((np.abs(r - g) <= args.neutral) & (np.abs(g - b) <= args.neutral)
                       & (rgb.max(-1) > args.bright))

        # SAM matte = the solid character body (excludes the ledge, fills the disc
        # so eyes stay solid). Grow it by a thin ring and add ONLY non-grey pixels
        # in that ring -> the black outline comes in, the ledge grey stays out.
        M = np.array(Image.open(mat / f.name).convert("L")) > 110
        ring = ndimage.binary_dilation(M, iterations=args.dilate) & ~M
        keep = M | (ring & ~bright_grey)

        # drop any detached specks -> keep the largest blob (the character)
        lab, n = ndimage.label(keep)
        if n > 1:
            sizes = ndimage.sum(keep, lab, range(1, n + 1))
            keep = lab == (int(np.argmax(sizes)) + 1)

        alpha = Image.fromarray((keep * 255).astype(np.uint8))
        if args.feather:
            alpha = alpha.filter(ImageFilter.GaussianBlur(args.feather))
        a = np.dstack([src, np.array(alpha)]).astype(np.uint8)
        a[..., :3][np.array(alpha) == 0] = 0
        Image.fromarray(a, "RGBA").save(cut / f.name)

    inp = str(cut / "%04d.png")
    webm, mov, cream = V / "transparent.webm", V / "transparent.mov", V / "cream.mp4"
    print("encoding alpha webm...")
    sh("ffmpeg", "-y", "-framerate", args.fps, "-i", inp, "-c:v", "libvpx-vp9",
       "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "26", "-an", str(webm))
    print("encoding alpha mov (Safari)...")
    try:
        sh("ffmpeg", "-y", "-framerate", args.fps, "-i", inp, "-c:v", "hevc_videotoolbox",
           "-allow_sw", "1", "-alpha_quality", "0.9", "-vtag", "hvc1", "-an", str(mov))
    except subprocess.CalledProcessError as e:
        print("  mov failed:", e.stderr.decode()[-200:])
    print("encoding cream fallback...")
    sh("ffmpeg", "-y", "-f", "lavfi", "-i", "color=0xF4ECD7:s=960x960",
       "-framerate", args.fps, "-i", inp,
       "-filter_complex", "[0][1]overlay=shortest=1,format=yuv420p[o]", "-map", "[o]",
       "-c:v", "libx264", "-crf", "23", "-movflags", "+faststart", str(cream))
    for p in (webm, mov, cream):
        if p.exists(): print(f"  {p.name}  {p.stat().st_size//1024} KB")


if __name__ == "__main__":
    main()
