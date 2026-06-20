// ==UserScript==
// @name         Claude mascot — kicking feet on the chatbox
// @namespace    https://vgel.me/claude-mascot
// @version      0.1.0
// @description  Sits the transparent flower-Claude on top of the claude.ai composer, kicking its feet.
// @match        https://claude.ai/*
// @match        https://*.claude.ai/*
// @run-at       document-idle
// @grant        GM_xmlhttpRequest
// @connect      localhost
// @connect      cdn.jsdelivr.net
// ==/UserScript==
(function () {
  'use strict';

  // ---- CONFIG -------------------------------------------------------------
  const VIDEO_URL = 'http://localhost:8000/transparent.webm'; // swap to jsDelivr later
  const WIDTH_PX  = 130;   // mascot width
  const OVERLAP   = 14;    // px the mascot's feet dip below the composer's top edge
  // -------------------------------------------------------------------------

  const ID = 'cm-mascot-root';
  let rootEl = null, videoEl = null, blobUrl = null;

  // Fetch the video bytes with a privileged request (bypasses page CSP),
  // then hand the <video> a blob: URL it's allowed to play.
  function loadVideo(video) {
    if (typeof GM_xmlhttpRequest !== 'function') { video.src = VIDEO_URL; return; }
    GM_xmlhttpRequest({
      method: 'GET', url: VIDEO_URL, responseType: 'blob',
      onload: (r) => {
        try {
          blobUrl = URL.createObjectURL(r.response);
          video.src = blobUrl;
          video.play().catch(() => {});
        } catch (e) { console.warn('[mascot] blob failed, trying direct src', e); video.src = VIDEO_URL; }
      },
      onerror: (e) => { console.warn('[mascot] fetch failed; is the local server running?', e); video.src = VIDEO_URL; },
    });
  }

  function build() {
    if (document.getElementById(ID)) return;
    const root = document.createElement('div');
    root.id = ID;
    Object.assign(root.style, {
      position: 'fixed', zIndex: 2147483646, width: WIDTH_PX + 'px',
      pointerEvents: 'none', transform: 'translate(-50%, -100%)',
      left: '-9999px', top: '-9999px', lineHeight: '0',
      transition: 'opacity .2s', opacity: '0',
    });
    const v = document.createElement('video');
    v.autoplay = true; v.loop = true; v.muted = true; v.playsInline = true;
    Object.assign(v.style, { width: '100%', height: 'auto', display: 'block',
      filter: 'drop-shadow(0 3px 4px rgba(0,0,0,.18))' });
    root.appendChild(v);
    document.body.appendChild(root);
    rootEl = root; videoEl = v;
    loadVideo(v);
  }

  // The composer is a ProseMirror contenteditable; anchor to it (or its box).
  function findComposer() {
    const ce = document.querySelector('div[contenteditable="true"]');
    if (!ce) return null;
    // climb to the rounded input container if we can, else use the editable itself
    return ce.closest('fieldset') || ce.closest('[class*="composer" i]') || ce;
  }

  function reposition() {
    if (!rootEl) return;
    const box = findComposer();
    if (!box) { rootEl.style.opacity = '0'; return; }
    const r = box.getBoundingClientRect();
    if (r.width === 0) { rootEl.style.opacity = '0'; return; }
    rootEl.style.left = (r.left + r.width / 2) + 'px';
    rootEl.style.top  = (r.top + OVERLAP) + 'px';
    rootEl.style.opacity = '1';
  }

  build();
  reposition();
  // keep it glued to the composer through scroll/resize/SPA re-renders
  window.addEventListener('resize', reposition, true);
  window.addEventListener('scroll', reposition, true);
  new MutationObserver(() => { build(); reposition(); })
    .observe(document.body, { childList: true, subtree: true });
  setInterval(reposition, 500);

  window.addEventListener('beforeunload', () => { if (blobUrl) URL.revokeObjectURL(blobUrl); });
})();
