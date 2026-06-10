import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Shell from "../../components/Shell.jsx";
import { Card, CardHead, Pad, Loading, FlowBadge, Tier, Notice, Lock, Meter } from "../../components/ui.jsx";
import { Icon } from "../../components/icons.jsx";
import { ScoreGauge } from "../../components/charts.jsx";
import { api } from "../../lib/api.js";
import { vnd, vndFull, DSR_VI, SIZE_VI, dt } from "../../lib/format.js";

export default function CaseDetail() {
  const { cid } = useParams();
  const nav = useNavigate();
  const [d, setD] = useState(undefined);

  useEffect(() => { api.bankCase(cid).then(setD).catch(() => setD(null)); }, [cid]);

  if (d === undefined) return <Shell title="Chi tiết hồ sơ" crumb="Cổng Cán bộ Ngân hàng"><Loading /></Shell>;
  if (!d) return <Shell title="Chi tiết hồ sơ"><Card><Pad>Không tìm thấy hồ sơ.</Pad></Card></Shell>;

  const s = d.summary, m = d.model_result, op = d.ops_panel;

  return (
    <Shell title={s.company_name} crumb={`Hồ sơ ${s.customer_id} · ${s.industry_vi}`}
      actions={<button className="btn btn--ghost" onClick={() => nav("/bank/cases")}>← Danh sách</button>}>

      {d.warnings?.map((w, i) => (
        <div key={i} style={{ marginBottom: 14 }}><Notice kind="warn">{w}</Notice></div>
      ))}

      <div className="cols cols-2-1">
        {/* LEFT */}
        <div className="stack">
          {/* Model result */}
          <Card className="fade fade-1" flow={d.flow.color}>
            <CardHead eyebrow="Kết quả mô hình" title="Đánh giá tín dụng"
              right={<FlowBadge flow={d.flow.color} />} />
            <Pad>
              <div className="flex between wrap" style={{ gap: 16 }}>
                <div style={{ textAlign: "center", flex: "none" }}>
                  <ScoreGauge score={m.credit_score} />
                  <div className="flex" style={{ justifyContent: "center", gap: 8 }}>
                    <Tier tier={m.risk_tier} /><span className="muted" style={{ fontSize: 12.5 }}>Hạng rủi ro</span>
                  </div>
                </div>
                <div style={{ flex: 1, minWidth: 220 }}>
                  <div className="kv"><span className="k">Xác suất vỡ nợ (PD)</span><span className="v">{m.pd_band}</span></div>
                  <div className="kv"><span className="k">Độ dày dữ liệu (DSR)</span><span className="v">{DSR_VI[m.dsr_group]} · {(m.dsr_value * 100).toFixed(0)}%</span></div>
                  <div className="kv"><span className="k">Sức mạnh dòng tiền</span><span className="v">{m.cashflow_strength}</span></div>
                  <div className="kv"><span className="k">Ổn định doanh thu</span><span className="v">{m.revenue_stability}</span></div>
                  <div className="kv"><span className="k">Quy mô</span><span className="v">{SIZE_VI[s.enterprise_size]}</span></div>
                </div>
              </div>

              <div style={{ marginTop: 12 }}>
                <div className="flex between" style={{ fontSize: 12.5, marginBottom: 5 }}>
                  <span className="muted">Độ phủ dữ liệu thay thế</span><b>{m.data_coverage_pct}%</b>
                </div>
                <Meter value={m.data_coverage_pct} />
              </div>

              <div className="cols cols-2" style={{ marginTop: 16 }}>
                <div style={{ background: "var(--surface-2)", borderRadius: 12, padding: "14px 16px" }}>
                  <div className="muted" style={{ fontSize: 12 }}>Đề nghị của KH</div>
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{vnd(s.requested_limit_vnd)}</div>
                </div>
                <div style={{ background: "var(--shb-orange-soft)", borderRadius: 12, padding: "14px 16px", border: "1px solid var(--shb-orange-line)" }}>
                  <div style={{ fontSize: 12, color: "var(--shb-orange-2)" }}>Hạn mức đề xuất (mô hình)</div>
                  <div style={{ fontSize: 18, fontWeight: 800, color: "var(--shb-orange-2)" }}>{vnd(m.suggested_limit_vnd)}</div>
                </div>
              </div>
            </Pad>
          </Card>

          {/* Criteria-level explanation */}
          <Card className="fade fade-2">
            <CardHead eyebrow="Giải trình theo tiêu chí" title="Vì sao có kết quả này"
              right={<Lock>Giá trị SHAP & trọng số: chỉ Quản trị/Kiểm toán</Lock>} />
            <Pad>
              <div className="cols cols-2">
                <div>
                  <div className="section-title" style={{ color: "var(--green)" }}>Yếu tố tích cực</div>
                  {d.criteria.positive.length ? d.criteria.positive.map((p, i) => (
                    <div className="factor pos" key={i}>
                      <span className="ic"><Icon.check width={13} height={13} /></span>
                      <div>{p.label}<br /><small>Nguồn: {p.source}</small></div>
                    </div>
                  )) : <div className="muted" style={{ fontSize: 13 }}>—</div>}
                </div>
                <div>
                  <div className="section-title" style={{ color: "var(--red)" }}>Yếu tố rủi ro</div>
                  {d.criteria.risk.length ? d.criteria.risk.map((p, i) => (
                    <div className="factor neg" key={i}>
                      <span className="ic"><Icon.alert width={13} height={13} /></span>
                      <div>{p.label}<br /><small>Nguồn: {p.source}</small></div>
                    </div>
                  )) : <div className="muted" style={{ fontSize: 13 }}>—</div>}
                </div>
              </div>
            </Pad>
          </Card>
        </div>

        {/* RIGHT */}
        <div className="stack">
          {/* Flow decision */}
          <Card className="fade fade-2" flow={d.flow.color}>
            <CardHead eyebrow="Luồng xử lý" title="Quyết định đề xuất" />
            <Pad>
              <div style={{ fontWeight: 800, fontSize: 17, letterSpacing: "-0.01em" }}>{d.flow.title}</div>
              <p className="muted" style={{ fontSize: 13.5, marginTop: 6 }}>{d.flow.action}</p>
              <div className="flex" style={{ gap: 8, marginTop: 6 }}>
                <span className="badge badge--navy">Khuyến nghị: {d.flow.recommendation}</span>
              </div>
              <div className="flex wrap" style={{ gap: 8, marginTop: 16 }}>
                {d.flow.color === "green" && <button className="btn btn--primary"><Icon.check width={16} height={16} /> Chuyển LOS/CMS</button>}
                {d.flow.color !== "green" && <button className="btn btn--navy"><Icon.doc width={16} height={16} /> Yêu cầu bổ sung</button>}
                <button className="btn btn--ghost"><Icon.flag width={16} height={16} /> Ghi chú</button>
              </div>
            </Pad>
          </Card>

          {/* Operational benefit panel */}
          <Card className="fade fade-3">
            <CardHead eyebrow="Lợi ích vận hành" title="Tác động & Bước tiếp theo" />
            <Pad>
              <div style={{ background: "var(--green-soft)", borderRadius: 12, padding: "14px 16px", marginBottom: 14 }}>
                <div className="flex between">
                  <div>
                    <div style={{ fontSize: 12, color: "#146a47" }}>Rút ngắn thời gian xử lý (ước tính)</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "var(--green)" }}>−{op.tat_saving_pct}%</div>
                  </div>
                  <Icon.bolt width={30} height={30} style={{ color: "var(--green)" }} />
                </div>
              </div>

              <div className="kv"><span className="k">Cần xem xét thủ công</span><span className="v">{op.manual_review_required ? "Có" : "Không"}</span></div>
              <div className="kv"><span className="k">Sẵn sàng chuyển LOS/CMS</span><span className="v">{op.los_ready ? "Có" : "Chưa"}</span></div>
              <div className="kv"><span className="k">Cần chuyển thẩm định tăng cường</span><span className="v">{op.escalate ? "Có" : "Không"}</span></div>

              <div className="section-title" style={{ marginTop: 14 }}>Tài liệu còn thiếu</div>
              {op.missing_docs.length ? op.missing_docs.map((x, i) => (
                <div key={i} className="flex" style={{ fontSize: 13, padding: "5px 0" }}>
                  <Icon.doc width={15} height={15} style={{ color: "var(--amber)" }} /> {x}
                </div>
              )) : <div className="muted" style={{ fontSize: 13 }}>Đầy đủ hồ sơ cơ bản.</div>}

              <Notice kind="info"><b>Hành động tiếp theo:</b> {op.next_action}</Notice>
              <div className="hint" style={{ marginTop: 10 }}>Cập nhật: {dt(s.timestamp)}</div>
            </Pad>
          </Card>
        </div>
      </div>
    </Shell>
  );
}
