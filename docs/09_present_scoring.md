# TÀI LIỆU PRESENT — Hệ thống Chấm điểm Tín dụng MSME/SME

> Toàn bộ công thức, tiêu chí dữ liệu và logic chấm điểm. Trích trực tiếp từ code,
> không phải spec — đảm bảo khớp 100% với hệ thống đang chạy.

---

## 0. PIPELINE TỔNG QUAN

```
CompanyBundle (dữ liệu thô 6 nguồn)
   │
   ├─[1] DQI        → đo chất lượng từng nguồn → vector [0,1]⁶
   │
   ├─[2] CLUSTER    → phân 4 nhóm theo DQI(CIC), DQI(BCTC)
   │
   ├─[3] ML BLEND   → score = w·global(x) + (1-w)·cluster(x)   ∈ [0,1000]
   │
   ├─[4] SHAP       → top-3 yếu tố ảnh hưởng
   │
   ├─[5] DRI        → final = raw × (0.7 + 0.3·DRI)
   │
   └─[6] RATING     → master scale + trần cluster + hard-stop → AAA..D
```

**Triết lý cốt lõi:** một MSME thiếu CIC/BCTC vẫn được chấm trong khung phù hợp với
dữ liệu nó **thực sự có** — thay vì bị loại vì thiếu hồ sơ truyền thống.

---

## 1. SCORECARD 1000 ĐIỂM — 3 LỚP

| Lớp | Câu hỏi rủi ro | Điểm | Bản chất dữ liệu |
|-----|----------------|------|------------------|
| **L1 — CIC** | Lịch sử trả nợ với TCTD? | 200 | Quá khứ tín dụng |
| **L2 — BCTC** | Năng lực tài chính nội tại? | 300 | Cấu trúc tài chính |
| **L3 — Phi truyền thống** | Đang vận hành & tuân thủ tốt? | 500 | Dấu chân số thời gian thực |

**Nguyên tắc MECE** (chống trùng lặp):
- Khả năng trả nợ → **chỉ** đo bằng DSCR (L2). Sao kê ở L3 chỉ đo **độ ổn định** dòng tiền.
- Lịch sử trả nợ → **chỉ** ở CIC (L1). Thuế/BHXH ở L3 đo **nghĩa vụ ngoài tín dụng**.
- Doanh thu → biến **phân khúc/chuẩn hóa**, không tính điểm trực tiếp 2 lần.

---

## 2. CHI TIẾT TIÊU CHÍ TỪNG LỚP (công thức IF/ELSE)

### LỚP 1 — CIC (200đ)

| Tiêu chí | Max | Logic chấm |
|----------|-----|------------|
| Nhóm nợ hiện tại | 80 | G1→80 · G2→40 · G3→10 · G4-5→0 (hard stop D) |
| Lịch sử nợ xấu 24T | 40 | worst≤1→40 · worst=2 (1 lần)→25 · worst=2 (nhiều)→15 · G3+→0 |
| Credit Utilization | 40 | <50%→40 · 50-80%→25 · 80-100%→10 · >100%→0 |
| Số TCTD | 25 | 1-3→25 · 4-5→15 · >5→5 (dấu hiệu vay chồng) |
| Tăng trưởng dư nợ 12T | 15 | <30%→15 · 30-70%→8 · >70%→0 (over-leveraging) |

### LỚP 2 — BCTC (300đ)

| Tiêu chí | Max | Logic chấm |
|----------|-----|------------|
| DSCR (khả năng trả nợ) | 80 | ≥1.5→80 · 1.25-1.5→60 · 1.0-1.25→35 · <1.0→0 |
| Đòn bẩy D/E | 60 | <1.0→60 · 1.0-2.0→40 · 2.0-3.0→20 · >3.0→0 |
| EBITDA Margin | 50 | ≥15%→50 · 10-15%→35 · 5-10%→20 · 0-5%→5 · <0→0 |
| Cash Conversion Cycle | 40 | <30d→40 · 30-60d→28 · 60-90d→15 · >90d→5 |
| Current Ratio | 40 | ≥2.0→40 · 1.5-2.0→30 · 1.0-1.5→18 · <1.0→5 |
| CAGR doanh thu 3 năm | 30 | >15%→30 · 5-15%→20 · 0-5%→10 · âm→0 |

