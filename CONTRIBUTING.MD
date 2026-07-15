# Contributing to AuroraOS 98

Thank you for helping improve AuroraOS 98! This repository is an experimental Linux desktop environment for x86-64 and Raspberry Pi hardware, and contributions are welcome in code, documentation, packaging, issue reports, and testing.

## Start here

1. Read the main project README: `README.md`
2. Check existing issues before opening a new one.
3. Use a fork and branch workflow for code changes.

## How to contribute

### Report bugs

- Search open issues first.
- Include:
  - A clear title.
  - A short description of what you expected and what happened.
  - The host platform you used (macOS, Linux, QEMU ARM64, QEMU x86-64, Raspberry Pi).
  - Any relevant logs or terminal output.
  - Repro steps if possible.

### Propose enhancements

- Open an issue describing the feature, the motivation, and the expected behavior.
- If your change is implementation-ready, link it to a pull request.

### Code contributions

- Fork the repo and create a branch for your work.
- Keep changes focused and descriptive.
- Use meaningful commit messages.

#### Build and test

This project uses `Makefile`, `meson.build`, and several helpers under `tools/`.

Common targets:

```sh
make
make firefox-qemu
make run-fast-qemu
make pi-test-image
```

For documentation or website updates, preview locally with:

```sh
python3 -m http.server 8765 --directory website
```

### Coding style

- Follow the existing style for C, Python, and shell code.
- Keep formatting consistent with the surrounding files.
- Add comments and documentation for non-obvious behavior.

### Documentation and packaging

- Improve docs in `docs/` when adding new features or behavior.
- Update desktop files and app manifests in `rootfs-overlay/` when packaging applications.
- Keep package metadata and templates aligned with existing repository patterns.

## Submit a pull request

- Target the `main` branch unless the issue specifies otherwise.
- Describe your changes clearly in the PR body.
- Link related issues and mention any testing you performed.

## Project structure

- `src/` — core Aurora applications and compositor code.
- `rootfs-overlay/` — filesystem overlay for the preview image.
- `assets/` — icons, cursors, fonts, and artwork.
- `docs/` — project documentation.
- `tools/` — build and packaging helpers.
- `website/` — static project website.

## Notes

- The current preview is an initramfs-based QEMU environment and not a full persistent OS installation.
- The Raspberry Pi image is experimental and should be tested on dedicated hardware.
- Build artifacts are excluded from version control; do not add generated images or binary releases to Git.

Thanks again for contributing to AuroraOS 98!