"""
ScoreSight Platform · Scoring Engine
====================================

Mirrors the deployed T5 /score pipeline (hard fraud rule -> DSR -> calibrated
LightGBM head -> PDO score -> decision -> DSR-tiered limit -> SHAP reasons) and
adds the derived banking artefacts the multi-portal UI needs (risk tier, PD band,
criteria-level explanation, operational benefit panel, audit payload).

Single code path: the 300 sample SMEs and any newly submitted application are
scored identically.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ART = Path(__file__).resolve().parent / "artifacts"

# ── PDO scorecard (from t4_training/score_mapping.py) ────────────────────────
PDO, BASE_SCORE, BASE_ODDS = 50, 600, 9.0
SCORE_MIN, SCORE_MAX = 300, 850
_FACTOR = PDO / np.log(2)
_OFFSET = BASE_SCORE - _FACTOR * np.log(BASE_ODDS)
DECISION_THRESHOLDS = {"approve": 620, "review": 540}


def prob_bad_to_score(p_bad: float) -> int:
    p = float(np.clip(p_bad, 1e-6, 1 - 1e-6))
    odds_good = (1 - p) / p
    score = _OFFSET + _FACTOR * np.log(odds_good)
    return int(np.clip(round(score), SCORE_MIN, SCORE_MAX))


# ── Artefacts ────────────────────────────────────────────────────────────────
_bundle = joblib.load(ART / "scoresight_bundle.joblib")
FEATURES: list[str] = _bundle["features"]
NUMERIC: list[str] = _bundle["numeric"]
CATEGORICAL: list[str] = _bundle["categorical"]
GLOBAL_MODEL = _bundle["global_model"]
CAL_SEG: dict = _bundle["cal_seg"]
LIMIT_FACTOR: dict = _bundle["limit_factor"]      # thin .5 / semi .75 / thick 1.0
GROUPS: list[str] = _bundle["groups"]

DSR_WEIGHTS = pd.Series(json.loads((ART / "weights_refined.json").read_text(encoding="utf-8")), dtype=float)
DSR_THR = json.loads((ART / "dsr_config.json").read_text(encoding="utf-8"))["dsr_thresholds"]
FEATURE_DICT = json.loads((ART / "feature_dictionary.json").read_text(encoding="utf-8"))

MODEL_VERSION = "v1.2.0"
RULE_ENGINE_BASE_VERSION = "2026.06"

BASE_LIMIT_VND: dict[str, int] = {
    "micro": 50_000_000,
    "small": 200_000_000,
    "medium": 1_000_000_000,
}

# SHAP explainer — built once
import shap  # noqa: E402

_EXPLAINER = shap.TreeExplainer(GLOBAL_MODEL)

# Vietnamese, business-friendly feature labels
FEATURE_LABELS: dict[str, str] = {
    "invoice_revenue_growth": "Tăng trưởng doanh thu hóa đơn",
    "supplier_payment_regularity": "Độ đều thanh toán nhà cung cấp",
    "gmv_growth_12m": "Tăng trưởng GMV 12 tháng",
    "unique_buyer_count": "Số khách mua độc nhất",
    "payroll_regularity": "Độ đều trả lương",
    "vat_filing_on_time_ratio": "Tỷ lệ nộp VAT đúng hạn",
    "buyer_diversity_score": "Mức đa dạng khách mua",
    "supplier_diversity_score": "Mức đa dạng nhà cung cấp",
    "return_rate": "Tỷ lệ hoàn trả đơn",
    "network_default_exposure": "Phơi nhiễm nợ xấu mạng lưới",
    "invoice_revenue_12m": "Doanh thu hóa đơn 12 tháng",
    "momo_net_cashflow_avg": "Dòng tiền ròng ví điện tử",
    "pos_volume_6m": "Khối lượng giao dịch POS 6 tháng",
    "shopee_gmv_3m": "GMV sàn TMĐT 3 tháng",
    "pagerank_score": "Vị thế trong mạng lưới (PageRank)",
    "seller_rating": "Đánh giá người bán",
    "delivery_success_rate": "Tỷ lệ giao hàng thành công",
    "logistics_return_rate": "Tỷ lệ hoàn hàng vận chuyển",
    "electricity_growth": "Tăng trưởng tiêu thụ điện",
    "electricity_consumption_avg": "Mức tiêu thụ điện trung bình",
    "utility_payment_on_time": "Thanh toán tiện ích đúng hạn",
    "shipment_count_monthly": "Số đơn vận chuyển hàng tháng",
    "shared_device_risk_flag": "Cờ thiết bị dùng chung (gian lận)",
    "facebook_engagement_rate": "Tỷ lệ tương tác Facebook",
    "facebook_page_age_months": "Tuổi trang Facebook",
    "google_review_count": "Số đánh giá Google",
    "google_avg_rating": "Điểm đánh giá Google trung bình",
    "business_age_months": "Tuổi doanh nghiệp (tháng)",
    "num_employees": "Số nhân viên",
    "order_count_monthly": "Số đơn hàng hàng tháng",
    "active_days_per_month": "Số ngày hoạt động/tháng",
    "invoice_cancel_rate": "Tỷ lệ hủy hóa đơn",
    "vat_filing_on_time_ratio ": "Tỷ lệ nộp VAT đúng hạn",
    "industry": "Ngành nghề",
    "region": "Khu vực",
    "enterprise_size": "Quy mô doanh nghiệp",
}

SOURCE_LABELS = {
    "ecommerce": "Sàn TMĐT",
    "payment": "Thanh toán số",
    "einvoice": "Hóa đơn điện tử",
    "utility": "Tiện ích (điện)",
    "logistics": "Vận chuyển",
    "digital_footprint": "Dấu chân số",
    "graph": "Mạng lưới đối tác",
    "identity": "Định danh DN",
}

DSR_GROUP_VI = {"thin": "Mỏng", "semi": "Trung bình", "thick": "Dày"}


# ── Helpers ──────────────────────────────────────────────────────────────────
def _as_lgb(X: pd.DataFrame) -> pd.DataFrame:
    X = X.copy()
    for c in CATEGORICAL:
        X[c] = X[c].astype("category")
    return X


def build_row(fields: dict) -> pd.DataFrame:
    row: dict[str, Any] = {f: np.nan for f in FEATURES}
    for k, v in fields.items():
        if k in row and v is not None and not (isinstance(v, float) and np.isnan(v)):
            row[k] = v
    return pd.DataFrame([row])


def compute_dsr(row: pd.DataFrame) -> float:
    shared = [f for f in DSR_WEIGHTS.index if f in row.columns]
    valid = row[shared].notna().astype(float).iloc[0]
    w = DSR_WEIGHTS[shared]
    return float((valid * w).sum() / w.sum())


def assign_group(dsr: float) -> str:
    if dsr <= DSR_THR["thin_max"]:
        return "thin"
    if dsr <= DSR_THR["semi_max"]:
        return "semi"
    return "thick"


def risk_tier(score: int) -> str:
    if score >= 700:
        return "A"
    if score >= 620:
        return "B"
    if score >= 540:
        return "C"
    return "D"


def pd_band(p_bad: float) -> str:
    if p_bad < 0.03:
        return "Rất thấp"
    if p_bad < 0.06:
        return "Thấp"
    if p_bad < 0.10:
        return "Trung bình - thấp"
    if p_bad < 0.20:
        return "Trung bình"
    return "Cao"


def flow_color(decision: str) -> str:
    return {"approve": "green", "manual_review": "yellow", "decline": "red"}[decision]


def decision_of(score: int) -> str:
    if score >= DECISION_THRESHOLDS["approve"]:
        return "approve"
    if score >= DECISION_THRESHOLDS["review"]:
        return "manual_review"
    return "decline"


def credit_limit(enterprise_size: str, dsr_group: str, decision: str) -> int:
    if decision == "decline":
        return 0
    base = BASE_LIMIT_VND.get(enterprise_size, BASE_LIMIT_VND["micro"])
    return int(base * LIMIT_FACTOR.get(dsr_group, 0.5))


def shap_reasons_from_values(vals: np.ndarray, n: int = 6) -> list[dict]:
    order = np.argsort(np.abs(vals))[::-1][:n]
    out = []
    for i in order:
        v = float(vals[i])
        fname = FEATURES[i]
        out.append({
            "feature": fname,
            "label": FEATURE_LABELS.get(fname, fname),
            "shap_value": round(v, 4),
            "direction": "increase_risk" if v > 0 else "decrease_risk",
            "source": FEATURE_DICT.get(fname, {}).get("source", "identity"),
        })
    return out


def _shap_for_row(X_lgb: pd.DataFrame) -> np.ndarray:
    sv = _EXPLAINER.shap_values(X_lgb)
    if isinstance(sv, list):
        sv = sv[1]
    return sv[0]


def revenue_stability(row: pd.Series) -> str:
    g = row.get("invoice_revenue_growth")
    if g is None or (isinstance(g, float) and np.isnan(g)):
        g = row.get("gmv_growth_12m")
    if g is None or (isinstance(g, float) and np.isnan(g)):
        return "Chưa đủ dữ liệu"
    if g >= 0.10:
        return "Ổn định / tăng"
    if g >= -0.05:
        return "Ổn định"
    return "Biến động"


def cashflow_strength(row: pd.Series) -> str:
    sp = row.get("supplier_payment_regularity")
    if sp is None or (isinstance(sp, float) and np.isnan(sp)):
        return "Chưa đủ dữ liệu"
    if sp >= 0.8:
        return "Mạnh"
    if sp >= 0.6:
        return "Khá"
    return "Yếu"


# ── Core scoring (single source of truth) ────────────────────────────────────
def score_fields(customer_id: str, fields: dict) -> dict:
    """Full scoring of one applicant. Returns the rich internal record;
    role-specific shaping happens in the API layer."""
    warnings_: list[str] = []

    # Hard fraud rule
    if fields.get("shared_device_risk_flag") in (1, 1.0, "1", True):
        return {
            "customer_id": customer_id,
            "credit_score": 300,
            "p_bad": 1.0,
            "dsr_value": 0.0,
            "dsr_group": "thin",
            "enterprise_size": str(fields.get("enterprise_size", "micro")),
            "decision": "decline",
            "flow": "red",
            "risk_tier": "D",
            "pd_band": "Cao",
            "credit_limit_vnd": 0,
            "top_reasons": [{
                "feature": "shared_device_risk_flag",
                "label": "Thiết bị dùng chung — tín hiệu gian lận",
                "shap_value": 99.0, "direction": "increase_risk", "source": "graph",
            }],
            "revenue_stability": "—",
            "cashflow_strength": "—",
            "n_available": 0,
            "warnings": ["HARD DECLINE: shared_device_risk_flag = 1"],
            "hard_decline": True,
        }

    row = build_row(fields)
    enterprise_size = str(fields.get("enterprise_size", "micro"))
    if enterprise_size not in BASE_LIMIT_VND:
        enterprise_size = "micro"

    dsr = compute_dsr(row)
    group = assign_group(dsr)
    n_available = int(row[FEATURES].notna().sum(axis=1).iloc[0])
    if n_available < 8:
        warnings_.append(
            f"Chỉ có {n_available}/{len(FEATURES)} trường dữ liệu — độ tin cậy thấp, nên xem xét thủ công."
        )

    X_lgb = _as_lgb(row[FEATURES])
    if group in CAL_SEG:
        p_bad = float(CAL_SEG[group].predict_proba(X_lgb)[0, 1])
    else:
        p_bad = float(GLOBAL_MODEL.predict_proba(X_lgb)[0, 1])

    score = prob_bad_to_score(p_bad)
    decision = decision_of(score)
    limit = credit_limit(enterprise_size, group, decision)

    try:
        sv = _shap_for_row(X_lgb)
        reasons = shap_reasons_from_values(sv)
    except Exception as exc:  # pragma: no cover
        reasons = []
        warnings_.append(f"SHAP không tính được: {exc}")

    rser = row.iloc[0]
    return {
        "customer_id": customer_id,
        "credit_score": score,
        "p_bad": round(p_bad, 4),
        "dsr_value": round(dsr, 4),
        "dsr_group": group,
        "enterprise_size": enterprise_size,
        "decision": decision,
        "flow": flow_color(decision),
        "risk_tier": risk_tier(score),
        "pd_band": pd_band(p_bad),
        "credit_limit_vnd": limit,
        "top_reasons": reasons,
        "revenue_stability": revenue_stability(rser),
        "cashflow_strength": cashflow_strength(rser),
        "n_available": n_available,
        "warnings": warnings_,
        "hard_decline": False,
    }
