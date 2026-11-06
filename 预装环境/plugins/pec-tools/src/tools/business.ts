import { defineTool } from '@deepseek-ai/dsh-tools'
import { ToolError } from '../errors.js'

const notImplemented = (name: string) => {
  throw new ToolError('NOT_IMPLEMENTED', `${name} 尚未实现，请补全 execute`)
}

/**
 * 六个业务工具：schema 已给出，execute 待实现。
 * 交付要求：
 *  1. 补全 description（适用 / 不适用场景各一句）
 *  2. 返回 { data, provenance }，provenance 精确到表 + 行 id
 *  3. 错误码只用 NOT_FOUND / INVALID_ARGUMENT / POLICY_DENIED / UPSTREAM_TIMEOUT
 *  4. 金额与体积一律用十进制库计算，禁止浮点
 */

export const orderLookup = defineTool({
  name: 'order.lookup',
  description: '查询采购订单与履约状态。',   // TODO: 补全适用与不适用场景
  parameters: {
    orderId: { type: 'string', required: true, description: '采购订单号，如 PO-20261013-0042' },
    tenantId: { type: 'string', required: true, description: '运行时注入，模型不可自填' },
  },
  output: { schema: { type: 'object' }, render: () => [{ type: 'text', text: '' }] },
  async execute(_args, _exec) { return notImplemented('order.lookup') as never },
})

export const supplierProfile = defineTool({
  name: 'supplier.profile',
  description: '查询供应商画像：等级、黑名单、近 12 月延迟天数。',
  parameters: {
    supplierId: { type: 'string', required: true, description: '供应商编码，如 SUP-1042' },
    tenantId: { type: 'string', required: true, description: '运行时注入' },
  },
  output: { schema: { type: 'object' }, render: () => [{ type: 'text', text: '' }] },
  async execute(_args, _exec) { return notImplemented('supplier.profile') as never },
})

export const pricingQuote = defineTool({
  name: 'pricing.quote',
  description: '按 SKU 与数量计算阶梯价、金额与税额。',
  parameters: {
    skuId: { type: 'string', required: true, description: 'SKU 编码' },
    qty: { type: 'integer', required: true, description: '采购数量，必须 > 0' },
  },
  output: { schema: { type: 'object' }, render: () => [{ type: 'text', text: '' }] },
  async execute(_args, _exec) { return notImplemented('pricing.quote') as never },
})

export const freightCalc = defineTool({
  name: 'freight.calc',
  description: '按体积与物流费单价计算计费体积、总运费与计件运费。',
  parameters: {
    orderId: { type: 'string', required: true, description: '订单号' },
    qty: { type: 'integer', required: true, description: '数量，为 0 时返回 E_DIV_ZERO' },
  },
  output: { schema: { type: 'object' }, render: () => [{ type: 'text', text: '' }] },
  async execute(_args, _exec) { return notImplemented('freight.calc') as never },
})

export const contractSearch = defineTool({
  name: 'contract.search',
  description: '检索合同条款，返回条款号、正文与出处。',
  parameters: {
    supplierId: { type: 'string', required: true, description: '供应商编码' },
    keyword: { type: 'string', required: true, description: '检索词，如「违约金」' },
  },
  output: { schema: { type: 'object' }, render: () => [{ type: 'text', text: '' }] },
  async execute(_args, _exec) { return notImplemented('contract.search') as never },
})

export const ticketSimilar = defineTool({
  name: 'ticket.similar',
  description: '召回相似历史工单，返回处置动作与相似度。',
  parameters: {
    exceptionType: { type: 'string', required: true, description: 'DELAY / STOCK / PRICE / FREIGHT / RISK' },
    supplierId: { type: 'string', description: '可选的供应商过滤' },
    amountMax: { type: 'number', description: '可选：金额上限（元）' },
  },
  output: { schema: { type: 'object' }, render: () => [{ type: 'text', text: '' }] },
  async execute(_args, _exec) { return notImplemented('ticket.similar') as never },
})
