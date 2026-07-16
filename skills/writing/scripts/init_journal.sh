#!/usr/bin/env bash
# init_journal.sh <draft-root>
#
# Idempotently creates <draft-root>/.writing-journal.md with a header if it
# doesn't already exist. Safe to call at the start of every WRITING session.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: init_journal.sh <draft-root>" >&2
  exit 1
fi

root="$1"
if [ ! -d "$root" ]; then
  echo "error: draft root '$root' is not a directory" >&2
  exit 1
fi

journal="$root/.writing-journal.md"

if [ -f "$journal" ]; then
  echo "journal already exists: $journal"
  exit 0
fi

cat > "$journal" <<'EOF'
# Writing Journal

Append-only. One entry per WRITING session, added by the skill at the end
of a session — not a manual chore. Each entry records what changed, why,
and what the author said (or implied) comes next. This file is the source
of truth for "what did I say I'd do next"; do not rewrite past entries
except to fix a factual error, and note the correction rather than
silently editing history.

The WRITING skill reads this whole file plus `git log -p` for the
manuscript on every invocation to reconcile stated direction against
actual changes, before doing any edit.

<!-- entries below, newest last -->
EOF

echo "created $journal"
