PROJECT := auroraos
BUILD_DIR := build
ROOTFS_DIR := $(BUILD_DIR)/rootfs
AURORA_QEMU_WIDTH ?= 1440
AURORA_QEMU_HEIGHT ?= 900
AURORA_QEMU_REFRESH ?= 60

.PHONY: all check icons provided-icons system-icons assets native rootfs qemu-progress run-qemu-progress qemu-gui run-qemu-gui qemu-icon-gui run-qemu-icon-gui linux-qemu run-linux-qemu firefox-qemu run-firefox-qemu open-linux-qemu serenity-reference-check serenity-behavior-check chromium-runtime-check chromium-rootfs-check full-chromium-image run-full-chromium-qemu run-shell pi4-image pi5-image x86_64-chromium-image clean aurora-fb-shell

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

provided-icons:
	python3 tools/extract_provided_icons.py

system-icons:
	python3 tools/prepare_icon_pack.py

native:
	@mkdir -p "$(BUILD_DIR)/bin" "$(BUILD_DIR)/libexec/aurora"
	$(CC) -std=c11 -Wall -Wextra -O2 src/aurora-compositor/main.c -o "$(BUILD_DIR)/bin/aurora-compositor"
	$(CC) -std=c11 -Wall -Wextra -O2 -Isrc/aurora-shell src/aurora-shell/main.c -o "$(BUILD_DIR)/bin/aurora-shell"
	$(CC) -std=c11 -Wall -Wextra -O2 src/aurora-pi-hardwared/main.c -o "$(BUILD_DIR)/libexec/aurora/aurora-pi-hardwared"
	@printf 'Built native Aurora component scaffolds in %s\n' "$(BUILD_DIR)"

aurora-fb-shell:
	@mkdir -p "$(BUILD_DIR)/bin"
	$(CC) -std=c11 -Wall -Wextra -O2 src/aurora-fb-shell/aurora_fb_shell.c -o "$(BUILD_DIR)/bin/aurora-fb-shell"
	@printf 'Built optimized Aurora framebuffer shell\n'
	@ls -lh "$(BUILD_DIR)/bin/aurora-fb-shell"

rootfs: icons provided-icons system-icons assets native
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

qemu-progress:
	@mkdir -p "$(BUILD_DIR)/tools"
	$(CC) -std=c11 -Wall -Wextra -O2 tools/mk_qemu_progress_boot.c -o "$(BUILD_DIR)/tools/mk_qemu_progress_boot"
	"$(BUILD_DIR)/tools/mk_qemu_progress_boot" "$(BUILD_DIR)/aurora-progress.img"
	@printf 'Created QEMU progress boot image at %s\n' "$(BUILD_DIR)/aurora-progress.img"

run-qemu-progress: qemu-progress
	qemu-system-x86_64 -m 128M -drive file="$(BUILD_DIR)/aurora-progress.img",format=raw,if=floppy -boot a -display none -serial stdio

qemu-gui:
	@mkdir -p "$(BUILD_DIR)/tools"
	$(CC) -std=c11 -Wall -Wextra -O2 tools/mk_qemu_gui_boot.c -o "$(BUILD_DIR)/tools/mk_qemu_gui_boot"
	"$(BUILD_DIR)/tools/mk_qemu_gui_boot" "$(BUILD_DIR)/aurora-gui.img"
	@printf 'Created QEMU GUI boot image at %s\n' "$(BUILD_DIR)/aurora-gui.img"

run-qemu-gui: qemu-gui
	qemu-system-x86_64 -m 128M -drive file="$(BUILD_DIR)/aurora-gui.img",format=raw,if=ide -boot c

qemu-icon-gui: system-icons
	python3 tools/mk_qemu_icon_boot.py
	@printf 'Created QEMU icon GUI boot image at %s\n' "$(BUILD_DIR)/aurora-icon-gui.img"

run-qemu-icon-gui: qemu-icon-gui
	qemu-system-x86_64 -m 128M -drive file="$(BUILD_DIR)/aurora-icon-gui.img",format=raw,if=ide -boot c

linux-qemu: qemu-icon-gui
	python3 tools/mk_linux_framebuffer_screens.py
	python3 tools/build_linux_qemu.py

firefox-qemu: linux-qemu
	python3 tools/build_firefox_qemu.py --build

serenity-reference-check:
	@test -d third_party/serenity/.git
	@test -f src/aurora-serenity-bridge/component_map.toml
	@test -f docs/serenity-linux-adaptation.md
	@printf 'OK: SerenityOS is available as an Aurora Linux reference, not as the base OS.\n'

serenity-behavior-check: serenity-reference-check
	python3 tools/check_serenity_behavior_sources.py

chromium-runtime-check:
	@test -f docs/chromium-runtime.md
	@printf 'OK: Chromium is assigned to the full graphical Linux rootfs, not the framebuffer initramfs.\n'

chromium-rootfs-check:
	python3 tools/build_full_chromium_image.py --check

full-chromium-image: rootfs
	python3 tools/build_full_chromium_image.py --build

run-full-chromium-qemu:
	python3 tools/run_full_chromium_qemu.py

run-linux-qemu: linux-qemu
	qemu-system-x86_64 -m 768M \
		-kernel build/linux-base/iso/boot/vmlinuz-virt \
		-initrd build/linux-base/aurora-initramfs.cpio.gz \
		-append "console=tty0 init=/init quiet video=Virtual-1:$(AURORA_QEMU_WIDTH)x$(AURORA_QEMU_HEIGHT)@$(AURORA_QEMU_REFRESH)" \
		-device virtio-vga,xres=$(AURORA_QEMU_WIDTH),yres=$(AURORA_QEMU_HEIGHT) \
		-device usb-ehci,id=ehci \
		-device usb-tablet,bus=ehci.0 \
		-display cocoa \
		-monitor none \
		-serial none

run-firefox-qemu:
	qemu-system-x86_64 -m 6144M \
		-kernel build/linux-base/iso/boot/vmlinuz-virt \
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

open-linux-qemu:
	open "$(CURDIR)/run-aurora-qemu.command"

run-shell: system-icons
	python3 src/aurora-shell/aurora_shell.py

pi4-image:
	@printf 'Pi 4 image target: use distro/buildroot/raspberrypi4_defconfig with overlays from %s\n' "$(ROOTFS_DIR)"

pi5-image:
	@printf 'Pi 5 image target: use distro/buildroot/raspberrypi5_defconfig with overlays from %s\n' "$(ROOTFS_DIR)"

x86_64-chromium-image:
	@printf 'x86-64 Chromium image target: make full-chromium-image, then make run-full-chromium-qemu\n'

clean:
	@rm -rf "$(BUILD_DIR)"
