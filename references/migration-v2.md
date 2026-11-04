# v2 更新与迁移

## 现状评审与保留

旧入口 SKILL 描述固定全员会议和统一审批；scaffold 却使用另一套 PRODUCT_DESIGN/DEVELOPMENT 状态，未生成 Superpowers/Matt 角色，且把示例 Maven 项目和日期/环境当成通用事实。旧 Matt 自评兼作独立评审。保留文件交接、Superpowers 候选方案/设计/计划/seams、Matt TDD、独立 Tester、版本化审批、真实命令和有限重试；删除这些强制串行会议及示例项目假设。

选择增强现有 Skill + 本地文件门禁辅助脚本，而非独立管理平台；只写文档无法约束状态，开发常驻管理平台又超出本次范围。v2 增加风险路由、独立 Reviewer、任务 DAG、可行性检查、证据快照及恢复 API。

## 迁移步骤

1. 备份旧 workflow/、角色和相关证据，保留原历史，不覆盖用户业务改动；暂停旧 writer。
2. 读取目标仓库实际 AGENTS/构建/CI，删除示例 Maven/非Git/子Agent可用等未经检测假设。记录真实基准 SHA、dirty/untracked、工具能力和授权。
3. 初始化空队列使用 scaffold `workflow/current-task.yaml`；单任务完整字段复制 `workflow/templates/task-template.yaml`，不要直接把单任务模板作为队列。也可 import `new_state/new_task` 后通过 Store.update 添加任务。所有后续状态变更经引擎，不能手改 status。
4. 原 task_id 保留；填 requirement_ids、AC、parent/dependencies、风险与依据、workspace/branch、角色/session、设计/计划哈希。原 history 归档，不伪造 v2 门禁历史。
5. 旧状态映射仅供确定恢复阶段：REQUIREMENT_INPUT→INTAKE；PRODUCT_DESIGN/PRODUCT_REVIEW→REQUIREMENTS；SUPERPOWERS_DESIGN/TECHNICAL_DESIGN→DESIGN；PLAN_REVIEW_MEETING→PLANNING；APPROVAL_GATE→APPROVAL；DEVELOPMENT/MATT_IMPLEMENT_TDD/MATT_UNIT_TEST/UNIT_TEST→IMPLEMENTATION；MATT_CODE_REVIEW→CODE_REVIEW；FUNCTIONAL_TEST→QA；BUG_FIX/MATT_BUG_FIX_TDD→FIX；ACCEPTANCE/DONE→DELIVERY。REVIEWING/TESTING/FIXING 分别映射 RUNNING+CODE_REVIEW/QA/FIX。旧会议不是强制新阶段；NEEDS_USER_INPUT→BLOCKED（或真实等待审批时 WAITING_APPROVAL）。
6. 为防继承无证据完成，迁移任务从 PENDING/INTAKE 重新经合法转移重验现有产物；符合新规范的真实证据可核实后引用。旧 DONE 不自动映射 COMPLETED，旧 Matt 自评不作为独立 Review，旧审批只有内容/范围/来源仍有效才可复用，L3/L4 必须明确 human 授权。
7. 登记项目真实命令，再运行 `python3 scripts/workflow_check.py --stage schema` 与 `bash scripts/verify.sh`。执行中任务先核对租约/进程/工作区、未知非幂等操作结果，保留 checkpoint 后恢复。

## 文件变化

- 重写：SKILL.md、references/workflow-file-contract.md、agents/openai.yaml；scaffold AGENTS、已有角色/说明、队列/任务模板、workflow_check.py、verify.sh。
- 新增：workflow_engine.py、自动化 tests、Superpowers/Matt/Reviewer/Integration 角色、docs/workflow-contract.md、设计/计划/审批/Review/QA/缺陷/会议/实现/交付模板、本迁移指南。
- 弃用：developer.md 保留为转发入口；旧单状态字段/固定会议/统一人工审批协议废弃；docs/designs 保留兼容，不强制搬移历史设计。没有删除历史产物。

## 运行方式与限制

`python3 scripts/workflow_engine.py --help` 查看实际 CLI。没有 init 命令：复制空队列或使用 Python new_state。ready 返回可领取集合；claim 领取；transition 经过门禁；recover 回收过期租约；run-evidence 实际运行 argv 并保存日志/receipt。所有 API 写操作由 Store.update 包裹。集成 command_evidence 必须来自真实 role=integration 命令执行；历史完成任务的 completed_snapshot 保留原版本证据，后续任务代码变化不自动废弃历史交付。状态文件排他锁依赖本地 Unix 文件系统，不承诺分布式锁或跨主机存储语义。

真实并行、独立会话身份、会话恢复和原始授权可信性由已有 Codex/执行环境提供；脚本不启动 Agent，不后台轮询或保证长期唤醒。没有独立 Reviewer/Tester 时可准备工作，但不能交付。高风险操作和外部非幂等动作需原有审批及幂等支持。哈希/receipt 可拒绝一般字段改写，不能防同权限恶意重写全部记录。测试场景的模拟与真实结果以实际验证报告为准，不能从本指南推导测试已通过。
