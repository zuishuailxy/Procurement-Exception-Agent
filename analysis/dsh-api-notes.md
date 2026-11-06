# DSH 平台 API 取证笔记（只读，针对 pec-tools 插件可行性）

- 取证对象：本机 `DeepSeek Harness.app` 的 `app.asar`，版本 **0.2.2-rc.1**。
- 考场预装插件声明的是 `@deepseek-ai/dsh-tools 0.2.1-rc.2`。**本文件全部结论先按 0.2.2-rc.1 认定**，每条标注 `【已证实 0.2.2-rc.1】` 或 `【需考场 0.2.1-rc.2 核实】`。
- 取证方法：`python3 analysis/tools/asar.py get <path>` 读各包 `README.md` 与 `lib/*.js`（bundle 后的产物，无 `.d.ts`）。`docs/` 目录**没有**被打包，所以 README 里引用的 `docs/subsystems/*.md`、`docs/tool-catalog.md` 在本机不可读 → 精确类型只能从 lib JS 反推。
- 记号：`✅` 已从 0.2.2-rc.1 证实；`⚠️` 需考场核实。

---

## 1. defineTool 契约

来源：`@deepseek-ai/dsh-tools/README.md`「Register a tool」「Understand the implementation」；`lib/schema.js`（`defineTool` 实现，L272–340）；`lib/types/pipeline.js`（`createSuccessResult` L467–497、`createExecution` L58–120）。

### 1.1 声明形状 ✅

```ts
ctx.tools.register(defineTool({
  name, description,
  parameters: { path: { type: 'string', required: true, description: '…' }, limit: { type: 'number' } },
  output: {
    schema: { type: 'string' },                  // 值校验用
    render: (args, value) => [{ type: 'text', text: value }],   // 模型实际看到的内容
    presentationMeta?: (args, value) => JsonValue,               // 可选，给 UI 的持久化元数据
  },
  deferLoading?: true,
  timeoutMs?: number,          // ⚠️ 只是声明，registry 不强制（README「Known Limitations」）
  isConcurrencySafe?: (args) => boolean,
  projectContent?, finalizeContent?, presentCall?, presentResult?,
  async execute(args, exec) { … },
}))
```

- `parameters` DSL：`string | number | integer | boolean | null | array | object`，外加 **author-only** `json`，以及 exact-one `oneOf`（README「Register a tool」）。`defineTool` 在 execute 前用 `validateArgs` 校验，失败抛 `ToolArgsError` → 模型收到普通错误结果，不结束 turn。
- `output.schema` 也接受同一套 value DSL（`valueSchemaSpecToJsonSchema`）。**返回值和 schema 不符 → `ToolOutputError`（code `INVALID_TOOL_OUTPUT`）**，属于硬失败。
- 兼容原生 JSON Schema（`JsonSchemaNode`），这是与 subagent / workflow / MCP 共用的 wire 形状。

### 1.2 `exec` 到底有哪些字段 ✅

`lib/types/pipeline.js` 的 `createExecution()` 构造出的对象就是传给 `execute(args, exec)` 的同一个 `exec`：

| 字段 | 说明 |
|---|---|
| `exec.signal` | **caller-owned AbortSignal**。工具体必须观察它（协作式取消）。取消前未进 body → `ABORTED_BEFORE_DISPATCH`；进 body 后 → `ABORTED`（"replace only a successful outcome"）。 |
| `exec.agent` | 调用的 **Agent 句柄**（`agent.session` 就是本会话）。**programmatic 调用（`ctx.tools.execute()` 由非模型方发起）时可能为 `undefined`**。 |
| `exec.arguments` | 已 `deepFreeze` 的已校验参数快照（与 `args` 同一份）。**policy 层不得改写**（README 明确）。 |
| `exec.name` / `exec.callId` / `exec.rootCallId` | 工具名与关联 token（PTC 子调用共享 rootCallId）。 |
| `exec.token` | 不透明执行 token（registry 内部关联 cancellation state）。 |
| `exec.parent` | 父调用（PTC 程序内子调用时存在）。 |
| `exec.toolSet` | 本步解析出的 `ResolvedToolSet`（条件工具用）。 |
| `exec.schema` | 调用方随调用带来的 schema（如 PTC/MCP）时存在。 |
| `exec.deferContext(ctx)` | 把一个 context 挂到结果之后（`additionalContexts`），延迟到结果提交时附上。 |
| `exec.concludeTurn()` | 声明"本次调用后结束 turn"。 |

**没有** `exec.log`、`exec.session`、`exec.user`、`exec.tenant`、`exec.role`。
- 「`log`」是 **batch 层**的概念：`ctx.tools.execute({ calls, agent, log: { turn, step } })` 里的 `log` 决定是否把 `tool/call`/`tool/result` 写进 Session（`lib/types/batch.js` L206–217）。模型步骤内的调用由 loop 提供 `log`；程序化调用没有 → 不产生 root call/result 事件。
- 要 session：`exec.agent?.session`。要身份：`exec.agent?.session.id`（见第 6 节）。

### 1.3 返回值如何进入模型上下文与 UI ✅（关键）

执行完成链（README「Understand the implementation / Design concept」+ `lib/types/pipeline.js`）：

```
tools/pre-execute（可 allow/deny/ask/cancel）
  → 注册的 monotonic guards（同步，首个 deny 生效）
  → tools/execute（环绕 dispatch：timeout/retry/metrics）
  → tool body（execute(args, exec)）
  → tools/post-execute（可替换 content/value、block、attach contexts）
  → definition 自带的 finalizeContent
  → tools/result（只读观察，冻结后的最终结果）
```

