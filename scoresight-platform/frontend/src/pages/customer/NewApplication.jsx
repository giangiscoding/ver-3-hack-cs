import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Shell from "../../components/Shell.jsx";
import { Card, CardHead, Pad, Field, Notice } from "../../components/ui.jsx";
import { Icon } from "../../components/icons.jsx";
import { api } from "../../lib/api.js";

// Prefilled with a realistic, strong SME profile (so the demo shows a pre-qualified path)
const PREFILL = {
  company_name: "Công ty TNHH Thương mại An Phát",
  mst: "0312987654",
  industry: "retail",
  business_age_months: 54,
  annual_revenue_vnd: 14_000_000_000,
  requested_limit_vnd: 800_000_000,
  loan_purpose: "Bổ sung vốn lưu động nhập hàng mùa cao điểm",
  contact_person: "Nguyễn Văn An",
  phone: "0903123456",
  email: "ketoan@anphat.com.vn",
  num_employees: 16,
  invoice_revenue_12m: 13_500_000_000,
  invoice_revenue_growth: 0.19,
  supplier_payment_regularity: 0.86,
  payroll_regularity: 0.9,
  momo_net_cashflow_avg: 18_000_000,
  gmv_growth_12m: 0.16,
  vat_filing_on_time_ratio: 0.95,
};

