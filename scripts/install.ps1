#!/usr/bin/env pwsh
# Install script for Windows
param()

Write-Host "Installing AInbox..."
if (Get-Command cargo -ErrorAction SilentlyContinue) {
    cargo install --path .
}
else {
    python -m pip install -e .
}
Write-Host "Installation complete. Run 'mailbox --version' to verify."
