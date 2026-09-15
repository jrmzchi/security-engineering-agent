#!/usr/bin/env bash
# Runs the applicable security scanners against this repository and
# stores raw + normalized results under output/scans/<timestamp>/.
# Detects available tools and the repository's ecosystems, runs
# Semgrep, Gitleaks, OSV-Scanner, Trivy, and ecosystem-native audit
# tools where applicable, and writes results without requiring Docker
# for basic source-code/dependency scanning. An unavailable or failing
# tool is reported as a coverage gap rather than stopping the run —
# scanner output is candidate evidence for an AI reviewer to analyze
# afterward (see skills/security-review), not itself a final verdict.
#
# Coverage-gap detection is deliberately conservative: if a tool ran
# but produced no parseable output, that is treated as a gap rather
# than "zero findings" — CLI flags for external tools can change across
# versions, and a rejected flag should never look identical to a clean
# scan.
#
# Usage: ./scripts/macos/scan.sh [--diff-only] [--diff-base <ref>] [--mode <QUICK|STANDARD|DEEP|TARGETED>]

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
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

DIFF_ONLY=false
DIFF_BASE="HEAD"
MODE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --diff-only)
            DIFF_ONLY=true
            shift
            ;;
        --diff-base)
            if [ $# -lt 2 ]; then
                echo "--diff-base requires a value" >&2
                exit 3
            fi
            DIFF_BASE="$2"
            shift 2
            ;;
        --mode)
            if [ $# -lt 2 ]; then
                echo "--mode requires a value" >&2
                exit 3
            fi
            MODE="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 3
            ;;
    esac
done
if [ -z "$MODE" ]; then
    if [ "$DIFF_ONLY" = true ]; then MODE="TARGETED"; else MODE="STANDARD"; fi
fi

PY="$(command -v python3 || true)"

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

# All JSON reading/writing goes through python3 rather than hand-rolled
# string concatenation or a jq/python3 dual path — this guarantees
# correct escaping and correct types (numbers vs strings vs null)
# regardless of what characters appear in a repo path or a coverage-gap
# message. If python3 is unavailable, this script cannot produce a
# normalized summary at all; it still runs the scanners and leaves raw
# output on disk, and says so.
if [ -z "$PY" ]; then
    echo "WARNING: python3 not found — normalized/summary.json will not be written (raw scanner output will still be saved)." >&2
fi

json_get_count() {
    # $1 = file, $2 = python expression (relative to `data`) for the
    # array whose length to report, e.g. "data['results']" or "data".
    # Prints an integer, or nothing (caller treats missing output as
    # "could not determine", never as zero) if the file is missing,
    # empty, invalid JSON, or the expression doesn't resolve to a list.
    local file="$1" expr="$2"
    [ -n "$PY" ] || return 0
    [ -s "$file" ] || return 0
    "$PY" - "$file" <<PYEOF 2>/dev/null
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    val = $expr
    if isinstance(val, list):
        print(len(val))
except Exception:
    pass
PYEOF
}

TIMESTAMP="$(date +%Y-%m-%dT%H%M%S)"
SCAN_DIR="$REPO_ROOT/output/scans/$TIMESTAMP"
RAW_DIR="$SCAN_DIR/raw"
NORMALIZED_DIR="$SCAN_DIR/normalized"
mkdir -p "$RAW_DIR" "$NORMALIZED_DIR"

echo "Scanning: $REPO_ROOT"
echo "Output:   $SCAN_DIR"
echo ""

GIT_COMMIT=""
DIRTY="false"
if command -v git >/dev/null 2>&1; then
    # git prints the unresolved ref name back to stdout as part of its
    # own error message when HEAD can't be resolved (e.g. a repo with
    # no commits yet) - capturing stdout alone would silently record
    # the literal string "HEAD" as if it were a real commit hash.
    # Check the exit code explicitly rather than trusting non-empty
    # output.
    if commit_out="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null)"; then
        GIT_COMMIT="$commit_out"
    fi
    if [ -n "$(git -C "$REPO_ROOT" status --short 2>/dev/null)" ]; then DIRTY="true"; fi
fi

get_tool_version() {
    # Best-effort version string for scan metadata; never fails the
    # script if the tool is missing or its version flag errors.
    local cmd="$1"; shift
    command -v "$cmd" >/dev/null 2>&1 || return 0
    "$cmd" "$@" 2>/dev/null | head -n1 || true
}
SEMGREP_VERSION="$(get_tool_version semgrep --version)"
GITLEAKS_VERSION="$(get_tool_version gitleaks version)"
OSV_SCANNER_VERSION="$(get_tool_version osv-scanner --version)"
TRIVY_VERSION="$(get_tool_version trivy --version)"

HAS_DOTNET=false; HAS_NODE=false; HAS_PYTHON=false
has_pattern '*.csproj' && HAS_DOTNET=true
has_pattern '*.sln' && HAS_DOTNET=true
has_pattern '*.fsproj' && HAS_DOTNET=true
has_pattern 'package.json' && HAS_NODE=true
has_pattern 'requirements.txt' && HAS_PYTHON=true
has_pattern 'pyproject.toml' && HAS_PYTHON=true
has_pattern 'setup.py' && HAS_PYTHON=true
has_pattern 'Pipfile' && HAS_PYTHON=true
HAS_REQUIREMENTS_TXT=false
[ -f "$REPO_ROOT/requirements.txt" ] && HAS_REQUIREMENTS_TXT=true

COVERAGE_GAPS=()
declare -A FINDINGS_COUNT
ANY_TOOL_RAN=false

add_gap() { COVERAGE_GAPS+=("$1"); }

# --- Semgrep ---
if command -v semgrep >/dev/null 2>&1; then
    ANY_TOOL_RAN=true
    SEMGREP_TARGETS=("$REPO_ROOT")
    if [ "$DIFF_ONLY" = true ] && command -v git >/dev/null 2>&1; then
        mapfile -t CHANGED < <(git -C "$REPO_ROOT" diff --name-only "$DIFF_BASE" -- 2>/dev/null)
        CHANGED_FULL=()
        for f in "${CHANGED[@]:-}"; do
            [ -z "$f" ] && continue
            [ -e "$REPO_ROOT/$f" ] && CHANGED_FULL+=("$REPO_ROOT/$f")
        done
        # No changed files matched (or diff itself failed) — fall back
        # to scanning the whole tree rather than passing no target at
        # all, which semgrep would reject as an error.
        [ "${#CHANGED_FULL[@]}" -gt 0 ] && SEMGREP_TARGETS=("${CHANGED_FULL[@]}")
    fi
    SEMGREP_STDERR="$RAW_DIR/semgrep.stderr.log"
    semgrep scan --config auto --json --quiet "${SEMGREP_TARGETS[@]}" > "$RAW_DIR/semgrep.json" 2>"$SEMGREP_STDERR"
    SEMGREP_EXIT=$?
    if [ ! -s "$RAW_DIR/semgrep.json" ]; then
        add_gap "semgrep ran (exit $SEMGREP_EXIT) but produced no output. stderr: $(cat "$SEMGREP_STDERR" 2>/dev/null)"
    else
        count="$(json_get_count "$RAW_DIR/semgrep.json" "data['results']")"
        if [ -n "$count" ]; then
            FINDINGS_COUNT[semgrep]="$count"
        else
            add_gap "semgrep ran but its output did not contain a parseable 'results' array — possible CLI flag mismatch for the installed version, or python3 unavailable to check."
        fi
    fi
else
    add_gap "Scanner unavailable: semgrep (not found on PATH). Coverage impact: automated static-analysis candidates unavailable for this run. Fallback: manual semantic review per plays/code-review.md."
fi

# --- Gitleaks ---
# --redact is gitleaks' own, tested redaction — the primary control
# against ever writing a live secret to disk. No further post-
# processing is layered on top: a hand-rolled second pass that reads,
# parses, and rewrites the file is itself a second place a real secret
# could end up unredacted if that step fails silently, which is exactly
# the failure mode this replaces.
if command -v gitleaks >/dev/null 2>&1; then
    ANY_TOOL_RAN=true
    GITLEAKS_RAW="$RAW_DIR/gitleaks.json"
    GITLEAKS_STDERR="$RAW_DIR/gitleaks.stderr.log"
    gitleaks detect --no-git --redact --source "$REPO_ROOT" --report-format json --report-path "$GITLEAKS_RAW" --exit-code 0 >/dev/null 2>"$GITLEAKS_STDERR"
    GITLEAKS_EXIT=$?
    if [ ! -s "$GITLEAKS_RAW" ]; then
        # No report file can legitimately mean "zero findings" — but
        # only trust that when the exit code also looks like
        # success/no-findings (0 or 1).
        if [ "$GITLEAKS_EXIT" -eq 0 ] || [ "$GITLEAKS_EXIT" -eq 1 ]; then
            FINDINGS_COUNT[gitleaks]=0
        else
            add_gap "gitleaks exited with code $GITLEAKS_EXIT and produced no report. stderr: $(cat "$GITLEAKS_STDERR" 2>/dev/null)"
        fi
    else
        count="$(json_get_count "$GITLEAKS_RAW" "data")"
        if [ -n "$count" ]; then
            FINDINGS_COUNT[gitleaks]="$count"
        else
            add_gap "gitleaks produced a report but its contents could not be parsed as a JSON array."
        fi
    fi
else
    add_gap "Scanner unavailable: gitleaks (not found on PATH). Coverage impact: automated secret detection unavailable for this run. Fallback: manual secret review per plays/secrets-security.md."
fi

# --- OSV-Scanner ---
if command -v osv-scanner >/dev/null 2>&1; then
    ANY_TOOL_RAN=true
    OSV_RAW="$RAW_DIR/osv-scanner.json"
    OSV_STDERR="$RAW_DIR/osv-scanner.stderr.log"
    osv-scanner --recursive --format json --output "$OSV_RAW" "$REPO_ROOT" 2>"$OSV_STDERR"
    OSV_EXIT=$?
    if [ ! -s "$OSV_RAW" ]; then
        if [ "$OSV_EXIT" -eq 0 ] || [ "$OSV_EXIT" -eq 1 ]; then
            FINDINGS_COUNT[osv-scanner]=0
        else
            add_gap "osv-scanner exited with code $OSV_EXIT and produced no report — possible CLI flag mismatch for the installed version. stderr: $(cat "$OSV_STDERR" 2>/dev/null)"
        fi
    else
        count="$(json_get_count "$OSV_RAW" "data['results']")"
        if [ -n "$count" ]; then
            FINDINGS_COUNT[osv-scanner]="$count"
        else
            add_gap "osv-scanner ran but its output did not contain a parseable 'results' array — possible CLI flag mismatch for the installed version."
        fi
    fi
else
    add_gap "Scanner unavailable: osv-scanner (not found on PATH). Coverage impact: automated dependency-vulnerability detection unavailable for this run. Fallback: ecosystem-native tools below, or manual review per plays/dependency-security.md."
fi

# --- Trivy (optional) ---
if command -v trivy >/dev/null 2>&1; then
    ANY_TOOL_RAN=true
    TRIVY_RAW="$RAW_DIR/trivy.json"
    TRIVY_STDERR="$RAW_DIR/trivy.stderr.log"
    trivy fs --scanners vuln,misconfig --format json --output "$TRIVY_RAW" "$REPO_ROOT" 2>"$TRIVY_STDERR"
    TRIVY_EXIT=$?
    if [ ! -s "$TRIVY_RAW" ]; then
        if [ "$TRIVY_EXIT" -eq 0 ] || [ "$TRIVY_EXIT" -eq 1 ]; then
            FINDINGS_COUNT[trivy]=0
        else
            add_gap "trivy exited with code $TRIVY_EXIT and produced no report — possible CLI flag mismatch for the installed version (e.g. --scanners value naming changed between versions). stderr: $(cat "$TRIVY_STDERR" 2>/dev/null)"
        fi
    else
        count="$(json_get_count "$TRIVY_RAW" "data['Results']")"
        if [ -n "$count" ]; then
            FINDINGS_COUNT[trivy]="$count"
        else
            add_gap "trivy ran but its output did not contain a parseable 'Results' array — possible CLI flag mismatch for the installed version."
        fi
    fi
else
    add_gap "Scanner unavailable: trivy (not found on PATH). Coverage impact: none required — trivy is an optional enhancement over osv-scanner/gitleaks for this project type."
fi

# --- Ecosystem-native tools ---
if [ "$HAS_DOTNET" = true ]; then
    if command -v dotnet >/dev/null 2>&1; then
        ANY_TOOL_RAN=true
        (cd "$REPO_ROOT" && dotnet list package --vulnerable --include-transitive) > "$RAW_DIR/dotnet-list-package-vulnerable.txt" 2>&1
        FINDINGS_COUNT[dotnet-list-package]="see raw output (text format, not machine-parsed)"
    else
        add_gap "dotnet unavailable. Coverage impact: .NET dependency vulnerabilities not double-checked via native tooling (osv-scanner above still covers this ecosystem if it ran)."
    fi
fi
if [ "$HAS_NODE" = true ]; then
    if command -v npm >/dev/null 2>&1; then
        ANY_TOOL_RAN=true
        NPM_RAW="$RAW_DIR/npm-audit.json"
        NPM_STDERR="$RAW_DIR/npm-audit.stderr.log"
        (cd "$REPO_ROOT" && npm audit --json) > "$NPM_RAW" 2>"$NPM_STDERR"
        if [ ! -s "$NPM_RAW" ]; then
            add_gap "npm audit produced no output. stderr: $(cat "$NPM_STDERR" 2>/dev/null)"
        else
            count="$([ -n "$PY" ] && "$PY" - "$NPM_RAW" <<'PYEOF' 2>/dev/null
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    vulns = data.get("metadata", {}).get("vulnerabilities")
    if isinstance(vulns, dict):
        if "total" in vulns:
            print(vulns["total"])
        else:
            print(sum(v for k, v in vulns.items() if k != "total" and isinstance(v, int)))
except Exception:
    pass
PYEOF
)"
            if [ -n "$count" ]; then
                FINDINGS_COUNT[npm-audit]="$count"
            else
                add_gap "npm audit ran but its output did not contain the expected metadata.vulnerabilities field — possible npm version mismatch."
            fi
        fi
    else
        add_gap "npm unavailable. Coverage impact: Node dependency vulnerabilities not double-checked via native tooling."
    fi
