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
# content. HYGIENE deliberately uses a narrower prune list (just
# .git/node_modules) since __pycache__/*.pyc are exactly what it is
# looking for — pruning them there would defeat the check.
$MdPruneNames = @('.git', 'node_modules', 'bin', 'obj', 'output', '__pycache__')
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
