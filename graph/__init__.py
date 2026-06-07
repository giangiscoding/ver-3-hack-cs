"""
Graph fraud-detection module — Neo4j graph database.

Public API:
    from graph import analyze, analyze_all, available, FraudReport

    if available():                       # Neo4j đang chạy?
        report = analyze("0123456789")    # FraudReport cho 1 DN
        report.fraud_flags                # → ["shared_controller", ...]

Tích hợp với scorer:
    from scorer import score
    rep = analyze(mst)
    result = score(bundle, fraud_flags=rep.fraud_flags)

Nạp dữ liệu: python -m graph.loader [--clear]
"""

from graph.detector import analyze, analyze_all, available
from graph.models import FraudReport

__all__ = ["analyze", "analyze_all", "available", "FraudReport"]
