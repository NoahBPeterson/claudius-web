# 🌻 Claude mascot — kicking feet

A browser extension that perches the hand-drawn flower-**Claude** character on top
of the [claude.ai](https://claude.ai) message box, happily kicking its feet while
you chat.

<!-- swap in a screen recording / gif here -->

The character design is by **thebes** ([@voooooogel](https://x.com/voooooogel),
[vgel.me](https://vgel.me)), released **CC0**. This is a fan project and is **not
affiliated with Anthropic**.

---

## Install (developer mode)

### Chrome / Edge / Brave
1. `chrome://extensions` → enable **Developer mode**
2. **Load unpacked** → select the [`extension/`](extension/) folder
3. Reload **claude.ai**

### Firefox
1. `about:debugging#/runtime/this-firefox`
2. **Load Temporary Add-on…** → pick `extension/manifest.json`
3. Reload **claude.ai**

See [`extension/README.md`](extension/README.md) for tuning knobs (size, side,
perch height, speed) and packaging notes.

---

## How it works (the interesting bits)

**Rendering past a brutal CSP.** claude.ai ships
`Content-Security-Policy: default-src 'none'` with no `media-src` and
`img-src 'self'` — so `<video>` and blob/data `<img>` are *both* blocked. (This is
why a Tampermonkey userscript can't do it.) A `<canvas>` isn't a resource load, so
it's exempt: the extension bundles a transparent **sprite sheet**, `fetch`es its
own packaged file, decodes it with `createImageBitmap`, and draws frames to a
canvas. No CSP tampering, no host permissions.

**Sticking to the composer through scroll + overscroll.** The composer is
`position: sticky` inside a scroll container. A `position: fixed` overlay lives in
a separate compositor layer that the macOS/Chrome rubber-band transform never
touches, so it visually detaches during the bounce. The fix: attach the mascot as
a child of the composer's **nearest sticky/fixed ancestor**, so it rides the
composer natively — pinned during scroll, bouncing during overscroll.

## How the art was made

The animation was produced by a small pipeline (scripts in this repo):

1. **Hero still** — generated in the CC0 style via image models on
   [OpenRouter](https://openrouter.ai) (`generate.py`, `prompts.py`).
2. **Motion** — image-to-video (Seedance) turns the still into a looping
   kicking clip, every frame a complete drawing.
3. **Transparency** — the clip was rendered on a green screen, then chroma-keyed
   to true alpha with a targeted despill (`greenkey.py`). Earlier dead-ends
   (rembg salient-object matting, SAM-3 per-frame and video tracking) are kept in
   the repo as `*_slice.py` / `transparent.py` for the curious.
4. **Sprite sheet** — `make_sprite.py` packs the alpha frames into
   `extension/sprite.webp` for the canvas player.

The pipeline needs API keys (`OPENROUTER_API_KEY`, `FAL_KEY`) in a local `.env` —
see `.env.example`. It is managed with [uv](https://docs.astral.sh/uv/):
`uv run python make_sprite.py`, etc. You don't need any of this to use the
extension — `extension/` is self-contained.

---

## License

Code: MIT. Character: CC0 by thebes. Anthropic's burst logo is their trademark;
this is fan use — don't ship it commercially or imply official endorsement.
