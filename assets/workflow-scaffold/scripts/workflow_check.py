#!/usr/bin/env python3
"""Validate the file-driven AI研发流程 state and stage gates."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "workflow" / "current-task.yaml"

ALLOWED_STATUSES = {
    "REQUIREMENT_INPUT",
    "PRODUCT_DESIGN",
    "PRODUCT_REVIEW",
    "TECHNICAL_DESIGN",
    "DEVELOPMENT",
    "UNIT_TEST",
    "FUNCTIONAL_TEST",
    "BUG_FIX",
    "ACCEPTANCE",
    "DONE",
    "BLOCKED",
    "NEEDS_USER_INPUT",
    "CANCELLED",
}

ALLOWED_OWNERS = {"orchestrator", "product", "developer", "tester", "user", "system"}

ALLOWED_GATE_STATUSES = {"not_started", "passed", "failed", "not_applicable", "blocked"}

ALLOWED_TRANSITIONS = {
    "": {"REQUIREMENT_INPUT"},
    "REQUIREMENT_INPUT": {"PRODUCT_DESIGN", "NEEDS_USER_INPUT", "BLOCKED", "CANCELLED"},
    "PRODUCT_DESIGN": {"PRODUCT_REVIEW", "NEEDS_USER_INPUT", "BLOCKED", "CANCELLED"},
    "PRODUCT_REVIEW": {"TECHNICAL_DESIGN", "PRODUCT_DESIGN", "NEEDS_USER_INPUT", "BLOCKED", "CANCELLED"},
    "TECHNICAL_DESIGN": {"DEVELOPMENT", "NEEDS_USER_INPUT", "BLOCKED", "CANCELLED"},
    "DEVELOPMENT": {"UNIT_TEST", "NEEDS_USER_INPUT", "BLOCKED", "CANCELLED"},
    "UNIT_TEST": {"FUNCTIONAL_TEST", "DEVELOPMENT", "BUG_FIX", "NEEDS_USER_INPUT", "BLOCKED", "CANCELLED"},
    "FUNCTIONAL_TEST": {"ACCEPTANCE", "BUG_FIX", "NEEDS_USER_INPUT", "BLOCKED", "CANCELLED"},
    "BUG_FIX": {"UNIT_TEST", "NEEDS_USER_INPUT", "BLOCKED", "CANCELLED"},
    "ACCEPTANCE": {"DONE", "FUNCTIONAL_TEST", "BUG_FIX", "NEEDS_USER_INPUT", "BLOCKED", "CANCELLED"},
    "DONE": set(),
    "BLOCKED": {"REQUIREMENT_INPUT", "PRODUCT_DESIGN", "TECHNICAL_DESIGN", "DEVELOPMENT", "BUG_FIX", "CANCELLED"},
    "NEEDS_USER_INPUT": {"PRODUCT_DESIGN", "TECHNICAL_DESIGN", "DEVELOPMENT", "BUG_FIX", "CANCELLED"},
    "CANCELLED": set(),
}

REQUIRED_TOP_KEYS = {
    "task_id",
    "title",
    "status",
    "current_owner",
    "input",
    "artifacts",
    "quality_gates",
    "iterations",
    "limits",
    "open_bugs",
    "blockers",
    "assumptions",
    "history",
}

REQUIRED_ARTIFACTS = {
    "prd",
    "technical_design",
    "implementation_report",
    "test_cases",
    "test_report",
    "delivery_report",
}

REQUIRED_GATES = {
    "product_review",
    "technical_review",
    "unit_test",
    "lint",
    "type_check",
    "build",
    "functional_test",
    "regression_test",
}


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:
        print("ERROR: PyYAML is required. Install with: python3 -m pip install pyyaml", file=sys.stderr)
        sys.exit(2)

    if not path.exists():
        print(f"ERROR: missing workflow state file: {path}", file=sys.stderr)
        sys.exit(1)

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        print(f"ERROR: workflow state must be a YAML mapping: {path}", file=sys.stderr)
        sys.exit(1)
    return data


def repo_path(value: str) -> Path:
    return ROOT / value


def gate_status(data: dict[str, Any], name: str) -> str:
    gate = data.get("quality_gates", {}).get(name, {})
    if isinstance(gate, dict):
        return str(gate.get("status", ""))
    return str(gate)


def artifact_path(data: dict[str, Any], name: str) -> Path | None:
    value = data.get("artifacts", {}).get(name, "")
    if not value:
        return None
    return repo_path(str(value))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_schema(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_TOP_KEYS - set(data))
    require(not missing, f"missing top-level keys: {', '.join(missing)}", errors)

    status = data.get("status")
    require(status in ALLOWED_STATUSES, f"invalid status: {status}", errors)
    require(data.get("current_owner") in ALLOWED_OWNERS, f"invalid current_owner: {data.get('current_owner')}", errors)

    artifacts = data.get("artifacts", {})
    require(isinstance(artifacts, dict), "artifacts must be a mapping", errors)
    if isinstance(artifacts, dict):
        missing_artifacts = sorted(REQUIRED_ARTIFACTS - set(artifacts))
        require(not missing_artifacts, f"missing artifact keys: {', '.join(missing_artifacts)}", errors)

    gates = data.get("quality_gates", {})
    require(isinstance(gates, dict), "quality_gates must be a mapping", errors)
    if isinstance(gates, dict):
        missing_gates = sorted(REQUIRED_GATES - set(gates))
        require(not missing_gates, f"missing quality gate keys: {', '.join(missing_gates)}", errors)
        for name, gate in gates.items():
            if isinstance(gate, dict):
                gate_value = str(gate.get("status", ""))
                require(gate_value in ALLOWED_GATE_STATUSES, f"invalid quality gate status for {name}: {gate_value}", errors)
            else:
                require(False, f"quality gate {name} must be a mapping", errors)

    for key in ("iterations", "limits"):
        require(isinstance(data.get(key), dict), f"{key} must be a mapping", errors)

    for key in ("open_bugs", "blockers", "assumptions", "history"):
        require(isinstance(data.get(key), list), f"{key} must be a list", errors)

    history = data.get("history", [])
    if isinstance(history, list):
        require(bool(history), "history must contain at least one state transition", errors)
        previous_to = None
        for index, item in enumerate(history):
            require(isinstance(item, dict), f"history[{index}] must be a mapping", errors)
            if not isinstance(item, dict):
                continue
            for key in ("from", "to", "actor", "time", "reason", "artifacts", "validation"):
                require(key in item, f"history[{index}] missing key: {key}", errors)
            from_status = str(item.get("from", ""))
            to_status = str(item.get("to", ""))
            actor = str(item.get("actor", ""))
            require(from_status in ALLOWED_TRANSITIONS, f"history[{index}] invalid from status: {from_status}", errors)
            require(to_status in ALLOWED_STATUSES, f"history[{index}] invalid to status: {to_status}", errors)
            if from_status in ALLOWED_TRANSITIONS:
                require(
                    to_status in ALLOWED_TRANSITIONS[from_status],
                    f"history[{index}] invalid transition: {from_status} -> {to_status}",
                    errors,
                )
            if previous_to is not None:
                require(from_status == previous_to, f"history[{index}] from does not match previous to status", errors)
            require(actor in ALLOWED_OWNERS, f"history[{index}] invalid actor: {actor}", errors)
            require(isinstance(item.get("artifacts"), list), f"history[{index}] artifacts must be a list", errors)
            require(isinstance(item.get("validation"), dict), f"history[{index}] validation must be a mapping", errors)
            previous_to = to_status
        if history and isinstance(history[-1], dict):
            require(history[-1].get("to") == status, "latest history.to must match current status", errors)

    return errors


def validate_product(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    prd = artifact_path(data, "prd")
    require(prd is not None and prd.exists(), "product gate failed: PRD file is missing", errors)
    require(gate_status(data, "product_review") == "passed", "product gate failed: product_review status must be passed", errors)
    if prd and prd.exists():
        text = prd.read_text(encoding="utf-8")
        require(bool(re.search(r"\bREQ-\d{3}\b", text)), "product gate failed: no requirement IDs like REQ-001", errors)
        require(bool(re.search(r"\bAC-REQ-\d{3}-\d{2}\b", text)), "product gate failed: no acceptance IDs like AC-REQ-001-01", errors)
        require("Given" in text and "When" in text and "Then" in text, "product gate failed: acceptance criteria must use Given/When/Then", errors)
        require("异常" in text or "Exception" in text, "product gate failed: exception scenarios are missing", errors)
        require("边界" in text or "Boundary" in text, "product gate failed: boundary scenarios are missing", errors)
        require("权限" in text or "Permission" in text, "product gate failed: permission rules are missing", errors)
        require("假设" in text or "Assumption" in text, "product gate failed: assumptions are missing", errors)
        require("非目标" in text or "Non-goals" in text or "Non-Goals" in text, "product gate failed: non-goals are missing", errors)
        vague = ["正常工作", "符合预期", "用户体验良好", "正确处理", "系统稳定"]
        present = [word for word in vague if word in text]
        require(not present, f"product gate failed: vague acceptance wording found: {', '.join(present)}", errors)
    return errors


def validate_development(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for name, label in (("technical_design", "technical design"), ("implementation_report", "implementation report")):
        path = artifact_path(data, name)
        require(path is not None and path.exists(), f"development gate failed: {label} is missing", errors)
    require(gate_status(data, "technical_review") == "passed", "development gate failed: technical_review status must be passed", errors)
    for gate in ("unit_test", "lint", "type_check", "build"):
        status = gate_status(data, gate)
        require(status in {"passed", "not_applicable"}, f"development gate failed: {gate} must be passed or not_applicable", errors)
    report = artifact_path(data, "implementation_report")
    if report and report.exists():
        text = report.read_text(encoding="utf-8")
        require("验收标准" in text or "Acceptance" in text, "development gate failed: acceptance mapping is missing from implementation report", errors)
        require("命令" in text or "Command" in text, "development gate failed: executed commands are missing from implementation report", errors)
    return errors


def validate_testing(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for name, label in (("test_cases", "test cases"), ("test_report", "test report")):
        path = artifact_path(data, name)
        require(path is not None and path.exists(), f"testing gate failed: {label} is missing", errors)
    for gate in ("functional_test", "regression_test"):
        require(gate_status(data, gate) == "passed", f"testing gate failed: {gate} status must be passed", errors)
    open_bugs = data.get("open_bugs", [])
    high = []
    if isinstance(open_bugs, list):
        for bug in open_bugs:
            bug_text = str(bug)
            if "P0" in bug_text or "P1" in bug_text:
                high.append(bug_text)
    require(not high, f"testing gate failed: open P0/P1 bugs exist: {', '.join(high)}", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=["schema", "product", "development", "testing", "done"],
        default="schema",
        help="Gate level to validate.",
    )
    args = parser.parse_args()

    data = load_yaml(STATE_FILE)
    errors = validate_schema(data)
    if args.stage in {"product", "development", "testing", "done"}:
        errors.extend(validate_product(data))
    if args.stage in {"development", "testing", "done"}:
        errors.extend(validate_development(data))
    if args.stage in {"testing", "done"}:
        errors.extend(validate_testing(data))
    if args.stage == "done":
        require(data.get("status") == "DONE", "done gate failed: status must be DONE", errors)
        delivery = artifact_path(data, "delivery_report")
        require(delivery is not None and delivery.exists(), "done gate failed: delivery report is missing", errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"workflow_check: {args.stage} gate passed for {STATE_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
