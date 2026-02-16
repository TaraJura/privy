#!/usr/bin/env bash
# build_macos.sh — Build a standalone macOS .pkg installer for privy-cli.
#
# Usage:
#   ./scripts/build_macos.sh              # unsigned local build
#   CODESIGN_IDENTITY="Developer ID Application: ..." \
#   INSTALLER_IDENTITY="Developer ID Installer: ..." \
#     ./scripts/build_macos.sh            # signed build
#
# The script produces:
#   dist/privy/                           — PyInstaller onedir output
#   dist/privy-<version>-<arch>.pkg       — macOS installer package

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# ── Read version from pyproject.toml ────────────────────────────────────────
VERSION=$(python3 -c "
import re, pathlib
text = pathlib.Path('pyproject.toml').read_text()
m = re.search(r'version\s*=\s*\"([^\"]+)\"', text)
print(m.group(1))
")
ARCH=$(uname -m)
echo "==> Building privy-cli v${VERSION} for ${ARCH}"

# ── Step 1: Set up build venv ───────────────────────────────────────────────
echo "==> Setting up build environment..."
if [ -d build-venv ]; then
    rm -rf build-venv
fi
python3 -m venv build-venv
source build-venv/bin/activate
pip install --upgrade pip --quiet
pip install -e "." --quiet
pip install "pyinstaller>=6.0" --quiet

# ── Step 2: Run PyInstaller ─────────────────────────────────────────────────
echo "==> Running PyInstaller..."
pyinstaller privy.spec --clean --noconfirm

# ── Step 2b: Fix python-docx template resolution ───────────────────────────
# python-docx's parts/*.py files reference "../templates/*.xml" relative to
# __file__.  PyInstaller doesn't preserve the parts/ directory on disk, so
# the OS can't resolve "..".  Creating an empty parts/ directory fixes this.
echo "==> Patching python-docx template paths..."
mkdir -p dist/privy/_internal/docx/parts

# ── Step 3: Quick smoke test ────────────────────────────────────────────────
echo "==> Smoke test..."
./dist/privy/privy --help > /dev/null
echo "    privy --help OK"

# ── Step 4: Sign binaries (if identity is set) ─────────────────────────────
if [ -n "${CODESIGN_IDENTITY:-}" ]; then
    echo "==> Signing binaries with: ${CODESIGN_IDENTITY}"
    find dist/privy/ \( -name '*.dylib' -o -name '*.so' \) -print0 | while IFS= read -r -d '' f; do
        codesign --force --options runtime --sign "$CODESIGN_IDENTITY" --timestamp "$f" 2>/dev/null || true
    done
    codesign --force --options runtime \
        --sign "$CODESIGN_IDENTITY" \
        --timestamp \
        --entitlements entitlements.plist \
        dist/privy/privy
    echo "    Signing complete."
else
    echo "==> Skipping code signing (set CODESIGN_IDENTITY to enable)."
fi

# ── Step 5: Build .pkg ──────────────────────────────────────────────────────
echo "==> Building .pkg installer..."
COMPONENT_PKG="dist/privy-component.pkg"
UNSIGNED_PKG="dist/privy-${VERSION}-${ARCH}-unsigned.pkg"
FINAL_PKG="dist/privy-${VERSION}-${ARCH}.pkg"

pkgbuild \
    --root dist/privy \
    --identifier com.privy-cli.pkg \
    --version "$VERSION" \
    --install-location /usr/local/lib/privy \
    --scripts packaging/scripts \
    "$COMPONENT_PKG"

productbuild \
    --distribution packaging/distribution.xml \
    --package-path dist \
    --resources packaging/resources \
    "$UNSIGNED_PKG"

# ── Step 6: Sign .pkg (if identity is set) ──────────────────────────────────
if [ -n "${INSTALLER_IDENTITY:-}" ]; then
    echo "==> Signing .pkg with: ${INSTALLER_IDENTITY}"
    productsign --sign "$INSTALLER_IDENTITY" "$UNSIGNED_PKG" "$FINAL_PKG"
    rm -f "$UNSIGNED_PKG"
else
    echo "==> Skipping .pkg signing (set INSTALLER_IDENTITY to enable)."
    mv "$UNSIGNED_PKG" "$FINAL_PKG"
fi

rm -f "$COMPONENT_PKG"

# ── Step 7: Notarize (if credentials are set) ───────────────────────────────
if [ -n "${APPLE_ID:-}" ] && [ -n "${TEAM_ID:-}" ] && [ -n "${APP_SPECIFIC_PASSWORD:-}" ]; then
    echo "==> Notarizing..."
    xcrun notarytool submit "$FINAL_PKG" \
        --apple-id "$APPLE_ID" \
        --team-id "$TEAM_ID" \
        --password "$APP_SPECIFIC_PASSWORD" \
        --wait
    xcrun stapler staple "$FINAL_PKG"
    echo "    Notarization complete."
else
    echo "==> Skipping notarization (set APPLE_ID, TEAM_ID, APP_SPECIFIC_PASSWORD to enable)."
fi

# ── Done ────────────────────────────────────────────────────────────────────
deactivate
echo ""
echo "==> Build complete: ${FINAL_PKG}"
echo "    Size: $(du -h "$FINAL_PKG" | cut -f1)"
