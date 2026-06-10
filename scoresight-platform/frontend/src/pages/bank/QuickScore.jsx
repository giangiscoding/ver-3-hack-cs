import { useEffect, useState } from "react";
import Shell from "../../components/Shell.jsx";
import { Card, CardHead, Pad, Field, Tier, FlowBadge, Notice } from "../../components/ui.jsx";
import { Icon } from "../../components/icons.jsx";
import { ScoreGauge } from "../../components/charts.jsx";
import { api } from "../../lib/api.js";
import { vnd, DSR_VI } from "../../lib/format.js";

const START = {
  mst: "0301456789", industry: "services", region: "HCMC",
  business_age_months: 30, num_employees: 9, annual_revenue_vnd: 4_500_000_000,
  requested_limit_vnd: 300_000_000, invoice_revenue_12m: 4_200_000_000,
  supplier_payment_regularity: 0.72,
};

export default function QuickScore() {
  const [f, setF] = useState(START);
  const [meta, setMeta] = useState(null);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => { api.meta().then(setMeta).catch(() => {}); }, []);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const num = (k) => (e) => setF({ ...f, [k]: e.target.value === "" ? "" : Number(e.target.value) });

  async function run() {
    setErr(""); setBusy(true);
    try {
      const r = await api.quickScore({
        mst: f.mst, industry: f.industry, region: f.region,
        business_age_months: Number(f.business_age_months) || null,
        num_employees: Number(f.num_employees) || null,
        annual_revenue_vnd: Number(f.annual_revenue_vnd) || null,
        requested_limit_vnd: Number(f.requested_limit_vnd) || null,
        invoice_revenue_12m: Number(f.invoice_revenue_12m) || null,
        supplier_payment_regularity: Number(f.supplier_payment_regularity) || null,
      });
      setRes(r);
    } catch (ex) { setErr(ex.message); } finally { setBusy(false); }
  }

  return (
    <Shell title="Chấm điểm nhanh" crumb="Cổng Cán bộ Ngân hàng · Pre-screen">
      <div className="cols cols-2">
        <Card className="fade fade-1">
          <CardHead eyebrow="Đầu vào tối thiểu" title="Thông tin sơ bộ doanh nghiệp" />
          <Pad>
            <Field label="Mã số thuế / ĐKKD"><input className="input mono" value={f.mst} onChange={set("mst")} /></Field>
            <div className="grid2">
              <Field label="Ngành nghề">
                <select className="input" value={f.industry} onChange={set("industry")}>
                  {meta?.industries?.map((i) => <option key={i} value={i}>{meta.industries_vi[i]}</option>)}
                </select>
              </Field>
              <Field label="Khu vực">
                <select className="input" value={f.region} onChange={set("region")}>
                  {meta?.regions?.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </Field>
            </div>
            <div className="grid3">
              <Field label="Hoạt động (tháng)"><input className="input" type="number" value={f.business_age_months} onChange={num("business_age_months")} /></Field>
              <Field label="Số nhân viên"><input className="input" type="number" value={f.num_employees} onChange={num("num_employees")} /></Field>
              <Field label="Doanh thu năm"><input className="input" type="number" value={f.annual_revenue_vnd} onChange={num("annual_revenue_vnd")} /></Field>
            </div>
            <div className="grid2">
              <Field label="Doanh thu hóa đơn 12T"><input className="input" type="number" value={f.invoice_revenue_12m} onChange={num("invoice_revenue_12m")} /></Field>
              <Field label="Độ đều TT nhà cung cấp (0–1)"><input className="input" type="number" step="0.01" value={f.supplier_payment_regularity} onChange={num("supplier_payment_regularity")} /></Field>
            </div>
            <Field label="Số tiền đề nghị vay"><input className="input" type="number" value={f.requested_limit_vnd} onChange={num("requested_limit_vnd")} /></Field>

            {err && <div className="notice notice--warn" style={{ marginBottom: 12 }}><Icon.alert width={16} height={16} style={{ flex: "none" }} /> {err}</div>}
            <button className="btn btn--primary btn--block btn--lg" disabled={busy} onClick={run}>
              {busy ? "Đang chấm điểm…" : "Chấm điểm"} <Icon.bolt width={17} height={17} />
            </button>
          </Pad>
        </Card>

        <Card className="fade fade-2" flow={res?.flow}>
          <CardHead eyebrow="Kết quả mô hình" title="Đánh giá sơ bộ" right={res && <FlowBadge flow={res.flow} />} />
          <Pad>
            {!res ? (
              <div className="loading" style={{ padding: 50 }}>
                <div className="muted" style={{ textAlign: "center" }}>
                  <Icon.bolt width={28} height={28} style={{ color: "var(--ink-3)", marginBottom: 8 }} /><br />
                  Nhập thông tin và nhấn “Chấm điểm” để xem kết quả tức thì.
                </div>
              </div>
            ) : (
              <>
                <div className="flex between wrap">
                  <div style={{ textAlign: "center", flex: "none" }}>
                    <ScoreGauge score={res.credit_score} />
                  </div>
                  <div style={{ flex: 1, minWidth: 180 }}>
                    <div className="kv"><span className="k">Hạng rủi ro</span><span className="v"><Tier tier={res.risk_tier} /></span></div>
                    <div className="kv"><span className="k">Xác suất vỡ nợ (PD)</span><span className="v">{res.pd_band}</span></div>
                    <div className="kv"><span className="k">Độ dày dữ liệu</span><span className="v">{DSR_VI[res.dsr_group]}</span></div>
                    <div className="kv"><span className="k">Hạn mức đề xuất</span><span className="v">{vnd(res.suggested_limit_vnd)}</span></div>
                  </div>
                </div>
                <Notice kind={res.flow === "green" ? "ok" : res.flow === "yellow" ? "warn" : "warn"}>
                  <b>Khuyến nghị:</b> {res.recommendation}
                </Notice>
                {res.warnings?.length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    {res.warnings.map((w, i) => <div key={i} className="notice notice--warn" style={{ marginBottom: 6 }}>
                      <Icon.alert width={15} height={15} style={{ flex: "none" }} /> {w}</div>)}
                  </div>
                )}
                <div className="hint" style={{ marginTop: 12 }}>
                  Chấm điểm nhanh dùng cho pre-screen. Hồ sơ chính thức cần đầy đủ dữ liệu để có đánh giá đầy đủ.
                </div>
              </>
            )}
          </Pad>
        </Card>
      </div>
    </Shell>
  );
}
