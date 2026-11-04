# <task_id> Plan / <version>

作者/真实 session：
输入 Design 版本/path/SHA-256：
授权或待审批范围：
可行性证据：

| Task ID | Parent | REQ/AC | ADR | dependencies | role/agent | workspace/branch | resources/允许路径 | 验收与测试命令 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## DAG 与调度依据

声明数据/接口依赖、无环验证、独占资源/冲突路径、max_parallel、逻辑并行及真实执行能力；串行降级原因。

## 每任务 TDD 步骤

真实文件路径、公共 seam、RED 测试及预期失败原因、GREEN 最小实现、REFACTOR、完整验证、产物和 evidence 路径。

## 集成与交接

拓扑整合顺序、接口契约检查、构建/集成/回归命令、role=integration 的真实 run-evidence command_evidence、冲突修复任务生成方式、Review/QA 交接、检查点、重试预算、回滚。
