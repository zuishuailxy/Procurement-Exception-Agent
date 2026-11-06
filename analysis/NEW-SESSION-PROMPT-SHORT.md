# 新会话短提示词（直接粘贴）

```text
# 交接：完成 PEC 采购异常处置 Agent（截止 2026-11-08 15:00 Asia/Shanghai）

先完整读取并严格遵循：
/Users/magicyoung/Project/Procurement-Exception-Agent/analysis/NEW-SESSION-PROMPT.md

要点：
1. 工作方式：plan-then-code + SDD。先写 pec-agent/plan.md 和 pec-agent/todo.md，再按“模块 spec → 实现 → 验证”推进；不要先写业务代码。
2. 环境已就绪：DSH 0.2.1-rc.2、headless profile、API key 在 pec-agent/.env（不要读取/打印/提交）、数据在 pec-agent/db/pec.db；技能根目录已隔离。
3. 基线已提交在 pec-agent 仓库（HEAD 9209145，基线 e0855dd）：7 个工具已注册，5 个已实现，ticket_similar 仍是 NOT_IMPLEMENTED 桩；node dev/test-tools.mjs 应 19 passed。
4. 第一天先跑基线验证：cd pec-agent && ./dev/build.sh && node dev/test-tools.mjs，再跑一次 headless order_lookup 确认；失败先修基线，不要往下做。
5. 不要重写已完成模块；不要改 DSH 内核、预装环境/、实例数据包/、交付物里的 package.json；新增工具必须同步 policy/tool-surface.ts 的 allow 列表并重编译。
6. 工具名统一下划线（order_lookup 等，映射见文件 §3.3）；金额逻辑注意 Fixed 是 4 位定点，不要二次 rescale。
7. 本会话是第一天记录（用户会导出）；关键节点保留可复制的命令与结果。
8. 用户不在线时按 plan 自主推进，不要停下来等确认；只有真正阻塞才问。

现在开始：读文件 → 跑基线验证 → 写 plan.md/todo.md（先落盘）→ 从 ticket_similar 开始按顺序推进。
```

## 变更说明（v1 → v2）

- 删掉了“先接线”的过时要求：接线已完成并提交（e0855dd + 9209145）。
- 基线验证命令从 `pec.data.catalog` 改为 `node dev/test-tools.mjs` + `order_lookup`。
- 补充：工具命名映射、`tool-surface.ts` 的 allow 同步、技能根目录隔离、`DSH_HOME` 强制、Fixed 二次缩放陷阱。
- 明确“本会话是第一天记录”，上一轮讨论会话不计入交付。
