---
name: ai-rd-workflow
description: Use when initializing, reviewing, or running repository R&D workflows with risk-based authorization, Superpowers design, Matt TDD implementation, independent review and QA, task DAGs, evidence gates, or recovery using existing Codex execution capabilities.
---

# AI 研发工作流 v2

以任务、依赖和风险决定流程。Orchestrator 调度，Product 定义验收，Architect 使用 Superpowers 设计，Matt 使用 TDD 实现，Reviewer 独立评审，Tester 独立验证。文件交接和真实执行证据驱动门禁；会议只解决实际分歧。不得伪造角色发言、审批、测试或日志。

## 启动与能力检测

1. 读取仓库 `AGENTS.md`、代码/构建/CI、全部现有工作流文件；检查 `git status --short`、基准 SHA、dirty/untracked 文件。保护用户现有改动，不擅自初始化 Git、提交、推送或部署。
2. 读取 [统一契约](references/workflow-file-contract.md)。初始化使用 `assets/workflow-scaffold/`；合并已有文件，禁止覆盖用户规则。脚本命令从目标仓库根目录运行。
3. 检查当前真实工具：独立 Agent/会话、会话恢复、Git Worktree、命令执行、测试环境、Superpowers 和 Matt implement 技能。读取实际安装的技能，不把名称当作成功调用。探测只用只读或可逆操作，记录工具名、结果、时间、执行环境限制。
4. 默认 `capabilities.mode: serial`；只有存在多个真实独立执行会话、隔离工作区和可用并发槽位才能启用真实并行。DAG 中存在多个 READY 任务只是逻辑并行。无独立会话时允许串行准备/实现；独立 Reviewer/Tester 无法取得时最终门禁 BLOCKED，不用同一 Agent 换角色标签冒充独立验证。
5. 建立 v2 任务队列 `workflow/current-task.yaml`。记录稳定 ID、需求、范围、授权来源、风险理由、依赖、工作区、产物和检查点。现有 v1 按 [迁移指南](references/migration-v2.md) 迁移，不自动继承通过结论。

## 风险路由

评估数据敏感性、权限、外部影响、不可逆性、依赖、复杂度与回滚能力；不能以代码行数判断。实施前、集成时和范围变化后重新评估。

| 等级 | 示例与推荐路径 | 授权及协作 |
| --- | --- | --- |
| LEVEL 1 | 简单 Bug/文案/局部非关键配置：定位→最小设计与可行性→TDD→Review→针对性 QA | 记录已有预授权范围；默认无会议，必要质量检查始终保留 |
| LEVEL 2 | 常规功能/API：需求→轻量设计→可行性→计划→风险门禁→开发→集成→Review→QA | 范围内自动推进；独立任务按 DAG 调度 |
| LEVEL 3 | 跨模块/核心架构/重大重构：需求→按议题多 Agent 讨论→Superpowers Design→Spike/可行性→Plan→设计评审→审批→开发→集成→Review→专项 QA→验收 | 保存分歧、ADR、接口、依赖、明确人工设计审批及回滚；已有有效人工版本授权可复用 |
| LEVEL 4 | 生产迁移、认证权限、重要数据删除、不可逆/付费操作、生产部署/敏感基础设施 | 实际高风险操作前必须明确人工授权，绑定范围与设计/计划哈希；技术投票无效 |

升级立即停止受影响操作、失效相关授权/证据并重走门禁，其余独立任务继续。预授权必须来自真实用户或组织政策，记录主体、范围、期限、限制和来源；Agent 不能自行创建用户授权。

## 专业角色与交接

读取 scaffold 中对应 `.agents/*.md`。Orchestrator 不代替专业结论，不覆盖拒绝意见。Architect 保留 Superpowers 候选方案、取舍、设计、计划、公共 seams 和设计自检方法；低风险缩减篇幅，不删安全分析。重大不确定性创建隔离、有时间与范围上限的 Spike，不直接改生产业务代码。

