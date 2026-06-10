import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth.jsx";
import { BrandMark, Icon } from "./icons.jsx";
import { initials } from "../lib/format.js";

const NAV = {
  customer: {
    role: "Cổng Doanh nghiệp",
    items: [
      { to: "/customer/dashboard", label: "Tổng quan", icon: Icon.grid },
      { to: "/customer/application", label: "Nộp hồ sơ vay", icon: Icon.doc },
      { to: "/customer/status", label: "Trạng thái & Kết quả", icon: Icon.list },
    ],
  },
  bank_user: {
    role: "Cổng Cán bộ Ngân hàng",
    items: [
      { to: "/bank/cases", label: "Danh sách hồ sơ", icon: Icon.folder },
      { to: "/bank/quick-score", label: "Chấm điểm nhanh", icon: Icon.bolt },
    ],
  },
  admin: {
    role: "Cổng Quản trị & Kiểm toán",
    items: [
      { to: "/admin/dashboard", label: "Giám sát mô hình", icon: Icon.chart },
      { to: "/admin/cases", label: "Kiểm toán hồ sơ", icon: Icon.shield },
      { to: "/admin/rule-engine", label: "Cấu hình Rule Engine", icon: Icon.sliders },
      { to: "/admin/governance", label: "Quản trị & Tích hợp", icon: Icon.plug },
    ],
  },
};

export default function Shell({ title, crumb, actions, children }) {
  const { user, signOut } = useAuth();
  const cfg = NAV[user?.role] || NAV.customer;
  const loc = useLocation();

  return (
    <div className="shell">
      <aside className="side">
        <div className="side__brand">
          <BrandMark size={38} />
          <div>
            <div className="side__brandtxt">ScoreSight</div>
            <div className="side__role">{cfg.role}</div>
          </div>
        </div>

        <div className="side__group">Điều hướng</div>
        <nav>
          {cfg.items.map((it) => (
            <NavLink key={it.to} to={it.to}
              className={({ isActive }) =>
                "navlink" + (isActive || loc.pathname.startsWith(it.to) ? " active" : "")}>
              <it.icon width={18} height={18} />
              {it.label}
            </NavLink>
          ))}
        </nav>

        <div className="side__foot">
          <div className="side__user">
            <div className="avatar">{initials(user?.display_name)}</div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {user?.display_name}
              </div>
              <small>{user?.username}</small>
            </div>
          </div>
          <button className="navlink" style={{ width: "100%", marginTop: 6 }} onClick={signOut}>
            <Icon.logout width={18} height={18} /> Đăng xuất
          </button>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div>
            {crumb && <div className="crumb">{crumb}</div>}
            <h1>{title}</h1>
          </div>
          <div className="flex">{actions}</div>
        </header>
        <div className="content">{children}</div>
      </div>
    </div>
  );
}
