#Requires -Version 5.1

<#
.SYNOPSIS
    Repository consistency check — mechanical recall only, no semantic
    judgment.
.DESCRIPTION
    See plays/repository-consistency.md for what this does and does
    not do, and tools/consistency-patterns.txt for the pattern source
    both this script and consistency-check.sh read (do not add an
    equivalent pattern list here — read that file instead).
.EXAMPLE
    .\scripts\windows\consistency-check.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
    (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

$RepoRoot = Get-RepoRoot
$PatternsFile = Join-Path $RepoRoot 'tools\consistency-patterns.txt'

if (-not (Test-Path $PatternsFile)) {
    Write-Error "ERROR: pattern source not found: $PatternsFile"
    exit 2
}

function Test-Pruned {
    param(
        [Parameter(Mandatory)][string]$FullName,
        [Parameter(Mandatory)][string[]]$PruneNames
    )
    $segments = $FullName.Split('\')
    foreach ($name in $PruneNames) {
        if ($segments -contains $name) { return $true }
    }
    return $false
}

# Markdown/reference scans below never descend into generated/vendored
# content, or into work/ (session working notes and analysis reports —
# not this kit's own authored plays/skills/templates/tests, and exactly
# the kind of content that quotes a stale/vocabulary pattern verbatim
# while reporting on it, which is not the same as containing the mistake
# — see plays/repository-consistency.md's "Interpreting output"). HYGIENE
# deliberately uses a narrower prune list (just .git/node_modules) since
# __pycache__/*.pyc are exactly what it is looking for — pruning them
# there would defeat the check.
$MdPruneNames = @('.git', 'node_modules', 'bin', 'obj', 'output', '__pycache__', 'work')
$HygienePruneNames = @('.git', 'node_modules')

try {
    $MdFiles = Get-ChildItem -Path $RepoRoot -Recurse -File -Filter '*.md' -ErrorAction Stop |
        Where-Object { -not (Test-Pruned -FullName $_.FullName -PruneNames $MdPruneNames) }
} catch {
    Write-Error "ERROR: failed to enumerate Markdown files: $_"
    exit 2
}

$Hits = 0
$SectionPrinted = @{}

function Write-SectionHeader {
    param([string]$Category)
    if (-not $SectionPrinted.ContainsKey($Category)) {
        Write-Output ''
        Write-Output $Category
        $SectionPrinted[$Category] = $true
    }
}

function Get-RelativePath {
    param([string]$FullPath)
    $rel = $FullPath.Substring($RepoRoot.Length)
    $rel = $rel.TrimStart('\', '/')
    return $rel -replace '\\', '/'
}

Write-Output 'Repository Consistency Check'

# Read every file's content once and reuse it for both pattern passes
# below, instead of re-reading each file once per pattern.
$FileLines = @{}
foreach ($file in $MdFiles) {
    $FileLines[$file.FullName] = Get-Content -Path $file.FullName -ErrorAction SilentlyContinue
}

# --- STALE_TERM / VOCABULARY: pattern-file-driven recall -----------------
$PatternLines = Get-Content -Path $PatternsFile -ErrorAction Stop
foreach ($line in $PatternLines) {
    if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) { continue }
    $parts = $line.Split('|', 3)
    if ($parts.Count -lt 2) { continue }
    $category = $parts[0].Trim()
    $pattern = $parts[1]
    if ($category -ne 'STALE_TERM' -and $category -ne 'VOCABULARY') { continue }
    if ([string]::IsNullOrWhiteSpace($pattern)) { continue }

    foreach ($file in $MdFiles) {
        $lineNo = 0
        foreach ($textLine in $FileLines[$file.FullName]) {
            $lineNo++
            if ($textLine -match $pattern) {
                Write-SectionHeader $category
                Write-Output "  $(Get-RelativePath $file.FullName):$lineNo"
                Write-Output "  `"$($textLine.Trim())`""
                $Hits++
            }
        }
    }
}

# --- BROKEN_REFERENCE: backtick-quoted path existence ---------------------
# Requires at least one "/" — a bare filename in backticks
# (`finding-validation.md`) is overwhelmingly prose shorthand for a
# path already given in full nearby, not a standalone reference;
# matching those produced ~90% noise in testing. `.security/*` is
# excluded on purpose — those files live in a TARGET repository under
# review, never in this kit's own repository.
$RefPattern = '`([A-Za-z0-9_-]+(?:/[A-Za-z0-9_.-]+)+\.(?:md|ps1|sh|json|cs|py|js|txt))`'
foreach ($file in $MdFiles) {
    $lineNo = 0
    foreach ($textLine in $FileLines[$file.FullName]) {
        $lineNo++
        $matches_ = [regex]::Matches($textLine, $RefPattern)
        foreach ($m in $matches_) {
            $ref = $m.Groups[1].Value
            if ($ref -match '^https?://' -or $ref.StartsWith('.security/')) { continue }
            $refFull = Join-Path $RepoRoot ($ref -replace '/', '\')
            if (-not (Test-Path $refFull)) {
                Write-SectionHeader 'BROKEN_REFERENCE'
                Write-Output "  $(Get-RelativePath $file.FullName):$lineNo"
                Write-Output "  `"$ref`""
                $Hits++
            }
        }
    }
}

# --- HYGIENE: accidentally-TRACKED generated artifacts ---------------------
# A generated-looking file that git already ignores is not a hygiene
# problem — it's doing what .gitignore is for. Only a file git would
# actually check in (already tracked, or untracked-and-not-ignored)
# counts here. When git itself is unavailable, fall back to reporting
# filesystem presence (over-inclusive, but a check that runs everywhere
# beats one that silently does nothing without git).
$GitAvailable = $false
try {
    $null = & git -C $RepoRoot --no-optional-locks rev-parse --git-dir 2>$null
    if ($LASTEXITCODE -eq 0) { $GitAvailable = $true }
} catch { }

function Test-GitTrackedOrAddable {
    param([string]$RelPath)
    if (-not $GitAvailable) { return $true }
    $out = & git -C $RepoRoot --no-optional-locks status --porcelain --ignored -- $RelPath 2>$null
    if ($out -and $out.Trim().StartsWith('!!')) { return $false }
    return $true
}

$HygieneHits = Get-ChildItem -Path $RepoRoot -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object {
        (-not (Test-Pruned -FullName $_.FullName -PruneNames $HygienePruneNames)) -and
        (($_.PSIsContainer -and $_.Name -eq '__pycache__') -or
         (-not $_.PSIsContainer -and $_.Extension -eq '.pyc'))
    }
foreach ($hit in $HygieneHits) {
    $rel = Get-RelativePath $hit.FullName
    if (Test-GitTrackedOrAddable -RelPath $rel) {
        Write-SectionHeader 'HYGIENE'
        Write-Output "  $rel"
        $Hits++
    }
}

foreach ($d in @('output\scans', 'output\reports')) {
    $full = Join-Path $RepoRoot $d
    if (Test-Path $full) {
        Get-ChildItem -Path $full -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -ne '.gitkeep' } |
            ForEach-Object {
                $rel = Get-RelativePath $_.FullName
                if (Test-GitTrackedOrAddable -RelPath $rel) {
                    Write-SectionHeader 'HYGIENE'
                    Write-Output "  $rel"
                    $Hits++
                }
            }
    }
}

# --- SCOPE_COVERAGE: Group 3 play Scope vs. tools/context_manifest's ------
# rule table, both directions (implementation-batches.md Batch 0
# criterion 7). Unlike every category above, a SCOPE_COVERAGE hit is a
# confirmed defect requiring a code change, not a judgment call -- see
# plays/repository-consistency.md's SCOPE_COVERAGE entry. This script
# delegates to the single shared Python implementation in
# tools/context_manifest/ and does not, and must not, reimplement the
# comparison itself (see tools/context_manifest/scope_coverage.py's own
# module docstring) -- scripts/macos/consistency-check.sh calls the
# exact same entry point.
#
# [FIXED, per independent review]: every native-command invocation and
# error write below runs under a temporarily relaxed
# $ErrorActionPreference and writes stderr via [Console]::Error, not
# Write-Error -- under this script's global EAP='Stop' (line 19),
# Write-Error and a native command's own stderr output are BOTH
# terminating errors on PowerShell 5.1, which was silently turning the
# intended `exit 2` below into PowerShell's own uncaught-error exit
# code (1) instead, and could abort the whole script from inside the
# python3-stub-detection loop before it ever reached the working
# `python` fallback. Mirrors scripts/windows/doctor.ps1's own
# Test-Tool, which already documents and works around this exact
# PS 5.1 behavior.
function Write-ScopeCoverageError {
    param([string]$Message)
    [Console]::Error.WriteLine($Message)
}

function Invoke-NonTerminating {
    param([scriptblock]$Action)
    $prevEAP = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $Action
    } finally {
        $ErrorActionPreference = $prevEAP
    }
}

$PythonBin = $null
foreach ($candidate in @('python3', 'python')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    # Get-Command alone is not enough: on Windows, a "python3"/"python"
    # name on PATH can be a non-functional App Execution Alias stub
    # (present, but exits non-zero instead of running) -- verified by
    # actually invoking it, the same FOUND-vs-FAILED distinction
    # scripts/windows/doctor.ps1's Test-Tool already makes for other
    # tools. [FIXED, per independent review]: also require 3.7+ here,
    # not just "runs at all" -- tools/context_manifest/ uses
    # `from __future__ import annotations` throughout, which an older
    # interpreter cannot even import, and cli.py's own version check
    # cannot run on an interpreter unable to import cli.py in the first
    # place (see that module's own comment) -- this probe is the only
    # place that check can actually happen.
    $null = Invoke-NonTerminating { & $candidate -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)" 2>$null }
    if ($LASTEXITCODE -eq 0) { $PythonBin = $candidate; break }
}
if (-not $PythonBin) {
    Write-ScopeCoverageError "ERROR: Python 3 not found on PATH -- required for the SCOPE_COVERAGE check (V4 core runtime prerequisite, see tools/README.md). Run scripts/windows/doctor.ps1 for install guidance."
    exit 2
}
Push-Location $RepoRoot
try {
    # [FIXED, per a round-2 independent review Minor]: -B disables
    # writing __pycache__/*.pyc for this invocation -- without it, this
    # check was not idempotent (see scripts/macos/consistency-check.sh's
    # matching comment).
    $ScopeCoverageOutput = Invoke-NonTerminating { & $PythonBin -B -m tools.context_manifest.cli scope-coverage-check 2>&1 }
    $ScopeCoverageExit = $LASTEXITCODE
} finally {
    Pop-Location
}
if ($ScopeCoverageExit -eq 2) {
    Write-Output ''
    $ScopeCoverageOutput | ForEach-Object { Write-ScopeCoverageError $_ }
    Write-ScopeCoverageError 'ERROR: SCOPE_COVERAGE check could not run.'
    exit 2
} elseif ($ScopeCoverageExit -ne 0) {
    # Any other non-zero exit (e.g. an uncaught Python exception, exit 1
    # from a Python interpreter too old to run this module -- see
    # tools/context_manifest/cli.py's own disclosed limitation on this)
    # is treated the same as a confirmed SCOPE_COVERAGE hit, matching
    # scripts/macos/consistency-check.sh's equivalent branch.
    Write-Output ''
    $ScopeCoverageOutput | ForEach-Object { Write-Output $_ }
    $Hits++
}

Write-Output ''
if ($Hits -eq 0) {
    Write-Output 'Result:'
    Write-Output 'PASS'
    exit 0
} else {
    Write-Output 'Result:'
    Write-Output "REVIEW_REQUIRED ($Hits hit$(if ($Hits -ne 1) { 's' }))"
    exit 1
}
