#Requires -Version 5.1
<#
.SYNOPSIS
    Runs the applicable security scanners against this repository and
    stores raw + normalized results under output/scans/<timestamp>/.
.DESCRIPTION
    Detects available tools and the repository's ecosystems, runs
    Semgrep, Gitleaks, OSV-Scanner, Trivy, and ecosystem-native audit
    tools where applicable, and writes results without requiring
    Docker for basic source-code/dependency scanning. An unavailable or
    failing tool is reported as a coverage gap rather than stopping the
    run - scanner output is candidate evidence for an AI reviewer to
    analyze afterward (see skills/security-review), not itself a final
    verdict.

    Coverage-gap detection is deliberately conservative: if a tool ran
    but produced no parseable output, that is treated as a gap rather
    than "zero findings" - CLI flags for external tools can change
    across versions, and a rejected flag should never look identical to
    a clean scan.
.PARAMETER DiffOnly
    Only pass files changed vs. the given git ref to tools that support
    file-scoped scanning (Semgrep). Other tools still scan the whole
    tree (dependency/secret scanning is not meaningfully diff-scoped).
.PARAMETER DiffBase
    Git ref to diff against when -DiffOnly is used. Default: HEAD.
.PARAMETER Mode
    Review mode this scan is being run under (QUICK/STANDARD/DEEP/
    TARGETED - see plays/code-review.md and plays/scanner-selection.md).
    Recorded in the scan metadata only; does not change scanner
    behavior. Defaults to TARGETED when -DiffOnly is set, STANDARD
    otherwise.
.EXAMPLE
    .\scripts\windows\scan.ps1
.EXAMPLE
    .\scripts\windows\scan.ps1 -DiffOnly -DiffBase main -Mode TARGETED
#>

[CmdletBinding()]
param(
    [switch]$DiffOnly,
    [string]$DiffBase = 'HEAD',
    [string]$Mode
)

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
    (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

function Test-EcosystemPresent {
    param([string]$RepoRoot, [string[]]$Patterns)
    foreach ($pattern in $Patterns) {
        $hit = Get-ChildItem -Path $RepoRoot -Recurse -File -Filter $pattern -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch '\\(node_modules|bin|obj|\.git|output)\\' } |
            Select-Object -First 1
        if ($hit) { return $true }
    }
    return $false
}

function Invoke-ToolSafely {
    <#
    Runs a scanner, capturing stdout/stderr/exit code without letting a
    non-zero exit (most scanners exit non-zero when findings exist) or
    an unexpected error abort the whole scan run.
    #>
    param(
        [Parameter(Mandatory)][string]$ToolName,
        [Parameter(Mandatory)][string]$Command,
        [Parameter(Mandatory)][string[]]$Arguments,
        [string]$WorkingDirectory
    )
    $result = [ordered]@{
        tool     = $ToolName
        ran      = $false
        exitCode = $null
        error    = $null
        stdout   = $null
        stderr   = $null
    }
    $cmd = Get-Command $Command -ErrorAction SilentlyContinue
    if (-not $cmd) {
        $result.error = "'$Command' not found on PATH"
        return [PSCustomObject]$result
    }
    $stderrFile = $null
    $prevEAP = $ErrorActionPreference
    $prevLocation = $null
    try {
        # PowerShell 5.1 treats a native command's stderr output as a
        # terminating error when $ErrorActionPreference = 'Stop', even
        # though it is only being redirected to a file here. Most
        # scanners (gitleaks, trivy, osv-scanner) write informational
        # lines to stderr - without this, an installed, working tool
        # would be reported as "unavailable" the moment it logs
        # anything. Relax EAP for just this call and restore it after.
        $ErrorActionPreference = 'Continue'
        $stderrFile = New-TemporaryFile
        if ($WorkingDirectory) {
            $prevLocation = Get-Location
            Set-Location -Path $WorkingDirectory
        }
        $stdout = & $Command @Arguments 2> $stderrFile.FullName
        $exit = $LASTEXITCODE
        $stderr = Get-Content -Raw -ErrorAction SilentlyContinue $stderrFile.FullName
        $result.ran = $true
        $result.exitCode = $exit
        $result.stdout = ($stdout -join "`n")
        $result.stderr = $stderr
    } catch {
        $result.error = $_.Exception.Message
    } finally {
        $ErrorActionPreference = $prevEAP
        if ($prevLocation) { Set-Location -Path $prevLocation.Path }
        if ($stderrFile -and (Test-Path $stderrFile.FullName)) {
            Remove-Item $stderrFile.FullName -ErrorAction SilentlyContinue
        }
    }
    [PSCustomObject]$result
}

