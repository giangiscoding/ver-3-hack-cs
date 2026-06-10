const TOKEN_KEY = "ss_token";

export function getToken() {
  return window.__ss_token || null;
}
export function setToken(t) {
  window.__ss_token = t;
}

async function req(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  const tok = getToken();
  if (tok) headers.Authorization = `Bearer ${tok}`;
  const res = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* ignore */
  }
  if (!res.ok) {
    const msg = (data && data.detail) || `Lỗi ${res.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

export const api = {
  login: (username, password) => req("POST", "/api/login", { username, password }),
  meta: () => req("GET", "/api/meta"),

  // customer
  customerApplication: () => req("GET", "/api/customer/application"),
  customerSubmit: (payload) => req("POST", "/api/customer/application", payload),

  // bank
  bankCases: (q, flow) => {
    const p = new URLSearchParams();
    if (q) p.set("q", q);
    if (flow) p.set("flow", flow);
    return req("GET", `/api/bank/cases?${p.toString()}`);
  },
  bankCase: (cid) => req("GET", `/api/bank/cases/${cid}`),
  quickScore: (payload) => req("POST", "/api/bank/quick-score", payload),

  // admin
  monitoring: () => req("GET", "/api/admin/monitoring"),
  adminCases: (q) => req("GET", `/api/admin/cases?${q ? "q=" + encodeURIComponent(q) : ""}`),
  caseAudit: (cid) => req("GET", `/api/admin/cases/${cid}/audit`),
  rules: () => req("GET", "/api/admin/rule-engine"),
  proposeRules: (rules) => req("POST", "/api/admin/rule-engine/propose", { rules }),
  approveRules: (approver) => req("POST", "/api/admin/rule-engine/approve", { approver }),
  accessControl: () => req("GET", "/api/admin/access-control"),
  integration: () => req("GET", "/api/admin/integration"),
  auditLogs: () => req("GET", "/api/admin/audit-logs"),
};

export { TOKEN_KEY };
