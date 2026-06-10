import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Shell from "../../components/Shell.jsx";
import { Card, Pad, Loading, FlowBadge, Tier } from "../../components/ui.jsx";
import { Icon } from "../../components/icons.jsx";
import { api } from "../../lib/api.js";
import { vnd, DSR_VI, DECISION_VI } from "../../lib/format.js";

export default function AdminCases() {
  const nav = useNavigate();
  const [data, setData] = useState(undefined);
  const [q, setQ] = useState("");

  function load() { setData(undefined); api.adminCases(q).then(setData).catch(() => setData({ cases: [] })); }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  return (
    <Shell title="Kiểm toán hồ sơ" crumb="Cổng Quản trị & Kiểm toán">
      <Card className="fade fade-1"><Pad>
        <div className="flex" style={{ maxWidth: 460 }}>
          <div style={{ position: "relative", flex: 1 }}>
            <Icon.search width={16} height={16} style={{ position: "absolute", left: 12, top: 12, color: "var(--ink-3)" }} />
            <input className="input" style={{ paddingLeft: 36 }} placeholder="Tìm theo tên, MST, mã hồ sơ…"
              value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} />
          </div>
          <button className="btn btn--ghost" onClick={load}>Tìm</button>
        </div>
      </Pad></Card>

      <Card className="fade fade-2" style={{ marginTop: 18, overflow: "hidden" }}>
        {data === undefined ? <Loading /> : (
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead><tr>
                <th>Mã hồ sơ</th><th>Doanh nghiệp</th><th>Điểm</th><th>Hạng</th>
                <th>Dữ liệu</th><th>Quyết định</th><th>Hạn mức</th><th>Luồng</th><th></th>
              </tr></thead>
              <tbody>
                {data.cases.map((c) => (
                  <tr key={c.customer_id} className="row-click" onClick={() => nav(`/admin/cases/${c.customer_id}`)}>
                    <td className="mono" style={{ fontSize: 12.5, fontWeight: 600 }}>{c.customer_id}</td>
                    <td>{c.company_name}<div className="muted" style={{ fontSize: 12 }}>{c.mst}</div></td>
                    <td className="mono" style={{ fontWeight: 700 }}>{c.credit_score}</td>
                    <td><Tier tier={c.risk_tier} /></td>
                    <td><span className="tag-soft">{DSR_VI[c.dsr_group]}</span></td>
                    <td>{DECISION_VI[c.decision]}</td>
                    <td className="tnum">{vnd(c.credit_limit_vnd)}</td>
                    <td><FlowBadge flow={c.flow} /></td>
                    <td><Icon.shield width={16} height={16} style={{ color: "var(--ink-3)" }} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </Shell>
  );
}
