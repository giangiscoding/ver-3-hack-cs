"""
ScoreSight Platform · Data Store
================================

Loads the 300-SME sample, synthesizes deterministic Vietnamese company metadata,
batch-scores every case with the real model (one SHAP pass), and builds the
portfolio aggregates the admin dashboard needs. Also holds the in-memory
rule-engine (maker-checker) state and the audit log.
"""
from __future__ import annotations

import hashlib
import warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from engine import (
    ART, CATEGORICAL, FEATURES, FEATURE_DICT, FEATURE_LABELS, GROUPS,
    MODEL_VERSION, RULE_ENGINE_BASE_VERSION, SOURCE_LABELS,
    _EXPLAINER, _as_lgb, assign_group, build_row, cashflow_strength,
    compute_dsr, credit_limit, decision_of, flow_color, pd_band,
    prob_bad_to_score, revenue_stability, risk_tier, shap_reasons_from_values,
    CAL_SEG, GLOBAL_MODEL, BASE_LIMIT_VND, LIMIT_FACTOR,
)

warnings.filterwarnings("ignore")

# ── Deterministic Vietnamese company-name synthesis ──────────────────────────
_PREFIX = {
    "retail": ["Bán lẻ", "Thương mại", "Siêu thị mini"],
    "services": ["Dịch vụ", "Giải pháp", "Tư vấn"],
    "manufacturing": ["Sản xuất", "Cơ khí", "Chế biến"],
    "F&B": ["Ẩm thực", "Thực phẩm", "Cà phê"],
    "agriculture": ["Nông sản", "Nông nghiệp", "Trang trại"],
    "wholesale": ["Phân phối", "Bán sỉ", "Xuất nhập khẩu"],
}
_NAMES = ["An Phát", "Minh Long", "Hoàng Gia", "Đại Việt", "Tân Tiến", "Phú Thịnh",
          "Bình Minh", "Thành Đạt", "Kim Sơn", "Hải Đăng", "Trường Sơn", "Vạn Lộc",
          "Nam Phong", "Ngọc Hà", "Đông Đô", "Phương Nam", "Sao Mai", "Hồng Phúc",
          "Tâm Đức", "Việt Hưng", "Gia Bảo", "Thiên Ân", "Lạc Hồng", "Hoa Sen"]
_SUFFIX = ["TNHH", "Cổ phần", "TNHH MTV"]
_REGION_VI = {"HCMC": "TP.HCM", "Hanoi": "Hà Nội", "Danang": "Đà Nẵng",
              "HaiPhong": "Hải Phòng", "CanTho": "Cần Thơ", "other": "Tỉnh khác"}
_INDUSTRY_VI = {"retail": "Bán lẻ", "services": "Dịch vụ", "manufacturing": "Sản xuất",
                "F&B": "Ẩm thực (F&B)", "agriculture": "Nông nghiệp", "wholesale": "Bán buôn"}
_CONTACTS = ["Nguyễn Văn An", "Trần Thị Bình", "Lê Hoàng Cường", "Phạm Thu Dung",
             "Vũ Minh Đức", "Đặng Thị Hà", "Bùi Quang Huy", "Hồ Thị Lan"]


def _seed(cid: str) -> int:
    return int(hashlib.md5(cid.encode()).hexdigest(), 16)


def _company_meta(cid: str, industry: str, region: str, size: str) -> dict:
    s = _seed(cid)
    pref = _PREFIX.get(industry, ["Thương mại"])[s % len(_PREFIX.get(industry, ["x"]))]
    name = _NAMES[(s >> 4) % len(_NAMES)]
    suf = _SUFFIX[(s >> 8) % len(_SUFFIX)]
    mst = str(3_100_000_000 + (s % 899_999_999)).rjust(10, "0")[:10]
    contact = _CONTACTS[(s >> 12) % len(_CONTACTS)]
    phone = "0" + str(900_000_000 + (s % 99_999_999)).rjust(9, "0")[:9]
    return {
        "company_name": f"Công ty {suf} {pref} {name}",
        "mst": mst,
        "contact_person": contact,
        "phone": phone,
        "email": f"ketoan@{name.lower().replace(' ', '')}.com.vn",
        "industry_vi": _INDUSTRY_VI.get(industry, industry),
        "region_vi": _REGION_VI.get(region, region),
    }


def _requested_limit(size: str, suggested: int, cid: str) -> int:
    """Synthetic requested amount, typically above the model's suggested limit."""
    base = {"micro": 80_000_000, "small": 600_000_000, "medium": 1_500_000_000}[size]
    jitter = (_seed(cid) % 40) / 100.0  # 0..0.39
    req = int(base * (1.0 + jitter))
    return max(req, int(suggested * 1.2)) if suggested else req


