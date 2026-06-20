#!/usr/bin/env python3
"""
Claude-mascot image pipeline (Track A) over the OpenRouter API.

Flow:
  1. python generate.py discover            # confirm exact image-model slugs
  2. python generate.py hero                # 1 hero still per model (refs attached)
  3. <look at output/hero/*.png, pick the best>
  4. python generate.py isolate --hero output/hero/<best>.png --model nano-pro
  5. python generate.py build-rig --layers output/layers/<best> --width W --height H
  6. open output/claude-mascot-rigged.html

Track B fallback:
  python generate.py posesheet --hero output/hero/<best>.png --model nano-pro

OpenRouter image generation uses the chat-completions endpoint with
modalities:["image","text"]; returned images arrive as base64 data URLs (or http
URLs) under choices[0].message.images. Editing = same call with the source image
attached as an image_url in the user content.
"""
import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

import prompts  # noqa: E402

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS_URL = "https://openrouter.ai/api/v1/models"
REFS_DIR = ROOT.parent / "claude"          # the CC0 sticker references
REF_FILES = ["head.jpg", "claude_pet_cat.webp", "claude_minecart.webp"]
HERO_DIR = ROOT / "output" / "hero"
LAYERS_DIR = ROOT / "output" / "layers"
TIMEOUT = 240


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def key():
    k = os.getenv("OPENROUTER_API_KEY", "")
    if not k or "REPLACE_ME" in k:
        sys.exit("ERROR: set OPENROUTER_API_KEY in mascot-gen/.env first.")
    return k


def headers():
    return {
        "Authorization": f"Bearer {key()}",
        "Content-Type": "application/json",
        # OpenRouter likes these for attribution; harmless if you change them.
        "HTTP-Referer": "https://localhost/claude-mascot",
        "X-Title": "Claude Mascot Pipeline",
    }


