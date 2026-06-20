#!/usr/bin/env python3
"""
Slice the mascot into registered rig layers using SAM 3 (hosted on fal.ai).

SAM 3 does promptable CONCEPT segmentation: give it a text concept and it
returns a binary mask per instance, on the ORIGINAL pixels. We cut each part,
keep it at its original canvas position, and the fake-checkerboard background
simply falls outside every mask. No color heuristics, no re-generation.

Setup:  put FAL_KEY in .env   (https://fal.ai/dashboard/keys)
Run:    uv run python sam3_slice.py output/hero/nano-pro.png
"""
import io
import os
import sys
from pathlib import Path

import numpy as np
import requests
from dotenv import load_dotenv
from PIL import Image
from scipy import ndimage

load_dotenv( Path(__file__).resolve().parents[1] / ".env")
if not os.getenv("FAL_KEY") or "REPLACE" in os.getenv("FAL_KEY", ""):
    sys.exit("ERROR: set FAL_KEY in mascot-gen/.env first (https://fal.ai/dashboard/keys)")

import fal_client  # noqa: E402  (imported after key check for a clean error)

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "output/hero/nano-pro.png")
OUT = Path("output/layers/sam3"); OUT.mkdir(parents=True, exist_ok=True)
RAW = OUT / "_masks"; RAW.mkdir(exist_ok=True)

# concept -> how many instances we expect & how to name them (split L->R by box).
CONCEPTS = [
    ("flower head",      ["head"]),
    ("purple sweater",   ["body"]),
    ("orange curly tail", ["tail"]),
    ("blue jeans pant leg", ["leg-left", "leg-right"]),
    ("brown shoe",       ["foot-left", "foot-right"]),
    ("orange hand",      ["hands"]),
]


def run_concept(image_url, prompt, n):
    res = fal_client.subscribe("fal-ai/sam-3/image", arguments={
        "image_url": image_url,
        "prompt": prompt,
        "apply_mask": False,            # we want raw masks, not overlays
        "return_multiple_masks": True,
        "max_masks": max(n, 4),
        "include_boxes": True,
        "include_scores": True,
        "output_format": "png",
    })
    out = []
    metas = res.get("metadata") or [{}] * len(res.get("masks", []))
    for m, meta in zip(res.get("masks", []), metas):
        data = requests.get(m["url"], timeout=120).content
        mask = np.array(Image.open(io.BytesIO(data)).convert("L")) > 127
        out.append({"mask": mask, "score": meta.get("score", 0), "box": meta.get("box")})
    out.sort(key=lambda d: d["score"], reverse=True)
    return out


def cx(mask):
    xs = np.where(mask.any(0))[0]
    return xs.mean() if len(xs) else 0


def drop_grey_halo(mask, rgb):
    """Remove bright neutral-grey pixels (ledge / checkerboard halo) from a mask,
    while keeping dark outlines and the warm face disc."""
    a = rgb.astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    neutral = (np.abs(r - g) < 10) & (np.abs(g - b) < 10)
    bright = a.max(-1) > 95
    return mask & ~(neutral & bright)


def extend_top(mask, px, rgb):
    """Extend the hip upward with ONE solid jeans color (the median of the leg's
    bright pixels), so a kicked leg shows clean continuous denim -- not the
    vertical streaks you get from smearing each column's jagged top edge."""
    ys, xs = np.where(mask)
    cols = rgb[ys, xs].astype(np.int16)
    bright = cols.max(1) > 110                       # jeans, excluding dark outline
    fill = np.median(cols[bright] if bright.any() else cols, axis=0).astype(np.uint8)
    out = mask.copy()
    for x in np.where(mask.any(0))[0]:
        top = int(np.where(mask[:, x])[0].min())
        lo = max(0, top - px)
        out[lo:top, x] = True
        rgb[lo:top, x] = fill
        rgb[top:top + 4, x] = fill                   # paint over the jagged cut seam
    return out


def save(name, mask, rgb, extend_up=0):
    rgb = rgb.copy()
    mask = drop_grey_halo(mask, rgb)
    mask = ndimage.binary_opening(mask, iterations=1)   # shed lone speckle pixels
    if extend_up:
        mask = extend_top(mask, extend_up, rgb)
    out = np.zeros((*mask.shape, 4), np.uint8)
    out[..., :3] = rgb
    out[..., 3] = np.where(mask, 255, 0)
    Image.fromarray(out, "RGBA").save(OUT / f"{name}.png")
    ys, xs = np.where(mask)
    bb = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if mask.any() else None
    print(f"  {name:11s} {int(mask.sum()):7d}px  bbox={bb}")


def main():
    rgb = np.array(Image.open(SRC).convert("RGB"))
    H, W = rgb.shape[:2]
    print(f"source {SRC.name} {W}x{H}\nuploading to fal...")
    image_url = fal_client.upload_file(str(SRC))

    EXTEND = {"leg-left": 45, "leg-right": 45}
    for prompt, names in CONCEPTS:
        try:
            masks = run_concept(image_url, prompt, len(names))
        except Exception as e:
            print(f"  [{prompt}] FAILED: {e}"); continue
        if not masks:
            print(f"  [{prompt}] no masks"); continue
        # save raw masks for inspection
        for i, m in enumerate(masks):
            Image.fromarray((m["mask"] * 255).astype(np.uint8)).save(
                RAW / f"{prompt.replace(' ', '_')}_{i}.png")
        if len(names) == 1:
            save(names[0], masks[0]["mask"], rgb, EXTEND.get(names[0], 0))
        else:
            # take the top-N by score, then order left->right to name them
            chosen = sorted(masks[:len(names)], key=lambda m: cx(m["mask"]))
            for name, m in zip(names, chosen):
                save(name, m["mask"], rgb, EXTEND.get(name, 0))

    # ---- preview recomposite (back -> front) ----
    comp = np.zeros((H, W, 4), np.uint8)
    for f in ["body", "leg-left", "leg-right", "foot-left", "foot-right",
              "tail", "hands", "head"]:
        p = OUT / f"{f}.png"
        if not p.exists():
            continue
        l = np.array(Image.open(p)); a = l[..., 3:4] / 255.0
        comp[..., :3] = (l[..., :3] * a + comp[..., :3] * (1 - a)).astype(np.uint8)
        comp[..., 3] = np.maximum(comp[..., 3], l[..., 3])
    Image.fromarray(comp, "RGBA").save(OUT / "_recomposite.png")
    print("\nwrote", OUT / "_recomposite.png", "and raw masks in", RAW)


if __name__ == "__main__":
    main()
