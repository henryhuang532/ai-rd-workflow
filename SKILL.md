---
name: ai-rd-workflow
description: Use when a user asks Codex to initialize, standardize, or run a repository R&D workflow with multi-agent meetings, Superpowers design and planning, Matt implement TDD delivery and code review, tester validation, stage gates, defect repair loops, AGENTS.md, workflow state, or file-based handoffs.
---

# AI 研发流程

## Core Rule

把研发过程组织成由 Orchestrator 主持的多 agent 会议。会议中的每个角色必须有独立上下文、明确产物和可追溯发言；角色之间通过仓库文件和 Orchestrator 交接，不能用复制聊天内容代替交接。

本技能采用固定分工：

- **Superpowers 席**负责需求澄清后的方案推导、design、plan、公共测试接口（seams）和设计自检。
- **Matt implement 席**负责读取已批准的 design/plan，按 TDD 实施、运行实现侧验证，并执行 Standards/Spec 两轴代码评审。
- **Tester 席**独立依据 PRD、批准的验收标准和实际代码验证功能；不把 Matt 的实现报告当作测试证据。
- **Product 席**补充业务目标、规则、优先级和验收语义；不写实现代码。
- **Orchestrator 席**主持会议、准备议程、汇总发言、审查产物、推进状态、路由缺陷和输出报告；不替代任何专家完成其应交付的产物。

“Superpowers 负责设计，Matt 负责实现”是硬边界。不得把含糊的 Developer Agent 作为默认实现者，也不得在批准前调用实现技能、写业务代码或写实现测试。

## Use This Workflow

1. **先看真实仓库状态**：使用 `git rev-parse --show-toplevel`、`rg --files`、`git status --short`、`git log -1 --oneline`，读取 `AGENTS.md`、README、领域文档、设计/测试目录、构建文件、CI 和现有工作流。记录当前分支、实施前基准 SHA、已有 staged/unstaged 改动、可用命令和已知环境限制。
2. **建立会议封套**：为任务生成稳定 `task_id` 和 `meeting_id`，在 `workflow/current-task.yaml` 写入原始需求、参与者、基线 SHA、已有改动、允许/禁止路径、目标状态和待确认问题。
3. **召开启动会（KICKOFF_MEETING）**：Orchestrator 让 Product、Superpowers、Matt、Tester 分别独立发言。会议记录必须区分事实、建议、风险、假设和需要用户决定的事项；Orchestrator 负责合并，不让一个角色替其他角色拍板。
4. **由 Superpowers 产出 design 与 plan**：先做候选方案和取舍，再写可独立阅读的 design；设计获准后再写逐任务 plan。设计和计划要指定真实文件路径、公共 seams、行为验收、测试命令、预期证据和非目标。未获批准时只能写文档，不能实施。
5. **召开设计/计划评审会**：Product 检查业务覆盖，Matt 检查可实现性和 seams，Tester 检查可验证性，Orchestrator 检查范围、接口、状态和风险。任何实质性争议必须形成决议；不能把“看起来合理”当作批准。
6. **记录明确批准门**：批准绑定 design/plan 的版本、SHA-256、来源和时间。可接受来源包括已授权的 Gitee 评审结论或用户在聊天中的明确确认；issue 关闭、标签或沉默不算批准。批准前不调用 Matt implement。
7. **交给 Matt implement 席实施**：交接包必须包含批准版路径和哈希、批准依据、确认的 seams、PRD 映射、任务顺序、基线 SHA、已有改动、允许/禁止路径、真实命令、环境限制、回滚边界和预期证据路径。Matt 每个行为遵循 `RED → GREEN → REFACTOR`：先写一个能证明目标行为的测试并确认按预期失败，再写最小实现，最后保持全套测试通过后重构。
8. **由 Matt 完成实现侧验证和代码评审**：运行受影响测试、类型检查、构建以及项目完整测试一次；失败要记录原始命令、输出摘要、原因和未验证范围。代码评审必须覆盖实施前基线 SHA 到当前状态的已提交、未提交和新增文件，并分别输出 Standards 与 Spec 结果、严重级别、行号、修复和复测证据。无差异时也要记录实际 diff 检查，不能声称已完成评审而不提供范围证据。
9. **召开功能测试会**：Tester 依据 PRD 和批准的验收标准独立执行功能、回归、权限、边界和异常用例，保存命令/日志/截图等证据。发现问题时创建结构化 bug 文件，包含条款、复现步骤、实际结果、期望结果、环境和证据链接。
10. **处理缺陷会议和回归**：Orchestrator 将同一个 bug 包交回原 Matt implement 会话；先补失败回归测试，再修复、运行实现侧验证，交回 Tester 回归。若公共接口、数据模型、验收标准或业务规则改变，必须回到 Superpowers design/plan 评审；实现细节修复无需重新批准。连续修复失败或外部依赖不可用时进入 `BLOCKED`/`NEEDS_USER_INPUT`，写明事实和重试次数。
11. **验收和交付**：只有 Tester 证据、Matt 实现/评审证据、Orchestrator 状态和批准记录都齐全，才能进入 `ACCEPTANCE`/`DONE`。最终报告区分已完成、已验证、未验证、失败、阻塞和建议下一步，不把局部通过写成全仓通过。

