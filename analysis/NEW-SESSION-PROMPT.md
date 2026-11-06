# 交接提示词：完成 PEC 采购异常处置 Agent 全部交付物

> 把本文件全文粘贴给新会话即可。目标：在 **2026-11-08 15:00（Asia/Shanghai）前**完成《业务案例实测任务书-候选人版-v3.1》的全部交付物，并在 Mac 上打包提交。用户只在最后验收；中途不要反复确认，按本提示自主推进，遇到真正阻塞再问。

## 0. 工作方式（必须遵守）

按 **plan-then-code + SDD（spec-driven development）** 执行：

1. **先读**材料与现状，不要先写业务代码。
2. 写 `pec-agent/plan.md`：目标、架构、模块边界、每个模块的 spec（输入/输出/错误/验收标准/测试向量）、数据口径与假设、风险、时间排期。
3. 写 `pec-agent/todo.md`：按依赖排序的任务清单，每项含「完成定义 + 验证命令」。
4. 再进入实现：**每个模块先写 spec/测试向量，再写实现，再验证**；一块一验，不要攒到最后。
5. 每完成一块更新 `todo.md`；每天收工在 `pec-agent` 仓库打 tag（`d1` / `d2`）。

## 1. 目录与仓库

- 工作区（材料，只读，不要改）：`/Users/magicyoung/Project/Procurement-Exception-Agent/`
  - `业务案例实测任务书-候选人版-v3.1.pdf`：题目（21 页）
  - `预装环境规格-v1.0.docx`：环境规格（7 个工具、1 份初始技能、profile、目录边界、自检）
  - `预装环境/`：预装插件源码、初始技能 `freight-anomaly-standard`、profile 样例、skill 模板
  - `实例数据包/`：6 份数据 + `db/pec.db` + schema/seed + `scripts/verify.py`
  - `analysis/taskbook.txt`：PDF 全文提取（`analysis/` 下还有两份既有分析，先读）
- 交付项目：`pec-agent/`（**独立 git 仓库**；DSH 的技能目录按“最近 .git 祖先”解析，所以必须在 `pec-agent/` 内有 `.git`，所有提交/tag 在 `pec-agent/` 内做）
  - `plugins/pec-tools/`：唯一允许改的业务代码；`package.json` 保持原样
  - `.dsh/skills/`：技能目录（已有初始 `freight-anomaly-standard`）
  - `db/pec.db`：数据副本；`dev/`：本地 DSH CLI、build/run 脚本、本地 profile overlay
  - `memory/`、`eval/`、`traces/`：待完成

## 2. 环境（已搭好，不要重装）

- DSH **0.2.1-rc.2** CLI：`pec-agent/dev/node_modules/.bin/dsh`（npm 安装，版本与预装插件声明的 `@deepseek-ai/dsh-tools` 一致）
- 本地 profile：`pec-agent/.dsh-home/profiles/headless`，已用 `cordis.patch.yml` 的 `- insert:` 挂载 `plugins/pec-tools/lib/index.js`
- API key：已写在 `pec-agent/.env`（**不要读取、不要打印、不要提交**）；headless 默认模型 `provider: deepseek-official, model: deepseek-flash`
- 插件依赖已装好：`better-sqlite3@11.10.0` 在 Node 24 下用
  `CXXFLAGS="-isystem $(xcrun --show-sdk-path)/usr/include/c++/v1"` 编译通过
- 技能根目录已隔离：`pec-agent/.dsh-home/profiles/headless/cordis.patch.yml` 里给 `skill-filesystem` 设了 `includeDefaultRoots: false` + `customSkillDirs: ['/…/pec-agent/.dsh/skills']`，headless 只看到项目自己的 `freight-anomaly-standard`，不会混入本机 `~/.agents/skills` 的 humanizer 等技能。
- 常用命令（都在 `pec-agent/` 内执行）：
  - 编译：`./dev/build.sh`（当前只编译旧入口，新增源文件要加进 entry 列表）
  - 单轮：`./dev/run-headless.sh --json "调用 pec.data.catalog 看看有哪些表"`
  - 多轮：`./dev/run-headless.sh --session-id <id> --json "第二轮任务"`
  - 身份：`PEC_USER_ID=U-02 ./dev/run-headless.sh ...`（缺省 `U-07`，T-001 buyer）
  - 隔离：`PEC_MEMORY_PATH=... PEC_AUDIT_PATH=... PEC_DB_PATH=...`
  - 直接调工具（不需要模型）：`node dev/test-tools.mjs`（19 项冒烟）或 `node -e "import('./plugins/pec-tools/lib/tools/xxx.js')..."`

