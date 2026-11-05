# 工作流 v2 统一契约

本规范同时随 scaffold 复制到 `docs/workflow-contract.md`。数据与转移以 `scripts/workflow_engine.py` 为可执行约束；脚本不能执行的角色独立性/授权来源核验由真实执行环境提供，缺失则阻塞。不得直接编辑 status 绕过门禁。

## 数据与生命周期

顶层：`schema_version: 2`、`revision`、`capabilities`、`policy`、`tasks`。current-task 文件现为队列，不再是唯一活动任务。

每任务至少有 task_id、parent_task_id、requirement_ids、title、description、risk_level、status、stage、dependencies、assigned_role、assigned_agent、workspace、branch、acceptance_criteria、artifacts、attempts、timestamps、evidence；另存 requirements、design、plan、authorization、reviews、tests、bugs、lease、operations、history。ID 唯一，依赖存在且无环；父任务只是归组，前置关系必须显式写 dependencies，避免父子依赖死锁。

新增任务另初始化 requirements_baseline、open_questions、prechecks、agent_dispatches。旧 v2 活跃任务缺少这些字段时可读取和保存 INTAKE/REQUIREMENTS/阻塞检查点，但必须补齐有效基线才可继续 DESIGN 及后续阶段；不得推导为已确认。历史 COMPLETED 且没有 requirements_baseline 字段的任务，仅在归档模式按原证据规则验证，不生成新基线或新交付批准；重新交付必须满足新门禁。详见迁移指南。

生命周期：PENDING、READY、RUNNING、WAITING_APPROVAL、BLOCKED、FAILED、COMPLETED、CANCELLED。REVIEWING/TESTING/FIXING 是旧输入别名，迁移为 RUNNING + CODE_REVIEW/QA/FIX；v2 不同时维护两套含义。阶段：INTAKE、REQUIREMENTS、DESIGN、FEASIBILITY、PLANNING、APPROVAL、IMPLEMENTATION、INTEGRATION、CODE_REVIEW、QA、FIX、DELIVERY。

| 转移/阶段 | 进入/退出条件与产物 | 执行角色、审批和失败策略 |
| --- | --- | --- |
| PENDING→READY | 依赖完成、资源可用、需求/范围存在 | Orchestrator；失败保持等待，独立分支继续 |
| READY→RUNNING | 领取原子租约，真实 session/workspace，重试预算 | 任务指定角色；超时恢复检查点，不盲目重放 |
| INTAKE→REQUIREMENTS | 原始需求、风险理由、影响范围 | Product；重大歧义 BLOCKED |
| REQUIREMENTS→DESIGN | 唯一且非空 REQ/AC、可验证标准、版本化需求基线及真实确认来源；本范围无未决阻塞规则 | Product 收敛，Architect/Superpowers 接收；候选预审保留 REQUIREMENTS，变化返回 Product |
| DESIGN→FEASIBILITY | 设计版本/哈希、ADR、接口、测试和回滚 | Architect；重大假设隔离 Spike |
| FEASIBILITY→PLANNING | 七项检查有命令/证据，未决假设已处理 | Architect；失败回 DESIGN |
| PLANNING→APPROVAL | DAG、所有权、资源、验收/测试映射 | Architect/Orchestrator；缺失计划不得实施 |
| APPROVAL→IMPLEMENTATION | 有效预授权或所需明确人工审批，版本一致 | Matt；L3/L4 所需审批未取得 WAITING_APPROVAL |
| IMPLEMENTATION→INTEGRATION | TDD RED/GREEN、变更与实现侧验证 | Matt/Integration；失败 FIX 或 BLOCKED |
| INTEGRATION→CODE_REVIEW | 所有前置产物整合、无冲突、构建与契约测试 | Integration；冲突建修复任务，不宣布完成 |
| CODE_REVIEW→QA | 独立 Reviewer 两轴结论通过，当前版本绑定 | Reviewer；拒绝 FIX，架构问题回 DESIGN |
| QA→DELIVERY | 独立 Tester 验收/回归通过、所有 AC 有证据 | Tester；缺陷 FIX，环境问题 BLOCKED |
| DELIVERY→COMPLETED | 再验授权/版本/证据/独立性，无阻塞缺陷 | Orchestrator 只执行门禁；缺证据拒绝完成 |
| RUNNING→BLOCKED/FAILED | 原因、日志、检查点、重试次数与下次时间 | Orchestrator；有界恢复，不阻塞无关任务 |
| BLOCKED/FAILED→READY | 原因已处理、预算允许、人工接管记录 | Orchestrator；恢复后重跑受影响门禁 |
| 任意未完成→CANCELLED | 有权主体取消、保存已有产物和租约结果 | Orchestrator；取消不等于成功，不撤销外部效果 |

