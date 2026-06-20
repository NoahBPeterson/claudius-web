"""All prompt text for the Claude-mascot pipeline. Edit freely."""

PALETTE = """\
PALETTE (flat fills, NO gradients, NO shading):
- petals, all skin, hands, tail: terracotta-coral #CD6B4F
- face disc: warm white #FAF4E8
- sweater: soft lavender #B49AD4
- jeans: dusty light blue #9DBFD6
- shoes: cocoa brown #6E4A2E
- outlines: near-black ink #1A1A1A, thick uniform weight, slightly wobbly/hand-drawn"""

NEGATIVE = (
    "gradients, 3D render, cel shading, drop shadow, thin clean vector lines, "
    "anti-aliased smooth tech linework, photorealism, extra fingers, extra limbs, "
    "text, letters, watermark, signature, logo, busy background, perspective distortion"
)

# --- Step 1: the hero still -------------------------------------------------
# Pose is engineered for clean separability: legs straight & parallel with a
# gap, arms straight down on the ledge, tail to one side clear of the legs.
HERO = """\
A cartoon character drawn in a hand-drawn marker/ink sticker style, flat color,
thick wobbly black outlines, NO gradients, NO shading, NOT photorealistic.

THE CHARACTER: its head is a flower-like burst -- 13 LONG, slender, SPIKY
terracotta-orange (#CD6B4F) petals radiating evenly around a pale warm-white
(#FAF4E8) circular face disc; the petals are about 1.8x the disc's radius long,
fattest in the middle, tapering to rounded points, with slight hand-drawn
irregularity (no two identical). On the disc is a simple kaomoji face: two
"^ ^" caret eyes and a small "w" mouth, in wobbly black lines. The head is
OVERSIZED on a small human body. It wears a lavender (#B49AD4) crewneck sweater,
dusty light-blue (#9DBFD6) jeans, and brown (#6E4A2E) rounded shoes. Hands are
the same terracotta-orange (#CD6B4F) as the petals. A thin, smooth, tapering,
curled orange (#CD6B4F) tail like a cat/monkey tail emerges from the lower back.

POSE: sitting on the front edge of a plain stone ledge, facing the viewer,
happy. Legs hang straight DOWN, parallel, with a small gap between them, feet
relaxed. Both arms hang straight down at the sides, hands resting flat on the
ledge top beside the hips. Tail curls down to the LEFT side, clear of the legs.
Head upright and centered.

COMPOSITION: single character, centered, full body in frame, generous margins,
front orthographic view (no perspective foreshortening), even flat lighting.
TRANSPARENT background. High resolution.

Match the character in the attached reference images exactly (petal shape, face,
outline texture, proportions).

{palette}

Avoid: {negative}""".format(palette=PALETTE, negative=NEGATIVE)


# --- Step 3: layer isolation (+ inpaint of hidden joints) -------------------
# Each entry: key (matches the CSS rig), and the edit prompt run against the
# chosen hero still. Keys must stay in sync with build_rig() in generate.py.
_ISO = """\
From the attached image, output ONLY the character's {part}, isolated on a fully
TRANSPARENT background. Keep the exact same pixels, colors, outline, and
hand-drawn style -- do not redraw or restyle. Keep it in the SAME position and
scale as in the original image (do not re-center, do not crop, same canvas size).
Everything else fully transparent.{extend}

{palette}"""

def _iso(part, extend=""):
    return _ISO.format(part=part, extend=(" " + extend if extend else ""), palette=PALETTE)

LAYERS = [
    ("ledge",     _iso("stone ledge it sits on")),
    ("tail",      _iso("thin curled orange tail",
                       "Extend the base of the tail upward into the lower back so no gap "
                       "remains where the body hid it; match the orange (#CD6B4F) and outline.")),
    ("leg-left",  _iso("LEFT leg (viewer's left) with its jeans and shoe",
                       "Extend the top of the leg upward into a complete hip joint that was "
                       "hidden behind the sweater; match the jeans color (#9DBFD6) and outline.")),
    ("leg-right", _iso("RIGHT leg (viewer's right) with its jeans and shoe",
                       "Extend the top of the leg upward into a complete hip joint that was "
                       "hidden behind the sweater; match the jeans color (#9DBFD6) and outline.")),
    ("foot-left", _iso("LEFT shoe only (viewer's left brown shoe)")),
    ("foot-right",_iso("RIGHT shoe only (viewer's right brown shoe)")),
    ("torso",     _iso("lavender sweater torso (body only, no head, no arms, no legs)")),
    ("arm-left",  _iso("LEFT arm and hand (viewer's left)",
                       "Extend the top of the arm up into a complete shoulder hidden behind the "
                       "sweater; match the lavender (#B49AD4) sleeve and orange (#CD6B4F) hand.")),
    ("arm-right", _iso("RIGHT arm and hand (viewer's right)",
                       "Extend the top of the arm up into a complete shoulder hidden behind the "
                       "sweater; match the lavender (#B49AD4) sleeve and orange (#CD6B4F) hand.")),
    ("head",      _iso("entire flower-burst head with the face disc")),
]


# --- Track B fallback: a 4-pose sprite sheet --------------------------------
POSESHEET = """\
A 1x4 sprite sheet: 4 equal panels in a single horizontal row, IDENTICAL
character, style, scale, and framing in every panel -- ONLY the legs change.
The character is the attached flower-head cartoon, sitting on a ledge.
Panel 1: both legs hanging straight down.
Panel 2: legs swung slightly forward.
Panel 3: legs kicked fully forward and up.
Panel 4: legs swung back behind.
Transparent background, no gaps between panels, panels perfectly aligned so the
body/head/ledge stay pixel-locked and only the legs move.

{palette}

Avoid: {negative}""".format(palette=PALETTE, negative=NEGATIVE)
