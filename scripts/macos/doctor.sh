#!/usr/bin/env bash
# Reports which security tooling is available for this repository.
# Checks for Git, Semgrep, Gitleaks, OSV-Scanner, Trivy, dotnet, node,
# npm, python, pip, and pip-audit. Classifies each as FOUND, MISSING,
# OPTIONAL, or FAILED (found on PATH but invoking it produced no output
# and a non-zero exit - a broken/corrupted install, distinct from
# simply being absent). Never fails because an irrelevant ecosystem
# tool is unavailable (e.g. a pure .NET repo is not penalized for
# missing npm).
#
# Usage: ./scripts/macos/doctor.sh [--help]

set -uo pipefail

BASH_VER_NUM=$(( ${BASH_VERSINFO[0]:-0} * 100 + ${BASH_VERSINFO[1]:-0} ))
if [ "$BASH_VER_NUM" -lt 404 ]; then
    # Stock macOS ships Bash 3.2; Homebrew's bash is commonly installed
    # but not first on PATH (or the user hasn't opened a new shell since
    # installing it). Try the two standard Homebrew prefixes and
    # transparently re-exec under a newer bash before giving up - this
    # automates exactly what the error message below already tells the
    # user to do by hand.
    for candidate in /opt/homebrew/bin/bash /usr/local/bin/bash; do
        if [ -x "$candidate" ]; then
            cand_num="$("$candidate" -c 'echo $(( BASH_VERSINFO[0]*100 + BASH_VERSINFO[1] ))' 2>/dev/null)"
            if [ -n "${cand_num:-}" ] && [ "$cand_num" -ge 404 ]; then
                # ${1+"$@"} rather than "$@": under Bash <= 4.3 with
                # `set -u` and zero positional parameters (this
                # script's only call form), a bare "$@" is treated as
                # an unbound variable and would abort right here,
                # before the newer bash ever gets a chance to run.
                exec "$candidate" "$0" ${1+"$@"}
            fi
        fi
    done
    echo "This script requires Bash 4.4 or later (found: ${BASH_VERSION:-unknown})." >&2
    echo "macOS ships Bash 3.2 by default (this script needs 4.4+ for" >&2
    echo "associative arrays and safe handling of empty arrays under set -u)." >&2
    echo "Install a newer Bash via Homebrew:  brew install bash" >&2
    echo "then either open a new shell (if Homebrew's bash is earlier on your" >&2
    echo "PATH than /bin/bash) or run: \$(brew --prefix)/bin/bash $0" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# This script takes no options other than --help - but it should still
# reject an unrecognized one explicitly (matching install.sh/scan.sh's
# convention) rather than silently ignoring it and running the full
# report anyway.
for arg in ${1+"$@"}; do
    case "$arg" in
        -h|--help)
            echo "Usage: ./scripts/macos/doctor.sh"
            echo "Reports which security tooling is available for this repository."
            echo "Takes no options."
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            exit 3
            ;;
    esac
done

has_pattern() {
    # -quit IS supported by BSD find (macOS's default) as well as GNU
    # find, so find exits after the first match instead of walking the
    # whole tree. `set +o pipefail` in the subshell is defense in
    # depth: without -quit, a very large match set could make grep -q
    # close the pipe before find finishes writing, and pipefail would
    # then report the whole pipeline as failed (SIGPIPE) even though a
    # match genuinely exists.
    local pattern="$1"
    local out
    out=$(
        set +o pipefail
        find "$REPO_ROOT" \
            \( -path '*/node_modules' -o -path '*/bin' -o -path '*/obj' -o -path '*/.git' -o -path '*/output' \) -prune -o \
            -type f -iname "$pattern" -print -quit 2>/dev/null
    )
    [ -n "$out" ]
}

HAS_DOTNET=false
HAS_NODE=false
HAS_PYTHON=false
has_pattern '*.csproj' && HAS_DOTNET=true
has_pattern '*.sln' && HAS_DOTNET=true
has_pattern '*.fsproj' && HAS_DOTNET=true
has_pattern 'package.json' && HAS_NODE=true
has_pattern 'requirements.txt' && HAS_PYTHON=true
has_pattern 'pyproject.toml' && HAS_PYTHON=true
has_pattern 'setup.py' && HAS_PYTHON=true
has_pattern 'Pipfile' && HAS_PYTHON=true

echo "Checking security tooling for: $REPO_ROOT"
echo ""

declare -A STATUS
declare -A VERSION
declare -A PATHOF