结果对象里 **`value` 与 `content` 是分开的两条路**（`createSuccessResult`）：

- `value` = 校验通过、`deepFreeze` 的 canonical JSON。**只给程序化调用方用，不写 Session、不给模型。** README 原文："Canonical values belong to execution; the Session records rendered content and optional presentation metadata instead."
- `content` = `output.render(args, value)` 的返回值（block 数组），**这才是模型在 `tool/result` 里读到的东西**，也是唯一被 Session 持久化、后续每步重发的部分。
- `meta` = `output.presentationMeta(args, value)`，持久化给 UI 的元数据。

**结论：模型看不见 `output.schema` 的字段，也看不见 `value`。模型只看 `render()` 产出的文本/图片块。**

UI 侧（README「Host presentation descriptors」）：
- `presentCall()` / `presentResult()` 是 **Host-local**，**Web Client 不消费**。
- Web 端走 `tool.call.toolview`（按工具名选渲染器）+ 原始 call arguments + 结果 content + `meta`。
- 也就是说：**想影响 Web UI 卡片，靠 `presentationMeta` + 预置 toolview；想影响模型，只有 `render()`。**

### 1.4 想让 provenance 被模型引用，怎么声明 ✅

**必须把 provenance 写进 `render()` 的输出文本。** 唯一正确的做法：

```ts
output: {
  // value 里保留结构化 provenance，供审计/程序化消费
  schema: { type: 'object', properties: {
    caseId: { type: 'string' }, source: { type: 'string' }, fetchedAt: { type: 'string' },
    rows: { type: 'array', items: { type: 'json' } },
  }},
  render: (_args, v) => [
    { type: 'text', text:
      `来源: ${v.source} | 案件: ${v.caseId} | 抓取时间: ${v.fetchedAt}\n` +
      JSON.stringify(v.rows, null, 2) },
  ],
}
```

三条硬约束（踩坑点）：
1. `render()` 抛错 = `output.render failed` → 整个工具调用变 `INVALID_TOOL_OUTPUT`。render 必须是纯函数、不得 await、不得抛。
2. `render()` 的返回值必须 lossless JSON（`snapshotProjection` 校验，NaN/BigInt/undefined/循环 → 失败）。
3. 模型**不会**自己去看 `output.schema` 里"有个 source 字段"——schema 只在 assembly 时作为工具参数声明（`parameters`）发给模型；`output.schema` 根本不上 wire（README：「`output`, `execute`, `finalizeContent`, `timeoutMs`, and presentation callbacks never leak onto the wire」）。
4. 若想让 provenance 还能被"引用为上下文"（不占工具结果正文），用 `tools/post-execute` 返回 `additionalContexts`，或 `exec.deferContext()`——两者都会作为独立 context 追加在结果之后（`lib/types/pipeline.js` L455 附近）。

---

## 2. guard 契约

来源：`@deepseek-ai/dsh-tools/README.md`「Enforce policy on calls」；`lib/types/index.js`（`ToolsService.guard` / `checkGuards`，L303–330）；`lib/types/pipeline.js`（`prepare` L128–175、`serviceAsk` L361–405）。

### 2.1 签名与语义（**示例写法已过时**）✅

题目给的示例 `(call, next) => ({deny}) / next()` **不是 0.2.2 的写法**。真实签名：

```ts
const dispose = ctx.tools.guard((exec) => string | undefined)
```

`lib/types/index.js`：

```js
checkGuards(exec) {
  for (const layer of [this.guards.global, ...this.guards.chainLayers(exec.agent)]) {
    for (const guard of layer.guards.values()) {
      const reason = guard(exec);
      if (reason !== undefined) return reason;
    }
  }
  return undefined;
}
```

- **入参只有 1 个**：`exec`（与第 1.2 节同形：`name / arguments / callId / agent / signal / toolSet …`）。
- **没有 `next()`**，没有 `{deny}` 包装。**返回字符串 = 拒绝原因；返回 `undefined` = 放行。**
- **同步**（不能返回 Promise）。README：「monotonic **synchronous** guard」。
- **单调**：一旦某个 guard 返回原因就短路，**后面的 listener 无法把 deny 翻回 allow**（README：「no later listener can turn that denial back into permission」）。这是它与 `tools/pre-execute` 的本质区别。
- **作用域**：`this.guards.effect(this.ctx, …)`；在 `ctx`（全局）注册 = 所有 agent 生效，在 `agent.ctx` 注册 = 只对该 agent 生效。检查顺序：全局层 → agent 作用域链。

### 2.2 `{ask}` 是什么语义、在哪里 ✅

`{ask}` **不是 guard 的返回值**，而是 **`tools/pre-execute` waterfall** 的返回值之一。`pipeline.prepare()` 的真实顺序：

```
executor refusal（ToolNotFound / 已 unload）
  → ctx.waterfall('tools/pre-execute', exec, () => ({kind:'allow'}))   // 可扩展、可重排、异步
  → 若 kind === 'ask'：await this.serviceAsk(exec, ask)               // 走 approval seam
  → 若 kind === 'cancel'：直接 ABORTED_BEFORE_DISPATCH
  → 若 decision.kind === 'allow'：checkGuards(exec)                    // ← guard 在这里
  → 否则 decision.reason 即拒绝
  → dispatch body
```

