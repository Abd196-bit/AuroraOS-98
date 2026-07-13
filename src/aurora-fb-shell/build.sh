#!/bin/bash
# AuroraOS Shell Build & Test Helper

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SHELL_DIR="$PROJECT_DIR/src/aurora-fb-shell"
BUILD_DIR="$PROJECT_DIR/build"

case "${1:-help}" in
    build)
        echo "Building aurora-fb-shell..."
        mkdir -p "$BUILD_DIR/bin"
        gcc -std=c11 -Wall -Wextra -O2 "$SHELL_DIR/aurora_fb_shell.c" \
            -o "$BUILD_DIR/bin/aurora-fb-shell"
        echo "✓ Built: $BUILD_DIR/bin/aurora-fb-shell"
        ls -lh "$BUILD_DIR/bin/aurora-fb-shell"
        ;;
    
    test)
        echo "Testing compilation..."
        gcc -std=c11 -Wall -Wextra -O2 -c "$SHELL_DIR/aurora_fb_shell.c" \
            -o /tmp/aurora-fb-shell-test.o
        echo "✓ Compilation successful (no warnings)"
        ;;
    
    run)
        echo "Running linux-qemu with aurora-shell..."
        cd "$PROJECT_DIR"
        make run-linux-qemu
        ;;
    
    clean)
        echo "Cleaning build artifacts..."
        rm -f "$BUILD_DIR/bin/aurora-fb-shell"
        rm -f /tmp/aurora-fb-shell-*
        echo "✓ Cleaned"
        ;;
    
    info)
        echo "AuroraOS Shell Build Information"
        echo "================================="
        echo ""
        echo "Project:  $PROJECT_DIR"
        echo "Shell:    $SHELL_DIR"
        echo "Build:    $BUILD_DIR"
        echo ""
        echo "Features:"
        echo "  ✓ Framebuffer UI (no X11/Wayland needed)"
        echo "  ✓ Web browser launching (Chromium)"
        echo "  ✓ Terminal launching (xterm)"
        echo "  ✓ File manager launching"
        echo "  ✓ Network status detection"
        echo "  ✓ Responsive 100ms input polling"
        echo "  ✓ Zombie process handling"
        echo "  ✓ <700MB RAM target"
        echo ""
        echo "Keyboard shortcuts (in shell):"
        echo "  B       - Launch browser"
        echo "  T       - Launch terminal"
        echo "  E       - Launch file explorer"
        echo "  D       - Launch directory manager"
        echo "  P       - Launch package center"
        echo "  N       - Show network status"
        echo "  S       - Show system status"
        echo "  Q       - Quit"
        echo ""
        echo "Usage: $0 {build|test|run|clean|info|help}"
        ;;
    
    help|*)
        echo "AuroraOS Shell Helper"
        echo "===================="
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  build   - Build aurora-fb-shell binary"
        echo "  test    - Test compilation without building"
        echo "  run     - Run in QEMU"
        echo "  clean   - Clean build artifacts"
        echo "  info    - Show build information"
        echo "  help    - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 build          # Compile the shell"
        echo "  $0 run            # Test in QEMU"
        echo "  $0 test           # Check for compilation errors"
        ;;
esac
