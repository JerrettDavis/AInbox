#!/bin/bash
# Install script for Linux/macOS

set -euo pipefail

repo="${AINBOX_REPO:-JerrettDavis/AInbox}"
version="${AINBOX_VERSION:-latest}"
install_dir="${AINBOX_INSTALL_DIR:-$HOME/.local/bin}"
archive_path="${AINBOX_ARCHIVE_PATH:-}"

platform="$(uname -s)"
arch="$(uname -m)"

case "$platform" in
  Linux)
    case "$arch" in
      x86_64|amd64) asset_name="mailbox-linux-x86_64.tar.gz" ;;
      *) echo "Unsupported Linux architecture: $arch" >&2; exit 1 ;;
    esac
    ;;
  Darwin)
    case "$arch" in
      arm64|aarch64) asset_name="mailbox-macos-aarch64.tar.gz" ;;
      x86_64) asset_name="mailbox-macos-x86_64.tar.gz" ;;
      *) echo "Unsupported macOS architecture: $arch" >&2; exit 1 ;;
    esac
    ;;
  *)
    echo "Unsupported platform: $platform" >&2
    exit 1
    ;;
esac

normalize_tag() {
  if [[ "$1" == latest ]]; then
    printf '%s' "latest"
  elif [[ "$1" == v* ]]; then
    printf '%s' "$1"
  else
    printf 'v%s' "$1"
  fi
}

download_file() {
  local source_url="$1"
  local destination="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$source_url" -o "$destination"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$destination" "$source_url"
  else
    echo "curl or wget is required to download AInbox releases." >&2
    exit 1
  fi
}

echo "Installing AInbox..."
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
mkdir -p "$install_dir"

archive_file="$tmp_dir/$asset_name"
if [[ -n "$archive_path" ]]; then
  cp "$archive_path" "$archive_file"
else
  tag="$(normalize_tag "$version")"
  if [[ "$tag" == "latest" ]]; then
    release_url="https://github.com/${repo}/releases/latest/download/${asset_name}"
  else
    release_url="https://github.com/${repo}/releases/download/${tag}/${asset_name}"
  fi
  download_file "$release_url" "$archive_file"
fi

tar -xzf "$archive_file" -C "$tmp_dir"
install -m 755 "$tmp_dir/mailbox" "$install_dir/mailbox"

echo "Installed mailbox to $install_dir/mailbox"
case ":$PATH:" in
  *":$install_dir:"*) ;;
  *) echo "Add $install_dir to PATH to run 'mailbox' directly." ;;
esac
echo "Run 'mailbox --version' to verify."
