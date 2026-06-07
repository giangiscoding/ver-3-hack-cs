# Data Module

**Vị trí:** `data/`  
**Vai trò trong hệ thống:** Sinh và cung cấp dữ liệu giả lập cho toàn bộ pipeline

← [README](../README.md)  
→ Được dùng bởi: [02_scoring.md](02_scoring.md) · [03_graph.md](03_graph.md)

---

## Vị trí trong kiến trúc modular monolith

```
data/                        ← MODULE NÀY
├── __init__.py              ← public API: load_company(mst), load_all()
├── config.py                ← statistical anchors (GSO/SBV/GDT)
├── generate_v2.py           ← CLI generator (chạy một lần)
└── output/                  ← JSON files — nguồn sự thật duy nhất
    ├── companies_master.json
    ├── layer1_cic.json
    ├── layer2_bctc.json
    ├── layer3a_einvoices.json
    ├── layer3a_bank_statements.json
    ├── layer3a_contracts.json
    ├── layer3b_compliance.json
    ├── layer3c_esg.json
    ├── layer3d_maturity.json
    ├── graph.json
    └── analytics_flat.csv
```

**Public API** (module khác gọi vào đây, không đọc file trực tiếp):

```python
from data import load_company, load_all_flat

company = load_company("0123456789")
# Trả về: CompanyBundle(meta, cic, bctc, einvoices, bank, compliance, esg, maturity, contracts)

df = load_all_flat()
# Trả về: pd.DataFrame — analytics_flat.csv
```

---

## Thiết kế 2 giai đoạn

### Stage 1 — Anchor thống kê thật

Lấy phân phối từ nguồn công khai Việt Nam, không phải phán đoán tuỳ ý:

| Tham số | Nguồn | Giá trị |
| ------- | ----- | ------- |
| Phân bổ ngành | GSO 2022 | Trade 35%, Mfg 18%, Const 13%, F&B 9%... |
| Phân bổ địa lý | GSO 2022 | HCM 35%, HN 20%, BD 8%... |
| Phân bổ phân khúc | SBV 2023 | Micro 50%, Small 35%, Medium 15% |
| D/E trung bình | SBV | 2.1 (cao hơn ASEAN average) |
| Tax late filing | GDT | 30% có trễ hạn ≥1 lần |
| Thin-file rate | SBV | 42% Micro không có CIC |

### Stage 2 — Điều chỉnh MSME

Sau khi sample metadata, áp các điều chỉnh đặc thù MSME:

- **Thin-file:** Micro 42% không có CIC, 68% không có BCTC
- **D/E inflate:** nhân thêm 1.25× cho Micro (ít vốn tự có)
- **Seasonal pattern:** doanh thu theo tháng điều chỉnh theo ngành và mùa vụ Việt Nam

---

## Fundamentals-driven health (population heterogeneity)

Thay vì một biến `health` duy nhất điều khiển mọi chỉ số, generator mô hình hóa
**5 nền tảng tiềm ẩn** (fundamentals), mỗi cái sinh ra một nhóm dữ liệu:

| Fundamental | Sinh ra | Layer |
| --- | --- | --- |
| `fin` | DSCR, D/E, EBITDA, current ratio... | BCTC |
| `credit` | nhóm nợ, utilization, debt growth | CIC |
| `cashflow` | CV dòng tiền, in/out ratio, nợ BHXH | Bank |
| `tax` | số tháng đúng hạn, cưỡng chế, trễ tiện ích | Compliance |
| `div` | đa dạng khách hàng (concentration) | E-invoice |

**Creditworthiness thật** = `compute_health(funds, archetype)` = tổ hợp có **trọng số
KHÁC NHAU theo nhóm dữ liệu** (`HEALTH_DRIVER_WEIGHTS`):

