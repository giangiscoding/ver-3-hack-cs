export function vnd(n) {
  if (n == null) return "—";
  if (n === 0) return "0 ₫";
  if (n >= 1e9) return `${(n / 1e9).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} tỷ ₫`;
  if (n >= 1e6) return `${(n / 1e6).toLocaleString("vi-VN", { maximumFractionDigits: 0 })} triệu ₫`;
  return `${n.toLocaleString("vi-VN")} ₫`;
}

export function vndFull(n) {
  if (n == null) return "—";
  return n.toLocaleString("vi-VN") + " ₫";
}

export function pct(n, d = 1) {
  if (n == null) return "—";
  return `${Number(n).toFixed(d)}%`;
}

export function dt(s) {
  if (!s) return "—";
  const d = new Date(s);
  return d.toLocaleString("vi-VN", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export const FLOW = {
  green: { label: "Luồng Xanh", cls: "green", badge: "badge--green" },
  yellow: { label: "Luồng Vàng", cls: "yellow", badge: "badge--amber" },
  red: { label: "Luồng Đỏ", cls: "red", badge: "badge--red" },
};

export const DECISION_VI = {
  approve: "Phê duyệt",
  manual_review: "Xem xét thủ công",
  decline: "Từ chối",
};

export const DSR_VI = { thin: "Mỏng", semi: "Trung bình", thick: "Dày" };

export const SIZE_VI = { micro: "Siêu nhỏ", small: "Nhỏ", medium: "Vừa" };

export function initials(name) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  return (parts[0][0] + (parts[parts.length - 1][0] || "")).toUpperCase();
}
