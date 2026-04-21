#!/usr/bin/env pwsh
# Ensure the native mailbox binary is installed and available in the current PowerShell session.

param(
    [string]$Version = $env:AINBOX_VERSION,
    [string]$InstallDir = $env:AINBOX_INSTALL_DIR,
    [string]$Repo = $env:AINBOX_REPO,
    [string]$ArchivePath = $env:AINBOX_ARCHIVE_PATH
)

if (-not $InstallDir) {
    $InstallDir = Join-Path $env:USERPROFILE "AppData\Local\Programs\AInbox\bin"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$installScript = Join-Path $scriptDir "install.ps1"

function Add-InstallDirToPath {
    if (-not ($env:PATH -split ';' | Where-Object { $_ -eq $InstallDir })) {
        $env:PATH = "$InstallDir;$env:PATH"
    }
}

function Show-Mailbox {
    $command = Get-Command mailbox -ErrorAction Stop
    Write-Host "mailbox available at $($command.Source)"
    & $command.Source --version
}

if (Get-Command mailbox -ErrorAction SilentlyContinue) {
    Show-Mailbox
    return
}

$installedMailbox = Join-Path $InstallDir "mailbox.exe"
if (Test-Path $installedMailbox) {
    Add-InstallDirToPath
    if (Get-Command mailbox -ErrorAction SilentlyContinue) {
        Write-Host "Using existing mailbox install from $InstallDir"
        Show-Mailbox
        return
    }
}

Write-Host "mailbox not found on PATH; installing the latest native release..."
& $installScript -Version $Version -InstallDir $InstallDir -Repo $Repo -ArchivePath $ArchivePath
Add-InstallDirToPath

if (Get-Command mailbox -ErrorAction SilentlyContinue) {
    Show-Mailbox
    Write-Host "PATH updated for this PowerShell session."
    return
}

throw "mailbox was installed but is still not available on PATH. Add $InstallDir to PATH and retry."
