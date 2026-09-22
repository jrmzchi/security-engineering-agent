#!/usr/bin/env bash
# Repository consistency check — mechanical recall only, no semantic
# judgment. See plays/repository-consistency.md for what this does and
# does not do, and tools/consistency-patterns.txt for the pattern
# source both this script and consistency-check.ps1 read (do not add
# an equivalent pattern list here — read that file instead).
#
# Usage: ./scripts/macos/consistency-check.sh [--help]

set -uo pipefail

BASH_VER_NUM=$(( ${BASH_VERSINFO[0]:-0} * 100 + ${BASH_VERSINFO[1]:-0} ))
if [ "$BASH_VER_NUM" -lt 404 ]; then
    # See scripts/macos/doctor.sh for why this bootstrap exists (stock
    # macOS ships Bash 3.2) — same logic, not duplicated in comments.
    for candidate in /opt/homebrew/bin/bash /usr/local/bin/bash; do
        if [ -x "$candidate" ]; then
            cand_num="$("$candidate" -c 'echo $(( BASH_VERSINFO[0]*100 + BASH_VERSINFO[1] ))' 2>/dev/null)"
            if [ -n "${cand_num:-}" ] && [ "$cand_num" -ge 404 ]; then
                exec "$candidate" "$0" ${1+"$@"}
            fi
        fi
    done
    echo "This script requires Bash 4.4 or later (found: ${BASH_VERSION:-unknown})." >&2
    echo "Install a newer Bash via Homebrew:  brew install bash" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PATTERNS_FILE="$REPO_ROOT/tools/consistency-patterns.txt"

for arg in ${1+"$@"}; do
    case "$arg" in
        -h|--help)
            echo "Usage: ./scripts/macos/consistency-check.sh"
            echo "Mechanical recall check over this kit's own repository."
            echo "See plays/repository-consistency.md. Takes no options."
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            exit 2
            ;;
    esac
done

if [ ! -f "$PATTERNS_FILE" ]; then
    echo "ERROR: pattern source not found: $PATTERNS_FILE" >&2
    exit 2
fi

# Directories this check never descends into — generated/vendored
# content, or work/ (session working notes and analysis reports, not
# this kit's own authored Markdown — exactly the kind of content that
# quotes a stale/vocabulary pattern verbatim while reporting on it,
# which is not the same as containing the mistake; see
# plays/repository-consistency.md's "Interpreting output").
PRUNE_ARGS=( -path '*/.git' -o -path '*/node_modules' -o -path '*/bin' -o -path '*/obj' -o -path '*/output' -o -path '*/__pycache__' -o -path '*/work' )

HITS=0
declare -A SECTION_PRINTED

print_header() {
    local category="$1"
    if [ -z "${SECTION_PRINTED[$category]:-}" ]; then
        echo ""
        echo "$category"
        SECTION_PRINTED[$category]=1
    fi
}

