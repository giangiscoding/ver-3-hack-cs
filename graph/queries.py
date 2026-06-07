"""
Cypher queries — mô hình đồ thị + phát hiện gian lận.

Mô hình:
  (:Company {mst, phan_khuc, nganh})
  (:Owner   {id, ten, flag})
  (:Owner)-[:OWNS {phan_tram}]->(:Company)          # sở hữu thường
  (:Owner)-[:OWNS_CROSS {phan_tram}]->(:Company)    # sở hữu chéo (shadow controller)
  (:Company)-[:SAME_ADDRESS]->(:Company)            # cùng địa chỉ (shell)
  (:Company)-[:INTERNAL_TXN {gia_tri}]->(:Company)  # giao dịch nội bộ (circular)
  (:Company)-[:TRADE {gia_tri}]->(:Company)         # giao dịch thương mại hợp lệ

Map từ graph.json edge "type":
  so_huu→OWNS · so_huu_cheo→OWNS_CROSS · cung_dia_chi→SAME_ADDRESS
  giao_dich_noi_bo→INTERNAL_TXN · giao_dich_thuong_mai→TRADE
"""

EDGE_TYPE_MAP = {
    "so_huu": "OWNS",
    "so_huu_cheo": "OWNS_CROSS",
    "cung_dia_chi": "SAME_ADDRESS",
    "giao_dich_noi_bo": "INTERNAL_TXN",
    "giao_dich_thuong_mai": "TRADE",
}

# ── Schema ────────────────────────────────────────────────────────────────────
CONSTRAINTS = [
    "CREATE CONSTRAINT company_mst IF NOT EXISTS FOR (c:Company) REQUIRE c.mst IS UNIQUE",
    "CREATE CONSTRAINT owner_id IF NOT EXISTS FOR (o:Owner) REQUIRE o.id IS UNIQUE",
]

CLEAR_ALL = "MATCH (n) DETACH DELETE n"

# ── Bulk load (UNWIND batches) ────────────────────────────────────────────────
LOAD_COMPANIES = """
UNWIND $rows AS row
MERGE (c:Company {mst: row.mst})
SET c.phan_khuc = row.phan_khuc, c.nganh = row.nganh
"""

LOAD_OWNERS = """
UNWIND $rows AS row
MERGE (o:Owner {id: row.id})
SET o.ten = row.ten, o.flag = row.flag
"""

# Một query cho mỗi loại quan hệ (Cypher không tham số hoá được rel type)
LOAD_OWNS = """
UNWIND $rows AS row
MATCH (o:Owner {id: row.source}), (c:Company {mst: row.target})
MERGE (o)-[r:OWNS]->(c)
SET r.phan_tram = row.phan_tram
"""
LOAD_OWNS_CROSS = """
UNWIND $rows AS row
MATCH (o:Owner {id: row.source}), (c:Company {mst: row.target})
MERGE (o)-[r:OWNS_CROSS]->(c)
SET r.phan_tram = row.phan_tram
"""
LOAD_SAME_ADDRESS = """
UNWIND $rows AS row
MATCH (a:Company {mst: row.source}), (b:Company {mst: row.target})
MERGE (a)-[:SAME_ADDRESS]->(b)
"""
LOAD_INTERNAL_TXN = """
UNWIND $rows AS row
MATCH (a:Company {mst: row.source}), (b:Company {mst: row.target})
MERGE (a)-[r:INTERNAL_TXN]->(b)
SET r.gia_tri = row.gia_tri_mn_vnd
"""
LOAD_TRADE = """
UNWIND $rows AS row
MATCH (a:Company {mst: row.source}), (b:Company {mst: row.target})
MERGE (a)-[r:TRADE]->(b)
SET r.gia_tri = row.gia_tri_mn_vnd
"""

LOAD_BY_REL = {
    "OWNS": LOAD_OWNS, "OWNS_CROSS": LOAD_OWNS_CROSS, "SAME_ADDRESS": LOAD_SAME_ADDRESS,
    "INTERNAL_TXN": LOAD_INTERNAL_TXN, "TRADE": LOAD_TRADE,
}

# ── Phát hiện gian lận (theo MST) ─────────────────────────────────────────────

# Pattern 1: Shadow controller — một chủ sở hữu nắm chéo ≥2 DN (gồm DN đang xét)
DETECT_SHADOW_CONTROLLER = """
MATCH (o:Owner)-[:OWNS_CROSS]->(:Company {mst: $mst})
MATCH (o)-[:OWNS_CROSS]->(other:Company)
WITH o, collect(DISTINCT other.mst) AS companies
WHERE size(companies) >= 2
RETURN o.id AS controller, o.ten AS ten, o.flag AS flag, companies
ORDER BY size(companies) DESC LIMIT 1
"""

# Pattern 2: Shell company — chia sẻ địa chỉ với DN khác
DETECT_SHELL = """
MATCH (c:Company {mst: $mst})-[:SAME_ADDRESS]-(other:Company)
RETURN collect(DISTINCT other.mst) AS companies
"""

# Pattern 3: Circular transaction — vòng giao dịch nội bộ quay về chính nó
# (vòng trong data có thể dài tới 8 DN → cần *1..10)
DETECT_CIRCULAR = """
MATCH path = (c:Company {mst: $mst})-[:INTERNAL_TXN*1..10]->(c)
RETURN [n IN nodes(path) | n.mst] AS ring, length(path) AS len
ORDER BY len LIMIT 1
"""

# ── Phát hiện toàn portfolio (cho batch / dashboard) ──────────────────────────
ALL_SHADOW_CONTROLLERS = """
MATCH (o:Owner)-[:OWNS_CROSS]->(c:Company)
WITH o, collect(DISTINCT c.mst) AS companies
WHERE size(companies) >= 2
RETURN o.id AS controller, o.flag AS flag, companies
ORDER BY size(companies) DESC
"""

ALL_CIRCULAR_RINGS = """
MATCH path = (c:Company)-[:INTERNAL_TXN*2..10]->(c)
WITH [n IN nodes(path) | n.mst] AS ring, length(path) AS len
RETURN DISTINCT ring, len ORDER BY len
"""

# Centrality feature (PageRank qua GDS nếu có; fallback degree)
DEGREE_FEATURES = """
MATCH (c:Company {mst: $mst})
OPTIONAL MATCH (c)-[out]->()
OPTIONAL MATCH (c)<-[inc]-()
RETURN count(DISTINCT out) AS out_degree, count(DISTINCT inc) AS in_degree
"""

GRAPH_STATS = """
MATCH (c:Company) WITH count(c) AS companies
MATCH (o:Owner) WITH companies, count(o) AS owners
OPTIONAL MATCH ()-[r]->() RETURN companies, owners, count(r) AS rels
"""
