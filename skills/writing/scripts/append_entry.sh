#!/usr/bin/env bash
# append_entry.sh <draft-root> <what> <why> <direction>
#
# Appends one fixed-shape entry to <draft-root>/.writing-journal.md.
# Fails loudly if the journal doesn't exist yet (run init_journal.sh
# first) so a session can never silently skip journaling.
set -euo pipefail

if [ $# -lt 4 ]; then
  echo "usage: append_entry.sh <draft-root> <what> <why> <stated-direction>" >&2
  exit 1
fi

root="$1"; what="$2"; why="$3"; direction="$4"
journal="$root/.writing-journal.md"

if [ ! -f "$journal" ]; then
  echo "error: no journal at $journal — run init_journal.sh first" >&2
  exit 1
fi

{
  echo
  echo "## $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- **what changed:** $what"
  echo "- **why:** $why"
  echo "- **stated direction:** $direction"
} >> "$journal"

echo "appended entry to $journal"
