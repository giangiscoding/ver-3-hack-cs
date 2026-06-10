import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Shell from "../../components/Shell.jsx";
import { Card, Pad, Loading, FlowBadge, Tier } from "../../components/ui.jsx";
import { Icon } from "../../components/icons.jsx";
import { api } from "../../lib/api.js";
import { vnd, SIZE_VI, DSR_VI } from "../../lib/format.js";

const FILTERS = [
  { k: "", label: "Tất cả" },
  { k: "green", label: "Luồng Xanh" },
  { k: "yellow", label: "Luồng Vàng" },
  { k: "red", label: "Luồng Đỏ" },
];

export default function BankCases() {
  const nav = useNavigate();
  const [data, setData] = useState(undefined);
  const [q, setQ] = useState("");
  const [flow, setFlow] = useState("");

  function load() { setData(undefined); api.bankCases(q, flow).then(setData).catch(() => setData({ cases: [], count: 0 })); }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [flow]);

  return (
    <Shell title="Danh sách hồ sơ" crumb="Cổng Cán bộ Ngân hàng"
      actions={
        <button className="btn btn--primary" onClick={() => nav("/bank/quick-score")}>
          <Icon.bolt width={17} height={17} /> Chấm điểm nhanh
        </button>}>
      <Card className="fade fade-1">
        <Pad>
          <div className="flex between wrap" style={{ gap: 12 }}>
            <div className="flex" style={{ flex: 1, minWidth: 240, maxWidth: 420 }}>
              <div style={{ position: "relative", flex: 1 }}>
                <Icon.search width={16} height={16} style={{ position: "absolute", left: 12, top: 12, color: "var(--ink-3)" }} />
                <input className="input" style={{ paddingLeft: 36 }} placeholder="Tìm theo tên công ty, MST, mã KH…"
                  value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} />
              </div>
              <button className="btn btn--ghost" onClick={load}>Tìm</button>
            </div>
            <div className="flex wrap" style={{ gap: 6 }}>
              {FILTERS.map((f) => (
                <button key={f.k} className={`btn ${flow === f.k ? "btn--navy" : "btn--ghost"}`}
                  style={{ padding: "8px 13px" }} onClick={() => setFlow(f.k)}>{f.label}</button>
              ))}
            </div>
          </div>
        </Pad>
      </Card>

      <Card className="fade fade-2" style={{ marginTop: 18, overflow: "hidden" }}>
        {data === undefined ? <Loading /> : (
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Doanh nghiệp</th><th>MST</th><th>Quy mô</th><th>Điểm</th>
                  <th>Hạng</th><th>Dữ liệu</th><th>Đề nghị</th><th>Đề xuất cấp</th><th>Luồng</th><th></th>
                </tr>
              </thead>
              <tbody>
                {data.cases.map((c) => (
                  <tr key={c.customer_id} className="row-click" onClick={() => nav(`/bank/cases/${c.customer_id}`)}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{c.company_name}</div>
                      <div className="muted" style={{ fontSize: 12 }}>{c.industry_vi} · {c.region_vi}</div>
                    </td>
                    <td className="mono" style={{ fontSize: 12.5 }}>{c.mst}</td>
                    <td>{SIZE_VI[c.enterprise_size]}</td>
                    <td className="mono" style={{ fontWeight: 700 }}>{c.credit_score}</td>
                    <td><Tier tier={c.risk_tier} /></td>
                    <td><span className="tag-soft">{DSR_VI[c.dsr_group]}</span></td>
                    <td className="tnum muted">{vnd(c.requested_limit_vnd)}</td>
                    <td className="tnum" style={{ fontWeight: 600 }}>{vnd(c.credit_limit_vnd)}</td>
                    <td><FlowBadge flow={c.flow} /></td>
                    <td><Icon.arrow width={16} height={16} style={{ color: "var(--ink-3)" }} /></td>
                  </tr>
                ))}
                {data.cases.length === 0 && (
                  <tr><td colSpan={10} className="muted" style={{ textAlign: "center", padding: 30 }}>Không có hồ sơ phù hợp.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {data && <div className="muted" style={{ fontSize: 12.5, marginTop: 10 }}>Hiển thị {data.cases.length} hồ sơ.</div>}
    </Shell>
  );
}
