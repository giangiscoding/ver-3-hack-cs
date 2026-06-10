import { FLOW } from "../lib/format.js";
import { Icon } from "./icons.jsx";

export function Card({ children, className = "", flow, ...rest }) {
  const fc = flow ? `flowcard ${FLOW[flow]?.cls || ""}` : "";
  return <div className={`card ${fc} ${className}`} {...rest}>{children}</div>;
}
export function CardHead({ eyebrow, title, right }) {
  return (
    <div className="card__head">
      <div className="card__title">
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        {title}
      </div>
      {right}
    </div>
  );
}
export function Pad({ children, style }) {
  return <div className="card__pad" style={style}>{children}</div>;
}

export function Stat({ k, value, unit, sub, className = "" }) {
  return (
    <Card className={`stat ${className}`}>
      <div className="k">{k}</div>
      <div className="v">{value}{unit && <span className="unit"> {unit}</span>}</div>
      {sub && <div className="sub">{sub}</div>}
    </Card>
  );
}

export function FlowBadge({ flow, text }) {
  const f = FLOW[flow] || FLOW.yellow;
  return (
    <span className={`badge ${f.badge}`}>
      <span className="dot-flow" style={{ background: "currentColor" }} />
      {text || f.label}
    </span>
  );
}

export function Tier({ tier }) {
  return <span className={`tier tier--${tier}`}>{tier}</span>;
}

export function Field({ label, required, hint, children }) {
  return (
    <div className="field">
      {label && <label>{label}{required && <span className="req"> *</span>}</label>}
      {children}
      {hint && <div className="hint">{hint}</div>}
    </div>
  );
}

export function Loading({ text = "Đang tải dữ liệu mô hình…" }) {
  return (
    <div className="loading">
      <div style={{ textAlign: "center" }}>
        <div className="spin" style={{ margin: "0 auto 14px" }} />
        <div className="muted">{text}</div>
      </div>
    </div>
  );
}

export function Notice({ kind = "info", children }) {
  const I = kind === "warn" ? Icon.alert : kind === "ok" ? Icon.check : Icon.info;
  return (
    <div className={`notice notice--${kind}`}>
      <I width={17} height={17} style={{ flex: "none", marginTop: 1 }} />
      <div>{children}</div>
    </div>
  );
}

export function Lock({ children }) {
  return <span className="lock"><Icon.lock width={13} height={13} /> {children}</span>;
}

export function Meter({ value, max = 100, color = "var(--shb-orange)" }) {
  const w = Math.max(0, Math.min(100, (value / max) * 100));
  return <div className="meter"><i style={{ width: `${w}%`, background: color }} /></div>;
}
