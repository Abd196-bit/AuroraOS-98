#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
APP_DIR="$HOME/Applications/AuroraOS 98.app"

case "${1:-install}" in
  uninstall)
    rm -rf "$APP_DIR"
    printf 'Removed %s\n' "$APP_DIR"
    exit 0
    ;;
  install) ;;
  *)
    printf 'Usage: %s [install|uninstall]\n' "$0" >&2
    exit 2
    ;;
esac

command -v qemu-system-aarch64 >/dev/null 2>&1 || {
  printf 'QEMU is required. Install it with: brew install qemu lz4 libarchive\n' >&2
  exit 1
}

mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"
cat >"$APP_DIR/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleDisplayName</key><string>AuroraOS 98</string>
  <key>CFBundleExecutable</key><string>AuroraOS98</string>
  <key>CFBundleIdentifier</key><string>org.auroraos.vm</string>
  <key>CFBundleName</key><string>AuroraOS 98</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.1</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
EOF

cat >"$APP_DIR/Contents/MacOS/AuroraOS98" <<EOF
#!/bin/zsh
set -e
cd ${(q)PROJECT_DIR}
exec ./run-aurora-qemu.command
EOF
chmod +x "$APP_DIR/Contents/MacOS/AuroraOS98"

printf 'Installed %s for macOS user %s.\n' "$APP_DIR" "$(id -un)"
printf 'Open it from Finder > Applications, or run: open %s\n' "$(printf '%s' "$APP_DIR" | sed 's/ /\\ /g')"