## 3. 已完成（不要重做，除非测试证明有问题）

**环境与脚手架修复（记入 CHANGELOG）**
1. `output.schema` 在 0.2.1 必须显式 `additionalProperties: true/false`，否则插件导入即失败。
2. 插件入口必须 `export const inject = ['tools']`，否则 cordis 4 报 “cannot get property tools without inject”。
3. guard 真实签名是 `(exec) => string | undefined`（返回字符串即拒绝）；题面/profile 里的 `(call, next) => ({deny})` 在 0.2.1 上会抛错。
4. profile patch 在 0.2.1 上不能裸 `- name:`，要 `- insert: [...]`。
5. **工具名限制（重要）**：真实 DeepSeek Messages API 只接受 `^[a-zA-Z0-9_-]+$` 的工具名；题面/脚手架的 `order.lookup`、`pec.data.catalog` 这种带点命名会 400：`Invalid 'tools[1].name' ...`。已把全部工具名改为下划线（映射见 §3.1），skills/系统提示/文档必须用下划线名；交付 README 里保留“题面名 → 实现名”映射并说明这是环境适配。
6. `pec_data_catalog` 的 render 原来读 `v.tables`，而 execute 返回 `{data:{tables}}`，会报 `Cannot read properties of undefined (reading 'map')`；已改为读 `v.data.tables`。
7. 开发会话的环境可能已继承 `DSH_HOME=~/.dsh`，`dev/run-headless.sh` 已改为**强制** `export DSH_HOME="$ROOT/.dsh-home"`，否则会去读桌面版 profile。
8. 本机 macOS 27.3 上 `workspace-write` 的 bash 沙箱不可用（`sandbox-exec: sandbox_apply` 失败）。本地 eval 可设 `DSH_PERMISSION_MODE=danger-full-access`；更推荐在插件里用 `ctx.tools.restrict` 把 PEC agent 的工具面收紧到 pec 工具 + `skill`（同时满足“不得绕过工具直接读表”）。

### 3.0 考场基线 vs 本地现状（重要，第一天先对齐）

- **考场起点**：预装 `pec` profile 已加载插件，`index.ts` 已注册 7 个工具（catalog + 6 业务桩），`business.ts` 的 6 个 `execute` 全部抛 `NOT_IMPLEMENTED`；候选人从“填 execute / description / render”开始，**没有接线这一步**。
- **本地现状（接线已在上一会话完成，commit `e0855dd`）**：7 个工具已注册；5 个已实现（order_lookup / supplier_profile / pricing_quote / freight_calc / contract_search），`ticket_similar` 仍是 `NOT_IMPLEMENTED` 桩；`dev/test-tools.mjs` 19 项冒烟测试全过；跨租户 `POLICY_DENIED` + audit 已验证；`lib/` 已重新编译。
- **接线不是考试任务**，只是本地脚手架追平；新会话从“基线已验证”的状态直接开始业务实现。

### 3.1 工具命名映射（题面名 → 实现名）

```
pec.data.catalog → pec_data_catalog
order.lookup → order_lookup
supplier.profile → supplier_profile
pricing.quote → pricing_quote
freight.calc → freight_calc
contract.search → contract_search
ticket.similar → ticket_similar
```
新增工具也一律用下划线：`advice_card`、`memory_recall`、`memory_remember`、`memory_forget`、`skill_write`。

