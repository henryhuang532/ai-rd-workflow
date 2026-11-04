# AI研发流程协作规则

本仓库使用文件驱动的多角色研发流程。用户只向流程总负责人提交业务需求；产品、研发、测试角色优先由独立子智能体模拟，并通过仓库文件交接，不要求用户复制或转发 Agent 消息。

## 项目现状

- 当前目录不是 Git 仓库；不得擅自执行 `git init`、`git push` 或修改提交历史。
- 当前目录已包含 Maven 多模块项目：`oa-backend`、`oa-gateway`；已有文档位于 `docs/superpowers/`。
- 当前技术栈是 Java 21 目标、Spring Boot 3.5.x、Spring Cloud Gateway、Maven、JUnit 5、MyBatis-Plus、Flyway、MySQL 8。

## 文件位置

- 流程状态：`workflow/current-task.yaml`
- 任务模板：`workflow/templates/task-template.yaml`
- 产品 PRD：`docs/requirements/<task_id>-prd.md`
- 技术设计：`docs/designs/<task_id>-technical-design.md`
- 测试用例：`docs/test-cases/<task_id>-test-cases.md`
- 缺陷报告：`docs/bugs/<task_id>-<bug_id>.md`
- 实现报告、测试报告、交付报告：`docs/reports/`
- 角色规则：`.agents/orchestrator.md`、`.agents/product.md`、`.agents/developer.md`、`.agents/tester.md`

## 真实命令

当前项目使用 Maven。以下命令必须按实际执行结果写入对应报告：

| 能力 | 当前命令 |
| --- | --- |
| 依赖安装 | `mvn -U -DskipTests dependency:resolve` |
| 开发环境启动 | 后端：`mvn -pl oa-backend spring-boot:run`；网关：`mvn -pl oa-gateway spring-boot:run` |
| 单元测试 | `mvn test` |
| 功能测试 | 当前缺失；尚未建立独立接口功能测试框架 |
| lint | 当前缺失；未配置 Checkstyle、Spotless 或 PMD |
| format check | 当前缺失；未配置格式检查 |
| type-check | Java 编译即类型检查；使用 `mvn -DskipTests compile` |
| build | `mvn clean verify` |
| 数据库或依赖服务 | `docker compose -f docker-compose.dev.yml up -d`，需要 Docker 可用 |
| 流程校验 | `python3 scripts/workflow_check.py --stage schema` |
| 总体验证 | `bash scripts/verify.sh` |

流程脚本依赖 PyYAML；干净环境可先执行 `python3 -m pip install -r scripts/requirements.txt`。

不得声称某条命令通过，除非已经真实执行并记录命令、时间、退出码和关键输出。

## 状态规则

允许状态：`REQUIREMENT_INPUT`、`PRODUCT_DESIGN`、`PRODUCT_REVIEW`、`TECHNICAL_DESIGN`、`DEVELOPMENT`、`UNIT_TEST`、`FUNCTIONAL_TEST`、`BUG_FIX`、`ACCEPTANCE`、`DONE`、`BLOCKED`、`NEEDS_USER_INPUT`、`CANCELLED`。

标准流转：

`REQUIREMENT_INPUT -> PRODUCT_DESIGN -> PRODUCT_REVIEW -> TECHNICAL_DESIGN -> DEVELOPMENT -> UNIT_TEST -> FUNCTIONAL_TEST -> ACCEPTANCE -> DONE`

缺陷返修：

`FUNCTIONAL_TEST -> BUG_FIX -> UNIT_TEST -> FUNCTIONAL_TEST`

每次阶段变化必须更新 `workflow/current-task.yaml` 的 `status`、`current_owner`、`quality_gates` 和 `history`。

## 角色边界

- 当前 Codex 环境支持子智能体时，产品、研发、测试必须分别由独立子 Agent 执行；总负责人只负责任务拆分、调度、审查和状态流转。
- 只有子智能体工具不可用时，才允许在当前会话中按角色顺序降级执行；降级原因必须写入 `workflow/current-task.yaml`。
- 产品 Agent 只负责需求分析、PRD、验收标准和产品审查，不修改业务代码，不决定具体技术实现。
- 研发 Agent 只根据已批准 PRD 进行技术设计、实现和单元测试，不擅自改变产品规则或扩大范围。
- 测试 Agent 依据 PRD 和验收标准设计并执行测试，不修改业务代码，不降低验收标准。
- 流程总负责人负责调度、质量门禁、状态流转、缺陷返修和交付报告，不替代专业角色绕过交付物。

## 强制门禁

- 不得跳过当前流程状态直接进入后续阶段。
- 产品规则以已批准 PRD 为准。
- 所有业务代码修改必须具有对应测试。
- 测试失败时不得进入完成状态。
- 存在未关闭的 P0 或 P1 缺陷时不得完成交付。
- P2 缺陷必须具有明确处理结论。
- 不得通过删除测试、禁用测试或弱化断言使流程通过。
- 不得修改任务范围之外的代码，除非是实现需求所需的最小重构，并在实现报告中说明。
- 只有重大业务歧义、权限/资金/不可逆数据删除、兼容性破坏、外部账号密钥缺失、用户未提交修改冲突或多轮修复失败时才暂停询问用户。
