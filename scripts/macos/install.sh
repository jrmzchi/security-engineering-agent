#!/usr/bin/env bash
# Installs missing security tooling for this repository (Semgrep,
# Gitleaks, OSV-Scanner, Trivy) via Homebrew. Never installs anything
# without first explaining what it is about to do.
#
# Usage:
#   ./scripts/macos/install.sh --check-only    # report only, install nothing
#   ./scripts/macos/install.sh                 # interactive confirm per install
#   ./scripts/macos/install.sh --yes           # skip the interactive prompt

set -uo pipefail

BASH_VER_NUM=$(( ${BASH_VERSINFO[0]:-0} * 100 + ${BASH_VERSINFO[1]:-0} ))
if [ "$BASH_VER_NUM" -lt 404 ]; then
    echo "This script requires Bash 4.4 or later (found: ${BASH_VERSION:-unknown})." >&2
    echo "macOS ships Bash 3.2 by default (this script needs 4.4+ for" >&2
    echo "associative arrays and safe handling of empty arrays under set -u)." >&2
    echo "Install a newer Bash via Homebrew:  brew install bash" >&2
    echo "then either open a new shell (if Homebrew's bash is earlier on your" >&2
    echo "PATH than /bin/bash) or run: \$(brew --prefix)/bin/bash $0" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CHECK_ONLY=false
ASSUME_YES=false
while [ $# -gt 0 ]; do
    case "$1" in
        --check-only) CHECK_ONLY=true; shift ;;
        --yes|-y) ASSUME_YES=true; shift ;;
        *) echo "Unknown argument: $1" >&2; exit 3 ;;
    esac
done

echo "Current tool status:"
# Invoke via `bash` explicitly rather than "$SCRIPT_DIR/doctor.sh" - a
# git checkout on a filesystem/config where the executable bit was not
# preserved (a common outcome when this repo was committed from
# Windows) would otherwise fail with "Permission denied" here.
bash "$SCRIPT_DIR/doctor.sh"
DOCTOR_EXIT=$?
echo ""
if [ "$DOCTOR_EXIT" -ne 0 ]; then
    echo "doctor.sh exited with code $DOCTOR_EXIT - see its output above before continuing." >&2
    exit "$DOCTOR_EXIT"
fi

if [ "$CHECK_ONLY" = true ]; then
    echo "(--check-only: nothing will be installed.)"
    exit 0
fi

MISSING=()
for tool in semgrep gitleaks osv-scanner trivy; do
    command -v "$tool" >/dev/null 2>&1 || MISSING+=("$tool")
done

if [ "${#MISSING[@]}" -eq 0 ]; then
    echo "All four security scanners are already installed. Nothing to do."
    exit 0
fi

if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Install it from https://brew.sh, then re-run this script." >&2
    echo "Alternatively, install the missing tools manually — see tools/README.md for each tool's official installation instructions." >&2
    exit 2
fi

# Homebrew formula names for each tool. All four are available as
# standard brew formulae as of writing; if a formula name changes
# upstream, this script will fail that single `brew install` call and
# move on rather than aborting the whole run.
declare -A BREW_FORMULA=(
    [semgrep]="semgrep"
    [gitleaks]="gitleaks"
    [osv-scanner]="osv-scanner"
    [trivy]="trivy"
)

echo "Package manager detected: brew"
echo ""
echo "The following would be installed:"
for tool in "${MISSING[@]}"; do
    echo "  - $tool  (via brew formula '${BREW_FORMULA[$tool]}')"
done
echo ""

if [ "$ASSUME_YES" = false ]; then
    read -r -p "Proceed with the installs listed above? (y/N) " answer
    case "$answer" in
        [Yy]*) ;;
        *) echo "Aborted — nothing was installed."; exit 0 ;;
    esac
fi

for tool in "${MISSING[@]}"; do
    echo "Installing $tool via brew..."
    brew install "${BREW_FORMULA[$tool]}" || echo "Warning: failed to install $tool — see output above." >&2
done

echo ""

# pip-audit is a separate case: it is a pip package, not something
# brew installs, and only relevant when this repo actually has Python
# dependencies. scan.sh already treats its absence as a coverage gap
# rather than a hard failure, so this is an offer, not a requirement.
if command -v pip-audit >/dev/null 2>&1; then
    :
elif command -v pip3 >/dev/null 2>&1; then
    echo "pip-audit is not installed (used for Python dependency scanning if this repo has Python code)."
    if [ "$ASSUME_YES" = true ]; then
        pip3 install --user pip-audit || echo "Warning: failed to install pip-audit — see output above." >&2
    else
        read -r -p "Install it now via 'pip3 install --user pip-audit'? (y/N) " pip_answer
        case "$pip_answer" in
            [Yy]*) pip3 install --user pip-audit || echo "Warning: failed to install pip-audit — see output above." >&2 ;;
            *) echo "Skipped pip-audit." ;;
        esac
    fi
fi

echo ""
echo "Done. Re-run ./scripts/macos/doctor.sh to confirm."
exit 0
