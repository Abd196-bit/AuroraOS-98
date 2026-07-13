#!/bin/zsh
set -e

cd "$(dirname "$0")"

exec make run-firefox-qemu
