[CmdletBinding()]
param(
    [string]$ArtifactRoot,
    [switch]$UseInstalledPluginAgents
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Require-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

function Resolve-MailboxShimDirectory {
    param(
        [string]$RepoRoot,
        [string]$ArtifactRootPath
    )

    if (Get-Command mailbox -ErrorAction SilentlyContinue) {
        return $null
    }

    $shimDir = Join-Path $ArtifactRootPath 'bin'
    New-Item -ItemType Directory -Path $shimDir -Force | Out-Null

    if (Get-Command python -ErrorAction SilentlyContinue) {
        $shimPath = Join-Path $shimDir 'mailbox.cmd'
        @(
            '@echo off'
            "set ""PYTHONPATH=$RepoRoot;%PYTHONPATH%"""
            'python -m ainbox.cli %*'
        ) | Set-Content -Path $shimPath
        return $shimDir
    }

    if (Get-Command cargo -ErrorAction SilentlyContinue) {
        $shimPath = Join-Path $shimDir 'mailbox.cmd'
        @(
            '@echo off'
            "pushd ""$RepoRoot"""
            'cargo run --quiet --bin mailbox -- %*'
            'set "MAILBOX_EXIT_CODE=%ERRORLEVEL%"'
            'popd'
            'exit /b %MAILBOX_EXIT_CODE%'
        ) | Set-Content -Path $shimPath
        return $shimDir
    }

    throw "Neither 'mailbox', 'python', nor 'cargo' is available. Cannot provide a mailbox command for the headless test."
}

function Convert-WindowsPathToBashPath {
    param([string]$WindowsPath)

    $normalized = $WindowsPath -replace '\\', '/'
    if ($normalized -match '^([A-Za-z]):/(.*)$') {
        return "/mnt/$($matches[1].ToLower())/$($matches[2])"
    }

    throw "Cannot convert path to bash form: $WindowsPath"
}

function Resolve-MailboxLauncherConfig {
    param([string]$RepoRoot)

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{
            WindowsExecutable = (Get-Command python).Source
            BashExecutable    = Convert-WindowsPathToBashPath -WindowsPath (Get-Command python).Source
            PythonPath        = ($RepoRoot -replace '\\', '/')
            Mode              = 'python'
        }
    }

    if (Get-Command cargo -ErrorAction SilentlyContinue) {
        return @{
            WindowsExecutable = (Get-Command cargo).Source
            BashExecutable    = Convert-WindowsPathToBashPath -WindowsPath (Get-Command cargo).Source
            RepoRoot          = ($RepoRoot -replace '\\', '/')
            Mode              = 'cargo'
        }
    }

    throw "Neither 'python' nor 'cargo' is available for the mailbox launcher."
}

function Write-BashMailboxLauncher {
    param(
        [string]$Workspace,
        [hashtable]$LauncherConfig
    )

    $launcherPath = Join-Path $Workspace 'mailbox.sh'
    $content = if ($LauncherConfig.Mode -eq 'python') {
@"
#!/usr/bin/env bash
set -euo pipefail
PYTHONPATH='$($LauncherConfig.PythonPath)'${PYTHONPATH:+":$PYTHONPATH"} '$($LauncherConfig.BashExecutable)' -m ainbox.cli "\$@"
"@
    } else {
@"
#!/usr/bin/env bash
set -euo pipefail
cd '$($LauncherConfig.RepoRoot)'
'$($LauncherConfig.BashExecutable)' run --quiet --bin mailbox -- "\$@"
"@
    }

    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($launcherPath, ($content -replace "`r`n", "`n"), $utf8NoBom)
}

