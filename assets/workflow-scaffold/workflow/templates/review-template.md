# <task_id> 当前评审记录

这是本任务当前阶段唯一的评审入口。后续复审更新本文件；旧版本、完整命令输出和会话原文放在 history/evidence 目录。

## 结论

能否进入下一阶段：pending / 可以 / 不可以

一句话说明原因：

kind: code_review（集成后正式评审；需求/候选设计预审使用 precheck-template.md）
requirements_sha256（requirements_digest(task)，完整已确认基线指纹）：

Reviewer / 真实 session：
Matt 实现 session(s)：
独立性核实依据：
base/head SHA、tree snapshot：
范围（含 dirty/untracked、排除及理由）：
REQ/AC、Design/Plan 哈希：

| 维度 | 结论 pending/pass/fail | 报告/证据 |
| --- | --- | --- |
| standards | pending | |
| spec | pending | |

代码质量检查安全、异常、性能、维护性、架构和测试充分性；需求符合性检查需求、ADR、接口和验收。完整命令回执、哈希和会话输出只放证据目录，在这里提供链接。

## 必须处理的问题

每个问题只写一件事。正文使用普通中文，不复制整份需求或设计。

### P1｜一句话说明问题

**问题**

**证据**（文件、行号、用例或命令）

**影响**

**建议**

**完成条件**

**状态**：阻塞 / 待确认 / 已修复 / 仅记录

| 问题 ID | 文件:行号 | 维度 | 严重级别 | 状态 | 阻塞合并 |
| --- | --- | --- | --- | --- | --- |

## 复审

修复版本/SHA、问题逐项处理、重新执行命令、独立复审结论、未解决风险。代码变化后旧结论失效，不能仅改 SHA 字段。
