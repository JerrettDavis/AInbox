#!/usr/bin/env pwsh
# Install script for Windows
param(
    [string]$Version = $env:AINBOX_VERSION,
    [string]$InstallDir = $env:AINBOX_INSTALL_DIR,
    [string]$Repo = $env:AINBOX_REPO,
    [string]$ArchivePath = $env:AINBOX_ARCHIVE_PATH
)

if (-not $Version) {
    $Version = "latest"
}
if (-not $InstallDir) {
    $InstallDir = Join-Path $env:USERPROFILE "AppData\Local\Programs\AInbox\bin"
}
if (-not $Repo) {
    $Repo = "JerrettDavis/AInbox"
}

$assetName = switch ($env:PROCESSOR_ARCHITECTURE) {
    "AMD64" { "mailbox-windows-x86_64.zip" }
    "x86_64" { "mailbox-windows-x86_64.zip" }
    default { throw "Unsupported Windows architecture: $env:PROCESSOR_ARCHITECTURE" }
}

if ($Version -ne "latest" -and -not $Version.StartsWith("v")) {
    $Version = "v$Version"
}

Write-Host "Installing AInbox..."
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("ainbox-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

try {
    $archiveFile = Join-Path $tempDir $assetName
    if ($ArchivePath) {
        Copy-Item $ArchivePath $archiveFile -Force
    }
    else {
        if ($Version -eq "latest") {
            $releaseUrl = "https://github.com/$Repo/releases/latest/download/$assetName"
        }
        else {
            $releaseUrl = "https://github.com/$Repo/releases/download/$Version/$assetName"
        }
        Invoke-WebRequest -Uri $releaseUrl -OutFile $archiveFile
    }

    Expand-Archive -Path $archiveFile -DestinationPath $tempDir -Force
    Copy-Item (Join-Path $tempDir "mailbox.exe") (Join-Path $InstallDir "mailbox.exe") -Force
}
finally {
    Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Installed mailbox to $(Join-Path $InstallDir 'mailbox.exe')"
if (-not ($env:PATH -split ';' | Where-Object { $_ -eq $InstallDir })) {
    Write-Host "Add $InstallDir to PATH to run 'mailbox' directly."
}
Write-Host "Run 'mailbox --version' to verify."
