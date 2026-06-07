# 07 — Cluster-based ML Scoring

← [02_scoring](02_scoring.md) · [04_dri](04_dri.md) · [05_rating](05_rating.md)
→ [06_ui](06_ui.md)

> **Ý tưởng cốt lõi:** **chấm độ đầy đủ + chất lượng dữ liệu**, **phân nhóm** theo
> mẫu dữ liệu có sẵn, rồi chấm điểm bằng **stacked blend**: một global model làm nền
> (khử nhiễu, pool toàn bộ data) + **mô hình chuyên biệt từng nhóm** tinh chỉnh.
> Một MSME thiếu CIC được đánh trong khung phù hợp với dữ liệu nó thực sự có.
> **Tại sao blend chứ không pure-router?** Pure-router (chỉ model riêng từng nhóm)
> THUA global ~6% vì global pool data khử nhiễu tốt hơn; nhưng **blend = global +
> cluster THẮNG global ~1-3%** (xem phần Thực nghiệm cuối tài liệu).

---

## Pipeline tổng quan

```
CompanyBundle
   │
   ├─▶ [1] DQI scoring            scorer/data_quality.py
   │       6 nguồn → vector chất lượng [0,1]⁶
   │
   ├─▶ [2] Cluster classification  scorer/cluster.py
   │       DQI(CIC), DQI(BCTC) vs ngưỡng 0.5 → 1 trong 4 cluster
   │
   ├─▶ [3] Feature extraction      ml/features.py
   │       Bộ feature riêng cluster + full set cho global (NaN-native)
   │
   ├─▶ [4] STACKED BLEND           ml/predict.py
   │       score = w·global(x) + (1-w)·cluster_model(x)
   │       global = LightGBM toàn bộ feature; cluster = model auto-chọn
   │
   ├─▶ [5] SHAP explanation        ml/predict.py + ml/registry.py
   │       Top-3 yếu tố từ cluster model (tree → TreeExplainer, linear → coef×x)
   │
   ├─▶ [6] DRI confidence haircut  scorer/dri.py
   │       final = raw × (0.7 + 0.3·DRI)
   │
   └─▶ [7] Master scale rating     scorer/rating.py
           1 thang calibrated + trần theo cluster
```

---

## [1] Data Quality Index (DQI)

Mỗi nguồn được chấm `[0,1]` dựa trên **độ đầy đủ** + **chất lượng nội tại**:

| Nguồn | Cách chấm |
| --- | --- |
| CIC | 0.5·nhóm_nợ + 0.3·utilization + 0.2·số_TCTD |
| BCTC | 0.6·độ_sâu(số năm) + 0.4·đầy_đủ(số chỉ số) |
| E-invoice | số tháng có hóa đơn / 12 |
| Bank | số tháng sao kê / 12 |
| Compliance | lịch sử thuế / 24 tháng |
| ESG | có/không |

`overall = 0.25·CIC + 0.25·BCTC + 0.15·einvoice + 0.15·bank + 0.10·compliance + 0.10·esg`

---

## [2] Cluster classification (DQI-based)

`DQI_THRESHOLD = 0.5`. **Khác biệt quan trọng:** không phải binary
available/not — một CIC chỉ có 6 tháng lịch sử → DQI < 0.5 → xếp NO_CIC.

| Cluster | Điều kiện | n (5000) | Trần rating |
| --- | --- | --- | --- |
| FULL | CIC ≥ 0.5 **và** BCTC ≥ 0.5 | ~1901 | — |
| NO_CIC | chỉ BCTC ≥ 0.5 | ~805 | AA |
| NO_BCTC | chỉ CIC ≥ 0.5 | ~1240 | A |
| L3_ONLY | cả hai < 0.5 | ~1054 | BBB |

Trần xếp hạng = chính sách tín dụng: thiếu dữ liệu truyền thống thì không thể
đạt hạng cao nhất dù điểm cao.

---

## [3-4] Stacked blend per cluster

**Global model** (`ml/models/global.pkl`): 1 LightGBM trên toàn bộ feature set
(28 cols, NaN-native), train trên cả 5000 DN → nền khử nhiễu mạnh.

**Cluster model** (`ml/models/cluster_*.pkl`): mỗi cluster **auto-chọn loại model
tốt nhất theo CV** (`ml/registry.py`), dùng bộ feature riêng. Ứng viên:
`lgbm_strong`, `lgbm_small` (regularized cho nhóm ít data), `ridge` (linear).