### LỚP 3A — Vận hành & Dấu chân số (190đ)

| Tiêu chí | Max | Logic chấm |
|----------|-----|------------|
| E-Invoice Vitality | 60 | Active≥11 & slope>+0.01→60 · Active≥9 & slope≥-0.01→40 · Active≥6→20 · else→5 |
| Customer Concentration (top-5) | 50 | <40%→50 · 40-60%→30 · 60-80%→15 · >80%→0 |
| Anchor-Supplier Network | 60 | ≥3 anchor ≥24T→60 · 1-2 anchor→35 · không có→10 |
| Bank Cash Flow Stability | 20 | CV<0.2 & I/O≥1→20 · CV<0.4→12 · else→2 |

> **Vitality slope:** hồi quy tuyến tính doanh thu theo tháng, chuẩn hóa theo mean
> (`slope/mean_rev`) → đo xu hướng tăng/giảm doanh thu HĐĐT.

### LỚP 3B — Tuân thủ hành vi (160đ)

| Tiêu chí | Max | Logic chấm |
|----------|-----|------------|
| Tax Compliance | 60 | cưỡng chế→0 (trần BB) · 24/24 đúng hạn→60 · trễ≤30d ≤2 lần→35 · nợ đang xử lý→10 · else→0 |
| BHXH Compliance | 50 | không nợ→50 · nợ≤2T→25 · nợ 3-6T→8 · >6T→0 |
| Utility Compliance | 30 | 0 lần trễ→30 · ≤2 lần→18 · >2 lần→5 |
| Account Vitality | 20 | active≥11T & ≥3 sản phẩm→20 · ≥2 sản phẩm→12 · else→5 |

### LỚP 3C — ESG Behavioral Proxy (120đ)

| Tiêu chí | Max | Logic chấm |
|----------|-----|------------|
| (E) Environmental | 40 | danh sách ô nhiễm→0 (trần BB) · 0 vi phạm→40 · có vi phạm→15 |
| (S) Social/Labor | 40 | đang đình công→0 · 0 tranh chấp→40 · đã giải quyết→20 |
| (G) Governance | 40 | 0 vụ kiện→40 · bị đơn đã xử→20 · đang tranh chấp→5 |

### LỚP 3D — Business Maturity (30đ)

| Tiêu chí | Max | Logic chấm |
|----------|-----|------------|
| Legal Entity Age | 20 | ≥10y→20 · 5-10y→15 · 3-5y→10 · 1-3y→5 · <1y→0 |
| HKD tiền thân (bonus) | 10 | đủ 3 điều kiện→10 · 2/3→5 · else→0 |

> HKD continuity là **bonus additive** — không phạt DN mới, chỉ thưởng DN có lịch sử
> hoạt động thật trước khi chuyển pháp nhân (cùng địa điểm + cùng ngành + cùng chủ).

---

## 3. DQI — DATA QUALITY INDEX (chất lượng dữ liệu)

Đo chất lượng từng nguồn → vector 6 chiều ∈ [0,1]. Dùng để **phân cluster**.

**Công thức tổng hợp:**
```
DQI_overall = 0.25·CIC + 0.25·BCTC + 0.15·eInvoice + 0.15·Bank
            + 0.10·Compliance + 0.10·ESG
```

**Từng nguồn:**

| Nguồn | Công thức |
|-------|-----------|
| **CIC** | `0.50·group_q + 0.30·util_q + 0.20·tctd_q` <br> group_q = (5−nhóm_nợ)/4 · util_q tối ưu 30-70% · tctd_q = min(1, n/4) |
| **BCTC** | `0.60·depth_q + 0.40·completeness_q` <br> depth_q = số năm có doanh thu /3 · completeness = 4 chỉ số chính có đủ không |
| **eInvoice** | `min(1, số_tháng_HĐĐT / 12)` |
| **Bank** | `min(1, số_tháng_sao_kê / 12)` |
| **Compliance** | `min(1, max(0.5, lịch_sử_thuế / 24))` · thiếu hẳn → 0.3 |
| **ESG** | có dữ liệu → 1.0 · không → 0.5 |

---

## 4. CLUSTER — PHÂN NHÓM (ngưỡng DQI = 0.50)

