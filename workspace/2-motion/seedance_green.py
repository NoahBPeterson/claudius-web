#!/usr/bin/env python3
"""Roll a green-screen kicking loop on Seedance 2.0 (fal) from the green hero."""
import argparse, os, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv( Path(__file__).resolve().parents[1] / ".env")
if not os.getenv("FAL_KEY") or "REPLACE" in os.getenv("FAL_KEY", ""):
    sys.exit("set FAL_KEY")
import fal_client

PROMPT = (
    "A flat 2D hand-drawn cartoon character with a big orange flower-burst head sits "
    "and happily kicks its dangling legs, swinging its feet back and forth; its long "
    "thin orange tail gently sways and curls; the petals bob slightly; cheerful relaxed "
    "idle motion. The background is a FLAT SOLID GREEN screen and MUST stay perfectly "
    "flat, uniform, solid green the entire time — do NOT add any ledge, furniture, "
    "scenery, shadows, gradients, reflections or background elements of any kind. "
    "Static locked-off camera: no zoom, no pan, no parallax. The character stays "
    "centered in the same spot. Preserve the flat colors and thick black hand-drawn "
    "outlines in every frame. Clean 2D animation."
)

ap = argparse.ArgumentParser()
ap.add_argument("--hero", default="output/hero/green_hero.png")
ap.add_argument("--duration", default="5")
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--tag", default="green")
ap.add_argument("--loop-frame", action="store_true", help="pin end frame = start (return-to-start)")
args = ap.parse_args()

print(f"uploading {args.hero} ...")
url = fal_client.upload_file(args.hero)
arguments = {
    "prompt": PROMPT,
    "image_url": url,
    "resolution": "1080p",
    "duration": args.duration,
    "aspect_ratio": "1:1",
    "generate_audio": False,
    "seed": args.seed,
}
if args.loop_frame:
    arguments["end_image_url"] = url

print(f"rolling Seedance 2.0 (dur={args.duration}s seed={args.seed} loop_frame={args.loop_frame})...")
res = fal_client.subscribe("bytedance/seedance-2.0/image-to-video", arguments=arguments,
                           with_logs=True, on_queue_update=lambda u: None)
out = Path(f"output/video/{args.tag}_raw.mp4")
out.write_bytes(requests.get(res["video"]["url"], timeout=600).content)
print(f"saved {out} ({out.stat().st_size//1024} KB)  seed={res.get('seed')}")
