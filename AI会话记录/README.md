# AI 会话导出（交付物）

> 对应任务书 §8.1「AI 会话导出：两天的记录」、交接文档 §9「按日分文件夹」。本目录保存**与 AI 的真实会话记录**，与 `pec-agent/` 交付代码分开存放，最终打包时一起收入 `姓名-PEC-日期.zip`。

## 目录

```
AI会话记录/
├── export-dsh-session.mjs     # 导出器（只读 DSH 会话文件；可重复运行；按 --out 目录名生成 D1/D2 标题）
├── D1/                        # 第一天（2026-11-07）
│   ├── README.md                                       # 元数据 + 统计 + 阅读说明
│   ├── session-421f9bed-....md                         # 人读版对话记录（推荐）
│   ├── session-421f9bed-....jsonl                      # 完整事件流（NDJSON，保真）
│   └── session-421f9bed-....jsonl.zst                  # 原始会话文件（DSH 多帧 zstd）
└── D2/                        # 第二天（2026-11-08，CR#1 → T10 → T11 → T12/T13）
    ├── README.md
    ├── session-4678dfc5-....md
    ├── session-4678dfc5-....jsonl
    └── session-4678dfc5-....jsonl.zst
```

## D1（2026-11-07）

| 项 | 值 |
|---|---|
| 会话 | `session-421f9bed-9e9f-44eb-9245-e5a142daec35`（标题「第一天」） |
| 起止 | 09:53 创建 → 19:43 导出（Asia/Shanghai） |
| 内容 | 13 轮：读交接 → 基线验证 → T1 `ticket_similar` → T2 `advice_card`（含 headless 暴露的 lossless JSON 基线修复）→ T3 记忆 + 注入 → T4 技能 A/B + `skill_write` → T5 评测/门禁 → T5 稳定性修复 → T6 专项集 + A/B → T7 traces → T8 文档 + `d1` tag → 会话导出；共 220 次工具调用 |
| 交付代码 | 对应 `pec-agent/` 仓库 commit `cb66e38`、tag **`d1`** |
| 文件 | Markdown 约 600KB / JSONL 6.9MB / 原始 zst 2.0MB |

## D2（2026-11-08）

| 项 | 值 |
|---|---|
| 会话 | `session-4678dfc5-5b4c-4533-9abd-ace050aff3ec`（标题「第二天」） |
| 起止 | 10:25 创建 → 14:32 导出（会话进行中快照，Asia/Shanghai） |
| 内容 | 8 轮：T9 CR#1 落地 + 全回归（用户复跑暴露 g-09 断言假阳性修复、g-01 prompt 二义修复）→ T10 失败归因（bash 越界 + 能力边界修复）→ T11 评测报告 + A/B 定稿（六指标全绿）→ T12 defense + 文档定稿 → T13 干净环境复现/打包/`d2` → 交付打包与 README 三段命令；1583 事件 / 212 次工具调用 |
| 交付代码 | 对应 `pec-agent/` 仓库 commit `f6ff916`、tag **`d2`** |
| 文件 | Markdown 约 580KB / JSONL 4.9MB / 原始 zst 1.5MB |

**怎么读**：先看 `D*/session-*.md`（用户/助手正文 + 工具调用参数 + 结果，超长截断）；需要保真核对时用 `D*/session-*.jsonl`（含运行时上下文、技能目录、时间快照等系统注入）；`.zst` 与 DSH 平台存储一致，可直接归档。

## 重新导出（会话结束后补齐末轮）

本次 D2 导出在会话进行中执行，**最后一个 assistant 回复的收尾部分可能不在快照里**；会话结束后重跑同一命令即可覆盖（会同时更新 `D2/README.md` 的事件数/统计）：

```bash
cd /Users/magicyoung/Project/Procurement-Exception-Agent
node AI会话记录/export-dsh-session.mjs \
  --session-id session-4678dfc5-5b4c-4533-9abd-ace050aff3ec \
  --out AI会话记录/D2
```

若需重新打包交付 zip（含更新后的 D2）：

```bash
cd /Users/magicyoung/Project/Procurement-Exception-Agent
rm -f Candidate-PEC-2026-11-08.zip
zip -r -q Candidate-PEC-2026-11-08.zip README.md pec-agent AI会话记录 \
  -x 'pec-agent/.git/*' 'pec-agent/.env' 'pec-agent/.dsh-home/*' 'pec-agent/runs/*' \
     '*/node_modules/*' '*.DS_Store' '*/.DS_Store' '*.log'
```

## 说明

- 导出器只 **读取** DSH 会话存储（`$DSH_HOME/sessions/<项目编码>/<会话ID>/session.v4.jsonl.zstd`），不修改原件；DSH 的 `.zstd` 是**多帧拼接**，普通 `zstd -d` 只能解第一帧，脚本按帧魔数切帧逐帧解压。
- 会话记录中不含 `.env`/API Key（全程未读取/未打印）；包含工作区文件内容与命令输出，均属本次交付材料。
- 同工作区另有 D1 的 fork 会话 `session-d654f611…`（`isSeeded=true`，本会话历史副本，非独立对话），未导出。
