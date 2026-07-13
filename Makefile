PROJECT := auroraos
BUILD_DIR := build
ROOTFS_DIR := $(BUILD_DIR)/rootfs
AURORA_QEMU_WIDTH ?= 1440
AURORA_QEMU_HEIGHT ?= 900
AURORA_QEMU_REFRESH ?= 60
AURORA_QEMU_CPUS ?= 4
AURORA_QEMU_ACCEL ?= tcg,thread=multi

.PHONY: all check icons system-icons assets native rootfs firefox-qemu run-firefox-qemu firefox-qemu-arm64 run-firefox-qemu-arm64 run-fast-qemu open-qemu pi4-image pi5-image clean

all: check native rootfs

check:
	@printf 'Checking AuroraOS repository layout...\n'
	@test -f "MSW98UI-Regular copy.ttf"
	@test -f "MSW98UI-Bold copy.ttf"
	@test -f "click.wav"
	@test -f assets/manifest.json
	@test -f systemd/system/aurora-pi-hardwared.service
	@test -f systemd/user/aurora-session.target
	@test -f packaging/default-apps.toml
	@printf 'OK: required Pi-first OS scaffold files are present.\n'

assets:
	@mkdir -p "$(BUILD_DIR)/assets/fonts" "$(BUILD_DIR)/assets/sounds"
	@cp "MSW98UI-Regular copy.ttf" "$(BUILD_DIR)/assets/fonts/MSW98UI-Regular.ttf"
	@cp "MSW98UI-Bold copy.ttf" "$(BUILD_DIR)/assets/fonts/MSW98UI-Bold.ttf"
	@cp "click.wav" "$(BUILD_DIR)/assets/sounds/click.wav"
	@printf 'Prepared pixel UI assets in %s/assets\n' "$(BUILD_DIR)"

icons:
	python3 tools/generate_pixel_icons.py

system-icons:
	python3 tools/prepare_icon_pack.py

native:
	@mkdir -p "$(BUILD_DIR)/bin" "$(BUILD_DIR)/libexec/aurora"
	$(CC) -std=c11 -Wall -Wextra -O2 src/aurora-compositor/main.c -o "$(BUILD_DIR)/bin/aurora-compositor"
	$(CC) -std=c11 -Wall -Wextra -O2 -Isrc/aurora-shell src/aurora-shell/main.c -o "$(BUILD_DIR)/bin/aurora-shell"
	$(CC) -std=c11 -Wall -Wextra -O2 src/aurora-pi-hardwared/main.c -o "$(BUILD_DIR)/libexec/aurora/aurora-pi-hardwared"
	@printf 'Built native Aurora component scaffolds in %s\n' "$(BUILD_DIR)"

rootfs: icons system-icons assets native
	@mkdir -p "$(ROOTFS_DIR)/usr/share/aurora/assets" \
		"$(ROOTFS_DIR)/usr/lib/systemd/system" \
		"$(ROOTFS_DIR)/usr/lib/systemd/user" \
		"$(ROOTFS_DIR)/etc/aurora" \
		"$(ROOTFS_DIR)/usr/bin" \
		"$(ROOTFS_DIR)/usr/libexec/aurora" \
		"$(ROOTFS_DIR)/usr/share/applications"
	@cp -R "$(BUILD_DIR)/assets/." "$(ROOTFS_DIR)/usr/share/aurora/assets/"
	@cp -R assets/icons "$(ROOTFS_DIR)/usr/share/aurora/assets/"
	@cp src/aurora-shell/icon_map.toml "$(ROOTFS_DIR)/usr/share/aurora/assets/icons/icon_map.toml"
	@cp assets/manifest.json "$(ROOTFS_DIR)/usr/share/aurora/assets/manifest.json"
	@cp systemd/system/*.service "$(ROOTFS_DIR)/usr/lib/systemd/system/"
	@cp systemd/user/* "$(ROOTFS_DIR)/usr/lib/systemd/user/"
	@cp packaging/*.toml "$(ROOTFS_DIR)/etc/aurora/"
	@cp "$(BUILD_DIR)/bin/aurora-compositor" "$(ROOTFS_DIR)/usr/bin/"
	@cp "$(BUILD_DIR)/bin/aurora-shell" "$(ROOTFS_DIR)/usr/bin/"
	@cp "$(BUILD_DIR)/libexec/aurora/aurora-pi-hardwared" "$(ROOTFS_DIR)/usr/libexec/aurora/"
	@if [ -d rootfs-overlay ]; then cp -R rootfs-overlay/. "$(ROOTFS_DIR)/"; fi
	@printf 'Created staged Aurora rootfs overlay at %s\n' "$(ROOTFS_DIR)"

firefox-qemu:
	python3 tools/build_firefox_qemu.py --build

firefox-qemu-arm64:
	python3 tools/build_arm64_qemu.py --build

run-firefox-qemu:
	qemu-system-x86_64 -m 6144M \
		-accel $(AURORA_QEMU_ACCEL) \
		-smp $(AURORA_QEMU_CPUS) \
		-kernel build/firefox-qemu/vmlinuz-virt \
		-initrd build/firefox-qemu/aurora-firefox-initramfs.cpio.lz4 \
		-append "console=tty0 init=/init quiet video=Virtual-1:$(AURORA_QEMU_WIDTH)x$(AURORA_QEMU_HEIGHT)@$(AURORA_QEMU_REFRESH)" \
		-device virtio-vga,xres=$(AURORA_QEMU_WIDTH),yres=$(AURORA_QEMU_HEIGHT) \
		-device usb-ehci,id=ehci \
		-device usb-tablet,bus=ehci.0 \
		-audiodev coreaudio,id=aud0 \
		-device ES1370,audiodev=aud0 \
		-netdev user,id=net0 \
		-device virtio-net-pci,netdev=net0 \
		-display cocoa \
		-monitor none \
		-serial stdio

run-firefox-qemu-arm64:
	qemu-system-aarch64 -m 6144M \
		-machine virt,accel=hvf \
		-cpu host \
		-smp $(AURORA_QEMU_CPUS) \
		-kernel build/firefox-qemu-arm64/vmlinuz-virt \
		-initrd build/firefox-qemu-arm64/aurora-firefox-initramfs.cpio.lz4 \
		-append "console=tty0 init=/init quiet" \
		-device virtio-gpu-pci \
		-device qemu-xhci,id=xhci \
		-device usb-tablet,bus=xhci.0 \
		-device usb-kbd,bus=xhci.0 \
		-audiodev coreaudio,id=aud0 \
		-device ES1370,audiodev=aud0 \
		-netdev user,id=net0 \
		-device virtio-net-pci,netdev=net0 \
		-display cocoa \
		-monitor none \
		-serial none

run-fast-qemu: run-firefox-qemu-arm64

open-qemu:
	open "$(CURDIR)/run-aurora-qemu.command"

pi4-image:
	@printf 'Pi 4 image target: use distro/buildroot/raspberrypi4_defconfig with overlays from %s\n' "$(ROOTFS_DIR)"

pi5-image:
	@printf 'Pi 5 image target: use distro/buildroot/raspberrypi5_defconfig with overlays from %s\n' "$(ROOTFS_DIR)"

clean:
	@rm -rf "$(BUILD_DIR)"