check_tool() {
    local name="$1" cmd="$2" version_flag="${3:---version}"
    local p out exit_code
    p="$(command -v "$cmd" 2>/dev/null || true)"
    if [ -z "$p" ]; then
        STATUS[$name]="MISSING"
        VERSION[$name]=""
        PATHOF[$name]=""
        return
    fi
    PATHOF[$name]="$p"
    out="$("$cmd" "$version_flag" 2>/dev/null)"
    exit_code=$?
    if [ -n "$out" ]; then
        STATUS[$name]="FOUND"
        VERSION[$name]="$(printf '%s' "$out" | head -n1)"
    elif [ "$exit_code" -ne 0 ]; then
        # On PATH, but invoking it produced no output and a non-zero
        # exit - a broken/corrupted install, not just a tool that
        # writes its version to stderr instead of stdout.
        STATUS[$name]="FAILED"
        VERSION[$name]=""
    else
        STATUS[$name]="FOUND"
        VERSION[$name]=""
    fi
}

check_tool git git
check_tool semgrep semgrep
check_tool gitleaks gitleaks version
check_tool osv-scanner osv-scanner
check_tool trivy trivy
check_tool dotnet dotnet
check_tool node node
check_tool npm npm
check_tool python3 python3
check_tool pip3 pip3
check_tool pip-audit pip-audit

# Ecosystem-native tools are only "required" (MISSING) when their
# ecosystem is actually present in this repo; otherwise OPTIONAL.
# Trivy overlaps with osv-scanner/gitleaks, so it stays OPTIONAL even
# when missing regardless of ecosystem.
[ "$HAS_DOTNET" = false ] && [ "${STATUS[dotnet]}" = "MISSING" ] && STATUS[dotnet]="OPTIONAL"
[ "$HAS_NODE" = false ] && [ "${STATUS[node]}" = "MISSING" ] && STATUS[node]="OPTIONAL"
[ "$HAS_NODE" = false ] && [ "${STATUS[npm]}" = "MISSING" ] && STATUS[npm]="OPTIONAL"
[ "$HAS_PYTHON" = false ] && [ "${STATUS[python3]}" = "MISSING" ] && STATUS[python3]="OPTIONAL"
[ "$HAS_PYTHON" = false ] && [ "${STATUS[pip3]}" = "MISSING" ] && STATUS[pip3]="OPTIONAL"
[ "$HAS_PYTHON" = false ] && [ "${STATUS[pip-audit]}" = "MISSING" ] && STATUS[pip-audit]="OPTIONAL"
[ "${STATUS[trivy]}" = "MISSING" ] && STATUS[trivy]="OPTIONAL"

printf "%-14s %-10s %-15s %s\n" "TOOL" "STATUS" "VERSION" "PATH"
for name in git semgrep gitleaks osv-scanner trivy dotnet node npm python3 pip3 pip-audit; do
    printf "%-14s %-10s %-15s %s\n" "$name" "${STATUS[$name]}" "${VERSION[$name]:-'-'}" "${PATHOF[$name]:-'-'}"
done

echo ""
echo "Detected in this repository:"
echo "  .NET (csproj/sln/fsproj): $HAS_DOTNET"
echo "  Node (package.json):      $HAS_NODE"
echo "  Python (requirements/pyproject/setup/Pipfile): $HAS_PYTHON"

MISSING_LIST=()
FAILED_LIST=()
for name in git semgrep gitleaks osv-scanner trivy dotnet node npm python3 pip3 pip-audit; do
    [ "${STATUS[$name]}" = "MISSING" ] && MISSING_LIST+=("$name")
    [ "${STATUS[$name]}" = "FAILED" ] && FAILED_LIST+=("$name")
done

if [ "${#MISSING_LIST[@]}" -gt 0 ] || [ "${#FAILED_LIST[@]}" -gt 0 ]; then
    if [ "${#MISSING_LIST[@]}" -gt 0 ]; then
        echo ""
        echo "Missing tools relevant to this repository:"
        for m in "${MISSING_LIST[@]}"; do echo "  - $m"; done
        echo ""
        echo "Run ./scripts/macos/install.sh to install missing tools (it will explain each step first)."
    fi
    if [ "${#FAILED_LIST[@]}" -gt 0 ]; then
        echo ""
        echo "Tools found on PATH but not working (broken/corrupted install):"
        for b in "${FAILED_LIST[@]}"; do echo "  - $b (${PATHOF[$b]})"; done
    fi
else
    echo ""
    echo "All tools relevant to this repository are available."
fi

exit 0
