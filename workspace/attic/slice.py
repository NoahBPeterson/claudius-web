#!/usr/bin/env python3
"""
Local, model-free layer slicer for the flat color-coded mascot art.

Every pixel is classified to the NEAREST palette centroid. Grey centroids
(the fake checkerboard background AND the stone ledge) are discarded; the
chromatic character colors are kept. Black outline pixels are reassigned to
the nearest colored region. Same-color regions are split into instances by
connected components. Output layers are RGBA at the ORIGINAL canvas position,
so they stack back perfectly.

Usage: uv run python slice.py output/hero/nano-pro.png
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "output/hero/nano-pro.png")
OUT = Path("output/layers/local"); OUT.mkdir(parents=True, exist_ok=True)

# chromatic character colors (greys are handled by saturation, not centroids).
COLORS = {
    "terracotta": (208, 96, 64), "blue": (128, 176, 192),
    "white": (240, 240, 224),    "lavender": (192, 160, 208),
    "brown": (80, 48, 32),
}
NAMES = list(COLORS) + ["black"]
CENT = np.array([COLORS[n] for n in COLORS], dtype=np.int16)
BG, BLACK = -1, len(COLORS)            # label sentinels
SAT_MIN, DARK_MAX = 30, 78             # grey if sat<SAT_MIN & bright; black if max<DARK_MAX


def classify(rgb):
    """Label per pixel: greys(by low saturation)->BG, dark->BLACK, else nearest color.

    Saturation-first keeps the grey checkerboard AND grey ledge out, while the
    near-black outlines (low sat but very dark) are preserved as their own class.
    """
    a = rgb.astype(np.int16)
    mx, mn = a.max(-1), a.min(-1)
    sat = mx - mn
    lab = np.full(rgb.shape[:2], BG, np.int16)
    chromatic = sat >= SAT_MIN
    black = (~chromatic) & (mx < DARK_MAX)
    d = ((a[:, :, None, :] - CENT[None, None]) ** 2).sum(-1)
    nearest = d.argmin(-1).astype(np.int16)
    lab[chromatic] = nearest[chromatic]
    lab[black] = BLACK
    return lab


def mask_for(lab, *names):
    m = np.zeros(lab.shape, bool)
    for n in names:
        m |= lab == NAMES.index(n)
    return m


def reassign_black(lab, keep_mask):
    """give each black pixel the color label of its nearest colored neighbor."""
    black = lab == NAMES.index("black")
    colored = keep_mask & ~black
    if not colored.any():
        return lab
    # nearest colored pixel index for every pixel
    idx = ndimage.distance_transform_edt(~colored, return_distances=False,
                                         return_indices=True)
    nearest = lab[tuple(idx)]
    out = lab.copy()
    out[black] = nearest[black]
    return out


def components(mask, min_px=400):
    lbl, n = ndimage.label(mask)
    comps = []
    for i in range(1, n + 1):
        m = lbl == i
        if m.sum() < min_px:
            continue
        ys, xs = np.where(m)
        comps.append({"mask": m, "cx": xs.mean(), "cy": ys.mean(),
                      "x0": xs.min(), "x1": xs.max(), "y0": ys.min(), "y1": ys.max(),
                      "n": int(m.sum())})
    return comps


def save_layer(name, mask, rgb, extend_up=0):
    if extend_up:
        mask = extend_top(mask, extend_up, rgb)
    out = np.zeros((*mask.shape, 4), np.uint8)
    out[..., :3] = rgb
    out[..., 3] = np.where(mask, 255, 0)
    Image.fromarray(out, "RGBA").save(OUT / f"{name}.png")
    ys, xs = np.where(mask)
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if mask.any() else None
    print(f"  {name:11s} {int(mask.sum()):7d}px  bbox={bbox}")


def extend_top(mask, px, rgb):
    """fill upward from each column's topmost pixel so a moving joint shows no gap."""
    out = mask.copy()
    cols = np.where(mask.any(0))[0]
    for x in cols:
        ys = np.where(mask[:, x])[0]
        top = ys.min()
        lo = max(0, top - px)
        out[lo:top, x] = True
        rgb[lo:top, x] = rgb[top, x]   # carry the column's color upward
    return out