**已写代码**（`pec-agent/plugins/pec-tools/src/`）
- `policy/identity.ts`：`PEC_USER_ID` → `users` 表解析 tenantId/role（进程可信输入，模型不可伪造；缺省 U-07）
- `policy/audit.ts`：JSONL 审计（`PEC_AUDIT_PATH`，默认 `./runs/audit.jsonl`）
- `policy/guard.ts`：同步 guard，拦截伪造 `tenantId` 参数并留痕
- `policy/masking.ts`：角色矩阵、手机号/姓名掩码、合同原文访问级别
- `core/money.ts`：BigInt 4 位定点 + HALF_UP（无 decimal.js）+ 日期差
- `core/provenance.ts`：provenance 结构与 render 用的 `[来源: table#rowId]`
- `tools/order-lookup.ts`、`tools/supplier-profile.ts`、`tools/pricing-quote.ts`、`tools/freight-calc.ts`、`tools/contract-search.ts`：已实现，含租户校验、provenance、角色脱敏、FTS5+同义词回退
- `memory/store.ts`：会话/用户记忆存储、TTL（7/90 天）、白名单、冲突 history
- `errors.ts` 已重写（四种错误码 + `E_DIV_ZERO` 作为 INVALID_ARGUMENT 的 reason）
- `db.ts` 支持 `PEC_DB_PATH`
- `index.ts` 已加 `inject = ['tools']`
- `dev/build.sh`（esbuild）、`dev/run-headless.sh`、`dev/pec.local.yml`、`.env.example`

**已验证**：
- `./dev/run-headless.sh --json "调用 pec_data_catalog 看看数据集里有哪些表"` 成功：1 次 `tool_call`、6 张表行数、`step_end.usage` 有 token。
- 工具接线完成（commit `e0855dd`）：`node dev/test-tools.mjs` 19 项全过；5 个工具返回真实数据；`ticket_similar` 仍是桩。
- 跨租户：`PEC_USER_ID=U-08` 查 `PO-20261013-0042` → `POLICY_DENIED`，`audit.jsonl` 有 `cross-tenant-order` 记录；U-08 查自己租户订单正常。
- 端到端：headless 调 `order_lookup` → `tool_result` 带 `[来源: orders#...]` → `final` 引用来源。
- `pricing_quote` 57,600.00 / 税额 7,488.00 / 恰好 50,000.00；`freight_calc` 4 / 340.00 / 0.57、0.40→1 / 85.00、qty=0 → E_DIV_ZERO；`contract_search` CL-07 3‰、短词“运费承担”回退命中、SUP-1047 无合同返回未检索到。

**注意**：`tools/business.ts` 仍是**旧桩**（只是名字已改成下划线），`index.ts` 仍只注册旧桩；`lib/` 也是旧桩编译产物。需要把 `business.ts` 改为 re-export 新工具、`index.ts` 注册全部工具、`dev/build.sh` 加入新文件。

## 4. 待完成（按这个顺序）

1. **基线验证（5 分钟，然后开始业务实现）**：
   - `./dev/build.sh && node dev/test-tools.mjs`（应 19 passed / 0 failed）；
   - `./dev/run-headless.sh --json "调用 order_lookup 查询订单 PO-20261013-0042 的承诺交期、实际交期、延迟天数和状态；最后一行必须写出数据来源（[来源: 表名#行id] 格式）"`，确认 `tool_call` + `[来源: orders#PO-20261013-0042]`；
   - 若失败，先修基线，不要继续往下做。
