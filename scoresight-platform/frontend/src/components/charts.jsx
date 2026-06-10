// Lightweight dependency-free SVG charts.

export function ScoreGauge({ score, min = 300, max = 850, size = 190 }) {
  const r = size / 2 - 16;
  const cx = size / 2, cy = size / 2;
  const start = -220, end = 40; // degrees (sweep ~260)
  const frac = Math.max(0, Math.min(1, (score - min) / (max - min)));
  const ang = start + (end - start) * frac;
  const toXY = (deg) => {
    const a = (deg * Math.PI) / 180;
    return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  };
  const arc = (a0, a1, color, w) => {
    const [x0, y0] = toXY(a0), [x1, y1] = toXY(a1);
    const large = Math.abs(a1 - a0) > 180 ? 1 : 0;
    return <path d={`M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`}
      stroke={color} strokeWidth={w} fill="none" strokeLinecap="round" />;
  };
  const color = score >= 700 ? "var(--green)" : score >= 620 ? "#2b6fb5"
    : score >= 540 ? "var(--amber)" : "var(--red)";
  const [hx, hy] = toXY(ang);
  return (
    <svg width={size} height={size * 0.82} viewBox={`0 0 ${size} ${size * 0.82}`}>
      {arc(start, end, "var(--line-2)", 13)}
      {arc(start, ang, color, 13)}
      <circle cx={hx} cy={hy} r="7" fill="#fff" stroke={color} strokeWidth="3.5" />
      <text x={cx} y={cy + 2} textAnchor="middle" fontSize="40" fontWeight="800"
        fill="var(--ink)" style={{ fontVariantNumeric: "tabular-nums" }}>{score}</text>
      <text x={cx} y={cy + 24} textAnchor="middle" fontSize="12" fill="var(--ink-3)">/ {max} điểm</text>
    </svg>
  );
}

export function Donut({ data, size = 168, thickness = 26, centerLabel, centerSub }) {
  // data: [{label, value, color}]
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const r = (size - thickness) / 2;
  const cx = size / 2, cy = size / 2;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div style={{ display: "flex", gap: 18, alignItems: "center", flexWrap: "wrap" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <g transform={`rotate(-90 ${cx} ${cy})`}>
          {data.map((d, i) => {
            const len = (d.value / total) * c;
            const el = (
              <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke={d.color}
                strokeWidth={thickness} strokeDasharray={`${len} ${c - len}`}
                strokeDashoffset={-offset} />
            );
            offset += len;
            return el;
          })}
        </g>
        {centerLabel && (
          <>
            <text x={cx} y={cy - 2} textAnchor="middle" fontSize="26" fontWeight="800"
              fill="var(--ink)" style={{ fontVariantNumeric: "tabular-nums" }}>{centerLabel}</text>
            <text x={cx} y={cy + 18} textAnchor="middle" fontSize="11" fill="var(--ink-3)">{centerSub}</text>
          </>
        )}
      </svg>
      <div style={{ display: "grid", gap: 8 }}>
        {data.map((d, i) => (
          <div key={i} className="flex" style={{ fontSize: 13 }}>
            <span style={{ width: 11, height: 11, borderRadius: 3, background: d.color }} />
            <span style={{ minWidth: 110 }}>{d.label}</span>
            <b className="tnum">{d.value}</b>
            <span className="muted tnum">({((d.value / total) * 100).toFixed(0)}%)</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Bars({ data, color = "var(--shb-orange)", unit = "" }) {
  // data: [{label, value}]
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div style={{ display: "grid", gap: 12 }}>
      {data.map((d, i) => (
        <div key={i}>
          <div className="flex between" style={{ fontSize: 12.5, marginBottom: 5 }}>
            <span>{d.label}</span>
            <b className="tnum">{d.value}{unit}</b>
          </div>
          <div className="meter">
            <i style={{ width: `${(d.value / max) * 100}%`, background: d.color || color }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ShapBars({ items, kind }) {
  // items: [{label, shap_value, value}]; kind: 'pos' | 'neg'
  const max = Math.max(...items.map((i) => Math.abs(i.shap_value)), 0.01);
  const color = kind === "pos" ? "var(--green)" : "var(--red)";
  return (
    <div style={{ display: "grid", gap: 11 }}>
      {items.map((it, i) => (
        <div key={i}>
          <div className="flex between" style={{ fontSize: 12.5, marginBottom: 4 }}>
            <span>{it.label}</span>
            <span className="mono muted" style={{ fontSize: 11.5 }}>
              {it.shap_value > 0 ? "+" : ""}{it.shap_value}
            </span>
          </div>
          <div className="meter">
            <i style={{ width: `${(Math.abs(it.shap_value) / max) * 100}%`, background: color }} />
          </div>
        </div>
      ))}
    </div>
  );
}
