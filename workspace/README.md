# workspace — the asset pipeline

How the animated sprite in [`../extension/`](../extension/) was produced, as a
repeatable 4-stage pipeline. **You don't need this to use the extension** — the
sprite is already built and committed. This is for regenerating or remixing it.

```
workspace/
├── .env.example         # copy to .env, add your keys
├── pyproject.toml       # uv project (run everything from THIS folder)
├── reference-art/       # drop your own CC0 Claude stickers here (stage 1 input)
├── output/              # all generated artifacts land here (gitignored scratch)
├── 1-hero/              # still image     (OpenRouter)
├── 2-motion/            # image → video   (fal.ai)
├── 3-transparency/      # green-screen → transparent  (local, ffmpeg)
├── 4-sprite/            # video → sprite sheet         (local)
└── attic/               # abandoned approaches, kept for the record
```

## Setup (once)

```bash
cd workspace
cp .env.example .env      # then fill in OPENROUTER_API_KEY and FAL_KEY
```

Managed with [uv](https://docs.astral.sh/uv/) — `uv run` auto-syncs deps. **Run
every command from this `workspace/` folder** (paths and `.env` resolve here).

## The pipeline

### 1 · Hero still — `1-hero/` (OpenRouter)
A single hand-drawn character still, in the CC0 style. Put a few reference
stickers in `reference-art/` first (they're attached to the prompt for fidelity).

```bash
uv run python 1-hero/generate.py discover        # list image models on your account
uv run python 1-hero/generate.py hero            # -> output/hero/*.png
```

Pick the best result. The full character spec lives in `1-hero/prompts.py`;
model slugs in `1-hero/models.json`.

### 2 · Motion on a green screen — `2-motion/` (fal.ai)
Animate the still into a looping "kicking feet" clip. **Green screen is the key
decision** — green appears nowhere in the character, so the next stage can key it
out exactly. Either run the script (it expects a green-background hero) or feed
your own green-screen clip straight to stage 3.

```bash
uv run python 2-motion/seedance_green.py --duration 5    # -> output/video/green_raw.mp4
```

The model is **Seedance 2.0 image-to-video** (`bytedance/seedance-2.0/image-to-video`
on fal). The exact prompt:

> A flat 2D hand-drawn cartoon character with a big orange flower-burst head sits
> and happily kicks its dangling legs, swinging its feet back and forth; its long
> thin orange tail gently sways and curls; the petals bob slightly; cheerful
> relaxed idle motion. **The background is a FLAT SOLID GREEN screen and MUST stay
> perfectly flat, uniform, solid green the entire time — do NOT add any ledge,
> furniture, scenery, shadows, gradients, reflections or background elements of
> any kind.** Static locked-off camera: no zoom, no pan, no parallax. The
> character stays centered in the same spot. Preserve the flat colors and thick
> black hand-drawn outlines in every frame. Clean 2D animation.

Negative-prompt equivalents (no camera motion, no scenery, no 3D, no morphing)
are baked into the script.

### 3 · Green-screen → transparent — `3-transparency/` (local, free)
Chroma-key the green to true alpha, with a targeted despill that removes the
green fringe without tinting the cream face. No API, runs on ffmpeg + numpy.

```bash
uv run python 3-transparency/greenkey.py output/video/<your-green-clip>.mp4
# -> output/video/transparent.webm (+ .mov for Safari, + cream.mp4 fallback)
```

Tune with `--lo/--hi` (green-excess key thresholds), `--erode`, `--feather`.

### 4 · Sprite sheet — `4-sprite/` (local, free)
Pack the transparent frames into the sheet the extension draws to a `<canvas>`.

```bash
uv run python 4-sprite/make_sprite.py        # reads output/video/transparent.webm
# -> ../extension/sprite.webp  (+ prints the SP={...} metadata)
```

If the printed `FRAMES/COLS/FW/FH` change, update the `SP = {...}` line at the top
of [`../extension/content.js`](../extension/content.js).

---

The `attic/` folder holds approaches that didn't make the cut (Kling i2v, rembg
matting, SAM-3 per-frame and video tracking, the cut-out CSS rig, the Tampermonkey
userscript). See [`attic/README.md`](attic/README.md).