function New-ArtifactRoot {
    param([string]$RequestedPath)

    if ($RequestedPath) {
        New-Item -ItemType Directory -Path $RequestedPath -Force | Out-Null
        return (Resolve-Path $RequestedPath).Path
    }

    $path = Join-Path ([System.IO.Path]::GetTempPath()) ("ainbox-headless-e2e-" + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    return $path
}

function Get-AgentDefinition {
    param([string]$Path)

    $content = Get-Content -Raw -Path $Path
    $match = [regex]::Match($content, '(?s)^---\s*(.*?)\s*---\s*(.*)$')
    if (-not $match.Success) {
        throw "Could not parse agent file: $Path"
    }

    $frontmatter = @{}
    foreach ($line in ($match.Groups[1].Value -split "`r?`n")) {
        if (-not $line.Trim()) {
            continue
        }

        $parts = $line -split ':', 2
        if ($parts.Count -ne 2) {
            continue
        }

        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($key -eq 'maxTurns') {
            $frontmatter[$key] = [int]$value
        } else {
            $frontmatter[$key] = $value
        }
    }

    return @{
        description = $frontmatter.description
        model       = $frontmatter.model
        maxTurns    = $frontmatter.maxTurns
        prompt      = $match.Groups[2].Value.Trim()
    }
}

function Get-AgentPayloadJson {
    param()

    $payload = @{
        orchestrator = @{
            description = 'Deterministic headless mailbox orchestrator for scripted e2e validation.'
            model       = 'sonnet'
            maxTurns    = 8
            prompt      = @'
You are a deterministic headless mailbox workflow agent.

Follow the user's requested mailbox steps exactly.
- Use mailbox CLI commands directly.
- Do not delegate.
- Do not inspect unrelated files.
- Keep tool use minimal and bounded to the stated task.
- Reply with JSON only when the user asks for JSON.
'@
        }
        'project-manager' = @{
            description = 'Deterministic headless mailbox collaborator for scripted e2e validation.'
            model       = 'sonnet'
            maxTurns    = 8
            prompt      = @'
You are a deterministic headless mailbox workflow agent.

Follow the user's requested mailbox steps exactly.
- Use mailbox CLI commands directly.
- Do not delegate.
- Do not inspect unrelated files.
- Keep tool use minimal and bounded to the stated task.
- Reply with JSON only when the user asks for JSON.
'@
        }
    }

    return ($payload | ConvertTo-Json -Depth 6 -Compress)
}

function Invoke-CommandWithEnv {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [hashtable]$Environment,
        [string]$WorkingDirectory
    )

    $previousValues = @{}
    foreach ($key in $Environment.Keys) {
        if (Test-Path "Env:$key") {
            $previousValues[$key] = (Get-Item "Env:$key").Value
        } else {
            $previousValues[$key] = $null
        }
        Set-Item -Path "Env:$key" -Value ([string]$Environment[$key])
    }

    Push-Location $WorkingDirectory
    try {
        $output = & $FilePath @ArgumentList 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
        foreach ($key in $Environment.Keys) {
            if ($null -eq $previousValues[$key]) {
                Remove-Item "Env:$key" -ErrorAction SilentlyContinue
            } else {
                Set-Item -Path "Env:$key" -Value $previousValues[$key]
            }
        }
    }

    return @{
        ExitCode = $exitCode
        Output   = $output.Trim()
    }
}

function Convert-JsonResponse {
    param(
        [string]$Text,
        [string]$Context
    )

    $trimmed = $Text.Trim()
    $jsonCandidate = $trimmed

    $fencedMatch = [regex]::Match($trimmed, '(?s)```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```')
    if ($fencedMatch.Success) {
        $jsonCandidate = $fencedMatch.Groups[1].Value.Trim()
    } else {
        $objectMatch = [regex]::Match($trimmed, '(?s)(\{.*\}|\[.*\])')
        if ($objectMatch.Success) {
            $jsonCandidate = $objectMatch.Groups[1].Value.Trim()
        }
    }

    try {
        return $jsonCandidate | ConvertFrom-Json -AsHashtable
    }
    catch {
        throw "Failed to parse JSON response for $Context.`nRaw output:`n$Text"
    }
}

function Invoke-MailboxAgentStep {
    param(
        [string]$StepName,
        [string]$AgentId,
        [string]$ClaudeAgent,
        [string]$Prompt,
        [string]$Workspace,
        [string]$TranscriptPath,
        [string]$SharedRoot,
        [string]$AgentsJson,
        [bool]$UseInstalledAgents,
        [string]$MailboxShimDir
    )

    $envVars = @{
        MAILBOX_AGENT_ID = $AgentId
        MAILBOX_SHARED   = $SharedRoot
        PYTHONUTF8       = '1'
    }
    if ($MailboxShimDir) {
        $envVars.PATH = "$MailboxShimDir$([System.IO.Path]::PathSeparator)$env:PATH"
    }

    $args = @(
        '-p',
        '--dangerously-skip-permissions',
        '--max-turns', '8',
        '--agent', $ClaudeAgent
    )

    if (-not $UseInstalledAgents) {
        $args += @('--agents', $AgentsJson)
    }

    $args += $Prompt

    $result = Invoke-CommandWithEnv -FilePath 'claude' -ArgumentList $args -Environment $envVars -WorkingDirectory $Workspace
    Set-Content -Path $TranscriptPath -Value $result.Output

    if ($result.ExitCode -ne 0) {
        throw "Claude step '$StepName' failed with exit code $($result.ExitCode).`n$($result.Output)"
    }

    return (Convert-JsonResponse -Text $result.Output -Context $StepName)
}

