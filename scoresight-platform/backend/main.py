"""
ScoreSight Platform · API
=========================

Common login -> role-based routing. Each role sees only what it is allowed to:

  customer   : application + simplified result (NO score/PD/SHAP/rules)
  bank_user  : model output + criteria-level explanation + ops panel (NO raw
               SHAP table / rule-engine config / weights)
  admin      : full audit, SHAP drivers, rule engine (maker-checker), access
               matrix, integration monitoring, audit logs

Run:  uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine import (
    BASE_LIMIT_VND, DECISION_THRESHOLDS, DSR_THR, FEATURE_LABELS,
    LIMIT_FACTOR, MODEL_VERSION, SOURCE_LABELS, FEATURE_DICT, score_fields,
)
from security import login, require_roles
from store import STORE

app = FastAPI(title="ScoreSight Platform API", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

CUSTOMER_VND_FMT = "{:,.0f}".replace(",", ".")


# ════════════════════════════════════════════════════════════ Auth ══════════
class LoginReq(BaseModel):
    username: str
    password: str


@app.post("/api/login")
def api_login(req: LoginReq):
    res = login(req.username, req.password)
    STORE.log(req.username, "LOGIN", f"Đăng nhập vai trò {res['role']}")
    return res


@app.get("/api/health")
def health():
    return {"status": "ok", "model": MODEL_VERSION, "cases": len(STORE.cases)}


# ─────────────────────────────────────── customer-facing status mapping ─────
def _customer_view(rec: dict) -> dict:
    """Strictly simplified. No score / PD / tier / SHAP / rule logic."""
    d = rec["decision"]
    if d == "approve":
        lo = int(rec["credit_limit_vnd"])
        hi = int(rec["credit_limit_vnd"] * 1.4)
        status = "Đã sơ duyệt (Pre-qualified)"
        headline = "Hồ sơ của bạn đã được ghi nhận"
        detail = "Hồ sơ đã được tiếp nhận và đang trong quá trình hoàn tất thủ tục phê duyệt."
        next_step = "Chuyên viên (RM) sẽ liên hệ với bạn trong 1–2 ngày làm việc để hoàn tất hồ sơ."
    elif d == "manual_review":
        status = "Đang xem xét (Under review)"
        headline = "Hồ sơ của bạn cần được xem xét thêm."
        miss = rec.get("missing_docs") or ["sao kê ngân hàng gần nhất"]
        detail = ("Vui lòng bổ sung: " + ", ".join(miss[:2]) + ". "
                  "Sau khi nhận đủ thông tin, hồ sơ sẽ được xử lý tiếp.")
        next_step = "Bổ sung tài liệu được yêu cầu để tiếp tục."
    else:
        status = "Chưa đủ điều kiện (Not eligible)"
        headline = "Hồ sơ chưa đủ điều kiện tại thời điểm này."
        detail = ("Bạn có thể nộp lại sau khi cải thiện các thông tin tài chính cần thiết, "
                  "hoặc liên hệ ngân hàng để được tư vấn.")
        next_step = "Cải thiện hồ sơ tài chính và nộp lại sau."
    timeline = [
        {"key": "submitted", "label": "Đã tiếp nhận", "done": True},
        {"key": "checking", "label": "Kiểm tra dữ liệu", "done": True},
        {"key": "assessment", "label": "Đánh giá tín dụng", "done": True},
        {"key": "result", "label": "Kết quả / Bước tiếp theo", "done": True},
    ]
    return {
        "customer_id": rec["customer_id"],
        "company_name": rec.get("company_name", "Doanh nghiệp của bạn"),
        "status": status, "headline": headline, "detail": detail,
        "next_step": next_step, "timeline": timeline,
        "submitted_at": rec.get("timestamp"),
    }


# Pinned demo states — never overwritten by user submissions
_PINNED_APPS: dict[str, dict] = {
    "customer_green": {
        "customer_id": "APP-GREEN-DEMO",
        "company_name": "Công ty TNHH Sản xuất Minh Long",
        "decision": "approve",
        "credit_limit_vnd": 750_000_000,
        "hard_decline": False,
        "n_available": 18,
        "timestamp": "2026-06-07T09:00:00",
        "missing_docs": [],
    },
}

# In-memory store of customer-submitted applications (keyed by username)
_CUSTOMER_APPS: dict[str, dict] = {}


# ═══════════════════════════════════════════════════════ Customer Portal ════
class ApplicationReq(BaseModel):
    company_name: str
    mst: str | None = None
    industry: str | None = None
    business_age_months: int | None = None
    annual_revenue_vnd: float | None = None
    requested_limit_vnd: float | None = None
    loan_purpose: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    consent_data: bool = False
    consent_terms: bool = False
    # optional alt-data fields the form collects
    fields: dict[str, Any] = {}


@app.get("/api/customer/application")
def customer_application(sess=Depends(require_roles("customer"))):
    uname = sess["username"]
    if uname in _PINNED_APPS:
        return {"has_application": True, **_customer_view(_PINNED_APPS[uname])}
    app_ = _CUSTOMER_APPS.get(uname)
    if not app_:
        return {"has_application": False}
    return {"has_application": True, **_customer_view(app_)}


@app.post("/api/customer/application")
def customer_submit(req: ApplicationReq, sess=Depends(require_roles("customer"))):
    if not (req.consent_data and req.consent_terms):
        raise HTTPException(status_code=400, detail="Bạn cần đồng ý điều khoản và cho phép phân tích dữ liệu.")
    # assemble model fields
    fields = dict(req.fields)
    if req.industry:
        fields["industry"] = req.industry
    if req.business_age_months is not None:
        fields["business_age_months"] = req.business_age_months
    fields.setdefault("enterprise_size", _infer_size(req.annual_revenue_vnd, fields))
    cid = f"APP-{datetime.now().strftime('%H%M%S')}"
    rec = score_fields(cid, fields)
    rec["company_name"] = req.company_name
    rec["missing_docs"] = STORE.cases.get(cid, {}).get("missing_docs", [])
    # reuse missing-doc heuristic
    from store import _missing_key_docs
    import pandas as pd
    rec["missing_docs"] = _missing_key_docs(pd.Series(fields))
    rec["timestamp"] = datetime.now().isoformat(timespec="seconds")
    _CUSTOMER_APPS[sess["username"]] = rec
    STORE.log(sess["username"], "SUBMIT_APPLICATION", f"{req.company_name} → {rec['decision']}")
    return {"has_application": True, **_customer_view(rec)}


def _infer_size(rev: float | None, fields: dict) -> str:
    emp = fields.get("num_employees")
    if rev and rev >= 50_000_000_000:
        return "medium"
    if rev and rev >= 3_000_000_000:
        return "small"
    if emp and emp >= 50:
        return "medium"
    if emp and emp >= 10:
        return "small"
    return "micro"


# ═══════════════════════════════════════════════════════ Bank User Portal ══
def _bank_summary(rec: dict) -> dict:
    return {
        "customer_id": rec["customer_id"], "company_name": rec["company_name"],
        "mst": rec["mst"], "industry_vi": rec["industry_vi"], "region_vi": rec["region_vi"],
        "enterprise_size": rec["enterprise_size"], "credit_score": rec["credit_score"],
        "risk_tier": rec["risk_tier"], "dsr_group": rec["dsr_group"],
        "requested_limit_vnd": rec["requested_limit_vnd"],
        "credit_limit_vnd": rec["credit_limit_vnd"], "decision": rec["decision"],
        "flow": rec["flow"], "timestamp": rec["timestamp"],
    }


def _bank_detail(rec: dict) -> dict:
    flow_text = {
        "green": ("Luồng Xanh — Phê duyệt nhanh",
                  "Chuyển sang LOS/CMS theo quy trình phê duyệt chuẩn."),
        "yellow": ("Luồng Vàng — Cần xem xét thủ công",
                   "Yêu cầu bổ sung tài liệu hoặc chuyển chuyên viên thẩm định."),
        "red": ("Luồng Đỏ — Thẩm định tăng cường / Khuyến nghị từ chối",
                "Chuyển chuyên viên phê duyệt tín dụng để xử lý."),
    }[rec["flow"]]
    rec_text = {"approve": "Phê duyệt nhanh (Fast-track)",
                "manual_review": "Cần xem xét thủ công",
                "decline": "Thẩm định tăng cường / khuyến nghị từ chối"}[rec["decision"]]
    return {
        "summary": _bank_summary(rec),
        "model_result": {
            "credit_score": rec["credit_score"], "max_score": 850,
            "risk_tier": rec["risk_tier"], "pd_band": rec["pd_band"],
            "suggested_limit_vnd": rec["credit_limit_vnd"], "dsr_group": rec["dsr_group"],
            "dsr_value": rec["dsr_value"], "cashflow_strength": rec["cashflow_strength"],
            "revenue_stability": rec["revenue_stability"],
            "data_coverage_pct": rec["data_coverage_pct"],
            "recommendation": rec_text,
        },
        "criteria": rec["criteria"],
        "flow": {"color": rec["flow"], "title": flow_text[0], "action": flow_text[1],
                 "recommendation": rec_text},
        "ops_panel": {
            "tat_saving_pct": rec["tat_saving_pct"], "next_action": rec["next_action"],
            "manual_review_required": rec["decision"] != "approve",
            "missing_docs": rec["missing_docs"], "los_ready": rec["los_ready"],
            "escalate": rec["escalate"],
        },
        "warnings": (["Tín hiệu gian lận: thiết bị dùng chung — từ chối cứng."]
                     if rec["hard_decline"] else
                     (["Dữ liệu rất mỏng — độ tin cậy thấp."] if rec["n_available"] < 8 else [])),
    }


@app.get("/api/bank/cases")
def bank_cases(q: str | None = None, flow: str | None = None,
               sess=Depends(require_roles("bank_user", "admin"))):
    items = list(STORE.cases.values())
    if q:
        ql = q.strip().lower()
        items = [c for c in items if ql in c["customer_id"].lower()
                 or ql in c["company_name"].lower() or ql in c["mst"]]
    if flow in ("green", "yellow", "red"):
        items = [c for c in items if c["flow"] == flow]
    items = sorted(items, key=lambda c: c["timestamp"], reverse=True)[:60]
    return {"count": len(items), "cases": [_bank_summary(c) for c in items]}


@app.get("/api/bank/cases/{cid}")
def bank_case(cid: str, sess=Depends(require_roles("bank_user", "admin"))):
    rec = STORE.cases.get(cid)
    if not rec:
        raise HTTPException(404, "Không tìm thấy hồ sơ.")
    STORE.log(sess["username"], "VIEW_CASE", f"Xem hồ sơ {cid} ({rec['company_name']})")
    return _bank_detail(rec)


class QuickScoreReq(BaseModel):
    mst: str | None = None
    industry: str | None = None
    region: str | None = None
    business_age_months: int | None = None
    num_employees: int | None = None
    annual_revenue_vnd: float | None = None
    requested_limit_vnd: float | None = None
    invoice_revenue_12m: float | None = None
    supplier_payment_regularity: float | None = None


@app.post("/api/bank/quick-score")
def bank_quick_score(req: QuickScoreReq, sess=Depends(require_roles("bank_user", "admin"))):
    fields: dict[str, Any] = {}
    if req.industry: fields["industry"] = req.industry
    if req.region: fields["region"] = req.region
    if req.business_age_months is not None: fields["business_age_months"] = req.business_age_months
    if req.num_employees is not None: fields["num_employees"] = req.num_employees
    if req.invoice_revenue_12m is not None: fields["invoice_revenue_12m"] = req.invoice_revenue_12m
    if req.supplier_payment_regularity is not None:
        fields["supplier_payment_regularity"] = req.supplier_payment_regularity
    fields["enterprise_size"] = _infer_size(req.annual_revenue_vnd, fields)
    rec = score_fields(req.mst or "QUICK", fields)
    STORE.log(sess["username"], "QUICK_SCORE", f"MST {req.mst or '—'} → {rec['decision']}")
    return {
        "credit_score": rec["credit_score"], "risk_tier": rec["risk_tier"],
        "pd_band": rec["pd_band"], "dsr_group": rec["dsr_group"],
        "decision": rec["decision"], "flow": rec["flow"],
        "suggested_limit_vnd": rec["credit_limit_vnd"],
        "recommendation": {"approve": "Phê duyệt nhanh", "manual_review": "Xem xét thủ công",
                           "decline": "Khuyến nghị từ chối"}[rec["decision"]],
        "warnings": rec["warnings"],
    }


# ═══════════════════════════════════════════════════════ Admin / Audit ══════
@app.get("/api/admin/monitoring")
def admin_monitoring(sess=Depends(require_roles("admin"))):
    return STORE.aggregates()


@app.get("/api/admin/cases")
def admin_cases(q: str | None = None, sess=Depends(require_roles("admin"))):
    items = list(STORE.cases.values())
    if q:
        ql = q.strip().lower()
        items = [c for c in items if ql in c["customer_id"].lower()
                 or ql in c["company_name"].lower() or ql in c["mst"]]
    items = sorted(items, key=lambda c: c["timestamp"], reverse=True)[:80]
    return {"count": len(items), "cases": [_bank_summary(c) for c in items]}


@app.get("/api/admin/cases/{cid}/audit")
def admin_case_audit(cid: str, sess=Depends(require_roles("admin"))):
    rec = STORE.cases.get(cid)
    if not rec:
        raise HTTPException(404, "Không tìm thấy hồ sơ.")
    STORE.log(sess["username"], "AUDIT_CASE", f"Kiểm toán hồ sơ {cid}")
    payload = {k: v for k, v in rec["feature_values"].items() if v is not None}
    missing = [k for k, v in rec["feature_values"].items() if v is None]
    sources = sorted({SOURCE_LABELS.get(FEATURE_DICT.get(k, {}).get("source", "identity"),
                                         "Khác") for k in payload})
    shap_pos = [r for r in rec["top_reasons"] if r["direction"] == "decrease_risk"]
    shap_neg = [r for r in rec["top_reasons"] if r["direction"] == "increase_risk"]
    return {
        "customer_id": cid, "company_name": rec["company_name"], "mst": rec["mst"],
        "input_payload": payload, "missing_data": missing,
        "data_sources_used": sources,
        "model_output": {
            "credit_score": rec["credit_score"], "p_bad": rec["p_bad"],
            "pd_band": rec["pd_band"], "risk_tier": rec["risk_tier"],
            "dsr_value": rec["dsr_value"], "dsr_group": rec["dsr_group"],
            "suggested_limit_vnd": rec["credit_limit_vnd"], "decision": rec["decision"],
            "flow": rec["flow"],
        },
        "rule_engine_result": {
            "active_version": STORE.active_rules()["version"],
            "fraud_hard_stop": rec["hard_decline"],
            "applied_thresholds": STORE.active_rules()["rules"],
        },
        "shap": {
            "top_positive": [{"label": r["label"], "feature": r["feature"],
                              "shap_value": r["shap_value"],
                              "value": rec["feature_values"].get(r["feature"])}
                             for r in shap_pos],
            "top_negative": [{"label": r["label"], "feature": r["feature"],
                              "shap_value": r["shap_value"],
                              "value": rec["feature_values"].get(r["feature"])}
                             for r in shap_neg],
        },
        "timestamp": rec["timestamp"], "model_version": rec["model_version"],
        "decision_version": rec["decision_version"],
        "accessed_by": sess["display_name"],
        "override_history": rec["override_history"],
        "actual_default": rec["actual_default"],
    }


@app.get("/api/admin/rule-engine")
def admin_rules(sess=Depends(require_roles("admin"))):
    return {
        "active": STORE.active_rules(),
        "pending": STORE.pending_change,
        "history": [{"version": v["version"], "status": v["status"],
                     "proposed_by": v["proposed_by"], "approved_by": v["approved_by"],
                     "created_at": v["created_at"]} for v in STORE.rule_versions],
    }


class RuleProposeReq(BaseModel):
    rules: dict


@app.post("/api/admin/rule-engine/propose")
def admin_rules_propose(req: RuleProposeReq, sess=Depends(require_roles("admin"))):
    return STORE.propose_rule_change(req.rules, maker=sess["display_name"])


class RuleApproveReq(BaseModel):
    approver: str | None = None


@app.post("/api/admin/rule-engine/approve")
def admin_rules_approve(req: RuleApproveReq, sess=Depends(require_roles("admin"))):
    # second-approver identity (maker-checker); default to a distinct checker name
    checker = (req.approver or "Kiểm soát viên cấp 2").strip()
    try:
        return STORE.approve_rule_change(checker=checker)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/admin/access-control")
def admin_access_control(sess=Depends(require_roles("admin"))):
    Y, N, L = "Có", "Không", "Hạn chế"
    rows = [
        ("Nộp hồ sơ", Y, Y, Y), ("Xem kết quả rút gọn", Y, Y, Y),
        ("Xem điểm tín dụng", N, Y, Y), ("Xem hạng rủi ro", N, Y, Y),
        ("Xem lý do theo tiêu chí", N, Y, Y), ("Xem giá trị SHAP", N, N, Y),
        ("Xem cấu hình rule engine", N, N, Y), ("Sửa cấu hình rule", N, N, Y),
        ("Xem nhật ký kiểm toán", N, N, Y), ("Ghi đè thủ công", N, L, "Có (kiểm soát)"),
    ]
    return {
        "columns": ["Tính năng", "Khách hàng", "RM / Cán bộ TD", "Admin / Kiểm toán"],
        "rows": [{"feature": r[0], "customer": r[1], "bank": r[2], "admin": r[3]} for r in rows],
    }


@app.get("/api/admin/integration")
def admin_integration(sess=Depends(require_roles("admin"))):
    return {
        "connections": [
            {"name": "LOS / RLOS / CLOS", "status": "active", "latency_ms": 210},
            {"name": "CMS handoff", "status": "active", "latency_ms": 180},
            {"name": "RM Portal / Sale Hub API", "status": "active", "latency_ms": 240},
            {"name": "Nền tảng cho vay số (Digital Lending)", "status": "active", "latency_ms": 260},
            {"name": "SCF Platform", "status": "active", "latency_ms": 305},
            {"name": "API Scoring Service", "status": "active", "latency_ms": 95},
        ],
        "last_latency_ms": 240, "failed_requests_today": 3, "uptime_pct": 99.95,
    }


@app.get("/api/admin/audit-logs")
def admin_audit_logs(sess=Depends(require_roles("admin"))):
    return {"logs": STORE.audit_log[:100]}


# convenience: form option metadata used by the frontend
@app.get("/api/meta")
def meta():
    return {
        "industries": ["retail", "services", "manufacturing", "F&B", "agriculture", "wholesale"],
        "industries_vi": {"retail": "Bán lẻ", "services": "Dịch vụ",
                          "manufacturing": "Sản xuất", "F&B": "Ẩm thực (F&B)",
                          "agriculture": "Nông nghiệp", "wholesale": "Bán buôn"},
        "regions": ["HCMC", "Hanoi", "Danang", "HaiPhong", "CanTho", "other"],
        "decision_thresholds": DECISION_THRESHOLDS,
        "dsr_thresholds": DSR_THR, "limit_factor": LIMIT_FACTOR,
        "base_limit_vnd": BASE_LIMIT_VND, "model_version": MODEL_VERSION,
    }
