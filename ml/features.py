"""
Feature extraction — chuyển CompanyBundle thành vector đặc trưng cho ML.

Mỗi cluster dùng một tập feature riêng phù hợp với nguồn dữ liệu có mặt.
LightGBM xử lý NaN natively → feature không có giá trị để là None/NaN.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from scorer.models import CompanyBundle

# ── Feature sets per cluster ──────────────────────────────────────────────────

META_FEATURES = [
    "meta_segment",           # 0=Micro, 1=Small, 2=Medium
    "meta_tuoi_dn_nam",       # tuổi pháp nhân
    "meta_log_so_nhan_vien",  # log(nhân viên) — giảm skewness
]

CIC_FEATURES = [
    "cic_debt_group",
    "cic_worst_24m",
    "cic_utilization_pct",
    "cic_num_tctd",
    "cic_debt_growth_pct",
]

BCTC_FEATURES = [
    "bctc_dscr",
    "bctc_de_ratio",
    "bctc_ebitda_margin_pct",
    "bctc_ccc_days",
    "bctc_current_ratio",
    "bctc_cagr_pct",
]

L3A_FEATURES = [
    "l3a_active_months",
    "l3a_customer_conc_top5_pct",
    "l3a_cashflow_cv",
    "l3a_inflow_outflow_ratio",
]

L3B_FEATURES = [
    "l3b_tax_on_time_months",
    "l3b_tax_cuong_che",
    "l3b_bhxh_debt_months",
    "l3b_utility_late_count",
    "l3b_bank_products",
]

L3C_FEATURES = [
    "l3c_env_violations",
    "l3c_labor_disputes",
    "l3c_legal_cases",
]

L3D_FEATURES = [
    "l3d_age_years",
    "l3d_has_hkd",
]

# Feature columns per cluster
CLUSTER_FEATURE_COLS: dict[str, list[str]] = {
    "FULL":    META_FEATURES + CIC_FEATURES + BCTC_FEATURES + L3A_FEATURES + L3B_FEATURES + L3C_FEATURES + L3D_FEATURES,
    "NO_CIC":  META_FEATURES +                BCTC_FEATURES + L3A_FEATURES + L3B_FEATURES + L3C_FEATURES + L3D_FEATURES,
    "NO_BCTC": META_FEATURES + CIC_FEATURES +                L3A_FEATURES + L3B_FEATURES + L3C_FEATURES + L3D_FEATURES,
    "L3_ONLY": META_FEATURES +                               L3A_FEATURES + L3B_FEATURES + L3C_FEATURES + L3D_FEATURES,
}

ALL_FEATURE_COLS = (
    META_FEATURES + CIC_FEATURES + BCTC_FEATURES +
    L3A_FEATURES + L3B_FEATURES + L3C_FEATURES + L3D_FEATURES
)


# ── Feature extraction ────────────────────────────────────────────────────────

def extract(bundle: CompanyBundle) -> dict:
    """
    Trả về dict feature đầy đủ (None cho giá trị thiếu).
    LightGBM handle NaN natively → None → NaN trong DataFrame.
    """
    f: dict = {}

    # ── Meta (luôn có) ────────────────────────────────────────────────────────
    seg = bundle.meta.get("phan_khuc", "Micro")
    f["meta_segment"] = {"Micro": 0, "Small": 1, "Medium": 2}.get(seg, 0)
    f["meta_tuoi_dn_nam"] = bundle.meta.get("tuoi_doanh_nghiep_nam")
    nv = bundle.meta.get("so_nhan_vien", 1) or 1
    f["meta_log_so_nhan_vien"] = float(np.log1p(nv))

    # ── CIC ──────────────────────────────────────────────────────────────────
    cic = bundle.cic
    if cic.get("available"):
        f["cic_debt_group"]      = cic.get("debt_group_current")
        f["cic_worst_24m"]       = cic.get("worst_debt_group_24m")
        f["cic_utilization_pct"] = cic.get("credit_utilization_pct")
        f["cic_num_tctd"]        = cic.get("num_financial_institutions")
        f["cic_debt_growth_pct"] = cic.get("debt_growth_12m_pct")
    else:
        for k in CIC_FEATURES:
            f[k] = None

    # ── BCTC ─────────────────────────────────────────────────────────────────
    bctc = bundle.bctc
    if bctc.get("available"):
        f["bctc_dscr"]             = bctc.get("dscr")
        f["bctc_de_ratio"]         = bctc.get("de_ratio")
        f["bctc_ebitda_margin_pct"]= bctc.get("ebitda_margin_pct")
        f["bctc_ccc_days"]         = bctc.get("cash_conversion_cycle_days")
        f["bctc_current_ratio"]    = bctc.get("current_ratio")
        f["bctc_cagr_pct"]         = bctc.get("cagr_3y_pct")
    else:
        for k in BCTC_FEATURES:
            f[k] = None

    # ── L3A: e-invoices ───────────────────────────────────────────────────────
    inv = bundle.einvoices
    if inv.get("available"):
        f["l3a_active_months"]           = inv.get("so_thang_co_hoa_don")
        f["l3a_customer_conc_top5_pct"]  = inv.get("customer_concentration_top5_pct")
    else:
        f["l3a_active_months"]          = None
        f["l3a_customer_conc_top5_pct"] = None

    # ── L3A: bank ────────────────────────────────────────────────────────────
    bank = bundle.bank
    if bank.get("available"):
        f["l3a_cashflow_cv"]         = bank.get("cashflow_cv")
        f["l3a_inflow_outflow_ratio"] = bank.get("inflow_outflow_ratio")
    else:
        f["l3a_cashflow_cv"]         = None
        f["l3a_inflow_outflow_ratio"] = None

    # ── L3B: compliance (luôn có) ────────────────────────────────────────────
    comp = bundle.compliance
    if comp.get("available"):
        thue = comp.get("thue", {})
        bhxh = comp.get("bhxh", {})
        tich = comp.get("tien_ich", {})
        ngnh = comp.get("ngan_hang", {})
        f["l3b_tax_on_time_months"] = thue.get("so_thang_dung_han_24t")
        f["l3b_tax_cuong_che"]      = int(thue.get("co_cuong_che", False))
        f["l3b_bhxh_debt_months"]   = bhxh.get("so_thang_no_bhxh")
        f["l3b_utility_late_count"] = tich.get("so_lan_tre_12t")
        f["l3b_bank_products"]      = ngnh.get("so_san_pham_dang_dung")
    else:
        for k in L3B_FEATURES:
            f[k] = None

    # ── L3C: ESG (luôn có) ───────────────────────────────────────────────────
    esg = bundle.esg
    if esg.get("available"):
        f["l3c_env_violations"] = esg.get("moi_truong", {}).get("so_vi_pham_24t")
        f["l3c_labor_disputes"] = esg.get("lao_dong", {}).get("so_tranh_chap_24t")
        f["l3c_legal_cases"]    = esg.get("phap_ly", {}).get("so_vu_kien_kinh_te_active")
    else:
        for k in L3C_FEATURES:
            f[k] = None

    # ── L3D: maturity (luôn có) ──────────────────────────────────────────────
    mat = bundle.maturity
    if mat.get("available"):
        f["l3d_age_years"] = mat.get("tuoi_phap_nhan_nam")
        f["l3d_has_hkd"]   = int(mat.get("co_hkd_tien_than", False))
    else:
        f["l3d_age_years"] = None
        f["l3d_has_hkd"]   = None

    return f


def to_dataframe(features: dict, cluster_id: str) -> pd.DataFrame:
    """
    Chuyển feature dict → DataFrame với đúng cột của cluster.
    None → NaN để LightGBM xử lý.
    """
    cols = CLUSTER_FEATURE_COLS[cluster_id]
    row = {col: features.get(col, None) for col in cols}
    df = pd.DataFrame([row], columns=cols)
    return df.astype(float)
