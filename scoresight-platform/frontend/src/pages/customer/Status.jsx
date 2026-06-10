import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Shell from "../../components/Shell.jsx";
import { Card, CardHead, Pad, Loading, Notice } from "../../components/ui.jsx";
import { Icon } from "../../components/icons.jsx";
import { api } from "../../lib/api.js";
import { dt } from "../../lib/format.js";

function statusKind(status) {
  if (status?.includes("sơ duyệt")) return "ok";
  if (status?.includes("xem xét")) return "warn";
  return "info";
}

export default function CustomerStatus() {
  const nav = useNavigate();
  const [app, setApp] = useState(undefined);

  useEffect(() => { api.customerApplication().then(setApp).catch(() => setApp(null)); }, []);

  if (app === undefined) return <Shell title="Trạng thái & Kết quả" crumb="Cổng Doanh nghiệp"><Loading /></Shell>;

  if (!app || !app.has_application) {
    return (
      <Shell title="Trạng thái & Kết quả" crumb="Cổng Doanh nghiệp">
        <Card className="fade fade-1"><Pad>
          <Notice kind="info">Bạn chưa nộp hồ sơ nào. Hãy nộp hồ sơ để xem trạng thái tại đây.</Notice>
          <button className="btn btn--primary" style={{ marginTop: 16 }} onClick={() => nav("/customer/application")}>
            <Icon.doc width={17} height={17} /> Nộp hồ sơ vay
          </button>
        </Pad></Card>
      </Shell>
    );
  }

  const kind = statusKind(app.status);
  return (
    <Shell title="Trạng thái & Kết quả" crumb={`Cổng Doanh nghiệp · ${app.company_name}`}>
      <div className="cols cols-2-1">
        <Card className="fade fade-1" flow={kind === "ok" ? "green" : kind === "warn" ? "yellow" : undefined}>
          <CardHead eyebrow="Kết quả hồ sơ"
            title={app.company_name}
            right={<span className={`badge ${kind === "ok" ? "badge--green" : kind === "warn" ? "badge--amber" : "badge--navy"}`}>{app.status}</span>} />
          <Pad>
            <h2 style={{ fontSize: 21, margin: "2px 0 10px", letterSpacing: "-0.01em" }}>{app.headline}</h2>
            <p style={{ color: "var(--ink-2)", fontSize: 14.5, marginTop: 0 }}>{app.detail}</p>

            <div className="notice notice--info" style={{ marginTop: 16 }}>
              <Icon.arrow width={17} height={17} style={{ flex: "none", marginTop: 1 }} />
              <div><b>Bước tiếp theo:</b> {app.next_step}</div>
            </div>

            <div className="flex wrap" style={{ marginTop: 18, gap: 10 }}>
              <button className="btn btn--ghost" onClick={() => nav("/customer/application")}>
                Nộp hồ sơ mới
              </button>
              <button className="btn btn--navy">
                <Icon.user width={16} height={16} /> Liên hệ chuyên viên
              </button>
            </div>

            <Notice kind="info" >
              <span style={{ fontSize: 12.5 }}>
                Vì lý do bảo mật, kết quả hiển thị cho doanh nghiệp ở dạng rút gọn.
                Điểm số và chi tiết đánh giá được cán bộ ngân hàng sử dụng nội bộ.
              </span>
            </Notice>
          </Pad>
        </Card>

        <Card className="fade fade-2">
          <CardHead eyebrow="Tiến trình" title="Hồ sơ của bạn" />
          <Pad>
            <div className="timeline">
              {app.timeline.map((t, i) => (
                <div className="tl" key={t.key}>
                  <div className="tl__rail">
                    <div className={`tl__node ${t.done ? "done" : ""}`}>
                      {t.done ? <Icon.check width={14} height={14} /> : i + 1}
                    </div>
                    {i < app.timeline.length - 1 && <div className={`tl__line ${t.done ? "done" : ""}`} />}
                  </div>
                  <div className="tl__body">
                    <b>{t.label}</b>
                  </div>
                </div>
              ))}
            </div>
            <div className="kv" style={{ marginTop: 8 }}>
              <span className="k">Thời điểm nộp</span>
              <span className="v">{dt(app.submitted_at)}</span>
            </div>
          </Pad>
        </Card>
      </div>
    </Shell>
  );
}