## 会议协议与角色边界

每次会议记录至少包含：`meeting_id`、`task_id`、阶段、参与者及其独立会话、输入文件版本、每席发言、异议、决议、行动项、输出路径和下一门禁。Orchestrator 必须先发议程和上下文，再收集独立发言，最后发布决议；不得让多个角色共用一个上下文后把单 agent 顺序执行称为会议。

| 角色 | 允许产物 | 明确禁止 |
| --- | --- | --- |
| Product | 目标、PRD、验收语义、优先级 | 业务代码、实现细节拍板 |
| Superpowers | 候选方案、design、plan、公共 seams、设计自检 | 业务代码、实现测试、绕过批准 |
| Matt implement | TDD 测试与实现、验证记录、双轴 code-review、修复 | 修改 PRD 消除失败、扩大范围、绕过 TDD |
| Tester | 测试用例、独立执行证据、bug/回归报告 | 以实现报告代替执行、修改业务代码 |
| Orchestrator | 会议纪要、状态、交接包、门禁决议、交付报告 | 代写专家产物、隐式批准、替专家实现 |

## Files To Establish

使用仓库已有等价目录，避免重复创建。至少建立：

```text
AGENTS.md
.agents/orchestrator.md
.agents/product.md
.agents/superpowers-designer.md
.agents/matt-implementer.md
.agents/tester.md
workflow/current-task.yaml
workflow/templates/task-template.yaml
workflow/history/
workflow/meetings/
docs/requirements/
docs/superpowers/specs/
docs/superpowers/plans/
docs/test-cases/
docs/bugs/
docs/reports/
scripts/workflow_check.py
scripts/verify.sh
```

如果仓库仍使用 `.agents/developer.md`，可以保留兼容入口，但其内容必须明确转发到 Matt implement 席，不能重新定义一个独立 Developer 流程。创建或审查这些文件时读取 `references/workflow-file-contract.md`。

## 状态机

标准路径：

```text
REQUIREMENT_INPUT -> KICKOFF_MEETING -> SUPERPOWERS_DESIGN -> DESIGN_REVIEW_MEETING
-> PLAN_REVIEW_MEETING -> APPROVAL_GATE -> MATT_IMPLEMENT_TDD -> MATT_UNIT_TEST
-> MATT_CODE_REVIEW -> FUNCTIONAL_TEST -> ACCEPTANCE -> DONE
```

缺陷路径：

```text
FUNCTIONAL_TEST -> BUG_REVIEW_MEETING -> MATT_BUG_FIX_TDD -> MATT_UNIT_TEST
-> MATT_CODE_REVIEW -> FUNCTIONAL_TEST
```

异常状态：`NEEDS_USER_INPUT`、`BLOCKED`、`CANCELLED`。

`workflow/current-task.yaml` 至少记录：

```yaml
task_id: <stable-id>
meeting_id: <current-meeting-id>
state: <state>
participants: [orchestrator, product, superpowers, matt, tester]
baseline_sha: <sha-or-null>
existing_changes: {staged: [], unstaged: []}
artifacts:
  design: {path: <path>, sha256: <hash>, version: <version>, approved: false}
  plan: {path: <path>, sha256: <hash>, version: <version>, approved: false}
handoff:
  seams: []
  acceptance_mapping: []
  allowed_paths: []
  forbidden_paths: []
  commands: []
  evidence_paths: []
approval: {source: null, timestamp: null, decision: pending}
sessions: {superpowers: null, matt: null, tester: null}
review: {standards: [], spec: [], status: pending}
retry_count: {product: 0, superpowers: 0, matt: 0, tester: 0}
limitations: []
```

## 设计、实现和验证细则

### Superpowers 设计席

