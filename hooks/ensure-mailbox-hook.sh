#!/bin/bash
# Best-effort Claude hook that installs the native mailbox binary if it is missing.

set -euo pipefail

if command -v mailbox >/dev/null 2>&1; then
  exit 0
fi

plugin_root="${CLAUDE_PLUGIN_ROOT:-}"
if [[ -z "$plugin_root" ]]; then
  exit 0
fi

install_script="$plugin_root/scripts/install.sh"
if [[ ! -x "$install_script" ]]; then
  exit 0
fi

resolve_install_dir() {
  local dir
  IFS=':' read -r -a path_parts <<< "${PATH:-}"
  for dir in "${path_parts[@]}"; do
    [[ -n "$dir" ]] || continue
    if [[ -d "$dir" && -w "$dir" ]]; then
      printf '%s' "$dir"
      return 0
    fi
    if [[ ! -e "$dir" ]]; then
      local parent
      parent="$(dirname "$dir")"
      if [[ -d "$parent" && -w "$parent" ]]; then
        printf '%s' "$dir"
        return 0
      fi
    fi
  done
  return 1
}

install_dir="$(resolve_install_dir || true)"
if [[ -z "$install_dir" ]]; then
  exit 0
fi

mkdir -p "$install_dir"
AINBOX_INSTALL_DIR="$install_dir" "$install_script" >/dev/null 2>&1 || exit 0
exit 0