2. `tools/ticket-similar.ts`：按异常类型 + 供应商 + 金额区间召回历史工单，返回相似度/动作/耗时，带 provenance。
3. `tools/advice-card.ts`：建议卡工具（action/params/amount/evidence/risks/confidence/needHuman）；校验 R7 审批门槛（<5 万自动、5–20 万主管、≥20 万总监+财务、黑名单一律人工）、证据 ref 必须存在、规则不过抛错；render 卡片。
4. 记忆工具与注入：`memory.recall` / `memory.remember` / `memory.forget`；用 `ctx.systemPrompt.section({ text: (ctx) => ... })` 每轮注入 3–5 条（0.2.1 的 `text` 支持函数）；`inject` 需覆盖 `systemPrompt` 或用 `ctx.get('systemPrompt')` 可选挂载。
5. 技能：手写 `.dsh/skills/delay-small-standard/SKILL.md`；实现 `skill.write` 工具（frontmatter 校验 + 护栏/反例必填 + 落盘 `.dsh/skills/<name>/SKILL.md`）；用一次真实的成功对话让 Agent 生成 `stock-replenish`（保存 trace）。
6. 评测：`eval/golden_set.jsonl` 12 条（5 正常/3 边界/2 对抗/2 记忆技能）+ 专项集（记忆 5 对、越权矩阵、技能命中、A/B 8 条）；`eval/run.sh` + `eval/collect.mjs`；`report.md` + `ab_report.md` + 门禁（不达标非 0 退出）。
7. A/B：8 条同租户同类工单（`status=DELAYED and amount<50000 and supplier.blacklisted=0 and tenant=T-001`），A 组移走 `.dsh/skills`，B 组保留；同一模型/数据；主指标用**工具调用步数**（`tool_call` 事件数），token 用 `status.step_end.usage`（可能缺省，需容错）；结论一致率逐位比对。
8. `traces/` 四类：qa / memory / skill-write / skill-hit。
9. 文档：`design.md`、`README.md`（三段演示命令）、`ARCHITECTURE.md`、`CHANGELOG.md`（含 CR#1）、`defense/defense.md`；最终打包 zip。
10. 失败归因 1 例 + 修复前后对照；CR#1 演练；干净环境复现。

## 5. 已定设计决策（不要推翻）

- **身份**：平台没有 tenantId/userId/role 服务；用 `PEC_USER_ID`（进程环境，可信）+ `users` 表解析；guard/tools 只信 `exec.agent?.session?.id` 与 identity，不读模型传的 userId/role；跨租户一律 `POLICY_DENIED` + 审计（不是 NOT_FOUND）。
- **provenance 必须写进 `render()` 文本**：模型只看得见 render，`output.schema`/canonical value 不上 wire；统一格式 `[来源: orders#PO-...]`。
- **十进制**：BigInt 定点（`core/money.ts`）；R1/R2/R3 逐位；`qty=0` 的 `E_DIV_ZERO` 放在 INVALID_ARGUMENT 的 message/detail 里。
- **合同检索**：FTS5 trigram 只支持 ≥3 字；短词/业务词用同义词 + LIKE 回退（如 运费→运输费用、质保→质保期、付款→支付货款、延迟→延迟交货）；无命中明确返回“未检索到”，不得引用。
- **权限/脱敏**：contacts 对非 ● 角色返回掩码并审计；合同原文 buyer/manager/auditor 不可见（只给结构化摘要）、risk 脱敏、finance/admin 原文；数据没有 cost_price 字段，不伪造成本价（记录假设）。
- **建议卡**：必须由工具统一校验 R7/黑名单/证据存在性并 render；模型不能绕过规则。
- **A/B 主指标**：工具调用步数（技能文本会抬高 token，token 不一定降 30%）；步数来自 `tool_call` 事件（必须 native executor，PTC 会塌缩）。
- **扩展点**：CR#1 只改工具注册/策略配置，不改执行链路；CHANGELOG 写影响面与回归。
- **税率**：数据无税率，`pricing.quote` 税额按 `PEC_VAT_RATE`（默认 0.13）并标注 `assumption:`。
- **工具名**：一律用 `[a-zA-Z0-9_-]` 下划线命名（原因见 §3 第 5 条）；skills/系统提示/评测断言都用实现名，README 保留映射表。
- **工具面收紧（已验证可用）**：PEC agent 只应看到 6 业务工具 + catalog + 建议卡 + memory/skill 工具；实现方式：
  - `ctx.tools.restrict({ allow: [...] })` 在 0.2.1-rc.2 存在（`dsh-tools/lib/types/index.d.ts:645`、`lib/index.js:2991`），但**只能在 agent 作用域**调用；在插件全局 ctx 调用会抛 `tools.restrict() requires a scoped context (agent.ctx)`。
  - 正确做法：插件 `apply` 里 `ctx.on('agent/created', ({ agent }) => agent.ctx.tools.restrict({ allow: [...] }))`（代码在 `src/policy/tool-surface.ts`，已接线）。
  - `allow` 必须包含 7 个业务工具 + `skill`；新增工具实现后要同步加进去（未知名字会让 restrict 抛错）。
  - 已验证：headless 里问“列出可用工具名”，模型只列出 `contract_search/freight_calc/order_lookup/pec_data_catalog/pricing_quote/skill/supplier_profile/ticket_similar`，`runs/audit.jsonl` 有 `tool-surface.restricted` 记录；bash/read/write/grep 已不可见。