function ConvertTo-JsonArraySafe {
    # ConvertTo-Json collapses a 0- or 1-element array to '' or a bare
    # object instead of '[]' / '[{...}]'. Wrap explicitly so downstream
    # consumers (including a re-read of this same file) always see a
    # JSON array, regardless of how many items were redacted.
    param($Items, [int]$Depth = 10)
    $arr = @($Items)
    if ($arr.Count -eq 0) { return '[]' }
    $body = ($arr | ConvertTo-Json -Depth $Depth)
    if ($arr.Count -eq 1) { return "[$body]" }
    return $body
}

function Protect-Secret {
    # Redacts a secret value for storage: keep a very short prefix/
    # suffix, mask the rest. This is a defense-in-depth pass on top of
    # gitleaks' own --redact flag (the primary control) - never persist
    # a raw value to disk anywhere, including "raw" tool output, per
    # plays/secrets-security.md.
    param([string]$Value)
    if ([string]::IsNullOrEmpty($Value)) { return $Value }
    if ($Value.Length -le 8) { return '*' * $Value.Length }
    return $Value.Substring(0, 2) + ('*' * ($Value.Length - 4)) + $Value.Substring($Value.Length - 2)
}

function Get-JsonArrayCount {
    # Returns $null (not a phantom 1 or 0) when $Parsed or the named
    # property is missing/empty-string/absent, so callers can tell
    # "confirmed zero findings" apart from "could not determine".
    # @($null).Count is 1 in PowerShell - a bare .Count on a null
    # property is exactly the phantom-count bug this exists to avoid.
    param($Parsed, [string]$Property)
    if ($null -eq $Parsed) { return $null }
    if (-not ($Parsed.PSObject.Properties.Name -contains $Property)) { return $null }
    $val = $Parsed.$Property
    if ($null -eq $val) { return $null }
    return @($val).Count
}

function ConvertFrom-JsonSafe {
    # $null in, $null out; '' in, $null out (rather than throwing or
    # silently succeeding with a value whose .Count lies) - see
    # Get-JsonArrayCount above for why a bare null is treated as "no
    # usable output" rather than "zero findings".
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $null }
    return $Text | ConvertFrom-Json
}

function Get-ToolVersionString {
    # Best-effort version string for scan metadata. Never throws -
    # missing/broken tools just report $null, same as everywhere else
    # in this script that tolerates a tool being unavailable.
    param([string]$Command, [string[]]$VersionArgs = @('--version'))
    $cmd = Get-Command $Command -ErrorAction SilentlyContinue
    if (-not $cmd) { return $null }
    $prevEAP = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $out = & $Command @VersionArgs 2>$null
        if ($out) { return ($out | Select-Object -First 1).ToString().Trim() }
        return $null
    } catch {
        return $null
    } finally {
        $ErrorActionPreference = $prevEAP
    }
}