| Cluster | Điều kiện | Trần rating | Lý do |
|---------|-----------|-------------|-------|
| **FULL** | CIC≥0.5 & BCTC≥0.5 | — (tối đa AAA) | Đầy đủ dữ liệu |
| **NO_CIC** | CIC<0.5, BCTC≥0.5 | **AA** | Thiếu lịch sử tín dụng |
| **NO_BCTC** | CIC≥0.5, BCTC<0.5 | **A** | Thiếu báo cáo tài chính |
| **L3_ONLY** | CIC<0.5 & BCTC<0.5 | **BBB** | Chỉ có dữ liệu phi truyền thống |

> Mỗi cluster dùng tập feature riêng và model ML riêng. Khi thiếu dữ liệu, điểm
> được **phân bổ lại** sang lớp khác (ví dụ thiếu CIC 200đ → BCTC +80, L3 +120).

---

## 5. MÔ HÌNH ML — STACKED BLEND

**Công thức blend:**
```
score = w · global(x)  +  (1 − w) · cluster_model(x)
```

- **Global model** (LightGBM, 28 features, NaN-native): nền khử nhiễu, pool toàn bộ data
- **Cluster model** (auto-chọn: Ridge/LightGBM/CatBoost): tinh chỉnh riêng nhóm
- **w**: trọng số tune trên validation, mỗi cluster một giá trị

**Trọng số thực tế (blend.json):**

| Cluster | Model | w (global) | Diễn giải |
|---------|-------|-----------|-----------|
| FULL | Ridge | 0.15 | cluster đóng góp 85% (đủ data) |
| NO_BCTC | Ridge | 0.25 | cluster 75% |
| L3_ONLY | Ridge | 0.70 | global 70% (ít data) |
| NO_CIC | Ridge | 0.75 | global 75% (ít data nhất) |

**Kết quả so sánh kiến trúc:**

| Kiến trúc | Test MAE | vs global |
|-----------|----------|-----------|
| Global LightGBM | 42.1 | baseline |
| Pure router | 42.4 | −0.6% (thua) |
| **Stacked blend** | **39.7** | **+5.7%** |

> **Vì sao Ridge thắng?** Dữ liệu synthetic xây từ công thức scorecard tuyến tính →
> quan hệ feature-target tuyến tính → Ridge khớp tự nhiên. Khi dùng data thật (PD
> lịch sử, phi tuyến) thì auto-select sẽ tự chuyển sang CatBoost/LightGBM.

**SHAP giải thích:** top-3 yếu tố lấy từ cluster model — tree dùng TreeExplainer,
linear dùng `coef × feature_chuẩn_hóa`.

---

## 6. DRI — DATA RICHNESS INDEX (hệ số chiết khấu)

Điểm chỉ tin cậy khi đủ dữ liệu → áp DRI làm **hệ số nhân**, không cộng điểm.

**Công thức:**
```
DRI = 0.35·Coverage + 0.30·Depth + 0.15·Freshness + 0.20·CrossValidation

Điểm_cuối = Điểm_thô × (0.7 + 0.3 × DRI)
```
→ DRI=0 vẫn giữ 70% điểm; DRI=1 giữ 100%.

| Thành phần | Đo gì | Cách tính |
|------------|-------|-----------|
| **Coverage** (0.35) | Có bao nhiêu nguồn | CIC,BCTC trọng số 2; L3 trọng số 1 → /8 |
| **Depth** (0.30) | Độ sâu lịch sử | TB của: HĐĐT/12T, bank/12T, thuế/24T, BCTC/3 năm |
| **Freshness** (0.15) | Dữ liệu mới không | HĐĐT stale sau 6 tháng · thuế ≥12T → tươi |
| **Cross-Validation** (0.20) | Các nguồn có khớp nhau | BCTC rev ≈ eInvoice rev · BHXH nhân viên ≈ thực · Bank inflow ≈ eInvoice |

> **Cross-validation** là điểm sáng: phát hiện gian lận mềm — nếu doanh thu khai trên
> BCTC lệch quá xa hóa đơn điện tử thực tế → DRI giảm → điểm bị chiết khấu.

---

## 7. RATING — MASTER SCALE (calibrated)

**8 bậc, ngưỡng calibrate theo phân phối thực** (không chia đều 0-1000):

