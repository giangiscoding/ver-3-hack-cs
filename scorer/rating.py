"""Rating scale, hard stops, và approval actions.

MASTER SCALE CALIBRATION (phương pháp S&P/Moody's master scale):
  Các ngưỡng rating được calibrate theo phân phối điểm thực của portfolio,
  không phải chia đều 0-1000. Mục tiêu: credit pyramid thực tế cho MSME VN.

  Phân phối đạt được trên 5000 DN synthetic (điểm blend × DRI, qua engine có cap):
    AAA 1% · AA 4% · A 12% · BBB 20% · BB 22% · B 18% · CCC 12% · D 12%

  Ngưỡng được suy ra tự động bởi ml/calibrate.py (không hardcode thủ công).
  Chạy lại sau khi train lại models để re-calibrate.

  ĐÂY LÀ MASTER SCALE DUY NHẤT cho mọi cluster → một hạng BB mang cùng
  ý nghĩa rủi ro dù DN thuộc cluster nào. Sự khác biệt giữa các cluster
  thể hiện qua: (1) điểm ML thấp hơn khi ít dữ liệu, (2) trần xếp hạng.
"""

from scorer.models import CompanyBundle

RATING_BANDS = [
    (800, 1001, "AAA"),
    (720,  800, "AA"),
    (620,  720, "A"),
    (510,  620, "BBB"),
    (420,  510, "BB"),
    (340,  420, "B"),
    (270,  340, "CCC"),
    (  0,  270, "D"),
]

RATING_ORDER = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "D"]

APPROVAL_ACTIONS = {
    "AAA": "auto_approve",
    "AA":  "auto_approve",
    "A":   "auto_approve",
    "BBB": "conditional_approve",
    "BB":  "manual_review",
    "B":   "senior_review",
    "CCC": "auto_reject",
    "D":   "auto_reject",
}

RISK_LEVELS = {
    "AAA": "Rất thấp",
    "AA":  "Thấp",
    "A":   "Thấp - Trung bình",
    "BBB": "Trung bình",
    "BB":  "Trung bình - Cao",
    "B":   "Cao",
    "CCC": "Rất cao",
    "D":   "Vỡ nợ / Loại",
}


def to_rating(score: int) -> str:
    """Tra cứu rating từ điểm số trên master scale."""
    for lo, hi, grade in RATING_BANDS:
        if lo <= score < hi:
            return grade
    return "D"


def downgrade(rating: str, steps: int = 1) -> str:
    idx = min(RATING_ORDER.index(rating) + steps, len(RATING_ORDER) - 1)
    return RATING_ORDER[idx]


def apply_cap(rating: str, cap: str) -> str:
    """Nếu rating tốt hơn cap, trả về cap; ngược lại giữ nguyên."""
    if RATING_ORDER.index(rating) < RATING_ORDER.index(cap):
        return cap
    return rating


def apply_hard_stops(
    score: int,
    bundle: CompanyBundle,
    fraud_flags: list[str],
    rating_cap: str | None = None,
) -> tuple[str, str | None]:
    """
    Returns (final_rating, hard_stop_reason | None).

    Chấm trên MASTER SCALE duy nhất (RATING_BANDS).
    rating_cap: trần xếp hạng do cluster quy định (e.g. "BBB" cho L3_ONLY)
    """

    # ── CIC nhóm 4-5 → D bất kể điểm ────────────────────────────────────────
    cic = bundle.cic
    if cic.get("available") and cic.get("debt_group_current", 1) >= 4:
        return "D", f"CIC nhóm nợ {cic['debt_group_current']} — hard stop"

    base_rating = to_rating(score)

    # ── Áp trần cluster trước (data availability cap) ─────────────────────────
    cluster_cap_reason = None
    if rating_cap and RATING_ORDER.index(base_rating) < RATING_ORDER.index(rating_cap):
        base_rating = rating_cap
        cluster_cap_reason = f"Trần cluster {rating_cap}: thiếu dữ liệu truyền thống"

    # ── Fraud risk rất cao → D ────────────────────────────────────────────────
    if "circular_transaction" in fraud_flags and "shared_controller" in fraud_flags:
        return "D", f"Fraud: {', '.join(fraud_flags)}"

    hard_cap = None  # trần từ vi phạm cứng

    # ── Cưỡng chế thuế → trần BB ─────────────────────────────────────────────
    if bundle.compliance.get("available"):
        if bundle.compliance.get("thue", {}).get("co_cuong_che"):
            hard_cap = "BB"

    # ── Ô nhiễm nghiêm trọng → trần BB ──────────────────────────────────────
    if bundle.esg.get("available"):
        if bundle.esg.get("moi_truong", {}).get("trong_danh_sach_o_nhiem_nghiem_trong"):
            hard_cap = "BB"

    # ── Fraud flag trung bình → giảm 1 bậc ───────────────────────────────────
    if fraud_flags and "shared_controller" in fraud_flags:
        base_rating = downgrade(base_rating, 1)

    # Áp trần vi phạm cứng (nghiêm ngặt hơn trần cluster)
    if hard_cap and RATING_ORDER.index(base_rating) < RATING_ORDER.index(hard_cap):
        reasons = []
        if bundle.compliance.get("available") and bundle.compliance.get("thue", {}).get("co_cuong_che"):
            reasons.append("cưỡng chế thuế")
        if bundle.esg.get("available") and bundle.esg.get("moi_truong", {}).get("trong_danh_sach_o_nhiem_nghiem_trong"):
            reasons.append("danh sách ô nhiễm nghiêm trọng")
        return hard_cap, f"Hard stop trần BB: {', '.join(reasons)}"

    if cluster_cap_reason and base_rating == rating_cap:
        return base_rating, cluster_cap_reason

    return base_rating, None
