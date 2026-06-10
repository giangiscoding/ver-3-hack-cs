import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth.jsx";
import { BrandMark, Icon } from "../components/icons.jsx";
import { Field } from "../components/ui.jsx";

const DEMO = [
  { label: "Doanh nghiệp (Luồng vàng)", u: "Customer_123", p: "Customer_123", pill: "customer_1" },
  { label: "Doanh nghiệp (Luồng xanh)", u: "Customer_green", p: "Customer_green", pill: "customer_2" },
  { label: "Cán bộ NH (RM / CBTĐ)", u: "Bankuser_123", p: "Bankuser_123" },
  { label: "Quản trị / Kiểm toán", u: "Bank_admin", p: "Bank_admin" },
];

export default function Login() {
  const { signIn } = useAuth();
  const nav = useNavigate();
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e?.preventDefault();
    setErr(""); setBusy(true);
    try {
      const user = await signIn(u, p);
      nav(user.home, { replace: true });
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <div className="auth__brandside">
        <div className="auth__grid" />
        <div style={{ position: "relative" }}>
          <div className="flex" style={{ gap: 12 }}>
            <BrandMark size={46} />
            <div>
              <div style={{ fontWeight: 800, fontSize: 20, letterSpacing: "-0.02em" }}>ScoreSight</div>
              <div style={{ color: "#93a3bd", fontSize: 12, letterSpacing: "0.05em" }}>SHB · ALTERNATIVE CREDIT SCORING</div>
            </div>
          </div>

          <h1>Chấm điểm tín dụng <span className="accent">MSME</span><br />bằng dữ liệu phi truyền thống</h1>
          <p className="auth__lede">
            Một điểm đăng nhập chung — ba trải nghiệm theo vai trò. Quyết định nhanh hơn,
            giải trình minh bạch, kiểm soát truy cập chặt chẽ.
          </p>

          <div className="auth__points">
            <div className="auth__point"><span className="dot">1</span>
              <div><b>Doanh nghiệp</b> — nộp hồ sơ, theo dõi tiến độ, nhận kết quả rút gọn.</div></div>
            <div className="auth__point"><span className="dot">2</span>
              <div><b>Cán bộ ngân hàng</b> — điểm số, hạng rủi ro, lý do theo tiêu chí, luồng Xanh/Vàng/Đỏ.</div></div>
            <div className="auth__point"><span className="dot">3</span>
              <div><b>Quản trị & kiểm toán</b> — SHAP, rule engine (maker-checker), nhật ký & tích hợp.</div></div>
          </div>
        </div>
      </div>

      <div className="auth__formside">
        <form className="auth__card" onSubmit={submit}>
          <h2>Đăng nhập hệ thống</h2>
          <div className="sub">Truy cập an toàn cho doanh nghiệp và cán bộ ngân hàng.</div>

          <Field label="Email / Tên đăng nhập" required>
            <input className="input" value={u} onChange={(e) => setU(e.target.value)}
              placeholder="Nhập tên đăng nhập" autoComplete="username" />
          </Field>
          <Field label="Mật khẩu" required>
            <input className="input" type="password" value={p} onChange={(e) => setP(e.target.value)}
              placeholder="Nhập mật khẩu" autoComplete="current-password" />
          </Field>

          {err && (
            <div className="notice notice--warn" style={{ marginBottom: 12 }}>
              <Icon.alert width={16} height={16} style={{ flex: "none", marginTop: 1 }} /> {err}
            </div>
          )}

          <button className="btn btn--primary btn--block btn--lg" disabled={busy}>
            {busy ? "Đang đăng nhập…" : "Đăng nhập"} <Icon.arrow width={17} height={17} />
          </button>

          <div className="flex between" style={{ marginTop: 12, fontSize: 12.5 }}>
            <a className="muted" href="#">Quên mật khẩu?</a>
            <a className="muted" href="#">Điều khoản & Chính sách bảo mật</a>
          </div>

          <div className="creds">
            <div style={{ fontWeight: 600, marginBottom: 6, color: "var(--ink)" }}>Tài khoản demo (nhấn để điền):</div>
            {DEMO.map((d) => (
              <div className="row" key={d.u}>
                <span>{d.label}</span>
                <button type="button" className="pill" onClick={() => { setU(d.u); setP(d.p); setErr(""); }}>
                  {d.pill ?? d.u}
                </button>
              </div>
            ))}
          </div>
        </form>
      </div>
    </div>
  );
}
