#Requires -Version 5.1
<#
.SYNOPSIS
    Reports which security tooling is available for this repository.
.DESCRIPTION
    Checks for Git, Semgrep, Gitleaks, OSV-Scanner, Trivy, dotnet, node,
    npm, python, pip, and pip-audit. Classifies each as FOUND, MISSING,
    OPTIONAL, or FAILED (found on PATH but invoking it produced no
    output and a non-zero exit - a broken/corrupted install, distinct
    from simply being absent). Never fails the run because an
    irrelevant ecosystem tool is unavailable (e.g. a pure .NET repo is
    not penalized for missing npm). See README.md for how this fits
    into the overall workflow.
.EXAMPLE
    .\scripts\windows\doctor.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
    (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

function Test-EcosystemPresent {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string[]]$Patterns
    )
    foreach ($pattern in $Patterns) {
        $hit = Get-ChildItem -Path $RepoRoot -Recurse -File -Filter $pattern -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch '\\(node_modules|bin|obj|\.git|output)\\' } |
            Select-Object -First 1
        if ($hit) { return $true }
    }
    return $false
}

function Test-Tool {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Command,
        [string[]]$VersionArgs = @('--version')
    )
    $cmd = Get-Command $Command -ErrorAction SilentlyContinue
    if (-not $cmd) {
        return [PSCustomObject]@{ Name = $Name; Status = 'MISSING'; Path = $null; Version = $null }
    }
    $version = $null
    $failed = $false
    $prevEAP = $ErrorActionPreference
    try {
        # Relax EAP for this call only - PowerShell 5.1 treats a native
        # command's stderr output as a terminating error under
        # EAP='Stop' even when redirected, which would otherwise mark
        # a perfectly working tool FAILED just for logging to stderr
        # (same issue as scan.ps1's Invoke-ToolSafely).
        $ErrorActionPreference = 'Continue'
        $output = & $Command @VersionArgs 2>$null
        $exit = $LASTEXITCODE
        if ($output) {
            $version = ($output | Select-Object -First 1).ToString().Trim()
        } elseif ($exit -ne 0) {
            # On PATH, but invoking it produced no output and a
            # non-zero exit - a broken/corrupted install, not just a
            # tool that happens to write its version to stderr.
            $failed = $true
        }
    } catch {
        $failed = $true
    } finally {
        $ErrorActionPreference = $prevEAP
    }
    if ($failed) {
        return [PSCustomObject]@{ Name = $Name; Status = 'FAILED'; Path = $cmd.Source; Version = $null }
    }
    [PSCustomObject]@{ Name = $Name; Status = 'FOUND'; Path = $cmd.Source; Version = $version }
}

try {
    $repoRoot = Get-RepoRoot
    Write-Host "Checking security tooling for: $repoRoot" -ForegroundColor Cyan
    Write-Host ''

    $hasDotnet = Test-EcosystemPresent -RepoRoot $repoRoot -Patterns @('*.csproj', '*.sln', '*.fsproj')
    $hasNode   = Test-EcosystemPresent -RepoRoot $repoRoot -Patterns @('package.json')
    $hasPython = Test-EcosystemPresent -RepoRoot $repoRoot -Patterns @('requirements.txt', 'pyproject.toml', 'setup.py', 'Pipfile')

    $results = @(
        Test-Tool -Name 'git'         -Command 'git'
        Test-Tool -Name 'semgrep'     -Command 'semgrep'
        Test-Tool -Name 'gitleaks'    -Command 'gitleaks' -VersionArgs @('version')
        Test-Tool -Name 'osv-scanner' -Command 'osv-scanner'
        Test-Tool -Name 'trivy'       -Command 'trivy'
        Test-Tool -Name 'dotnet'      -Command 'dotnet'
        Test-Tool -Name 'node'        -Command 'node'
        Test-Tool -Name 'npm'         -Command 'npm'
        Test-Tool -Name 'python'      -Command 'python'
        Test-Tool -Name 'pip'         -Command 'pip'
        Test-Tool -Name 'pip-audit'   -Command 'pip-audit'
    )

    # Ecosystem-native tools are only "required" (MISSING) when their
    # ecosystem is actually detected in this repo; otherwise they are
    # OPTIONAL. The four cross-ecosystem security scanners (git,
    # semgrep, gitleaks, osv-scanner) stay MISSING if absent regardless
    # of ecosystem, since they apply to any source tree. Trivy overlaps
    # with osv-scanner/gitleaks for dependency/secret scanning, so it is
    # treated as OPTIONAL (a coverage enhancement, not a hard
    # requirement) even when present-ecosystem tools are found.
    $ecosystemNeeded = @{
        'dotnet'    = $hasDotnet
        'node'      = $hasNode
        'npm'       = $hasNode
        'python'    = $hasPython
        'pip'       = $hasPython
        'pip-audit' = $hasPython
    }

    foreach ($r in $results) {
        if ($r.Status -eq 'MISSING' -and $ecosystemNeeded.ContainsKey($r.Name) -and -not $ecosystemNeeded[$r.Name]) {
            $r.Status = 'OPTIONAL'
        }
        if ($r.Name -eq 'trivy' -and $r.Status -eq 'MISSING') {
            $r.Status = 'OPTIONAL'
        }
    }

    $results | Format-Table -Property Name, Status, Version, Path -AutoSize

    Write-Host ''
    Write-Host 'Detected in this repository:' -ForegroundColor Cyan
    Write-Host ("  .NET (csproj/sln/fsproj): {0}" -f $(if ($hasDotnet) { 'yes' } else { 'no' }))
    Write-Host ("  Node (package.json):      {0}" -f $(if ($hasNode) { 'yes' } else { 'no' }))
    Write-Host ("  Python (requirements/pyproject/setup/Pipfile): {0}" -f $(if ($hasPython) { 'yes' } else { 'no' }))

    $missing = $results | Where-Object { $_.Status -eq 'MISSING' }
    $broken = $results | Where-Object { $_.Status -eq 'FAILED' }
    if ($missing -or $broken) {
        if ($missing) {
            Write-Host ''
            Write-Host 'Missing tools relevant to this repository:' -ForegroundColor Yellow
            foreach ($m in $missing) { Write-Host "  - $($m.Name)" }
            Write-Host ''
            Write-Host 'Run .\scripts\windows\install.ps1 to install missing tools (it will explain each step first).'
        }
        if ($broken) {
            Write-Host ''
            Write-Host 'Tools found on PATH but not working (broken/corrupted install):' -ForegroundColor Red
            foreach ($b in $broken) { Write-Host "  - $($b.Name) ($($b.Path))" }
        }
    } else {
        Write-Host ''
        Write-Host 'All tools relevant to this repository are available.' -ForegroundColor Green
    }

    exit 0
} catch {
    Write-Error "doctor.ps1 failed: $($_.Exception.Message)"
    exit 1
}
