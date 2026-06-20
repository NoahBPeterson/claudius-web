#!/usr/bin/env python3
"""
Image-to-video: animate the hero still into a looping "kicking feet" clip via a
video model on fal. Every frame is a COMPLETE drawing (tail bends, torso present,
legs don't cross) -- the things a flat cutout rig can't do.

Loop strategy: tail_image_url = image_url (model animates away and back), and we
also ping-pong in post (forward + reverse) for a guaranteed-seamless idle loop.

Setup:  FAL_KEY in .env
Run:    uv run python i2v.py [hero.png] [--model MODEL] [--prompt "..."]
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
if not os.getenv("FAL_KEY") or "REPLACE" in os.getenv("FAL_KEY", ""):
    sys.exit("ERROR: set FAL_KEY in mascot-gen/.env first")
import fal_client  # noqa: E402

OUT = Path("output/video"); OUT.mkdir(parents=True, exist_ok=True)

DEFAULT_PROMPT = (
    "A flat 2D hand-drawn cartoon character with a big orange flower-burst head "
    "sits on the edge of a stone ledge and happily kicks its dangling legs, "
    "swinging its feet back and forth; its long thin orange tail gently sways and "
    "curls; the petals and head bob slightly; cheerful relaxed idle motion. "
    "The camera is completely static and locked off — no zoom, no pan, no parallax. "
    "The character stays centered in the exact same spot. Preserve the original "
    "flat coloring, thick black hand-drawn outlines and 2D cartoon style in every "
    "frame. Smooth clean 2D animation."
)
NEG = ("camera motion, zoom, pan, dolly, 3d render, realism, photorealistic, "
       "morphing face, melting, extra limbs, distorted petals, text, watermark, "
       "background change, blur, low quality, jitter")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hero", nargs="?", default="output/hero/nano-pro.png")
    ap.add_argument("--model", default="fal-ai/kling-video/v2.1/pro/image-to-video")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--duration", default="5")
    ap.add_argument("--cfg", type=float, default=0.5)
    ap.add_argument("--no-loop-frame", action="store_true",
                    help="don't pin the end frame to the start image")
    ap.add_argument("--tag", default="kick")
    args = ap.parse_args()

    hero = Path(args.hero)
    if not hero.exists():
        sys.exit(f"hero not found: {hero}")
    print(f"uploading {hero.name} ...")
    url = fal_client.upload_file(str(hero))

    arguments = {
        "prompt": args.prompt,
        "image_url": url,
        "negative_prompt": NEG,
        "duration": args.duration,
        "cfg_scale": args.cfg,
        "aspect_ratio": "1:1",
    }
    if not args.no_loop_frame:
        arguments["tail_image_url"] = url      # end == start  -> animate back

    print(f"generating with {args.model} (duration {args.duration}s)... this takes a minute or two")
    res = fal_client.subscribe(args.model, arguments=arguments, with_logs=True,
                               on_queue_update=lambda u: None)
    video_url = res["video"]["url"]
    raw = OUT / f"{args.tag}_raw.mp4"
    raw.write_bytes(requests.get(video_url, timeout=300).content)
    print(f"saved {raw}  ({raw.stat().st_size//1024} KB)")

    # ping-pong -> seamless loop (forward then reversed), re-encoded web-friendly
    loop_mp4 = OUT / f"{args.tag}_loop.mp4"
    webm = OUT / f"{args.tag}_loop.webm"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw),
        "-filter_complex", "[0]reverse[r];[0][r]concat=n=2:v=1:a=0,setpts=N/FRAME_RATE/TB[v]",
        "-map", "[v]", "-an", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(loop_mp4)], check=True, capture_output=True)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(loop_mp4), "-an",
        "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32", str(webm)],
        check=True, capture_output=True)
    print(f"wrote seamless loop:\n  {loop_mp4}\n  {webm}")

    # quick contact sheet of frames to eyeball
    sheet = OUT / f"{args.tag}_frames.png"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw), "-vf",
        "select='not(mod(n\\,15))',scale=256:-1,tile=5x1", "-frames:v", "1", str(sheet)],
        check=True, capture_output=True)
    print(f"  {sheet}  (frame strip)")


if __name__ == "__main__":
    main()