function Initialize-MailboxWorkspace {
    param(
        [string]$Workspace,
        [string]$AgentId,
        [string]$SharedRoot,
        [string]$MailboxShimDir,
        [hashtable]$LauncherConfig
    )

    $envVars = @{
        MAILBOX_AGENT_ID = $AgentId
        MAILBOX_SHARED   = $SharedRoot
        PYTHONUTF8       = '1'
    }
    if ($MailboxShimDir) {
        $envVars.PATH = "$MailboxShimDir$([System.IO.Path]::PathSeparator)$env:PATH"
    }

    $result = Invoke-CommandWithEnv -FilePath 'mailbox' -ArgumentList @('init') -Environment $envVars -WorkingDirectory $Workspace
    if ($result.ExitCode -ne 0) {
        throw "Failed to initialize mailbox for $AgentId.`n$result.Output"
    }

    Write-BashMailboxLauncher -Workspace $Workspace -LauncherConfig $LauncherConfig
}

function Invoke-MailboxCommand {
    param(
        [string]$AgentId,
        [string]$Workspace,
        [string]$SharedRoot,
        [string]$MailboxShimDir,
        [string[]]$ArgumentList,
        [string]$TranscriptPath
    )

    $envVars = @{
        MAILBOX_AGENT_ID = $AgentId
        MAILBOX_SHARED   = $SharedRoot
        PYTHONUTF8       = '1'
    }
    if ($MailboxShimDir) {
        $envVars.PATH = "$MailboxShimDir$([System.IO.Path]::PathSeparator)$env:PATH"
    }

    $result = Invoke-CommandWithEnv -FilePath 'mailbox' -ArgumentList $ArgumentList -Environment $envVars -WorkingDirectory $Workspace
    if ($TranscriptPath) {
        Set-Content -Path $TranscriptPath -Value $result.Output
    }
    if ($result.ExitCode -ne 0) {
        throw "Mailbox command failed for ${AgentId}: mailbox $($ArgumentList -join ' ').`n$($result.Output)"
    }

    return $result.Output
}

function Invoke-MailboxJsonCommand {
    param(
        [string]$AgentId,
        [string]$Workspace,
        [string]$SharedRoot,
        [string]$MailboxShimDir,
        [string[]]$ArgumentList,
        [string]$TranscriptPath,
        [string]$Context
    )

    $output = Invoke-MailboxCommand -AgentId $AgentId -Workspace $Workspace -SharedRoot $SharedRoot -MailboxShimDir $MailboxShimDir -ArgumentList $ArgumentList -TranscriptPath $TranscriptPath
    return (Convert-JsonResponse -Text $output -Context $Context)
}

