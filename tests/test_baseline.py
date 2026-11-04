import importlib.util
import unittest
from pathlib import Path

class Baseline(unittest.TestCase):
    def test_version_two_runtime_available(self):
        self.assertTrue(Path('assets/workflow-scaffold/scripts/workflow_engine.py').exists(),
                        'missing DAG, lease, evidence-aware runtime')
    def test_independent_reviewer_contract(self):
        self.assertTrue(Path('assets/workflow-scaffold/.agents/reviewer.md').exists())
    def test_no_fixed_kickoff(self):
        self.assertNotIn('召开启动会（KICKOFF_MEETING）', Path('SKILL.md').read_text())
