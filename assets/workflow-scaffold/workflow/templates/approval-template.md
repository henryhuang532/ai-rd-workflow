# <task_id> 授权记录（模板不构成授权）

kind: human / preauthorized
决策: pending
真实授权主体：
来源原文/链接/原始记录路径与哈希：
时间/期限：
任务/动作/环境/允许路径范围：
风险等级及因素：
Requirements baseline version/path、requirements_digest(task)（authorization.requirements_sha256，含 PRD/REQ/AC 范围）：
Design path/version/SHA-256：
Plan path/version/SHA-256：
限制、预算与不可逆边界：
核实来源的真实执行会话/人员：
版本/范围变化后的重新授权记录：

L3/L4 必须 human。沉默、Agent 投票、自填 approved 字段不能替代真实人工授权。审批结论必须由当前可信执行环境核实；本地文件哈希无法证明主体身份。

需求确认、设计/实施授权分别记录；选择单个 DEC 不批准整份产物。需求基线变化后旧授权失效，不能只修改哈希字段沿用。
