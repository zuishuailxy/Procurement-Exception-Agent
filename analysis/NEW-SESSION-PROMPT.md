# 交接提示词 v2：完成 PEC 采购异常处置 Agent 全部交付物

> 目标：在 **2026-11-08 15:00（Asia/Shanghai）前**完成《业务案例实测任务书-候选人版-v3.1》全部交付物，在 Mac 上打包提交。**每完成 `todo.md` 里的一个条目，必须停下来向用户汇报并等确认**（用户要能理解改了什么）；不要一次性连做多块。
>
> 本会话是**第一天**的 AI 会话记录（要导出成交付物）；上一轮讨论会话不计入。

## 0. 工作方式：plan-then-code + SDD

1. **先读**材料与现状，不要先写业务代码。
2. 写 `pec-agent/plan.md`：目标、架构、模块边界、每个模块的 spec（输入/输出/错误/验收标准/测试向量）、数据口径与假设、风险、时间排期。
3. 写 `pec-agent/todo.md`：按依赖排序的任务，每项含「完成定义 + 验证命令」。
4. 再实现：**每个模块先写 spec/测试向量，再写代码，再验证**；一块一验。
5. 每完成一块更新 `todo.md`，**按 §0.1 模板向用户汇报并等确认**；每天收工在 `pec-agent` 仓库打 tag（`d1` / `d2`）。

## 0.1 每个 todo 完成后的确认流程（必须遵守）

每完成 `todo.md` 里的一个条目，**停下来**，按下面模板向用户汇报，等用户确认后再做下一项；禁止连续做多个条目、禁止“等最后一起汇报”。

汇报模板（每条都要写，用户要用它理解改动）：

1. **完成项**：`todo.md` 第 N 项「…」；对应题面/验收项（R1–R14、六项指标、§8.3 第几条）。
2. **改了什么（文件级）**：
   - `路径/文件.ts`：新增/修改了什么（一句话）+ 关键行为变化；
   - 有 schema/配置/接口变化时贴最小 diff 或函数签名；
   - 如新增文件，说明它在架构里的位置。
3. **为什么这么改**：对应哪条业务规则/评测指标；有没有替代方案、为什么没选。
4. **怎么验证**：执行的命令 + 关键输出（3–10 行），说明 PASS/FAIL；如果是 headless 跑，贴 `tool_call` / `final` 的关键片段。
5. **对六项指标的影响**：准确率 / 引用可溯 / 记忆命中 / 技能复用 / 提效 / 越权拦截，哪一项受影响、当前证据是什么。
6. **风险、假设、未决项**：题面缺口、口径冲突、需要用户拍板的地方。
7. **下一步**：`todo.md` 下一项是什么、预计耗时。

用户确认方式：回复「继续」/「改…」/「先解释…」。**未确认前不要开始下一项**；用户不在线就把汇报留在会话里等回复，不要自行推进。

同时更新：`todo.md` 勾选状态；影响交付口径的写进 `CHANGELOG.md`；必要时在 `design.md` 补决策记录。

## 1. 目录与仓库

- 工作区（材料，只读）：`/Users/magicyoung/Project/Procurement-Exception-Agent/`
  - `业务案例实测任务书-候选人版-v3.1.pdf`（题目，21 页）
  - `预装环境规格-v1.0.docx`（环境规格：7 个工具、初始技能、profile、目录边界、自检）
  - `预装环境/`（预装插件源码、初始技能、profile 样例、skill 模板）
  - `实例数据包/`（6 份数据 + `db/pec.db` + schema/seed + `scripts/verify.py`）
  - `analysis/taskbook.txt`、`analysis/dsh-api-notes.md`、`analysis/data-audit.md`（先读）
- 交付项目：`pec-agent/`（**独立 git 仓库**；DSH 技能目录按“最近 `.git` 祖先”解析，所以 `.git` 必须在 `pec-agent/` 内）
  - 当前 HEAD：`9209145`（在 `e0855dd` 基线之上清了 memory seed）；工作区干净
  - `plugins/pec-tools/`：唯一允许改的业务代码；`package.json` 保持原样
  - `.dsh/skills/`：技能目录（已有初始 `freight-anomaly-standard`）
  - `db/pec.db`、`dev/`、`memory/`、`eval/`、`traces/`

