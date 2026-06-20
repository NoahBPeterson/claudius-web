#!/usr/bin/env python3
"""Build a tight transparent sprite sheet from the alpha webm for the extension."""
import math, shutil, subprocess
from pathlib import Path
import numpy as np
from PIL import Image

V = Path("output/video"); EXT = Path("../extension"); EXT.mkdir(exist_ok=True)
tmp = EXT / "_frames"
if tmp.exists(): shutil.rmtree(tmp)
tmp.mkdir()

STEP = 2          # sample every 2nd frame -> 12 fps (source is 24)
MAXF = 48         # ~4s window; player ping-pongs it -> seamless ~8s loop
TARGET_H = 280    # frame height in the sheet (retina headroom for ~130px display)
COLS = 8

# decode alpha webm -> sampled frames (keep alpha)
subprocess.run(["ffmpeg", "-y", "-c:v", "libvpx-vp9", "-i", str(V / "transparent.webm"),
                "-vf", f"select='not(mod(n\\,{STEP}))'", "-vsync", "0", str(tmp / "%03d.png")],
               check=True, capture_output=True)
files = sorted(tmp.glob("*.png"))[:MAXF]
imgs = [Image.open(f).convert("RGBA") for f in files]

# union alpha bbox across all frames -> crop tight so the feet sit at the bottom
acc = np.zeros(np.array(imgs[0]).shape[:2], np.uint16)
for im in imgs:
    acc = np.maximum(acc, np.array(im)[..., 3])
ys, xs = np.where(acc > 8)
pad = 6
x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, imgs[0].width)
y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, imgs[0].height)
cw, ch = x1 - x0, y1 - y0
fw = round(TARGET_H * cw / ch); fh = TARGET_H

frames = [im.crop((x0, y0, x1, y1)).resize((fw, fh), Image.LANCZOS) for im in imgs]
n = len(frames); rows = math.ceil(n / COLS)
sheet = Image.new("RGBA", (COLS * fw, rows * fh), (0, 0, 0, 0))
for i, im in enumerate(frames):
    sheet.paste(im, ((i % COLS) * fw, (i // COLS) * fh), im)
sheet.save(EXT / "sprite.webp", "WEBP", lossless=True, quality=100, method=6)
shutil.rmtree(tmp)

kb = (EXT / "sprite.webp").stat().st_size // 1024
print(f"FRAMES={n} COLS={COLS} ROWS={rows} FW={fw} FH={fh} "
      f"sheet={sheet.size} size={kb}KB  aspect={fw/fh:.3f}")
