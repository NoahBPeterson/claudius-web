# Claude mascot — browser extension

Sits the flower-Claude character on top of the claude.ai message box, kicking its
feet. Renders to a `<canvas>` so it works under claude.ai's strict CSP
(`default-src 'none'`, no `media-src`, `img-src 'self'`) — no `<video>`, no `<img>`,
no header rewriting, no special permissions.

## Files
- `manifest.json` — MV3, works in Chrome and Firefox
- `content.js` — finds the composer, draws the sprite to a canvas, keeps it perched
- `sprite.webp` — 48-frame transparent sprite sheet (8×6, 198×280 per frame)

## Install — Chrome (or Edge/Brave)
1. Go to `chrome://extensions`
2. Toggle **Developer mode** (top-right)
3. **Load unpacked** → select this `extension/` folder
4. Open/reload **claude.ai** → Claude perches on the message box
   *(Chrome may log a harmless warning about `browser_specific_settings` — ignore it.)*

## Install — Firefox
1. Go to `about:debugging#/runtime/this-firefox`
2. **Load Temporary Add-on…** → select `manifest.json` inside this folder
3. Reload **claude.ai**

Note: a *temporary* add-on is removed when Firefox restarts. To install permanently
you must sign it at addons.mozilla.org (`web-ext sign`) or use Firefox Developer
Edition with `xpinstall.signatures.required = false`.

## Tuning (all at the top of `content.js`)
| const | does |
|-------|------|
| `DISPLAY_W` | mascot width in px |
| `OVERLAP` | fraction of the mascot that dips below the box's top edge (0 = fully above, 1 = fully below) |
| `FPS` | playback speed |
| `findComposer()` | the selector for the message box it perches on |

After editing, hit the **reload** ↻ on the extension card (Chrome) or re-load the
temporary add-on (Firefox), then reload claude.ai.

## Regenerating the sprite
From `mascot-gen/`: `uv run python make_sprite.py` (re-reads
`output/video/transparent.webm`). Update the `SP = {...}` line in `content.js` if
the printed `FRAMES/COLS/FW/FH` change.

---
Character design by thebes (@voooooogel, vgel.me), CC0. Fan project, not affiliated
with Anthropic.
