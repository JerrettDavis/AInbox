param(
    [string]$Root = $(Join-Path $env:TEMP ("ainbox-motion-demo-" + [guid]::NewGuid()))
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent

if ($env:MAILBOX_BIN) {
    $script:MailboxCommand = $env:MAILBOX_BIN
    $script:MailboxPrefix = @()
} elseif (Get-Command mailbox -ErrorAction SilentlyContinue) {
    $script:MailboxCommand = "mailbox"
    $script:MailboxPrefix = @()
} elseif (Test-Path (Join-Path $repoRoot "target\debug\mailbox.exe")) {
    $script:MailboxCommand = Join-Path $repoRoot "target\debug\mailbox.exe"
    $script:MailboxPrefix = @()
} elseif (Get-Command cargo -ErrorAction SilentlyContinue) {
    $script:MailboxCommand = "cargo"
    $script:MailboxPrefix = @("run", "--quiet", "--manifest-path", (Join-Path $repoRoot "Cargo.toml"), "--")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $script:MailboxCommand = "python"
    $script:MailboxPrefix = @("-m", "ainbox.cli")
} else {
    throw "Could not find mailbox runtime. Set MAILBOX_BIN, build the native CLI, or ensure cargo/python is available."
}

function Invoke-Mailbox {
    param(
        [string]$WorkingDirectory,
        [string]$AgentId,
        [string[]]$Arguments
    )

    Push-Location $WorkingDirectory
    try {
        $env:MAILBOX_AGENT_ID = $AgentId
        & $script:MailboxCommand @($script:MailboxPrefix + $Arguments)
    }
    finally {
        Pop-Location
    }
}

$shared = Join-Path $Root "shared-root"
$worker = Join-Path $Root "worker"
$reviewer = Join-Path $Root "reviewer"

New-Item -ItemType Directory -Path $worker, $reviewer, $shared -Force | Out-Null
$env:MAILBOX_SHARED = $shared

Invoke-Mailbox -WorkingDirectory $worker -AgentId "worker-agent" -Arguments @("init") | Out-Null
Invoke-Mailbox -WorkingDirectory $reviewer -AgentId "reviewer-agent" -Arguments @("init") | Out-Null

$created = Invoke-Mailbox -WorkingDirectory $worker -AgentId "worker-agent" -Arguments @(
    "create-motion",
    "--title", "Pause and report",
    "--participant", "worker-agent",
    "--participant", "reviewer-agent",
    "--description", "Stop current work and report status before proceeding.",
    "--scope", "cluster",
    "--format", "json"
) | Out-String

$motion = $created | ConvertFrom-Json
$motionId = $motion.id

Invoke-Mailbox -WorkingDirectory $reviewer -AgentId "reviewer-agent" -Arguments @("sync", "--pull-only") | Out-Null
$inbox = Invoke-Mailbox -WorkingDirectory $reviewer -AgentId "reviewer-agent" -Arguments @("list") | Out-String

Invoke-Mailbox -WorkingDirectory $worker -AgentId "worker-agent" -Arguments @(
    "vote-motion", "--id", $motionId, "--vote", "yes"
) | Out-Null

Invoke-Mailbox -WorkingDirectory $reviewer -AgentId "reviewer-agent" -Arguments @(
    "vote-motion", "--id", $motionId, "--vote", "yes", "--reason", "Status collected"
) | Out-Null

$resolved = Invoke-Mailbox -WorkingDirectory $worker -AgentId "worker-agent" -Arguments @(
    "wait-motion", "--id", $motionId, "--format", "json"
) | Out-String | ConvertFrom-Json

$report = [ordered]@{
    root = $Root
    shared = $shared
    motion_id = $motionId
    reviewer_inbox = $inbox.Trim()
    resolution = $resolved
}

$reportPath = Join-Path $Root "report.json"
$report | ConvertTo-Json -Depth 10 | Set-Content -Path $reportPath -Encoding UTF8
Write-Host "Motion demo report: $reportPath"
