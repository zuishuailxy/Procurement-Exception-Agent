
# -*- coding: utf-8 -*-
"""从 data/ 构建 SQLite（含 FTS5），并输出 schema.sql。"""
import csv, json, sqlite3, os

BASE = r"D:\work\26年度\\组织管理\招聘及培训\AI-Harness实测命题\实例数据包".replace("\\\\", "\\")
DB = os.path.join(BASE, "db", "pec.db")
if os.path.exists(DB):
    os.remove(DB)

con = sqlite3.connect(DB)
con.executescript("""
PRAGMA foreign_keys = ON;
CREATE TABLE suppliers (
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, name TEXT NOT NULL,
  risk_level TEXT NOT NULL CHECK (risk_level IN ('A','B','C','D')),
  blacklisted INTEGER NOT NULL DEFAULT 0, delay_days_12m INTEGER NOT NULL DEFAULT 0,
  contacts TEXT NOT NULL
);
CREATE TABLE skus (
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, name TEXT NOT NULL,
  safety_stock INTEGER NOT NULL, on_hand INTEGER NOT NULL, in_transit INTEGER NOT NULL,
  moq INTEGER NOT NULL, volume REAL NOT NULL, price_tiers TEXT NOT NULL
);
CREATE TABLE orders (
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
  supplier_id TEXT NOT NULL REFERENCES suppliers(id),
  sku_id TEXT NOT NULL REFERENCES skus(id),
  qty INTEGER NOT NULL, unit_price REAL NOT NULL,
  ordered_at TEXT NOT NULL, promised_at TEXT NOT NULL, delivered_at TEXT,
  status TEXT NOT NULL CHECK (status IN ('OPEN','SHIPPED','DELAYED','CLOSED','DRAFT')),
  freight_rate REAL NOT NULL, volume REAL NOT NULL,
  amount REAL, billed_volume INTEGER, freight REAL, unit_freight REAL
);
CREATE TABLE contracts (
  clause_no TEXT PRIMARY KEY, supplier_id TEXT NOT NULL REFERENCES suppliers(id),
  type TEXT NOT NULL, text TEXT NOT NULL, effective_from TEXT NOT NULL
);
CREATE TABLE tickets (
  id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(id), tenant_id TEXT NOT NULL,
  exception_type TEXT NOT NULL, action TEXT NOT NULL, outcome TEXT NOT NULL,
  minutes INTEGER NOT NULL, overridden INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE users (
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, name TEXT NOT NULL,
  role TEXT NOT NULL, focus_categories TEXT NOT NULL
);
CREATE INDEX idx_orders_tenant ON orders(tenant_id);
CREATE INDEX idx_orders_supplier ON orders(supplier_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_tickets_order ON tickets(order_id);
CREATE INDEX idx_contracts_supplier ON contracts(supplier_id);
""")

def rows(name):
    with open(os.path.join(BASE, "data", name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

sup = rows("suppliers.csv")
sku = rows("skus.csv")
ord_ = rows("orders.csv")

con.executemany("INSERT INTO suppliers VALUES (?,?,?,?,?,?,?)",
    [(r["id"], r["tenant_id"], r["name"], r["risk_level"], 1 if str(r["blacklisted"]).lower() in ("true","1") else 0,
      int(r["delay_days_12m"]), r["contacts"]) for r in sup])
con.executemany("INSERT INTO skus VALUES (?,?,?,?,?,?,?,?,?)",
    [(r["id"], r["tenant_id"], r["name"], int(r["safety_stock"]), int(r["on_hand"]), int(r["in_transit"]),
      int(r["moq"]), float(r["volume"]), r["price_tiers"]) for r in sku])
con.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
    [(r["id"], r["tenant_id"], r["supplier_id"], r["sku_id"], int(r["qty"]), float(r["unit_price"]),
      r["ordered_at"], r["promised_at"], r["delivered_at"] or None, r["status"], float(r["freight_rate"]),
      float(r["volume"]), float(r["amount"]), int(r["billed_volume"]), float(r["freight"]),
      float(r["unit_freight"]) if r["unit_freight"] else None) for r in ord_])

contracts = json.load(open(os.path.join(BASE, "data", "contracts.json"), encoding="utf-8"))
con.executemany("INSERT INTO contracts VALUES (?,?,?,?,?)",
    [(c["clause_no"], c["supplier_id"], c["type"], c["text"], c["effective_from"]) for c in contracts])

tickets = [json.loads(l) for l in open(os.path.join(BASE, "data", "tickets.jsonl"), encoding="utf-8")]
con.executemany("INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?)",
    [(t["id"], t["order_id"], t["tenant_id"], t["exception_type"], t["action"], t["outcome"],
      int(t["minutes"]), 1 if t["overridden"] else 0) for t in tickets])

users = json.load(open(os.path.join(BASE, "data", "users.json"), encoding="utf-8"))
con.executemany("INSERT INTO users VALUES (?,?,?,?,?)",
    [(u["id"], u["tenant_id"], u["name"], u["role"], json.dumps(u["focus_categories"], ensure_ascii=False)) for u in users])

# FTS5：条款全文检索（中文用 trigram，支持子串匹配）
try:
    con.executescript("""
    CREATE VIRTUAL TABLE contracts_fts USING fts5(
      clause_no UNINDEXED, supplier_id UNINDEXED, type, text,
      tokenize = 'trigram'
    );
    """)
    tokenizer = "trigram"
except sqlite3.OperationalError:
    con.executescript("""
    CREATE VIRTUAL TABLE contracts_fts USING fts5(
      clause_no UNINDEXED, supplier_id UNINDEXED, type, text,
      tokenize = 'unicode61'
    );
    """)
    tokenizer = "unicode61"
con.execute("INSERT INTO contracts_fts (clause_no, supplier_id, type, text) SELECT clause_no, supplier_id, type, text FROM contracts")
print("fts tokenizer:", tokenizer)
con.commit()

import re
dump = list(con.iterdump())
base_re = re.compile(r'^INSERT INTO "?(suppliers|skus|orders|contracts|tickets|users)"? ')
ddl = [l for l in dump if l.startswith("CREATE") and "contracts_fts_" not in l]
seed = [l for l in dump if base_re.match(l)]
seed.append("INSERT INTO contracts_fts (clause_no, supplier_id, type, text) SELECT clause_no, supplier_id, type, text FROM contracts;")
with open(os.path.join(BASE, "db", "schema.sql"), "w", encoding="utf-8") as f:
    f.write("PRAGMA foreign_keys = ON;\n\n" + "\n".join(ddl) + "\n")
with open(os.path.join(BASE, "db", "seed.sql"), "w", encoding="utf-8") as f:
    f.write("BEGIN;\n" + "\n".join(seed) + "\nCOMMIT;\n")
con.close()
print("db ok", DB)
