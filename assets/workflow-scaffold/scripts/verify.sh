#!/usr/bin/env bash
set -euo pipefail
WORKFLOW_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WORKFLOW_ROOT"
python3 scripts/workflow_check.py --stage schema
python3 -m unittest discover -s tests -v
if [[ $# -gt 0 ]]; then
  "$@"
else
  echo 'verify: project checks not configured; workflow checks only. Supply the real project verification command as argv.'
fi
