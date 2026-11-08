# AI 会话记录导出（D1）

| 项 | 值 |
|---|---|
| 会话标题 | 第一天 |
| 会话 ID | `session-421f9bed-9e9f-44eb-9245-e5a142daec35` |
| 工作目录 | `/Users/magicyoung/Project/Procurement-Exception-Agent` |
| 创建时间 | 2026-11-07 09:53:25（Asia/Shanghai） |
| 导出时间 | 2026-11-07 19:43:09（Asia/Shanghai） |
| 事件总数 | 1718 |
| 轮数（turn） | 13 |
| 用户消息（真实） | 13 |
| 助手消息 | 215 |
| 工具调用 | 220（isError 0 次；命令非零退出 3 次，已如实保留在记录里） |
| Token 合计 | input 200130 / output 302177 / cacheRead 57696512 / total 58198819 |

## 文件

| 文件 | 说明 |
|---|---|
| `session-421f9bed-9e9f-44eb-9245-e5a142daec35.md` | **人读版对话记录**（推荐先看）：用户/助手正文 + 工具调用 JSON + 结果（超长截断） |
| `session-421f9bed-9e9f-44eb-9245-e5a142daec35.jsonl` | 解压后的完整事件流（NDJSON，含运行时上下文/技能目录/时间快照等系统注入，保真） |
| `session-421f9bed-9e9f-44eb-9245-e5a142daec35.jsonl.zst` | 原始会话文件（DSH 多帧 zstd），与平台存储一致 |

## 工具调用统计

| 工具 | 次数 |
|---|---|
| `bash` | 154 |
| `write` | 26 |
| `job_output` | 22 |
| `read` | 11 |
| `edit` | 3 |
| `present` | 3 |
| `list_agents` | 1 |

## 如何复核/重新导出

原始会话文件在 DSH 的 session 存储里（`$DSH_HOME/sessions/<项目编码>/<会话ID>/session.v4.jsonl.zstd`）。
DSH 的 `.zstd` 是**多帧拼接**，直接 `zstd -d` 只能解第一帧；请用本目录上一级的 `export-dsh-session.mjs`：

```bash
cd <工作区根目录>
node AI会话记录/export-dsh-session.mjs --session-id session-421f9bed-9e9f-44eb-9245-e5a142daec35 --out AI会话记录/D1
```

> 说明：本次导出在会话进行中执行，**最后一个 assistant 回复的收尾部分可能不在快照里**；如需包含完整末轮，可在会话结束后重跑上面的命令覆盖导出。
> 平台按项目一级目录编码会话根，工作区根为 `/Users/magicyoung/Project/Procurement-Exception-Agent`；不要修改 `session.v4.jsonl.zstd` 原件（导出器只读）。
