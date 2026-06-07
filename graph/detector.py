"""
Fraud detector — chạy Cypher trên Neo4j, trả về FraudReport cho mỗi doanh nghiệp.

3 pattern (theo docs/03_graph.md):
  1. Shadow controller   — chủ sở hữu ẩn nắm chéo nhiều DN  → flag "shared_controller"
  2. Shell company       — chia sẻ địa chỉ với DN khác       → flag "shell_company"
  3. Circular transaction— vòng giao dịch nội bộ quay vòng  → flag "circular_transaction"

Flags khớp với scorer/rating.py:
  circular_transaction + shared_controller → D (hard stop)
  shared_controller đơn lẻ                 → giảm 1 bậc

Risk score [0,1] = tổng trọng số các pattern (cap 1.0).
"""

from __future__ import annotations

from graph import connection as conn
from graph import queries as q
from graph.models import FraudReport

# Trọng số rủi ro từng pattern
W_CIRCULAR = 0.55
W_SHADOW = 0.45
W_SHELL = 0.30


def available() -> bool:
    """Neo4j có sẵn sàng không (để engine quyết định có chạy graph analysis)."""
    return conn.ping()


def analyze(mst: str) -> FraudReport:
    """Phân tích gian lận đồ thị cho một MST. Yêu cầu Neo4j đang chạy."""
    report = FraudReport(mst=mst)
    connected: set[str] = set()
    score = 0.0

    # ── Pattern 1: Shadow controller ──────────────────────────────────────────
    rows = conn.run_query(q.DETECT_SHADOW_CONTROLLER, mst=mst)
    if rows:
        r = rows[0]
        peers = [m for m in r["companies"] if m != mst]
        report.fraud_flags.append("shared_controller")
        report.patterns["shadow_controller"] = {
            "controller": r["controller"],
            "ten": r.get("ten"),
            "is_flagged_shadow": r.get("flag") == "shadow_controller",
            "companies_controlled": r["companies"],
        }
        connected.update(peers)
        score += W_SHADOW

    # ── Pattern 2: Shell company (cùng địa chỉ) ───────────────────────────────
    rows = conn.run_query(q.DETECT_SHELL, mst=mst)
    if rows and rows[0]["companies"]:
        peers = rows[0]["companies"]
        report.fraud_flags.append("shell_company")
        report.patterns["shell_company"] = {"same_address_with": peers}
        connected.update(peers)
        score += W_SHELL

    # ── Pattern 3: Circular transaction ───────────────────────────────────────
    rows = conn.run_query(q.DETECT_CIRCULAR, mst=mst)
    if rows and rows[0].get("ring"):
        ring = rows[0]["ring"]
        report.fraud_flags.append("circular_transaction")
        report.patterns["circular_transaction"] = {"ring": ring, "length": rows[0]["len"]}
        connected.update(m for m in ring if m != mst)
        score += W_CIRCULAR

    report.fraud_risk_score = min(1.0, score)
    report.connected_msts = sorted(connected)
    return report


def analyze_all() -> dict[str, FraudReport]:
    """
    Quét toàn portfolio (hiệu quả hơn gọi analyze() từng cái):
    lấy tất cả shadow controllers + circular rings một lần, gộp thành report.
    """
    reports: dict[str, FraudReport] = {}

    def _get(mst: str) -> FraudReport:
        return reports.setdefault(mst, FraudReport(mst=mst))

    # Shadow controllers
    for r in conn.run_query(q.ALL_SHADOW_CONTROLLERS):
        companies = r["companies"]
        for mst in companies:
            rep = _get(mst)
            if "shared_controller" not in rep.fraud_flags:
                rep.fraud_flags.append("shared_controller")
                rep.fraud_risk_score = min(1.0, rep.fraud_risk_score + W_SHADOW)
            rep.patterns.setdefault("shadow_controller", {"controller": r["controller"],
                                                           "companies_controlled": companies})
            rep.connected_msts = sorted(set(rep.connected_msts) | {m for m in companies if m != mst})

    # Circular rings
    for r in conn.run_query(q.ALL_CIRCULAR_RINGS):
        ring = r["ring"]
        for mst in ring:
            rep = _get(mst)
            if "circular_transaction" not in rep.fraud_flags:
                rep.fraud_flags.append("circular_transaction")
                rep.fraud_risk_score = min(1.0, rep.fraud_risk_score + W_CIRCULAR)
            rep.patterns.setdefault("circular_transaction", {"ring": ring, "length": r["len"]})
            rep.connected_msts = sorted(set(rep.connected_msts) | {m for m in ring if m != mst})

    return reports
