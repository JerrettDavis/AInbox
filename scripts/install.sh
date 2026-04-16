#!/bin/bash
# Install script for Linux/macOS

set -e

echo "Installing AInbox..."
python3 -m pip install -e .
echo "Installation complete. Run 'mailbox --version' to verify."