function Test-InstalledAInboxAgent {
    param(
        [string]$SharedRoot,
        [string]$MailboxShimDir
    )

    $tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("ainbox-agent-probe-" + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    try {
        $probe = Invoke-MailboxAgentStep `
            -StepName 'probe-installed-agent' `
            -AgentId 'probe-agent' `
            -ClaudeAgent 'ainbox:orchestrator' `
            -Prompt 'Reply with JSON only: {"ok":true}' `
            -Workspace $tempDir `
            -TranscriptPath (Join-Path $tempDir 'probe.txt') `
            -SharedRoot $SharedRoot `
            -AgentsJson '{}' `
            -UseInstalledAgents $true `
            -MailboxShimDir $MailboxShimDir

        return [bool]$probe.ok
    }
    catch {
        return $false
    }
    finally {
        Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
    }
}

Require-Command 'claude'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$launcherConfig = Resolve-MailboxLauncherConfig -RepoRoot $repoRoot
$artifactRootPath = New-ArtifactRoot -RequestedPath $ArtifactRoot
$mailboxShimDir = Resolve-MailboxShimDirectory -RepoRoot $repoRoot -ArtifactRootPath $artifactRootPath
$transcriptRoot = Join-Path $artifactRootPath 'transcripts'
$workspaceRoot = Join-Path $artifactRootPath 'workspaces'
$sharedRoot = Join-Path $artifactRootPath 'shared-root'

New-Item -ItemType Directory -Path $transcriptRoot -Force | Out-Null
New-Item -ItemType Directory -Path $workspaceRoot -Force | Out-Null
New-Item -ItemType Directory -Path $sharedRoot -Force | Out-Null

$workspaces = @{
    'orchestrator-agent' = Join-Path $workspaceRoot 'orchestrator-agent'
    'reviewer-agent'     = Join-Path $workspaceRoot 'reviewer-agent'
    'analyst-agent'      = Join-Path $workspaceRoot 'analyst-agent'
}

foreach ($workspace in $workspaces.Values) {
    New-Item -ItemType Directory -Path $workspace -Force | Out-Null
}

foreach ($agentId in $workspaces.Keys) {
    Initialize-MailboxWorkspace -Workspace $workspaces[$agentId] -AgentId $agentId -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -LauncherConfig $launcherConfig
}

$agentMode = if ($UseInstalledPluginAgents) { 'installed-plugin' } else { 'dynamic-headless' }
$agentsJson = Get-AgentPayloadJson

$orchestratorClaudeAgent = if ($agentMode -eq 'installed-plugin') { 'ainbox:orchestrator' } else { 'orchestrator' }
$workerClaudeAgent = if ($agentMode -eq 'installed-plugin') { 'ainbox:project-manager' } else { 'project-manager' }

$steps = [System.Collections.Generic.List[object]]::new()

function Add-StepRecord {
    param(
        [string]$Name,
        [string]$AgentId,
        [hashtable]$Result
    )

    $steps.Add([ordered]@{
        step    = $Name
        agentId = $AgentId
        result  = $Result
    })
}

$createElectionRaw = Invoke-MailboxJsonCommand -AgentId 'orchestrator-agent' -Workspace $workspaces['orchestrator-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('create-election', '--role', 'feature-lead', '--candidate', 'reviewer-agent', '--candidate', 'analyst-agent', '--participant', 'orchestrator-agent', '--participant', 'reviewer-agent', '--participant', 'analyst-agent', '--format', 'json') -TranscriptPath (Join-Path $transcriptRoot '01-create-election.txt') -Context 'create-election'
$electionId = [string]$createElectionRaw.id
Invoke-MailboxCommand -AgentId 'orchestrator-agent' -Workspace $workspaces['orchestrator-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('vote-election', '--id', $electionId, '--candidate', 'analyst-agent') -TranscriptPath $null | Out-Null
Invoke-MailboxCommand -AgentId 'orchestrator-agent' -Workspace $workspaces['orchestrator-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('sync', '--push-only') -TranscriptPath $null | Out-Null
$createElection = @{
    step        = 'create-election'
    election_id = $electionId
    voted_for   = 'analyst-agent'
}
Add-StepRecord -Name 'create-election' -AgentId 'orchestrator-agent' -Result $createElection
$featureThread = "feature-idea-$electionId"

$null = Invoke-MailboxCommand -AgentId 'reviewer-agent' -Workspace $workspaces['reviewer-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('sync', '--pull-only') -TranscriptPath $null
$null = Invoke-MailboxCommand -AgentId 'reviewer-agent' -Workspace $workspaces['reviewer-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('vote-election', '--id', $electionId, '--candidate', 'analyst-agent') -TranscriptPath $null
$null = Invoke-MailboxCommand -AgentId 'reviewer-agent' -Workspace $workspaces['reviewer-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('send', '--to', 'analyst-agent', '--subject', 'Backed you for feature lead', '--correlation-id', "election:$electionId", '--body', 'I voted for you for feature lead.') -TranscriptPath $null
$null = Invoke-MailboxCommand -AgentId 'reviewer-agent' -Workspace $workspaces['reviewer-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('sync', '--push-only') -TranscriptPath (Join-Path $transcriptRoot '02-reviewer-vote.txt')
$reviewerVote = @{
    step            = 'reviewer-vote'
    election_id     = $electionId
    vote            = 'analyst-agent'
    message_sent_to = 'analyst-agent'
}
Add-StepRecord -Name 'reviewer-vote' -AgentId 'reviewer-agent' -Result $reviewerVote

$null = Invoke-MailboxCommand -AgentId 'analyst-agent' -Workspace $workspaces['analyst-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('sync', '--pull-only') -TranscriptPath $null
$null = Invoke-MailboxCommand -AgentId 'analyst-agent' -Workspace $workspaces['analyst-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('vote-election', '--id', $electionId, '--candidate', 'reviewer-agent') -TranscriptPath (Join-Path $transcriptRoot '03-analyst-vote.txt')
$analystVote = @{
    step        = 'analyst-vote'
    election_id = $electionId
    vote        = 'reviewer-agent'
}
Add-StepRecord -Name 'analyst-vote' -AgentId 'analyst-agent' -Result $analystVote

$electionState = Invoke-MailboxJsonCommand -AgentId 'orchestrator-agent' -Workspace $workspaces['orchestrator-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('show-election', '--id', $electionId, '--format', 'json') -TranscriptPath (Join-Path $transcriptRoot '04-assign-followup.txt') -Context 'show-election'
$analystVotes = [int]$electionState.votes.votes.'analyst-agent'
$reviewerVotes = [int]$electionState.votes.votes.'reviewer-agent'
$winner = if ($analystVotes -ge $reviewerVotes) { 'analyst-agent' } else { 'reviewer-agent' }
$proposer = $winner
$reviewer = if ($proposer -eq 'analyst-agent') { 'reviewer-agent' } else { 'analyst-agent' }
$null = Invoke-MailboxCommand -AgentId 'orchestrator-agent' -Workspace $workspaces['orchestrator-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('send', '--to', $proposer, '--subject', 'Prepare AInbox feature suggestion', '--correlation-id', $featureThread, '--body', "Send one quick AInbox feature suggestion in at most 4 bullet points to $reviewer using correlation-id $featureThread.") -TranscriptPath $null
$null = Invoke-MailboxCommand -AgentId 'orchestrator-agent' -Workspace $workspaces['orchestrator-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('send', '--to', $reviewer, '--subject', 'Review AInbox feature suggestion', '--correlation-id', $featureThread, '--body', "After the proposer sends their idea, critique it and send a refined recommendation back to orchestrator-agent using correlation-id $featureThread.") -TranscriptPath $null
$null = Invoke-MailboxCommand -AgentId 'orchestrator-agent' -Workspace $workspaces['orchestrator-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('sync', '--push-only') -TranscriptPath $null
$assignment = @{
    step           = 'assign-followup'
    election_id    = $electionId
    winner         = $winner
    proposer       = $proposer
    reviewer       = $reviewer
    correlation_id = $featureThread
}
Add-StepRecord -Name 'assign-followup' -AgentId 'orchestrator-agent' -Result $assignment

$suggestionPrompt = @"
You are $proposer in a headless mailbox workflow test.
Write one concise AInbox library feature suggestion in at most 4 bullet points.
Return ONLY valid JSON:
{"step":"feature-suggestion","sender":"$proposer","sent_to":"$reviewer","correlation_id":"$featureThread","suggestion":"..."}
"@

$suggestion = Invoke-MailboxAgentStep -StepName 'feature-suggestion' -AgentId $proposer -ClaudeAgent $workerClaudeAgent -Prompt $suggestionPrompt -Workspace $workspaces[$proposer] -TranscriptPath (Join-Path $transcriptRoot '05-feature-suggestion.txt') -SharedRoot $sharedRoot -AgentsJson $agentsJson -UseInstalledAgents ($agentMode -eq 'installed-plugin') -MailboxShimDir $mailboxShimDir
$null = Invoke-MailboxCommand -AgentId $proposer -Workspace $workspaces[$proposer] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('sync', '--pull-only') -TranscriptPath $null
$null = Invoke-MailboxCommand -AgentId $proposer -Workspace $workspaces[$proposer] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('send', '--to', $reviewer, '--subject', 'AInbox quick feature suggestion', '--correlation-id', $featureThread, '--body', [string]$suggestion.suggestion) -TranscriptPath $null
$null = Invoke-MailboxCommand -AgentId $proposer -Workspace $workspaces[$proposer] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('sync', '--push-only') -TranscriptPath $null
Add-StepRecord -Name 'feature-suggestion' -AgentId $proposer -Result $suggestion

$null = Invoke-MailboxCommand -AgentId $reviewer -Workspace $workspaces[$reviewer] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('sync', '--pull-only') -TranscriptPath $null
$reviewerInbox = Invoke-MailboxCommand -AgentId $reviewer -Workspace $workspaces[$reviewer] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('read', '--correlation-id', $featureThread) -TranscriptPath (Join-Path $transcriptRoot '06-reviewer-inbox.txt')
$reviewPrompt = @"
You are $reviewer in a headless mailbox workflow test.
The proposer was $proposer.
Here is the mailbox coordination content you received:
$reviewerInbox

Here is the actual feature suggestion from ${proposer}:
$([string]$suggestion.suggestion)

Send back a refined recommendation that explicitly mentions which agent proposed the idea.
Return ONLY valid JSON:
{"step":"review-suggestion","sender":"$reviewer","sent_to":"orchestrator-agent","correlation_id":"$featureThread","final_recommendation":"..."}
"@

$reviewResult = Invoke-MailboxAgentStep -StepName 'review-suggestion' -AgentId $reviewer -ClaudeAgent $workerClaudeAgent -Prompt $reviewPrompt -Workspace $workspaces[$reviewer] -TranscriptPath (Join-Path $transcriptRoot '06-review-suggestion.txt') -SharedRoot $sharedRoot -AgentsJson $agentsJson -UseInstalledAgents ($agentMode -eq 'installed-plugin') -MailboxShimDir $mailboxShimDir
$null = Invoke-MailboxCommand -AgentId $reviewer -Workspace $workspaces[$reviewer] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('send', '--to', 'orchestrator-agent', '--subject', 'Refined AInbox feature recommendation', '--correlation-id', $featureThread, '--body', [string]$reviewResult.final_recommendation) -TranscriptPath $null
$null = Invoke-MailboxCommand -AgentId $reviewer -Workspace $workspaces[$reviewer] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('sync', '--push-only') -TranscriptPath $null
Add-StepRecord -Name 'review-suggestion' -AgentId $reviewer -Result $reviewResult

$null = Invoke-MailboxCommand -AgentId 'orchestrator-agent' -Workspace $workspaces['orchestrator-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('sync', '--pull-only') -TranscriptPath $null
$orchestratorInbox = Invoke-MailboxCommand -AgentId 'orchestrator-agent' -Workspace $workspaces['orchestrator-agent'] -SharedRoot $sharedRoot -MailboxShimDir $mailboxShimDir -ArgumentList @('read', '--correlation-id', $featureThread) -TranscriptPath (Join-Path $transcriptRoot '07-orchestrator-inbox.txt')
$finalPrompt = @"
You are orchestrator-agent concluding the mailbox workflow test.
Election winner: $proposer
Final recommendation mailbox content:
$orchestratorInbox

Return ONLY valid JSON summarizing the completed workflow:
{"step":"final-summary","election_id":"$electionId","winner":"$proposer","final_recommendation":"..."}
"@

$finalResult = Invoke-MailboxAgentStep -StepName 'final-summary' -AgentId 'orchestrator-agent' -ClaudeAgent $orchestratorClaudeAgent -Prompt $finalPrompt -Workspace $workspaces['orchestrator-agent'] -TranscriptPath (Join-Path $transcriptRoot '07-final-summary.txt') -SharedRoot $sharedRoot -AgentsJson $agentsJson -UseInstalledAgents ($agentMode -eq 'installed-plugin') -MailboxShimDir $mailboxShimDir
Add-StepRecord -Name 'final-summary' -AgentId 'orchestrator-agent' -Result $finalResult

$report = [ordered]@{
    artifactRoot = $artifactRootPath
    repoRoot     = $repoRoot
    agentMode    = $agentMode
    mailboxShimDir = $mailboxShimDir
    sharedRoot   = $sharedRoot
    electionId   = $electionId
    proposer     = $proposer
    reviewer     = $reviewer
    correlationId = $featureThread
    final        = $finalResult
    steps        = $steps
}

$reportPath = Join-Path $artifactRootPath 'report.json'
$report | ConvertTo-Json -Depth 8 | Set-Content -Path $reportPath

Write-Output "Headless mailbox e2e completed successfully."
Write-Output "Artifacts: $artifactRootPath"
Write-Output "Report: $reportPath"
($report | ConvertTo-Json -Depth 8)