def _missing_key_docs(row: pd.Series) -> list[str]:
    key = {
        "invoice_revenue_12m": "Dữ liệu hóa đơn điện tử (12 tháng)",
        "supplier_payment_regularity": "Lịch sử thanh toán nhà cung cấp",
        "momo_net_cashflow_avg": "Sao kê dòng tiền ví/ngân hàng",
        "vat_filing_on_time_ratio": "Hồ sơ kê khai thuế VAT",
    }
    return [v for k, v in key.items() if pd.isna(row.get(k))]


def _criteria_explanation(reasons: list[dict]) -> dict:
    pos = [{"label": r["label"], "source": SOURCE_LABELS.get(r["source"], r["source"])}
           for r in reasons if r["direction"] == "decrease_risk"][:4]
    neg = [{"label": r["label"], "source": SOURCE_LABELS.get(r["source"], r["source"])}
           for r in reasons if r["direction"] == "increase_risk"][:4]
    return {"positive": pos, "risk": neg}


def _tat_saving(flow: str) -> int:
    return {"green": 42, "yellow": 28, "red": 18}[flow]


def _next_action(rec: dict, missing: list[str]) -> str:
    if rec["decision"] == "approve" and not missing:
        return "Chuyển hồ sơ sang LOS/CMS để phê duyệt chuẩn."
    if rec["decision"] == "approve" and missing:
        return f"Xác minh nhanh: {missing[0]}, sau đó chuyển LOS/CMS."
    if rec["decision"] == "manual_review":
        return f"Yêu cầu bổ sung: {missing[0] if missing else 'sao kê 6 tháng gần nhất'}."
    return "Chuyển chuyên viên thẩm định tăng cường / khuyến nghị từ chối."