def load_models():
    with open(ROOT / "models.json") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def data_url(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def user_msg(text, images=None):
    content = [{"type": "text", "text": text}]
    for img in images or []:
        content.append({"type": "image_url", "image_url": {"url": img}})
    return [{"role": "user", "content": content}]


def call(model_slug, text, input_images=None, retries=2):
    """Return a list of raw image bytes from one generation/edit call."""
    body = {
        "model": model_slug,
        "messages": user_msg(text, input_images),
        "modalities": ["image", "text"],
    }
    last = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(API_URL, headers=headers(), json=body, timeout=TIMEOUT)
            if r.status_code != 200:
                last = f"HTTP {r.status_code}: {r.text[:400]}"
                # 4xx (bad slug / not image-capable) won't fix on retry
                if 400 <= r.status_code < 500:
                    break
                time.sleep(2 * (attempt + 1))
                continue
            return extract_images(r.json())
        except requests.RequestException as e:
            last = str(e)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(last or "unknown error")


def extract_images(resp):
    """Pull image bytes out of an OpenRouter chat response."""
    out = []
    choices = resp.get("choices") or []
    if not choices:
        raise RuntimeError(f"no choices in response: {json.dumps(resp)[:300]}")
    msg = choices[0].get("message", {})
    imgs = msg.get("images") or []
    # Some providers nest images inside content parts instead.
    if not imgs and isinstance(msg.get("content"), list):
        for part in msg["content"]:
            if isinstance(part, dict) and part.get("type") in ("image_url", "output_image"):
                imgs.append(part)
    for item in imgs:
        url = (item.get("image_url") or {}).get("url") if isinstance(item, dict) else None
        url = url or (item.get("url") if isinstance(item, dict) else None)
        if not url:
            continue
        if url.startswith("data:"):
            out.append(base64.b64decode(url.split(",", 1)[1]))
        elif url.startswith("http"):
            out.append(requests.get(url, timeout=TIMEOUT).content)
    if not out:
        txt = msg.get("content") if isinstance(msg.get("content"), str) else ""
        raise RuntimeError(f"no image returned. model text: {txt[:300]!r}")
    return out


def save(img_bytes, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(img_bytes)
    print(f"  saved {path.relative_to(ROOT)}  ({len(img_bytes)//1024} KB)")


def refs():
    out = []
    for name in REF_FILES:
        p = REFS_DIR / name
        if p.exists():
            out.append(data_url(p))
        else:
            print(f"  (ref missing, skipping: {p})")
    return out


def pick_models(arg):
    models = load_models()
    if arg:
        wanted = [m.strip() for m in arg.split(",")]
        bad = [m for m in wanted if m not in models]
        if bad:
            sys.exit(f"unknown model key(s): {bad}. known: {list(models)}")
        return {k: models[k] for k in wanted}
    return models


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_discover(_):
    r = requests.get(MODELS_URL, headers=headers(), timeout=TIMEOUT)
    r.raise_for_status()
    rows = []
    for m in r.json().get("data", []):
        arch = m.get("architecture", {})
        outs = arch.get("output_modalities") or []
        if "image" in outs:
            rows.append((m["id"], ",".join(arch.get("input_modalities") or [])))
    rows.sort()
    print(f"\nImage-OUTPUT-capable models on your account ({len(rows)}):\n")
    for slug, ins in rows:
        print(f"  {slug:55s}  (in: {ins})")
    print("\nUpdate models.json so each friendly key maps to the right slug above.\n")


def cmd_hero(args):
    models = pick_models(args.models)
    r = refs()
    print(f"Generating hero still with {len(r)} references attached...")
    for key_name, slug in models.items():
        print(f"\n[{key_name}] {slug}")
        try:
            imgs = call(slug, prompts.HERO, input_images=r)
            for i, b in enumerate(imgs):
                suffix = "" if i == 0 else f"-{i}"
                save(b, HERO_DIR / f"{key_name}{suffix}.png")
        except Exception as e:
            print(f"  FAILED: {e}")
    print("\nDone. Compare output/hero/*.png and pick the best, then run `isolate`.")


def cmd_isolate(args):
    hero = Path(args.hero)
    if not hero.exists():
        sys.exit(f"hero not found: {hero}")
    models = pick_models(args.model)
    slug = next(iter(models.values()))
    src = data_url(hero)
    out_dir = LAYERS_DIR / hero.stem
    print(f"Isolating {len(prompts.LAYERS)} layers from {hero.name} via {slug}")
    print(f"-> {out_dir.relative_to(ROOT)}/\n")
    only = set(args.only.split(",")) if args.only else None
    for layer_key, prompt in prompts.LAYERS:
        if only and layer_key not in only:
            continue
        print(f"[{layer_key}]")
        try:
            imgs = call(slug, prompt, input_images=[src])
            save(imgs[0], out_dir / f"{layer_key}.png")
        except Exception as e:
            print(f"  FAILED: {e}")
    print("\nDone. Inspect the layers (transparency + extended joints), redo any "
          "with `--only <key>`, then run `build-rig`.")


def cmd_posesheet(args):
    hero = Path(args.hero)
    if not hero.exists():
        sys.exit(f"hero not found: {hero}")
    models = pick_models(args.model)
    slug = next(iter(models.values()))
    print(f"[Track B] 4-pose sprite sheet from {hero.name} via {slug}")
    imgs = call(slug, prompts.POSESHEET, input_images=[data_url(hero)])
    save(imgs[0], ROOT / "output" / f"posesheet-{hero.stem}.png")
    print("Done. Slice into 4 frames; I'll wire a steps() sprite animation.")


def cmd_build_rig(args):
    layers_dir = Path(args.layers)
    if not layers_dir.exists():
        sys.exit(f"layers dir not found: {layers_dir}")
    W, H = args.width, args.height
    present = {p.stem for p in layers_dir.glob("*.png")}
    dirname = layers_dir.name

    def img(k):
        if k not in present:
            print(f"  (missing layer, skipping in rig: {k})")
            return None
        return (f'<image href="layers/{dirname}/{k}.png" '
                f'x="0" y="0" width="{W}" height="{H}"/>')

    def leg(side):
        """leg group with its foot NESTED so the foot inherits the kick + flicks."""
        li, fi = img(f"leg-{side}"), img(f"foot-{side}")
        if not li and not fi:
            return None
        foot = (f'<g class="cm-foot cm-foot-{side}">{fi}</g>') if fi else ""
        return f'<g class="cm-leg cm-leg-{side}">{li or ""}{foot}</g>'

    # a drawn ledge (the art has none) -- a slab the figure sits on, legs dangling
    ledge = (f'<rect x="{int(.03*W)}" y="{int(.617*H)}" width="{int(.94*W)}" '
             f'height="{int(.40*H)}" rx="{int(.014*W)}" fill="#E7DCC2" '
             f'stroke="#1A1A1A" stroke-width="9" stroke-linejoin="round"/>')
    # z-order back -> front
    parts = [
        ledge,
        f'<g class="cm-tail">{img("tail")}</g>' if "tail" in present else None,
        leg("left"),
        leg("right"),
        img("body"),
        img("hands"),
        f'<g class="cm-head">{img("head")}</g>' if "head" in present else None,
    ]
    body = "\n".join(f"      {p}" for p in parts if p)

    # Pivots are FRACTIONS of canvas, converted to px -- measured from the SAM 3
    # layer bounding boxes (joint = where each moving part attaches).
    def px(fx, fy):
        return f"{int(fx*W)}px {int(fy*H)}px"
    origins = {
        "cm-tail":       px(0.352, 0.605),   # tail base at the hip
        "cm-head":       px(0.430, 0.576),   # neck
        "cm-leg-left":   px(0.493, 0.586),   # left hip
        "cm-leg-right":  px(0.586, 0.586),   # right hip
        "cm-foot-left":  px(0.547, 0.874),   # left ankle
        "cm-foot-right": px(0.635, 0.869),   # right ankle
    }
    html = RIG_TEMPLATE.format(
        w=W, h=H, body=body,
        o_tail=origins["cm-tail"], o_head=origins["cm-head"],
        o_legL=origins["cm-leg-left"], o_legR=origins["cm-leg-right"],
        o_footL=origins["cm-foot-left"], o_footR=origins["cm-foot-right"],
    )
    out = ROOT / "output" / "claude-mascot-rigged.html"
    out.write_text(html)
    print(f"Wrote {out.relative_to(ROOT)}  (canvas {W}x{H})")
    print("Open it; then tell me which joints look off and I'll tune the pivots.")


RIG_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Claude mascot (rigged raster)</title>
<style>
  body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#F4ECD7;}}
  .claude-mascot{{width:340px;height:auto;display:block;}}
  .claude-mascot svg{{width:100%;height:auto;overflow:visible;}}
  .cm-tail,.cm-head,.cm-leg,.cm-foot{{transform-box:view-box;}}
  .cm-bounce{{animation:cm-bounce .5s ease-in-out infinite;}}
  .cm-tail{{transform-origin:{o_tail};animation:cm-tail 2.3s ease-in-out infinite;}}
  .cm-head{{transform-origin:{o_head};animation:cm-tilt 2.0s ease-in-out infinite;}}
  .cm-leg-left{{transform-origin:{o_legL};animation:cm-kickA 1.0s ease-in-out infinite;}}
  .cm-leg-right{{transform-origin:{o_legR};animation:cm-kickB 1.0s ease-in-out infinite;}}
  .cm-foot-left{{transform-origin:{o_footL};animation:cm-flickA 1.0s ease-in-out infinite;}}
  .cm-foot-right{{transform-origin:{o_footR};animation:cm-flickB 1.0s ease-in-out infinite;}}
  @keyframes cm-bounce{{0%,100%{{transform:translateY(-3px);}}50%{{transform:translateY(0);}}}}
  @keyframes cm-tilt{{0%,100%{{transform:rotate(-3deg);}}50%{{transform:rotate(3deg);}}}}
  @keyframes cm-tail{{0%{{transform:rotate(-7deg);}}22%{{transform:rotate(6deg);}}50%{{transform:rotate(12deg);}}72%{{transform:rotate(4deg);}}100%{{transform:rotate(-7deg);}}}}
  @keyframes cm-kickA{{0%{{transform:rotate(-9deg);}}8%{{transform:rotate(-12deg);}}44%{{transform:rotate(12deg);}}52%{{transform:rotate(15deg);}}60%{{transform:rotate(11deg);}}92%{{transform:rotate(-12deg);}}100%{{transform:rotate(-9deg);}}}}
  @keyframes cm-kickB{{0%{{transform:rotate(11deg);}}8%{{transform:rotate(14deg);}}44%{{transform:rotate(-10deg);}}52%{{transform:rotate(-13deg);}}60%{{transform:rotate(-9deg);}}92%{{transform:rotate(14deg);}}100%{{transform:rotate(11deg);}}}}
  @keyframes cm-flickA{{0%,100%{{transform:rotate(5deg);}}44%{{transform:rotate(-9deg);}}60%{{transform:rotate(9deg);}}}}
  @keyframes cm-flickB{{0%,100%{{transform:rotate(-9deg);}}44%{{transform:rotate(5deg);}}60%{{transform:rotate(-11deg);}}}}
  @media (prefers-reduced-motion:reduce){{
    .cm-bounce,.cm-tail,.cm-head,.cm-leg,.cm-foot{{animation:none;}}
    .cm-leg-left{{transform:rotate(-9deg);}} .cm-leg-right{{transform:rotate(8deg);}}
  }}
</style></head>
<body>
  <div class="claude-mascot" role="img" aria-label="The Claude flower-head character sitting on a ledge, kicking its feet">
    <svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
      <g class="cm-bounce">
{body}
      </g>
    </svg>
  </div>
</body></html>
"""


def main():
    p = argparse.ArgumentParser(description="Claude-mascot OpenRouter image pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("discover", help="list image-capable model slugs on your account")

    h = sub.add_parser("hero", help="generate a hero still per model")
    h.add_argument("--models", help="comma list of friendly keys (default: all)")

    i = sub.add_parser("isolate", help="split a chosen hero into rig layers")
    i.add_argument("--hero", required=True, help="path to chosen hero PNG")
    i.add_argument("--model", default="nano-pro", help="friendly key of editor model")
    i.add_argument("--only", help="comma list of layer keys to (re)do")

    ps = sub.add_parser("posesheet", help="Track B: 4-pose sprite sheet")
    ps.add_argument("--hero", required=True)
    ps.add_argument("--model", default="nano-pro")

    b = sub.add_parser("build-rig", help="assemble rigged HTML from layer PNGs")
    b.add_argument("--layers", required=True, help="dir of layer PNGs (output/layers/<hero>)")
    b.add_argument("--width", type=int, default=1024)
    b.add_argument("--height", type=int, default=1536)

    args = p.parse_args()
    {
        "discover": cmd_discover, "hero": cmd_hero, "isolate": cmd_isolate,
        "posesheet": cmd_posesheet, "build-rig": cmd_build_rig,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
