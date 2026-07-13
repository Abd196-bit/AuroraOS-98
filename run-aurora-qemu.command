#!/bin/zsh
set -e

cd "$(dirname "$0")"

case "$(uname -m)" in
  arm64|aarch64)
    exec make run-fast-qemu
    ;;
  *)
    exec make run-firefox-qemu
    ;;
esac
