# Scoring Engine Module

**Vị trí:** `scorer/`  
**Vai trò:** Nhận `CompanyBundle` từ data module → tính điểm 3 lớp → trả về `ScoreReport`

← [README](../README.md) · [01_data.md](01_data.md)  
→ Phụ thuộc vào: [04_dri.md](04_dri.md)  
→ Output sang: [05_rating.md](05_rating.md) · [06_ui.md](06_ui.md)

> **Lưu ý kiến trúc:** Tài liệu này mô tả bộ chấm **rule-based 3 lớp**. Trong hệ thống
> hiện tại nó là **đường fallback** (khi chưa train ML) và để **hiển thị/giải thích**.
> Đường chấm điểm **chính** là **stacked blend ML** — xem [07_ml_cluster.md](07_ml_cluster.md).
> `engine.py` tự chọn: có model → blend ML; chưa có → rule-based.

---

## Vị trí trong kiến trúc modular monolith

```
scorer/
├── __init__.py              ← public API: score(bundle) -> ScoreReport
├── engine.py                ← orchestrator: gọi 6 layers + DRI + rating
├── layers/
│   ├── layer1_cic.py        ← 200đ
│   ├── layer2_bctc.py       ← 300đ
│   ├── layer3a_ops.py       ← 190đ (E-invoice, CF, Anchor)
│   ├── layer3b_compliance.py← 160đ (Thuế, BHXH, Tiện ích, Bank)
│   ├── layer3c_esg.py       ← 120đ (E, S, G)
│   └── layer3d_maturity.py  ← 30đ  (Tuổi DN, HKD)
├── dri.py                   ← DRI calculator (xem 04_dri.md)
└── rating.py                ← Rating + hard stops (xem 05_rating.md)
```

**Public API:**

```python
from scorer import score

report = score(bundle)          # bundle từ data.load_company()
print(report.final_score)       # 0–1000
print(report.rating)            # "BBB"
print(report.breakdown)         # dict chi tiết từng tiêu chí
print(report.hard_stop)         # None hoặc lý do hard-stop
```

---

## Data flow qua engine

```
CompanyBundle
    │
    ├─ cic        ──► layer1_cic.py    → LayerResult(diem=165, max=200, chi_tiet={...})
    ├─ bctc       ──► layer2_bctc.py   → LayerResult(diem=210, max=300, chi_tiet={...})
    ├─ einvoices  ──►
    ├─ bank       ──► layer3a_ops.py   → LayerResult(diem=140, max=190, chi_tiet={...})
    ├─ contracts  ──►
    ├─ compliance ──► layer3b.py       → LayerResult(diem=120, max=160, chi_tiet={...})
    ├─ esg        ──► layer3c_esg.py   → LayerResult(diem=100, max=120, chi_tiet={...})
    └─ maturity   ──► layer3d.py       → LayerResult(diem=25,  max=30,  chi_tiet={...})
                                                │
                            raw_score = sum(all diem) = 760
                                                │
                            dri.py ──────────► DRI = 0.82
                                                │
                            adjusted = 760 × (0.7 + 0.3×0.82) = 719
                                                │
                            rating.py ─────── check hard_stops
                                           └─ "BBB" (660–739)
```

---

## Layer 1 — CIC (200 điểm)

**Input:** `cic: dict` từ `layer1_cic.json`  
**Khi `available=false`:** toàn bộ layer trả 0đ, DRI Coverage giảm

| Tiêu chí | Điểm max | Logic |
| -------- | -------- | ----- |
| Nhóm nợ hiện tại | 80 | G1→80 · G2→40 · G3→10 · G4-5→0 + **HARD STOP** |
| Lịch sử nợ xấu 24T | 40 | Sạch→40 · G2 một lần→25 · G2 nhiều lần→15 · G3+→0 |
| Credit utilization | 40 | <50%→40 · 50-80%→25 · 80-100%→10 · >100%→0 |
| Số TCTD | 25 | 1-3→25 · 4-5→15 · >5→5 |
| Tăng trưởng dư nợ 12T | 15 | <30%→15 · 30-70%→8 · >70%→0 |

---

## Layer 2 — BCTC (300 điểm)

**Input:** `bctc: dict` từ `layer2_bctc.json`  
**Khi `available=false`:** trả 0đ, DRI Coverage giảm mạnh

| Tiêu chí | Điểm max | Logic |
| -------- | -------- | ----- |
| DSCR | 80 | ≥1.5→80 · 1.25-1.5→60 · 1.0-1.25→35 · <1.0→0 |
| D/E ratio | 60 | <1.0→60 · 1.0-2.0→40 · 2.0-3.0→20 · >3.0→0 |
| EBITDA Margin | 50 | ≥15%→50 · 10-15%→35 · 5-10%→20 · <5%→5 · <0→0 |
| Cash Conversion Cycle | 40 | <30d→40 · 30-60→28 · 60-90→15 · >90→5 |
| Current Ratio | 40 | ≥2.0→40 · 1.5-2.0→30 · 1.0-1.5→18 · <1.0→5 |
| CAGR doanh thu 3 năm | 30 | >15%→30 · 5-15%→20 · 0-5%→10 · âm→0 |

---

## Layer 3A — Vận hành & Dấu chân số (190 điểm)

### E-Invoice Vitality (60đ)

**Input:** `einvoices["du_lieu_theo_thang"]`  
**Tính slope:** linear regression trên monthly revenue series

```python
import numpy as np
revs = [m["tong_doanh_thu_mn_vnd"] for m in monthly_data]
x = np.arange(len(revs))
slope = np.polyfit(x, revs, 1)[0]
norm_slope = slope / np.mean(revs)   # normalized slope
```

