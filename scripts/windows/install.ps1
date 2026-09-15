#Requires -Version 5.1
<#
.SYNOPSIS
    Installs missing security tooling for this repository (Semgrep,
    Gitleaks, OSV-Scanner, Trivy), using whichever package manager is
    available.
.DESCRIPTION
    Never installs anything without first explaining what it is about
    to do. Detects winget, then falls back to choco, then scoop.
    Prefers winget when multiple are available.
.PARAMETER CheckOnly
    Only report what is missing (equivalent to doctor.ps1)  -  installs
    nothing.
.PARAMETER Confirm
    Skip the interactive yes/no prompt and proceed with the installs
    that were explained. Without this switch, the script asks before
    each tool it would install.
.EXAMPLE
    .\scripts\windows\install.ps1 -CheckOnly
.EXAMPLE
    .\scripts\windows\install.ps1
#>

[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$Confirm
)

$ErrorActionPreference = 'Stop'

function Get-PackageManager {
    if (Get-Command winget -ErrorAction SilentlyContinue) { return 'winget' }
    if (Get-Command choco -ErrorAction SilentlyContinue) { return 'choco' }
    if (Get-Command scoop -ErrorAction SilentlyContinue) { return 'scoop' }
    return $null
}

# Package identifiers per manager. Not every tool is available in every
# manager's repository at all times  -  this script skips a tool it does
# not know how to install via the detected manager and says so, rather
# than guessing.
$packages = @{
    'semgrep' = @{ winget = $null; choco = 'semgrep'; scoop = $null }  # semgrep ships via pip/pipx/brew upstream; no winget package as of writing
    'gitleaks' = @{ winget = 'Gitleaks.Gitleaks'; choco = 'gitleaks'; scoop = 'gitleaks' }
    'osv-scanner' = @{ winget = 'Google.OSVScanner'; choco = $null; scoop = 'osv-scanner' }
    'trivy' = @{ winget = 'AquaSecurity.Trivy'; choco = 'trivy'; scoop = 'trivy' }
}

function Install-Tool {
    param([string]$Name, [string]$Manager, [string]$PackageId)
    switch ($Manager) {
        'winget' { winget install --id $PackageId --silent --accept-package-agreements --accept-source-agreements }
        'choco'  { choco install $PackageId -y }
        'scoop'  { scoop install $PackageId }
    }
}

try {
    $doctorScript = Join-Path $PSScriptRoot 'doctor.ps1'
    Write-Host 'Current tool status:' -ForegroundColor Cyan
    & $doctorScript
    $doctorExit = $LASTEXITCODE
    Write-Host ''
    if ($doctorExit -ne 0) {
        Write-Warning "doctor.ps1 exited with code $doctorExit - see its output above before continuing."
        exit $doctorExit
    }

    if ($CheckOnly) {
        Write-Host '(-CheckOnly: nothing will be installed.)' -ForegroundColor Yellow
        exit 0
    }

    $missing = @()
    foreach ($tool in 'semgrep', 'gitleaks', 'osv-scanner', 'trivy') {
        $cmdName = if ($tool -eq 'osv-scanner') { 'osv-scanner' } else { $tool }
        if (-not (Get-Command $cmdName -ErrorAction SilentlyContinue)) { $missing += $tool }
    }

    if ($missing.Count -eq 0) {
        Write-Host 'All four security scanners are already installed. Nothing to do.' -ForegroundColor Green
        exit 0
    }

    $manager = Get-PackageManager
    if (-not $manager) {
        Write-Warning 'No supported package manager found (winget, choco, or scoop). Install winget (App Installer from the Microsoft Store) or one of the others, then re-run this script. Alternatively, install the missing tools manually  -  see tools/README.md for each tool''s official installation instructions.'
        exit 2
    }

    Write-Host "Package manager detected: $manager" -ForegroundColor Cyan
    Write-Host ''
    Write-Host 'The following would be installed:' -ForegroundColor Cyan
    $plan = @()
    foreach ($tool in $missing) {
        $pkgId = $packages[$tool][$manager]
        if ($pkgId) {
            Write-Host "  - $tool  (via $manager package '$pkgId')"
            $plan += [PSCustomObject]@{ Tool = $tool; PackageId = $pkgId }
        } else {
            Write-Host "  - $tool  -- no known $manager package; see tools/README.md for manual install instructions" -ForegroundColor Yellow
        }
    }

    if ($plan.Count -eq 0) {
        Write-Host ''
        Write-Host 'Nothing installable via the detected package manager. See tools/README.md.' -ForegroundColor Yellow
        exit 0
    }

    Write-Host ''
    if (-not $Confirm) {
        $answer = Read-Host 'Proceed with the installs listed above? (y/N)'
        if ($answer -notmatch '^[Yy]') {
            Write-Host 'Aborted  -  nothing was installed.'
            exit 0
        }
    }

    foreach ($p in $plan) {
        Write-Host "Installing $($p.Tool) via $manager..." -ForegroundColor Cyan
        Install-Tool -Name $p.Tool -Manager $manager -PackageId $p.PackageId
    }

    Write-Host ''

    # pip-audit is a separate case: it is a pip package, not something
    # winget/choco/scoop install, and only relevant when this repo
    # actually has Python dependencies. scan.ps1 already treats its
    # absence as a coverage gap rather than a hard failure, so this is
    # an offer, not a requirement.
    if (-not (Get-Command pip-audit -ErrorAction SilentlyContinue)) {
        if (Get-Command pip -ErrorAction SilentlyContinue) {
            Write-Host 'pip-audit is not installed (used for Python dependency scanning if this repo has Python code).'
            $doInstall = $Confirm
            if (-not $doInstall) {
                $pipAnswer = Read-Host "Install it now via 'pip install --user pip-audit'? (y/N)"
                $doInstall = $pipAnswer -match '^[Yy]'
            }
            if ($doInstall) {
                pip install --user pip-audit
            } else {
                Write-Host 'Skipped pip-audit.'
            }
        }
    }

    Write-Host ''
    Write-Host 'Done. Re-run .\scripts\windows\doctor.ps1 to confirm.' -ForegroundColor Green
    exit 0
} catch {
    Write-Error "install.ps1 failed: $($_.Exception.Message)"
    exit 1
}