fi
if [ "$HAS_PYTHON" = true ]; then
    if command -v pip-audit >/dev/null 2>&1; then
        ANY_TOOL_RAN=true
        PIP_RAW="$RAW_DIR/pip-audit.json"
        PIP_STDERR="$RAW_DIR/pip-audit.stderr.log"
        PIP_ARGS=(--format json)
        [ "$HAS_REQUIREMENTS_TXT" = true ] && PIP_ARGS+=(-r "$REPO_ROOT/requirements.txt")
        (cd "$REPO_ROOT" && pip-audit "${PIP_ARGS[@]}") > "$PIP_RAW" 2>"$PIP_STDERR"
        if [ ! -s "$PIP_RAW" ]; then
            add_gap "pip-audit produced no output. stderr: $(cat "$PIP_STDERR" 2>/dev/null)"
        else
            # pip-audit's JSON is {"dependencies": [...], "fixes": [...]},
            # each dependency optionally carrying its own "vulns" list —
            # not a flat list of only-vulnerable entries.
            count="$([ -n "$PY" ] && "$PY" - "$PIP_RAW" <<'PYEOF' 2>/dev/null
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    deps = data.get("dependencies")
    if isinstance(deps, list):
        print(sum(len(d.get("vulns") or []) for d in deps))
except Exception:
    pass
