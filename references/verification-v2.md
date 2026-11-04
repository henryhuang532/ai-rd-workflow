# v2 验证与交付记录

执行时间：2026-11-04T07:20:39.515342+00:00

基准 HEAD：`d002c2361c74daa45df2a660457464d7706e1e90`；改动未提交。引擎 SHA-256：`5c8eb09076ab999eaaa9b53f925ed8a44c51db8b83df8e8be6118e9de873e648`。

实际命令：`bash scripts/verify.sh`，退出码：0。完整输出：[verification-v2.log](verification-v2.log)。

包级检查 3 项、引擎测试 44 项通过；另检查全部 YAML、Markdown 本地链接、两份契约同步、git diff --check。没有业务应用构建配置；项目构建/功能测试不适用本仓库，目标项目必须配置真实验证命令。

## 14 项场景映射

| 场景 | 测试/执行性质 |
| --- | --- |
| 1 小 Bug 完成 | test_01_small_bug，完整状态路径模拟；真实RED→修改临时代码→GREEN命令 |
| 2 普通功能验收 | test_02_ordinary_feature，模拟角色审批，真实命令证据 |
| 3 复杂DAG | test_03_*，内存状态机模拟并检查环/缺失依赖 |
| 4 并行条件 | test_04_*及real_git_worktrees，真实两个worktree/领取；session/probe模拟 |
| 5 高风险阻断 | test_05_*，模拟预授权被拒绝，不执行生产操作 |
| 6 设计变更失效审批 | test_06_*，实际修改文件/重算哈希 |
| 7 独立Review拒绝 | test_07_*，模拟拒绝与自审身份 |
| 8 Tester缺陷回流 | test_08_*，模拟缺陷及QA→FIX→Review门禁 |
| 9 重复失败升级 | test_09_*，模拟计数与阻塞 |
| 10 证据版本不一致 | test_10_*，实际改临时代码导致旧证据拒绝 |
| 11 超时/429 | test_11_*：429为模拟错误；real_timeout为真实子进程超时124 |
| 12 恢复幂等 | test_12_*、operation_uncertainty：真实文件状态存取和租约恢复，外部动作模拟 |
| 13 Git冲突 | test_13_real_git_merge_conflict，真实git merge失败，完成拒绝 |
| 14 伪造绕门禁 | test_14_*，字段、状态和回执不一致均拒绝；不代表能防同权限恶意重写全部文件 |

另验证队列历史完成任务归档、非法领取/依赖跳过、工作区丢失、租约所有权、并发原子写入、动态风险升级和集成修复任务。

## 验证边界

真实执行的是本地Git、文件锁/原子替换、subprocess、超时和一致性校验。角色会话、人工审批、能力probe与429是测试夹具，均不是独立真实授权。当前重构实际使用独立文档、测试和Review子Agent，但未运行一个完整业务项目的多Agent研发闭环。没有执行生产部署、真实付费、迁移或删除，也未验证跨重启会话恢复、长期无人值守唤醒、外部服务幂等、分布式存储锁。

引擎不启动Agent或后台服务。真实并行/恢复依赖已有Codex能力；无独立Review/QA则最终门禁阻塞。本地同权限文件无法认证角色身份/审批来源；动作、环境、期限由可信执行环境核对。审批/设计与历史证据须保留不可变归档。Python采用Unix fcntl，跨平台和网络文件系统未验证。

## 变更清单

M 为修改，?? 为新增；未删除文件。developer.md保留兼容转发；旧单状态和固定会议/统一审批协议弃用。迁移见 [migration-v2.md](migration-v2.md)。

```text
M SKILL.md
M agents/openai.yaml
M assets/workflow-scaffold/.agents/developer.md
M assets/workflow-scaffold/.agents/orchestrator.md
M assets/workflow-scaffold/.agents/product.md
M assets/workflow-scaffold/.agents/tester.md
M assets/workflow-scaffold/AGENTS.md
M assets/workflow-scaffold/docs/bugs/README.md
M assets/workflow-scaffold/docs/designs/README.md
M assets/workflow-scaffold/docs/reports/README.md
M assets/workflow-scaffold/scripts/verify.sh
M assets/workflow-scaffold/scripts/workflow_check.py
M assets/workflow-scaffold/workflow/current-task.yaml
M assets/workflow-scaffold/workflow/templates/task-template.yaml
M references/workflow-file-contract.md
A assets/workflow-scaffold/.agents/integration.md
A assets/workflow-scaffold/.agents/matt-implementer.md
A assets/workflow-scaffold/.agents/reviewer.md
A assets/workflow-scaffold/.agents/superpowers-designer.md
A assets/workflow-scaffold/docs/workflow-contract.md
A assets/workflow-scaffold/scripts/workflow_engine.py
A assets/workflow-scaffold/tests/test_engine.py
A assets/workflow-scaffold/workflow/templates/approval-template.md
A assets/workflow-scaffold/workflow/templates/bug-template.md
A assets/workflow-scaffold/workflow/templates/delivery-template.md
A assets/workflow-scaffold/workflow/templates/design-template.md
A assets/workflow-scaffold/workflow/templates/implementation-template.md
A assets/workflow-scaffold/workflow/templates/meeting-template.md
A assets/workflow-scaffold/workflow/templates/plan-template.md
A assets/workflow-scaffold/workflow/templates/qa-template.md
A assets/workflow-scaffold/workflow/templates/review-template.md
A references/migration-v2.md
A references/review-v2.md
A references/verification-v2.log
A references/verification-v2.md
A scripts/verify.sh
A tests/test_baseline.py
```

独立最终复审：[review-v2.md](review-v2.md)，两个评审维度通过；引擎摘要与本报告一致。