| Archetype | fin | credit | cashflow | tax | div |
| --- | --- | --- | --- | --- | --- |
| FULL | .34 | .34 | .14 | .10 | .08 |
| NO_CIC | .42 | .04 | .26 | .18 | .10 |
| NO_BCTC | .05 | .36 | .36 | .13 | .10 |
| L3_ONLY | .05 | .05 | .40 | .30 | .20 |

→ Phản ánh thực tế: **sống còn của micro thin-file phụ thuộc kỷ luật dòng tiền +
tuân thủ thuế**, còn DN lớn phụ thuộc tỷ số tài chính + lịch sử tín dụng. Cùng một
feature tác động tới rủi ro với trọng số khác nhau theo nhóm → tạo **population
heterogeneity** → cluster model có signal riêng → stacked blend cải thiện.

**`FUND_RHO`** (mặc định 0.40) điều khiển độ tương quan giữa các fundamentals với
"chất lượng chung": `fund_k = μ + ρ·(base−μ) + √(1−ρ²)·ε` (giữ nguyên variance).

- ρ cao → DN tốt đều mọi mặt (đồng nhất) → blend cải thiện ít (+1-3%).
- ρ thấp → thin-file là quần thể khác biệt (vd DN lời nhưng cẩu thả thuế) → blend +5%+.

Xem [07_ml_cluster.md](07_ml_cluster.md) cho thực nghiệm chứng minh.

---

## Schema từng output file

### `companies_master.json` — array of Company

```json
{
  "mst": "7921819600",
  "ten_doanh_nghiep": "Công ty TNHH Thương Mại Thành Công",
  "loai_hinh": "Công ty TNHH",
  "phan_khuc": "Small",
  "nganh_chinh": "G",
  "mo_ta_nganh": "Bán buôn và bán lẻ...",
  "tinh_thanh_pho": "TP. Hồ Chí Minh",
  "dia_chi": "Số 42 Lê Lợi, Phường 1, TP. Hồ Chí Minh",
  "nguoi_dai_dien": "Nguyễn Văn Minh",
  "email": "info@7921819600.vn",
  "sdt": "0912345678",
  "doanh_thu_bn_vnd": 18.5,
  "so_nhan_vien": 24,
  "ngay_thanh_lap": "2018-03-15",
  "tuoi_doanh_nghiep_nam": 7.7
}
```

### `layer1_cic.json` — keyed by MST

```json
{
  "available": true,
  "debt_group_current": 1,
  "debt_group_history_24m": [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
  "worst_debt_group_24m": 1,
  "credit_utilization_pct": 52.3,
  "num_financial_institutions": 2,
  "debt_growth_12m_pct": 18.4
}
```

Khi `"available": false`:
```json
{ "available": false, "ly_do": "Thin-file — chưa có lịch sử tín dụng TCTD" }
```

### `layer2_bctc.json` — keyed by MST

```json
{
  "available": true,
  "revenue_bn_vnd": { "year_n_2": 12.1, "year_n_1": 15.3, "year_n": 18.5 },
  "cagr_3y_pct": 10.2,
  "ebitda_bn_vnd": 1.48,
  "ebitda_margin_pct": 8.0,
  "vcsh_bn_vnd": 3.2,
  "total_debt_bn_vnd": 7.5,
  "de_ratio": 2.34,
  "current_ratio": 1.35,
  "cash_conversion_cycle_days": 58,
  "dscr": 1.28,
  "annual_debt_service_bn_vnd": 1.16
}
```

### `layer3a_einvoices.json` — keyed by MST

```json
{
  "available": true,
  "mst_doanh_nghiep": "7921819600",
  "so_thang_co_hoa_don": 11,
  "customer_concentration_top5_pct": 48.2,
  "du_lieu_theo_thang": [
    {
      "thang": "2025-01",
      "tong_doanh_thu_mn_vnd": 1850.3,
      "so_hoa_don": 42,
      "chi_tiet_nguoi_mua": [
        { "mst_nguoi_mua": "0287347143", "ten_nguoi_mua": "...", "so_tien_mn_vnd": 620.1 }
      ]
    }
  ]
}
```

