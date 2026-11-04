"""Workflow contract tests.

State/approval/review fixtures are simulations, never human authorization.
Git/subprocess/filesystem tests execute locally in isolated temporary directories.
"""
import copy
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ENGINE = Path(__file__).resolve().parents[1] / 'scripts/workflow_engine.py'


class EngineScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ENGINE.exists():
            raise AssertionError('workflow_engine.py missing: no executable v2 contract')
        spec = importlib.util.spec_from_file_location('workflow_engine', ENGINE)
        cls.e = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.e)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        (self.root / 'code.txt').write_text('base\n')
        self.git('add', 'code.txt')
        self.git('commit', '-qm', 'fixture')
        self.state = self.e.new_state()
        self.task = self.e.new_task('TASK-001', 'fixture', risk=1)
        self.state['tasks'].append(self.task)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.STDOUT, text=True).strip()

    def prepare_plan(self):
        """SIMULATED specialist records; real files/hashes, no real human approval."""
        (self.root / 'workflow').mkdir(exist_ok=True)
        for name in ('design', 'plan', 'approval', 'feasibility', 'review', 'integration', 'delivery'):
            (self.root / 'workflow' / (name + '.md')).write_text('SIMULATION: ' + name)
        for name in ('design', 'plan'):
            self.task[name] = self.e.artifact(self.root, 'workflow/' + name + '.md')
        self.task['requirements'] = [{'requirement_id': 'REQ-001', 'acceptance_ids': ['AC-REQ-001-01']}]
        self.task['requirement_ids'] = ['REQ-001']
        self.task['acceptance_criteria'] = ['AC-REQ-001-01']
        self.task['feasibility'] = {'checks': {k: True for k in self.e.CHECKS},
                                    'evidence': [self.e.artifact(self.root, 'workflow/feasibility.md')]}
        self.task['authorization'] = {
            'decision': 'approved', 'kind': 'preauthorized', 'risk_level': self.task['risk_level'],
            'scope': ['TASK-001'], 'source': self.e.artifact(self.root, 'workflow/approval.md'),
            'design_sha256': self.task['design']['sha256'], 'plan_sha256': self.task['plan']['sha256']}
        self.state['capabilities']['independent_sessions'] = True

    def advance_to_review(self):
        self.prepare_plan()
        self.e.claim(self.state, 'TASK-001', 'session-matt', self.root, self.root)
        self.task['implementation_sessions'] = ['session-matt']
        behavior = [sys.executable, '-c', "from pathlib import Path; assert Path('code.txt').read_text() == 'fixed\\n'"]
        red = self.e.run_evidence(self.root, behavior, 'matt', 'session-matt', ['AC-REQ-001-01'])
        (self.root / 'code.txt').write_text('fixed\n')
        green = self.e.run_evidence(self.root, behavior, 'matt', 'session-matt', ['AC-REQ-001-01'])
        self.task['tdd'] = [dict(red=red, green=green, acceptance_ids=['AC-REQ-001-01'],
                                failure_reason='SIMULATION: code.txt must contain fixed instead of base')]
        for stage in ['REQUIREMENTS', 'DESIGN', 'FEASIBILITY', 'PLANNING', 'APPROVAL', 'IMPLEMENTATION', 'INTEGRATION', 'CODE_REVIEW']:
            self.e.transition(self.state, 'TASK-001', 'RUNNING', stage, 'orchestrator', self.root)
        self.task['reviews'] = [dict(dimension=dim, role='reviewer', session='session-reviewer',
                                     verdict='pass', snapshot=self.e.snapshot(self.root),
                                     report=self.e.artifact(self.root, 'workflow/review.md'))
                                for dim in ('standards', 'spec')]

    def finish(self):
        self.e.transition(self.state, 'TASK-001', 'RUNNING', 'QA', 'orchestrator', self.root)
        self.task['tests'] = [self.e.run_evidence(self.root, [sys.executable, '-c', 'print("independent fixture QA")'],
                                                  'tester', 'session-tester', ['AC-REQ-001-01'])]
        integration_command = self.e.run_evidence(self.root, [sys.executable, '-c', 'print("integration fixture")'],
                                                   'integration', 'session-integration', ['AC-REQ-001-01'])
        self.task['integration'] = dict(command_evidence=integration_command, snapshot=self.e.snapshot(self.root), passed=True,
                                       evidence=self.e.artifact(self.root, 'workflow/integration.md'))
        self.task['delivery_report'] = self.e.artifact(self.root, 'workflow/delivery.md')
        self.e.transition(self.state, 'TASK-001', 'RUNNING', 'DELIVERY', 'orchestrator', self.root)
        self.e.transition(self.state, 'TASK-001', 'COMPLETED', 'DELIVERY', 'orchestrator', self.root)
        self.e.validate(self.state, self.root, delivery=True)

    def test_01_small_bug_completes_without_meeting(self):
        self.advance_to_review()
        self.finish()
        self.assertEqual(self.task['status'], 'COMPLETED')
        self.assertNotIn('meeting', self.task)

    def test_02_ordinary_feature_completes(self):
        self.task['risk_level'] = 2
        self.advance_to_review()
        self.finish()
        self.assertEqual(self.task['status'], 'COMPLETED')

    def test_06_design_change_invalidates_old_approval(self):
        self.prepare_plan()
        (self.root / 'workflow/design.md').write_text('SIMULATED revised design')
        self.task['design'] = self.e.artifact(self.root, 'workflow/design.md')
        with self.assertRaisesRegex(self.e.WorkflowError, 'stale design approval'):
            self.e.authorize(self.task, self.root)

    def test_07_reviewer_rejects_code(self):
        self.advance_to_review()
        self.task['reviews'][-1]['verdict'] = 'reject'
        with self.assertRaises(self.e.WorkflowError):
            self.e.transition(self.state, 'TASK-001', 'RUNNING', 'QA', 'orchestrator', self.root)

    def test_07_matt_cannot_review_own_code(self):
        self.advance_to_review()
        self.task['reviews'][-1]['session'] = 'session-matt'
        with self.assertRaisesRegex(self.e.WorkflowError, 'self review'):
            self.e.review_gate(self.task, self.root)

    def test_08_defect_can_enter_fix_and_requires_review_again(self):
        self.advance_to_review()
        self.e.transition(self.state, 'TASK-001', 'RUNNING', 'QA', 'orchestrator', self.root)
        bug = self.e.defect(self.state, 'TASK-001', 'BUG-001', 'implementation')
        self.assertEqual(bug['owner'], 'matt')
        self.e.transition(self.state, 'TASK-001', 'RUNNING', 'FIX', 'orchestrator', self.root)
        self.assertEqual(self.task['stage'], 'FIX')
        with self.assertRaises(self.e.WorkflowError):
            self.e.transition(self.state, 'TASK-001', 'RUNNING', 'DELIVERY', 'orchestrator', self.root)
        self.e.transition(self.state, 'TASK-001', 'RUNNING', 'CODE_REVIEW', 'orchestrator', self.root)

    def test_10_code_change_invalidates_test_evidence(self):
        self.prepare_plan()
        self.task['tests'] = [self.e.run_evidence(self.root, [sys.executable, '-c', 'print("pass")'],
                                                  'tester', 'session-tester', ['AC-REQ-001-01'])]
        (self.root / 'code.txt').write_text('changed after QA')
        with self.assertRaisesRegex(self.e.WorkflowError, 'version mismatch'):
            self.e.test_gate(self.task, self.root)

    def test_14_exit_status_field_forgery_rejected(self):
        self.prepare_plan()
        evidence = self.e.run_evidence(self.root, [sys.executable, '-c', 'raise SystemExit(7)'],
                                       'tester', 'session-tester', ['AC-REQ-001-01'])
        evidence['exit_code'] = 0
        self.task['tests'] = [evidence]
        with self.assertRaisesRegex(self.e.WorkflowError, 'differ from command receipt'):
            self.e.test_gate(self.task, self.root)

    def test_real_timeout_retains_command_receipt(self):
        evidence = self.e.run_evidence(self.root, [sys.executable, '-c', 'import time; time.sleep(2)'],
                                       'tester', 'session-tester', ['AC-001'], timeout=0.05)
        self.assertEqual(evidence['exit_code'], 124)
        self.assertTrue(evidence['timed_out'])
        self.assertTrue((self.root / evidence['receipt']['path']).exists())

    def test_01_initial_state_has_separate_lifecycle_and_stage(self):
        self.e.validate(self.state, self.root)
        self.assertEqual(self.task['status'], 'PENDING')
        self.assertEqual(self.task['stage'], 'INTAKE')

    def test_03_complex_dag_dependency_completion_controls_readiness(self):
        b = self.e.new_task('TASK-002', 'dependent', risk=3)
        b['dependencies'] = ['TASK-001']
        self.state['tasks'].append(b)
        self.assertNotIn('TASK-002', self.e.ready(self.state, self.root))

    def test_03_dag_cycle_rejected(self):
        b = self.e.new_task('TASK-002', 'dependent')
        b['dependencies'] = ['TASK-001']
        self.task['dependencies'] = ['TASK-002']
        self.state['tasks'].append(b)
        with self.assertRaises(self.e.WorkflowError):
            self.e.validate(self.state, self.root)

    def test_03_missing_dependency_rejected(self):
        self.task['dependencies'] = ['UNKNOWN']
        with self.assertRaises(self.e.WorkflowError):
            self.e.validate(self.state, self.root)

    def test_04_independent_tasks_are_logically_ready(self):
        b = self.e.new_task('TASK-002', 'independent')
        self.state['tasks'].append(b)
        (self.root / 'workflow').mkdir(exist_ok=True)
        (self.root / 'workflow/probe.txt').write_text('SIMULATED independent-session probe')
        self.state['capabilities'].update(mode='parallel', independent_sessions=True, probe=self.e.artifact(self.root, 'workflow/probe.txt'))
        self.state['policy']['max_parallel'] = 2
        self.assertEqual(set(self.e.ready(self.state, self.root)), {'TASK-001', 'TASK-002'})

    def test_05_high_risk_cannot_jump_to_implementation(self):
        self.task['risk_level'] = 4
        with self.assertRaises(self.e.WorkflowError):
            self.e.transition(self.state, 'TASK-001', 'RUNNING', 'IMPLEMENTATION', 'orchestrator', self.root)

    def test_11_429_retains_failure_and_bounds_retries(self):
        for index in range(self.state['policy']['max_attempts']):
            if index:
                self.e.transition(self.state, 'TASK-001', 'READY', 'INTAKE', 'orchestrator', self.root)
            self.e.claim(self.state, 'TASK-001', 'session-a', self.root, self.root)
            self.e.fail(self.state, 'TASK-001', 'Codex 429', now=1000)
        self.assertIn(self.task['status'], ('BLOCKED', 'FAILED'))
        self.assertIn('429', str(self.task))

    def test_11_expired_lease_preserves_checkpoint(self):
        self.task.update(status='RUNNING', stage='IMPLEMENTATION', lease={
            'session': 'session-a', 'expires_at': 10, 'workspace': str(self.root)
        })
        self.task['checkpoint'] = {'last_safe_step': 'red-test'}
        self.e.recover(self.state, now=20)
        self.assertNotEqual(self.task['status'], 'RUNNING')
        self.assertEqual(self.task['checkpoint']['last_safe_step'], 'red-test')

    def test_12_nonidempotent_operation_replay_rejected(self):
        self.assertTrue(self.e.operation(self.state, 'TASK-001', 'charge-001', idempotent=False))
        with self.assertRaises(self.e.WorkflowError):
            self.e.operation(self.state, 'TASK-001', 'charge-001', idempotent=False)

    def test_12_idempotent_operation_is_not_reexecuted(self):
        self.assertTrue(self.e.operation(self.state, 'TASK-001', 'read-001', idempotent=True))
        self.task['operations']['read-001']['status'] = 'completed'
        self.assertFalse(self.e.operation(self.state, 'TASK-001', 'read-001', idempotent=True))

    def test_14_direct_completion_without_evidence_rejected(self):
        with self.assertRaises(self.e.WorkflowError):
            self.e.transition(self.state, 'TASK-001', 'COMPLETED', 'DELIVERY', 'orchestrator', self.root)

    def test_14_forged_status_without_history_or_evidence_rejected(self):
        self.task.update(status='COMPLETED', stage='DELIVERY')
        with self.assertRaises(self.e.WorkflowError):
            self.e.validate(self.state, self.root, delivery=True)

    def test_08_tester_defect_routes_to_fix(self):
        bug = self.e.defect(self.state, 'TASK-001', 'BUG-001', 'implementation')
        self.assertEqual(bug['bug_id'], 'BUG-001')
        self.assertEqual(bug['owner'], 'matt')
        self.assertNotEqual(self.task['status'], 'COMPLETED')

    def test_09_repeated_defect_failure_escalates(self):
        self.e.claim(self.state, 'TASK-001', 'session-a', self.root, self.root)
        for _ in range(self.state['policy']['max_attempts'] + 1):
            self.e.defect(self.state, 'TASK-001', 'BUG-001', 'implementation')
        self.assertIn(self.task['status'], ('BLOCKED', 'FAILED'))
        self.assertIn('reviewer', str(self.task).lower())

    def test_13_real_git_merge_conflict_cannot_complete(self):
        original_branch = self.git('branch', '--show-current')
        self.git('checkout', '-qb', 'side')
        (self.root / 'code.txt').write_text('side\n')
        self.git('commit', '-qam', 'side')
        self.git('checkout', original_branch)
        (self.root / 'code.txt').write_text('main\n')
        self.git('commit', '-qam', 'main')
        merged = subprocess.run(['git', '-C', str(self.root), 'merge', 'side'], capture_output=True)
        self.assertNotEqual(merged.returncode, 0)
        self.assertTrue(self.git('diff', '--name-only', '--diff-filter=U'))
        with self.assertRaises(self.e.WorkflowError):
            self.e.transition(self.state, 'TASK-001', 'COMPLETED', 'DELIVERY', 'orchestrator', self.root)

    def test_05_level4_preauthorization_is_insufficient(self):
        self.task['risk_level'] = 4
        self.prepare_plan()
        with self.assertRaisesRegex(self.e.WorkflowError, 'explicit human'):
            self.e.authorize(self.task, self.root)

    def test_04_serial_fallback_limits_actual_claims(self):
        self.state['tasks'].append(self.e.new_task('TASK-002', 'independent'))
        self.state['policy']['max_parallel'] = 4
        self.assertEqual(self.e.ready(self.state, self.root), ['TASK-001'])
        self.e.claim(self.state, 'TASK-001', 'session-a', self.root, self.root)
        with self.assertRaises(self.e.WorkflowError):
            self.e.claim(self.state, 'TASK-002', 'session-b', self.root, self.root)

    def test_real_atomic_store_rejects_invalid_update(self):
        import yaml
        path = self.root / 'workflow/current-task.yaml'
        path.parent.mkdir(exist_ok=True)
        path.write_text(yaml.safe_dump(self.state))
        before = path.read_bytes()
        store = self.e.Store(path)
        with self.assertRaises(self.e.WorkflowError):
            store.update(lambda state: state['tasks'][0].update(status='COMPLETED'), self.root)
        self.assertEqual(before, path.read_bytes())
        store.update(lambda state: self.e.transition(state, 'TASK-001', 'READY', 'INTAKE', 'orchestrator', self.root), self.root)
        self.assertEqual(store.load()['revision'], 1)
        self.assertEqual(store.load()['tasks'][0]['status'], 'READY')

    def test_04_parallel_workspace_collision_rejected(self):
        self.state['tasks'].append(self.e.new_task('TASK-002', 'independent'))
        (self.root / 'workflow').mkdir(exist_ok=True)
        (self.root / 'workflow/probe.txt').write_text('SIMULATION probe')
        self.state['capabilities'].update(mode='parallel', independent_sessions=True,
                                          probe=self.e.artifact(self.root, 'workflow/probe.txt'))
        self.state['policy']['max_parallel'] = 2
        self.e.claim(self.state, 'TASK-001', 'session-a', self.root, self.root)
        self.state['tasks'][1]['workspace'] = str(self.root)
        with self.assertRaises(self.e.WorkflowError):
            self.e.claim(self.state, 'TASK-002', 'session-b', self.root, self.root)

    def test_tdd_red_success_is_rejected(self):
        self.advance_to_review()
        self.task['tdd'][0]['red'] = self.e.run_evidence(self.root, [sys.executable, '-c', 'print("pass")'],
                                                        'matt', 'session-matt', ['AC-REQ-001-01'])
        with self.assertRaisesRegex(self.e.WorkflowError, 'RED must fail'):
            self.e.implementation_gate(self.task, self.root)

    def test_real_atomic_store_concurrent_writers(self):
        import concurrent.futures
        import yaml
        self.state['tasks'].append(self.e.new_task('TASK-002', 'independent'))
        path = self.root / 'workflow/current-task.yaml'
        path.parent.mkdir(exist_ok=True)
        path.write_text(yaml.safe_dump(self.state))
        def update(task_id):
            self.e.Store(path).update(lambda state: self.e.transition(state, task_id, 'READY', 'INTAKE',
                                                                      'orchestrator', self.root), self.root)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(update, ['TASK-001', 'TASK-002']))
        final = self.e.Store(path).load()
        self.assertEqual(final['revision'], 2)
        self.assertTrue(all(t['status'] == 'READY' for t in final['tasks']))

    def test_real_git_worktrees_support_distinct_claims(self):
        """Real worktree isolation; session identities/probe remain simulation."""
        area = tempfile.TemporaryDirectory()
        self.addCleanup(area.cleanup)
        first, second = Path(area.name) / 'a', Path(area.name) / 'b'
        self.git('worktree', 'add', '--detach', str(first), 'HEAD')
        self.git('worktree', 'add', '--detach', str(second), 'HEAD')
        self.state['tasks'].append(self.e.new_task('TASK-002', 'independent'))
        (self.root / 'workflow').mkdir(exist_ok=True)
        (self.root / 'workflow/probe.txt').write_text('SIMULATED independent sessions; real worktrees')
        self.state['capabilities'].update(mode='parallel', independent_sessions=True,
                                          probe=self.e.artifact(self.root, 'workflow/probe.txt'))
        self.state['policy']['max_parallel'] = 2
        self.e.claim(self.state, 'TASK-001', 'session-a', first, self.root)
        self.e.claim(self.state, 'TASK-002', 'session-b', second, self.root)
        self.e.validate(self.state, self.root)
        self.assertEqual(len([t for t in self.state['tasks'] if t['lease']]), 2)
        self.assertNotEqual(self.state['tasks'][0]['workspace'], self.state['tasks'][1]['workspace'])

    def test_completed_task_does_not_block_future_queue_after_code_changes(self):
        self.advance_to_review()
        self.finish()
        old_snapshot = copy.deepcopy(self.task['completed_snapshot'])
        (self.root / 'code.txt').write_text('next task changes code')
        self.state['tasks'].append(self.e.new_task('TASK-002', 'next task'))
        self.e.validate(self.state, self.root)
        self.assertEqual(self.e.ready(self.state, self.root), ['TASK-002'])
        self.assertEqual(self.task['completed_snapshot'], old_snapshot)
        with self.assertRaises(self.e.WorkflowError):
            self.e.validate(self.state, self.root, delivery=True)

    def test_real_store_recovers_expired_lease_with_missing_design(self):
        import yaml
        self.advance_to_review()
        self.task['checkpoint'] = {'last_safe_step': 'review checkpoint'}
        self.task['lease']['expires_at'] = 10
        path = self.root / 'workflow/current-task.yaml'
        path.write_text(yaml.safe_dump(self.state))
        (self.root / 'workflow/design.md').unlink()
        store = self.e.Store(path)
        store.update(lambda state: self.e.recover(state, now=20), self.root)
        recovered = store.load()['tasks'][0]
        self.assertEqual(recovered['status'], 'BLOCKED')
        self.assertIsNone(recovered['lease'])
        self.assertEqual(recovered['checkpoint']['last_safe_step'], 'review checkpoint')
        self.assertIn('expired lease', recovered['failure']['reason'])

    def test_real_store_recovers_lost_workspace(self):
        import yaml
        self.e.claim(self.state, 'TASK-001', 'session-a', self.root, self.root)
        self.task['workspace'] = str(self.root / 'missing-workspace')
        path = self.root / 'workflow/current-task.yaml'
        path.parent.mkdir(exist_ok=True)
        path.write_text(yaml.safe_dump(self.state))
        store = self.e.Store(path)
        store.update(lambda state: self.e.recover(state), self.root)
        self.assertEqual(store.load()['tasks'][0]['status'], 'BLOCKED')

    def test_cancel_with_stale_evidence_is_persistable(self):
        self.advance_to_review()
        (self.root / 'workflow/design.md').write_text('changed without reapproval')
        self.e.transition(self.state, 'TASK-001', 'CANCELLED', 'CODE_REVIEW', 'orchestrator', self.root)
        self.e.validate(self.state, self.root)
        self.assertEqual(self.task['status'], 'CANCELLED')

    def test_lease_heartbeat_rejects_other_session_and_saves_checkpoint(self):
        self.e.claim(self.state, 'TASK-001', 'session-a', self.root, self.root, now=100, ttl=30)
        with self.assertRaises(self.e.WorkflowError):
            self.e.heartbeat(self.state, 'TASK-001', 'session-b', {}, now=110)
        self.e.heartbeat(self.state, 'TASK-001', 'session-a', {'safe': 'test-red'}, now=110, ttl=60)
        self.assertEqual(self.task['lease']['expires_at'], 170)
        self.assertEqual(self.task['checkpoint'], {'safe': 'test-red'})

    def test_dynamic_risk_escalation_revokes_authorization(self):
        self.advance_to_review()
        self.e.escalate(self.state, 'TASK-001', 4, 'production authentication impact discovered')
        self.assertEqual(self.task['risk_level'], 4)
        self.assertEqual(self.task['authorization'], {})
        self.assertEqual(self.task['status'], 'BLOCKED')
        self.e.validate(self.state, self.root)

    def test_integration_failure_creates_traceable_repair_task(self):
        self.prepare_plan()
        self.e.claim(self.state, 'TASK-001', 'session-a', self.root, self.root)
        for stage in ['REQUIREMENTS', 'DESIGN', 'FEASIBILITY', 'PLANNING', 'APPROVAL', 'IMPLEMENTATION', 'INTEGRATION']:
            self.e.transition(self.state, 'TASK-001', 'RUNNING', stage, 'orchestrator', self.root)
        repair = self.e.integration_failure(self.state, 'TASK-001', 'SIMULATED API merge conflict')
        self.assertEqual(repair['parent_task_id'], 'TASK-001')
        self.assertEqual(repair['requirement_ids'], ['REQ-001'])
        self.assertEqual(self.task['status'], 'BLOCKED')
        self.e.validate(self.state, self.root)
        self.assertIn(repair['task_id'], self.e.ready(self.state, self.root))

    def test_operation_uncertainty_survives_real_store_recovery(self):
        import yaml
        self.e.claim(self.state, 'TASK-001', 'session-a', self.root, self.root, now=100, ttl=1)
        self.e.operation(self.state, 'TASK-001', 'irreversible-001', idempotent=False)
        path = self.root / 'workflow/current-task.yaml'
        path.parent.mkdir(exist_ok=True)
        path.write_text(yaml.safe_dump(self.state))
        store = self.e.Store(path)
        store.update(lambda state: self.e.recover(state, now=102), self.root)
        recovered = store.load()
        with self.assertRaisesRegex(self.e.WorkflowError, 'non-idempotent'):
            self.e.operation(recovered, 'TASK-001', 'irreversible-001', idempotent=False)

    def test_running_transition_requires_claim_lease(self):
        self.e.transition(self.state, 'TASK-001', 'READY', 'INTAKE', 'orchestrator', self.root)
        with self.assertRaisesRegex(self.e.WorkflowError, 'lease'):
            self.e.transition(self.state, 'TASK-001', 'RUNNING', 'INTAKE', 'orchestrator', self.root)

    def test_running_transition_cannot_bypass_incomplete_dependency(self):
        import time
        dependent = self.e.new_task('TASK-002', 'dependent')
        dependent['dependencies'] = ['TASK-001']
        self.state['tasks'].append(dependent)
        self.e.transition(self.state, 'TASK-002', 'READY', 'INTAKE', 'orchestrator', self.root)
        dependent['lease'] = {'session': 'SIMULATED session', 'expires_at': time.time() + 300}
        dependent['workspace'] = str(self.root)
        dependent['assigned_agent'] = 'SIMULATED session'
        with self.assertRaisesRegex(self.e.WorkflowError, 'dependenc'):
            self.e.transition(self.state, 'TASK-002', 'RUNNING', 'INTAKE', 'orchestrator', self.root)

    def test_real_snapshot_changes_for_uncommitted_code(self):
        before = self.e.snapshot(self.root)
        (self.root / 'code.txt').write_text('changed\n')
        after = self.e.snapshot(self.root)
        self.assertEqual(before['sha'], after['sha'])
        self.assertNotEqual(before['tree'], after['tree'])

    def test_real_command_failure_cannot_be_recorded_as_pass(self):
        evidence = self.e.run_evidence(self.root, [sys.executable, '-c', 'import sys; sys.exit(7)'],
                                       'tester', 'tester-session', ['AC-001'])
        self.assertEqual(evidence['exit_code'], 7)

    def test_real_command_evidence_binds_git_revision(self):
        evidence = self.e.run_evidence(self.root, [sys.executable, '-c', "print('verified')"],
                                       'tester', 'tester-session', ['AC-001'])
        self.assertEqual(evidence['exit_code'], 0)
        self.assertIn(self.git('rev-parse', 'HEAD'), str(evidence))


if __name__ == '__main__':
    unittest.main()
