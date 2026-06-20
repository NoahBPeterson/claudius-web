# Store submission kit — Claudius Mascot

Everything needed to list the extension on the Chrome Web Store and Firefox AMO.
Build the packages with `../package.sh` (outputs to `../dist/`, gitignored).

## Assets in this folder
| file | use |
|------|-----|
| `store-icon-512.png` | store listing icon (512×512) |
| `icon-96.png` | AMO listing icon (96×96) |
| `screenshot-1280x800.png` | listing screenshot (mockup — see note) |
| `promo-440x280.png` | Chrome small promo tile |

> **Screenshot note:** these are clean *mockups*. A real screen-capture of the
> mascot perched on your actual claude.ai composer will convert better — grab one
> (1280×800 or 640×400) and use it instead.

---

## Listing copy

**Name:** Claudius Mascot

**Summary** (Chrome ≤132 chars): *A little flower-headed Claude that perches on
your claude.ai message box and kicks its feet while you chat.*

**Description:**
> Claudius Mascot adds a tiny hand-drawn companion to claude.ai: the flower-headed
> Claude character sits on the edge of your message box and happily kicks its feet
> while you work. That's it — no settings, no accounts, no tracking. It respects
> "reduce motion," never blocks clicks or typing, and rides along as you scroll.
>
> Unofficial fan project. Not affiliated with or endorsed by Anthropic. Character
> design by thebes (@voooooogel), released CC0.

**Category:** Fun / Social & Communication
**Single purpose:** Display a decorative animated mascot on claude.ai.
**Permissions:** none beyond running a content script on `claude.ai`.
**Data collection:** none. The extension makes no network requests and stores
nothing — you can certify "does not collect user data" / no privacy policy needed.

---

## Chrome Web Store
1. One-time: register a developer account at
   <https://chrome.google.com/webstore/devconsole> (**$5 one-time fee**, not per
   extension).
2. **New item** → upload `dist/claudius-mascot-chrome-v1.0.0.zip`.
3. Fill the listing (copy above), add `store-icon-512.png`, at least one
   screenshot, and the `promo-440x280.png` tile.
4. Privacy tab: declare **no data collection**; single-purpose = the line above.
5. Submit for review (usually a few days).

## Firefox AMO
1. Free account at <https://addons.mozilla.org/developers/>.
2. **Submit a New Add-on** → **On this site** (listed) → upload
   `dist/claudius-mascot-firefox-v1.0.0.zip`.
3. AMO signs it automatically; fill the listing (same copy + assets).
4. Data-collection prompt: **No** (already declared in the manifest).

> The build lints clean (0 errors). Two warnings remain — they only note that the
> `data_collection_permissions` manifest key is newer than the Firefox 115 floor;
> older Firefox ignores it. AMO accepts the upload.

## Self-install (no store)
- **Firefox:** to install a permanent signed `.xpi` without listing, use
  `web-ext sign` with AMO API credentials (unlisted channel).
- **Chrome:** share `dist/claudius-mascot-chrome-v1.0.0.zip` via GitHub Releases;
  users Load-unpacked, or you distribute a `.crx`.