`pre-execute` 的返回联合（从 `lib/types/pipeline.js` 反推）：`{kind:'allow'}` | `{kind:'deny', reason, info?}` | `{kind:'ask', reason?, displayReason?}` | `{kind:'cancel'}`。

`{ask}` 语义：把决定权交给 **approval seam（`@deepseek-ai/dsh-user-approval`）**，即"暂停等人类/机器回答"。降级路径（`serviceAsk` L361–405）**全部 fail-closed 成 deny**：
- 没挂 approval 服务 → `deny`（reason 带 "requires approval (not yet supported)"）；
- `exec.agent === undefined`（没有 agent 可路由）→ `deny`；
- 无人回答 / 用户拒绝 → `deny: the user rejected tool "…"`；
- 审批被取消 → `deny: approval … was cancelled`；
- `--approval-policy never`（headless 无人值守）→ 直接拒。
- 只有 `allowed-once` 才放行。

**对题目的直接影响**：headless 批跑里 `ask` 等于 `deny`。所以"危险操作要人工确认"在评测里不可用，只能用 `deny` + 审计。

### 2.3 guard 内部能拿到哪些调用者身份 ✅/⚠️

`exec` 里能拿到：
- `exec.agent`（Agent 句柄）→ `exec.agent.id` / `exec.agent.session.id`（agent id === session id，`lib/index.js` L643 有断言 `if (id !== agent.session.id) throw …`）。
- `exec.agent.session.header`（`{ cwd, origin, agentPreset?, … }`）。
- `exec.name / exec.arguments / exec.callId / exec.signal`。

**拿不到**：`userId` / `tenantId` / `role` / `exec.log` / `exec.session`（要 session 只能 `exec.agent.session`）。
`exec.agent` 为 `undefined` 时（程序化调用、初始化钩子）**任何依赖 agent 的策略都必须显式 fail-closed**，否则成为绕过面。

### 2.4 "拒绝也留痕"怎么做 ✅

三个可选落点，建议**同时**用前两个：

1. **平台自带审计（零代码）**：模型步骤内的每次调用都会写 `tool/call` 与 `tool/result` 进 Session 日志（`lib/types/batch.js`），含 `isError` 与 `data.error { name, code, reason? }`。拒绝也会落一条 `tool/result`（`content: [{type:'text', text:'Error: <reason>'}]`, `isError: true`）。落盘由 `dsh-session-persistence-jsonl` 负责，root 由 profile 配置（`session-persistence-jsonl/README.md`「On-disk layout」）。
2. **自己的审计文件（推荐给题目）**：注册 `ctx.on('tools/result', (exec, result) => …)` —— README 定义为「observe-only」、拿到**冻结后的最终结果**，且是**异步**的，可以自由写文件。写 `$DSH_HOME/` 或插件自己的目录，不要写 workspace（会被判成改了业务代码）。
   - 时机：**在结果 finalize 之后、下一步之前**；异常被 logger.warn 吞掉（`pipeline.js` L343–348），不会污染工具结果。
3. **guard 内部直接写**：只能 `appendFileSync`（guard 同步）。适合"必须保证即使进程立刻崩也留痕"的场景，但阻塞事件循环，不推荐在主路径。

**坑**：`tools/pre-execute` 的 deny 可以带 `info`（结构化 `ToolErrorInfo`），该 `info` **只进持久化投影，不进模型 content**（README：「without adding that detail to model content」）。而 **guard 的 deny 没有 info 通道**——guard 只能给字符串。所以需要"结构化留痕"就用 `pre-execute` deny + `info`，或自己写审计文件。

### 2.5 `tools/pre-execute` 与 guard 的顺序 ✅

**pre-execute 先，guard 后**（`prepare()` 里 `checkGuards` 在 `decision.kind === 'allow'` 分支调用）。因此：
- pre-execute 可以 allow/deny/ask/cancel；**只有 allow（含 ask→批准）才会走到 guard**。
- guard 是最后一道**不可翻案**的闸门。
- 两者都发生在 body 之前、`tools/execute` 环绕之前。

---

## 3. 每轮动态注入（最关键）→ **能做到，官方有正式扩展点** ✅

来源：`@deepseek-ai/dsh-system-prompt/README.md`「Contribute a prompt section」「Contribute a prompt variable」；`lib/index.js`（`assemble()` L340–410、`section()` L255、`resolveContext()` L185）；`@deepseek-ai/dsh-agent/lib/index.js` 的 `assembleContextFor()`（L407–413）；`@deepseek-ai/dsh-agent-loop/lib/index.js` 的 `preStep()`（L667–700）。

### 3.1 结论

**能做，且不需要替代方案。** 关键是 README 只在示例里写了静态字符串，但 **`section.text` 与 `context.text` 都允许是函数**：

```js
// lib/index.js assemble()
const sections = sectionDefinitions.map((section) => ({
  name: section.name,
  text: typeof section.text === "function" ? section.text(context) : section.text,
  ...
}));
```

`assemble()` 由 **agent loop 在每个 proposed step 之前调用一次**（system-prompt README：「The agent loop calls `assemble(context)` once per proposed step before `agent/pre-step`」）。所以 `text(context)` **就是"每轮执行一次"的钩子**。

`context` 的实参来自 `assembleContextFor(agent, signal)` + loop 补的两个字段：

```js
assemble({
  agent,            // ← Agent 句柄，含 .session
  scope: agent,
  signal,           // ← AbortSignal
  modelSelection,   // { provider, model, reasoningEffort? }
  toolSet,          // 本步 ResolvedToolSet
})
```

