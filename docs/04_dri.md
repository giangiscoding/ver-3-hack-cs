# DRI — Data Richness Index

**Vị trí:** `scorer/dri.py`  
**Vai trò:** Tính hệ số chất lượng dữ liệu → điều chỉnh raw score trước khi rating

← [02_scoring.md](02_scoring.md) · [01_data.md](01_data.md)  
→ Output sang: [05_rating.md](05_rating.md)

---

## Lý do cần DRI

MSME Việt Nam thường **thin-file** — thiếu BCTC, không có CIC, hóa đơn điện tử thưa.  
Nếu điểm thiếu data = 0 thì DN Micro tốt nhưng không có CIC sẽ bị phạt oan.  
DRI giải quyết bằng cách **chiết khấu toàn bộ score** thay vì cộng 0 vào từng tiêu chí:

```
final_score = raw_score × (0.7 + 0.3 × DRI)
```

- DRI = 1.0 → không chiết khấu (đủ dữ liệu)
- DRI = 0.0 → chiết khấu 30% (chỉ giữ 70% điểm)

*Nghĩa là ngay cả DN không có data gì, vẫn giữ được 70% điểm thực sự kiếm được — không bị phạt kép.*

---

## Công thức

```
DRI = 0.35 × Coverage + 0.30 × Depth + 0.15 × Freshness + 0.20 × Cross_Validation
```

| Thành phần | Trọng số | Đo lường |
| ---------- | -------- | -------- |
| Coverage | 35% | Có bao nhiêu nguồn data trong số 6 nguồn |
| Depth | 30% | Data đủ sâu không (đủ tháng, đủ năm) |
| Freshness | 15% | Data có mới không |
| Cross_Validation | 20% | Các nguồn có nhất quán với nhau không |

---

## Coverage (0.0 – 1.0)

Đếm số nguồn data `available=true` trong tổng 6 nguồn:

```python
def compute_coverage(bundle) -> float:
    sources = [
        bundle.cic.get("available", False),        # weight 2 (CIC quan trọng)
        bundle.bctc.get("available", False),       # weight 2
        bundle.einvoices.get("available", False),  # weight 1
        bundle.bank.get("available", False),       # weight 1
        bundle.compliance.get("available", False), # weight 1
        bundle.esg.get("available", False),        # weight 1
    ]
    weights = [2, 2, 1, 1, 1, 1]   # tổng = 8
    score = sum(w for s, w in zip(sources, weights) if s)
    return score / 8
```

| Số nguồn có | Coverage |
| ----------- | -------- |
| Tất cả 6 (CIC + BCTC + đủ L3) | ~1.0 |
| 4 nguồn (thiếu CIC, BCTC) | ~0.5 |
| Chỉ E-Invoice + Bank | ~0.25 |

---

## Depth (0.0 – 1.0)

Đo độ sâu của time-series data:

```python
def compute_depth(bundle) -> float:
    scores = []

    # E-Invoice: kỳ vọng 12 tháng
    if bundle.einvoices.get("available"):
        months = bundle.einvoices.get("so_thang_co_hoa_don", 0)
        scores.append(months / 12)

    # Bank statement: kỳ vọng 12 tháng
    if bundle.bank.get("available"):
        months = len(bundle.bank.get("du_lieu_theo_thang", []))
        scores.append(months / 12)

    # Tax history: kỳ vọng 24 tháng
    if bundle.compliance.get("available"):
        months = len(bundle.compliance["thue"].get("lich_su_24_thang", []))
        scores.append(months / 24)

    # BCTC: kỳ vọng 3 năm
    if bundle.bctc.get("available"):
        rev = bundle.bctc.get("revenue_bn_vnd", {})
        years = sum(1 for v in rev.values() if v and v > 0)
        scores.append(years / 3)

    return sum(scores) / len(scores) if scores else 0.0
```

---

## Freshness (0.0 – 1.0)

Đo mức độ mới của dữ liệu so với BASE_DATE (2025-12):

