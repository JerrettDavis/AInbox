#!/usr/bin/env pwsh
# Install script for Windows
param()

Write-Host "Installing AInbox..."
python -m pip install -e .
Write-Host "Installation complete. Run 'mailbox --version' to verify."
