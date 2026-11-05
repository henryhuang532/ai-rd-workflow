# <task_id> 独立 QA

kind: qa_execution（当前版本独立代码评审通过后执行）
requirements_sha256（requirements_digest(task)，完整已确认基线指纹）：

Tester / 真实 session：
独立性核实依据：
代码 SHA/tree、环境、依赖：
输入 PRD/Design/Plan 版本：

| TC ID | REQ/AC | 前置条件/数据 | 步骤 | 预期 | 实际 | 状态 | 命令/退出码/日志证据 |
| --- | --- | --- | --- | --- | --- | --- | --- |

## 覆盖与回归

正常、异常、边界、权限、集成和受影响回归各自的适用性/用例；所有 AC 至少一个独立测试；专项测试。

## 缺陷与限制

缺陷 ID/级别/责任/状态、未执行或阻塞项、环境问题；Matt 的执行仅作背景，不能替代此处测试。

## 结论

pending；绑定最终代码版本与实际 run-evidence 产物。明确区分真实执行、模拟状态机测试及未验证能力。

run_evidence 默认 kind=command，不自动算 QA。正式执行显式传 kind='qa_execution' 和 requirements_sha256；CLI 参数为 --kind qa_execution --requirements-sha256 <基线哈希>。需求预审、条件式用例和文档检查使用 precheck-template.md，保留 draft/not_run，不填入正式通过证据。
