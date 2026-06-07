# BẢNG TIÊU CHUẨN XẾP HẠNG TÍN DỤNG SME/MSME (1.000 ĐIỂM)
## Mô hình 3 lớp — Privacy by Design — MECE

---

## NGUYÊN TẮC MECE & PHÂN TÁCH RỦI RO

Để tránh overlap (vấn đề chính trong scorecard gốc — ví dụ DSCR ở BCTC trùng với Cash Flow Pattern ở sao kê), mỗi lớp đo **một loại rủi ro khác biệt**:

| Lớp | Câu hỏi rủi ro cốt lõi | Bản chất dữ liệu |
|-----|------------------------|------------------|
| **Lớp 1 (CIC)** | DN này có **lịch sử trả nợ** tốt với hệ thống TCTD không? | Quá khứ tín dụng |
| **Lớp 2 (BCTC)** | DN này có **năng lực tài chính nội tại** để trả nợ không? | Cấu trúc & sức khỏe tài chính |
| **Lớp 3 (Phi truyền thống)** | DN này **đang thực sự vận hành** lành mạnh & tuân thủ không? | Hành vi & dấu chân số thời gian thực |

**Quy tắc chống trùng lặp áp dụng:**
- Khả năng trả nợ → chỉ đo bằng **DSCR (Lớp 2)**. Sao kê ở Lớp 3 chỉ đo **tính ổn định/biến động dòng tiền**, KHÔNG đo lại khả năng trả nợ.
- Lịch sử trả nợ → chỉ ở **CIC (Lớp 1)**. Tuân thủ thuế/BHXH ở Lớp 3 đo **nghĩa vụ ngoài tín dụng**.
- Quy mô DN (doanh thu) → là **biến phân khúc/chuẩn hóa**, không tính điểm trực tiếp 2 lần.

---

## LỚP 1 — DỮ LIỆU TRUYỀN THỐNG (CIC) — 200 ĐIỂM

| Tên Tiêu chí | Điểm Max | Logic chấm điểm (IF/ELSE) | Nguồn dữ liệu |
|--------------|----------|---------------------------|---------------|
| **Nhóm nợ hiện tại (CIC)** | 80 | IF Nhóm 1 → 80; IF Nhóm 2 → 40; IF Nhóm 3 → 10; IF Nhóm 4-5 → 0 (loại trực tiếp) | CIC — tra cứu có consent DN |
| **Lịch sử nợ xấu 24T** | 40 | IF không có nợ nhóm 2+ nào → 40; IF từng nhóm 2 (1 lần) → 25; IF từng nhóm 3+ → 0 | CIC lịch sử |
| **Tỷ lệ sử dụng hạn mức (Credit Utilization)** | 40 | IF <50% → 40; 50-80% → 25; 80-100% → 10; >100% (vượt hạn) → 0 | CIC dư nợ / hạn mức |
| **Mức độ phân tán quan hệ tín dụng** | 25 | IF 1-3 TCTD → 25; 4-5 TCTD → 15; >5 TCTD (dấu hiệu vay chồng) → 5 | CIC số TCTD đang quan hệ |
| **Tăng trưởng dư nợ bất thường 12T** | 15 | IF tăng <30% → 15; 30-70% → 8; >70% (over-leveraging nhanh) → 0 | CIC chuỗi dư nợ |

*Bổ sung mới so với gốc: Phân tán quan hệ tín dụng + Tăng trưởng dư nợ bất thường (bắt sớm rủi ro vay chồng chéo mà nhóm nợ chưa phản ánh).*

---

## LỚP 2 — DỮ LIỆU BÁN TRUYỀN THỐNG (BCTC) — 300 ĐIỂM

| Tên Tiêu chí | Điểm Max | Logic chấm điểm (IF/ELSE) | Nguồn dữ liệu |
|--------------|----------|---------------------------|---------------|
| **DSCR (Khả năng trả nợ)** | 80 | IF ≥1.5 → 80; 1.25-1.5 → 60; 1.0-1.25 → 35; <1.0 → 0 | BCTC + lịch trả nợ nội bộ |
| **Đòn bẩy (Nợ/VCSH)** | 60 | IF <1.0 → 60; 1.0-2.0 → 40; 2.0-3.0 → 20; >3.0 → 0 | BCTC |
| **EBITDA Margin** | 50 | IF ≥15% → 50; 10-15% → 35; 5-10% → 20; <5% → 5; <0 → 0 | BCTC |
| **Cash Conversion Cycle (CCC)** | 40 | IF <30 ngày → 40; 30-60 → 28; 60-90 → 15; >90 → 5 | BCTC |
| **Thanh khoản (Current Ratio)** | 40 | IF ≥2.0 → 40; 1.5-2.0 → 30; 1.0-1.5 → 18; <1.0 → 5 | BCTC |
| **Tăng trưởng doanh thu 3 năm (CAGR)** | 30 | IF >15% → 30; 5-15% → 20; 0-5% → 10; âm → 0 | BCTC nhiều kỳ |

