"""Layer 2 — BCTC: Sức khỏe tài chính (300 điểm)"""

from scorer.models import LayerResult


def score(bctc: dict) -> LayerResult:
    if not bctc.get("available"):
        return LayerResult(
            layer="L2_BCTC", diem_tho=0, diem_max=300,
            available=False,
            chi_tiet={"ly_do": bctc.get("ly_do", "Không có BCTC")},
        )

    detail = {}

    # ── DSCR (80đ) ───────────────────────────────────────────────────────────
    dscr = bctc.get("dscr", 0)
    if dscr >= 1.5:
        d = 80;  mo_ta = "≥ 1.5 — xuất sắc"
    elif dscr >= 1.25:
        d = 60;  mo_ta = "1.25–1.5 — tốt"
    elif dscr >= 1.0:
        d = 35;  mo_ta = "1.0–1.25 — đạt ngưỡng"
    else:
        d = 0;   mo_ta = "< 1.0 — không đủ trả nợ"
    detail["dscr"] = {"diem": d, "max": 80, "gia_tri": f"{dscr:.2f}", "mo_ta": mo_ta}

    # ── Đòn bẩy D/E (60đ) ───────────────────────────────────────────────────
    de = bctc.get("de_ratio", 99)
    if de < 1.0:
        d = 60;  mo_ta = "< 1.0 — thấp"
    elif de < 2.0:
        d = 40;  mo_ta = "1.0–2.0 — trung bình"
    elif de < 3.0:
        d = 20;  mo_ta = "2.0–3.0 — cao"
    else:
        d = 0;   mo_ta = "> 3.0 — rủi ro cao"
    detail["de_ratio"] = {"diem": d, "max": 60, "gia_tri": f"{de:.2f}x", "mo_ta": mo_ta}

    # ── EBITDA Margin (50đ) ──────────────────────────────────────────────────
    em = bctc.get("ebitda_margin_pct", 0)
    if em >= 15:
        d = 50;  mo_ta = "≥ 15%"
    elif em >= 10:
        d = 35;  mo_ta = "10–15%"
    elif em >= 5:
        d = 20;  mo_ta = "5–10%"
    elif em >= 0:
        d = 5;   mo_ta = "0–5% — biên thấp"
    else:
        d = 0;   mo_ta = "< 0 — thua lỗ"
    detail["ebitda_margin"] = {"diem": d, "max": 50, "gia_tri": f"{em:.1f}%", "mo_ta": mo_ta}

    # ── Cash Conversion Cycle (40đ) ──────────────────────────────────────────
    ccc = bctc.get("cash_conversion_cycle_days", 999)
    if ccc < 30:
        d = 40;  mo_ta = "< 30 ngày"
    elif ccc < 60:
        d = 28;  mo_ta = "30–60 ngày"
    elif ccc < 90:
        d = 15;  mo_ta = "60–90 ngày"
    else:
        d = 5;   mo_ta = "> 90 ngày — vốn lưu động chậm"
    detail["cash_conversion_cycle"] = {"diem": d, "max": 40, "gia_tri": f"{ccc} ngày", "mo_ta": mo_ta}

    # ── Current Ratio (40đ) ──────────────────────────────────────────────────
    cr = bctc.get("current_ratio", 0)
    if cr >= 2.0:
        d = 40;  mo_ta = "≥ 2.0"
    elif cr >= 1.5:
        d = 30;  mo_ta = "1.5–2.0"
    elif cr >= 1.0:
        d = 18;  mo_ta = "1.0–1.5"
    else:
        d = 5;   mo_ta = "< 1.0 — thanh khoản kém"
    detail["current_ratio"] = {"diem": d, "max": 40, "gia_tri": f"{cr:.2f}", "mo_ta": mo_ta}

    # ── CAGR doanh thu 3 năm (30đ) ───────────────────────────────────────────
    cagr = bctc.get("cagr_3y_pct", 0)
    if cagr > 15:
        d = 30;  mo_ta = "> 15%"
    elif cagr >= 5:
        d = 20;  mo_ta = "5–15%"
    elif cagr >= 0:
        d = 10;  mo_ta = "0–5%"
    else:
        d = 0;   mo_ta = "Âm — doanh thu giảm"
    detail["cagr_3y"] = {"diem": d, "max": 30, "gia_tri": f"{cagr:.1f}%", "mo_ta": mo_ta}

    total = sum(v["diem"] for v in detail.values())
    return LayerResult(layer="L2_BCTC", diem_tho=total, diem_max=300, available=True, chi_tiet=detail)
