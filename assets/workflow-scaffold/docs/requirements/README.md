# Requirements

PRD files live here as `TASK-YYYYMMDD-NNN-prd.md`.

Each PRD must include numbered requirements, Given/When/Then acceptance criteria, normal scenarios, exception scenarios, boundary scenarios, permission rules, assumptions, and non-goals.

Separate confirmed decisions, facts, proposals, assumptions, and open questions. Record each question's owner and blocking REQ scope. Draft expectations remain conditional and not_run; prioritize decision questions and key scenarios before expanding a full matrix.

Before formal DESIGN, register requirements_baseline through Store.update: status=confirmed, version, document={path,sha256}, requirements snapshot, acceptance_ids, confirmation={actor,timestamp,source:{path,sha256},document_sha256,baseline_sha256}. Compute baseline_sha256 with requirements_digest(task), which binds version, PRD and REQ/AC scope. Reuse valid existing confirmation; never infer whole-document approval from one decision. See [the contract](../workflow-contract.md) and [precheck template](../../workflow/templates/precheck-template.md).

