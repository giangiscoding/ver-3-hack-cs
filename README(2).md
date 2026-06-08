# ScoreSight — Nền tảng chấm điểm tín dụng MSME (SHB)

A working multi-portal prototype for an alternative-data credit-scoring platform,
wired end-to-end to the **live ScoreSight model** (LightGBM + per-segment
calibration + PDO scorecard) on the 300-SME sample dataset.

One common login → three role-based experiences:

| Vai trò | Cổng | Thấy gì |
|---|---|---|
| **Doanh nghiệp / Khách hàng** | `/customer/*` | Hồ sơ + kết quả **rút gọn** (trạng thái, hạn mức dự kiến, bước tiếp theo). Không thấy điểm/PD/SHAP/quy tắc. |
| **Cán bộ ngân hàng (RM/CBTĐ)** | `/bank/*` | Điểm số, hạng rủi ro, lý do **theo tiêu chí**, luồng Xanh/Vàng/Đỏ, bảng lợi ích vận hành. Không thấy SHAP thô/cấu hình rule/trọng số. |
| **Quản trị & Kiểm toán** | `/admin/*` | Giám sát mô hình, kiểm toán hồ sơ đầy đủ, **SHAP**, rule engine (**maker-checker**), ma trận phân quyền, giám sát tích hợp, nhật ký. |

## Tài khoản demo

| Vai trò | Username | Password |
|---|---|---|
| Doanh nghiệp | `Customer_123` | `Customer_123` |
| Cán bộ ngân hàng | `Bankuser_123` | `Bankuser_123` |
| Quản trị / Kiểm toán | `Bank_admin` | `Bank_admin` |

---

## Chạy thử (local)

Cần **2 terminal**: một cho backend (FastAPI), một cho frontend (Vite).

### 1) Backend — FastAPI (cổng 8000)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Lần khởi động đầu mất ~5–10 giây: hệ thống chấm điểm toàn bộ 300 hồ sơ + tính SHAP một lần rồi cache.
Kiểm tra: mở http://localhost:8000/api/health → `{"status":"ok", ...}`.

### 2) Frontend — React + Vite (cổng 5173)

```bash
cd frontend
npm install
npm run dev
```

Mở **http://localhost:5173** và đăng nhập bằng một tài khoản demo ở trên.
Vite proxy chuyển mọi request `/api/*` sang backend ở cổng 8000 (xem `frontend/vite.config.js`).

---

## Kiến trúc

```
scoresight-platform/
├── backend/                  FastAPI · wired to the real model
│   ├── artifacts/            model bundle, sample CSV, weights, configs
│   ├── engine.py             scoring pipeline (mirrors deployed /score)
│   ├── store.py              precompute 300 cases, aggregates, rule engine, audit log
│   ├── security.py           login, opaque tokens, role gating
│   ├── main.py               API: /api/login + customer/bank/admin routes
│   └── requirements.txt
└── frontend/                 React + Vite · SHB branded, Vietnamese
    └── src/
        ├── pages/            Login + customer/* + bank/* + admin/*
        ├── components/       Shell, UI primitives, SVG charts, icons
        └── lib/              api client, auth context, formatting
```

### Mô hình (thật, không mô phỏng)
- **Điểm:** thang 300–850 (PDO=50, base 600 @ odds 9:1).
- **Ngưỡng quyết định:** duyệt ≥ 620 (Xanh) · xem xét ≥ 540 (Vàng) · từ chối < 540 (Đỏ).
- **Hạng rủi ro:** A ≥ 700 · B ≥ 620 · C ≥ 540 · D < 540.
- **DSR (độ dày dữ liệu):** thin / semi / thick → chọn đầu hiệu chỉnh xác suất & hệ số hạn mức (0.5 / 0.75 / 1.0).
- **Hạn mức nền:** micro 50tr · small 200tr · medium 1 tỷ VND.
- **Quy tắc cứng:** `shared_device_risk_flag = 1` → từ chối ngay (tín hiệu gian lận).
- **Giải thích:** SHAP TreeExplainer (đầy đủ ở cổng kiểm toán; rút gọn theo tiêu chí ở cổng cán bộ).

> Cùng **một đường scoring** dùng cho cả 300 hồ sơ mẫu lẫn hồ sơ mới nộp/चấm nhanh — khớp với endpoint `/score` triển khai thật.

### Lưu ý
- Đây là **prototype**: token phiên lưu trong bộ nhớ; rule engine & nhật ký kiểm toán là trạng thái in-memory (khởi động lại sẽ reset).
- Toàn bộ chữ giao diện bằng tiếng Việt; font **Be Vietnam Pro** (hỗ trợ dấu tiếng Việt).
- Bảng màu SHB: cam `#F56B29`, navy `#0F1B2D`.