PYEOF
)"
            if [ -n "$count" ]; then
                FINDINGS_COUNT[pip-audit]="$count"
                if [ "$HAS_REQUIREMENTS_TXT" = false ]; then
                    add_gap "pip-audit scanned the current Python environment (no requirements.txt found at repo root to scan directly) — results may not reflect this repository's declared dependencies exactly."
                fi
            else
                add_gap "pip-audit ran but its output did not contain the expected 'dependencies' field — possible pip-audit version mismatch."
            fi
        fi
    else
        add_gap "pip-audit unavailable. Coverage impact: Python dependency vulnerabilities not double-checked via native tooling (osv-scanner above still covers this ecosystem if it ran)."
    fi
fi

# --- Summary ---
# Write findings-count and coverage-gap lines to intermediate files and
# hand them to python3 for assembly, rather than hand-building JSON
# with echo/string interpolation — this is what guarantees correct
# escaping and correct types (integers vs strings vs null) regardless
# of what characters appear in a repo path or a gap message.
FINDINGS_TXT="$SCAN_DIR/.findings_count.tmp"
GAPS_TXT="$SCAN_DIR/.coverage_gaps.tmp"
: > "$FINDINGS_TXT"
for key in "${!FINDINGS_COUNT[@]}"; do
    printf '%s\t%s\n' "$key" "${FINDINGS_COUNT[$key]}" >> "$FINDINGS_TXT"