### `layer3a_bank_statements.json` — keyed by MST

```json
{
  "available": true,
  "mst_doanh_nghiep": "7921819600",
  "cashflow_cv": 0.18,
  "inflow_outflow_ratio": 1.09,
  "du_lieu_theo_thang": [
    { "thang": "2025-01", "tong_thu_mn_vnd": 1920.5, "tong_chi_mn_vnd": 1760.3, "so_du_cuoi_thang_mn_vnd": 840.2, "so_giao_dich": 87 }
  ]
}
```

### `layer3b_compliance.json` — keyed by MST

```json
{
  "available": true,
  "thue": {
    "so_thang_dung_han_24t": 22,
    "co_cuong_che": false,
    "lich_su_24_thang": [ { "thang": "2024-01", "trang_thai": "dung_han", "so_ngay_tre": 0 } ]
  },
  "bhxh": { "so_thang_no_bhxh": 0, "co_no_bhxh": false, "so_nhan_vien_dong_bhxh": 22 },
  "tien_ich": {
    "so_lan_tre_12t": 1,
    "lich_su_12_thang": [ { "thang": "2025-01", "trang_thai": "dung_han_auto_debit" } ]
  },
  "ngan_hang": { "so_san_pham_dang_dung": 3, "so_thang_active_12t": 12 }
}
```

### `layer3c_esg.json` — keyed by MST

```json
{
  "available": true,
  "moi_truong": { "so_vi_pham_24t": 0, "trong_danh_sach_o_nhiem_nghiem_trong": false },
  "lao_dong": { "so_tranh_chap_24t": 0, "dang_dinh_cong": false },
  "phap_ly": { "so_vu_kien_kinh_te_active": 0, "la_bi_don": false }
}
```

### `layer3d_maturity.json` — keyed by MST

```json
{
  "available": true,
  "ngay_dang_ky": "2018-03-15",
  "tuoi_phap_nhan_nam": 7.7,
  "co_hkd_tien_than": true,
  "dieu_kien_hkd": { "cung_dia_diem": true, "cung_nganh_nghe": true, "cung_chu": true }
}
```

### `graph.json`

```json
{
  "nodes": [
    { "id": "7921819600", "type": "doanh_nghiep", "phan_khuc": "Small", "nganh": "G" },
    { "id": "owner_7921819600", "type": "chu_so_huu", "ten": "Nguyễn Văn Minh" }
  ],
  "edges": [
    { "source": "owner_7921819600", "target": "7921819600", "type": "so_huu", "phan_tram": 80 },
    { "source": "shadow_controller_0", "target": "7921819600", "type": "so_huu_cheo", "phan_tram": 35 }
  ],
  "fraud_clusters": [ ["mst1", "mst2", "mst3"] ],
  "fraud_edge_count": 28
}
```

Edge types: `so_huu` · `so_huu_cheo` · `cung_dia_chi` · `giao_dich_noi_bo` · `giao_dich_thuong_mai`

---

## Cách chạy

```bash
# Sinh mới (overwrite output/)
python data/generate_v2.py --n 5000

# Kiểm tra nhanh
python data/generate_v2.py --n 100
```

---

## Thống kê dataset hiện tại

| Chỉ số | Giá trị |
| ------ | ------- |
| Tổng công ty | 5.000 |
| Micro / Small / Medium | 2.515 / 1.749 / 736 |
| CIC có dữ liệu | 71.3% |
| BCTC có dữ liệu | 54.1% |
| E-Invoice có dữ liệu | 91.0% |
| Fraud clusters | 101 clusters · 300 công ty (6%) |
| Hard-stop D | 86 công ty (CIC G4-5) |
| Hard-stop BB cap | 437 công ty (cưỡng chế thuế) |
