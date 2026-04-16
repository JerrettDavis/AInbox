#!/bin/bash
# Install script for Linux/macOS

set -e

echo "Installing AInbox..."
if command -v cargo >/dev/null 2>&1; then
  cargo install --path .
else
  python3 -m pip install -e .
fi
echo "Installation complete. Run 'mailbox --version' to verify."
