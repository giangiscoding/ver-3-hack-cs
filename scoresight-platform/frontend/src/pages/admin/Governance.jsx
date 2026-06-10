import { useEffect, useState } from "react";
import Shell from "../../components/Shell.jsx";
import { Card, CardHead, Pad, Stat, Loading } from "../../components/ui.jsx";
import { Icon } from "../../components/icons.jsx";
import { api } from "../../lib/api.js";
import { dt } from "../../lib/format.js";

function cell(v) {
  if (v === "Có" || v.startsWith("Có")) return <span className="badge badge--green">{v}</span>;
  if (v === "Không") return <span className="tag-soft" style={{ color: "var(--ink-3)" }}>{v}</span>;
  return <span className="badge badge--amber">{v}</span>;
}

export default function Governance() {
  const [ac, setAc] = useState(undefined);
  const [intg, setIntg] = useState(null);
  const [logs, setLogs] = useState(null);

  useEffect(() => {
    api.accessControl().then(setAc).catch(() => setAc(null));
    api.integration().then(setIntg).catch(() => {});
    api.auditLogs().then((d) => setLogs(d.logs)).catch(() => setLogs([]));
  }, []);

  return (
    <Shell title="Quản trị & Tích hợp" crumb="Cổng Quản trị & Kiểm toán">
      {/* Integration monitoring */}
      <div className="cols cols-4 fade fade-1">
        <Stat k="Uptime dịch vụ" value={intg ? intg.uptime_pct : "—"} unit="%" sub="30 ngày" />
        <Stat k="Độ trễ gần nhất" value={intg ? intg.last_latency_ms : "—"} unit="ms" sub="API scoring" />
        <Stat k="Request lỗi hôm nay" value={intg ? intg.failed_requests_today : "—"} sub="Cần theo dõi" />
        <Stat k="Kết nối hoạt động" value={intg ? intg.connections.filter((c) => c.status === "active").length : "—"}
          sub={intg ? `/ ${intg.connections.length} hệ thống` : ""} />
      </div>

      <div className="cols cols-2-1 fade fade-2" style={{ marginTop: 18 }}>
        <Card>
          <CardHead eyebrow="Tích hợp hệ thống" title="Giám sát kết nối lõi" />
          <Pad>
            {!intg ? <Loading /> : (
              <table className="table">
                <thead><tr><th>Hệ thống</th><th>Trạng thái</th><th style={{ textAlign: "right" }}>Độ trễ</th></tr></thead>
                <tbody>
                  {intg.connections.map((c) => (
                    <tr key={c.name}>
                      <td><Icon.plug width={15} height={15} style={{ color: "var(--ink-3)", verticalAlign: "-2px", marginRight: 6 }} />{c.name}</td>
                      <td><span className="badge badge--green"><span className="dot-flow" style={{ background: "currentColor" }} /> Hoạt động</span></td>
                      <td className="mono tnum" style={{ textAlign: "right" }}>{c.latency_ms} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Pad>
        </Card>

        <Card>
          <CardHead eyebrow="Bảo mật" title="Nguyên tắc phân quyền" />
          <Pad>
            <div className="factor pos"><span className="ic"><Icon.check width={13} height={13} /></span>
              <div>Phân tách dữ liệu theo vai trò<br /><small>Khách hàng không thấy điểm/PD/SHAP</small></div></div>
            <div className="factor pos"><span className="ic"><Icon.check width={13} height={13} /></span>
              <div>Maker-checker cho thay đổi quy tắc<br /><small>Hai người độc lập</small></div></div>
            <div className="factor pos"><span className="ic"><Icon.check width={13} height={13} /></span>
              <div>Ghi nhật ký toàn bộ truy cập<br /><small>Phục vụ kiểm toán & truy vết</small></div></div>
          </Pad>
        </Card>
      </div>

      {/* Access control matrix */}
      <Card className="fade fade-3" style={{ marginTop: 18 }}>
        <CardHead eyebrow="Kiểm soát truy cập" title="Ma trận phân quyền theo vai trò" />
        <Pad>
          {ac === undefined ? <Loading /> : (
            <div style={{ overflowX: "auto" }}>
              <table className="table">
                <thead><tr>{ac.columns.map((c, i) => <th key={i} style={i ? { textAlign: "center" } : {}}>{c}</th>)}</tr></thead>
                <tbody>
                  {ac.rows.map((r, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 600 }}>{r.feature}</td>
                      <td style={{ textAlign: "center" }}>{cell(r.customer)}</td>
                      <td style={{ textAlign: "center" }}>{cell(r.bank)}</td>
                      <td style={{ textAlign: "center" }}>{cell(r.admin)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Pad>
      </Card>

      {/* Audit logs */}
      <Card className="fade fade-4" style={{ marginTop: 18 }}>
        <CardHead eyebrow="Nhật ký kiểm toán" title="Hoạt động gần đây"
          right={<span className="muted" style={{ fontSize: 12 }}>{logs?.length || 0} bản ghi</span>} />
        <Pad>
          {logs === null ? <Loading /> : logs.length === 0 ? (
            <div className="muted" style={{ fontSize: 13 }}>Chưa có hoạt động nào được ghi nhận.</div>
          ) : (
            <div style={{ maxHeight: 360, overflowY: "auto" }}>
              <table className="table">
                <thead><tr><th>Thời gian</th><th>Tác nhân</th><th>Hành động</th><th>Chi tiết</th></tr></thead>
                <tbody>
                  {logs.map((l, i) => (
                    <tr key={i}>
                      <td className="mono" style={{ fontSize: 12, whiteSpace: "nowrap" }}>{dt(l.ts)}</td>
                      <td>{l.actor}</td>
                      <td><span className="tag-soft mono" style={{ fontSize: 11 }}>{l.action}</span></td>
                      <td className="muted" style={{ fontSize: 12.5 }}>{l.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Pad>
      </Card>
    </Shell>
  );
}
