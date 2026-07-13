#!/bin/bash
# Aurora Framebuffer Shell Diagnostics

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE="$PROJECT_DIR/build/linux-base"
SCREENS="$BASE/screens"
INITRAMFS="$BASE/initramfs.cpio.gz"
ROOTFS="$BASE/initramfs-root"

echo "Aurora Framebuffer Shell Diagnostics"
echo "===================================="
echo ""

echo "1. Frame Files Status"
echo "-------------------"
if [ -d "$SCREENS" ]; then
    echo "✓ Screens directory exists: $SCREENS"
    frame_count=$(ls "$SCREENS"/*.bgra32 2>/dev/null | wc -l)
    echo "  Frame files: $frame_count"
    if [ "$frame_count" -gt 0 ]; then
        echo "  ✓ Sample frames:"
        ls "$SCREENS"/*.bgra32 | head -3 | sed 's/^/    /'
    else
        echo "  ✗ No frame files found!"
    fi
else
    echo "✗ Screens directory not found: $SCREENS"
    echo "  Run: make mk_linux_framebuffer_screens.py"
fi
echo ""

echo "2. Initramfs Contents"
echo "-------------------"
if [ -f "$INITRAMFS" ]; then
    echo "✓ Initramfs exists: $INITRAMFS"
    size=$(ls -lh "$INITRAMFS" | awk '{print $5}')
    echo "  Size: $size"
    
    # Check for frames in initramfs
    echo "  Checking /aurora files in initramfs..."
    if zcat "$INITRAMFS" | cpio -t 2>/dev/null | grep -q "^aurora/desktop-closed.bgra32"; then
        frames_in_cpio=$(zcat "$INITRAMFS" | cpio -t 2>/dev/null | grep "^aurora/.*\.bgra32" | wc -l)
        echo "  ✓ Aurora frames in initramfs: $frames_in_cpio"
    else
        echo "  ✗ Aurora frames NOT in initramfs!"
        echo "  ACTION: Run: make linux-qemu  (to rebuild initramfs with frames)"
    fi
else
    echo "✗ Initramfs not found: $INITRAMFS"
    echo "  ACTION: Run: make linux-qemu"
fi
echo ""

echo "3. Shell Binary"
echo "--------------"
shell_bin="$PROJECT_DIR/build/bin/aurora-fb-shell"
if [ -f "$shell_bin" ]; then
    echo "✓ Shell binary exists"
    size=$(ls -lh "$shell_bin" | awk '{print $5}')
    echo "  Size: $size"
    echo "  Compiled: $(file "$shell_bin")"
else
    echo "✗ Shell binary not found: $shell_bin"
    echo "  ACTION: Run: make aurora-fb-shell"
fi
echo ""

echo "4. Build Status"
echo "-------------"
if [ -f "$INITRAMFS" ] && [ "$frame_count" -gt 20 ]; then
    echo "✓ Everything looks good for: make run-linux-qemu"
else
    echo "⚠ Issues detected. Run these commands:"
    if [ "$frame_count" -lt 20 ]; then
        echo "  1. make mk_linux_framebuffer_screens.py"
    fi
    echo "  2. make linux-qemu"
    echo "  3. make run-linux-qemu"
fi
echo ""

echo "5. Troubleshooting Tips"
echo "---------------------"
echo "If shell still doesn't work:"
echo ""
echo "A. Shell crashes on startup:"
echo "   - Check /aurora/desktop-closed.bgra32 exists"
echo "   - Verify all frames are 4MB (1280x800x4)"
echo ""
echo "B. No /dev/fb0 error:"
echo "   - Check QEMU graphics: -vga std needed"
echo "   - Verify framebuffer driver loads (bochs/cirrus)"
echo ""
echo "C. To inspect QEMU framebuffer:"
echo "   - Add to QEMU: -serial stdio"
echo "   - Run shell with stderr redirected"
echo ""
echo "D. To debug initramfs directly:"
echo "   - Extract: cd /tmp && zcat $INITRAMFS | cpio -idm"
echo "   - Check: ls -la aurora/"
echo ""