## 6. 关键口径与已知陷阱（写进 design.md / CHANGELOG）

- 锚点：`PO-20261013-0042` 金额 57,600.00、计费体积 4、运费 340.00、计件 0.57、延迟 13 天；CL-07 违约金 3‰/日、上限 5%；13 天赔付 2,246.40（上限 2,880.00，未触顶）。
- `PO-20261014-0055` 金额恰好 50,000.00 → R7 走**采购主管**（不是自动）；`PO-20261015-0066` 体积 0.40 → 计费体积 1、运费 85.00（不是 34.00）；`PO-20261010-0099` qty=0 → `E_DIV_ZERO`，不得返回 0。
- 阶梯价边界：`SKU-88205` 99/100（68.00/59.50）、`SKU-88214` 499/500（10.50/9.00）有真实成对订单。
- 半值进位：85/200 = 0.425，库值 0.43；JS `(85/200).toFixed(2)` 给 "0.42"，必须用 BigInt 定点。
- A/B SQL 实际命中 31 条，但**不带租户过滤**（T-001 22 / T-002 4 / T-003 5），直接 `limit 8` 会混租户；必须加 `tenant_id='T-001'`。
- `SUP-1047` 无任何合同（合同未命中用例）；T-003 只有 payment 条款、无 penalty；28 条工单里 16 条集中在黑名单订单 `PO-20260917-0129`（不适合做标准技能命中）。
- README 说 T-001 80 单，实际 79；`delivered_at` 为空只有 1 条（0099）。
- 题面缺口：R8 汇率（无币种/汇率字段）、R11 成本价（无字段）、R9 风险分（无字段，本实现自定公式）、R10 等值边界（0 样本）、R7 ≥20 万（0 样本）。
- 题面内部冲突：技能 A `whenToUse` 写金额 <5 万，但示例用 57,600 的 0042；建议卡 `newDate=2026-10-28` 与“实际交期+14 天=11-16”冲突；样例技能 `freight-anomaly-standard` 的“运费承担”在 FTS/LIKE 都命中不了（要改为“运输费用”）。
- 12 条评测集只覆盖“回答准确率”；记忆命中率/越权拦截率/技能复用率/提效都需要**额外专项集**，不要只用 12 条。
- 工具名带点会被真实 DeepSeek API 400；已统一改下划线（§3.1）。
- `dev/run-headless.sh` 必须强制 `DSH_HOME=$ROOT/.dsh-home`，否则会误用桌面版 `~/.dsh` 的 profile。
- 本机 bash 工具在 workspace-write 下不可用；本地调试可 `DSH_PERMISSION_MODE=danger-full-access`，但交付的 PEC agent 已通过工具面收紧避免依赖 shell。
- **Fixed 的格式化陷阱（已踩过一次）**：`core/money.ts` 的 Fixed 始终是 4 位定点，`fixedToString()` 内部才做取整；计算中间值不要再 `rescale(v,2)`，否则会二次缩放（57,600 变 576）。新增金额逻辑后务必跑 `dev/test-tools.mjs` 的金额断言。

## 7. 验收指标与交付物（任务书 §8.1/8.2）

指标：回答准确率 ≥90%、引用可溯率 100%、记忆命中率 ≥80%、技能复用率 ≥60%、提效 ≥30%、越权拦截率 100%。

交付结构：