| Hạng | Điểm | Rủi ro | Hành động | Tỉ lệ thực tế |
|------|------|--------|-----------|---------------|
| AAA | 800-1000 | Rất thấp | auto_approve | 0.8% |
| AA | 720-800 | Thấp | auto_approve | 3.7% |
| A | 620-720 | Thấp-TB | auto_approve | 11.6% |
| BBB | 510-620 | Trung bình | conditional_approve | 19.8% |
| BB | 420-510 | TB-Cao | manual_review | 21.7% |
| B | 340-420 | Cao | senior_review | 18.1% |
| CCC | 270-340 | Rất cao | auto_reject | 12.4% |
| D | <270 | Vỡ nợ | auto_reject | 12.0% |

> **MASTER SCALE DUY NHẤT** cho mọi cluster → hạng BB mang cùng ý nghĩa rủi ro dù DN
> thuộc nhóm nào. Khác biệt cluster thể hiện qua điểm ML + trần rating.

### Hard-stops (override bất kể điểm)

| Điều kiện | Hậu quả |
|-----------|---------|
| CIC nhóm nợ 4-5 | → **D** ngay lập tức |
| Fraud: circular + shared_controller | → **D** |
| Đang cưỡng chế thuế | → trần **BB** |
| Trong danh sách ô nhiễm nghiêm trọng | → trần **BB** |
| shared_controller đơn lẻ | → giảm **1 bậc** |
| Trần cluster (NO_CIC=AA, NO_BCTC=A, L3_ONLY=BBB) | → áp trần |

---

## 8. GRAPH FRAUD DETECTION (Neo4j)

**Mô hình đồ thị:**
```
(:Company {mst, phan_khuc, nganh, rating, final_score})
(:Owner   {id, ten, flag})
(:Owner)-[:OWNS / OWNS_CROSS]->(:Company)
(:Company)-[:SAME_ADDRESS / INTERNAL_TXN / TRADE]->(:Company)
```

**3 pattern + trọng số rủi ro:**

| Pattern | Phát hiện | Risk weight | Flag |
|---------|-----------|-------------|------|
| Shadow controller | 1 chủ nắm chéo ≥2 DN | 0.45 | shared_controller |
| Circular transaction | vòng giao dịch nội bộ quay về | 0.55 | circular_transaction |
| Shell company | chia sẻ địa chỉ với DN khác | 0.30 | shell_company |

`fraud_risk_score = min(1.0, Σ weights)` — tích hợp thẳng vào hard-stop của rating.

---

## 9. SỐ LIỆU DEMO

| Chỉ số | Giá trị |
|--------|---------|
| Tổng công ty | 5.000 |
| Micro / Small / Medium | 2.481 / 1.713 / 806 |
| CIC / BCTC / eInvoice có data | 72.3% / 54.8% / 90.7% |
| Cluster FULL/NO_CIC/NO_BCTC/L3_ONLY | 1.970 / 772 / 1.214 / 1.044 |
| Graph | 8.712 nodes · 18.546 edges · 297 business group · bậc TB 3.7 quan hệ/DN · ~6% rủi ro |
| Stacked Blend MAE | 39.7 (±4% thang 1000) |

---

## 10. ĐIỂM NHẤN KHI PRESENT

1. **Bao phủ thin-file:** MSME thiếu CIC/BCTC (gần 1/2 dataset) vẫn chấm được — không bị loại.
2. **MECE chống trùng lặp:** mỗi lớp đo một loại rủi ro khác biệt, không double-count.
3. **DRI chống điểm ảo:** dữ liệu mỏng bị chiết khấu, cross-validation bắt khai khống.
4. **Stacked blend > 1 model:** kết hợp global ổn định + cluster chuyên biệt (+5.7% MAE).
5. **Auto-select model:** hệ thống tự chọn Ridge/LightGBM/CatBoost theo CV — không cứng nhắc.
6. **Master scale calibrated:** phân phối hạng khớp credit pyramid thực tế ngành NH.
7. **Graph fraud:** phát hiện sở hữu chéo / shell / circular — tích hợp hard-stop rating.
8. **Giải thích được (SHAP):** mỗi quyết định có top-3 lý do → minh bạch, audit được.
