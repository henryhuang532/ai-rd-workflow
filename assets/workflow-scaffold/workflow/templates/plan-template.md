# <task_id> Plan / <version>

作者/真实 session：
输入 Requirements baseline 版本/path/SHA-256：
输入 Design 版本/path/SHA-256：
授权或待审批范围：
可行性证据：

| Task ID | Parent | REQ/AC | ADR | dependencies | role/agent | workspace/branch | resources/允许路径 | 验收与测试命令 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## DAG 与调度依据

声明数据/接口依赖、无环验证、独占资源/冲突路径、max_parallel、逻辑并行及真实执行能力；串行降级原因。

## 每任务 TDD 步骤

技能来源仓库/提交 SHA、实际安装路径、所读原始 SKILL.md 及引用文档 SHA-256：
公共 seams、每个 seam 覆盖/未覆盖范围、用户确认来源及对应计划版本：

按 Matt 原始 `implement`、`tdd` 规划真实文件路径、逐个纵向切片的 RED 测试及预期失败原因、GREEN 最小实现、完整验证、产物和 evidence 路径；重构安排在 `code-review` 评审阶段。此处不重写原始技能；缺失从 `mattpocock/skills` 安装，安装/读取失败则受影响实施 BLOCKED，不凭理解或其他 TDD 技能替代。

## 集成与交接

拓扑整合顺序、接口契约检查、构建/集成/回归命令、role=integration 的真实 run-evidence command_evidence、冲突修复任务生成方式、Review/QA 交接、检查点、重试预算、回滚。
