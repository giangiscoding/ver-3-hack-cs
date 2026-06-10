# ScoreSight Platform — Tổng quan hệ thống

> Demo chấm điểm tín dụng MSME bằng dữ liệu phi truyền thống.  
> Backend: FastAPI · Frontend: React + Vite · Model: LightGBM + SHAP

---

## 1. Kiến trúc tổng quát

```
Browser (React SPA)
      │  fetch("/api/...")  Bearer <token>
      ▼
FastAPI  :8000
  ├── security.py   — xác thực, phát token, phân quyền
  ├── engine.py     — pipeline chấm điểm (DSR → LightGBM → PDO → SHAP)
  ├── store.py      — tải 300 hồ sơ mẫu, batch-score, rule engine, audit log
  └── main.py       — định nghĩa tất cả endpoint, định hình response theo vai trò
```

Frontend chạy trên Vite dev-server `:5173`, proxy `/api/*` xuống backend `:8000`.  
Token lưu trong `window.__ss_token` (in-memory, mất khi refresh trang).

---

## 2. Công nghệ sử dụng

### Backend

| Thư viện | Phiên bản | Vai trò |
|---|---|---|
| **FastAPI** | ≥0.115 | HTTP framework, validation, CORS |
| **Uvicorn** | ≥0.30 | ASGI server (`--reload` khi dev) |
| **Pydantic** | ≥2.7 | Validate request body (BaseModel) |
| **LightGBM** | ≥4.6 | Mô hình phân loại tín dụng (GBT) |
| **scikit-learn** | ≥1.9 | Calibration (CalibratedClassifierCV) |
| **SHAP** | ≥0.46 | TreeExplainer — giải thích quyết định |
| **joblib** | ≥1.4 | Tải model bundle (`scoresight_bundle.joblib`) |
| **pandas** | ≥2.2 | Xử lý dữ liệu tabular |
| **numpy** | ≥2.0 | Tính toán số |
| **pyarrow** | ≥15.0 | Backend cho pandas (CSV/parquet) |

### Frontend

| Thư viện | Phiên bản | Vai trò |
|---|---|---|
| **React** | ^18.3 | UI framework |
| **react-router-dom** | ^6.26 | Client-side routing, `Protected` guard |
| **Vite** | ^5.4 | Build tool & dev server |
| **@vitejs/plugin-react** | ^4.3 | Babel transform JSX, Fast Refresh |

---

## 3. Danh sách API endpoint

### Auth & Health

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| `POST` | `/api/login` | Public | Đăng nhập; trả `token`, `role`, `display_name`, `home` |
| `GET` | `/api/health` | Public | Kiểm tra server, trả model version và số case |
| `GET` | `/api/meta` | Public | Danh sách ngành, vùng, ngưỡng quyết định |

### Customer Portal

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| `GET` | `/api/customer/application` | `customer` | Lấy trạng thái hồ sơ (rút gọn — không có điểm/SHAP) |
| `POST` | `/api/customer/application` | `customer` | Nộp hồ sơ mới; chạy scoring pipeline ngay lập tức |

**Luồng đặc biệt:** `customer_green` được pin trong `_PINNED_APPS` → GET luôn trả `decision: approve` (xanh), không bao giờ bị ghi đè dù user có submit form.

### Bank User Portal

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| `GET` | `/api/bank/cases` | `bank_user`, `admin` | Danh sách hồ sơ; filter `?q=` (tìm kiếm) và `?flow=green/yellow/red` |
| `GET` | `/api/bank/cases/{cid}` | `bank_user`, `admin` | Chi tiết hồ sơ: điểm, hạng rủi ro, lý do theo tiêu chí, ops panel |
| `POST` | `/api/bank/quick-score` | `bank_user`, `admin` | Chấm điểm nhanh tại chỗ (không lưu vào store) |

### Admin / Audit Portal

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| `GET` | `/api/admin/monitoring` | `admin` | Tổng hợp danh mục: tỷ lệ phê duyệt, phân phối flow/tier/DSR/PD |
| `GET` | `/api/admin/cases` | `admin` | Danh sách hồ sơ với filter `?q=` |
| `GET` | `/api/admin/cases/{cid}/audit` | `admin` | Full audit: SHAP chi tiết, rule engine version, input payload, nguồn dữ liệu |
| `GET` | `/api/admin/rule-engine` | `admin` | Trạng thái rule engine: active, pending, lịch sử |
| `POST` | `/api/admin/rule-engine/propose` | `admin` | Đề xuất thay đổi ngưỡng (maker) |
| `POST` | `/api/admin/rule-engine/approve` | `admin` | Duyệt thay đổi (checker — khác người đề xuất) |
| `GET` | `/api/admin/access-control` | `admin` | Ma trận phân quyền 3 vai trò |
| `GET` | `/api/admin/integration` | `admin` | Trạng thái kết nối LOS/CMS/SCF (mock latency) |
| `GET` | `/api/admin/audit-logs` | `admin` | 100 log gần nhất (LOGIN, SUBMIT, VIEW, PROPOSE, APPROVE) |

---

## 4. Pipeline chấm điểm (engine.py)

