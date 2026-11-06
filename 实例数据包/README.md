# PEC 实例数据包 v1.0

采购异常处置 Agent 的六份实例数据，供 DSH 插件开发者对接使用。
数据为虚构，口径与《业务案例实测任务书 v3.1》附录 A/B 一致。

## 目录

```
实例数据包/
├── data/
│   ├── suppliers.csv     32 行
│   ├── skus.csv          86 行
│   ├── orders.csv       120 行
│   ├── contracts.json    46 条
│   ├── tickets.jsonl     28 条
│   └── users.json         8 个
├── db/
│   ├── pec.db            SQLite（含 FTS5 trigram 索引）
│   ├── schema.sql        建表语句
│   └── seed.sql          种子数据
├── scripts/
│   ├── gen_data.py       可复现生成器（seed 42）
│   ├── build_db.py       从 data/ 建库
│   └── verify.py         数据自检（16 项）
└── types.ts              TypeScript 类型
```

## 快速开始

```bash
# 直接查询
sqlite3 db/pec.db "select id, qty, amount from orders limit 5"

# 从零重建（等价于 scripts/build_db.py）
sqlite3 db/pec.db < db/schema.sql
sqlite3 db/pec.db < db/seed.sql

# 重新生成与自检
python scripts/gen_data.py && python scripts/build_db.py && python scripts/verify.py
```

Node 侧用 better-sqlite3：`new Database('db/pec.db', { readonly: true })`。

## 表结构

| 表 | 主键 | 关键字段 |
|---|---|---|
| suppliers | id | tenant_id, name, risk_level(A–D), blacklisted(0/1), delay_days_12m, contacts(JSON) |
| skus | id | tenant_id, name, safety_stock, on_hand, in_transit, moq, volume, price_tiers(JSON) |
| orders | id | tenant_id, supplier_id, sku_id, qty, unit_price, ordered_at, promised_at, delivered_at, status, freight_rate, volume, amount, billed_volume, freight, unit_freight |
| contracts | clause_no | supplier_id, type(payment/penalty/moq/warranty/freight), text, effective_from |
| tickets | id | order_id, tenant_id, exception_type, action, outcome, minutes, overridden |
| users | id | tenant_id, name, role(admin/buyer/manager/finance/risk/auditor), focus_categories(JSON) |

`orders` 里 `amount / billed_volume / freight / unit_freight` 是**派生列，仅供核对**。
工具实现必须自己按 R1–R3 重算，不要把派生列当输入。

`price_tiers` 形如 `[[1,99,128.0],[100,499,112.0],[500,null,96.0]]`，区间为闭区间，`null` 表示无上限。

## 数据口径

| 约束 | 含义 |
|---|---|
| 单价 | 每张订单的 `unit_price` 都等于该数量落在的阶梯价 |
| 金额 | `amount = qty × unit_price`，ROUND_HALF_UP 两位 |
| 进位 | `billed_volume = ceil(volume)`，总运费 = 计费体积 × `freight_rate` |
| 计件 | `unit_freight = 总运费 ÷ qty`，两位；`qty = 0` 时应返回 E_DIV_ZERO |
| 租户 | 订单的 `tenant_id` 与其供应商、SKU 的 `tenant_id` 必然一致 |
| 引用 | 条款号形如 CL-01..CL-46，全部可在 contracts 中命中 |

## 锚点样例（评测与演示直接用）

| 订单 | 关键值 | 期望 |
|---|---|---|
| PO-20261013-0042 | SUP-1042 恒远轴承(B) / SKU-88213 / 600 件 | 金额 57,600.00；计费体积 4；运费 340.00；计件 0.57；承诺 10-20、实际 11-02，延迟 13 天 |
| PO-20261014-0055 | SKU-88215 / 500 件 × 100.00 | 金额恰好 50,000.00（审批临界，应走主管） |
| PO-20261015-0066 | SKU-88214 / 体积 0.40 | 计费体积 1，运费 85.00（不是 34.00） |
| PO-20261010-0099 | qty = 0，status = DRAFT | 计件运费应报 E_DIV_ZERO，不得返回 0 |

CL-07 是恒远轴承的违约金条款（3‰/日，上限 5%）。

## 租户与黑名单

- T-001 集团本部：24 家供应商、60 个 SKU、80 张订单
- T-002 海外事业部：6 家供应商、14 个 SKU（其中 12 个 IMP- 进口件）
- T-003 经销伙伴：2 家供应商、12 个 SKU、15 张订单
- 黑名单 3 家：SUP-1007（泰嘉液压，D 级）、SUP-1062、SUP-1065

跨租户查询应返回 POLICY_DENIED，不是空结果。

## 评测与 A/B 用法

同类工单可用下面这条 SQL 筛（当前命中 31 条，建议取 8 条做对照）：

```sql
select o.id, o.qty, o.unit_price, o.amount, s.delay_days_12m
from orders o join suppliers s on s.id = o.supplier_id
where o.status = 'DELAYED' and o.amount < 50000 and s.blacklisted = 0
order by o.id
limit 8;
```

条款检索示例（FTS5 trigram，支持 ≥3 字子串）：

```sql
select c.clause_no, c.supplier_id, c.text
from contracts_fts f join contracts c on c.clause_no = f.clause_no
where contracts_fts match '违约金' and c.supplier_id = 'SUP-1042';
```

## 刻意保留的边界数据

- `PO-20261010-0099`：qty = 0 的脏数据（DRAFT），用于验证除零
- `PO-20261013-0042` 等延迟单：`delivered_at` 晚于 `promised_at`
- 部分订单 `delivered_at` 为空（未交付），解析时要容忍 NULL
- `volume = 0.40` 与 `3.20`：验证向上取整
- 金额恰好 50,000.00：验证审批阈值边界

## 版本

v1.0 / 2026-10 / 生成器 seed = 42。改动数据请同时更新 `scripts/verify.py` 的期望值。
