# 研发协作约定 v2

先检测仓库、工具和执行能力，不复制示例项目假设。完整规范见 [workflow-contract.md](docs/workflow-contract.md)，状态只能经 `scripts/workflow_engine.py` 门禁更新。

- 状态队列：`workflow/current-task.yaml`；模板：`workflow/templates/`；角色：`.agents/`。
- 需求：`docs/requirements/`；设计/计划：`docs/superpowers/specs/`、`docs/superpowers/plans/`；兼容既有设计目录 `docs/designs/`；用例：`docs/test-cases/`；缺陷：`docs/bugs/`；实现/Review/QA/交付报告：`docs/reports/`。
- Orchestrator 负责风险、调度、门禁；Product 负责需求；Superpowers Architect 负责设计/可行性/计划；Matt 负责 TDD 实现；独立 Reviewer 双轴评审；独立 Tester 验收与回归。Integration 按需委派。
- 风险按数据/权限/外部影响/可逆性/依赖评估，L1/L2 在真实预授权范围推进，L3 设计与 L4 操作均必须明确人工授权。无默认例会。设计/计划变化重新核验授权。
- DAG 无依赖且资源隔离可并行；真实独立会话不可用则串行并记录原因，不能用角色标签冒充独立 Review/QA。
- 必要验收不可省略；失败测试、过期版本证据、缺失独立验证或未关闭 P0/P1 阻止完成。P2 必须明确处理。禁止删除/禁用/弱化测试来通过。
- 不伪造命令、日志、批准或角色发言；本地哈希不提供可信身份。无法核实高风险授权来源则 BLOCKED。

## 项目命令登记

脚手架不假设 Maven、Java 或任何业务栈。初始化时从实际构建/CI 填入安装、启动、单元/功能/回归、lint、类型检查及构建命令，记录可用/current_missing/not_applicable 及依据。缺失命令不代表通过，不自动安装服务或发起付费操作。

流程自身：`python3 scripts/workflow_check.py --stage schema`、`bash scripts/verify.sh`。Python 依赖见 `scripts/requirements.txt`。项目真实命令另按仓库 CI 执行并保存证据。
