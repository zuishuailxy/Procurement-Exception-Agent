
# -*- coding: utf-8 -*-
"""数据自检：锚点、口径、租户一致性、A/B 样本量。"""
import sqlite3, json, math, os
from decimal import Decimal, ROUND_HALF_UP
BASE = r"D:\work\26年度\组织管理\招聘及培训\AI-Harness实测命题\实例数据包"
con = sqlite3.connect(os.path.join(BASE, "db", "pec.db"))
con.row_factory = sqlite3.Row
ok = True
def check(name, cond, detail=""):
    global ok
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  <<< " + str(detail)))
    if not cond: ok = False

n = lambda s: con.execute(s).fetchone()[0]
check("表行数", n("select count(*) from orders") == 120 and n("select count(*) from suppliers") == 32
      and n("select count(*) from skus") == 86 and n("select count(*) from contracts") == 46
      and n("select count(*) from tickets") == 28 and n("select count(*) from users") == 8)

o = con.execute("select * from orders where id='PO-20261013-0042'").fetchone()
amt = (Decimal(str(o["qty"])) * Decimal(str(o["unit_price"]))).quantize(Decimal("0.01"), ROUND_HALF_UP)
check("锚点 0042 金额", amt == Decimal("57600.00"), amt)
check("锚点 0042 进位体积", o["billed_volume"] == math.ceil(o["volume"]) == 4, o["billed_volume"])
check("锚点 0042 总运费", Decimal(str(o["freight"])) == Decimal("340.00"), o["freight"])
check("锚点 0042 计件运费", Decimal(str(o["unit_freight"])) == Decimal("0.57"), o["unit_freight"])
check("锚点 0042 交期延迟", o["promised_at"] == "2026-10-20" and o["delivered_at"] == "2026-11-02" and o["status"] == "DELAYED")

o2 = con.execute("select * from orders where id='PO-20261014-0055'").fetchone()
check("临界 5 万", Decimal(str(o2["amount"])) == Decimal("50000.00"), o2["amount"])
o3 = con.execute("select * from orders where id='PO-20261015-0066'").fetchone()
check("体积 0.40 进位", o3["billed_volume"] == 1 and Decimal(str(o3["freight"])) == Decimal("85.00"), o3["freight"])

bad = []
for r in con.execute("select o.id, o.qty, o.unit_price, s.price_tiers from orders o join skus s on s.id=o.sku_id"):
    if r["qty"] <= 0: continue
    tiers = json.loads(r["price_tiers"]); q = r["qty"]; want = None
    for lo, hi, p in tiers:
        if q >= lo and (hi is None or q <= hi): want = Decimal(str(p)); break
    if want is not None and Decimal(str(r["unit_price"])) != want: bad.append((r["id"], r["unit_price"], str(want)))
check("单价与阶梯价一致", len(bad) == 0, bad[:3])

bad2 = [r["id"] for r in con.execute("select o.id from orders o join suppliers s on s.id=o.supplier_id where s.tenant_id <> o.tenant_id")]
check("订单-供应商租户一致", len(bad2) == 0, bad2[:3])
bad3 = [r["id"] for r in con.execute("select o.id from orders o join skus k on k.id=o.sku_id where k.tenant_id <> o.tenant_id")]
check("订单-SKU 租户一致", len(bad3) == 0, bad3[:3])

check("黑名单 3 家", n("select count(*) from suppliers where blacklisted=1") == 3)
check("CL-07 属于恒远轴承", con.execute("select supplier_id, type from contracts where clause_no='CL-07'").fetchone()["supplier_id"] == "SUP-1042")

ab = n("""select count(*) from orders o join suppliers s on s.id=o.supplier_id
          where o.status='DELAYED' and o.amount < 50000 and s.blacklisted=0""")
check("A/B 同类样本 ≥ 8", ab >= 8, ab)

orphan = n("select count(*) from tickets t left join orders o on o.id=t.order_id where o.id is null")
check("工单均指向存在订单", orphan == 0, orphan)
check("FTS 可检索", n("select count(*) from contracts_fts where contracts_fts match '违约金'") > 0)

print("\nA/B 可用样本数:", ab)
print("黑名单供应商:", [r["id"] for r in con.execute("select id from suppliers where blacklisted=1")])
print("结果:", "全部通过" if ok else "存在失败项")
con.close()