done
: > "$GAPS_TXT"
for gap in "${COVERAGE_GAPS[@]:-}"; do
    [ -z "$gap" ] && continue
    printf '%s\n' "$gap" >> "$GAPS_TXT"
done

SUMMARY_PATH="$NORMALIZED_DIR/summary.json"
if [ -n "$PY" ]; then
    SCAN_ARGS=(
        "$SUMMARY_PATH" "$FINDINGS_TXT" "$GAPS_TXT" "$TIMESTAMP" "$REPO_ROOT"
        "$GIT_COMMIT" "$DIRTY" "$MODE" "$DIFF_ONLY" "$DIFF_BASE"
        "$HAS_DOTNET" "$HAS_NODE" "$HAS_PYTHON"
        "$SEMGREP_VERSION" "$GITLEAKS_VERSION" "$OSV_SCANNER_VERSION" "$TRIVY_VERSION"
    )
    "$PY" - "${SCAN_ARGS[@]}" <<'PYEOF'
import json, sys

(out_path, findings_txt, gaps_txt, timestamp, repo_root,
 git_commit, dirty, mode, diff_only, diff_base,
 has_dotnet, has_node, has_python,
 semgrep_version, gitleaks_version, osv_scanner_version, trivy_version) = sys.argv[1:18]

def to_bool(s):
    return s == "true"

