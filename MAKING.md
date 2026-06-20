# How it was made

The technical story behind [claudius-web](README.md) — both the runtime tricks
that make the overlay work, and the asset pipeline that produced the animation.

---

## Runtime: making an overlay survive claude.ai

**Rendering past a brutal CSP.** claude.ai ships
`Content-Security-Policy: default-src 'none'` with no `media-src` and
`img-src 'self'` — so `<video>` and blob/data `<img>` are *both* blocked. (This is
why a Tampermonkey userscript can't do it; that dead-end lives in
[`workspace/attic/claude-mascot.user.js`](workspace/attic/claude-mascot.user.js).)
A `<canvas>` isn't a resource load, so it's exempt: the extension bundles a
transparent **sprite sheet**, `fetch`es its own packaged file, decodes it with
`createImageBitmap`, and draws frames to a canvas. No CSP tampering, no host
permissions.

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

A 4-stage pipeline (full runnable details + the exact prompts in
[`workspace/README.md`](workspace/README.md)):

1. **Hero still** — generated in the CC0 style via image models on
   [OpenRouter](https://openrouter.ai) — [`workspace/1-hero/`](workspace/1-hero/).
2. **Motion** — Seedance 2.0 image-to-video turns the still into a looping
   kicking clip, every frame a complete drawing, **on a green screen** —
   [`workspace/2-motion/`](workspace/2-motion/).
3. **Transparency** — the green is chroma-keyed to true alpha with a targeted
   despill — [`workspace/3-transparency/`](workspace/3-transparency/).
4. **Sprite sheet** — the alpha frames are packed into
   [`extension/sprite.webp`](extension/) for the canvas player —
   [`workspace/4-sprite/`](workspace/4-sprite/).

**The key insight, learned the hard way:** don't fight an ambiguous background.
We burned real effort trying to matte the character off a checkerboard/ledge with
rembg and SAM-3 (grey background ≈ grey ledge ≈ anti-aliasing → endless edge
artifacts). Re-shooting on a flat green screen made the matte exact and free. The
abandoned approaches are preserved in
[`workspace/attic/`](workspace/attic/README.md).
