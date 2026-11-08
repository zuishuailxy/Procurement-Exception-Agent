# PEC 采购异常处置 Agent · 交付包说明

> 候选人交付物：基于 **DSH 0.2.1-rc.2** 的采购异常处置 Agent（插件 `pec-agent/plugins/pec-tools` + 技能 + 记忆 + 评测 + 答辩材料）。
> 六项指标全部达标：回答准确率 100% · 引用可溯 100% · 记忆命中 100% · 技能复用 100% · **提效 65.7%** · 越权拦截 100%（证据：`pec-agent/eval/report.md`）。

## 包内容

```
Candidate-PEC-2026-11-08.zip
├── README.md                    # 本文件（交付入口）
├── pec-agent/                   # 交付代码与文档（独立 git 仓库，含 d1/d2 tag；.git 不入包）
│   ├── plugins/pec-tools/       # 12 个业务/记忆/技能工具（defineTool + guard + render + provenance）
│   ├── .dsh/skills/             # 3 份 SKILL.md（手写 delay-small-standard / Agent 沉淀 stock-replenish / 样例）
│   ├── eval/                    # golden_set 15 条 + 专项集 + A/B + 门禁 + 失败归因 + 最终报告
│   ├── traces/                  # 五类真实 headless 事件流快照
│   ├── defense/defense.md       # 答辩：20 分钟提纲 + 30 条追问 + 现场改码预案
│   └── README / plan / todo / design / ARCHITECTURE / CHANGELOG
└── AI会话记录/                   # AI 会话导出（D1 已导出；D2 会话结束后按该目录 README 导出）
```

## 三段演示命令（题面 §8.2：单轮问答 / 多轮记忆 / 技能命中）

```bash
cd pec-agent
./dev/setup-profile.sh          # 首次运行：生成本地 headless profile（换机/解压后执行）
./dev/build.sh                  # 编译插件（profile 加载 lib/index.js）
node dev/test-tools.mjs         # 工具级冒烟：期望 136 passed / 0 failed

# ① 单轮问答：订单延迟 → 条款 → 建议卡（含来源）
./dev/run-headless.sh --json "处理订单 PO-20261013-0042 的交期延迟：先查订单事实，再检索该供应商的违约金条款，最后必须调用 advice_card 工具给出建议卡与审批路径（金额 ≥5 万时卡片强制需人工确认，但仍要出卡）"

# ② 多轮记忆：第 2 轮不再重复询问订单号（一键脚本，含自动断言）
./dev/demo-memory.sh

# ③ 技能命中：不点名技能，由 catalog 自主命中 delay-small-standard（3 步出卡）
./dev/run-headless.sh --json "PO-20260906-0114 延迟，按标准流程处理，最后给出建议卡"
```

预期关键输出、手动两轮 session 复用命令、干净环境复现步骤见 **`pec-agent/README.md` §1/§2/§8**。
完整回归：`cd pec-agent && bash eval/run.sh && node eval/collect.mjs --gate`（期望 golden 15/15、六指标全绿、退出码 0）。

## 前置与说明

- **API Key**：`.env` 不入包；复制 `pec-agent/.env.example` 为 `.env` 并填入 `DEEPSEEK_API_KEY`。
- **依赖**：`node_modules` 不入包，使用预装环境提供的 DSH/依赖（`pec-agent/dev/node_modules`、`pec-agent/plugins/pec-tools/node_modules`）。
- **数据**：`pec-agent/db/pec.db` 只读副本；运行产物（`runs/`、`.dsh-home/`、`memory/store.json` 运行值）不入包。
- **包名**：`Candidate-PEC-2026-11-08.zip`，提交前请替换为真实姓名。
- **会话导出**：D1/D2 均已导出（D2 为会话进行中快照）。会话结束后可重跑 `node AI会话记录/export-dsh-session.mjs --session-id session-4678dfc5-5b4c-4533-9abd-ace050aff3ec --out AI会话记录/D2` 覆盖末轮，再按 `AI会话记录/README.md` 重新打包。
