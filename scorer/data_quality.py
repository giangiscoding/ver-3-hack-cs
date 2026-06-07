"""
Data Quality Index (DQI) — đánh giá từng nguồn dữ liệu theo độ đầy đủ + chất lượng.

Mỗi nguồn được chấm 0-1 dựa trên:
  - Completeness: có mặt hay không, bao nhiêu tháng/năm
  - Quality: độ nhất quán nội bộ, các chỉ số phụ trợ

DQI Profile là vector 6 chiều được dùng để phân cluster.
"""

from __future__ import annotations
from dataclasses import dataclass
from scorer.models import CompanyBundle


@dataclass
class DQIProfile:
    cic: float
    bctc: float
    einvoice: float
    bank: float
    compliance: float
    esg: float

    @property
    def overall(self) -> float:
        return (
            0.25 * self.cic +
            0.25 * self.bctc +
            0.15 * self.einvoice +
            0.15 * self.bank +
            0.10 * self.compliance +
            0.10 * self.esg
        )

    def as_vector(self) -> list[float]:
        return [self.cic, self.bctc, self.einvoice, self.bank, self.compliance, self.esg]

    def as_dict(self) -> dict:
        return {
            "cic": self.cic, "bctc": self.bctc, "einvoice": self.einvoice,
            "bank": self.bank, "compliance": self.compliance, "esg": self.esg,
            "overall": round(self.overall, 3),
        }


def _score_cic(cic: dict) -> float:
    if not cic.get("available"):
        return 0.0

    # Chất lượng từ nhóm nợ: nhóm 1 = tốt nhất
    debt_group = cic.get("debt_group_current", 3)
    group_q = max(0.0, (5 - debt_group) / 4)  # G1→1.0, G3→0.5, G5→0.0

    # Utilization: 30-70% tối ưu, >100% rất xấu
    util = cic.get("credit_utilization_pct", 0.5)
    if util < 0.3:
        util_q = 0.7
    elif util <= 0.7:
        util_q = 1.0
    elif util <= 1.0:
        util_q = max(0.3, 1.0 - (util - 0.7) * 2.3)
    else:
        util_q = 0.0

    # Số tổ chức tín dụng: nhiều hơn = bức tranh đa dạng hơn
    n_tctd = cic.get("num_financial_institutions", 1)
    tctd_q = min(1.0, n_tctd / 4)

    return round(0.50 * group_q + 0.30 * util_q + 0.20 * tctd_q, 3)


def _score_bctc(bctc: dict) -> float:
    if not bctc.get("available"):
        return 0.0

    # Độ sâu: có đủ 3 năm không?
    rev = bctc.get("revenue_bn_vnd", {})
    years = sum(1 for v in rev.values() if v and v > 0)
    depth_q = min(1.0, years / 3)

    # Tính đầy đủ của các chỉ số chính
    has_fields = sum([
        bctc.get("dscr") is not None,
        bctc.get("de_ratio") is not None,
        bctc.get("ebitda_margin_pct") is not None,
        bctc.get("current_ratio") is not None,
    ])
    completeness_q = has_fields / 4

    return round(0.60 * depth_q + 0.40 * completeness_q, 3)


def _score_einvoice(einvoices: dict) -> float:
    if not einvoices.get("available"):
        return 0.0
    active = einvoices.get("so_thang_co_hoa_don", 0)
    return round(min(1.0, active / 12), 3)


def _score_bank(bank: dict) -> float:
    if not bank.get("available"):
        return 0.0
    months = len(bank.get("du_lieu_theo_thang", []))
    return round(min(1.0, months / 12), 3)


def _score_compliance(compliance: dict) -> float:
    if not compliance.get("available"):
        return 0.3  # compliance thường có, thiếu hoàn toàn là hiếm
    history = compliance.get("thue", {}).get("lich_su_24_thang", [])
    return round(min(1.0, max(0.5, len(history) / 24)), 3)


def _score_esg(esg: dict) -> float:
    return 1.0 if esg.get("available") else 0.5


def compute(bundle: CompanyBundle) -> DQIProfile:
    """Tính DQI profile cho một công ty."""
    return DQIProfile(
        cic=_score_cic(bundle.cic),
        bctc=_score_bctc(bundle.bctc),
        einvoice=_score_einvoice(bundle.einvoices),
        bank=_score_bank(bundle.bank),
        compliance=_score_compliance(bundle.compliance),
        esg=_score_esg(bundle.esg),
    )
