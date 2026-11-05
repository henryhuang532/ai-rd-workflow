# 报告与证据

保存实现、Review、QA、集成、阻塞和交付报告。每个任务和阶段只有一个当前评审入口，默认是 `docs/reports/<task_id>-review.md`；后续复审更新同一文件，旧版本和完整命令输出放入 `workflow/history/` 与 `workflow/evidence/`。评审正文先写结论，再逐项写问题、证据、影响、建议和完成条件，不复制整份需求或设计。命令必须真实，含退出码、版本、时间、日志及哈希。独立会话不可用时明确未验证，不用自评代替。模板见 `workflow/templates/`，门禁见 [统一契约](../workflow-contract.md)。

需求/候选设计预审报告标 requirements_precheck/design_precheck，记录问题和建议，不计为正式通过。正式 code_review 和 qa_execution 绑定需求基线及交付版本。交接按 handoff 模板保留模型选择理由、必要上下文和实际可观测用量，缺失用量不得填成零或宣称节省。
