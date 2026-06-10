import { useEffect, useState } from "react";
import Shell from "../../components/Shell.jsx";
import { Card, CardHead, Pad, Field, Loading, Notice } from "../../components/ui.jsx";
import { Icon } from "../../components/icons.jsx";
import { api } from "../../lib/api.js";
import { vnd, dt } from "../../lib/format.js";

const LABELS = {
  green_min_score: "Điểm tối thiểu — Luồng Xanh",
  yellow_min_score: "Điểm tối thiểu — Luồng Vàng",
  red_max_score: "Điểm tối đa — Luồng Đỏ",
  max_dsr_for_green: "DSR tối đa cho Luồng Xanh",
  fraud_hard_stop: "Chặn cứng khi có cờ gian lận",
  missing_key_doc_action: "Xử lý khi thiếu tài liệu then chốt",
  max_suggested_limit_vnd: "Hạn mức đề xuất tối đa (VND)",
};

export default function RuleEngine() {
  const [data, setData] = useState(undefined);
  const [draft, setDraft] = useState(null);
  const [approver, setApprover] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  function load() { api.rules().then((d) => { setData(d); setDraft({ ...d.active.rules }); }).catch(() => setData(null)); }
  useEffect(() => { load(); }, []);

  if (data === undefined) return <Shell title="Cấu hình Rule Engine" crumb="Cổng Quản trị & Kiểm toán"><Loading /></Shell>;

  const setR = (k, v) => setDraft({ ...draft, [k]: v });

  async function propose() {
    setErr(""); setMsg("");
    try { await api.proposeRules(draft); setMsg("Đã gửi đề xuất. Cần một người khác phê duyệt (maker-checker)."); load(); }
    catch (ex) { setErr(ex.message); }
  }
  async function approve() {
    setErr(""); setMsg("");
    try { const r = await api.approveRules(approver || undefined); setMsg(`Đã phê duyệt & triển khai phiên bản ${r.version}.`); setApprover(""); load(); }
    catch (ex) { setErr(ex.message); }
  }

  const pending = data.pending;

  return (
    <Shell title="Cấu hình Rule Engine" crumb="Cổng Quản trị & Kiểm toán"
      actions={<span className="badge badge--navy">Hiệu lực: {data.active.version}</span>}>

      {msg && <div style={{ marginBottom: 14 }}><Notice kind="ok">{msg}</Notice></div>}
      {err && <div style={{ marginBottom: 14 }}><Notice kind="warn">{err}</Notice></div>}

      <div className="cols cols-2-1">
        <Card className="fade fade-1">
          <CardHead eyebrow="Maker" title="Soạn thảo quy tắc quyết định"
            right={<span className="muted" style={{ fontSize: 12 }}>Người đề xuất ≠ người duyệt</span>} />
          <Pad>
            <div className="grid2">
              <Field label={LABELS.green_min_score}>
                <input className="input mono" type="number" value={draft.green_min_score} onChange={(e) => setR("green_min_score", Number(e.target.value))} />
              </Field>
              <Field label={LABELS.yellow_min_score}>
                <input className="input mono" type="number" value={draft.yellow_min_score} onChange={(e) => setR("yellow_min_score", Number(e.target.value))} />
              </Field>
              <Field label={LABELS.max_dsr_for_green}>
                <input className="input mono" type="number" step="0.01" value={draft.max_dsr_for_green} onChange={(e) => setR("max_dsr_for_green", Number(e.target.value))} />
              </Field>
              <Field label={LABELS.max_suggested_limit_vnd} hint={vnd(draft.max_suggested_limit_vnd)}>
                <input className="input mono" type="number" value={draft.max_suggested_limit_vnd} onChange={(e) => setR("max_suggested_limit_vnd", Number(e.target.value))} />
              </Field>
              <Field label={LABELS.missing_key_doc_action}>
                <select className="input" value={draft.missing_key_doc_action} onChange={(e) => setR("missing_key_doc_action", e.target.value)}>
                  <option value="manual_review">Chuyển xem xét thủ công</option>
                  <option value="decline">Từ chối</option>
                  <option value="request_docs">Yêu cầu bổ sung</option>
                </select>
              </Field>
              <Field label={LABELS.fraud_hard_stop}>
                <select className="input" value={String(draft.fraud_hard_stop)} onChange={(e) => setR("fraud_hard_stop", e.target.value === "true")}>
                  <option value="true">Bật (khuyến nghị)</option>
                  <option value="false">Tắt</option>
                </select>
              </Field>
            </div>
            <button className="btn btn--primary" onClick={propose}>
              <Icon.sliders width={16} height={16} /> Gửi đề xuất thay đổi
            </button>
            <div className="hint" style={{ marginTop: 8 }}>
              Thay đổi không có hiệu lực ngay — phải qua bước phê duyệt độc lập.
            </div>
          </Pad>
        </Card>

        <div className="stack">
          <Card className="fade fade-2" flow={pending ? "yellow" : undefined}>
            <CardHead eyebrow="Checker" title="Phê duyệt thay đổi" />
            <Pad>
              {pending ? (
                <>
                  <Notice kind="warn">
                    Phiên bản <b>{pending.version}</b> đang chờ duyệt — đề xuất bởi <b>{pending.proposed_by}</b>.
                  </Notice>
                  <Field label="Người phê duyệt (kiểm soát viên)" hint="Phải khác người đề xuất">
                    <input className="input" value={approver} onChange={(e) => setApprover(e.target.value)} placeholder="VD: Kiểm soát viên cấp 2" />
                  </Field>
                  <button className="btn btn--navy btn--block" onClick={approve}>
                    <Icon.check width={16} height={16} /> Phê duyệt & triển khai
                  </button>
                </>
              ) : (
                <div className="muted" style={{ fontSize: 13.5 }}>Không có thay đổi nào đang chờ duyệt.</div>
              )}
            </Pad>
          </Card>

          <Card className="fade fade-3">
            <CardHead eyebrow="Lịch sử" title="Phiên bản quy tắc" />
            <Pad>
              {data.history.slice().reverse().map((v) => (
                <div className="kv" key={v.version}>
                  <span className="k mono">{v.version}</span>
                  <span className="v" style={{ fontWeight: 500, fontSize: 12.5 }}>
                    {v.status === "active" ? <span className="badge badge--green">Hiệu lực</span>
                      : v.status === "pending_approval" ? <span className="badge badge--amber">Chờ duyệt</span>
                        : <span className="tag-soft">Lưu trữ</span>}
                    <div className="muted" style={{ fontSize: 11, marginTop: 3 }}>{v.proposed_by} → {v.approved_by || "—"}</div>
                  </span>
                </div>
              ))}
            </Pad>
          </Card>
        </div>
      </div>
    </Shell>
  );
}
