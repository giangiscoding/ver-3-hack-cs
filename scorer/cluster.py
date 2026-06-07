"""
Cluster-based scoring — phân nhóm doanh nghiệp theo Data Quality Index (DQI).

Cải tiến so với binary availability:
  • Dùng DQI thay vì chỉ kiểm tra available/not-available
  • DQI_THRESHOLD = 0.5 → nguồn đạt ngưỡng mới được xem là "có"
  • Ví dụ: CIC available nhưng chỉ có 6 tháng lịch sử → CIC_DQI = 0.3 < 0.5
           → cluster NO_CIC thay vì FULL

Mỗi cluster có:
  • layer_max riêng (dùng cho rule-based fallback — phân bổ lại điểm layer thiếu)
  • tran_rating (trần xếp hạng tối đa — chính sách tín dụng)

Rating dùng MASTER SCALE DUY NHẤT (xem scorer/rating.py) → một hạng BB mang
cùng ý nghĩa rủi ro dù DN thuộc cluster nào. Khác biệt giữa cluster thể hiện
qua: (1) model ML riêng cho điểm thấp hơn khi ít dữ liệu, (2) trần xếp hạng.

Nguyên lý phân bổ lại (rule-based fallback):
  • Thiếu CIC (200đ)  → BCTC +80 (40%), L3 +120 (60%)
  • Thiếu BCTC (300đ) → CIC  +100 (33%), L3 +200 (67%)
  • Thiếu cả hai      → L3 toàn bộ 1000đ (×2 scale)
"""

from dataclasses import dataclass
from scorer.data_quality import compute as compute_dqi, DQIProfile
from scorer.models import CompanyBundle

# Ngưỡng DQI để coi một nguồn là "đủ chất lượng"
DQI_THRESHOLD = 0.50

# ── Cluster IDs ──────────────────────────────────────────────────────────────

CLUSTER_FULL    = "FULL"      # CIC ≥ DQI_THRESHOLD, BCTC ≥ DQI_THRESHOLD
CLUSTER_NO_CIC  = "NO_CIC"   # CIC < DQI_THRESHOLD, BCTC ≥ DQI_THRESHOLD
CLUSTER_NO_BCTC = "NO_BCTC"  # CIC ≥ DQI_THRESHOLD, BCTC < DQI_THRESHOLD
CLUSTER_L3_ONLY = "L3_ONLY"  # CIC < DQI_THRESHOLD, BCTC < DQI_THRESHOLD

ALL_CLUSTERS = [CLUSTER_FULL, CLUSTER_NO_CIC, CLUSTER_NO_BCTC, CLUSTER_L3_ONLY]


@dataclass(frozen=True)
class ClusterConfig:
    cluster_id: str
    mo_ta: str
    layer_max: dict          # layer_name → int (tổng = 1000), cho rule-based fallback
    tran_rating: str | None  # trần xếp hạng tối đa (chính sách tín dụng)


# ── Cluster configurations ────────────────────────────────────────────────────
# Layer max gốc: L1_CIC=200, L2_BCTC=300, L3A=190, L3B=160, L3C=120, L3D=30

CLUSTER_CONFIGS: dict[str, ClusterConfig] = {

    CLUSTER_FULL: ClusterConfig(
        cluster_id=CLUSTER_FULL,
        mo_ta="Đầy đủ dữ liệu: CIC + BCTC + L3 Alternative",
        layer_max={
            "L1_CIC": 200, "L2_BCTC": 300,
            "L3A_OPS": 190, "L3B_COMPLIANCE": 160, "L3C_ESG": 120, "L3D_MATURITY": 30,
        },
        tran_rating=None,
    ),

    # Thiếu CIC → phân bổ 200đ: BCTC +80, L3 +120 (tỉ lệ 40:60)
    CLUSTER_NO_CIC: ClusterConfig(
        cluster_id=CLUSTER_NO_CIC,
        mo_ta="Thiếu CIC: BCTC + L3. Trần AA (không thể AAA thiếu lịch sử tín dụng).",
        layer_max={
            "L1_CIC": 0, "L2_BCTC": 380,
            "L3A_OPS": 236, "L3B_COMPLIANCE": 198, "L3C_ESG": 149, "L3D_MATURITY": 37,
        },
        tran_rating="AA",
    ),

    # Thiếu BCTC → phân bổ 300đ: CIC +100, L3 +200 (tỉ lệ 33:67)
    CLUSTER_NO_BCTC: ClusterConfig(
        cluster_id=CLUSTER_NO_BCTC,
        mo_ta="Thiếu BCTC: CIC + L3. Trần A (không thể AA/AAA thiếu báo cáo tài chính).",
        layer_max={
            "L1_CIC": 300, "L2_BCTC": 0,
            "L3A_OPS": 266, "L3B_COMPLIANCE": 224, "L3C_ESG": 168, "L3D_MATURITY": 42,
        },
        tran_rating="A",
    ),

    # Chỉ L3 → toàn bộ 1000đ từ L3 (×2 scale)
    CLUSTER_L3_ONLY: ClusterConfig(
        cluster_id=CLUSTER_L3_ONLY,
        mo_ta="Chỉ L3 Alternative (×2 scale). Trần BBB — mọi phê duyệt cần xác minh thêm.",
        layer_max={
            "L1_CIC": 0, "L2_BCTC": 0,
            "L3A_OPS": 380, "L3B_COMPLIANCE": 320, "L3C_ESG": 240, "L3D_MATURITY": 60,
        },
        tran_rating="BBB",
    ),
}


def classify(bundle: CompanyBundle) -> str:
    """
    Phân cluster dựa trên DQI profile, không phải chỉ binary available/not.
    Ngưỡng DQI_THRESHOLD xác định một nguồn có "đủ chất lượng" không.
    """
    dqi = compute_dqi(bundle)
    has_cic_quality  = dqi.cic  >= DQI_THRESHOLD
    has_bctc_quality = dqi.bctc >= DQI_THRESHOLD

    if has_cic_quality and has_bctc_quality:
        return CLUSTER_FULL
    elif has_bctc_quality:
        return CLUSTER_NO_CIC
    elif has_cic_quality:
        return CLUSTER_NO_BCTC
    else:
        return CLUSTER_L3_ONLY


def classify_with_dqi(bundle: CompanyBundle) -> tuple[str, DQIProfile]:
    """Trả về cả cluster_id và DQI profile."""
    dqi = compute_dqi(bundle)
    has_cic_quality  = dqi.cic  >= DQI_THRESHOLD
    has_bctc_quality = dqi.bctc >= DQI_THRESHOLD

    if has_cic_quality and has_bctc_quality:
        return CLUSTER_FULL, dqi
    elif has_bctc_quality:
        return CLUSTER_NO_CIC, dqi
    elif has_cic_quality:
        return CLUSTER_NO_BCTC, dqi
    else:
        return CLUSTER_L3_ONLY, dqi