def main():
    im = Image.open(SRC).convert("RGB")
    rgb = np.array(im)
    H, W = rgb.shape[:2]
    print(f"source {SRC.name} {W}x{H}")
    lab = classify(rgb)

    keep = lab != BG                          # character = non-grey
    lab = reassign_black(lab, keep)           # outlines -> nearest color
    keep = lab != BG

    blue = mask_for(lab, "blue") & keep
    brown = mask_for(lab, "brown") & keep
    lav = mask_for(lab, "lavender") & keep
    terra_only = mask_for(lab, "terracotta") & keep
    white = mask_for(lab, "white") & keep

    print("component scan:")
    for nm, m in [("blue", blue), ("brown", brown), ("lavender", lav),
                  ("terracotta", terra_only)]:
        cs = components(m)
        print(f"  {nm}: {len(cs)} parts " +
              ", ".join(f"[cx={c['cx']:.0f},cy={c['cy']:.0f},n={c['n']}]" for c in cs))

    # ---- legs (blue): split into L/R ----
    legs = sorted(components(blue), key=lambda c: c["cx"])
    print("\nwriting layers:")
    if len(legs) >= 2:
        save_layer("leg-left", legs[0]["mask"], rgb.copy(), extend_up=120)
        save_layer("leg-right", legs[-1]["mask"], rgb.copy(), extend_up=120)
    elif legs:
        # touching: split at vertical midline of the blob
        m = legs[0]["mask"]; mid = int((legs[0]["x0"] + legs[0]["x1"]) / 2)
        L = m.copy(); L[:, mid:] = False
        R = m.copy(); R[:, :mid] = False
        save_layer("leg-left", L, rgb.copy(), extend_up=120)
        save_layer("leg-right", R, rgb.copy(), extend_up=120)

    # ---- feet (brown): split into L/R ----
    feet = sorted(components(brown), key=lambda c: c["cx"])
    for nm, c in zip(["foot-left", "foot-right"], feet[:2] if len(feet) >= 2 else []):
        save_layer(nm, c["mask"], rgb.copy())

    # ---- body (lavender sweater + arms) as one base layer ----
    save_layer("body", lav, rgb.copy())

    # ---- head: bridge the petal/outline gaps, take the blob around the disc ----
    # disc centre = centroid of the largest white component (the face)
    disc = max(components(white, min_px=200), key=lambda c: c["n"])
    head_colors = terra_only | white
    bridged = ndimage.binary_dilation(head_colors, iterations=7)
    hl, _ = ndimage.label(bridged)
    head_region = hl == hl[int(disc["cy"]), int(disc["cx"])]
    head_mask = head_region & (terra_only | white)
    save_layer("head", head_mask, rgb.copy())

    # ---- tail + hands = terracotta outside the head ----
    rest = components(terra_only & ~head_region, min_px=300)
    if rest:
        tail = max(rest, key=lambda c: c["n"])           # tail = biggest leftover
        save_layer("tail", tail["mask"], rgb.copy(), extend_up=40)
        hands = [c for c in rest if c is not tail]
        if hands:
            hm = np.zeros((H, W), bool)
            for c in hands:
                hm |= c["mask"]
            save_layer("hands", hm, rgb.copy())

    # ---- preview recomposite ----
    comp = np.zeros((H, W, 4), np.uint8)
    for f in ["body", "leg-left", "leg-right", "foot-left", "foot-right",
              "tail", "hands", "head"]:
        p = OUT / f"{f}.png"
        if not p.exists():
            continue
        l = np.array(Image.open(p))
        a = l[..., 3:4] / 255.0
        comp[..., :3] = (l[..., :3] * a + comp[..., :3] * (1 - a)).astype(np.uint8)
        comp[..., 3] = np.maximum(comp[..., 3], l[..., 3])
    Image.fromarray(comp, "RGBA").save(OUT / "_recomposite.png")
    print("\nwrote", OUT / "_recomposite.png")


if __name__ == "__main__":
    main()