## 2. 环境（已就绪，不要重装）

- DSH **0.2.1-rc.2** CLI：`pec-agent/dev/node_modules/.bin/dsh`（与预装插件声明的 `@deepseek-ai/dsh-tools` 版本一致）
- headless profile：`pec-agent/.dsh-home/profiles/headless`，`cordis.patch.yml` 里已 `- insert:` 挂载 `plugins/pec-tools/lib/index.js`，并给 `skill-filesystem` 设了 `includeDefaultRoots: false` + `customSkillDirs`（只扫描 `pec-agent/.dsh/skills`，不会被本机 `humanizer` 等技能污染）
- API key：已写在 `pec-agent/.env`（**不要读取、不要打印、不要提交**）；默认模型 `provider: deepseek-official, model: deepseek-flash`
- 依赖已装好：`better-sqlite3@11.10.0` 在 Node 24 下用
  `CXXFLAGS="-isystem $(xcrun --show-sdk-path)/usr/include/c++/v1"` 编译通过
- 常用命令（都在 `pec-agent/` 内）：
  - 编译：`./dev/build.sh`（esbuild；**新增源文件必须同时加进 build.sh 的 entry 列表**）
  - 工具级冒烟（不需要模型）：`node dev/test-tools.mjs`（当前 19 passed）
  - 单轮：`./dev/run-headless.sh --json "…"`
  - 多轮：`./dev/run-headless.sh --session-id <id> --json "…"`
  - 身份：`PEC_USER_ID=U-02 ./dev/run-headless.sh …`（缺省 `U-07`，T-001 buyer；U-08 = T-002 buyer）
  - 隔离：`PEC_MEMORY_PATH=… PEC_AUDIT_PATH=… PEC_DB_PATH=…`

## 3. 已完成（不要重做，除非测试证明有问题）

### 3.1 环境/脚手架修复（记入 CHANGELOG）

1. `output.schema` 在 0.2.1 必须显式 `additionalProperties: true/false`，否则插件导入失败。
2. 插件入口必须 `export const inject = ['tools']`，否则 cordis 4 报 “cannot get property tools without inject”。
3. guard 真实签名是 `(exec) => string | undefined`（返回字符串即拒绝）；题面 `(call, next) => ({deny})` 在 0.2.1 上会抛错。
4. profile patch 不能裸 `- name:`，要 `- insert: [...]`。
5. **工具名限制**：真实 DeepSeek Messages API 只接受 `^[a-zA-Z0-9_-]+$`；带点的 `order.lookup` 会 400 `Invalid 'tools[1].name'`。全部工具已改下划线（映射见 §3.3），skills/提示/断言都用实现名；README 保留映射表。
6. `pec_data_catalog` 的 render 原来读 `v.tables`，execute 返回 `{data:{tables}}`，已修成 `v.data.tables`。
7. `DSH_HOME` 可能从开发会话继承 `~/.dsh`；`dev/run-headless.sh` 已强制 `export DSH_HOME="$ROOT/.dsh-home"`。
8. 本机 macOS 27.3 上 `workspace-write` bash 沙箱不可用；PEC agent 已用工具面收紧规避，不依赖 shell。

### 3.2 已实现并验证