| Điều kiện | Điểm |
| --------- | ---- |
| active_months ≥ 11 và norm_slope > 0.01 | 60 |
| active_months ≥ 9 và norm_slope ≥ -0.01 | 40 |
| active_months 6–8 | 20 |
| active_months < 6 hoặc norm_slope < -0.03 | 5 |

### Customer Concentration (50đ)

**Input:** `einvoices["customer_concentration_top5_pct"]`

| top5 % | Điểm |
| ------ | ---- |
| < 40% | 50 |
| 40–60% | 30 |
| 60–80% | 15 |
| > 80% | 0 |

### Anchor-Supplier Network (60đ)

**Input:** `contracts["so_anchor"]`, `contracts["hop_dong"]`  
**Khi `available=false`:** 10đ (không xác định ≠ không có)

```
anchor_count = số hợp đồng có thoi_han_thang ≥ 24
```

| Điều kiện | Điểm |
| --------- | ---- |
| ≥ 3 anchors dài hạn | 60 |
| 1–2 anchors | 35 |
| 0 anchors (nhưng data available) | 10 |
| data not available | 10 |

### Bank Cash Flow Stability (20đ)

**Input:** `bank["cashflow_cv"]`, `bank["inflow_outflow_ratio"]`

| Điều kiện | Điểm |
| --------- | ---- |
| CV < 20% và I/O ratio ≥ 1.0 | 20 |
| CV 20–40% | 12 |
| CV > 40% hoặc I/O ratio < 1.0 | 2 |

---

## Layer 3B — Tuân thủ hành vi (160 điểm)

### Tax Compliance (60đ)

**Input:** `compliance["thue"]`

| Điều kiện | Điểm |
| --------- | ---- |
| Đúng hạn 24T, không cưỡng chế | 60 |
| Trễ < 30 ngày, ≤ 2 lần | 35 |
| Có nợ thuế đang xử lý | 10 |
| Bị cưỡng chế → **HARD STOP trần BB** | 0 |

```python
late_severe = [m for m in tax_history if m["so_ngay_tre"] > 30]
late_count = len([m for m in tax_history if m["trang_thai"] == "tre_han"])
```

### BHXH Compliance (50đ)

**Input:** `compliance["bhxh"]["so_thang_no_bhxh"]`

| Tháng nợ | Điểm |
| -------- | ---- |
| 0 | 50 |
| 1–2 | 25 |
| 3–6 | 8 |
| > 6 | 0 |

### Utility Compliance (30đ)

**Input:** `compliance["tien_ich"]["so_lan_tre_12t"]`

| Số lần trễ | Điểm |
| ---------- | ---- |
| 0 | 30 |
| 1–2 | 18 |
| > 2 | 5 |

### Account Vitality (20đ)

**Input:** `compliance["ngan_hang"]`

| Điều kiện | Điểm |
| --------- | ---- |
| Active ≥ 11T và ≥ 3 sản phẩm | 20 |
| ≥ 2 sản phẩm | 12 |
| Chỉ TK cơ bản | 5 |

---

## Layer 3C — ESG Behavioral Proxy (120 điểm)

### Environmental (40đ)

**Input:** `esg["moi_truong"]`

| Điều kiện | Điểm |
| --------- | ---- |
| Không vi phạm 24T | 40 |
| Bị xử phạt 1 lần | 15 |
| Trong danh sách ô nhiễm nghiêm trọng → **HARD STOP trần BB** | 0 |

### Social / Labor (40đ)

**Input:** `esg["lao_dong"]`

| Điều kiện | Điểm |
| --------- | ---- |
| Không tranh chấp 24T | 40 |
| Có tranh chấp đã giải quyết | 20 |
| Đang đình công / kiện tụng | 0 |

### Governance (40đ)

**Input:** `esg["phap_ly"]`

| Điều kiện | Điểm |
| --------- | ---- |
| Không vụ kiện nào | 40 |
| Bị đơn, đã xử xong | 20 |
| Đang tranh chấp tài chính | 5 |

---

## Layer 3D — Business Maturity (30 điểm)

### Tuổi pháp nhân (20đ)

**Input:** `maturity["tuoi_phap_nhan_nam"]`

| Tuổi | Điểm |
| ---- | ---- |
| ≥ 10 năm | 20 |
| 5–10 năm | 15 |
| 3–5 năm | 10 |
| 1–3 năm | 5 |
| < 1 năm | 0 |

### Operational Continuity — HKD tiền thân (10đ, bonus additive)

**Input:** `maturity["co_hkd_tien_than"]`, `maturity["dieu_kien_hkd"]`

```
conditions_met = sum([cung_dia_diem, cung_nganh_nghe, cung_chu])
if conditions_met == 3: +10
if conditions_met == 2: +5
else: +0
```

*Không phạt DN mới — chỉ thưởng thêm nếu chứng minh được lịch sử*

---

## Output: ScoreReport

```python
@dataclass
class LayerResult:
    layer: str               # "L1_CIC"
    diem_tho: int
    diem_max: int
    available: bool          # False nếu không có data
    chi_tiet: dict           # {tieu_chi: {diem, max, gia_tri, mo_ta}}

@dataclass
class ScoreReport:
    mst: str
    raw_score: int           # tổng điểm thô (0–1000)
    dri: float               # 0.0–1.0
    final_score: int         # raw × (0.7 + 0.3×DRI)
    rating: str              # "BBB"
    hard_stop: str | None    # None hoặc lý do
    layers: dict[str, LayerResult]
    top_factors: list[dict]  # top 3 yếu tố ảnh hưởng nhiều nhất
    approval_action: str     # "auto_approve" | "manual_review" | "auto_reject"
```
