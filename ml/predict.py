"""
Inference — STACKED BLEND prediction + SHAP explanation.

  score = w_cluster · global(x) + (1 - w_cluster) · cluster_model(x)

Giải thích (top factors) lấy từ CLUSTER MODEL — dùng đúng bộ feature phù hợp với
nhóm dữ liệu, nên lời giải thích luôn dựa trên tín hiệu DN thực sự có.
"""

from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

from ml.features import extract, to_dataframe, CLUSTER_FEATURE_COLS, ALL_FEATURE_COLS
from ml import registry
from scorer.models import CompanyBundle

MODELS_DIR = Path(__file__).parent / "models"

FEATURE_DISPLAY = {
    "meta_segment": "Phân khúc (Micro/Small/Medium)",
    "meta_tuoi_dn_nam": "Tuổi pháp nhân (năm)",
    "meta_log_so_nhan_vien": "Quy mô nhân sự",
    "cic_debt_group": "CIC — Nhóm nợ hiện tại",
    "cic_worst_24m": "CIC — Nhóm nợ xấu nhất 24T",
    "cic_utilization_pct": "CIC — Tỷ lệ sử dụng hạn mức",
    "cic_num_tctd": "CIC — Số tổ chức tín dụng",
    "cic_debt_growth_pct": "CIC — Tăng trưởng dư nợ 12T",
    "bctc_dscr": "BCTC — DSCR (khả năng trả nợ)",
    "bctc_de_ratio": "BCTC — D/E (đòn bẩy tài chính)",
    "bctc_ebitda_margin_pct": "BCTC — Biên EBITDA (%)",
    "bctc_ccc_days": "BCTC — Chu kỳ chuyển đổi tiền mặt (ngày)",
    "bctc_current_ratio": "BCTC — Current ratio",
    "bctc_cagr_pct": "BCTC — Tăng trưởng doanh thu 3 năm",
    "l3a_active_months": "Hóa đơn điện tử — Số tháng hoạt động",
    "l3a_customer_conc_top5_pct": "Hóa đơn — Tập trung khách hàng top 5 (%)",
    "l3a_cashflow_cv": "Ngân hàng — Độ biến động dòng tiền (CV)",
    "l3a_inflow_outflow_ratio": "Ngân hàng — Tỷ lệ tiền vào/ra",
    "l3b_tax_on_time_months": "Thuế — Số tháng đúng hạn / 24T",
    "l3b_tax_cuong_che": "Thuế — Đang bị cưỡng chế",
    "l3b_bhxh_debt_months": "BHXH — Số tháng nợ BHXH",
    "l3b_utility_late_count": "Tiện ích — Số lần trễ 12T",
    "l3b_bank_products": "Ngân hàng — Số sản phẩm đang dùng",
    "l3c_env_violations": "ESG — Vi phạm môi trường 24T",
    "l3c_labor_disputes": "ESG — Tranh chấp lao động 24T",
    "l3c_legal_cases": "ESG — Vụ kiện kinh tế active",
    "l3d_age_years": "Maturity — Tuổi pháp nhân (năm)",
    "l3d_has_hkd": "Maturity — Có HKD tiền thân",
}


@lru_cache(maxsize=1)
def _load_blend_meta() -> dict:
    path = MODELS_DIR / "blend.json"
    if not path.exists():
        raise FileNotFoundError("Chưa train. Chạy: python -m ml.train")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_global():
    return joblib.load(MODELS_DIR / "global.pkl")


@lru_cache(maxsize=8)
def _load_cluster(cluster_id: str):
    return joblib.load(MODELS_DIR / f"cluster_{cluster_id}.pkl")


def predict(bundle: CompanyBundle, cluster_id: str, top_n: int = 3) -> tuple[int, list[dict]]:
    """
    Blended prediction + top-N yếu tố (SHAP từ cluster model).
    Returns: (score[0,1000], top_factors)
    """
    meta = _load_blend_meta()
    w = meta["weights"].get(cluster_id, 0.6)
    model_name = meta["model_types"][cluster_id]

    feats = extract(bundle)
    X_global  = pd.DataFrame([{c: feats.get(c) for c in ALL_FEATURE_COLS}], columns=ALL_FEATURE_COLS).astype(float)
    X_cluster = to_dataframe(feats, cluster_id)

    global_pred  = float(_load_global().predict(X_global)[0])
    cluster_pred = float(_load_cluster(cluster_id).predict(X_cluster)[0])
    blended = w * global_pred + (1 - w) * cluster_pred
    score = int(np.clip(round(blended), 0, 1000))

    # ── Top factors: SHAP từ cluster model (feature phù hợp nhóm) ──────────────
    top_factors = []
    try:
        cols = CLUSTER_FEATURE_COLS[cluster_id]
        contrib = registry.shap_contributions(_load_cluster(cluster_id), model_name, X_cluster, cols)
        idxs = np.argsort(-np.abs(contrib))[:top_n]
        for i in idxs:
            fname = cols[i]
            sv = float(contrib[i])
            fv = X_cluster.iloc[0, i]
            top_factors.append({
                "feature": fname,
                "display_name": FEATURE_DISPLAY.get(fname, fname),
                "shap_value": round(sv, 1),
                "feature_value": None if (fv is None or (isinstance(fv, float) and np.isnan(fv))) else round(float(fv), 3),
                "direction": "positive" if sv > 0 else "negative",
                "mo_ta": _shap_description(fname, sv, fv),
            })
    except Exception:
        top_factors = []

    return score, top_factors


def _shap_description(feature: str, shap_val: float, feature_val) -> str:
    direction = "tăng" if shap_val > 0 else "giảm"
    display = FEATURE_DISPLAY.get(feature, feature)
    fv = feature_val
    if fv is None or (isinstance(fv, float) and np.isnan(fv)):
        return f"{display} → {direction} điểm {abs(shap_val):.0f}đ"
    if feature == "cic_debt_group":
        return f"Nhóm nợ {int(fv)} → {direction} điểm {abs(shap_val):.0f}đ"
    if feature == "bctc_dscr":
        return f"DSCR={fv:.2f} → {direction} điểm {abs(shap_val):.0f}đ"
    if feature == "bctc_de_ratio":
        return f"D/E={fv:.2f} → {direction} điểm {abs(shap_val):.0f}đ"
    if feature == "l3b_tax_cuong_che" and fv == 1:
        return f"Đang bị cưỡng chế thuế → {direction} điểm {abs(shap_val):.0f}đ"
    return f"{display} → {direction} điểm {abs(shap_val):.0f}đ"


def models_available() -> bool:
    from scorer.cluster import ALL_CLUSTERS
    if not (MODELS_DIR / "global.pkl").exists() or not (MODELS_DIR / "blend.json").exists():
        return False
    return all((MODELS_DIR / f"cluster_{c}.pkl").exists() for c in ALL_CLUSTERS)
