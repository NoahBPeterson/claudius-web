/* Claude mascot — kicking feet on the claude.ai composer.
 *
 * claude.ai's CSP is `default-src 'none'` with no media-src and `img-src 'self'`,
 * so <video> and blob/data <img> are both blocked. A <canvas> is NOT a resource
 * load, so it's exempt: we fetch the extension's OWN sprite sheet, decode it with
 * createImageBitmap (a JS API, not a URL load), and draw frames to a canvas.
 * No CSP tampering, no host permissions.
 */
(function () {
  'use strict';
  const api = globalThis.browser || globalThis.chrome;

  // ---- sprite metadata (from make_sprite.py) ----
  const SP = { file: 'sprite.webp', cols: 8, rows: 6, frames: 48, fw: 198, fh: 280 };
  // ---- look & feel ----
  const DISPLAY_W = 132;                       // CSS width of the mascot
  const DISPLAY_H = Math.round(DISPLAY_W * SP.fh / SP.fw);
  const FPS = 12;
  const OVERLAP = 0.30;                         // fraction of the mascot below the box's top edge (lower = sits higher)
  const ALIGN = 'right';                        // 'left' | 'center' | 'right' edge of the box to perch on
  const INSET = 28;                             // px gap from that edge (ignored when centered)
  const Z = 2147483000;
  const ROOT_ID = 'claude-mascot-canvas-root';

  let rootEl = null, canvas = null, ctx = null, bitmap = null, lastAnchor = null, host = null;

  // ---------- locate the composer (your verified anchor + fallbacks) ----------
  function findComposer() {
    return document.querySelector('div[class*="bg-bg-000"][class*="box-content"]')
        || (document.querySelector('.ProseMirror') &&
            document.querySelector('.ProseMirror').closest('div[class*="bg-bg-000"]'))
        || (document.querySelector('div[contenteditable="true"]') &&
            document.querySelector('div[contenteditable="true"]').parentElement)
        || null;
  }

  // The composer is `position: sticky` inside a scroll container, so during
  // normal scroll it's pinned by the compositor while the content scrolls. A
  // plain absolute child of the scroll container would scroll with content and
  // trail the composer. The element that moves EXACTLY with the composer in all
  // cases (scroll, overscroll, resize) is the nearest sticky/fixed ancestor:
  // its descendants ride it perfectly. So we host the mascot there.
  function pinnedAncestor(el) {
    for (let n = el; n && n !== document.body; n = n.parentElement) {
      const p = getComputedStyle(n).position;
      if (p === 'sticky' || p === 'fixed') return n;
    }
    return null;
  }
  function scrollParentOf(el) {
    for (let n = el && el.parentElement; n && n !== document.body; n = n.parentElement) {
      const o = getComputedStyle(n).overflowY;
      if ((o === 'auto' || o === 'scroll' || o === 'overlay') && n.scrollHeight > n.clientHeight + 1)
        return n;
    }
    return null;
  }

  // Pick the host: the pinned (sticky/fixed) ancestor if there is one (moves
  // with the composer natively); else the document body if the page scrolls;
  // else the inner scroll container as a last resort.
  function ensureHost(anchor) {
    const want = pinnedAncestor(anchor) || scrollParentOf(anchor) || document.body;
    if (host === want && rootEl && rootEl.parentNode === want) return false;
    host = want;
    try {
      if (host !== document.body && getComputedStyle(host).position === 'static') {
        host.style.position = 'relative'; // containing block for our absolute child
      }
      host.appendChild(rootEl); // move our node into the layer that rides the composer
      console.debug('[mascot] attached to',
        host === document.body ? 'document.body (page scroll)' : host);
    } catch (e) { console.warn('[mascot] attach failed, falling back to body', e); host = document.body; document.body.appendChild(rootEl); }
    return true;
  }

  // ---------- build canvas + load the sprite (once) ----------
  async function build() {
    if (rootEl || document.getElementById(ROOT_ID)) return;
    const root = document.createElement('div');
    root.id = ROOT_ID;
    Object.assign(root.style, {
      position: 'absolute', left: '-9999px', top: '-9999px', width: DISPLAY_W + 'px',
      height: DISPLAY_H + 'px', zIndex: String(Z), pointerEvents: 'none',
      opacity: '0', transition: 'opacity .25s ease', lineHeight: '0', margin: '0',
    });
    canvas = document.createElement('canvas');
    const dpr = Math.min(window.devicePixelRatio || 1, 3);
    canvas.width = Math.round(DISPLAY_W * dpr);
    canvas.height = Math.round(DISPLAY_H * dpr);
    Object.assign(canvas.style, {
      width: DISPLAY_W + 'px', height: DISPLAY_H + 'px', display: 'block',
      filter: 'drop-shadow(0 3px 3px rgba(0,0,0,.18))',
    });
    ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
    root.appendChild(canvas);
    document.body.appendChild(root);
    rootEl = root;

    try {
      const res = await fetch(api.runtime.getURL(SP.file));
      bitmap = await createImageBitmap(await res.blob());
    } catch (e) { console.error('[mascot] sprite load failed', e); return; }
    startAnim();
  }

  function drawFrame(f) {
    if (!bitmap) return;
    const sx = (f % SP.cols) * SP.fw, sy = ((f / SP.cols) | 0) * SP.fh;
    ctx.clearRect(0, 0, DISPLAY_W, DISPLAY_H);
    ctx.drawImage(bitmap, sx, sy, SP.fw, SP.fh, 0, 0, DISPLAY_W, DISPLAY_H);
  }

  function startAnim() {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let f = 0, dir = 1, last = 0;
    const step = 1000 / FPS;
    if (reduce) drawFrame((SP.frames / 2) | 0);   // static mid-pose
    // One rAF loop drives BOTH animation and positioning. Repositioning every
    // frame keeps the mascot glued to the box through macOS rubber-band
    // overscroll, which moves the page without firing scroll/resize events.
    function tick(t) {
      place();
      if (!reduce && t - last >= step) {
        last = t;
        drawFrame(f);
        f += dir;                                  // ping-pong for a seamless loop
        if (f >= SP.frames - 1) { f = SP.frames - 1; dir = -1; }
        else if (f <= 0) { f = 0; dir = 1; }
      }
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  // ---------- keep it perched on the composer's top edge ----------
  function place() {
    if (!rootEl) return;
    const anchor = findComposer();
    if (!anchor) { rootEl.style.opacity = '0'; return; }
    lastAnchor = anchor;
    ensureHost(anchor);                       // attach into the composer's scrolling layer
    const r = anchor.getBoundingClientRect();
    if (r.width === 0) { rootEl.style.opacity = '0'; return; }

    // viewport-space target (top edge of the box)
    let vx;
    if (ALIGN === 'left')        vx = r.left + INSET;
    else if (ALIGN === 'right')  vx = r.right - DISPLAY_W - INSET;
    else                          vx = r.left + (r.width - DISPLAY_W) / 2;
    const vy = r.top - DISPLAY_H * (1 - OVERLAP);

    // convert viewport-space -> the host's local coordinate space. Because the
    // mascot now lives inside the same (bouncing) layer as the composer, the
    // local offset stays constant during overscroll, so it rides the bounce.
    let x, y;
    if (host === document.body) {             // document scrolls
      x = vx + window.scrollX;
      y = vy + window.scrollY;
    } else {                                  // inner scroll container
      const hr = host.getBoundingClientRect();
      x = vx - hr.left - host.clientLeft + host.scrollLeft;
      y = vy - hr.top  - host.clientTop  + host.scrollTop;
    }
    rootEl.style.left = Math.round(x) + 'px';
    rootEl.style.top  = Math.round(y) + 'px';
    rootEl.style.opacity = '1';
  }

  async function init() {
    await build();        // build() kicks off the rAF loop, which positions every frame
    place();              // place once immediately so it appears without a frame's delay
    // The rAF loop handles scroll/resize/overscroll. The observer re-places when
    // claude.ai re-mounts the composer on navigation, or re-attaches our node if
    // React detaches it from the host.
    new MutationObserver(() => {
      if (!rootEl || !rootEl.isConnected || !lastAnchor ||
          !document.contains(lastAnchor) || findComposer() !== lastAnchor) {
        host = null;      // force ensureHost() to re-attach
        place();
      }
    }).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