try {
    $repoRoot = Get-RepoRoot
    $timestamp = Get-Date -Format 'yyyy-MM-ddTHHmmss'
    $scanDir = Join-Path $repoRoot "output\scans\$timestamp"
    $rawDir = Join-Path $scanDir 'raw'
    $normalizedDir = Join-Path $scanDir 'normalized'
    New-Item -ItemType Directory -Force -Path $rawDir, $normalizedDir | Out-Null

    Write-Host "Scanning: $repoRoot" -ForegroundColor Cyan
    Write-Host "Output:   $scanDir" -ForegroundColor Cyan
    Write-Host ''

    if (-not $Mode) { $Mode = if ($DiffOnly) { 'TARGETED' } else { 'STANDARD' } }

    $gitCommit = $null
    $dirty = $null
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $prevEAP = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $commitOut = & git -C $repoRoot rev-parse HEAD 2>$null
        if ($LASTEXITCODE -eq 0 -and $commitOut) { $gitCommit = $commitOut.Trim() }
        $statusOut = & git -C $repoRoot status --short 2>$null
        $dirty = [bool]$statusOut
        $ErrorActionPreference = $prevEAP
    }

    $toolVersions = [ordered]@{
        semgrep     = Get-ToolVersionString -Command 'semgrep'
        gitleaks    = Get-ToolVersionString -Command 'gitleaks' -VersionArgs @('version')
        'osv-scanner' = Get-ToolVersionString -Command 'osv-scanner'
        trivy       = Get-ToolVersionString -Command 'trivy'
    }

    $hasDotnet = Test-EcosystemPresent -RepoRoot $repoRoot -Patterns @('*.csproj', '*.sln', '*.fsproj')
    $hasNode   = Test-EcosystemPresent -RepoRoot $repoRoot -Patterns @('package.json')
    $hasPython = Test-EcosystemPresent -RepoRoot $repoRoot -Patterns @('requirements.txt', 'pyproject.toml', 'setup.py', 'Pipfile')
    $requirementsTxt = Join-Path $repoRoot 'requirements.txt'
    $hasRequirementsTxt = Test-Path $requirementsTxt

    $coverage = New-Object System.Collections.Generic.List[object]
    $findingsCount = @{}
    $anyToolRan = $false

    # --- Semgrep: static analysis candidates ---
    $semgrepArgs = @('scan', '--config', 'auto', '--json', '--quiet')
    if ($DiffOnly) {
        $prevEAP2 = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $changed = & git -C $repoRoot diff --name-only $DiffBase -- 2>$null
        $ErrorActionPreference = $prevEAP2
        $changedFull = @()
        if ($changed) {
            $changedFull = $changed | ForEach-Object { Join-Path $repoRoot $_ } | Where-Object { Test-Path $_ }
        }
        if ($changedFull.Count -gt 0) {
            $semgrepArgs += $changedFull
        } else {
            # No changed files matched (or diff itself failed) - fall
            # back to scanning the whole tree rather than passing no
            # target at all, which semgrep would reject as an error.
            $semgrepArgs += $repoRoot
        }
    } else {
        $semgrepArgs += $repoRoot
    }
    $semgrep = Invoke-ToolSafely -ToolName 'semgrep' -Command 'semgrep' -Arguments $semgrepArgs
    if ($semgrep.ran) {
        $anyToolRan = $true
        if ([string]::IsNullOrWhiteSpace($semgrep.stdout)) {
            $coverage.Add("semgrep ran (exit $($semgrep.exitCode)) but produced no output. stderr: $($semgrep.stderr)")
        } else {
            Set-Content -Path (Join-Path $rawDir 'semgrep.json') -Value $semgrep.stdout -Encoding utf8
            try {
                $parsed = ConvertFrom-JsonSafe $semgrep.stdout
                $count = Get-JsonArrayCount $parsed 'results'
                if ($null -eq $count) {
                    $coverage.Add("semgrep ran but its output did not contain a parseable 'results' array - possible CLI flag mismatch for the installed version. stderr: $($semgrep.stderr)")
                } else {
                    $findingsCount['semgrep'] = $count
                }
            } catch {
                $coverage.Add("semgrep ran but output could not be parsed as JSON: $($_.Exception.Message)")
            }
        }
    } else {
        $coverage.Add("Scanner unavailable: semgrep ($($semgrep.error)). Coverage impact: automated static-analysis candidates unavailable for this run. Fallback: manual semantic review per plays/code-review.md.")
    }

    # --- Gitleaks: secrets ---
    # --redact is gitleaks' own, tested redaction - the primary
    # control against ever writing a live secret to disk. Protect-Secret
    # below is a second, defense-in-depth pass in case a future
    # gitleaks version reports the value in a field --redact does not
    # cover.
    $gitleaksRaw = Join-Path $rawDir 'gitleaks.json'
    $gitleaks = Invoke-ToolSafely -ToolName 'gitleaks' -Command 'gitleaks' -Arguments @('detect', '--no-git', '--redact', '--source', $repoRoot, '--report-format', 'json', '--report-path', $gitleaksRaw, '--exit-code', '0')
    if ($gitleaks.ran) {
        $anyToolRan = $true
        if (-not (Test-Path $gitleaksRaw) -or (Get-Item $gitleaksRaw).Length -eq 0) {
            # No report file at all can legitimately mean "zero
            # findings" for gitleaks - but only trust that when the
            # exit code also looks like success/no-findings (0 or 1).
            if ($gitleaks.exitCode -in 0, 1) {
                $findingsCount['gitleaks'] = 0
            } else {
                $coverage.Add("gitleaks exited with code $($gitleaks.exitCode) and produced no report. stderr: $($gitleaks.stderr)")
            }
        } else {
            try {
                $parsed = Get-Content -Raw $gitleaksRaw | ConvertFrom-JsonSafe
                $items = @($parsed)
                $findingsCount['gitleaks'] = $items.Count
                # Redact secret values in place before this file is
                # considered final - never leave a live secret value on
                # disk. Applies to both raw and normalized copies.
                foreach ($item in $items) {
                    if ($null -eq $item) { continue }
                    if ($item.PSObject.Properties.Name -contains 'Secret') {
                        $item.Secret = Protect-Secret $item.Secret
                    }
                    if ($item.PSObject.Properties.Name -contains 'Match') {
                        $item.Match = Protect-Secret $item.Match
                    }
                }
                (ConvertTo-JsonArraySafe $items) | Set-Content -Path $gitleaksRaw -Encoding utf8
            } catch {
                # Redaction failed for an unexpected reason - do not
                # leave a possibly-unredacted file sitting under a
                # normal-looking name. Quarantine it and say so loudly.
                $quarantine = "$gitleaksRaw.UNREDACTED.sensitive"
                try { Move-Item -Path $gitleaksRaw -Destination $quarantine -Force -ErrorAction SilentlyContinue } catch {}
                $coverage.Add("gitleaks ran but its output could not be parsed/redacted: $($_.Exception.Message). The report may contain unredacted secrets and has been quarantined to '$quarantine' - do not read it; investigate and delete it, then re-run once the underlying issue is fixed.")
            }
        }
    } else {
        $coverage.Add("Scanner unavailable: gitleaks ($($gitleaks.error)). Coverage impact: automated secret detection unavailable for this run. Fallback: manual secret review per plays/secrets-security.md.")
    }

    # --- OSV-Scanner: dependency vulnerabilities ---
    $osvRaw = Join-Path $rawDir 'osv-scanner.json'
    $osv = Invoke-ToolSafely -ToolName 'osv-scanner' -Command 'osv-scanner' -Arguments @('--recursive', '--format', 'json', '--output', $osvRaw, $repoRoot)
    if ($osv.ran) {
        $anyToolRan = $true
        if (-not (Test-Path $osvRaw) -or (Get-Item $osvRaw).Length -eq 0) {
            if ($osv.exitCode -in 0, 1) {
                $findingsCount['osv-scanner'] = 0
            } else {
                $coverage.Add("osv-scanner exited with code $($osv.exitCode)) and produced no report - possible CLI flag mismatch for the installed version. stderr: $($osv.stderr)")
            }
        } else {
            try {
                $parsed = Get-Content -Raw $osvRaw | ConvertFrom-JsonSafe
                $count = Get-JsonArrayCount $parsed 'results'
                if ($null -eq $count) {
                    $coverage.Add("osv-scanner ran but its output did not contain a parseable 'results' array - possible CLI flag mismatch for the installed version.")
                } else {
                    $findingsCount['osv-scanner'] = $count
                }
            } catch {
                $coverage.Add("osv-scanner ran but output could not be parsed as JSON: $($_.Exception.Message)")
            }
        }
    } else {
        $coverage.Add("Scanner unavailable: osv-scanner ($($osv.error)). Coverage impact: automated dependency-vulnerability detection unavailable for this run. Fallback: ecosystem-native tools below, or manual review per plays/dependency-security.md.")
    }

    # --- Trivy: filesystem/dependency/secret/config (optional, overlaps
    #     with the above; adds container/config coverage when relevant) ---
    $trivyRaw = Join-Path $rawDir 'trivy.json'
    $trivy = Invoke-ToolSafely -ToolName 'trivy' -Command 'trivy' -Arguments @('fs', '--scanners', 'vuln,misconfig', '--format', 'json', '--output', $trivyRaw, $repoRoot)
    if ($trivy.ran) {
        $anyToolRan = $true
        if (-not (Test-Path $trivyRaw) -or (Get-Item $trivyRaw).Length -eq 0) {
            if ($trivy.exitCode -in 0, 1) {
                $findingsCount['trivy'] = 0
            } else {
                $coverage.Add("trivy exited with code $($trivy.exitCode) and produced no report - possible CLI flag mismatch for the installed version (e.g. --scanners value naming changed between versions). stderr: $($trivy.stderr)")
            }
        } else {
            try {
                $parsed = Get-Content -Raw $trivyRaw | ConvertFrom-JsonSafe
                $count = Get-JsonArrayCount $parsed 'Results'
                if ($null -eq $count) {
                    $coverage.Add("trivy ran but its output did not contain a parseable 'Results' array - possible CLI flag mismatch for the installed version.")
                } else {
                    $findingsCount['trivy'] = $count
                }
            } catch {
                $coverage.Add("trivy ran but output could not be parsed as JSON: $($_.Exception.Message)")
            }
        }
    } else {
        $coverage.Add("Scanner unavailable: trivy ($($trivy.error)). Coverage impact: none required - trivy is an optional enhancement over osv-scanner/gitleaks for this project type.")
    }

    # --- Ecosystem-native tools ---
    if ($hasDotnet) {
        $dotnetOut = Join-Path $rawDir 'dotnet-list-package-vulnerable.txt'
        $r = Invoke-ToolSafely -ToolName 'dotnet' -Command 'dotnet' -Arguments @('list', 'package', '--vulnerable', '--include-transitive') -WorkingDirectory $repoRoot
        if ($r.ran) {
            $anyToolRan = $true
            Set-Content -Path $dotnetOut -Value $r.stdout -Encoding utf8
            $findingsCount['dotnet-list-package'] = 'see raw output (text format, not machine-parsed)'
        } else {
            $coverage.Add("dotnet list package --vulnerable unavailable ($($r.error)). Coverage impact: .NET dependency vulnerabilities not double-checked via native tooling (osv-scanner above still covers this ecosystem if it ran).")
        }
    }
    if ($hasNode) {
        $npmOut = Join-Path $rawDir 'npm-audit.json'
        $r = Invoke-ToolSafely -ToolName 'npm' -Command 'npm' -Arguments @('audit', '--json') -WorkingDirectory $repoRoot
        if ($r.ran) {
            $anyToolRan = $true
            if ([string]::IsNullOrWhiteSpace($r.stdout)) {
                $coverage.Add("npm audit ran (exit $($r.exitCode)) but produced no output. stderr: $($r.stderr)")
            } else {
                Set-Content -Path $npmOut -Value $r.stdout -Encoding utf8
                try {
                    $parsed = ConvertFrom-JsonSafe $r.stdout
                    $vulnCount = $null
                    if ($parsed -and $parsed.metadata -and $parsed.metadata.vulnerabilities) {
                        $vulns = $parsed.metadata.vulnerabilities
                        if ($vulns.PSObject.Properties.Name -contains 'total') {
                            $vulnCount = $vulns.total
                        } else {
                            $vulnCount = ($vulns.PSObject.Properties | Where-Object { $_.Name -ne 'total' } | ForEach-Object { $_.Value } | Measure-Object -Sum).Sum
                        }
                    }
                    if ($null -eq $vulnCount) {
                        $coverage.Add("npm audit ran but its output did not contain the expected metadata.vulnerabilities field - possible npm version mismatch.")
                    } else {
                        $findingsCount['npm-audit'] = $vulnCount
                    }
                } catch {
                    $coverage.Add("npm audit ran but output could not be parsed as JSON: $($_.Exception.Message)")
                }
            }
        } else {
            $coverage.Add("npm audit unavailable ($($r.error)). Coverage impact: Node dependency vulnerabilities not double-checked via native tooling.")
        }
    }
    if ($hasPython) {
        $pipOut = Join-Path $rawDir 'pip-audit.json'
        $pipArgs = @('--format', 'json')
        if ($hasRequirementsTxt) { $pipArgs += @('-r', $requirementsTxt) }
        $r = Invoke-ToolSafely -ToolName 'pip-audit' -Command 'pip-audit' -Arguments $pipArgs -WorkingDirectory $repoRoot
        if ($r.ran) {
            $anyToolRan = $true
            if ([string]::IsNullOrWhiteSpace($r.stdout)) {
                $coverage.Add("pip-audit ran (exit $($r.exitCode)) but produced no output. stderr: $($r.stderr)")
            } else {
                Set-Content -Path $pipOut -Value $r.stdout -Encoding utf8
                try {
                    $parsed = ConvertFrom-JsonSafe $r.stdout
                    # pip-audit's JSON is {"dependencies": [...], "fixes": [...]},
                    # each dependency optionally carrying its own "vulns" list -
                    # not a flat list of only-vulnerable entries.
                    if ($parsed -and ($parsed.PSObject.Properties.Name -contains 'dependencies')) {
                        $vulnCount = ($parsed.dependencies | ForEach-Object { if ($_.vulns) { @($_.vulns).Count } else { 0 } } | Measure-Object -Sum).Sum
                        $findingsCount['pip-audit'] = $vulnCount
                        if (-not $hasRequirementsTxt) {
                            $coverage.Add("pip-audit scanned the current Python environment (no requirements.txt found at repo root to scan directly) - results may not reflect this repository's declared dependencies exactly.")
                        }
                    } else {
                        $coverage.Add("pip-audit ran but its output did not contain the expected 'dependencies' field - possible pip-audit version mismatch.")
                    }
                } catch {
                    $coverage.Add("pip-audit ran but output could not be parsed as JSON: $($_.Exception.Message)")
                }
            }
        } else {
            $coverage.Add("pip-audit unavailable ($($r.error)). Coverage impact: Python dependency vulnerabilities not double-checked via native tooling (osv-scanner above still covers this ecosystem if it ran).")
        }
    }

    # --- Summary ---
    $summary = [ordered]@{
        timestamp     = $timestamp
        repoRoot      = $repoRoot
        gitCommit     = $gitCommit
        dirty         = $dirty
        mode          = $Mode
        diffOnly      = [bool]$DiffOnly
        diffBase      = $(if ($DiffOnly) { $DiffBase } else { $null })
        ecosystems    = [ordered]@{ dotnet = $hasDotnet; node = $hasNode; python = $hasPython }
        toolVersions  = $toolVersions
        findingsCount = $findingsCount
        coverageGaps  = $coverage
    }
    $summaryPath = Join-Path $normalizedDir 'summary.json'
    ($summary | ConvertTo-Json -Depth 10) | Set-Content -Path $summaryPath -Encoding utf8

    Write-Host ''
    Write-Host 'Findings count (raw, per tool - not yet validated):' -ForegroundColor Cyan
    $findingsCount.GetEnumerator() | ForEach-Object { Write-Host "  $($_.Key): $($_.Value)" }

    if ($coverage.Count -gt 0) {
        Write-Host ''
        Write-Host 'Coverage gaps:' -ForegroundColor Yellow
        $coverage | ForEach-Object { Write-Host "  - $_" }
    }

    Write-Host ''
    Write-Host "Raw output:        $rawDir"
    Write-Host "Normalized summary: $summaryPath"
    Write-Host ''
    Write-Host 'Scanner output above is CANDIDATE evidence only. Follow' -ForegroundColor Cyan
    Write-Host 'skills/security-review to analyze it - do not report a' -ForegroundColor Cyan
    Write-Host 'finding as confirmed solely because a scanner flagged it.' -ForegroundColor Cyan

    if (-not $anyToolRan) {
        # Intentional, handled exit path (not an unhandled exception) -
        # use Write-Warning rather than Write-Error, since
        # $ErrorActionPreference = 'Stop' would otherwise turn a
        # Write-Error here into a terminating error caught by the
        # outer catch block below, which would incorrectly report exit
        # code 1 (execution failure) instead of the intended 2
        # (required dependency unavailable).
        Write-Warning 'No scanner could be run at all - see coverage gaps above. Run .\scripts\windows\doctor.ps1 to see what is missing.'
        exit 2
    }

    exit 0
} catch {
    Write-Error "scan.ps1 failed: $($_.Exception.Message)"
    exit 1
}