```
pec-agent/
├── plugins/pec-tools/         # 6 个 defineTool + guard + render
├── .dsh/skills/               # delay-small-standard（手写）/ stock-replenish（沉淀）
├── memory/                    # store.json + extract.md
├── eval/                      # golden_set.jsonl / run.sh / collect.mjs / report.md / ab_report.md
├── traces/                    # qa / memory / skill-write / skill-hit
└── design.md / README.md / ARCHITECTURE.md / CHANGELOG.md / defense/defense.md
```

最终打包 `姓名-PEC-日期.zip`（先用 `Candidate` 占位并在 README 提醒用户改名）；README 给三段演示命令（单轮问答、多轮记忆、技能命中）。

## 8. CR#1 与答辩

- 线下没有官方 CR#1 宣读；自行设计一个等价变更演练（例如新增“金额 ≥10 万需财务会签”或给 order.lookup 加物流商字段），要求同时影响工具/技能/记忆三层，用 45 分钟落地、既有评测全部回归、新增 ≥2 条用例，并在 CHANGELOG 写“这是自拟 CR，不是官方 CR#1”。
- 准备 `defense/defense.md`：陈述提纲（工具、记忆、技能、提效数字怎么来的）、追问清单（重点：A/B 数字、技能护栏、guard 路径）、现场改码演练（随机改一处规则并跑回归）。

## 9. 会话导出

本会话（新会话）是**第一天**的 AI 会话记录；第二天再开一条会话继续，用户会分别导出这两条会话作为交付物。此前的讨论会话不计入交付。请在关键节点保留可复制的命令与结果，结束时提醒用户导出本会话，并把代表性 run 复制到 `traces/`。

## 9.1 插件到底怎么“加载”（新会话第一天要能解释清楚）

DSH 里没有“图形化开关插件”这一步，加载 = **启动一个 profile，而该 profile 的 patch 层里有一条 insert 指向插件入口**：

1. `plugins/pec-tools/src/*.ts` 先编译成 `plugins/pec-tools/lib/*.js`（`dev/build.sh`，esbuild）。
2. `plugins/pec-tools/package.json` 的 `main` 是 `lib/index.js`。
3. 本地 headless profile 的 patch 层 `pec-agent/.dsh-home/profiles/headless/cordis.patch.yml` 里有：
   ```yaml
   - insert:
       - id: pec-tools
         name: '/绝对路径/pec-agent/plugins/pec-tools/lib/index.js'
   ```
4. `./dev/run-headless.sh` 做两件事：`cd pec-agent`、`export DSH_HOME=pec-agent/.dsh-home`，然后 `dsh --profile headless ...`。DSH 组合 `dsh-base → dsh-headless → profile patch`，loader 按第 3 条的路径 import `lib/index.js`，调用 `apply(ctx)`，注册 6 个业务工具 + catalog + guard。
5. 验证：`./dev/run-headless.sh --json "调用 pec.data.catalog 看看有哪些表"`，在输出里找 `tool_call`（tool=`pec.data.catalog`）和 `tool_result`（6 张表行数）。

注意：改 `src/*.ts` 后必须重跑 `./dev/build.sh`，否则加载的还是旧 `lib/`。`lib/` 不作为手写源码维护。

## 10. 第一步动作

1. 读 `analysis/taskbook.txt`、`analysis/dsh-api-notes.md`、`analysis/data-audit.md` 和现有源码。
2. 在 `pec-agent/` 下跑 `./dev/build.sh`，再跑 `./dev/run-headless.sh --json "调用 pec.data.catalog 看看有哪些表"` 确认环境与 key 可用。
3. 写 `plan.md` 和 `todo.md`（先落盘，不要等用户回复）。
4. 从“待完成”第 1 项开始，按 SDD 推进；每完成一项更新 todo.md 并验证。

## 11. 约束

- 不改 DSH 内核/其他插件/profile 原件/交付物里的 `package.json`；只改 `plugins/pec-tools/src/**`、`.dsh/skills/**` 以及 memory/eval/traces/docs。
- 不新增运行时依赖（没有 decimal.js），只用 Node 标准库 + better-sqlite3 + dsh-tools。
- 不修改 `预装环境/`、`实例数据包/` 原件；不把 `.env`、`node_modules`、`.dsh-home` 提交/打包。
- 每完成一块立即验证；不要攒到最后。
