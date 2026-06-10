import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Shell from "../../components/Shell.jsx";
import { Card, CardHead, Pad, Loading, Tier, FlowBadge, Notice } from "../../components/ui.jsx";
import { Icon } from "../../components/icons.jsx";
import { ShapBars } from "../../components/charts.jsx";
import { api } from "../../lib/api.js";
import { vnd, vndFull, DSR_VI, DECISION_VI, dt } from "../../lib/format.js";

function fmtVal(v) {
  if (v == null) return "—";
  if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString("vi-VN") : v.toFixed(3);
  return String(v);
}

export default function CaseAudit() {
  const { cid } = useParams();
  const nav = useNavigate();
  const [a, setA] = useState(undefined);
  useEffect(() => { api.caseAudit(cid).then(setA).catch(() => setA(null)); }, [cid]);

  if (a === undefined) return <Shell title="Kiểm toán hồ sơ" crumb="Cổng Quản trị & Kiểm toán"><Loading /></Shell>;
  if (!a) return <Shell title="Kiểm toán hồ sơ"><Card><Pad>Không tìm thấy hồ sơ.</Pad></Card></Shell>;

  const mo = a.model_output;
  const payloadEntries = Object.entries(a.input_payload);

  return (
    <Shell title={`Kiểm toán · ${a.company_name}`} crumb={`Hồ sơ ${a.customer_id} · MST ${a.mst}`}
      actions={<button className="btn btn--ghost" onClick={() => nav("/admin/cases")}>← Danh sách</button>}>

      {/* Decision provenance banner */}
      <Card className="fade fade-1" flow={mo.flow}>
        <Pad>
          <div className="flex between wrap" style={{ gap: 16 }}>
            <div className="flex" style={{ gap: 18, flexWrap: "wrap" }}>
              <div><div className="muted" style={{ fontSize: 12 }}>Điểm tín dụng</div>
                <div style={{ fontSize: 26, fontWeight: 800 }} className="mono">{mo.credit_score}</div></div>
              <div><div className="muted" style={{ fontSize: 12 }}>Hạng</div><div style={{ marginTop: 4 }}><Tier tier={mo.risk_tier} /></div></div>
              <div><div className="muted" style={{ fontSize: 12 }}>PD</div><div style={{ fontSize: 18, fontWeight: 700 }} className="mono">{(mo.p_bad * 100).toFixed(2)}%</div><div className="muted" style={{ fontSize: 11 }}>{mo.pd_band}</div></div>
              <div><div className="muted" style={{ fontSize: 12 }}>Hạn mức</div><div style={{ fontSize: 16, fontWeight: 700 }}>{vnd(mo.suggested_limit_vnd)}</div></div>
              <div><div className="muted" style={{ fontSize: 12 }}>Quyết định</div><div style={{ marginTop: 4 }}><FlowBadge flow={mo.flow} text={DECISION_VI[mo.decision]} /></div></div>
            </div>
            <div style={{ textAlign: "right", fontSize: 12 }} className="muted">
              <div>Model: <b className="mono">{a.model_version}</b></div>
              <div>Decision: <b className="mono">{a.decision_version}</b></div>
              <div>Truy cập bởi: <b>{a.accessed_by}</b></div>
              <div>{dt(a.timestamp)}</div>
            </div>
          </div>
        </Pad>
      </Card>

      <div className="cols cols-2-1" style={{ marginTop: 18 }}>
        <div className="stack">
          {/* SHAP */}
          <Card className="fade fade-2">
            <CardHead eyebrow="Giải thích mô hình (XAI)" title="Đóng góp SHAP"
              right={<span className="badge badge--navy">TreeExplainer</span>} />
            <Pad>
              <div className="cols cols-2">
                <div>
                  <div className="section-title" style={{ color: "var(--green)" }}>Giảm rủi ro</div>
                  <ShapBars kind="pos" items={a.shap.top_positive.map((x) => ({ label: x.label, shap_value: x.shap_value, value: x.value }))} />
                </div>
                <div>
                  <div className="section-title" style={{ color: "var(--red)" }}>Tăng rủi ro</div>
                  <ShapBars kind="neg" items={a.shap.top_negative.map((x) => ({ label: x.label, shap_value: x.shap_value, value: x.value }))} />
                </div>
              </div>
              <div className="hint" style={{ marginTop: 12 }}>
                Giá trị SHAP biểu thị mức đóng góp của từng đặc trưng vào xác suất vỡ nợ dự báo (đơn vị log-odds).
              </div>
            </Pad>
          </Card>

          {/* Input payload */}
          <Card className="fade fade-3">
            <CardHead eyebrow="Dữ liệu đầu vào" title={`Payload đặc trưng (${payloadEntries.length})`}
              right={<span className="muted" style={{ fontSize: 12 }}>{a.missing_data.length} trường thiếu</span>} />
            <Pad>
              <div style={{ maxHeight: 320, overflowY: "auto" }}>
                <table className="table">
                  <thead><tr><th>Đặc trưng</th><th style={{ textAlign: "right" }}>Giá trị</th></tr></thead>
                  <tbody>
                    {payloadEntries.map(([k, v]) => (
                      <tr key={k}>
                        <td className="mono" style={{ fontSize: 12 }}>{k}</td>
                        <td className="mono tnum" style={{ textAlign: "right" }}>{fmtVal(v)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Pad>
          </Card>
        </div>

        <div className="stack">
          {/* Rule engine result */}
          <Card className="fade fade-2">
            <CardHead eyebrow="Rule Engine" title="Quy tắc đã áp dụng" />
            <Pad>
              <div className="kv"><span className="k">Phiên bản hiệu lực</span><span className="v mono">{a.rule_engine_result.active_version}</span></div>
              <div className="kv"><span className="k">Chặn gian lận (hard stop)</span>
                <span className="v">{a.rule_engine_result.fraud_hard_stop ? "ĐÃ KÍCH HOẠT" : "Không"}</span></div>
              <div className="section-title" style={{ marginTop: 12 }}>Ngưỡng áp dụng</div>
              {Object.entries(a.rule_engine_result.applied_thresholds).map(([k, v]) => (
                <div className="kv" key={k}>
                  <span className="k mono" style={{ fontSize: 12 }}>{k}</span>
                  <span className="v mono">{typeof v === "boolean" ? (v ? "true" : "false") : (k.includes("vnd") ? vnd(v) : String(v))}</span>
                </div>
              ))}
            </Pad>
          </Card>

          {/* Data sources + outcome */}
          <Card className="fade fade-3">
            <CardHead eyebrow="Nguồn & Kết quả" title="Truy xuất & Đối chiếu" />
            <Pad>
              <div className="section-title">Nguồn dữ liệu đã dùng</div>
              <div className="flex wrap" style={{ gap: 6 }}>
                {a.data_sources_used.map((s, i) => <span key={i} className="tag-soft">{s}</span>)}
              </div>
              <div className="kv" style={{ marginTop: 14 }}><span className="k">DSR</span><span className="v">{DSR_VI[mo.dsr_group]} · {(mo.dsr_value * 100).toFixed(0)}%</span></div>
              <div className="kv"><span className="k">Nhãn thực tế (đối chiếu)</span>
                <span className="v">{a.actual_default === 1
                  ? <span className="badge badge--red">Vỡ nợ</span>
                  : <span className="badge badge--green">Không vỡ nợ</span>}</span></div>

              <div className="section-title" style={{ marginTop: 14 }}>Lịch sử ghi đè</div>
              {a.override_history.length
                ? a.override_history.map((o, i) => <div key={i} className="kv"><span className="k">{o.actor}</span><span className="v">{o.note}</span></div>)
                : <div className="muted" style={{ fontSize: 13 }}>Chưa có ghi đè thủ công.</div>}
              <Notice kind="info"><span style={{ fontSize: 12.5 }}>Toàn bộ lượt truy cập hồ sơ này được ghi vào nhật ký kiểm toán.</span></Notice>
            </Pad>
          </Card>
        </div>
      </div>
    </Shell>
  );
}