- `policy/identity.ts`：`PEC_USER_ID` → `users` 表解析 tenantId/role（进程可信输入，模型不可伪造；缺省 U-07）
- `policy/audit.ts`：JSONL 审计（`PEC_AUDIT_PATH`，默认 `./runs/audit.jsonl`）
- `policy/guard.ts`：同步 guard，拦截伪造 `tenantId` 参数并留痕
- `policy/masking.ts`：角色矩阵、手机号/姓名掩码、合同原文访问级别
- `policy/tool-surface.ts`：`agent/created` → `agent.ctx.tools.restrict({ allow })`，把 PEC agent 工具面收紧到 7 业务工具 + `skill`（bash/read/write/grep 不可见；audit 有 `tool-surface.restricted`）
- `core/money.ts`：BigInt 4 位定点 + HALF_UP（无 decimal.js）+ 日期差
- `core/provenance.ts`：provenance 与 render 用的 `[来源: table#rowId]`
- `tools/`：`order_lookup`、`supplier_profile`、`pricing_quote`、`freight_calc`、`contract_search` 已实现（租户校验、provenance、角色脱敏、FTS5+同义词回退）；`ticket_similar` 仍是 `NOT_IMPLEMENTED` 桩
- `memory/store.ts`：会话/用户记忆存储、TTL（7/90 天）、白名单、冲突 history
- `errors.ts`（四种错误码 + `E_DIV_ZERO` reason）、`db.ts`（`PEC_DB_PATH`）、`index.ts`（inject）
- `dev/build.sh`、`dev/run-headless.sh`、`dev/test-tools.mjs`、`dev/pec.local.yml`、`.env.example`
- 接线完成：`tools/business.ts` re-export 新工具；`index.ts` 注册 catalog + 6 工具；`lib/` 已重编译

### 3.3 工具命名映射（题面名 → 实现名）

```
pec.data.catalog → pec_data_catalog
order.lookup     → order_lookup
supplier.profile → supplier_profile
pricing.quote    → pricing_quote
freight.calc     → freight_calc
contract.search  → contract_search
ticket.similar   → ticket_similar
```

新增工具一律下划线：`advice_card`、`memory_recall`、`memory_remember`、`memory_forget`、`skill_write`。

### 3.4 已验证的证据

- `node dev/test-tools.mjs`：**19 passed / 0 failed**
- catalog：6 张表行数；headless 1 次 `tool_call`、`step_end.usage` 有 token
- order_lookup：0042 延迟 13 天 + provenance；端到端 `final` 带 `[来源: orders#PO-20261013-0042]`
- pricing_quote：57,600.00 / 税额 7,488.00 / 恰好 50,000.00
- freight_calc：4 / 340.00 / 0.57；0.40→1 / 85.00；qty=0 → E_DIV_ZERO
- contract_search：CL-07 3‰；“运费承担”短词回退命中；SUP-1047 无合同返回未检索到
- supplier_profile：buyer 联系人脱敏
- 跨租户：`PEC_USER_ID=U-08` 查 0042 → `POLICY_DENIED` + audit `cross-tenant-order`

## 4. 待完成（按顺序）

1. **基线验证（5 分钟）**：`./dev/build.sh && node dev/test-tools.mjs`（19 passed）；`./dev/run-headless.sh --json "调用 order_lookup 查询订单 PO-20261013-0042 的承诺交期、实际交期、延迟天数和状态；最后一行写数据来源"`。失败先修基线。
2. `tools/ticket-similar.ts`：按异常类型 + 供应商 + 金额区间召回历史工单，返回相似度/动作/耗时/是否人工改判，带 provenance。
3. `tools/advice-card.ts`（`advice_card`）：建议卡（action/params/amount/evidence/risks/confidence/needHuman）；校验 R7（<5 万自动、5–20 万主管、≥20 万总监+财务、黑名单一律人工）、证据 ref 必须存在、规则不过抛错；render 卡片。
4. 记忆工具与注入：`memory_recall` / `memory_remember` / `memory_forget`；用 `ctx.systemPrompt.section({ text: (ctx) => … })` 每轮注入 3–5 条（0.2.1 的 text 支持函数）；inject 覆盖 `systemPrompt` 或用 `ctx.get('systemPrompt')` 可选挂载。
5. 技能：手写 `.dsh/skills/delay-small-standard/SKILL.md`；实现 `skill_write` 工具（frontmatter 校验 + 护栏/反例必填 + 落盘）；用一次真实成功对话让 Agent 生成 `stock-replenish`（保存 trace）。
6. 评测：`eval/golden_set.jsonl` 12 条（5 正常/3 边界/2 对抗/2 记忆技能）+ 专项集（记忆 5 对、越权矩阵、技能命中、A/B 8 条）；`eval/run.sh` + `eval/collect.mjs`；`report.md` + `ab_report.md` + 门禁（不达标非 0 退出）。
7. A/B：8 条同租户同类工单（`status='DELAYED' and amount<50000 and supplier.blacklisted=0 and tenant='T-001'`），A 组移走 `.dsh/skills`，B 组保留；同模型/数据；主指标**工具调用步数**（`tool_call` 事件数），token 用 `status.step_end.usage`（可能缺省，容错）；结论一致率逐位比。
8. `traces/` 四类：qa / memory / skill-write / skill-hit。
9. 文档：`design.md`、`README.md`（三段演示命令）、`ARCHITECTURE.md`、`CHANGELOG.md`（含 CR#1）、`defense/defense.md`；最终打包 zip。
10. 失败归因 1 例 + 修复前后对照；CR#1 演练；干净环境复现。

