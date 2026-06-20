#!/usr/bin/env bash
# Build store-ready packages for Claudius Mascot.
#   ./package.sh
# Outputs (gitignored) into dist/:
#   claudius-mascot-chrome-vX.Y.Z.zip   -> Chrome Web Store
#   claudius-mascot-firefox-vX.Y.Z.zip  -> Firefox AMO
set -euo pipefail
cd "$(dirname "$0")"

VER=$(grep -o '"version": *"[^"]*"' extension/manifest.json | head -1 | sed 's/.*"\([0-9.]*\)"/\1/')
mkdir -p dist
echo "Packaging Claudius Mascot v$VER"

# --- Chrome: a plain zip with manifest.json at the root ---
CHROME="dist/claudius-mascot-chrome-v$VER.zip"
rm -f "$CHROME"
( cd extension && zip -qr -X "../$CHROME" . \
    -x '*.DS_Store' -x '__MACOSX*' )
echo "  ✓ $CHROME"

# --- Firefox: lint + build via web-ext (AMO signs on upload) ---
FF="dist/claudius-mascot-firefox-v$VER.zip"
rm -f "$FF"
npx --yes web-ext build \
    --source-dir extension \
    --artifacts-dir dist \
    --filename "claudius-mascot-firefox-v$VER.zip" \
    --overwrite-dest >/dev/null
echo "  ✓ $FF"

echo
echo "Contents:"; unzip -l "$CHROME" | sed 's/^/   /'