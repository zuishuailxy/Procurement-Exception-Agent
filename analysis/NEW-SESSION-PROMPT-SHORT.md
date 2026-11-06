# 新会话短提示词（直接粘贴）

```text
# 交接：完成 PEC 采购异常处置 Agent（截止 2026-11-08 15:00 Asia/Shanghai）

先完整读取并严格遵循：
/Users/magicyoung/Project/Procurement-Exception-Agent/analysis/NEW-SESSION-PROMPT.md

要点：
1. 工作方式：plan-then-code + SDD。先写 pec-agent/plan.md 和 pec-agent/todo.md，再按“模块 spec → 实现 → 验证”推进；不要先写业务代码。
2. **每完成 todo.md 里的一个条目，必须停下来向用户汇报并等确认**（用户要能理解改了什么），按 handover §0.1 的 7 段模板：完成项 / 改了哪些文件 / 为什么 / 怎么验证 / 对六项指标的影响 / 风险与假设 / 下一步。用户回复“继续”再做下一项；禁止连做多块、禁止最后一起汇报。不要创建 goal 或自动续跑，一个 todo 结束就停。
3. 环境已就绪：DSH 0.2.1-rc.2、headless profile、API key 在 pec-agent/.env（不要读取/打印/提交）、数据在 pec-agent/db/pec.db；技能根目录已隔离。
4. 基线已提交在 pec-agent 仓库（HEAD 9209145，基线 e0855dd）：7 个工具已注册，5 个已实现，ticket_similar 仍是 NOT_IMPLEMENTED 桩；node dev/test-tools.mjs 应 19 passed。
5. 第一天先跑基线验证：cd pec-agent && ./dev/build.sh && node dev/test-tools.mjs，再跑一次 headless order_lookup 确认；失败先修基线，不要往下做。
6. 不要重写已完成模块；不要改 DSH 内核、预装环境/、实例数据包/、交付物里的 package.json；新增工具必须同步 policy/tool-surface.ts 的 allow 列表并重编译。
7. 工具名统一下划线（order_lookup 等，映射见文件 §3.3）；金额逻辑注意 Fixed 是 4 位定点，不要二次 rescale。
8. 本会话是第一天记录（用户会导出）；关键节点保留可复制的命令与结果。

现在开始：读文件 → 跑基线验证 → 写 plan.md/todo.md（先落盘）→ 做 ticket_similar 这一项 → 按 §0.1 向用户汇报并等确认。
```
