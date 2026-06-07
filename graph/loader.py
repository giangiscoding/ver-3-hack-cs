"""
Loader — đọc data/output/graph.json và nạp vào Neo4j.

Chạy: python -m graph.loader            (nạp toàn bộ)
      python -m graph.loader --clear    (xoá sạch rồi nạp lại)

Cần Neo4j đang chạy + biến môi trường NEO4J_* (xem graph/connection.py).
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

from graph import connection as conn
from graph import queries as q

GRAPH_JSON = Path(__file__).parent.parent / "data" / "output" / "graph.json"
BATCH = 5000


def _batched(rows, size=BATCH):
    for i in range(0, len(rows), size):
        yield rows[i:i + size]


def load(clear: bool = False) -> dict:
    """Nạp graph.json vào Neo4j. Trả về thống kê."""
    with open(GRAPH_JSON, encoding="utf-8") as f:
        g = json.load(f)

    if clear:
        conn.run_write(q.CLEAR_ALL)

    for c in q.CONSTRAINTS:
        conn.run_write(c)

    # ── Nodes ─────────────────────────────────────────────────────────────────
    companies = [
        {"mst": n["id"], "phan_khuc": n.get("phan_khuc"), "nganh": n.get("nganh")}
        for n in g["nodes"] if n["type"] == "doanh_nghiep"
    ]
    owners = [
        {"id": n["id"], "ten": n.get("ten"), "flag": n.get("flag")}
        for n in g["nodes"] if n["type"] == "chu_so_huu"
    ]
    for batch in _batched(companies):
        conn.run_write(q.LOAD_COMPANIES, rows=batch)
    for batch in _batched(owners):
        conn.run_write(q.LOAD_OWNERS, rows=batch)

    # ── Edges theo loại ─────────────────────────────────────────────────────────
    by_rel: dict[str, list] = {}
    for e in g["edges"]:
        rel = q.EDGE_TYPE_MAP.get(e["type"])
        if rel:
            by_rel.setdefault(rel, []).append(e)
    edge_counts = {}
    for rel, rows in by_rel.items():
        for batch in _batched(rows):
            conn.run_write(q.LOAD_BY_REL[rel], rows=batch)
        edge_counts[rel] = len(rows)

    return {"companies": len(companies), "owners": len(owners), "edges": edge_counts}


def main():
    clear = "--clear" in sys.argv
    if not conn.ping():
        print(f"❌ Không kết nối được Neo4j tại {conn.NEO4J_URI}")
        print("   Khởi động Neo4j (docker compose up -d / Aura) rồi đặt NEO4J_* env.")
        sys.exit(1)
    print(f"Kết nối Neo4j: {conn.NEO4J_URI}")
    stats = load(clear=clear)
    print(f"✅ Đã nạp: {stats['companies']} công ty, {stats['owners']} chủ sở hữu")
    for rel, n in stats["edges"].items():
        print(f"   {rel}: {n}")
    print("\nQuick check:")
    for row in conn.run_query(q.GRAPH_STATS):
        print(f"   {row}")
    conn.close()


if __name__ == "__main__":
    main()
