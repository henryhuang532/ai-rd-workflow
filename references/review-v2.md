# v2 独立代码评审

评审角色：独立 Reviewer 子 Agent `/root/review`；未参与实现修改。Standards Review 与 Specification Review 分别检查。评审对象为当前未提交文件，基准 Git HEAD `d002c2361c74daa45df2a660457464d7706e1e90`。此报告是代码评审，不是生产变更人工授权，也不把模拟角色记录当作实际产品交付。

## 版本与范围

- `assets/workflow-scaffold/scripts/workflow_engine.py` SHA-256：`5c8eb09076ab999eaaa9b53f925ed8a44c51db8b83df8e8be6118e9de873e648`。
- `assets/workflow-scaffold/tests/test_engine.py` SHA-256：`88826a4b0c258f65b4f94b7ba468bc702a87c520bda0b98288d27985d005ea68`。
- 审阅入口 Skill、统一契约及迁移说明，重点覆盖 DAG、授权、状态推进、证据、并发领取、集成、重试与恢复。之后代码内容变化需要重新评审受影响范围。

## Standards Review

结论：在文档声明的本地受信执行环境边界内通过，无尚未解决的阻塞性代码评审意见。首轮发现以下阻塞问题，并对修复复审：

| 发现位置/问题 | 严重级别 | 修复与复审 |
| --- | --- | --- |
| validate/delivery_gate 对历史完成任务使用当前代码快照，后续代码变化阻塞整个队列 | P1 | completed_snapshot 归档快照保留历史证据；新增队列回归通过 |
| transition 在 BLOCKED/CANCELLED 时要求旧 Review/审批继续通过，无法暂停失效任务 | P1 | 暂停/终止跳过失效的推进门禁；失效证据取消与持久化测试通过 |
| claim 使用旧 workspace 判断冲突，再写入实际参数 | P1 | 领取前比较实际路径，拒绝同路径及嵌套工作区；冲突测试通过 |
| 可绕过 claim 直接 READY→RUNNING，没有租约、依赖检查及 attempts 消耗 | P1 | transition 验有效租约和前置完成，validate 独立拒绝无领取记录 RUNNING；实际复现已由接受变为拒绝 |
| 集成仅通过布尔字段及普通文件证明 | P1 | 增加真实 command_evidence receipt、版本、退出码及角色校验 |

验证了原子锁/replace、失败写不落盘、租约检查点、工作区丢失、超时保留证据与非幂等结果不明时拒绝重放。外部操作不承诺 exactly-once。

## Specification Review

结论：本地 Skill/门禁重构的可执行范围通过；真实外部执行器能力保留明确限制。

- 风险 L1/L2 支持预授权，无固定会议；L3/L4 要求 human 类型审批。设计/计划哈希变化拒绝旧授权。
- Superpowers、Matt、独立 Reviewer/Tester、临时 Integration 的职责已分离，Matt 自审不能满足最终 Review。
- DAG 依赖及串行降级、隔离工作区和并发上限有可执行检查。修复了需求/架构问题无法从 QA/FIX 返回相应阶段的问题。
- 已完成任务按归档快照验证，新交付仍以当前快照验证；代码变化拒绝过期 QA/Review。
- 缺陷分类、有界修复、集成失败修复任务、429/超时恢复、检查点与幂等记录有测试覆盖。

## 实际执行证据

本次复审实际运行：

```text
python3 -m unittest discover -s assets/workflow-scaffold/tests -v
Ran 44 tests in 4.401s
OK
exit_code: 0
```

另外实际运行 Python 内存状态复现脚本，创建 A=PENDING、B 依赖 A，尝试绕过 claim 推进 B，并伪造无租约 RUNNING 后调用 validate。两次均被拒绝，脚本退出码 0：

```text
PASS: transition bypass rejected: valid owned lease required; use claim
PASS: forged RUNNING rejected: RUNNING requires claimed lease/workspace/attempt
```

测试类型必须区分：审批、独立角色身份、429/容量错误及完整研发流程使用模拟输入；Git Worktree、Git 冲突、命令运行/退出码/超时、文件证据哈希、原子持久化与并发 writer 为本地真实执行。44 项通过不代表真实生产任务、生产审批或持续后台调度已验证。

## 外部限制与非阻塞意见

1. 本地文件与 session 字符串没有可信签名根；有相同写权限的主体可重写脚本和完整记录。源授权、主体、期限、动作/环境及真实角色独立性需由既有可信执行环境核实，不能仅依赖 YAML 字段。
2. 脚本不创建 Agent、不提供后台唤醒或跨重启持久会话；这些能力需现有 Codex/执行器实际提供。
3. 归档设计、授权、报告与 receipt 应使用不可变任务专属路径；删除历史证据会使历史验证失败。
4. 测试命令的业务充分性、TDD 失败原因及评审报告语义仍需专业 Reviewer/Tester 判断；退出码和哈希只能验证一致性。
5. 本地 Unix 文件锁语义不等同分布式锁；未验证跨主机文件系统及真实服务端 429、生产迁移/部署。
