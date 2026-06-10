import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Shell from "../../components/Shell.jsx";
import { Card, CardHead, Pad, Loading, Notice } from "../../components/ui.jsx";
import { Icon } from "../../components/icons.jsx";
import { api } from "../../lib/api.js";
import { useAuth } from "../../lib/auth.jsx";

const STEPS = [
  { t: "Nộp hồ sơ", d: "Điền thông tin doanh nghiệp và cho phép phân tích dữ liệu.", ic: Icon.doc },
  { t: "Kiểm tra dữ liệu", d: "Hệ thống đối chiếu dữ liệu giao dịch, hóa đơn, dòng tiền.", ic: Icon.shield },
  { t: "Đánh giá tín dụng", d: "Mô hình đánh giá năng lực dựa trên dữ liệu phi truyền thống.", ic: Icon.chart },
  { t: "Kết quả & Bước tiếp theo", d: "Nhận kết quả rút gọn và hướng dẫn tiếp theo.", ic: Icon.check },
];

export default function CustomerDashboard() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [app, setApp] = useState(undefined);

  useEffect(() => { api.customerApplication().then(setApp).catch(() => setApp(null)); }, []);

  return (
    <Shell title={`Xin chào, ${user?.display_name || "Doanh nghiệp"}`} crumb="Cổng Doanh nghiệp">
      <div className="stack">
        <Card className="fade fade-1" style={{
          background: "linear-gradient(120deg, var(--navy), var(--navy-3))", color: "#fff", border: "none",
        }}>
          <Pad style={{ padding: "26px 28px" }}>
            <div className="flex between wrap" style={{ gap: 20 }}>
              <div style={{ maxWidth: 540 }}>
                <span className="badge badge--orange" style={{ background: "rgba(245,107,41,0.2)", color: "#ffd0b3", borderColor: "transparent" }}>
                  Vốn cho doanh nghiệp nhỏ & vừa
                </span>
                <h2 style={{ fontSize: 26, margin: "12px 0 8px", letterSpacing: "-0.02em" }}>
                  Tiếp cận vốn dựa trên dữ liệu thật của bạn
                </h2>
                <p style={{ color: "#c2cee0", margin: 0, fontSize: 14.5 }}>
                  Không cần lịch sử tín dụng truyền thống. Chúng tôi đánh giá dựa trên dòng tiền,
                  hóa đơn điện tử, giao dịch TMĐT và hoạt động kinh doanh thực tế.
                </p>
              </div>
              <button className="btn btn--primary btn--lg" onClick={() => nav("/customer/application")}>
                <Icon.doc width={18} height={18} /> Nộp hồ sơ vay
              </button>
            </div>
          </Pad>
        </Card>

        {app === undefined ? (
          <Loading />
        ) : app && app.has_application ? (
          <Card className="fade fade-2">
            <CardHead eyebrow="Hồ sơ hiện tại" title={app.company_name}
              right={<span className="badge badge--orange">{app.status}</span>} />
            <Pad>
              <Notice kind="info">{app.headline} {app.detail}</Notice>
              <div className="flex" style={{ marginTop: 16 }}>
                <button className="btn btn--ghost" onClick={() => nav("/customer/status")}>
                  Xem chi tiết trạng thái <Icon.arrow width={16} height={16} />
                </button>
              </div>
            </Pad>
          </Card>
        ) : (
          <Card className="fade fade-2">
            <Pad>
              <Notice kind="info">
                Bạn chưa có hồ sơ nào. Hãy bắt đầu bằng cách nộp hồ sơ vay — chỉ mất vài phút.
              </Notice>
            </Pad>
          </Card>
        )}

        <Card className="fade fade-3">
          <CardHead eyebrow="Quy trình" title="Hồ sơ của bạn sẽ đi qua 4 bước" />
          <Pad>
            <div className="cols cols-4">
              {STEPS.map((s, i) => (
                <div key={i} style={{ padding: "4px 4px 0" }}>
                  <div style={{ width: 40, height: 40, borderRadius: 11, background: "var(--shb-orange-soft)",
                    color: "var(--shb-orange)", display: "grid", placeItems: "center", marginBottom: 10 }}>
                    <s.ic width={20} height={20} />
                  </div>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{i + 1}. {s.t}</div>
                  <div className="muted" style={{ fontSize: 12.5, marginTop: 4 }}>{s.d}</div>
                </div>
              ))}
            </div>
          </Pad>
        </Card>
      </div>
    </Shell>
  );
}