→ **可以在 `text(ctx)` 里读 `ctx.agent.session`、读磁盘、算出 3–5 条记忆、返回注入文本。**

### 3.2 两种注入通道的区别 ✅

| | `ctx.systemPrompt.section({...})` | `ctx.systemPrompt.context({...})` |
|---|---|---|
| 落到哪 | **system-role 消息**（surface node 0，或 in-history 追加的 system 节点） | **user-role 的 sourced snapshot**（`renderContextSections` → `runtimeContext.project` → 追加到 pre-step 的 messages） |
| 是否被 `includeRuntimeContext:false` 掐掉 | 否 | **是**（除非 `required: true`） |
| 缓存影响 | 改动会让前缀从第一个变化 token 起失效（除非 `systemPromptUpdate:'in-history'`） | append-only，保留前缀复用 |
| 适合 | 稳定人格/策略 | **每轮变化的事实（记忆、时间、待办）** |

`context()` 有 `required?: boolean`（`refreshContext` 里 `entry.required === true` 才在 suppress 后保留）。

### 3.3 最小可行骨架（记忆注入）

```ts
import type { Context } from '@deepseek-ai/cordis'
import { readFileSync } from 'node:fs'

export const name = 'pec-memory-inject'
export const inject = ['systemPrompt']

export function apply(ctx: Context) {
  // 每轮重新读取 + 计算；返回 '' 则整段消失（renderPrompt 会过滤空段）
  ctx.systemPrompt.section({
    name: 'pec:memory',
    order: 10050,              // 外部贡献可用任意有限数，> WEB_SURFACE(10100) 之前即可
    interpolate: false,        // 记忆里可能含 {{ }}，防止被当变量解析而抛错
    text: ({ agent }) => {
      if (agent === undefined) return ''
      const file = `${agent.session.header.cwd}/.dsh/memory/${agent.session.id}.json`
      let mem: string[] = []
      try {
        mem = JSON.parse(readFileSync(file, 'utf8')).recent ?? []
      } catch { return '' }     // 读不到就静默降级，绝不抛
      if (mem.length === 0) return ''
      const picked = mem.slice(-5)
      return [
        '<pec_memory>',
        '以下是本会话已确认的用户/案件记忆，回答前必须先核对：',
        ...picked.map((m, i) => `${i + 1}. ${m}`),
        '</pec_memory>',
      ].join('\n')
    },
  })
}
```

**必须遵守的硬约束**（否则整个 prompt 组装会抛，turn 直接失败）：
1. `text()` **同步**（assemble 里是同步调用，没有 await）。读文件用 `readFileSync`，且必须 try/catch。
2. **不得返回 `undefined`、不得抛异常**。返回 `''` 是合法的"本段不出现"。
3. **`interpolate: false`**，否则文本里的 `{{…}}` 会被严格解析，未知变量直接抛 `unknown prompt variable`。
4. 用 `ctx.agent` 做 scope 隔离：在全局 `ctx` 注册的 section 对所有 agent 生效；想按 agent 差异化，用 `agent.ctx.systemPrompt.section(...)`（在 agent setup 阶段注册）。
5. **别用 `{{cwd}}` 变量**——loop 不注册它，会 `unresolved variable` 失败（README 明确警告）。

### 3.4 备选/补充通道（都能用，按需选）

- **`ctx.systemPrompt.variable(name, provider)`**：`provider(context)` 每次 assemble 求值，模板里写 `{{pec_memory}}`。名字必须匹配 `/^[a-z][a-z0-9_]*$/`，重复注册抛错。
- **`agent/pre-step` 监听器 + 注入消息**（这是 `dsh-agent-instructions` 与 `dsh-tool-skill` 用的机制）：`ctx.on('agent/pre-step', async ({ agent, messages, signal, step, modelSelection }, next) => { const d = await next(); if (d.kind !== 'enter') return d; return { kind:'enter', messages: [...d.messages, myContextMessage] }; })`。优点：**支持异步**、消息进 Session（可 replay/审计）；缺点：每轮都 append 会累积历史、吃 token，且需要自己写 `<system-reminder>` 框架。
- **`agent.inject()` / `agent.steer()`**（`dsh-agent` README「Drive an agent's conversation」）：`inject()` 不唤醒 driver，"lands in the next admitted step"。但**这是从外部驱动 agent 的 API**，在插件里对自己所在 agent 用要小心时序。
- **`waterfall('system-prompt/assemble', …)`**：可整体改 assembly，但属于最强侵入，不建议。

### 3.5 "下一轮自动注入 3–5 条记忆"能否达标

**能达标，且是原生能力**：`section.text(ctx)` 每步求值 → 天然"下一轮自动注入"。需要注意的只是：注入内容是 **system prompt 的一部分**（会被计入每次请求的 prefix），评测若按 token 算 A/B，要么接受这部分成本，要么改成 `context()`（append-only）或变量。

---

## 4. 技能机制 → **可观测、可复用，但正文里的"护栏"只是文本** ✅

来源：`@deepseek-ai/dsh-skill-filesystem/README.md`（「Skill format」「Roots and priority」「Change detection」）；`@deepseek-ai/dsh-tool-skill/README.md`（「What the model gets」「Catalog lifecycle」「Model Experience」）。

### 4.1 扫描规则 ✅

