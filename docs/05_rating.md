# Rating Module

**Vị trí:** `scorer/rating.py`  
**Vai trò:** Nhận `final_score` + `FraudReport` → áp hard stops → trả hạng và hành động phê duyệt

← [02_scoring.md](02_scoring.md) · [03_graph.md](03_graph.md) · [04_dri.md](04_dri.md)  
→ Output sang: [06_ui.md](06_ui.md)

---

## Thang điểm và hạng — MASTER SCALE CALIBRATED

> Ngưỡng KHÔNG chia đều 0-1000. Chúng được **calibrate tự động** (`ml/calibrate.py`)
> theo phân phối điểm thực để đạt credit pyramid mục tiêu (phương pháp S&P/Moody's
> master scale). Ngưỡng dưới đây ứng với data hiện tại (FUND_RHO=0.40); chạy lại
> `ml.calibrate` sau khi train sẽ tự cập nhật.

| Hạng | Điểm | % portfolio | Hành động phê duyệt |
| ---- | ---- | ----------- | ------------------- |
| AAA | ≥ 800 | 1% | Auto-approve · ưu đãi nhất · hạn mức tối đa |
| AA | 720–799 | 4% | Auto-approve · điều kiện chuẩn |
| A | 620–719 | 12% | Auto-approve · hạn mức điều chỉnh nhẹ |
| BBB | 510–619 | 20% | Approve có điều kiện · TSĐB bổ sung |
| BB | 420–509 | 22% | Review thủ công bắt buộc |
| B | 340–419 | 18% | Review cấp cao · TSĐB mạnh |
| CCC | 270–339 | 12% | Từ chối tự động · ngoại lệ cần Hội đồng |
| D | < 270 | 12% | Auto-reject |

**Trần theo cluster** (chính sách tín dụng, áp trong `apply_hard_stops`): NO_CIC → tối đa
AA · NO_BCTC → tối đa A · L3_ONLY → tối đa BBB. Thiếu dữ liệu truyền thống thì không
thể đạt hạng cao nhất dù điểm cao.

---

## Hard-stop rules

Hard-stop **override toàn bộ điểm số**, áp dụng trước khi tra bảng rating:

```python
def apply_hard_stops(score: int, bundle, fraud_report) -> tuple[str, str | None]:
    """
    Returns (rating, hard_stop_reason | None)
    """

    # ── Stop 1: CIC nhóm 4-5 → D bất kể điểm ────────────────────────────────
    cic = bundle.cic
    if cic.get("available") and cic.get("debt_group_current", 1) >= 4:
        return "D", "CIC nhóm nợ 4-5"

    # ── Stop 2: Cưỡng chế thuế → trần BB ────────────────────────────────────
    if bundle.compliance.get("available"):
        if bundle.compliance["thue"].get("co_cuong_che"):
            rating = score_to_rating(score)
            if rating in ("AAA", "AA", "A", "BBB"):
                return "BB", "Đang bị cưỡng chế thuế → trần BB"

    # ── Stop 3: Danh sách ô nhiễm nghiêm trọng → trần BB ────────────────────
    if bundle.esg.get("available"):
        if bundle.esg["moi_truong"].get("trong_danh_sach_o_nhiem_nghiem_trong"):
            rating = score_to_rating(score)
            if rating in ("AAA", "AA", "A", "BBB"):
                return "BB", "Trong danh sách ô nhiễm nghiêm trọng → trần BB"

    # ── Stop 4: Fraud risk cao → override ────────────────────────────────────
    if fraud_report and fraud_report.fraud_risk_score > 0.8:
        return "D", f"Fraud risk score {fraud_report.fraud_risk_score:.2f} — {', '.join(fraud_report.flags)}"

    # ── Stop 5: Fraud risk trung bình → giảm 1 bậc ───────────────────────────
    if fraud_report and 0.5 <= fraud_report.fraud_risk_score <= 0.8:
        rating = score_to_rating(score)
        downgraded = downgrade_one(rating)
        return downgraded, f"Fraud flag: {', '.join(fraud_report.flags)}"

    return score_to_rating(score), None
```

---

## Score → Rating mapping

```python
# Calibrated tự động bởi ml/calibrate.py (giá trị hiện tại, FUND_RHO=0.40)
RATING_BANDS = [
    (800, 1001, "AAA"),
    (720,  800, "AA"),
    (620,  720, "A"),
    (510,  620, "BBB"),
    (420,  510, "BB"),
    (340,  420, "B"),
    (270,  340, "CCC"),
    (0,    270, "D"),
]

def score_to_rating(score: int) -> str:
    for lo, hi, grade in RATING_BANDS:
        if lo <= score < hi:
            return grade
    return "D"

RATING_ORDER = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "D"]

def downgrade_one(rating: str) -> str:
    idx = RATING_ORDER.index(rating)
    return RATING_ORDER[min(idx + 1, len(RATING_ORDER) - 1)]
```

---

## Approval actions

```python
APPROVAL_ACTIONS = {
    "AAA": "auto_approve",
    "AA":  "auto_approve",
    "A":   "auto_approve",
    "BBB": "conditional_approve",   # cần TSĐB bổ sung
    "BB":  "manual_review",         # chuyên viên thẩm định
    "B":   "senior_review",         # cấp cao
    "CCC": "auto_reject",           # ngoại lệ cần HĐ
    "D":   "auto_reject",
}
```

---

## Output: RatingResult

```python
@dataclass
class RatingResult:
    final_score: int           # điểm sau DRI adjustment
    rating: str                # "BBB"
    hard_stop: str | None      # lý do hard-stop nếu có
    approval_action: str       # "conditional_approve"
    fraud_flags: list[str]     # từ FraudReport
    risk_level: str            # "Trung bình"
    recommended_ltv: float     # loan-to-value gợi ý (0.0–0.8)
    interest_tier: str         # "Chuẩn" / "Ưu đãi" / "Cao"
```

### Bảng gợi ý LTV và lãi suất

| Hạng | LTV tối đa | Lãi suất tier |
| ---- | ---------- | ------------- |
| AAA | 80% | Ưu đãi |
| AA | 75% | Ưu đãi |
| A | 70% | Chuẩn |
| BBB | 60% | Chuẩn |
| BB | 50% | Cao |
| B | 40% | Cao |
| CCC | — | Từ chối |
| D | — | Từ chối |
