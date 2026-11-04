#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 scripts/workflow_check.py --stage schema

status="$(
python3 - <<'PY'
from pathlib import Path
import yaml

data = yaml.safe_load(Path("workflow/current-task.yaml").read_text(encoding="utf-8"))
print(data.get("status", ""))
PY
)"

case "$status" in
  REQUIREMENT_INPUT|PRODUCT_DESIGN|PRODUCT_REVIEW|BLOCKED|NEEDS_USER_INPUT|CANCELLED)
    echo "verify: current workflow status is $status; schema gate is the applicable gate."
    ;;
  TECHNICAL_DESIGN|DEVELOPMENT)
    python3 scripts/workflow_check.py --stage product
    ;;
  UNIT_TEST|FUNCTIONAL_TEST|BUG_FIX)
    python3 scripts/workflow_check.py --stage development
    ;;
  ACCEPTANCE)
    python3 scripts/workflow_check.py --stage testing
    ;;
  DONE)
    python3 scripts/workflow_check.py --stage done
    ;;
  *)
    echo "verify: unsupported workflow status: $status" >&2
    exit 1
    ;;
esac

if [[ -f pom.xml ]]; then
  mvn clean verify
else
  echo "verify: pom.xml not found; Maven tests/build are not applicable for the current empty Java foundation workspace."
fi