trim() {
    local s="$1"
    s="${s#"${s%%[![:space:]]*}"}"
    s="${s%"${s##*[![:space:]]}"}"
    printf '%s' "$s"
}

echo "Repository Consistency Check"

mapfile -d '' MD_FILES < <(find "$REPO_ROOT" \( "${PRUNE_ARGS[@]}" \) -prune -o -type f -name '*.md' -print0 2>/dev/null)

# --- STALE_TERM / VOCABULARY: pattern-file-driven recall ---------------
# One grep invocation per pattern across every file at once (-H forces
# filename prefixes even with a single file) — not one invocation per
# file per pattern, which is the same recall but orders of magnitude
# more subprocess spawns for no benefit.
if [ "${#MD_FILES[@]}" -gt 0 ]; then
    while IFS='|' read -r category pattern description || [ -n "$category" ]; do
        case "$category" in \#*|"") continue ;; esac
        [ "$category" != "STALE_TERM" ] && [ "$category" != "VOCABULARY" ] && continue
        [ -z "${pattern:-}" ] && continue

        while IFS= read -r line; do
            [ -z "$line" ] && continue
            file="${line%%:*}"
            rest="${line#*:}"
            lineno="${rest%%:*}"
            content="${rest#*:}"
            print_header "$category"
            echo "  ${file#$REPO_ROOT/}:$lineno"
            echo "  \"$(trim "$content")\""
            HITS=$((HITS + 1))
        done < <(grep -inHE "$pattern" -- "${MD_FILES[@]}" 2>/dev/null)
    done < "$PATTERNS_FILE"

    # --- BROKEN_REFERENCE: backtick-quoted path existence -------------------
    # Requires at least one "/" — a bare filename in backticks
    # (`finding-validation.md`) is overwhelmingly prose shorthand for a
    # path already given in full nearby, not a standalone reference;
    # matching those produced ~90% noise in testing. `.security/*` is
    # excluded on purpose — those files live in a TARGET repository
    # under review, never in this kit's own repository (see
    # plays/project-security-baseline.md's/attack-surface-mapping.md's
    # "Output" sections).
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        file="${line%%:*}"
        rest="${line#*:}"
        lineno="${rest%%:*}"
        ref="${rest#*:}"
        ref="${ref#\`}"
        ref="${ref%\`}"
        [ -z "$ref" ] && continue
        case "$ref" in
            http://*|https://*|.security/*) continue ;;
        esac
        if [ ! -e "$REPO_ROOT/$ref" ]; then
            print_header "BROKEN_REFERENCE"
            echo "  ${file#$REPO_ROOT/}:$lineno"
            echo "  \"$ref\""
            HITS=$((HITS + 1))
        fi
    done < <(grep -noHE '`[A-Za-z0-9_-]+(/[A-Za-z0-9_.-]+)+\.(md|ps1|sh|json|cs|py|js|txt)`' -- "${MD_FILES[@]}" 2>/dev/null)
fi

# --- HYGIENE: accidentally-TRACKED generated artifacts -------------------
# A generated-looking file that git already ignores is not a hygiene
# problem — it's doing what .gitignore is for. Only a file git commands
# would actually check in (add, commit, or stage) counts here. When git
# itself is unavailable, fall back to reporting filesystem presence
# (over-inclusive, but a check that runs everywhere beats one that
# silently does nothing without git).
GIT_AVAILABLE=false
if command -v git >/dev/null 2>&1 && git -C "$REPO_ROOT" --no-optional-locks rev-parse --git-dir >/dev/null 2>&1; then
    GIT_AVAILABLE=true
fi

is_git_tracked_or_addable() {
    # True if git would include this path in a commit: already tracked,
    # or untracked-and-not-ignored.
    local relpath="$1"
    if [ "$GIT_AVAILABLE" != true ]; then
        return 0
    fi
    local out
    out=$(git -C "$REPO_ROOT" --no-optional-locks status --porcelain --ignored -- "$relpath" 2>/dev/null)
    [ -n "$out" ] && case "$out" in "!! "*) return 1 ;; esac
    return 0
}

while IFS= read -r -d '' hit; do
    rel="${hit#$REPO_ROOT/}"
    if is_git_tracked_or_addable "$rel"; then
        print_header "HYGIENE"
        echo "  $rel"
        HITS=$((HITS + 1))
    fi
done < <(find "$REPO_ROOT" \( -path '*/.git' -o -path '*/node_modules' \) -prune -o \
    \( -type d -name '__pycache__' -o -name '*.pyc' \) -print0 2>/dev/null)

for d in output/scans output/reports; do
    if [ -d "$REPO_ROOT/$d" ]; then
        while IFS= read -r -d '' f; do
            rel="${f#$REPO_ROOT/}"
            if is_git_tracked_or_addable "$rel"; then
                print_header "HYGIENE"
                echo "  $rel"
                HITS=$((HITS + 1))
            fi
        done < <(find "$REPO_ROOT/$d" -type f ! -name '.gitkeep' -print0 2>/dev/null)
    fi
done

echo ""
if [ "$HITS" -eq 0 ]; then
    echo "Result:"
    echo "PASS"
    exit 0
else
    plural=""
    [ "$HITS" -ne 1 ] && plural="s"
    echo "Result:"
    echo "REVIEW_REQUIRED ($HITS hit$plural)"
    exit 1
fi
