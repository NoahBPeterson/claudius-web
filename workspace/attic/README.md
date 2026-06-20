# attic — roads not taken

Approaches we built and abandoned. Kept because the journey is half the point —
and because each one failed for an instructive reason. None of these are wired
into the final pipeline.

| file | what it tried | why it lost |
|------|---------------|-------------|
| `claude-mascot.user.js` | Tampermonkey userscript overlay | claude.ai's CSP (`default-src 'none'`, no `media-src`) blocks `<video>` and blob/data `<img>`. Couldn't render. → became the canvas-based extension. |
| `i2v.py` | Kling image-to-video | Decent, but Seedance 2.0 gave better, more on-model motion. |
| `slice.py` | local color-segmentation into body parts | Built for a cut-out CSS rig (rotate limbs around joints). A paper-doll can't deform — tail looked detached, legs crossed, torso had holes. → went full-frame video instead. |
| `sam3_slice.py` | SAM-3 (image) part isolation | Same cut-out-rig dead end; segmenting a still can't animate. |
| `sam3_video.py` | SAM-3 video object tracking for the matte | Worked, but once we re-shot on a green screen, a plain chroma key was exact and free. |
| `refine_alpha.py` | matte clean-up over a checkerboard bg | Whack-a-mole: grey background ≈ grey ledge ≈ anti-aliasing. Green screen removed the ambiguity entirely. |
| `transparent.py` | rembg salient-object matting per frame | Salient-object models grab inconsistent regions frame-to-frame → flickering, dropped limbs. |

The throughline: **don't fight an ambiguous background — replace it with green.**
That one decision made the matte trivial and killed every artifact above.
