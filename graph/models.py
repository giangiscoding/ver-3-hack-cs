"""Shared data types for the graph fraud-detection module."""

from dataclasses import dataclass, field


@dataclass
class FraudReport:
    """Kết quả phân tích gian lận đồ thị cho một doanh nghiệp."""
    mst: str
    fraud_flags: list[str] = field(default_factory=list)   # khớp scorer.rating: shared_controller, circular_transaction, shell_company
    fraud_risk_score: float = 0.0                            # [0,1]
    patterns: dict = field(default_factory=dict)            # bằng chứng từng pattern
    connected_msts: list[str] = field(default_factory=list)  # DN liên đới trong cluster

    @property
    def is_high_risk(self) -> bool:
        return self.fraud_risk_score >= 0.8

    def to_dict(self) -> dict:
        return {
            "mst": self.mst,
            "fraud_flags": self.fraud_flags,
            "fraud_risk_score": round(self.fraud_risk_score, 3),
            "patterns": self.patterns,
            "connected_msts": self.connected_msts,
        }