风险越级时停止受影响写操作。设计/计划/验收变更需要重新计算哈希和影响；修改代码后旧 Review/QA 默认失效。低风险允许最小文档及快速连续转移，但每一必要门禁仍必须真实满足。

## 需求预审、收敛与基线

预审是 REQUIREMENTS 内按议题开展的活动，不增加主阶段。`prechecks[]` 使用 `kind: requirements_precheck | design_precheck`，记录真实 session、输入产物/哈希、REQ 范围、问题/风险/证据/建议和报告路径；输出是澄清输入，没有正式代码/验收 pass/fail。Reviewer 找规则冲突与风险，Tester 检查可测试性和候选场景，Architect 提供方案取舍。角色不能凭候选分析自行决定业务规则；规则选择不等于整份 PRD、设计或实施批准。

Product 区分确认/事实/建议/假设/待决；`open_questions[]` 每项含 question_id、description、owner、status（open/resolved/deferred）、blocking（布尔）和 requirement_ids。空 requirement_ids 表示阻塞整个本任务；非空只阻塞与本任务 REQ 交集。范围内 blocking=true 且未 resolved 的问题阻止基线门禁，改成 deferred 不能绕过。标记非阻塞或排除范围需记录真实理由与决定来源；脚本不判断自然语言业务充分性。

默认先汇总决策清单及关键场景，再等待重大业务决定；暂停依赖该决定的完整设计、接口和验收矩阵扩写，独立范围继续。用户要求完整候选草案时分别标注候选及条件式预期。未确认预期的用例为 draft/not_run，文档检查成功和预审完成不算验收通过。预审人员不可用时记录单会话分析及限制；无需为非必需预审阻塞无关工作，最终独立 Review/QA 仍必需。

`requirements_baseline` 字段：status=confirmed、version、document={path,sha256}、requirements（当时 requirements 原记录快照）、acceptance_ids（当时 acceptance_criteria），以及 confirmation={actor,timestamp,source:{path,sha256},document_sha256,baseline_sha256}。先填写基线版本/文档/映射，再用 `requirements_digest(task)` 计算 baseline_sha256：其指纹同时包含 version、document、requirements、acceptance_ids，确认元数据不参与，避免自引用。来源必须是已有用户/有权主体真实确认，绑定本版 PRD 及交付范围；内容和范围仍有效的确认可复用，不强加重复确认。基线可按交付子范围建立。候选技术预审可在基线前支持决策；正式 DESIGN 和后续活跃阶段由 requirements_gate 检查 REQ/AC 唯一/非空/映射、基线、来源及范围内阻塞项。

需求基线不是设计/实施授权。authorization、正式 reviews 及 QA receipt 另绑定 requirements_sha256（由 requirements_digest(task) 计算的完整基线指纹，包含版本/PRD/REQ/AC 范围），并保留原有设计/计划/代码版本约束。需求文档、REQ/AC 范围或业务预期变化时保存原版、复核影响并重建受影响基线/授权/证据；不能仅替换旧确认/报告中的哈希。小的格式修订也须先核实来源仍覆盖新版本，再记录影响与复用依据。哈希和字段仍不认证主体或证明语义正确。

后续阶段发现基线失效时可先在原阶段 BLOCKED 保存检查点，再由 transition 返回 READY/REQUIREMENTS 重新领取澄清；该回退不验证已经失效的基线，也不自动更新确认/授权，不重置尝试预算。重新前进时完整重验。

## 评审入口与写法

每个任务和阶段只保留一个当前评审入口，默认是 `docs/reports/<task_id>-review.md`。后续复审更新同一文件；旧版本放入任务历史，命令回执和完整会话输出放入任务证据目录。不要为同一轮生成多份重复总结。