def none_if_empty(s):
    return s if s else None

findings = {}
with open(findings_txt, encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n")
        if not line:
            continue
        key, _, value = line.partition("\t")
        try:
            findings[key] = int(value)
        except ValueError:
            findings[key] = value

gaps = []
with open(gaps_txt, encoding="utf-8") as f:
    gaps = [line.rstrip("\n") for line in f if line.strip()]

diff_only_b = to_bool(diff_only)
summary = {
    "timestamp": timestamp,
    "repoRoot": repo_root,
    "gitCommit": none_if_empty(git_commit),
    "dirty": to_bool(dirty),
    "mode": mode,
    "diffOnly": diff_only_b,
    "diffBase": diff_base if diff_only_b else None,
    "ecosystems": {
        "dotnet": to_bool(has_dotnet),
        "node": to_bool(has_node),
        "python": to_bool(has_python),
    },
    "toolVersions": {
        "semgrep": none_if_empty(semgrep_version),
        "gitleaks": none_if_empty(gitleaks_version),
        "osv-scanner": none_if_empty(osv_scanner_version),
        "trivy": none_if_empty(trivy_version),
    },
    "findingsCount": findings,
    "coverageGaps": gaps,
}

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
PYEOF
else
    echo "(python3 unavailable — writing a minimal, unescaped summary; treat findingsCount/coverageGaps as approximate)" > "$SUMMARY_PATH"
fi
rm -f "$FINDINGS_TXT" "$GAPS_TXT"

echo ""
echo "Findings count (raw, per tool — not yet validated):"
for key in "${!FINDINGS_COUNT[@]}"; do echo "  $key: ${FINDINGS_COUNT[$key]}"; done

if [ "${#COVERAGE_GAPS[@]}" -gt 0 ]; then
    echo ""
    echo "Coverage gaps:"
    for gap in "${COVERAGE_GAPS[@]}"; do echo "  - $gap"; done
fi

echo ""
echo "Raw output:         $RAW_DIR"
echo "Normalized summary:  $SUMMARY_PATH"
echo ""
echo "Scanner output above is CANDIDATE evidence only. Follow"
echo "skills/security-review to analyze it — do not report a"
echo "finding as confirmed solely because a scanner flagged it."

if [ "$ANY_TOOL_RAN" = false ]; then
    echo "No scanner could be run at all — see coverage gaps above. Run ./scripts/macos/doctor.sh to see what is missing." >&2
    exit 2
fi

exit 0
