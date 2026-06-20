# How it was made

The technical story behind [claudius-web](README.md) — both the runtime tricks
that make the overlay work, and the asset pipeline that produced the animation.

---

## Runtime: making an overlay survive claude.ai

**Rendering past a brutal CSP.** claude.ai ships
`Content-Security-Policy: default-src 'none'` with no `media-src` and
`img-src 'self'` — so `<video>` and blob/data `<img>` are *both* blocked. (This is
why a Tampermonkey userscript can't do it; that dead-end lives in
[`claude-mascot.user.js`](claude-mascot.user.js).) A `<canvas>` isn't a resource
load, so it's exempt: the extension bundles a transparent **sprite sheet**,
`fetch`es its own packaged file, decodes it with `createImageBitmap`, and draws
frames to a canvas. No CSP tampering, no host permissions.

**Sticking to the composer through scroll + overscroll.** The composer is
`position: sticky` inside a scroll container. A `position: fixed` overlay lives in
a separate compositor layer that the macOS/Chrome rubber-band transform never
touches, so it visually detaches during the bounce. An absolute child of the
scroll *container* instead trails the composer during normal scroll (it scrolls
with content while the sticky composer stays pinned). The fix that works in every
case: attach the mascot as a child of the composer's **nearest sticky/fixed
ancestor**, so it rides the composer natively — pinned during scroll, bouncing
during overscroll, no per-frame JS correction fighting the compositor.

All of this is in [`extension/content.js`](extension/content.js).

---

## Pipeline: producing the animation

1. **Hero still** — generated in the CC0 style via image models on
   [OpenRouter](https://openrouter.ai) (`generate.py`, `prompts.py`).
2. **Motion** — image-to-video (Seedance) turns the still into a looping kicking
   clip, every frame a complete drawing (`i2v.py`, `seedance_green.py`).
3. **Transparency** — the clip was rendered on a green screen, then chroma-keyed
   to true alpha with a targeted despill (`greenkey.py`). Earlier dead-ends —
   rembg salient-object matting and SAM-3 per-frame / video tracking — are kept as
   `slice.py`, `sam3_slice.py`, `sam3_video.py`, `refine_alpha.py`, and
   `transparent.py` for the curious.
4. **Sprite sheet** — `make_sprite.py` packs the alpha frames into
   `extension/sprite.webp` for the canvas player.

### Running the pipeline

Managed with [uv](https://docs.astral.sh/uv/). Needs API keys in a local `.env`
(copy `.env.example`): `OPENROUTER_API_KEY` and `FAL_KEY`.

```bash
uv run python generate.py        # hero stills
uv run python seedance_green.py  # green-screen motion clip
uv run python greenkey.py        # chroma-key -> transparent.webm
uv run python make_sprite.py     # -> extension/sprite.webp
```

You don't need any of this to use the extension — [`extension/`](extension/) is
self-contained.