评审正文先写结论，再逐项写问题。每个问题必须包含：问题、证据、影响、建议、完成条件和状态。问题应有文件/行号或其他可定位位置；没有影响和完成条件的意见不能作为阻塞项。正文使用普通中文，字段名、哈希、模型参数和命令细节只放元数据或证据链接。评审报告不复制整份 PRD、设计或测试报告；复审只补充新增或变化的问题。

## 子 Agent 选择与成本记录

只有存在具体独立问题/产物或独立质量门禁时才委派。格式、链接、ID 与结构化覆盖优先脚本；事实提取/定位、已确认规则同步、明确局部任务使用经验证可胜任的低成本模型；多步歧义、跨模块推理、权限/租户隔离/迁移关键判断使用更强模型。按子任务选 model/effort，角色不固定档位，不能从参数量推导能力、token 用量或价格。能力表来自当前真实工具，不维护固定型号或猜测可用性。

授权允许且工具支持覆盖时显式选择 model/reasoning_effort；否则记录实际继承和限制。新上下文交接包含任务/REQ、目的/阶段、当前确认与授权、安全约束、相关输入路径/版本、具体问题、允许/禁止路径、完成条件及输出契约。工具支持时不继承无关历史；如覆盖参数与完整历史 fork 不兼容则使用 `fork_turns: none` 配合交接包。已有可恢复专业会话可复用，但先核对其输入版本，不为了换模型创建同义任务绕过重试限额。

`agent_dispatches[]` 按 handoff 模板记录目的/风险、选择理由、请求与实际可观测 model/effort、上下文范围、输出预算、attempt、升级原因、用量和结果。用量不可观测时 tokens/cost 留 null，并记录原因；API 单价不能直接冒充订阅额度扣减。不因低价不断试错：证据不足、超出能力或风险升级时保留有效发现并升级，沿用同一任务和重试预算。仅对变化部分重审，稳定全文不重复生成。实际节省应按一次合格交付的主/子 Agent、协调、重试、复核总量衡量；模型更便宜不保证 token 更少。脚本不选择或启动模型，不声称本地结构校验已证明模型质量或节省比例。

## 技能依赖与安装

