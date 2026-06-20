# 🌻 claudius-web

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

Curious how it works — beating claude.ai's CSP, sticking to the composer through
scroll, and the image-gen → video → green-screen pipeline that made the art?
**See [MAKING.md](MAKING.md).**

## License

Code: MIT. Character: CC0 by thebes. Anthropic's burst logo is their trademark;
this is fan use — don't ship it commercially or imply official endorsement.