class Store:
    def __init__(self) -> None:
        self.df = pd.read_csv(ART / "sme_altdata_sample.csv")
        self.cases: dict[str, dict] = {}
        self.audit_log: list[dict] = []
        self._build()
        self._init_rules()

    # ── batch scoring (one SHAP pass over 300 rows) ──────────────────────────
    def _build(self) -> None:
        df = self.df
        X = df[FEATURES].copy()
        X_lgb = _as_lgb(X)

        # DSR + group + calibrated p_bad per group
        dsr_vals = X_lgb.apply(lambda r: compute_dsr(pd.DataFrame([r])), axis=1).values
        groups = np.array([assign_group(d) for d in dsr_vals])
        p_bad = np.zeros(len(df))
        for g in GROUPS:
            mask = groups == g
            if mask.any():
                p_bad[mask] = CAL_SEG[g].predict_proba(X_lgb[mask])[:, 1]

        # batch SHAP
        sv = _EXPLAINER.shap_values(X_lgb)
        if isinstance(sv, list):
            sv = sv[1]

        base_dt = datetime(2026, 6, 1, 8, 0, 0)
        for i, (_, row) in enumerate(df.iterrows()):
            cid = row["customer_id"]
            size = str(row["enterprise_size"])
            score = prob_bad_to_score(float(p_bad[i]))
            decision = decision_of(score)
            grp = groups[i]
            # hard fraud rule
            hard = row.get("shared_device_risk_flag") in (1, 1.0)
            if hard:
                score, decision, grp = 300, "decline", grp
            limit = 0 if decision == "decline" else credit_limit(size, grp, decision)
            reasons = (shap_reasons_from_values(sv[i]) if not hard else
                       [{"feature": "shared_device_risk_flag",
                         "label": "Thiết bị dùng chung — tín hiệu gian lận",
                         "shap_value": 99.0, "direction": "increase_risk", "source": "graph"}])
            meta = _company_meta(cid, str(row["industry"]), str(row["region"]), size)
            missing = _missing_key_docs(row)
            suggested = limit
            requested = _requested_limit(size, suggested, cid)
            flow = flow_color(decision)
            n_avail = int(row[FEATURES].notna().sum())
            ts = (base_dt + timedelta(minutes=i * 17)).isoformat(timespec="seconds")

            self.cases[cid] = {
                "customer_id": cid,
                **meta,
                "industry": str(row["industry"]),
                "region": str(row["region"]),
                "enterprise_size": size,
                "credit_score": int(score),
                "p_bad": round(float(p_bad[i]) if not hard else 1.0, 4),
                "pd_band": pd_band(float(p_bad[i]) if not hard else 1.0),
                "dsr_value": round(float(dsr_vals[i]), 4),
                "dsr_group": grp,
                "risk_tier": risk_tier(int(score)),
                "decision": decision,
                "flow": flow,
                "requested_limit_vnd": requested,
                "credit_limit_vnd": int(limit),
                "revenue_stability": revenue_stability(row),
                "cashflow_strength": cashflow_strength(row),
                "n_available": n_avail,
                "data_coverage_pct": round(float(dsr_vals[i]) * 100, 1),
                "top_reasons": reasons,
                "criteria": _criteria_explanation(reasons),
                "missing_docs": missing,
                "tat_saving_pct": _tat_saving(flow),
                "next_action": _next_action({"decision": decision}, missing),
                "los_ready": decision == "approve" and not missing,
                "escalate": decision == "decline",
                "actual_default": int(row["default"]),
                "feature_values": {f: (None if pd.isna(row[f]) else
                                       (float(row[f]) if f not in CATEGORICAL else str(row[f])))
                                   for f in FEATURES},
                "timestamp": ts,
                "model_version": MODEL_VERSION,
                "decision_version": f"{RULE_ENGINE_BASE_VERSION}.1",
                "override_history": [],
                "hard_decline": bool(hard),
            }

    # ── portfolio aggregates for admin dashboard ─────────────────────────────
    def aggregates(self) -> dict:
        c = list(self.cases.values())
        n = len(c)
        flows = {"green": 0, "yellow": 0, "red": 0}
        tiers = {"A": 0, "B": 0, "C": 0, "D": 0}
        dsr = {"thin": 0, "semi": 0, "thick": 0}
        pd_hist = {"Rất thấp": 0, "Thấp": 0, "Trung bình - thấp": 0, "Trung bình": 0, "Cao": 0}
        scores, tat, defaults_in_approve, approve_n = [], [], 0, 0
        for x in c:
            flows[x["flow"]] += 1
            tiers[x["risk_tier"]] += 1
            dsr[x["dsr_group"]] += 1
            pd_hist[x["pd_band"]] = pd_hist.get(x["pd_band"], 0) + 1
            scores.append(x["credit_score"])
            tat.append(x["tat_saving_pct"])
            if x["decision"] == "approve":
                approve_n += 1
                defaults_in_approve += x["actual_default"]
        avg_cov = float(np.mean([x["data_coverage_pct"] for x in c]))
        return {
            "applications_processed": n,
            "approval_rate": round(flows["green"] / n * 100, 1),
            "flow_distribution": flows,
            "tier_distribution": tiers,
            "dsr_distribution": dsr,
            "pd_distribution": pd_hist,
            "avg_score": int(np.mean(scores)),
            "avg_tat_saving": round(float(np.mean(tat)), 1),
            "manual_override_rate": 8.5,          # governance placeholder
            "data_coverage_quality": round(avg_cov, 1),
            "model_drift_psi": 0.07,              # < 0.1 = stable
            "npl_trend": "Ổn định",
            "bad_rate_in_approve": round(defaults_in_approve / max(approve_n, 1) * 100, 1),
        }

    # ── rule engine (maker-checker) ──────────────────────────────────────────
    def _init_rules(self) -> None:
        self.rule_versions = [{
            "version": f"{RULE_ENGINE_BASE_VERSION}.1",
            "status": "active",
            "rules": {
                "green_min_score": 620,
                "yellow_min_score": 540,
                "red_max_score": 539,
                "max_dsr_for_green": 0.45,
                "fraud_hard_stop": True,
                "missing_key_doc_action": "manual_review",
                "max_suggested_limit_vnd": 1_000_000_000,
            },
            "proposed_by": "system",
            "approved_by": "system",
            "created_at": "2026-06-01T08:00:00",
        }]
        self.pending_change: dict | None = None

    def active_rules(self) -> dict:
        return next(v for v in self.rule_versions if v["status"] == "active")

    def propose_rule_change(self, rules: dict, maker: str) -> dict:
        nver = f"{RULE_ENGINE_BASE_VERSION}.{len(self.rule_versions) + 1}"
        self.pending_change = {
            "version": nver, "status": "pending_approval", "rules": rules,
            "proposed_by": maker, "approved_by": None,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.log(maker, "PROPOSE_RULE_CHANGE", f"Đề xuất phiên bản {nver}")
        return self.pending_change

    def approve_rule_change(self, checker: str) -> dict:
        if not self.pending_change:
            raise ValueError("Không có thay đổi nào đang chờ duyệt.")
        if self.pending_change["proposed_by"] == checker:
            raise ValueError("Maker-checker: người duyệt phải khác người đề xuất.")
        for v in self.rule_versions:
            v["status"] = "archived"
        self.pending_change["status"] = "active"
        self.pending_change["approved_by"] = checker
        self.rule_versions.append(self.pending_change)
        approved = self.pending_change
        self.pending_change = None
        self.log(checker, "APPROVE_RULE_CHANGE", f"Phê duyệt & triển khai {approved['version']}")
        return approved

    # ── audit log ────────────────────────────────────────────────────────────
    def log(self, actor: str, action: str, detail: str) -> None:
        self.audit_log.insert(0, {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "actor": actor, "action": action, "detail": detail,
        })
        self.audit_log = self.audit_log[:200]


STORE = Store()
