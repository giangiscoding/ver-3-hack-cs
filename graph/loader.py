"""
Loader — đọc data/output/graph.json và nạp vào Neo4j.

Chạy: python -m graph.loader            (nạp toàn bộ)
      python -m graph.loader --clear    (xoá sạch rồi nạp lại)
      python -m graph.loader --scores   (nạp + chấm điểm gắn vào Company node)

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


def enrich_scores() -> int:
    """
    Chấm điểm toàn bộ DN (score) rồi gắn final_score/rating/cluster/dri vào Company node.
    Dùng cho graph view: tô màu node theo rating, hiện điểm khi click.
    """
    from data import list_msts, load_company
    from scorer import score

    rows = []
    for mst in list_msts():
        r = score(load_company(mst))
        rows.append({
            "mst":         r.mst,
            "final_score": r.final_score,
            "rating":      r.rating,
            "cluster":     r.cluster,
            "dri":         round(r.dri.dri, 3),
        })
    for batch in _batched(rows):
        conn.run_write(q.SET_COMPANY_SCORES, rows=batch)
    return len(rows)


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

    if "--scores" in sys.argv:
        print("\nChấm điểm & gắn vào Company node...")
        n = enrich_scores()
        print(f"✅ Đã gắn điểm cho {n} công ty")

    print("\nQuick check:")
    for row in conn.run_query(q.GRAPH_STATS):
        print(f"   {row}")
    conn.close()


if __name__ == "__main__":
    main()
