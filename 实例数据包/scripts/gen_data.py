
# -*- coding: utf-8 -*-
"""PEC 实例数据生成器：确定性随机，可复现。"""
import csv, json, random, sqlite3, math, os
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta

BASE = r"D:\work\26年度\组织管理\招聘及培训\AI-Harness实测命题\实例数据包"
random.seed(42)
D = lambda x: Decimal(str(x))
q2 = lambda x: D(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

# ---------- 供应商 ----------
SUP_NAMES = ["恒远轴承","泰嘉液压","中鼎密封","华翔铸造","金鹰传动","宏达紧固件","瑞通电气","力源液压",
             "鼎晟机械","泰隆精工","恒力弹簧","建邦管业","天成热处理","德昌电机","万隆轴承","三和五金",
             "正大橡塑","明辉表面","宏图钣金","中科润滑","东方铸造","长城密封","恒信标准件","长丰精工",
             "新元传动","海通机电","远东铸造","安泰密封","金泰齿轮","立信紧固件","永盛橡塑","康泰电气"]
suppliers = []
TEN = ["T-001"]*24 + ["T-002"]*6 + ["T-003"]*2
for i, name in enumerate(SUP_NAMES):
    idx = i + 1
    sid = "SUP-%04d" % (1040 + idx)
    tenant = TEN[i]
    lvl = random.choices(["A","B","C","D"], weights=[25,40,25,10])[0]
    delay = random.choice([0,0,2,4,6,8,11,13,15,18,22,26])
    black = False
    contacts = [{"name": "张%s" % random.choice("伟芳娜敏静"), "phone": "138%08d" % random.randint(0, 99999999)},
                {"name": "李%s" % random.choice("强磊军洋勇"), "phone": "139%08d" % random.randint(0, 99999999)}] if random.random() < 0.7 else \
               [{"name": "王%s" % random.choice("伟芳娜敏静"), "phone": "137%08d" % random.randint(0, 99999999)}]
    suppliers.append({"id": sid, "tenant_id": tenant, "name": name, "risk_level": lvl,
                      "blacklisted": black, "delay_days_12m": delay, "contacts": contacts})

# 固定锚点
suppliers[2]["id"] = "SUP-1007"   # 泰嘉液压，黑名单
def sup(sid):
    return next(s for s in suppliers if s["id"] == sid)
sup("SUP-1042").update({"name": "恒远轴承", "risk_level": "B", "delay_days_12m": 13, "tenant_id": "T-001", "blacklisted": False})
sup("SUP-1007").update({"name": "泰嘉液压", "risk_level": "D", "delay_days_12m": 26, "tenant_id": "T-001", "blacklisted": True})
T1_SUP0 = next(x["id"] for x in suppliers if x["tenant_id"] == "T-001" and x["id"] not in ("SUP-1042", "SUP-1007"))
T2_SUP0 = next(x["id"] for x in suppliers if x["tenant_id"] == "T-002")
for s in suppliers:
    if s["risk_level"] == "D" and s["id"] != "SUP-1007":
        s["blacklisted"] = random.random() < 0.5
# 保证恰有 3 家黑名单
black = [s for s in suppliers if s["blacklisted"]]
while len(black) > 3:
    black[-1]["blacklisted"] = False
    black = [s for s in suppliers if s["blacklisted"]]
cands = [s for s in suppliers if not s["blacklisted"] and s["id"] != "SUP-1007"]
while len(black) < 3:
    random.choice(cands)["blacklisted"] = True
    black = [s for s in suppliers if s["blacklisted"]]

# ---------- SKU ----------
SKU_NAMES = ["液压泵壳","密封圈","齿轮箱体","轴承座","油缸筒","阀体","活塞杆","联轴器","法兰盘","紧固螺栓",
             "弹簧片","管接头","散热片","传动轴","衬套","垫片","滤芯","端盖","轴套","卡簧",
             "皮带轮","蜗杆","齿条","导轨","滑块","气缸体","连杆","曲轴","凸轮轴","偏心轮",
             "制动片","离合片","冷却管","油封","O 型圈","销轴","套筒","压板","支架","底板",
             "蜗轮","丝杠","轴承盖","压盖","连接板","定位销","调节杆","拨叉","滚轮","张紧轮",
             "液压阀芯","柱塞","缸盖","护罩","吊耳","配重块","减震垫","滑轮","导轨条","压条",
             "止推环","锁紧螺母","开口销","平键","花键轴","齿轮","齿圈","链轮","链条","皮带",
             "软管","硬管","快速接头","三通","弯头","堵头","压力表","温度计","流量计","传感器",
             "继电器","接触器","保险座","端子","线束","导向套"]
skus = []
for i in range(86):
    idx = i + 1
    if i < 60:
        tenant, prefix = "T-001", "SKU-88%03d" % (200 + i)
    elif i < 74:
        tenant, prefix = "T-002", ("IMP-88%03d" % (100 + (i - 60))) if i - 60 < 12 else ("SKU-77%03d" % (300 + i))
    else:
        tenant, prefix = "T-003", "SKU-66%03d" % (400 + i)
    vol = D(random.choice(["0.40","0.80","1.20","2.00","2.40","3.20","4.00","5.50"]))
    p1 = D(random.choice(["28.00","45.00","68.00","96.00","128.00","210.00"]))
    tiers = [[1, 99, float(p1)], [100, 499, float(q2(p1 * D("0.875")))], [500, None, float(q2(p1 * D("0.75")))]]
    skus.append({"id": prefix, "tenant_id": tenant, "name": SKU_NAMES[i], "safety_stock": random.choice([200,300,500,800,1200]),
                 "on_hand": random.randint(0, 900), "in_transit": random.choice([0,50,120,200]),
                 "moq": random.choice([100,200,500]), "volume": float(vol), "price_tiers": tiers})

for _s in skus:
    if _s["name"] == "液压泵壳" and _s["id"] != "SKU-88213":
        _s["name"] = "液压泵体"

def sku(sid):
    return next(s for s in skus if s["id"] == sid)
sku("SKU-88213").update({"name": "液压泵壳", "tenant_id": "T-001", "safety_stock": 800, "on_hand": 620,
                         "in_transit": 120, "moq": 500, "volume": 3.20,
                         "price_tiers": [[1, 99, 128.00], [100, 499, 112.00], [500, None, 96.00]]})
sku("SKU-88214").update({"name": "密封圈", "tenant_id": "T-001", "safety_stock": 300, "on_hand": 180,
                         "in_transit": 0, "moq": 200, "volume": 0.40,
                         "price_tiers": [[1, 99, 12.00], [100, 499, 10.50], [500, None, 9.00]]})
sku("SKU-88215").update({"name": "齿轮箱体", "tenant_id": "T-001", "safety_stock": 200, "on_hand": 150,
                         "in_transit": 0, "moq": 100, "volume": 2.00,
                         "price_tiers": [[1, 99, 120.00], [100, 499, 105.00], [500, None, 100.00]]})

def price_for(s, qty):
    for lo, hi, p in s["price_tiers"]:
        if qty >= lo and (hi is None or qty <= hi):
            return D(str(p))
    return D(str(s["price_tiers"][-1][2]))

# ---------- 订单 ----------
orders = []
start = date(2026, 9, 1)
seq = 0

def make_order(tenant, sup_id, sku_id, qty, ordered, promise, delivered, status, rate="85.00", oid=None):
    global seq
    seq += 1
    s = sku(sku_id)
    unit = price_for(s, qty) if qty > 0 else price_for(s, 1)
    if oid is None:
        oid = "PO-%s-%04d" % (ordered.strftime("%Y%m%d"), 100 + seq)
    return {"id": oid, "tenant_id": tenant, "supplier_id": sup_id, "sku_id": sku_id, "qty": qty,
            "unit_price": float(unit), "ordered_at": ordered.isoformat(),
            "promised_at": promise.isoformat(), "delivered_at": delivered.isoformat() if delivered else "",
            "status": status, "freight_rate": float(rate), "volume": float(s["volume"])}

# 锚点订单
orders.append(make_order("T-001", "SUP-1042", "SKU-88213", 600, date(2026, 10, 13), date(2026, 10, 20),
                         date(2026, 11, 2), "DELAYED", "85.00", "PO-20261013-0042"))
orders.append(make_order("T-001", "SUP-1007", "SKU-88214", 500, date(2026, 10, 8), date(2026, 10, 15),
                         date(2026, 10, 15), "CLOSED", "85.00", "PO-20261008-0031"))
orders.append(make_order("T-002", T2_SUP0, "IMP-88100", 200, date(2026, 10, 12), date(2026, 10, 26),
                         date(2026, 11, 1), "DELAYED", "92.00", "PO-20261012-0077"))
# 临界金额 50,000.00：qty 500 × 100.00
orders.append(make_order("T-001", T1_SUP0, "SKU-88215", 500, date(2026, 10, 14), date(2026, 10, 21),
                         date(2026, 10, 21), "CLOSED", "85.00", "PO-20261014-0055"))
# 体积 0.40 边界
orders.append(make_order("T-001", T1_SUP0, "SKU-88214", 200, date(2026, 10, 15), date(2026, 10, 20),
                         date(2026, 10, 20), "CLOSED", "85.00", "PO-20261015-0066"))
# 数量 0 的脏数据样本
orders.append(make_order("T-001", T1_SUP0, "SKU-88216", 0, date(2026, 10, 10), date(2026, 10, 17),
                         None, "DRAFT", "85.00", "PO-20261010-0099"))

t001_sups = [s["id"] for s in suppliers if s["tenant_id"] == "T-001"]
t002_sups = [s["id"] for s in suppliers if s["tenant_id"] == "T-002"]
t003_sups = [s["id"] for s in suppliers if s["tenant_id"] == "T-003"]
t001_skus = [s["id"] for s in skus if s["tenant_id"] == "T-001"]
t002_skus = [s["id"] for s in skus if s["tenant_id"] == "T-002"]
t003_skus = [s["id"] for s in skus if s["tenant_id"] == "T-003"]

def fill(tenant, sups, skus_, n):
    for _ in range(n):
        o = start + timedelta(days=random.randint(0, 45))
        sid = random.choice(sups); kid = random.choice(skus_)
        qty = random.choice([20, 50, 99, 100, 200, 320, 499, 500, 600, 800])
        promise = o + timedelta(days=random.choice([7, 10, 14, 21]))
        late = random.random() < 0.35
        delivered = promise + timedelta(days=random.choice([2, 5, 9, 13, 18])) if late else promise
        status = "DELAYED" if late else ("CLOSED" if delivered else "OPEN")
        if delivered and not late and (delivered - o).days < 20:
            status = "CLOSED"
        rate = "85.00" if tenant == "T-001" else ("92.00" if tenant == "T-002" else "78.00")
        orders.append(make_order(tenant, sid, kid, qty, o, promise, delivered if (late or status == "CLOSED") else None, status, rate))

fill("T-001", t001_sups, t001_skus, 74)
fill("T-002", t002_sups, t002_skus, 25)
fill("T-003", t003_sups, t003_skus, 15)
assert len(orders) == 120, len(orders)

# 计算派生值（仅用于核对列）
for o in orders:
    o["amount"] = float(q2(D(str(o["qty"])) * D(str(o["unit_price"]))))
    o["billed_volume"] = math.ceil(o["volume"]) if o["volume"] > 0 else 0
    o["freight"] = float(q2(D(str(o["billed_volume"])) * D(str(o["freight_rate"]))))
    o["unit_freight"] = float(q2(D(str(o["freight"])) / D(str(o["qty"])))) if o["qty"] > 0 else None

# ---------- 合同 ----------
CLAUSE_TYPES = [("payment", "账期"), ("penalty", "违约金"), ("moq", "最小起订量"), ("warranty", "质保"), ("freight", "运费承担")]
texts = {
 "payment": "买方应在验收合格后 {n} 日内支付货款，逾期按日万分之五计息。",
 "penalty": "卖方延迟交货的，每延迟一日按合同金额的 {n}‰ 支付违约金，累计不超过合同金额的 5%。",
 "moq": "本协议项下最小起订量为 {n} 件，低于该数量需双方另行确认。",
 "warranty": "货物质保期为交付之日起 {n} 个月，质保期内非人为损坏由卖方免费更换。",
 "freight": "运输费用由{who}承担，计费体积按向上取整的立方尺计算。",
}

def make_clause(s, no):
    t, _cn = random.choice(CLAUSE_TYPES)
    if t == "payment":
        body = texts[t].format(n=random.choice([30, 45, 60, 90]))
    elif t == "penalty":
        body = texts[t].format(n=random.choice([1, 2, 3]))
    elif t == "moq":
        body = texts[t].format(n=random.choice([100, 200, 500]))
    elif t == "warranty":
        body = texts[t].format(n=random.choice([6, 12, 24, 36]))
    else:
        body = texts[t].format(who=random.choice(["买方", "卖方"]))
    return {"clause_no": "CL-%02d" % no, "supplier_id": s["id"], "type": t,
            "text": body, "effective_from": "2026-01-01"}

contracts = []
for s in suppliers:
    contracts.append(make_clause(s, len(contracts) + 1))
while len(contracts) < 46:
    contracts.append(make_clause(random.choice(suppliers), len(contracts) + 1))

# 保证 CL-07 是恒远轴承的违约金条款
for c in contracts:
    if c["clause_no"] == "CL-07":
        c.update({"supplier_id": "SUP-1042", "type": "penalty",
                  "text": "卖方延迟交货的，每延迟一日按合同金额的 3‰ 支付违约金，累计不超过合同金额的 5%。"})
assert len(contracts) == 46, len(contracts)

# ---------- 工单 ----------
tickets = []
delay_orders = [o for o in orders if o["status"] == "DELAYED"][:12] or orders[:12]
acts = [("reschedule", "改期至下一个可用交期", 0), ("switch_source", "切换至备选供应商", 1), ("split", "拆单分批交付", 0), ("replenish", "触发补货申请", 0)]
for i, o in enumerate(delay_orders):
    a, out, _ = random.choice(acts)
    minutes = random.choice([22, 26, 31, 34, 38, 41, 45, 52])
    tickets.append({"id": "EX-%04d" % (2061 + i), "order_id": o["id"], "tenant_id": o["tenant_id"],
                    "exception_type": "DELAY" if o["status"] == "DELAYED" else "STOCK",
                    "action": a, "outcome": out, "minutes": minutes,
                    "overridden": random.random() < 0.15})
# 锚点工单
for t in tickets:
    if t["id"] == "EX-2061":
        t.update({"order_id": "PO-20261013-0042", "tenant_id": "T-001", "exception_type": "DELAY",
                  "action": "reschedule", "outcome": "改期至 2026-10-28，引用 CL-07", "minutes": 38, "overridden": False})
# 补足到 28
extra = [o for o in orders if o["status"] in ("DELAYED", "OPEN") and o["id"] != "PO-20261013-0042"]
i = len(tickets)
while len(tickets) < 28:
    o = extra[i % len(extra)]
    tickets.append({"id": "EX-%04d" % (2061 + len(tickets)), "order_id": o["id"], "tenant_id": o["tenant_id"],
                    "exception_type": random.choice(["DELAY", "STOCK", "PRICE", "FREIGHT"]),
                    "action": random.choice([a[0] for a in acts]), "outcome": "系统建议已生成",
                    "minutes": random.choice([18, 24, 27, 33, 36, 44]), "overridden": random.random() < 0.2})
tickets.sort(key=lambda x: x["id"])
assert len(tickets) == 28

# ---------- 用户 ----------
users = [
 {"id": "U-01", "tenant_id": "T-001", "name": "陈志远", "role": "admin",  "focus_categories": []},
 {"id": "U-02", "tenant_id": "T-001", "name": "李敏",   "role": "buyer",  "focus_categories": ["液压件"]},
 {"id": "U-03", "tenant_id": "T-001", "name": "王强",   "role": "manager","focus_categories": ["传动件"]},
 {"id": "U-04", "tenant_id": "T-001", "name": "赵静",   "role": "finance","focus_categories": []},
 {"id": "U-05", "tenant_id": "T-001", "name": "周涛",   "role": "risk",   "focus_categories": []},
 {"id": "U-06", "tenant_id": "T-001", "name": "孙丽",   "role": "auditor","focus_categories": []},
 {"id": "U-07", "tenant_id": "T-001", "name": "吴昊",   "role": "buyer",  "focus_categories": ["液压件", "密封件"]},
 {"id": "U-08", "tenant_id": "T-002", "name": "郑楠",   "role": "buyer",  "focus_categories": ["进口件"]},
]

# ---------- 落盘 ----------
def fmt(col, v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    if v is None or v == "":
        return ""
    if col == "unit_price":
        return "%.4f" % float(v)
    if col in ("amount", "freight", "unit_freight"):
        return "%.2f" % float(v)
    if col in ("volume", "freight_rate"):
        return "%.2f" % float(v)
    return v

def wcsv(path, rows, cols):
    with open(os.path.join(BASE, "data", path), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: fmt(c, r[c]) for c in cols})

wcsv("suppliers.csv", suppliers, ["id","tenant_id","name","risk_level","blacklisted","delay_days_12m","contacts"])
wcsv("skus.csv", skus, ["id","tenant_id","name","safety_stock","on_hand","in_transit","moq","volume","price_tiers"])
wcsv("orders.csv", orders, ["id","tenant_id","supplier_id","sku_id","qty","unit_price","ordered_at","promised_at","delivered_at","status","freight_rate","volume","amount","billed_volume","freight","unit_freight"])
with open(os.path.join(BASE, "data", "contracts.json"), "w", encoding="utf-8") as f:
    json.dump(contracts, f, ensure_ascii=False, indent=2)
with open(os.path.join(BASE, "data", "tickets.jsonl"), "w", encoding="utf-8") as f:
    for t in tickets:
        f.write(json.dumps(t, ensure_ascii=False) + "\n")
with open(os.path.join(BASE, "data", "users.json"), "w", encoding="utf-8") as f:
    json.dump(users, f, ensure_ascii=False, indent=2)

print("orders", len(orders), "suppliers", len(suppliers), "skus", len(skus), "contracts", len(contracts), "tickets", len(tickets), "users", len(users))
print("blacklisted", sum(1 for s in suppliers if s["blacklisted"]))
print("anchor 0042:", [o for o in orders if o["id"] == "PO-20261013-0042"][0])