*Bổ sung mới: Current Ratio (thanh khoản — khác CCC vốn đo hiệu quả vận hành vốn lưu động) + CAGR doanh thu (xu hướng, khác EBITDA Margin vốn đo biên lợi nhuận tĩnh).*

---

## LỚP 3 — PHI TRUYỀN THỐNG & ESG — 500 ĐIỂM

> **Phân bổ nội bộ:** 3A Vận hành 190đ + 3B Tuân thủ 160đ + 3C ESG 120đ + 3D Business Maturity 30đ = **500đ**

### 3A. Hành vi vận hành & Dấu chân số (190 điểm)

| Tên Tiêu chí | Điểm Max | Logic chấm điểm (IF/ELSE) | Nguồn dữ liệu |
|--------------|----------|---------------------------|---------------|
| **E-Invoice Vitality (Tính liên tục HĐĐT)** | 60 | Vitality = Active_months × Slope. IF Active≥11 & Slope=+1 → 60; Active≥9 & Slope≥0 → 40; Active 6-9 → 20; <6 hoặc Slope=-0.3 → 5 | API HĐĐT (consent DN) |
| **Customer Concentration (NLP HĐĐT)** | 50 | Top-5 KH / tổng DT. IF <40% → 50; 40-60% → 30; 60-80% → 15; >80% (phụ thuộc) → 0 | API HĐĐT group by MST bên mua |
| **Anchor-Supplier Network (NLP hợp đồng đầu ra)** | 60 | AI parse hợp đồng, cross-check MST. Score = anchor_count × duration_factor. IF ≥3 anchor & HĐ dài hạn → 60; 1-2 anchor → 35; không xác định → 10 | KH upload hợp đồng + AI parse + dangkykinhdoanh.gov.vn |
| **Bank Cash Flow Stability (độ ổn định, KHÔNG đo khả năng trả nợ)** | 20 | CV = std/mean inflow 12T. IF CV<20% & inflow/outflow≥1 → 20; CV 20-40% → 12; CV>40% hoặc ratio<1 → 2 | Sao kê NH (nội bộ/upload có chữ ký NH) |

### 3B. Tuân thủ hành vi — Behavioral Compliance (160 điểm)

| Tên Tiêu chí | Điểm Max | Logic chấm điểm (IF/ELSE) | Nguồn dữ liệu |
|--------------|----------|---------------------------|---------------|
| **Tax Compliance** | 60 | IF nộp đúng hạn 24T, không cưỡng chế → 60; trễ <30 ngày (≤2 lần) → 35; có nợ thuế đang xử lý → 10; bị cưỡng chế → 0 | API Tổng cục Thuế (consent) + gdt.gov.vn |
| **Social Insurance Compliance (BHXH)** | 50 | IF không nợ BHXH 24T → 50; nợ <3 tháng → 25; nợ 3-6 tháng → 8; nợ >6 tháng → 0 (leading indicator stress) | API BHXH (consent) + danh sách nợ công khai |
| **Utility Compliance (điện/nước/viễn thông)** | 30 | IF auto-debit đều, không từ chối 12T → 30; có 1-2 lần trễ → 18; nhiều lần thiếu số dư → 5 | Sao kê NH (pattern auto-debit) + OCR hóa đơn upload |
| **Account Vitality & Cross-Product** | 20 | Active≥11T & dùng ≥3 sản phẩm NH → 20; ≥2 sản phẩm → 12; chỉ TK cơ bản → 5 | SHB Corporate Online (nội bộ) |

### 3C. ESG Behavioral Proxy (120 điểm)

