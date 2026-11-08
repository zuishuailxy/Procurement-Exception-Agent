#!/usr/bin/env node
/**
 * DSH 会话导出器（交付物「AI 会话导出，按日分文件夹」用）。
 *
 * 用法（在任意目录）：
 *   node export-dsh-session.mjs                          # 用当前 DSH_SESSION_ID + DSH_HOME
 *   node export-dsh-session.mjs --session-id session-xxx --out D1
 *   node export-dsh-session.mjs --session-id session-xxx --home ~/.dsh --cwd <工作目录>
 *
 * 产物（<out>/）：
 *   session-<id>.jsonl.zst   原始会话文件（压缩，保真）
 *   session-<id>.jsonl       解压后的完整事件流（NDJSON，含所有注入上下文/工具调用）
 *   session-<id>.md          人读版对话记录（用户/助手/工具调用/结果，长内容截断）
 *   README.md                元数据、统计、阅读说明、复跑命令
 *
 * 说明：DSH 的 session.v4.jsonl.zstd 是**多帧 zstd 拼接**，Node 自带的 zstdDecompressSync 只解第一帧，
 * 因此这里按 zstd 帧魔数切帧后逐帧解压。不修改原会话文件，只读取。
 */
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { basename, dirname, join, resolve } from 'node:path'
import zlib from 'node:zlib'

const args = process.argv.slice(2)
const arg = (name, fallback) => {
  const index = args.indexOf(`--${name}`)
  return index >= 0 ? args[index + 1] : fallback
}

const DSH_HOME = resolve(arg('home', process.env.DSH_HOME || join(homedir(), '.dsh')))
const CWD = resolve(arg('cwd', process.cwd()))
const SESSION_ID = arg('session-id', process.env.DSH_SESSION_ID)
if (!SESSION_ID) {
  console.error('缺少 session id：请传 --session-id，或从 DSH env 里设置 DSH_SESSION_ID')
  process.exit(1)
}

/** DSH 的 session 目录命名：--<绝对路径去掉首个 /> 的 / 换成 - -- */
function sessionDirCandidates(home, cwd, sessionId) {
  const encoded = `--${cwd.replace(/^\//, '').replaceAll('/', '-')}--`
  const base = join(home, 'sessions')
  const candidates = []
  if (existsSync(join(base, encoded, sessionId))) candidates.push(join(base, encoded, sessionId))
  // 兜底：在 sessions 下按名字找
  if (candidates.length === 0 && existsSync(base)) {
    for (const project of readdirSync(base)) {
      const candidate = join(base, project, sessionId)
      if (existsSync(candidate)) candidates.push(candidate)
    }
  }
  return candidates
}

const sessionDirs = sessionDirCandidates(DSH_HOME, CWD, SESSION_ID)
if (sessionDirs.length === 0) {
  console.error(`找不到会话目录：${SESSION_ID}（DSH_HOME=${DSH_HOME}, cwd=${CWD}）`)
  process.exit(1)
}
const sessionDir = sessionDirs[0]
const sourceFile = ['session.v4.jsonl.zstd', 'session.v4.jsonl.zst']
  .map((name) => join(sessionDir, name))
  .find((file) => existsSync(file))
if (!sourceFile) {
  console.error(`会话目录里没有 session.v4.jsonl.zstd：${sessionDir}`)
  process.exit(1)
}

function decompressZstdFrames(buffer) {
  const magic = Buffer.from([0x28, 0xb5, 0x2f, 0xfd])
  const starts = []
  for (let i = 0; i <= buffer.length - 4; i++) {
    if (buffer[i] === magic[0] && buffer[i + 1] === magic[1] && buffer[i + 2] === magic[2] && buffer[i + 3] === magic[3]) starts.push(i)
  }
  const chunks = []
  for (let k = 0; k < starts.length; k++) {
    const start = starts[k]
    const end = starts[k + 1] ?? buffer.length
    try {
      chunks.push(zlib.zstdDecompressSync(buffer.subarray(start, end)))
    } catch {
      const mergedEnd = starts[k + 2] ?? buffer.length
      try {
        chunks.push(zlib.zstdDecompressSync(buffer.subarray(start, mergedEnd)))
        k++
      } catch {
        /* 跳过坏帧 */
      }
    }
  }
  return Buffer.concat(chunks)
}

const raw = readFileSync(sourceFile)
const decompressed = decompressZstdFrames(raw)
const events = decompressed
  .toString('utf8')
  .split('\n')
  .filter((line) => line.trim())
  .map((line) => {
    try {
      return JSON.parse(line)
    } catch {
      return null
    }
  })
  .filter(Boolean)