读取仓库规则和相关领域文档，提出有实际差异的候选方案及取舍，推荐一个方案，写入 `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`；设计获批后写入 `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`。计划按可独立验收的纵向切片组织，每步列出真实路径、公共 seam、关键测试代码、执行命令、预期结果和验收映射。不要把推测路径写成既有事实。若采用 Gitee 评审，记录 issue/评论链接、内容哈希、发布时间和明确批准结论。

### Matt implement 席

读取 `.agents/skills/implement/SKILL.md` 及其 TDD/code-review 依赖；若依赖缺失，记录 `current_missing` 或 `BLOCKED`，不得伪造调用。按批准 plan 的顺序开发；公共 seam 的行为变化必须先有失败测试。每个行为保存失败命令、失败原因、最小实现、通过命令和验收映射。实现完成后按仓库真实配置运行完整测试一次；环境阻塞要原样记录。Matt 不修改 design/plan 的业务约定来掩盖失败。

### Tester 席

测试用例来自 PRD 和批准版验收标准，而非 Matt 的自评。至少覆盖正常、异常、边界、权限/可见性和回归场景中与任务相关的部分。测试证据必须包含实际命令和结果；不能只写“已验证”。

## Subagent Dispatch 与限流

有 subagent 工具时必须为每个席位使用独立会话。设计会可并行收集 Product、Superpowers、Matt、Tester 的独立意见，但涉及同一文件的实施、修复和状态变更必须由 Orchestrator 串行协调。Orchestrator 审阅每席产物后再推进门禁。

把 `429`、rate-limit、quota-exhausted、capacity-unavailable、slot-unavailable 视为同一 `role + stage + task` 的暂时失败：

- 不创建等价替代 agent，不重复发送并行提示。
- 在当前 Orchestrator 会话中按有界退避重试，保留原 prompt、文件路径、task 状态和已有会话句柄；有 `Retry-After` 时遵守它。
- 已创建的会话用 follow-up 恢复；创建被拒且没有句柄时，按严格角色标签在当前会话顺序执行并记录限制。
- 有界重试仍失败则进入 `BLOCKED` 或 `NEEDS_USER_INPUT`，写明真实错误和次数；不要无限循环。
- 只有任务含义实质变化或原会话确认不可恢复时才允许新 agent，并在状态中记录原因。

没有 subagent 工具时，不能把单 agent 自言自语称为多 agent 会议。应在 `workflow/current-task.yaml` 记录 `subagents: unavailable`，用分隔的角色文件、独立产物和显式门禁顺序执行，并把该限制写入报告。

## 用户入口与提问边界

未来需求只能由 Orchestrator 作为用户入口接收。角色 handoff 通过仓库文件和 Orchestrator 派发，不要求用户在 agent 之间转发消息。只在不可从代码、文档或已确认上下文解决，且会改变行为或验收的重大问题上询问用户：不可逆删除、金额/计费、权限/安全、不兼容行为、外部凭据/数据、与用户改动冲突或反复修复失败。其余选择写成带理由的设计决定或明确假设。

## Verification

完成前总是运行新鲜验证：

```bash
python3 scripts/workflow_check.py --stage schema
bash scripts/verify.sh
```

如果项目有构建文件，`verify.sh` 必须执行该项目真实的 lint、类型检查、测试或构建命令。能力缺失标记为 `not_applicable` 或 `current_missing`；不能编造命令或结果。技能文件自身变更后，至少运行 YAML/Markdown 结构检查、关键术语检索和 diff 检查，确认“Superpowers=design/plan”“Matt=implementation/review”“approval gate”“TDD red→green”均可检索。

## Common Mistakes

- 没有先读取仓库，就创建一套通用角色文件。
- 把单 agent 顺序执行称为多 agent 会议。
- 让 Superpowers 写业务代码，或让 Matt 在批准前实现。
- 把“Developer Agent”当成与 Matt 并列的默认实现者，造成责任漂移。
- 用聊天中的模糊同意、issue 关闭或标签代替可识别版本的批准。
- 没有保存 design/plan 的哈希、基线 SHA、dirty 状态和公共 seams。
- 只运行 Matt 的聚焦测试，就声称完整验证通过。
- Tester 直接采信实现报告，或为了让测试通过修改业务规则。
- code-review 只看 `HEAD` diff，漏掉未提交和新增文件。
- 缺陷通过修改 PRD 或删除验收标准来“修复”。
- `429` 后创建同角色同阶段的重复 agent，或无限重试。
- 把实现细节变化误当作需要重新批准，或把公共接口/验收变化当作无需回设计。
