"""Layer 1 — CIC: Lịch sử tín dụng (200 điểm)"""

from scorer.models import LayerResult


def score(cic: dict) -> LayerResult:
    if not cic.get("available"):
        return LayerResult(
            layer="L1_CIC", diem_tho=0, diem_max=200,
            available=False,
            chi_tiet={"ly_do": cic.get("ly_do", "Không có dữ liệu CIC")},
        )

    detail = {}

    # ── Nhóm nợ hiện tại (80đ) ───────────────────────────────────────────────
    g = cic.get("debt_group_current", 1)
    if g == 1:
        d = 80
    elif g == 2:
        d = 40
    elif g == 3:
        d = 10
    else:
        d = 0   # G4-5 → hard stop handled in rating.py
    detail["nhom_no_hien_tai"] = {"diem": d, "max": 80, "gia_tri": f"Nhóm {g}", "mo_ta": f"Nhóm nợ {g}"}

    # ── Lịch sử nợ xấu 24T (40đ) ────────────────────────────────────────────
    history = cic.get("debt_group_history_24m", [])
    worst = cic.get("worst_debt_group_24m", 1)
    bad_count = sum(1 for x in history if x >= 2)
    if worst <= 1:
        d = 40;  mo_ta = "Không có nợ xấu"
    elif worst == 2 and bad_count <= 1:
        d = 25;  mo_ta = "Từng nhóm 2 — 1 lần"
    elif worst == 2:
        d = 15;  mo_ta = "Nhóm 2 nhiều lần"
    else:
        d = 0;   mo_ta = "Từng nhóm 3+"
    detail["lich_su_no_xau_24t"] = {"diem": d, "max": 40, "gia_tri": f"Worst G{worst} ({bad_count} lần)", "mo_ta": mo_ta}

    # ── Credit utilization (40đ) ─────────────────────────────────────────────
    util = cic.get("credit_utilization_pct", 50)
    if util < 50:
        d = 40;  mo_ta = "< 50%"
    elif util < 80:
        d = 25;  mo_ta = "50–80%"
    elif util <= 100:
        d = 10;  mo_ta = "80–100%"
    else:
        d = 0;   mo_ta = "> 100% — vượt hạn mức"
    detail["credit_utilization"] = {"diem": d, "max": 40, "gia_tri": f"{util:.1f}%", "mo_ta": mo_ta}

    # ── Số TCTD (25đ) ────────────────────────────────────────────────────────
    n = cic.get("num_financial_institutions", 1)
    if n <= 3:
        d = 25;  mo_ta = "1–3 TCTD"
    elif n <= 5:
        d = 15;  mo_ta = "4–5 TCTD"
    else:
        d = 5;   mo_ta = f"> 5 TCTD — dấu hiệu vay chồng"
    detail["so_tctd"] = {"diem": d, "max": 25, "gia_tri": f"{n} TCTD", "mo_ta": mo_ta}

    # ── Tăng trưởng dư nợ 12T (15đ) ─────────────────────────────────────────
    growth = cic.get("debt_growth_12m_pct", 10)
    if growth < 30:
        d = 15;  mo_ta = "< 30%"
    elif growth < 70:
        d = 8;   mo_ta = "30–70%"
    else:
        d = 0;   mo_ta = "> 70% — over-leveraging"
    detail["tang_truong_du_no"] = {"diem": d, "max": 15, "gia_tri": f"{growth:.1f}%", "mo_ta": mo_ta}

    total = sum(v["diem"] for v in detail.values())
    return LayerResult(layer="L1_CIC", diem_tho=total, diem_max=200, available=True, chi_tiet=detail)