Matt 读取实际可用的 implement/TDD 技能，按授权计划 `RED → GREEN → REFACTOR`；保存失败原因及真实命令，再实现最小改动。Matt-A/B/C 每实例独立工作区、分支、任务所有权。Matt 可自检，但最终 Standards Review 和 Specification Review 必须来自独立 Reviewer。Tester 从 PRD/验收标准独立执行，不能引用 Matt 的成功说明替代测试。

每次交接包含 task/requirement IDs、阶段、真实会话 ID、基准/当前版本、输入及哈希、允许/禁止路径、接口契约、命令、完成条件、授权、重试次数、输出路径。会话不在时保留交接包，不编造会话。

## 执行闭环

1. Product 为每项需求分配 REQ ID、每项验收分配 AC ID，写可验证的 Given/When/Then、业务/权限/异常边界、非目标和假设。重大歧义才询问用户。
2. Architect 输出版本化设计与 ADR、接口/数据模型、任务 DAG、依赖及文件资源所有权、测试策略和回滚。Feasibility Check 真实检查依赖、栈兼容、关键接口、迁移必要性、测试环境、边界和未决假设；失败返回设计，不能直接宣布计划可执行。
3. Orchestrator 检查预授权或显式人工审批。审批绑定 design/plan SHA-256、动作、环境、主体、来源、时间；沉默、issue 关闭和 Agent 投票均无效。
4. 仅调度前置任务完成、租约/资源无冲突且门禁满足的任务。真实并发受 `max_parallel` 和执行器槽位共同限制；同一工作区禁止并发写入。没有后台服务时只运行当前前台可完成批次，退出前保存检查点；后续重新调用恢复。
5. Matt 实现并记录 TDD/构建证据。Integration 按拓扑整合分支、检查契约、构建及集成测试；冲突创建可追踪修复任务，禁止把失败标记完成。
6. Reviewer 针对明确 Git SHA 和完整 dirty/untracked 范围分别给出 Standards/Specification 结论、问题位置/级别/建议/阻塞性及复审。拒绝必须修复或通过有权主体处理，Orchestrator 无权抹去。
7. Tester 独立执行验收、边界、异常、集成与受影响回归；每 AC 绑定 test case 和真实证据。失败创建 bug，分类路由后 TDD 修复→独立复审→回归。
8. 最终以 Requirement→Design Decision→Task→Git Change→Test Case→Evidence 追踪验收。版本变化分析失效影响；无法证明不受影响时重新 Review/QA。COMPLETED 只能由验证器检查真实产物、版本、授权、独立结论、测试和阻塞缺陷后写入。

## 按需讨论、缺陷与恢复

只在重大需求歧义、方案/验收冲突、跨角色 ADR、多次修复失败或重大风险复核时讨论。按议题选人，依次记录方案→独立意见→反驳与证据→修订→决策；默认最多 3 轮。没有可验证结论则 BLOCKED/升级，不伪造发言。

缺陷分类和租约恢复、429/容量不足/超时/上下文耗尽/中断/工作区丢失/合并冲突/环境故障处理见统一契约。重试有上限、指数退避并遵守 Retry-After；复用真实可恢复会话，不创建同义任务绕过限额。非幂等操作结果不明时人工核对，不自动重放。重试耗尽不能自动通过或重构架构。

## 验证与真实性边界

```bash
python3 scripts/workflow_check.py --stage schema
bash scripts/verify.sh
```

按项目实际配置补运行构建、lint、类型检查和测试，记录命令/退出码/版本/日志。区分真实执行、模拟状态机测试和未验证能力。脚本是现有 Codex 的文件门禁辅助工具，不是独立 Agent 管理平台，不假设常驻服务。

本地同权限文件、哈希、会话字符串不是可信身份或签名；验证器可以阻止结构错误、过期证据和普通字段伪造，不能抵抗控制脚本及所有证据的恶意主体。高风险授权来源和独立角色身份必须由当前可信会话/已有执行环境核实；若无法核实则阻塞，不声称防伪安全已实现。
