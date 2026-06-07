"""Layer 3A — Vận hành & Dấu chân số (190 điểm)"""

import numpy as np
from scorer.models import LayerResult


def score(einvoices: dict, bank: dict, contracts: dict) -> LayerResult:
    detail = {}

    # ── E-Invoice Vitality (60đ) ──────────────────────────────────────────────
    if not einvoices.get("available"):
        detail["einvoice_vitality"] = {"diem": 0, "max": 60, "gia_tri": "N/A", "mo_ta": "Không có dữ liệu HĐĐT"}
    else:
        active = einvoices.get("so_thang_co_hoa_don", 0)
        monthly = einvoices.get("du_lieu_theo_thang", [])
        revs = [m["tong_doanh_thu_mn_vnd"] for m in monthly if m["tong_doanh_thu_mn_vnd"] > 0]

        norm_slope = 0.0
        if len(revs) >= 3:
            x = np.arange(len(revs))
            slope = float(np.polyfit(x, revs, 1)[0])
            mean_rev = float(np.mean(revs))
            norm_slope = slope / mean_rev if mean_rev > 0 else 0.0

        if active >= 11 and norm_slope > 0.01:
            d = 60;  mo_ta = f"Active {active}/12 tháng, xu hướng tăng"
        elif active >= 9 and norm_slope >= -0.01:
            d = 40;  mo_ta = f"Active {active}/12 tháng, ổn định"
        elif active >= 6:
            d = 20;  mo_ta = f"Active {active}/12 tháng"
        else:
            d = 5;   mo_ta = f"Active {active}/12 tháng — thưa hoặc giảm"
        detail["einvoice_vitality"] = {
            "diem": d, "max": 60,
            "gia_tri": f"{active} tháng · slope={norm_slope:+.3f}",
            "mo_ta": mo_ta,
        }

    # ── Customer Concentration (50đ) ─────────────────────────────────────────
    if not einvoices.get("available"):
        detail["customer_concentration"] = {"diem": 0, "max": 50, "gia_tri": "N/A", "mo_ta": "Không có dữ liệu HĐĐT"}
    else:
        conc = einvoices.get("customer_concentration_top5_pct", 100)
        if conc < 40:
            d = 50;  mo_ta = "< 40% — đa dạng khách hàng"
        elif conc < 60:
            d = 30;  mo_ta = "40–60%"
        elif conc < 80:
            d = 15;  mo_ta = "60–80% — phụ thuộc nhất định"
        else:
            d = 0;   mo_ta = "> 80% — phụ thuộc khách hàng cao"
        detail["customer_concentration"] = {"diem": d, "max": 50, "gia_tri": f"{conc:.1f}%", "mo_ta": mo_ta}

    # ── Anchor-Supplier Network (60đ) ─────────────────────────────────────────
    if not contracts.get("available"):
        d = 10;  mo_ta = "Không xác định — không có dữ liệu hợp đồng"
        detail["anchor_network"] = {"diem": d, "max": 60, "gia_tri": "N/A", "mo_ta": mo_ta}
    else:
        all_contracts = contracts.get("hop_dong", [])
        long_term = [c for c in all_contracts if c.get("thoi_han_thang", 0) >= 24]
        n_anchors = len(long_term)
        if n_anchors >= 3:
            d = 60;  mo_ta = f"≥ 3 anchor dài hạn"
        elif n_anchors >= 1:
            d = 35;  mo_ta = f"{n_anchors} anchor"
        else:
            d = 10;  mo_ta = "Không có anchor dài hạn"
        detail["anchor_network"] = {"diem": d, "max": 60, "gia_tri": f"{n_anchors} anchor ≥24T", "mo_ta": mo_ta}

    # ── Bank Cash Flow Stability (20đ) ───────────────────────────────────────
    if not bank.get("available"):
        detail["cashflow_stability"] = {"diem": 0, "max": 20, "gia_tri": "N/A", "mo_ta": "Không có sao kê ngân hàng"}
    else:
        cv = bank.get("cashflow_cv", 1.0)
        io = bank.get("inflow_outflow_ratio", 0.0)
        if cv < 0.20 and io >= 1.0:
            d = 20;  mo_ta = "CV thấp, dòng tiền vào > ra"
        elif cv < 0.40:
            d = 12;  mo_ta = "CV trung bình"
        else:
            d = 2;   mo_ta = "CV cao hoặc dòng tiền ra > vào"
        detail["cashflow_stability"] = {
            "diem": d, "max": 20,
            "gia_tri": f"CV={cv:.2f} · I/O={io:.2f}",
            "mo_ta": mo_ta,
        }

    total = sum(v["diem"] for v in detail.values())
    available = einvoices.get("available") or bank.get("available") or contracts.get("available")
    return LayerResult(layer="L3A_OPS", diem_tho=total, diem_max=190, available=bool(available), chi_tiet=detail)
