#!/usr/bin/env python3
"""Exploratory: call fal SAM 3 video tracking on the clip and inspect the output
format (overlay? matte? green-screen?) before building the alpha pipeline."""
import argparse, os, sys, subprocess
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
if not os.getenv("FAL_KEY") or "REPLACE" in os.getenv("FAL_KEY", ""):
    sys.exit("set FAL_KEY")
import fal_client

ap = argparse.ArgumentParser()
ap.add_argument("--endpoint", default="fal-ai/sam-3/video")
ap.add_argument("--video", default="output/video/video.mp4")
ap.add_argument("--prompt", default="orange flower-head cartoon character")
ap.add_argument("--apply-mask", default="false", choices=["true", "false"])
ap.add_argument("--threshold", type=float, default=0.4)
ap.add_argument("--tag", default="probe")
args = ap.parse_args()

print(f"uploading {args.video} ...")
url = fal_client.upload_file(args.video)
arguments = {
    "video_url": url,
    "prompt": args.prompt,
    "detection_threshold": args.threshold,
    "apply_mask": args.apply_mask == "true",
}
print(f"calling {args.endpoint}  prompt={args.prompt!r} apply_mask={args.apply_mask}")
res = fal_client.subscribe(args.endpoint, arguments=arguments, with_logs=True,
                           on_queue_update=lambda u: None)
print("RAW RESULT KEYS:", list(res.keys()))
print("RESULT:", {k: (v if not isinstance(v, (dict, list)) else type(v).__name__)
                   for k, v in res.items()})
vid = res.get("video") or {}
vurl = vid.get("url") if isinstance(vid, dict) else None
if not vurl:
    print("no video url; full result:", res); sys.exit()
out = Path(f"output/video/sam3_{args.tag}.mp4")
out.write_bytes(requests.get(vurl, timeout=300).content)
print(f"saved {out} ({out.stat().st_size//1024} KB)")
# pull 3 frames to inspect what the segmentation video actually is
for n in (0, 90, 180):
    subprocess.run(["ffmpeg", "-y", "-i", str(out), "-vf", f"select=eq(n\\,{n})",
                    "-frames:v", "1", f"output/video/sam3_{args.tag}_{n}.png"],
                   check=True, capture_output=True)
print("extracted probe frames")
