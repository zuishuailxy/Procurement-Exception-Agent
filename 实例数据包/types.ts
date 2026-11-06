// PEC 实例数据包 · TypeScript 类型
// 与 data/*.csv|json 一一对应。金额相关字段在数据里是 number，
// 业务计算请用十进制库（decimal.js / big.js），不要直接做浮点累加。

export type TenantId = 'T-001' | 'T-002' | 'T-003'
export type RiskLevel = 'A' | 'B' | 'C' | 'D'
export type OrderStatus = 'OPEN' | 'SHIPPED' | 'DELAYED' | 'CLOSED' | 'DRAFT'
export type ClauseType = 'payment' | 'penalty' | 'moq' | 'warranty' | 'freight'
export type TicketAction = 'reschedule' | 'switch_source' | 'split' | 'replenish'
export type Role = 'admin' | 'buyer' | 'manager' | 'finance' | 'risk' | 'auditor'

export interface Contact {
  name: string
  phone: string   // 已含掩码前的原始值，工具出口需按角色脱敏
}

export interface Supplier {
  id: string
  tenant_id: TenantId
  name: string
  risk_level: RiskLevel
  blacklisted: boolean
  delay_days_12m: number
  contacts: Contact[]
}

/** [下限, 上限, 单价]；上限为 null 表示无上限 */
export type PriceTier = [number, number | null, number]

export interface Sku {
  id: string
  tenant_id: TenantId
  name: string
  safety_stock: number
  on_hand: number
  in_transit: number
  moq: number
  volume: number
  price_tiers: PriceTier[]
}

export interface Order {
  id: string
  tenant_id: TenantId
  supplier_id: string
  sku_id: string
  qty: number
  unit_price: number
  ordered_at: string
  promised_at: string
  delivered_at: string | null
  status: OrderStatus
  freight_rate: number
  volume: number
  /** 派生列，仅供核对；工具须自行计算 */
  amount: number
  billed_volume: number
  freight: number
  unit_freight: number | null
}

export interface Contract {
  clause_no: string
  supplier_id: string
  type: ClauseType
  text: string
  effective_from: string
}

export interface Ticket {
  id: string
  order_id: string
  tenant_id: TenantId
  exception_type: 'DELAY' | 'STOCK' | 'PRICE' | 'FREIGHT' | 'RISK'
  action: TicketAction
  outcome: string
  minutes: number
  overridden: boolean
}

export interface User {
  id: string
  tenant_id: TenantId
  name: string
  role: Role
  focus_categories: string[]
}

/** 工具返回统一带上来源，供「引用可溯」校验 */
export interface Provenance {
  table: 'orders' | 'suppliers' | 'skus' | 'contracts' | 'tickets' | 'users'
  rowId: string
}

export interface ToolResult<T> {
  data: T
  provenance: Provenance[]
}
