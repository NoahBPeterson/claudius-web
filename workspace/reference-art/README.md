# reference-art

Drop a few **CC0 Claude stickers** here before running stage 1 — they get
attached to the image prompt so the generated hero matches the character.

Get them from the official sticker pack at
[vgel.me/misc/claude-stickers/](https://vgel.me/misc/claude-stickers/) (CC0 by
thebes). `1-hero/generate.py` looks for these filenames by default (edit
`REF_FILES` to change):

- `head.jpg`
- `claude_pet_cat.webp`
- `claude_minecart.webp`

Missing files are skipped with a warning — the stage still runs, just with less
character fidelity. The images themselves are not committed to this repo.
