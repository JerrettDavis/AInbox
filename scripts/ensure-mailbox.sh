#!/bin/bash
# Ensure the native mailbox binary is installed and available in the current shell session.

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
install_script="$script_dir/install.sh"
install_dir="${AINBOX_INSTALL_DIR:-$HOME/.local/bin}"
is_sourced=0

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  is_sourced=1
fi

finish() {
  local code="${1:-0}"
  if [[ "$is_sourced" -eq 1 ]]; then
    return "$code"
  fi
  exit "$code"
}

prepend_install_dir() {
  case ":$PATH:" in
    *":$install_dir:"*) ;;
    *) export PATH="$install_dir:$PATH" ;;
  esac
}

show_mailbox() {
  local mailbox_path
  mailbox_path="$(command -v mailbox)"
  echo "mailbox available at $mailbox_path"
  mailbox --version
}

if command -v mailbox >/dev/null 2>&1; then
  show_mailbox
  finish 0
fi

if [[ -x "$install_dir/mailbox" ]]; then
  prepend_install_dir
  if command -v mailbox >/dev/null 2>&1; then
    echo "Using existing mailbox install from $install_dir"
    show_mailbox
    if [[ "$is_sourced" -eq 0 ]]; then
      echo "Note: source this script to keep PATH changes in your current shell:"
      echo "  source \"$script_dir/ensure-mailbox.sh\""
    fi
    finish 0
  fi
fi

echo "mailbox not found on PATH; installing the latest native release..."
"$install_script"
prepend_install_dir

if command -v mailbox >/dev/null 2>&1; then
  show_mailbox
  if [[ "$is_sourced" -eq 0 ]]; then
    echo "Note: source this script to keep PATH changes in your current shell:"
    echo "  source \"$script_dir/ensure-mailbox.sh\""
  fi
  finish 0
fi

echo "mailbox was installed but is still not available on PATH." >&2
echo "Add $install_dir to PATH or source this script from your shell session." >&2
finish 1
