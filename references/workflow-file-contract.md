# Workflow File Contract

## AGENTS.md

Keep this concise. It must state:

- product, design, test, report, bug, and state file locations
- role boundaries
- real install/start/test/lint/type-check/build commands
- missing capabilities marked truthfully
- no skipped states
- approved PRD controls product rules
- business code changes require tests
- failed tests block completion
- command results must be real
- P0/P1 bugs block delivery
- tests cannot be deleted, disabled, or weakened to pass

## Role Files

Each `.agents/*.md` file must include:

- role positioning
- responsibilities
- input files
- output files
- allowed modification scope
- forbidden modification scope
- work steps
- completion criteria
- failure handling
- hard rules

When subagent tools are available, `.agents/orchestrator.md` must require Product, Developer, and Tester work to run in independent subagents. The orchestrator may review, route, and update state, but must not perform specialist work in the same context.

## Product PRD Requirements

PRD must include:

- unique requirement IDs: `REQ-001`
- acceptance IDs: `AC-REQ-001-01`
- Given/When/Then criteria
- user roles
- functional and non-functional scope
- business rules
- permission rules
- normal, exception, and boundary scenarios
- assumptions
- non-goals

Reject vague acceptance wording such as: 正常工作, 符合预期, 用户体验良好, 正确处理, 系统稳定.

## Developer Deliverables

Technical design must cover:

- current-state analysis
- impact scope
- module design
- data structures
- API changes
- compatibility
- error handling
- security and permissions
- test strategy
- risks
- rollback

Implementation report must include:

- summary
- changed files
- acceptance mapping
- executed commands
- test results
- known risks
- unfinished work

Mapping format:

```text
Acceptance criterion -> modified module -> unit test -> functional test
```

## Tester Deliverables

Test cases must include:

- ID
- related requirement
- prerequisites
- test data
- steps
- expected result
- actual result
- status
- evidence

Bug files must include:

- bug ID
- title
- severity
- related requirement
- environment
- prerequisites
- reproduction steps
- actual result
- expected result
- logs/evidence
- impact scope
- recommended regression scope

## current-task.yaml Minimum Fields

```yaml
task_id:
title:
status:
current_owner:
input:
  original_requirement:
artifacts:
  prd:
  technical_design:
  implementation_report:
  test_cases:
  test_report:
  delivery_report:
quality_gates:
  product_review:
  technical_review:
  unit_test:
  lint:
  type_check:
  build:
  functional_test:
  regression_test:
iterations:
  product:
  development:
  testing:
limits:
  max_product_iterations: 2
  max_development_iterations: 3
  max_testing_iterations: 3
open_bugs: []
blockers: []
assumptions: []
history: []
```

Every status change must append history with from, to, actor, time, reason, artifacts, and validation.

## Subagent Handoff Contract

Each subagent prompt must include:

- role name
- task ID
- current workflow status
- input files
- output files
- allowed modification scope
- forbidden modification scope
- completion criteria
- review rules

The orchestrator must review the produced files before advancing state. Defect repair must spawn a Developer repair subagent and then a Tester regression subagent.