## 5. 已定设计决策（不要推翻）

- **身份**：平台没有 tenantId/userId/role 服务；`PEC_USER_ID`（进程环境，可信）+ `users` 表解析；guard/tools 只信 `exec.agent?.session?.id` 与 identity，不读模型传的 userId/role；跨租户 `POLICY_DENIED` + 审计（不是 NOT_FOUND）。
- **provenance 必须写进 `render()`**：模型只看得见 render；`output.schema`/canonical value 不上 wire；统一 `[来源: orders#PO-...]`。
- **十进制**：BigInt 定点（`core/money.ts`）；Fixed 始终 4 位，`fixedToString()` 内部才取整；中间值不要再 `rescale`（踩过：57,600 → 576）。
- **合同检索**：FTS5 trigram 只支持 ≥3 字；短词/业务词用同义词 + LIKE 回退；无命中明确“未检索到”，不得引用。
- **权限/脱敏**：contacts 对非 ● 角色掩码并审计；合同原文 buyer/manager/auditor 不可见（只给结构化摘要）、risk 脱敏、finance/admin 原文；数据没有 cost_price 字段，不伪造（记录假设）。
- **建议卡**：必须由工具统一校验 R7/黑名单/证据存在性；模型不能绕过。
- **A/B 主指标**：工具调用步数（技能文本会抬高 token）；必须 native executor（PTC 会塌缩）。
- **扩展点**：CR#1 只改工具注册/策略配置，不改执行链路；CHANGELOG 写影响面与回归。
- **税率**：数据无税率，按 `PEC_VAT_RATE`（默认 0.13）并标注 `assumption:`。
- **工具名**：一律下划线；新增工具必须同步 `policy/tool-surface.ts` 的 allow 列表（未知名字会让 restrict 抛错）。
- **工具面收紧**：`ctx.tools.restrict` 只能 agent 作用域调；已在 `policy/tool-surface.ts` 用 `agent/created` + `agent.ctx.tools.restrict({ allow })` 实现。

## 6. 关键口径与陷阱（写进 design.md / CHANGELOG）

- 0042：金额 57,600.00、计费体积 4、运费 340.00、计件 0.57、延迟 13 天；CL-07 违约金 3‰/日、上限 5%；13 天赔付 2,246.40（上限 2,880.00，未触顶）。
- 0055：金额恰好 50,000.00 → R7 走**采购主管**（不是自动）；0066：体积 0.40 → 计费体积 1、运费 85.00（不是 34.00）；0099：qty=0 → E_DIV_ZERO，不得返回 0。
- 阶梯价边界：SKU-88205 99/100（68.00/59.50）、SKU-88214 499/500（10.50/9.00）有真实成对订单。
- 半值进位：85/200 = 0.425，库值 0.43；JS `(85/200).toFixed(2)` = "0.42"。
- A/B SQL 实际 31 条，但**不带租户过滤**（T-001 22 / T-002 4 / T-003 5）；必须加 `tenant_id='T-001'`。
- SUP-1047 无合同（未命中用例）；T-003 只有 payment、无 penalty；28 条工单里 16 条集中在黑名单订单 0129（不适合标准技能命中）。
- README 说 T-001 80 单，实际 79；`delivered_at` 为空只有 1 条（0099）。
- 题面缺口：R8 汇率（无币种/汇率字段）、R11 成本价（无字段）、R9 风险分（无字段，自定公式）、R10 等值边界（0 样本）、R7 ≥20 万（0 样本）。
- 题面冲突：技能 A `whenToUse` 写 <5 万但示例用 57,600 的 0042；建议卡 newDate=10-28 与“实际交期+14 天=11-16”冲突；样例技能“运费承担”命中不了（要改“运输费用”）。
- 12 条只覆盖“回答准确率”；记忆/越权/技能复用/提效都要**额外专项集**。
- 工具名带点会被真实 DeepSeek API 400；已统一下划线。
- `dev/run-headless.sh` 必须强制 `DSH_HOME=$ROOT/.dsh-home`。
- 本机 bash 在 workspace-write 下不可用；PEC agent 已通过工具面收紧规避。
- Fixed 格式化：中间值不要二次 rescale；新增金额逻辑后跑 `dev/test-tools.mjs`。