function UploadZone({ label, hint, files, onAdd, onRemove }) {
  const ref = useRef(null);
  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        style={{
          border: "1.5px dashed var(--border, #d0d5dd)",
          borderRadius: 8,
          padding: "20px 16px",
          textAlign: "center",
          cursor: "pointer",
          background: "var(--surface2, #f9fafb)",
        }}
        onClick={() => ref.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && ref.current?.click()}
      >
        <Icon.upload width={22} height={22} style={{ color: "var(--muted)", marginBottom: 6 }} />
        <div style={{ fontSize: 13, color: "var(--muted)" }}>
          <span style={{ color: "var(--accent, #2563eb)", fontWeight: 600 }}>Bấm để tải lên</span>{" "}
          {label}
        </div>
        {hint && (
          <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 3 }}>{hint}</div>
        )}
        <input
          ref={ref}
          type="file"
          multiple
          hidden
          onChange={(e) => {
            onAdd(Array.from(e.target.files));
            e.target.value = "";
          }}
        />
      </div>

      {files.length > 0 && (
        <ul style={{ margin: "8px 0 0", padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 5 }}>
          {files.map((file, i) => (
            <li
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "7px 10px",
                background: "var(--surface2, #f9fafb)",
                border: "1px solid var(--border, #e5e7eb)",
                borderRadius: 6,
                fontSize: 13,
              }}
            >
              <Icon.doc width={15} height={15} style={{ color: "var(--muted)", flex: "none" }} />
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {file.name}
              </span>
              <span style={{ fontSize: 11, color: "var(--muted)", marginRight: 2 }}>
                {(file.size / 1024).toFixed(0)} KB
              </span>
              <button
                type="button"
                onClick={() => onRemove(i)}
                title="Xóa file"
                style={{
                  display: "flex", alignItems: "center", justifyContent: "center",
                  background: "none", border: "none", cursor: "pointer",
                  padding: 3, borderRadius: 4, color: "var(--muted)",
                }}
              >
                <Icon.x width={14} height={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function NewApplication() {
  const nav = useNavigate();
  const [f, setF] = useState(PREFILL);
  const [meta, setMeta] = useState(null);
  const [consentData, setConsentData] = useState(false);
  const [consentTerms, setConsentTerms] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [legalFiles, setLegalFiles] = useState([]);
  const [invoiceFiles, setInvoiceFiles] = useState([]);

  useEffect(() => { api.meta().then(setMeta).catch(() => {}); }, []);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const num = (k) => (e) => setF({ ...f, [k]: e.target.value === "" ? "" : Number(e.target.value) });

  async function submit() {
    setErr("");
    if (!consentData || !consentTerms) { setErr("Vui lòng đồng ý các điều khoản trước khi gửi."); return; }
    setBusy(true);
    try {
      await api.customerSubmit({
        company_name: f.company_name, mst: f.mst, industry: f.industry,
        business_age_months: Number(f.business_age_months) || null,
        annual_revenue_vnd: Number(f.annual_revenue_vnd) || null,
        requested_limit_vnd: Number(f.requested_limit_vnd) || null,
        loan_purpose: f.loan_purpose, contact_person: f.contact_person,
        phone: f.phone, email: f.email,
        consent_data: consentData, consent_terms: consentTerms,
        fields: {
          num_employees: Number(f.num_employees) || null,
          invoice_revenue_12m: Number(f.invoice_revenue_12m) || null,
          invoice_revenue_growth: Number(f.invoice_revenue_growth) || null,
          supplier_payment_regularity: Number(f.supplier_payment_regularity) || null,
          payroll_regularity: Number(f.payroll_regularity) || null,
          momo_net_cashflow_avg: Number(f.momo_net_cashflow_avg) || null,
          gmv_growth_12m: Number(f.gmv_growth_12m) || null,
          vat_filing_on_time_ratio: Number(f.vat_filing_on_time_ratio) || null,
        },
      });
      nav("/customer/status");
    } catch (ex) { setErr(ex.message); } finally { setBusy(false); }
  }

  const totalFiles = legalFiles.length + invoiceFiles.length;

  return (
    <Shell title="Nộp hồ sơ vay" crumb="Cổng Doanh nghiệp · Hồ sơ mới">
      <div className="cols cols-2-1">
        <div className="stack">

          {/* ── Bước 1 ── */}
          <Card className="fade fade-1">
            <CardHead eyebrow="Bước 1" title="Thông tin doanh nghiệp" />
            <Pad>
              <Field label="Tên công ty" required>
                <input className="input" value={f.company_name} onChange={set("company_name")} />
              </Field>
              <div className="grid2">
                <Field label="Mã số thuế / ĐKKD" required>
                  <input className="input mono" value={f.mst} onChange={set("mst")} />
                </Field>
                <Field label="Ngành nghề">
                  <select className="input" value={f.industry} onChange={set("industry")}>
                    {meta?.industries?.map((i) => (
                      <option key={i} value={i}>{meta.industries_vi[i]}</option>
                    ))}
                  </select>
                </Field>
              </div>
              <div className="grid3">
                <Field label="Số năm hoạt động (tháng)">
                  <input className="input" type="number" value={f.business_age_months} onChange={num("business_age_months")} />
                </Field>
                <Field label="Số nhân viên">
                  <input className="input" type="number" value={f.num_employees} onChange={num("num_employees")} />
                </Field>
                <Field label="Doanh thu năm (VND)">
                  <input className="input" type="number" value={f.annual_revenue_vnd} onChange={num("annual_revenue_vnd")} />
                </Field>
              </div>
              <div className="grid2">
                <Field label="Số tiền đề nghị vay (VND)" required>
                  <input className="input" type="number" value={f.requested_limit_vnd} onChange={num("requested_limit_vnd")} />
                </Field>
                <Field label="Mục đích vay">
                  <input className="input" value={f.loan_purpose} onChange={set("loan_purpose")} />
                </Field>
              </div>
              <div className="grid3">
                <Field label="Người liên hệ"><input className="input" value={f.contact_person} onChange={set("contact_person")} /></Field>
                <Field label="Số điện thoại"><input className="input mono" value={f.phone} onChange={set("phone")} /></Field>
                <Field label="Email"><input className="input" value={f.email} onChange={set("email")} /></Field>
              </div>
            </Pad>
          </Card>

          {/* ── Bước 2 ── */}
          <Card className="fade fade-2">
            <CardHead eyebrow="Bước 2" title="Dữ liệu phi truyền thống (tùy chọn)"
              right={<span className="badge badge--navy">Càng nhiều dữ liệu, đánh giá càng chính xác</span>} />
            <Pad>
              <Notice kind="info">
                Bạn có thể liên kết hoặc nhập dữ liệu hóa đơn điện tử, ví/POS, sàn TMĐT.
                Dữ liệu giúp đánh giá năng lực trả nợ thay cho lịch sử tín dụng truyền thống.
              </Notice>
              <div className="grid2" style={{ marginTop: 14 }}>
                <Field label="Doanh thu hóa đơn 12 tháng (VND)">
                  <input className="input" type="number" value={f.invoice_revenue_12m} onChange={num("invoice_revenue_12m")} />
                </Field>
                <Field label="Tăng trưởng doanh thu hóa đơn (0–1)">
                  <input className="input" type="number" step="0.01" value={f.invoice_revenue_growth} onChange={num("invoice_revenue_growth")} />
                </Field>
                <Field label="Dòng tiền ròng ví/tháng (VND)">
                  <input className="input" type="number" value={f.momo_net_cashflow_avg} onChange={num("momo_net_cashflow_avg")} />
                </Field>
                <Field label="Độ đều thanh toán NCC (0–1)">
                  <input className="input" type="number" step="0.01" value={f.supplier_payment_regularity} onChange={num("supplier_payment_regularity")} />
                </Field>
                <Field label="Độ đều trả lương (0–1)">
                  <input className="input" type="number" step="0.01" value={f.payroll_regularity} onChange={num("payroll_regularity")} />
                </Field>
                <Field label="Tỷ lệ nộp VAT đúng hạn (0–1)">
                  <input className="input" type="number" step="0.01" value={f.vat_filing_on_time_ratio} onChange={num("vat_filing_on_time_ratio")} />
                </Field>
              </div>
            </Pad>
          </Card>

          {/* ── Bước 3 ── */}
          <Card className="fade fade-3">
            <CardHead
              eyebrow="Bước 3"
              title="Tải lên sao kê"
              right={
                totalFiles > 0
                  ? <span className="badge badge--navy">{totalFiles} file đã tải lên</span>
                  : <span className="badge" style={{ background: "var(--surface2)", color: "var(--muted)" }}>Tùy chọn</span>
              }
            />
            <Pad>
              <Notice kind="info">
                Tải lên tài liệu bổ sung giúp tăng độ chính xác đánh giá. Tất cả file được mã hóa và bảo mật.
              </Notice>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginTop: 16 }}>

                {/* Hồ sơ pháp lý */}
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 10 }}>
                    <Icon.folder width={16} height={16} style={{ color: "var(--muted)" }} />
                    <span style={{ fontSize: 13, fontWeight: 600 }}>Hồ sơ pháp lý</span>
                    {legalFiles.length > 0 && (
                      <span className="badge badge--navy" style={{ fontSize: 11 }}>{legalFiles.length}</span>
                    )}
                  </div>
                  <UploadZone
                    label="hồ sơ pháp lý"
                    hint="Giấy phép kinh doanh, ĐKKD, xác nhận tài sản đảm bảo …"
                    files={legalFiles}
                    onAdd={(newFiles) => setLegalFiles((prev) => [...prev, ...newFiles])}
                    onRemove={(i) => setLegalFiles((prev) => prev.filter((_, idx) => idx !== i))}
                  />
                </div>

                {/* Hóa đơn */}
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 10 }}>
                    <Icon.doc width={16} height={16} style={{ color: "var(--muted)" }} />
                    <span style={{ fontSize: 13, fontWeight: 600 }}>Hóa đơn</span>
                    {invoiceFiles.length > 0 && (
                      <span className="badge badge--navy" style={{ fontSize: 11 }}>{invoiceFiles.length}</span>
                    )}
                  </div>
                  <UploadZone
                    label="hóa đơn"
                    hint="Hóa đơn GTGT, sao kê ngân hàng, báo cáo tài chính…"
                    files={invoiceFiles}
                    onAdd={(newFiles) => setInvoiceFiles((prev) => [...prev, ...newFiles])}
                    onRemove={(i) => setInvoiceFiles((prev) => prev.filter((_, idx) => idx !== i))}
                  />
                </div>

              </div>
            </Pad>
          </Card>

        </div>

        {/* ── Bước 4 (sidebar) ── */}
        <div className="stack">
          <Card className="fade fade-2" style={{ position: "sticky", top: 92 }}>
            <CardHead eyebrow="Bước 4" title="Đồng ý & Gửi hồ sơ" />
            <Pad>
              <label className="flex" style={{ alignItems: "flex-start", gap: 10, marginBottom: 12, cursor: "pointer" }}>
                <input type="checkbox" checked={consentData} onChange={(e) => setConsentData(e.target.checked)} style={{ marginTop: 3 }} />
                <span style={{ fontSize: 13 }}>Tôi cho phép ngân hàng phân tích dữ liệu đã cung cấp phục vụ đánh giá tín dụng.</span>
              </label>
              <label className="flex" style={{ alignItems: "flex-start", gap: 10, marginBottom: 16, cursor: "pointer" }}>
                <input type="checkbox" checked={consentTerms} onChange={(e) => setConsentTerms(e.target.checked)} style={{ marginTop: 3 }} />
                <span style={{ fontSize: 13 }}>Tôi đồng ý với <a className="muted" style={{ textDecoration: "underline" }} href="#">Điều khoản dịch vụ</a> và <a className="muted" style={{ textDecoration: "underline" }} href="#">Chính sách bảo mật</a>.</span>
              </label>

              {err && <div className="notice notice--warn" style={{ marginBottom: 12 }}>
                <Icon.alert width={16} height={16} style={{ flex: "none" }} /> {err}</div>}

              <button className="btn btn--primary btn--block btn--lg" disabled={busy} onClick={submit}>
                {busy ? "Đang gửi & đánh giá…" : "Gửi hồ sơ"} <Icon.arrow width={17} height={17} />
              </button>
              <div className="hint" style={{ textAlign: "center", marginTop: 10 }}>
                Kết quả đánh giá thường có ngay sau khi gửi.
              </div>
            </Pad>
          </Card>
        </div>

      </div>
    </Shell>
  );
}