| Tên Tiêu chí | Điểm Max | Logic chấm điểm (IF/ELSE) | Nguồn dữ liệu |
|--------------|----------|---------------------------|---------------|
| **(E) Environmental Compliance** | 40 | IF không vi phạm môi trường 24T → 40; bị xử phạt hành chính (1 lần) → 15; nằm trong danh sách ô nhiễm nghiêm trọng → 0 | Cổng Bộ TN&MT + QĐ xử phạt công khai |
| **(S) Social/Labor Compliance** | 40 | IF không kiện tụng/đình công 24T → 40; có tranh chấp đã giải quyết → 20; đang kiện tụng/đình công → 0 | API BHXH + Cổng Thanh tra Bộ LĐTBXH |
| **(G) Governance — Tranh chấp pháp lý** | 40 | IF không vụ kiện kinh tế nào → 40; bị động (bị đơn) đã xử → 20; đang tranh chấp tài chính → 5 | API BHXH + Cổng Thanh tra Bộ LĐTBXH |

### 3D. Business Maturity (30 điểm)

> **Nguyên tắc MECE:** Hai biến này đo **tuổi & tính liên tục của pháp nhân** — hoàn toàn tách biệt với tuân thủ (3B) và ESG (3C). Không trùng với CAGR doanh thu ở Lớp 2 (CAGR đo tốc độ tăng trưởng tài chính, không đo tuổi hoạt động thực tế).

| Tên Tiêu chí | Điểm Max | Logic chấm điểm (IF/ELSE) | Nguồn dữ liệu |
|--------------|----------|---------------------------|---------------|
| **Legal Entity Age (Tuổi pháp nhân)** | 20 | IF ≥10 năm → 20; 5-10 năm → 15; 3-5 năm → 10; 1-3 năm → 5; <1 năm → 0 | Cổng DN Quốc gia (dangkykinhdoanh.gov.vn) — công khai, tra tự động bằng MST |
| **Operational Continuity (HKD tiền thân)** | 10 | IF có bằng chứng HKD tiền thân: cùng địa điểm + cùng ngành + cùng chủ → cộng thêm 10 (bonus tối đa); chỉ thỏa 2/3 điều kiện → +5; không có / không xác minh được → 0 | KH upload giấy phép HKD cũ → AI OCR trích xuất địa chỉ, mã ngành, tên chủ → cross-check với ĐKKD hiện tại |

*Lưu ý: Operational Continuity là **bonus additive** — không phạt DN mới thành lập hoàn toàn, chỉ thưởng cho DN có lịch sử hoạt động thực tế trước khi chuyển đổi pháp nhân.*

---

## ĐIỀU CHỈNH THEO DATA RICHNESS (DRI)

Điểm chỉ tin cậy khi đủ dữ liệu. Áp **DRI làm hệ số chiết khấu** thay vì cộng điểm:

```
Điểm_cuối = Điểm_thô × (0.7 + 0.3 × DRI)
DRI = 0.35×Coverage + 0.30×Depth + 0.15×Freshness + 0.20×Cross-Validation
```

DN dữ liệu mỏng (DRI thấp) → bị chiết khấu, tránh "điểm ảo".

---

## BẢNG QUY ĐỔI HẠNG (RATING SCALE)

| Hạng | Điểm | Mức rủi ro | Hành động phê duyệt tự động |
|------|------|-----------|------------------------------|
| **AAA** | 900-1000 | Rất thấp | Auto-approve, lãi suất ưu đãi nhất, hạn mức tối đa |
| **AA** | 820-899 | Thấp | Auto-approve, điều kiện chuẩn |
| **A** | 740-819 | Thấp-TB | Auto-approve, hạn mức điều chỉnh nhẹ |
| **BBB** | 660-739 | Trung bình | Approve có điều kiện (yêu cầu TSĐB bổ sung) |
| **BB** | 580-659 | TB-cao | Review thủ công bắt buộc (chuyên viên thẩm định) |
| **B** | 500-579 | Cao | Review cấp cao + yêu cầu TSĐB mạnh |
| **CCC** | 400-499 | Rất cao | Từ chối tự động trừ ngoại lệ có phê duyệt Hội đồng |
| **D** | <400 | Vỡ nợ/loại | Auto-reject |

**Hard-stop overrides** (bất kể điểm): Nợ CIC nhóm 4-5 → D; Đang cưỡng chế thuế → trần BB; Trong danh sách ô nhiễm nghiêm trọng → trần BB.
