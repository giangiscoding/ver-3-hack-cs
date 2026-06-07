"""
Smoke test cho graph module.

- Offline (luôn chạy): kiểm tra shaping graph.json → nodes/edges đúng cấu trúc Neo4j.
- Online (nếu Neo4j chạy): nạp dữ liệu + analyze các MST gian lận đã biết, assert flags.

Chạy: python -m graph.smoke_test
"""

from __future__ import annotations
import json
from pathlib import Path

from graph import connection as conn
from graph import queries as q

GRAPH_JSON = Path(__file__).parent.parent / "data" / "output" / "graph.json"


def offline_checks():
    print("── Offline: kiểm tra shaping graph.json ──")
    g = json.load(open(GRAPH_JSON, encoding="utf-8"))
    companies = [n for n in g["nodes"] if n["type"] == "doanh_nghiep"]
    owners = [n for n in g["nodes"] if n["type"] == "chu_so_huu"]
    print(f"  Companies: {len(companies)} | Owners: {len(owners)}")

    by_rel = {}
    for e in g["edges"]:
        rel = q.EDGE_TYPE_MAP.get(e["type"])
        assert rel, f"Edge type chưa map: {e['type']}"
        by_rel.setdefault(rel, 0)
        by_rel[rel] += 1
    print(f"  Edges theo rel: {by_rel}")

    # MST gian lận đã biết để test online
    cross = [e["target"] for e in g["edges"] if e["type"] == "so_huu_cheo"]
    circular = [e["source"] for e in g["edges"] if e["type"] == "giao_dich_noi_bo"]
    addr = [e["target"] for e in g["edges"] if e["type"] == "cung_dia_chi"]
    print(f"  Ví dụ shadow-controlled MST: {cross[:3]}")
    print(f"  Ví dụ circular MST: {circular[:3]}")
    print(f"  Ví dụ shell MST: {addr[:3]}")
    print("  ✅ Offline OK\n")
    return {"shadow": cross[:3], "circular": circular[:3], "shell": addr[:3]}


def online_checks(samples):
    print("── Online: Neo4j ──")
    if not conn.ping():
        print(f"  ⚠️  Neo4j chưa chạy tại {conn.NEO4J_URI}.")
        print("     Khởi động: docker compose up -d  (rồi: python -m graph.loader --clear)")
        print("     Hoặc trỏ NEO4J_URI tới Aura. Bỏ qua online test.")
        return
    from graph.loader import load
    from graph import analyze
    print(f"  Kết nối {conn.NEO4J_URI}, nạp dữ liệu...")
    load(clear=True)

    if samples["circular"]:
        mst = samples["circular"][0]
        rep = analyze(mst)
        print(f"  analyze({mst}) → flags={rep.fraud_flags} risk={rep.fraud_risk_score:.2f}")
        assert "circular_transaction" in rep.fraud_flags, "Phải phát hiện circular!"
    if samples["shadow"]:
        mst = samples["shadow"][0]
        rep = analyze(mst)
        print(f"  analyze({mst}) → flags={rep.fraud_flags} risk={rep.fraud_risk_score:.2f}")
        assert "shared_controller" in rep.fraud_flags, "Phải phát hiện shadow controller!"
    print("  ✅ Online OK")
    conn.close()


if __name__ == "__main__":
    s = offline_checks()
    online_checks(s)
