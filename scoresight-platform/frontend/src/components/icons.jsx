// Minimal stroke icon set (Vietnamese-product UI). 18px default.
const I = (p) => ({ width: 18, height: 18, viewBox: "0 0 24 24", fill: "none",
  stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", ...p });

export const Icon = {
  grid: (p) => (<svg {...I(p)}><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>),
  doc: (p) => (<svg {...I(p)}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h6"/></svg>),
  upload: (p) => (<svg {...I(p)}><path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/></svg>),
  flag: (p) => (<svg {...I(p)}><path d="M5 21V4"/><path d="M5 4h10l-1.5 3L15 10H5"/></svg>),
  search: (p) => (<svg {...I(p)}><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg>),
  bolt: (p) => (<svg {...I(p)}><path d="M13 2 4 14h6l-1 8 9-12h-6z"/></svg>),
  folder: (p) => (<svg {...I(p)}><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>),
  chart: (p) => (<svg {...I(p)}><path d="M4 20V4"/><path d="M4 20h16"/><rect x="7" y="11" width="3" height="6" rx="0.6"/><rect x="12" y="7" width="3" height="10" rx="0.6"/><rect x="17" y="13" width="3" height="4" rx="0.6"/></svg>),
  shield: (p) => (<svg {...I(p)}><path d="M12 3 5 6v6c0 4 3 7 7 9 4-2 7-5 7-9V6z"/><path d="m9 12 2 2 4-4"/></svg>),
  sliders: (p) => (<svg {...I(p)}><path d="M4 6h10M18 6h2M4 12h2M10 12h10M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="8" cy="12" r="2"/><circle cx="18" cy="18" r="2"/></svg>),
  lock: (p) => (<svg {...I(p)}><rect x="4.5" y="10" width="15" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>),
  plug: (p) => (<svg {...I(p)}><path d="M9 2v6M15 2v6"/><path d="M7 8h10v3a5 5 0 0 1-10 0z"/><path d="M12 16v6"/></svg>),
  list: (p) => (<svg {...I(p)}><path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/></svg>),
  logout: (p) => (<svg {...I(p)}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>),
  user: (p) => (<svg {...I(p)}><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>),
  arrow: (p) => (<svg {...I(p)}><path d="M5 12h14M13 6l6 6-6 6"/></svg>),
  check: (p) => (<svg {...I(p)}><path d="m5 13 4 4L19 7"/></svg>),
  alert: (p) => (<svg {...I(p)}><path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/></svg>),
  info: (p) => (<svg {...I(p)}><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg>),
  x: (p) => (<svg {...I(p)}><path d="M18 6 6 18M6 6l12 12"/></svg>),
};

export function BrandMark({ size = 36 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" aria-hidden>
      <rect width="40" height="40" rx="11" fill="#0F1B2D" />
      <path d="M11 26c0-3 2.4-4.2 5-4.7 2.2-.4 3.3-.9 3.3-2.1 0-1-.9-1.7-2.3-1.7-1.6 0-2.6.8-2.8 2.1H11c.2-3 2.6-4.9 6-4.9 3.3 0 5.6 1.8 5.6 4.4 0 3-2.4 4.1-5.1 4.6-2.1.4-3.2.9-3.2 2.1 0 1 .9 1.8 2.5 1.8 1.8 0 2.9-.9 3-2.3h3.2c-.2 3.1-2.7 5.1-6.2 5.1-3.5 0-5.8-1.8-5.8-4.5z" fill="#F56B29"/>
      <circle cx="28.5" cy="13.5" r="2.4" fill="#F56B29" />
    </svg>
  );
}