```
Input: dict{feature_name: value}
        │
        ▼
1. Hard fraud rule
   shared_device_risk_flag == 1  →  score=300, decline, red flow (dừng ngay)
        │
        ▼
2. Xây dựng feature row (build_row)
   Điền NaN cho các feature thiếu, align với danh sách FEATURES của model
        │
        ▼
3. Tính DSR — Data Sufficiency Ratio (compute_dsr)
   DSR = Σ(w_i × 1{feature_i có giá trị}) / Σ(w_i)
   Phân nhóm: thin (DSR ≤ thr_thin) | semi | thick
        │
        ▼
4. Dự đoán xác suất vỡ nợ (p_bad)
   Chọn calibrated model theo nhóm DSR (CAL_SEG[group])
   Dự phòng: GLOBAL_MODEL nếu nhóm không có calibration
        │
        ▼
5. Chuyển p_bad → PDO score (300–850)
   score = OFFSET + FACTOR × ln((1−p)/p)
   PDO=50, Base=600, BaseOdds=9.0
        │
        ▼
6. Quyết định (decision_of)
   score ≥ 620  → approve  (green)
   score ≥ 540  → manual_review  (yellow)
   score < 540  → decline  (red)
        │
        ▼
7. Tính hạn mức tín dụng (credit_limit)
   base  = BASE_LIMIT_VND[enterprise_size]  (micro/small/medium)
   limit = base × LIMIT_FACTOR[dsr_group]   (thin×0.5 / semi×0.75 / thick×1.0)
        │
        ▼
8. SHAP (TreeExplainer)
   Top-6 feature ảnh hưởng lớn nhất → nhãn tiếng Việt + chiều tác động
        │
        ▼
Output: dict{credit_score, p_bad, dsr_value, dsr_group, decision, flow,
             risk_tier, pd_band, credit_limit_vnd, top_reasons, ...}
```

---

## 5. Luồng xác thực

```
1. POST /api/login  {username, password}
   security.py: lookup ACCOUNTS dict (lowercase key)
   → phát token = secrets.token_urlsafe(24)
   → lưu _SESSIONS[token] = {username, role, display_name}
   → trả {token, role, display_name, home}

2. Mọi request tiếp theo:
   Header: Authorization: Bearer <token>
   require_roles("customer") → session_of() → kiểm tra role
   403 nếu role không khớp, 401 nếu token không tồn tại
```

**4 tài khoản demo:**

| Username | Vai trò | Ghi chú |
|---|---|---|
| `customer_123` / `Customer_123` | customer | Luồng vàng (nộp form → scoring) |
| `customer_green` / `Customer_green` | customer | Luồng xanh (pinned — luôn approve) |
| `bankuser_123` / `Bankuser_123` | bank_user | RM / Cán bộ thẩm định |
| `bank_admin` / `Bank_admin` | admin | Quản trị & Kiểm toán |

> Password = Username (case-sensitive). Backend normalize lowercase khi lưu session.

---

## 6. Routing frontend (React)

| Path | Component | Vai trò |
|---|---|---|
| `/login` | `Login.jsx` | Public |
| `/customer/dashboard` | `Dashboard.jsx` | customer |
| `/customer/application` | `NewApplication.jsx` | customer |
| `/customer/status` | `Status.jsx` | customer |
| `/bank/cases` | `Cases.jsx` | bank_user, admin |
| `/bank/cases/:cid` | `CaseDetail.jsx` | bank_user, admin |
| `/bank/quick-score` | `QuickScore.jsx` | bank_user, admin |
| `/admin/dashboard` | `Dashboard.jsx` | admin |
| `/admin/cases` | `Cases.jsx` | admin |
| `/admin/cases/:cid` | `CaseAudit.jsx` | admin |
| `/admin/rule-engine` | `RuleEngine.jsx` | admin |
| `/admin/governance` | `Governance.jsx` | admin |

`Protected` component kiểm tra `user.role` trước khi render; redirect về `/login` nếu chưa đăng nhập.

---

## 7. Phân quyền hiển thị dữ liệu

| Thông tin | Khách hàng | RM / CBTĐ | Admin |
|---|---|---|---|
| Kết quả rút gọn (trạng thái, bước tiếp theo) | ✓ | ✓ | ✓ |
| Điểm tín dụng (300–850) | ✗ | ✓ | ✓ |
| Hạng rủi ro (A/B/C/D) | ✗ | ✓ | ✓ |
| Lý do theo tiêu chí | ✗ | ✓ | ✓ |
| Giá trị SHAP chi tiết | ✗ | ✗ | ✓ |
| Cấu hình rule engine | ✗ | ✗ | ✓ |
| Nhật ký kiểm toán | ✗ | ✗ | ✓ |
| Ghi đè thủ công | ✗ | Hạn chế | ✓ (maker-checker) |

---

## 8. Dữ liệu & Artifacts

```
backend/artifacts/
├── scoresight_bundle.joblib   — model bundle: LightGBM global + calibrated segments + metadata
├── sme_altdata_sample.csv     — 300 SME mẫu (batch-scored lúc khởi động)
├── weights_refined.json       — trọng số DSR theo feature
├── dsr_config.json            — ngưỡng thin/semi/thick
└── feature_dictionary.json    — metadata feature (source, description)
```

Tất cả 300 hồ sơ được chấm điểm một lần khi `Store.__init__()` chạy (batch SHAP pass).  
Hồ sơ mới từ customer submit được chấm điểm online (single-row inference).

---

## 9. Khởi động hệ thống

```bash
# Backend
cd scoresight-platform/backend
uvicorn main:app --reload --port 8000

# Frontend
cd scoresight-platform/frontend
npm install
npm run dev          # chạy trên :5173, proxy /api/* → :8000
```

> Phải restart backend để reset `_CUSTOMER_APPS` (in-memory). `_PINNED_APPS` luôn được khởi tạo lại với dữ liệu cố định.