```python
from datetime import date

BASE_DATE = date(2025, 12, 31)

def compute_freshness(bundle) -> float:
    scores = []

    # E-Invoice: tháng cuối cùng có data
    if bundle.einvoices.get("available"):
        months = bundle.einvoices.get("du_lieu_theo_thang", [])
        if months:
            last = months[-1]["thang"]   # "2025-12"
            y, m = map(int, last.split("-"))
            months_ago = (BASE_DATE.year - y) * 12 + (BASE_DATE.month - m)
            scores.append(max(0, 1 - months_ago / 6))   # stale sau 6 tháng

    # BCTC: năm tài chính gần nhất
    if bundle.bctc.get("available"):
        # Giả sử year_n là năm hiện tại
        scores.append(1.0)

    # Tax: tháng khai báo gần nhất
    if bundle.compliance.get("available"):
        history = bundle.compliance["thue"].get("lich_su_24_thang", [])
        if history:
            scores.append(1.0 if len(history) >= 12 else len(history) / 12)

    return sum(scores) / len(scores) if scores else 0.5
```

---

## Cross-Validation (0.0 – 1.0)

Kiểm tra độ nhất quán giữa các nguồn:

```python
def compute_cross_validation(bundle) -> float:
    checks = []

    # Check 1: BCTC revenue vs E-Invoice revenue (trong vòng 1.5×)
    if bundle.bctc.get("available") and bundle.einvoices.get("available"):
        bctc_rev = bundle.bctc["revenue_bn_vnd"]["year_n"] * 1000   # mn VND
        inv_rev = sum(
            m["tong_doanh_thu_mn_vnd"]
            for m in bundle.einvoices.get("du_lieu_theo_thang", [])
        )
        if bctc_rev > 0 and inv_rev > 0:
            ratio = inv_rev / bctc_rev
            checks.append(1.0 if 0.5 <= ratio <= 1.5 else max(0, 1 - abs(ratio - 1)))

    # Check 2: BHXH nhân viên vs số NV trên master (trong vòng 80%)
    if bundle.compliance.get("available"):
        reported = bundle.compliance["bhxh"].get("so_nhan_vien_dong_bhxh", 0)
        actual = bundle.meta.get("so_nhan_vien", 1)
        if actual > 0:
            ratio = reported / actual
            checks.append(1.0 if ratio >= 0.8 else ratio / 0.8)

    # Check 3: Bank inflow vs E-Invoice revenue (gross check)
    if bundle.bank.get("available") and bundle.einvoices.get("available"):
        bank_inflow = sum(m["tong_thu_mn_vnd"] for m in bundle.bank.get("du_lieu_theo_thang", []))
        inv_rev = sum(m["tong_doanh_thu_mn_vnd"] for m in bundle.einvoices.get("du_lieu_theo_thang", []))
        if bank_inflow > 0 and inv_rev > 0:
            ratio = inv_rev / bank_inflow
            checks.append(1.0 if 0.4 <= ratio <= 1.2 else max(0, 1 - abs(ratio - 0.8)))

    return sum(checks) / len(checks) if checks else 0.5   # default 0.5 nếu không check được
```

---

## Tổng hợp và ví dụ

```python
def compute_dri(bundle) -> DRIResult:
    coverage = compute_coverage(bundle)
    depth = compute_depth(bundle)
    freshness = compute_freshness(bundle)
    xval = compute_cross_validation(bundle)

    dri = 0.35*coverage + 0.30*depth + 0.15*freshness + 0.20*xval
    return DRIResult(dri=dri, coverage=coverage, depth=depth, freshness=freshness, cross_val=xval)
```

### Ví dụ minh hoạ

| Loại DN | Coverage | Depth | Freshness | Cross-val | DRI | Hệ số |
| ------- | -------- | ----- | --------- | --------- | --- | ------ |
| Medium đủ data | 1.0 | 0.95 | 1.0 | 0.90 | **0.96** | ×0.99 |
| Small thiếu CIC | 0.75 | 0.85 | 1.0 | 0.80 | **0.83** | ×0.95 |
| Micro thin-file | 0.35 | 0.50 | 0.90 | 0.50 | **0.47** | ×0.84 |
| Micro rất mỏng | 0.20 | 0.30 | 0.70 | 0.30 | **0.27** | ×0.78 |

*Ngay cả Micro rất mỏng vẫn giữ 78% điểm thực sự kiếm được — không bị phạt quá mức.*

---

## Output: DRIResult

```python
@dataclass
class DRIResult:
    dri: float           # 0.0–1.0
    coverage: float
    depth: float
    freshness: float
    cross_val: float
    multiplier: float    # = 0.7 + 0.3 × dri
```