const header = events.find((event) => event.type === 'session') ?? {}
const title = events.filter((event) => event.type === 'session/title').map((event) => event.data?.title).filter(Boolean).pop() ?? '(无标题)'
const exportedAt = new Date()
const createdAt = header.createdAt ? new Date(header.createdAt) : statSync(sourceFile).birthtime
const localIso = (date) => {
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

// 先扫一遍，建立 callId → 工具名 映射与统计
const callNames = new Map()
const toolCounts = {}
let errors = 0
let nonzeroExit = 0
let usage = { inputTokens: 0, outputTokens: 0, cacheReadTokens: 0, totalTokens: 0 }
for (const event of events) {
  if (event.type === 'tool/call') callNames.set(event.data?.callId, event.data?.name)
  if (event.type === 'tool/result' && event.data?.message?.isError) errors += 1
  if (event.type === 'tool/result') {
    const resultText = (event.data?.message?.content ?? []).filter((block) => block.type === 'text').map((block) => block.text).join('\n')
    if (/exit code: [1-9]/.test(resultText)) nonzeroExit += 1
  }
  if (event.type === 'assistant/message' && event.data?.usage) {
    for (const key of Object.keys(usage)) usage[key] += Number(event.data.usage[key] ?? 0)
  }
}
for (const name of callNames.values()) toolCounts[name] = (toolCounts[name] ?? 0) + 1

const clip = (text, max) => {
  const value = String(text ?? '')
  if (value.length <= max) return value
  return `${value.slice(0, max)}\n…（已截断，完整内容见 .jsonl）`
}

const md = []
md.push(`# AI 会话记录 · ${title}`)
md.push('')
md.push(`- 会话 ID：\`${SESSION_ID}\``)
md.push(`- 工作目录：\`${CWD}\``)
md.push(`- 创建时间：${localIso(createdAt)}（Asia/Shanghai）`)
md.push(`- 导出时间：${localIso(exportedAt)}（Asia/Shanghai）`)
md.push(`- 平台：DSH ${process.env.DSH_VERSION ?? '0.2.1-rc.2'} · 模型 deepseek-flash（deepseek-official）· profile ${process.env.DSH_PROFILE ?? 'desktop'}`)
md.push('')
md.push('> 本文件由 `export-dsh-session.mjs` 从 DSH 会话事件流自动生成：用户/助手正文完整，工具调用参数与结果保留但超长截断；**完整原始事件流见同名 `.jsonl`**。运行时上下文、技能目录、时间快照等系统注入消息在 Markdown 中省略，原始 JSONL 中保留。')
md.push('')
md.push('---')
md.push('')

let renderedCalls = new Set()
let turn = 0
for (const event of events) {
  const data = event.data ?? {}
  switch (event.type) {
    case 'turn/start':
      turn = data.turn
      md.push(`\n# 第 ${turn} 轮\n`)
      break
    case 'user/message': {
      if (data.source?.kind !== 'user') break
      const text = (data.content ?? []).filter((block) => block.type === 'text').map((block) => block.text).join('\n')
      md.push(`## 🧑 用户\n\n${clip(text, 12_000)}`)
      break
    }
    case 'assistant/message': {
      const blocks = data.message?.content ?? []
      const texts = blocks.filter((block) => block.type === 'text').map((block) => block.text).join('\n\n')
      const reasoning = blocks.filter((block) => block.type === 'reasoning').map((block) => block.text).join('\n\n')
      if (reasoning) md.push(`> 🧠 思考（截断）\n>\n> ${clip(reasoning, 600).replaceAll('\n', '\n> ')}`)
      for (const block of blocks) {
        if (block.type !== 'tool-call') continue
        const callId = block.id ?? block.callId
        if (callId) renderedCalls.add(callId)
        md.push(`\n### 🔧 工具调用 \`${block.name}\`\n\n\`\`\`json\n${clip(block.arguments, 1_500)}\n\`\`\``)
      }
      if (texts) md.push(`## 🤖 助手\n\n${clip(texts, 30_000)}`)
      break
    }
    case 'tool/call': {
      const callId = data.callId
      if (renderedCalls.has(callId)) break
      renderedCalls.add(callId)
      md.push(`\n### 🔧 工具调用 \`${data.name}\`\n\n\`\`\`json\n${clip(data.arguments, 1_500)}\n\`\`\``)
      break
    }
    case 'tool/result': {
      const callId = data.message?.toolCallId ?? data.message?.source?.callId
      const name = callNames.get(callId) ?? '(tool)'
      const text = (data.message?.content ?? []).filter((block) => block.type === 'text').map((block) => block.text).join('\n')
      const errorMark = data.message?.isError ? ' ❌ error' : ''
      md.push(`\n#### ↩ 结果 \`${name}\`${errorMark}\n\n\`\`\`text\n${clip(text, 2_000)}\n\`\`\``)
      break
    }
    case 'turn/end':
      md.push(`\n---\n\n*第 ${data.turn ?? turn} 轮结束：${data.reason?.kind ?? 'completed'}（${localIso(exportedAt)} 导出）*\n`)
      break
    case 'deliverables/presented':
      md.push(`\n📎 交付文件：${(data.files ?? []).map((file) => `\`${basename(file.path ?? file)}\``).join('、')}\n`)
      break
    default:
      break
  }
}

const mdText = `${md.join('\n').replace(/\n{4,}/g, '\n\n\n')}\n`
const outDir = resolve(arg('out', `AI会话记录/${SESSION_ID.replace(/^session-/, '').slice(0, 8)}`))
mkdirSync(outDir, { recursive: true })
// 日目录标签（D1 / D2…）：标题与复跑命令按 --out 目录名生成，避免写死
const dayLabel = basename(outDir)
const outArg = dirname(outDir) === resolve('AI会话记录') ? `AI会话记录/${dayLabel}` : outDir
if (!/^D\d+$/.test(dayLabel)) {
  console.error(`提示：--out 目录名「${dayLabel}」不是 D1/D2 形式，README 标题按 ${dayLabel} 生成`)
}
const stem = SESSION_ID
writeFileSync(join(outDir, `${stem}.jsonl.zst`), raw)
writeFileSync(join(outDir, `${stem}.jsonl`), decompressed)
writeFileSync(join(outDir, `${stem}.md`), mdText)

const toolTable = Object.entries(toolCounts)
  .sort((a, b) => b[1] - a[1])
  .map(([name, count]) => `| \`${name}\` | ${count} |`)
  .join('\n')
const userMessages = events.filter((event) => event.type === 'user/message' && event.data?.source?.kind === 'user').length
const readme = `# AI 会话记录导出（${dayLabel}）

| 项 | 值 |
|---|---|
| 会话标题 | ${title.replaceAll('|', '\\|')} |
| 会话 ID | \`${SESSION_ID}\` |
| 工作目录 | \`${CWD}\` |
| 创建时间 | ${localIso(createdAt)}（Asia/Shanghai） |
| 导出时间 | ${localIso(exportedAt)}（Asia/Shanghai） |
| 事件总数 | ${events.length} |
| 轮数（turn） | ${turn} |
| 用户消息（真实） | ${userMessages} |
| 助手消息 | ${events.filter((event) => event.type === 'assistant/message').length} |
| 工具调用 | ${callNames.size}（isError ${errors} 次；命令非零退出 ${nonzeroExit} 次，已如实保留在记录里） |
| Token 合计 | input ${usage.inputTokens} / output ${usage.outputTokens} / cacheRead ${usage.cacheReadTokens} / total ${usage.totalTokens} |

## 文件

| 文件 | 说明 |
|---|---|
| \`${stem}.md\` | **人读版对话记录**（推荐先看）：用户/助手正文 + 工具调用 JSON + 结果（超长截断） |
| \`${stem}.jsonl\` | 解压后的完整事件流（NDJSON，含运行时上下文/技能目录/时间快照等系统注入，保真） |
| \`${stem}.jsonl.zst\` | 原始会话文件（DSH 多帧 zstd），与平台存储一致 |

## 工具调用统计

| 工具 | 次数 |
|---|---|
${toolTable}

## 如何复核/重新导出

原始会话文件在 DSH 的 session 存储里（\`$DSH_HOME/sessions/<项目编码>/<会话ID>/session.v4.jsonl.zstd\`）。
DSH 的 \`.zstd\` 是**多帧拼接**，直接 \`zstd -d\` 只能解第一帧；请用本目录上一级的 \`export-dsh-session.mjs\`：

\`\`\`bash
cd <工作区根目录>
node AI会话记录/export-dsh-session.mjs --session-id ${SESSION_ID} --out ${outArg}
\`\`\`

> 说明：本次导出在会话进行中执行，**最后一个 assistant 回复的收尾部分可能不在快照里**；如需包含完整末轮，可在会话结束后重跑上面的命令覆盖导出。
> 平台按项目一级目录编码会话根，工作区根为 \`${CWD}\`；不要修改 \`session.v4.jsonl.zstd\` 原件（导出器只读）。
`
writeFileSync(join(outDir, 'README.md'), readme)

console.log(`已导出会话 ${SESSION_ID}`)
console.log(`  目录：${outDir}`)
console.log(`  文件：${stem}.md / ${stem}.jsonl / ${stem}.jsonl.zst / README.md`)
console.log(`  事件 ${events.length} · 轮数 ${turn} · 工具调用 ${callNames.size}（isError ${errors} / 非零退出 ${nonzeroExit}）`)
console.log(`  大小：${(statSync(join(outDir, `${stem}.jsonl`)).size / 1024 / 1024).toFixed(1)} MB（jsonl） / ${(statSync(join(outDir, `${stem}.md`)).size / 1024).toFixed(0)} KB（md）`)