Superpowers 设计读取实际安装的 `brainstorming`、`writing-plans`。Matt 实现、TDD 与评审的唯一指定来源是 [mattpocock/skills](https://github.com/mattpocock/skills)，不能把 Superpowers TDD 视作替代品。

| 技能 | 原仓库路径 | 使用时机 |
| --- | --- | --- |
| `implement` | `skills/engineering/implement` | 按已授权 spec/任务实施 |
| `tdd` | `skills/engineering/tdd` | 每个测试/实现循环，含 `tests.md`、`mocking.md` |
| `code-review` | `skills/engineering/code-review` | 实现后的 Standards/Spec 双轴评审及重构阶段 |
| `codebase-design` | `skills/engineering/codebase-design` | 接口、模块深度及 seam 位置存在设计问题时 |

缺失时安装原目录及全部配套文件，不自行创建同名技能或抄写摘要。Codex 有 `skill-installer` 时使用其实际脚本；以下命令固定到本次核验的上游提交，已安装目录先核实来源，不覆盖用户定制：

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo mattpocock/skills \
  --ref 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d \
  --path skills/engineering/implement skills/engineering/tdd \
         skills/engineering/code-review skills/engineering/codebase-design
```

实际仅传入缺失项的路径；无该脚本时遵循原仓库 README 对当前执行器的安装说明。需要升级时先读取新版本，记录新提交 SHA 并核对计划变化。安装失败、缺少配套文档或来源无法核实，记录 current_missing、真实失败日志及检查点，受影响实施保持 BLOCKED；独立无关任务可继续。不得凭理解、记忆、本地流程摘要或其他来源的 TDD 技能继续实施。

实施前读取安装目录的原始 `implement/SKILL.md`、`tdd/SKILL.md`、`tdd/tests.md`、`tdd/mocking.md`；评审读取 `code-review/SKILL.md`，接口/seam 设计按需读取 `codebase-design` 及其适用引用。记录仓库 URL、上游提交 SHA、安装路径、实际所读文件路径及 SHA-256；恢复/升级时核对文件变化，重新读取受影响文档。安装成功不等于执行过技能，角色和报告必须提供实际读取及执行证据。

以原文为执行依据：测试之前确认用户已同意的公共 seams，并列明各自覆盖/未覆盖范围；一次一个纵向切片 RED→GREEN，不先写完全部测试再实现。当前核验版本将重构放到评审阶段，不套用 RED→GREEN→REFACTOR。已有有效用户确认可复用，变化后重新确认。上游技能中的提交、发布等动作仍受已有用户授权和仓库规则约束。以上是来源及交接约束，不能替代每次读取原始技能；本地脚本的 RED/GREEN 检查不能证明 Agent 确实遵循了技能，须由真实执行环境和独立评审核实。

## DAG 调度与集成

Architect 从模块接口、数据依赖和资源所有权推导 dependencies，记录依据；验证器执行 DAG 检查。调度 READY 集合，依赖完成后才能领取。无依赖、工作区与资源不冲突、授权有效才可并行。逻辑并行不代表真实会话并发。默认 serial + max_parallel=1；只有检测到独立会话、worktree 和槽位才提升并发。每个 Matt 实例独占 workspace/branch，禁止共享写工作区。计划注明冲突路径，跨工作区共享外部资源也须串行。

子任务进入集成后才进入独立 Review/QA。集成必须保存 role=integration 的实际 run-evidence command_evidence、成功退出码及当前 snapshot，不能用任意日志文件替代。父交付任务依赖全部子任务或其集成产物；不可让父任务先完成。Integration 可由临时独立 Agent 或已授权执行角色承担，Orchestrator 只调度和执行门禁。冲突记录具体分支/SHA/文件与失败命令，创建修复任务并重跑集成及受影响验证。

## 授权与证据

预授权来自用户/组织真实政策，记录 scope、restrictions、source、actor、timestamp、expiry；不从风险低推导授权。L3 设计审批及 L4 高风险动作均须明确人工批准（kind: human）；绑定 design/plan version 和 SHA-256、动作、环境、范围，内容改变旧审批失效。审批不能由 Agent 投票、沉默、字段 approved=true 或 issue 关闭替代。执行前复核实际来源，不把模板视作授权。脚本强制检查 decision/kind、风险/任务 scope、来源文件哈希和 design/plan 哈希；主体身份、有效期限、动作、环境与组织限制必须由当前可信执行环境复核，脚本不认证这些字段。

追踪链：REQ→ADR/Design→Task→Git SHA/dirty snapshot→TC→Evidence。AC 必须唯一并映射至少一项独立验收测试。命令证据含 argv/工作目录、真实开始/结束时间、退出码、完整日志或路径+哈希、执行角色/真实 session、代码 SHA 和工作树快照。RED 证据绑定失败时版本并记录预期失败原因；GREEN/Review/QA/集成绑定最终交付版本。模板的空字段永远不是通过证据。

正式 Review 使用 kind=code_review、requirements_sha256，另记录 base/head SHA、dirty/untracked 范围、Reviewer session、Standards 和 Specification 两轴、位置、severity、建议、blocking、结论及复审。Reviewer 与 Matt 必须独立，Tester 也不得由 Matt 自评充当。QA 保存用例、需求/AC、前置数据、步骤、预期/实际、命令/退出码/日志、正常/异常/边界/权限/回归适用性；其命令 receipt 必须含 kind=qa_execution 和 requirements_sha256。run_evidence 默认 kind=command，即使 role=tester 也不自动计入 QA；正式执行须显式传 kind 和基线哈希（CLI 对应 --kind qa_execution --requirements-sha256）。类型字段与哈希只约束记录一致性，不能将无关 exit 0 命令变成业务验收。

当前交付代码或设计版本改变后默认失效关联门禁；历史设计/计划/审批/证据必须保存到任务独立的不可变归档路径，不能复用覆盖；已完成历史任务以 completed_snapshot 归档并核验原版本证据，不要求随之后续任务改代码而重新执行，避免阻塞整个队列；重新开启/修改原任务则重新验证。只可由独立角色记录可验证影响分析后复用不受影响证据，不能只改版本字段。P0/P1 未关闭阻止交付；P2 需明确处理和有权接受剩余风险，不删测试或弱化断言以消除失败。

本地文件模式没有身份认证/签名根。本地哈希只能检测内容变化，无法证明来源。直接修改所有证据、脚本或审计记录的同权限攻击者不在本地门禁可防范围；需要已有可信执行器、受保护 CI/人工原始授权进行来源确认。无法确认则 BLOCKED，不生成“已验证”记录。

## 缺陷与会议

缺陷标准生命周期：发现→分类→根因→责任→修复→独立复审→受影响回归→关闭。六类路由：implementation→Matt；requirement→Product；architecture→Architect；test→Product+Tester；environment→BLOCKED；unreproducible→Tester 收集复现条件，未证实前不宣布修复。相同 bug 累计 attempts，不能换 ID 清零。默认最多 3 次，重复失败交独立 Reviewer 根因分析；耗尽 BLOCKED/人工接管，不自动通过或架构重写。

会议只为重大歧义、方案/验收冲突、跨角色 ADR、反复失败、重大风险复核。议题选择参与者、真实 session、最多 3 轮、输入版本，记录提出方案→独立意见→反驳证据→修订→决策与行动项。未形成可验证结论 BLOCKED/升级；多数票不替代人工授权。没有真实独立发言就记录为单会话分析，不伪造会议。

## 原子持久化与恢复

使用执行环境已有恢复功能；本地脚本通过锁、revision 校验、临时文件/fsync/原子 replace 更新状态，history 保存 from/to（含 stage）、actor/session、时间、原因、artifacts 与 validation。任务租约含真实 session、claimed_at/expires_at；所有权另由 assigned_agent/workspace 和 checkpoint 记录；租约失效先核对原执行是否仍活动和工作区状态再恢复，禁止两个 writer 接管。

429/容量不足：保留原任务与 session、prompt/产物、错误；遵守 Retry-After，指数退避并受 max_attempts 限制。超时/进程中断：保存失败和检查点，租约到期只回收调度权，不假定外部动作失败。上下文耗尽：输出 handoff 和检查点，使用真实恢复能力；不能恢复时记录新会话缘由。工作区丢失：BLOCKED，核对 Git/产物后重建，不静默丢代码。合并冲突：BLOCKED 或 FIX 任务。测试环境不可用：BLOCKED，禁止将 not_run 改为 passed。

操作以 operation_id/idempotency_key 去重，记录 started/completed（中断且仍为 started 表示结果未知） 及结果证据。幂等操作可按检查点和预算恢复；非幂等操作运行中中断或结果不明必须人工核对后决定，不自动重放。脚本不承诺跨进程/外部系统 exactly-once；优先使用服务原生幂等键。人工接管必须记主体、原因、原操作结果核对、恢复点和证据。

无常驻服务时每次前台调用处理可运行批次并写 checkpoint/next_retry_at，未来由用户或已有调度器再次调用；不假设后台自主唤醒、持久 Agent 或跨重启会话存在。

## 本地 API 调用约定

CLI 负责领取、转移、恢复、校验和运行命令；需求、审批、独立报告等结构化输入由已有 Agent 通过 Python API 交接。不要裸写 YAML。示例（在目标仓库根运行）：

```python
import sys
from pathlib import Path
sys.path.insert(0, 'scripts')
from workflow_engine import Store, new_task
root = Path.cwd()
store = Store(root / 'workflow/current-task.yaml')
store.update(lambda s: s['tasks'].append(new_task('TASK-001', '用户原始需求')), root)
```

每次 API 写操作使用 Store.update，读取最新状态后再改。真实专业会话把 requirements/design/plan/feasibility/authorization/reviews/tests/tdd/integration 等产物通过同样入口写入；字段形式参照任务模板及 tests/test_engine.py 的模拟示例，严禁复制其中模拟审批充当真实批准。命令证据可用 run_evidence，必须使用实际检查行为的 argv。不能把任意 exit 0 命令解释为验收。Store 的校验只证明记录一致性；Review/QA 语义判断仍由独立专业会话承担。

heartbeat 更新所属租约与检查点；fail 记录实际错误和退避；recover 回收过期或工作区丢失租约；escalate 清空旧授权；integration_failure 建立有 parent_task_id 的独立修复任务。operation 先将 started 通过 Store 持久化再执行外部动作，成功且证据保存后才更新为 completed；中间崩溃视为未知，不宣称 exactly-once。
