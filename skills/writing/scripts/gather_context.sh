#!/usr/bin/env bash
# gather_context.sh <manuscript-path> [n-commits]
#
# Prints the full journal for the manuscript's draft root plus the last
# n commits (default 20) of `git log -p` touching the manuscript file,
# so the skill can reconcile stated direction against actual changes
# in one pass. Read-only; makes no changes.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: gather_context.sh <manuscript-path> [n-commits]" >&2
  exit 1
fi

manuscript_path="$1"
n="${2:-20}"

if [ ! -e "$manuscript_path" ]; then
  echo "error: manuscript path '$manuscript_path' does not exist" >&2
  exit 1
fi

root="$(cd "$(dirname "$manuscript_path")" && pwd)"
base="$(basename "$manuscript_path")"
journal="$root/.writing-journal.md"

echo "=== JOURNAL: $journal ==="
if [ -f "$journal" ]; then
  cat "$journal"
else
  echo "(no journal yet at $journal — run init_journal.sh before the first session)"
fi

echo
echo "=== GIT LOG -p (last $n commits touching $base, root=$root) ==="
if git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if ! git -C "$root" log -p -n "$n" -- "$base"; then
    echo "(git log failed or no history for $base)"
  fi
  if [ -z "$(git -C "$root" log -n 1 -- "$base" 2>/dev/null)" ]; then
    echo "(no commits touch $base — manuscript may be untracked or edited outside git; flag this as a drift risk)"
  fi
else
  echo "(root is not inside a git work tree — manuscript history unavailable; rely on the journal alone and flag this as a drift risk in the brief)"
fi
