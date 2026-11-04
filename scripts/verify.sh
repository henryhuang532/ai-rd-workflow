#!/usr/bin/env bash
set -euo pipefail
SKILL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SKILL_ROOT"
python3 -m unittest discover -s tests -v
bash assets/workflow-scaffold/scripts/verify.sh
python3 - <<'PY'
from pathlib import Path
import re
import yaml
root=Path.cwd()
for path in root.rglob('*.yaml'):
    if '.git' not in path.parts:
        yaml.safe_load(path.read_text())
for path in [root/'SKILL.md', * (root/'references').glob('*.md'), *(root/'assets/workflow-scaffold').rglob('*.md')]:
    for dest in re.findall(r'\]\(([^)]+)\)',path.read_text()):
        if '://' in dest or dest.startswith('#'):
            continue
        assert (path.parent/dest.split('#')[0]).exists(), (path,dest)
a=(root/'references/workflow-file-contract.md').read_bytes()
b=(root/'assets/workflow-scaffold/docs/workflow-contract.md').read_bytes()
assert a==b, 'contract copies differ'
print('package: YAML, local Markdown links, synchronized contracts passed')
PY
git diff --check