- 只认两种形状：`<root>/<name>/SKILL.md` 或 `<root>/<name>.md`。**`**/SKILL.md` 嵌套不发现**（一层深）。
- 根目录与优先级（rank 越小越优先）：

| rank | source | path |
|---|---|---|
| 100 | project-dsh | `<projectRoot>/.dsh/skills` ← **题目允许改的目录** |
| 200 | project-agents | `<projectRoot>/.agents/skills` |
| 300 | custom | `Config.customSkillDirs` |
| 400 | user-dsh | `<dshHome>/skills` |
| 500 | user-agents | `<agentsHome>/skills` |

- `projectRoot` = 最近含 `.git` 的祖先；没有就用 cwd。→ **注意**：这个仓库根有 `.git`，所以 `.dsh/skills` 解析在仓库根，不是 cwd 的子目录。

### 4.2 frontmatter 字段 ✅

必填 `name`（kebab-case）、`description`（required）。
可选：`whenToUse`、`metadata`、`disable-model-invocation`、`user-invocable`。
- `disable-model-invocation: true` → 不进模型 catalog，也不能被 `skill` 工具加载，**只能靠用户 `/name` 显式触发**。
- `user-invocable: false` → 不进人类命令面。
- 布尔值支持 `true/false`、`yes/no`、`on/off`、`1/0`（大小写不敏感）；**拼错或非布尔 → 整个技能被丢弃 + warning**（模型侧完全看不出区别，只当不存在）。

### 4.3 正文何时进入上下文 ✅（关键）

**三段式，不是常驻**：
1. **catalog（常驻，1 次）**：只要 `skill` 工具可见且存在 model-invocable 技能，首个请求前追加一条 **durable user-role 消息**，`<available_skills>` 里只有 `name` + 截断后的 `description`（`catalogDescriptionMaxLength` 默认 500）。**body 不在里面。**
2. **body（按需，模型主动）**：模型调 `skill` 工具 → 结果里给 `<skill_content><skill_instructions>…</skill_instructions></skill_content>`，作为**普通 tool history 保留**（后续每步重发，直到 compact）。
3. **body（按需，用户显式）**：用户输入里出现 ` /name ` token → 该技能正文以 `user`-role instructions context 注入当步。

**catalog 变更**（增删、描述变、可见性变、incomplete 恢复）→ **追加一条 replacement catalog**（whole-list 替换），旧名字被显式 retire。body-only 编辑**不改变 digest**、不通知模型（README「Known Limitations」：Bodies are not versioned）。

### 4.4 热更新 ✅