## 7. 验收指标与交付物（任务书 §8.1/8.2）

指标：回答准确率 ≥90%、引用可溯率 100%、记忆命中率 ≥80%、技能复用率 ≥60%、提效 ≥30%、越权拦截率 100%。

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

- 线下没有官方 CR#1；自行设计等价变更（如新增“金额 ≥10 万需财务会签”或给 order_lookup 加物流商字段），同时影响工具/技能/记忆三层，45 分钟落地、既有评测全回归、新增 ≥2 条用例，CHANGELOG 注明“自拟 CR，不是官方 CR#1”。
- `defense/defense.md`：陈述提纲、追问清单（A/B 数字、技能护栏、guard 路径）、现场改码演练。

## 9. 会话导出

本会话是**第一天**记录；第二天再开一条会话继续，用户分别导出两条。此前讨论会话不计入。关键节点保留可复制命令和结果，结束提醒用户导出，并把代表性 run 放进 `traces/`。

## 10. 插件怎么“加载”（第一天要能解释）

1. `plugins/pec-tools/src/*.ts` → `./dev/build.sh` → `lib/*.js`（esbuild）。
2. `plugins/pec-tools/package.json` 的 `main` = `lib/index.js`。
3. `.dsh-home/profiles/headless/cordis.patch.yml` 里 `- insert: - id: pec-tools - name: 'file:///…/lib/index.js'`。
4. `./dev/run-headless.sh`（`cd pec-agent` + 强制 `DSH_HOME=pec-agent/.dsh-home`）→ `dsh --profile headless`，loader import `lib/index.js`，调用 `apply(ctx)`，注册工具 + guard + tool-surface。
5. 验证：`./dev/run-headless.sh --json "调用 pec_data_catalog 看看有哪些表"`，找 `tool_call` + 6 张表。
6. 改 `src/*.ts` 后必须重跑 `./dev/build.sh`，否则加载旧 `lib/`。

## 11. 第一步动作

1. 读 `analysis/taskbook.txt`、`analysis/dsh-api-notes.md`、`analysis/data-audit.md` 和现有源码。
2. 跑基线验证：`./dev/build.sh && node dev/test-tools.mjs` + 一次 headless `order_lookup`。
3. 写 `plan.md` 和 `todo.md`（先落盘，不要等用户回复）。
4. 从“待完成”第 2 项开始按 SDD 推进；每完成一项更新 todo.md、按 §0.1 汇报并等确认。

## 12. 约束

- 不改 DSH 内核/其他插件/profile 原件/交付物里的 `package.json`；只改 `plugins/pec-tools/src/**`、`.dsh/skills/**` 以及 memory/eval/traces/docs。
- 不新增运行时依赖（没有 decimal.js），只用 Node 标准库 + better-sqlite3 + dsh-tools。
- 不修改 `预装环境/`、`实例数据包/` 原件；不把 `.env`、`node_modules`、`.dsh-home` 提交/打包。
- 每完成一块立即验证；不要攒到最后。
- 每完成一个 todo 必须按 §0.1 向用户汇报并等确认；只有用户明确说“继续下一项/不必逐步确认”才可连续推进。
- **不要创建 goal、不要用自动续跑/自动继续**：那会绕过“每个 todo 等确认”的约定；一个 todo 结束就结束当前回合，等用户回复。