**Blend** theo trọng số tune trên validation (`ml/models/blend.json`):

```
score = w · global(x) + (1 - w) · cluster_model(x)
```

| Cluster | model chọn | w_global | Ý nghĩa |
| --- | --- | --- | --- |
| FULL | ridge | 0.15–0.25 | cluster đóng góp ~80% (nhiều tín hiệu riêng) |
| NO_CIC | ridge | 0.75 | global + cluster refine |
| NO_BCTC | ridge | 0.25–0.40 | cluster đóng góp mạnh |
| L3_ONLY | ridge | 0.70 | global trội nhưng cluster vẫn refine |

(w tự học theo độ heterogeneity của data — xem [01_data](01_data.md) về `FUND_RHO`.)

**Target:** `health_score × 1000`. Trong synthetic data, `health_score ∈ [0,1]`
là biến tiềm ẩn (creditworthiness thật) — tổ hợp 5 fundamentals với **trọng số
khác nhau theo nhóm** (xem [01_data](01_data.md)). Production thay bằng PD lịch sử.

---

## [5] SHAP explanation

Top-3 yếu tố lấy từ **cluster model** (đúng bộ feature nhóm có) → giải thích luôn
dựa trên tín hiệu DN thực sự có. Xử lý cả tree (TreeExplainer) lẫn linear
(đóng góp = coef × feature chuẩn hóa, `ml/registry.py`):

```
FULL — final 698 → A:
  ↑ BCTC — DSCR: +73
  ↑ CIC — Nhóm nợ xấu nhất 24T: +34
  ↓ Ngân hàng — Tỷ lệ tiền vào/ra: -30
```

---

## [7] Master scale calibration

**Một thang rating duy nhất** cho mọi cluster → "BB luôn mang cùng mức rủi ro".
Ngưỡng **suy ra từ phân phối điểm blend×DRI thực** (`ml/calibrate.py`), không hardcode.

| Rating | AAA | AA | A | BBB | BB | B | CCC | D |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Ngưỡng ≥ | 800 | 720 | 620 | 510 | 420 | 340 | 270 | 0 |
| Thực tế % | 1 | 4 | 12 | 20 | 22 | 18 | 12 | 12 |

Phân biệt giữa cluster đến từ: (1) điểm blend thấp hơn khi ít dữ liệu,
(2) **trần xếp hạng** theo cluster (NO_CIC→AA, NO_BCTC→A, L3_ONLY→BBB).

---

## Thực nghiệm: vì sao stacked blend

`python -m ml.compare` — so sánh 3 kiến trúc trên cùng held-out test set:

| Kiến trúc | Test MAE | vs global |
| --- | --- | --- |
| Global LightGBM | 42.1 | baseline |
| Pure router (model riêng/cluster) | 42.4 | −0.6% |
| **Stacked blend** | **39.8** | **+5.4%** |

Per-cluster (blend vs global): FULL +6.9%, NO_BCTC +6.7%, NO_CIC +4.0%, L3_ONLY +3.1%.

**Mức cải thiện phụ thuộc độ heterogeneity của quần thể** (`FUND_RHO` trong generator):

- ρ cao (DN tốt đều mọi mặt) → blend chỉ +1-3%, pure router thua ~6%.
- ρ thấp (thin-file là quần thể khác biệt: vd DN lời nhưng cẩu thả thuế) → blend +5%+,
  pure router gần hòa global. Ta dùng ρ=0.40 (thin-file thực sự khác biệt).

**Bài học:** với dữ liệu tín dụng (latent creditworthiness, features là quan sát
nhiễu), GBM global + NaN-native là baseline mạnh; hard-routing không tự thắng được.
Nhưng cluster model như **lớp tinh chỉnh** (blend) cải thiện thật, càng nhiều khi
quần thể càng heterogeneous. Cộng giá trị **governance**: trần rating, calibration
& giải thích riêng nhóm.

---

## Engine: ML primary + rule fallback

`scorer/engine.py` ưu tiên blend ML; nếu `ml/models/` chưa có → tự động fallback
rule-based cluster scoring (`scorer/layers/` + cluster weights).

`ScoreReport` có: `cluster`, `dqi` (profile dict), `scoring_method` ("ml"/"rule_based").

---

## Chạy

```bash
python -m ml.train        # global + cluster models + blend weights → ml/models/
python -m ml.calibrate    # calibrate master scale → ml/models/master_scale.json
python -m ml.compare      # so sánh global vs router vs blend
```

Re-calibrate sau mỗi lần train lại.