- `watch: true`（默认）→ Chokidar 监听 depth 1；`SKILL.md` 的 add/remove/**change** 与 bundle/`.md` 的 add/remove 会合并成一次 provider invalidation → 下个模型步生效。
- **`references/`、`scripts/`、`assets/` 等资源子树改动被忽略。**
- 第一方 `write`/`edit` 工具命中技能路径时**同步**invalidate（`fs/observed`），不用等 watcher。
- 缺失的 root 用 `fs.watchFile` 轮询直到出现。
- **body 编辑无需版本/缓存失效**：每次 load 都重读当前文件（catalog 与 body 生命周期分离）。

### 4.5 冲突取舍 ✅

按 rank 排序，**高优先级同名技能胜出**（registry 合并 provider 结果）。`skill-filesystem` 的 I/O 失败会**丢掉整个 root**（连同可读的兄弟），此时"低优先级的同名定义会顶上来"（README「Known Limitations」）。同 rank 内的取舍规则 ⚠️ 需在考场核实（README 只说"按 rank 合并"）。

### 4.6 技能正文的"护栏"能不能拦工具调用？ → **不能** ✅

技能正文是**纯文本**，通过 `skill` 工具结果或 `/name` 注入进入上下文，对模型**只有说服力，没有强制力**。它**不参与** `tools/pre-execute` / guard 的判定链，模型完全可以无视。

要真正拦截，必须二选一（都在**插件代码**里，不是 skill 文件里）：
- `ctx.tools.guard(exec => …)` —— 同步、单调、不可翻案。
- `ctx.on('tools/pre-execute', …)` —— 异步、可 ask、可带结构化 info。

**推荐组合**（也是题目"技能复用率"的正确做法）：
- 把**策略/流程/模板**写进 skill 正文（模型读、模型遵守、可复用、可被 catalog 观测到）。
- 把**硬约束**写进 guard（例如"未 `case.get` 就禁止 `case.close`"）。
- 两者通过**同一份规则常量**（插件源码里的 TS 常量）保持一致，避免正文与 guard 漂移。

### 4.7 "技能复用率 ≥60%"能被观测吗？ ✅ 能，但要自己埋点

平台侧可观测的事实：
- catalog 是 durable user-role 消息 → Session 里能查到"当时有哪些技能"。
- 每次 `skill` 调用是 `tool/call` + `tool/result`（headless `--json` 里是 `tool_call` 事件，`tool: "skill"`）。
- 用户 `/name` 注入在 Session 里是一条 `user/message`（source 带技能名）。

→ **判定复用率 = `tool_call` 中 `tool === 'skill'` 的次数 / 总任务数**，或按 `--session-id` 统计有多少会话加载过技能。建议在插件里再加一个 `tools/result` 监听器，把 `skill` 加载落到自己的审计文件，避免依赖日志格式。

---

## 5. headless 批跑 → **能做，工具次数与 token 都有现成字段** ✅

来源：`@deepseek-ai/dsh-headless/README.md`（「Running a one-shot task」「Machine-readable output」「Patch surface over base」「Exit mapping」）；`lib/json-stream-Dc3g2Bl1.js`（`projectJsonRun` L170–280）；`cordis.patch.yml`；`@deepseek-ai/dsh/README.md`（「Entry modes」「Profiles」）。

### 5.1 命令是否存在 ✅

**存在**。`dsh --profile headless "…"` 与 `dsh headless "…"` 都是合法入口（`@deepseek-ai/dsh` README 的 Entry modes 表）。`--json` 也是真实 flag（`Config.json`，由 `headless-startup` 解析）。

```sh
dsh --profile headless --json "处理 CASE-2024-001"
echo "$task" | dsh --profile headless --json - > run.jsonl
dsh --profile headless --json --session-id session-xxx "继续"
```

### 5.2 事件流 schema 在哪定义 ✅

`dsh-headless/src/json-stream.ts`（打包后 `lib/json-stream-Dc3g2Bl1.js`，导出 `projectJsonRun`）。**没有独立的 JSON Schema 文件**，类型就是该文件里的 `write({type: …})` 调用。NDJSON，一行一事件：

| type | 关键字段 |
|---|---|
| `session` | `sessionId`, `cwd`（**首行，在订阅前写出**） |
| `status` | `phase: 'turn_start' \| 'step_start' \| 'step_end' \| 'turn_end'`；`turn`/`step`；turn_end 带 `reason` |
| `thinking` | `text`（assistant/message 里的 reasoning 块，commit 时一次性给，不是逐 token） |
| `text` | `text` |
| `tool_call` | `callId`, `tool`, `input`（解析后的对象，空参 → `{}`） |
| `tool_result` | `callId`, `status: 'completed'\|'error'`, `result`（text 块拼接）, `error?: {name, code, reason?}` |
| `final` | `sessionId`, `reason`（durable turn reason，可能 `null`）, `text`（**不截断**） |
| `error` | `message`（runner 在 turn 之外失败时；**此流无 `final`**） |

**边界**：非 `final` 的字符串/key 8 KiB 上限并带 `truncated` 标记；单行 32 KiB 上限；嵌套 64 层截断。`final.text` 不截断。

### 5.3 工具调用次数 / token 用量从哪取 ✅（关键）

**工具调用次数**：数 `type === "tool_call"` 的行数即可（每次调用一行，`callId` 唯一）。注意：
- **PTC 模式**下，外层只有 `run_code` 一次 `tool_call`，程序内子调用**不产生 `tool_call` 事件**（README：「Inner dispatch events stay log-only」）。→ 若题目按"工具步数"评测，**必须用 native executor**，否则步数被算成 1。
- `tool_result` 可能少于 `tool_call`（中断/被丢弃），以 `tool_call` 为准，并把 `status:'error'` 单独统计。

**token 用量**：在 **`type === "status"` 且 `phase === "step_end"`** 的事件上，**`usage` 字段**：

```json
{"type":"status","phase":"step_end","turn":1,"step":2,
 "usage":{"inputTokens":1234,"outputTokens":567,"totalTokens":1801,
          "cacheReadTokens":0,"cacheWriteTokens":0,"reasoningTokens":0}}
```

- 聚合口径：把每个 `step_end.usage` 相加；`inputTokens + outputTokens` 或 `totalTokens` 二选一（**统一口径**，否则 A/B 不可比）。
- **陷阱**：`usage` 是**条件出现**的。`addUsage()` 的规则是——某个 attempt 没上报 usage，则**整个 step 的 usage 被省略**（"omits usage entirely rather than publish a partial sum"）。批跑脚本必须处理 `usage` 缺失，否则会低估。
- `usage` 是**跨 attempt 累加**的（重试的 attempt 只在 `assistant/attempt` 的 stream 里带 usage，已正确合并）。
- 兜底：直接从持久化的 Session 日志里 fold `assistant/message.data.usage` / `request/header`（`dsh-session` 的 surface 事件），或用 `dsh-session-stats`。

### 5.4 让 headless profile 加载 pec 插件 ✅

组合顺序（`@deepseek-ai/dsh` README「Profiles」）：`bundles` 依次 → profile `cordis.patch.yml` → `$DSH_HOME/cordis.patch.yml` → **`--patch` 覆盖层**。

三条可行路径：
1. **`--patch <file>`**（最干净，不动 profile）——overlay 里 `insert` 你的插件行：
   ```yaml
   - insert:
       - id: pec-tools
         name: '@pec/pec-tools'     # 需在 profile 的 node_modules 里可解析
   ```
2. **改 profile 的 `cordis.patch.yml`**：`$DSH_HOME/profiles/headless/cordis.patch.yml`（headless README 就是这么演示恢复 credentials 的）。
3. **`dsh plugin --profile headless add @pec/pec-tools`**（走 pnpm 装进 profile 目录）。

**cwd 与相对路径 `dbPath`** ✅/⚠️：
- headless 的 `sandbox-policy` 配置是 `workspaceRoot: !!js process.cwd()`（`cordis.patch.yml`）——**workspace root = 进程 cwd**。
- Session 记录 `cwd` 来自 `fs.resolve('.')` / `fs.processPath()`，无 fs 服务时用 `process.cwd()`。
- **结论**：`dbPath: './data/pec.db'` 这类相对路径**按进程 cwd 解析**，不按 profile 目录、不按 `$DSH_HOME`。批跑脚本必须 `cd` 到数据包根再启动，或在插件里自己 `path.resolve(ctx.session.cwd, dbPath)` 显式定基。**⚠️ 0.2.1-rc.2 是否有 `ctx.headlessStartup` 之类差异需核实。**

### 5.5 退出码 ✅

- **0**：最后一个 turn 的 `turn/end.reason.kind === 'completed'`。
- **1**：其它一切——aborted、error、**owned interval 内没有任何 turn**、Agent 创建失败、`--session-id` 不可用、profile 插件加载失败、usage/参数错误。
- `error` reason 额外往 stderr 写 `dsh: <code>: <message>`。
- **可靠性建议**：判定成功要 **`exit code === 0` 且 `final.reason.kind === 'completed'` 两者都成立**（README 明确要求）。`--json` 模式下若出现 `error` 事件，则**不会有 `final`**。
- `tool_result.status === 'completed'` 只表示"工具返回了"，**不代表里面的 shell 命令 exit 0**。

---

## 6. 会话与身份

来源：`@deepseek-ai/dsh-session/README.md`（「Create and inspect sessions」「Append and derive」「Request headers」）；`@deepseek-ai/dsh-agent/README.md`（「Scope registrations to one agent」「Initiator scope」）；`@deepseek-ai/dsh-agent/lib/index.js` `assembleContextFor`；`@deepseek-ai/dsh-anonymous-user-id/README.md`。

### 6.1 `ctx.session` 是什么？ ✅

**它不存在。** 插件上下文里**没有** `ctx.session` 这个服务。Session 是**每个 agent 一个**，通过以下途径拿：
- `exec.agent.session`（工具内）；
- `agent/pre-step` 的 payload `{ agent, messages, signal, step, modelSelection }`（`dsh-agent` 的 `installModelSelection` 用的就是这个签名）；
- `ctx.agents.get(id)` / `ctx.agents.list()`；
- 全局服务是 `ctx.sessions`（`SessionStore`：`create/get/list/fork/flush`），不是"当前会话"。

`Session` 对象能力（`dsh-session` README）：
- 读：`session.id`、`session.seq`、`session.header`（`{ cwd, origin, agentPreset?, isSeeded, … }`）、`deriveMessages()`、`requestHeader()`、`toolHistory()`。
- 写：`session.append(type, data, { surfaceOp })`。**surface 事件必须带 `surfaceOp`**；log-only 事件不能带 metadata。
- `ctx.sessions.fork(source, boundary?, childId?)`、`ctx.sessions.flush(session)`。

### 6.2 tenantId / userId / role 从哪来？ ✅（答案：没有）

- **`tenantId` 在整个 asar 里搜不到**（`asar.py find tenant` 无结果）。
- **没有 `userId`/`role` 服务**。身份维度只有：
  - `sessionId`（= `agentId`，opaque 字符串，`session-<uuid>`）；
  - `scope`（= agent，`dsh-scope` 的 `scopeOf/scopeChainOf`）；
  - `$DSH_HOME/.anonymous-user-id`（**per-installation 的匿名 UUID**，写在 `$DSH_HOME/.anonymous-user-id`，用于 telemetry / feedback / DeepSeek 请求头 `x-deepseek-harness-user-id`；README 明确："**Do not use it to identify a user**"）；
  - Web profile 的 DeepSeek 账号（`dsh-deepseek-account`）——**headless profile 默认 `disabled: true`**（见 headless `cordis.patch.yml`）。
- **结论**：`tenant/user/role` 必须由 pec 插件**自己建模**：`sessionId → { userId, role, tenantId }` 的映射（配置文件 / SQLite / 环境变量），来源是**进程可信输入**，不是模型输入。

### 6.3 模型能否通过工具参数伪造身份？ ✅ 不能（如果写法正确）

- `exec.agent`、`exec.agent.session.id`、`exec.callId` 都是**平台注入**的，模型只控制 `exec.arguments`（`parameters` 校验后的冻结快照）。
- **危险写法**（等于把身份交给模型）：`execute(args)` 里用 `args.userId` / `args.role` 做鉴权。
- **正确写法**：身份只从 `exec.agent.session.id` 派生；`args` 里的任何 id **只当查询键**，必须与平台身份做归属校验。guard 同理：guard 只该读 `exec.agent`，不该读 `exec.arguments.role`。
- 插件作用域本身也是边界：`agent.ctx` 注册的工具/guard **只对被 scope 的 agent 生效**，不会被别的 agent 继承。

### 6.4 会话持久化与过期配置 ✅/⚠️

- 持久化：`@deepseek-ai/dsh-session-persistence-jsonl`，`config.root` **必填无默认**（README 明确拒绝用 `process.cwd()` 做默认）。每 session 一个目录，默认 `compression: 'zstd'`（可设 `'none'` 拿可读 NDJSON）。**具体 root 由 profile 决定** ⚠️ 需在考场 `dsh --profile headless --dump-config` 确认。
- 过期/TTL：**没有找到"会话过期"配置**。相关的是 `dsh-session-checkpoint-policy`（检查点）与 `workspace` 的归档准入（`agent/README.md`「Registry and lifecycle」提到 archive admission / `workspace/session-stop`）。⚠️ 若题目要求"记忆过期"，得自己在插件里做（按 `fetchedAt`/`turn` 数裁剪），不要指望平台。
- Session 格式版本：`SESSION_FORMAT_VERSION`，当前有 v0→v4 的迁移链；插件写自定义事件**受类型约束**。

### 6.5 插件能否读写 session 状态 ✅（分情况）

| 想做的事 | 能否 | 正确做法 |
|---|---|---|
| 读会话历史 / 消息 | ✅ | `agent.session.deriveMessages()`、`requestHeader()`、`toolHistory()`；⚠️ `eventAt/snapshotEvents/ownEvents` 已 deprecated，新代码禁用 |
| 追加自定义 session 事件 | ⚠️ 受限 | `session.append` 只接受 `SessionEventMap` 里的类型；**外部插件不得调 `appendPluginRecord`**（README：仓库外的插件也"must not"）。要给模型看的内容，用 `agent.inject()` / `steer()` / pre-step 注入；要给自己存状态，用 **`ctx.storageDomain`**（`defineDomain` + schema，durable、同步读、`domain/changed`，且**不进模型上下文**） |
| 改别的会话 | ⚠️ | 只能通过 `ctx.agents.get(id)` 拿到 live agent 再操作；已被别人驱动的会话会被拒 |
| 让模型"记住" | ✅ | 就是第 3 节的动态注入 + 自己落盘（JSON / storageDomain / SQLite） |

---

## 7. 考场需核实清单（0.2.1-rc.2）

按优先级排，全部可在考场用 `dsh --profile headless --dump-config` / `--dump-config-schema` + `grep` 装好的 `node_modules/@deepseek-ai/*/lib/*.js` 复核：

1. `SystemPrompt.section({ text })` **是否仍接受函数**（第 3 节全部押在这上面）。核实点：`dsh-system-prompt/lib/index.js` 的 `assemble()` 里是否有 `typeof section.text === "function"`；以及 `assembleContextFor()` 是否仍传 `agent`。
2. `ToolsService.guard` 的签名是否仍是 `(exec) => string | undefined`（而非 0.2.1 早期的 `(call, next)` 或返回 `{deny}`）。核实 `lib/types/index.js` 的 `checkGuards`。
3. `tools/pre-execute` 的返回联合是否包含 `{kind:'ask'}`，以及 ask 的降级是否仍 fail-closed。
4. `exec` 上是否已有 `exec.session` / `exec.log`（当前版没有，只能 `exec.agent.session`）。
5. headless `--json` 的 `status/step_end` 是否仍带 `usage`，字段名是否仍为 `inputTokens/outputTokens/totalTokens/cacheReadTokens/cacheWriteTokens/reasoningTokens`；`usage` 是否仍是"不完整就省略"。
6. `dsh --profile headless --json` 是否仍是 `session → status/text/thinking/tool_call/tool_result → final`，`tool_call` 是否仍带 `callId/tool/input`。
7. `defineTool.output.render` 是否仍是模型唯一可见通道；`presentationMeta` 是否仍持久化给 Web。
8. `dsh-skill-filesystem` 的 roots/rank 与 frontmatter 字段是否一致；`dsh-tool-skill` 的 catalog 是否仍是 durable user-role 消息。
9. `$DSH_HOME/profiles/headless/cordis.patch.yml` 与 `--patch` 的层序是否仍为 `bundles → profile patch → home patch → --patch`。
10. headless profile 的 session-persistence `root` 实际值、`sandbox-policy.workspaceRoot` 是否仍为 `process.cwd()`（决定相对 `dbPath` 的解析基）。
11. 是否存在 `ctx.session` 或任何 `tenantId/userId/role` 服务（当前版没有；若考场版新增，第 6 节结论要改）。
12. 技能同名冲突在同 rank 内的取舍规则（README 未写）。

---

## 8. 对题目 6 项要求的可行性裁决

| 题目要求 | 裁决 | 依据 / 关键手段 |
|---|---|---|
| 6 个业务工具 | ✅ 能做 | `defineTool`，`parameters` DSL + `output.schema` + `output.render` |
| provenance 被模型引用 | ✅ 能做，**但必须写进 `render()` 文本**；`value`/`output.schema` 模型看不见 | 第 1.3–1.4 节 |
| 会话/用户记忆（抽取） | ✅ 能做 | 工具里写 JSON/SQLite/`storageDomain`；身份用 `exec.agent.session.id`，**别用模型传的 id 鉴权** |
| **下一轮自动注入 3–5 条记忆** | ✅ **能做（原生）**，无需替代方案 | `ctx.systemPrompt.section({ text: (ctx) => … })`，每 step assemble 一次；或 `context()` / `agent/pre-step` |
| 技能沉淀与复用 | ✅ 能做 | `.dsh/skills/<name>/SKILL.md`；catalog 自动曝光 + `skill` 工具按需加载 |
| 技能复用率可观测 | ✅ 能，但**要自己埋点** | 数 `tool_call.tool === 'skill'`；或 `tools/result` 写审计 |
| **技能正文里的护栏能拦截工具** | ❌ **不能**，只是文本约束 | 必须配 `ctx.tools.guard` / `tools/pre-execute` |
| 12 条评测集 + A/B | ✅ 能做 | `dsh --profile headless --json`；工具次数 = `tool_call` 行数（**必须 native executor**，PTC 会塌缩成 1 次 `run_code`）；token = `status.step_end.usage` 求和（注意缺省） |
| guard 用 `(call, next) => ({deny})` | ❌ 过时写法 | 改成 `guard(exec => string \| undefined)` |
| headless 里用 `ask` 要人工确认 | ❌ 等于拒绝 | 无人值守下必须 fail-closed 成 deny |
