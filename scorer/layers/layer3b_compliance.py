"""Layer 3B — Tuân thủ hành vi (160 điểm)"""

from scorer.models import LayerResult


def score(compliance: dict) -> LayerResult:
    if not compliance.get("available"):
        return LayerResult(
            layer="L3B_COMPLIANCE", diem_tho=0, diem_max=160,
            available=False,
            chi_tiet={"ly_do": "Không có dữ liệu tuân thủ"},
        )

    detail = {}

    # ── Tax Compliance (60đ) ──────────────────────────────────────────────────
    thue = compliance.get("thue", {})
    cuong_che = thue.get("co_cuong_che", False)
    tax_ok = thue.get("so_thang_dung_han_24t", 0)
    history = thue.get("lich_su_24_thang", [])
    severe_late = [m for m in history if m.get("so_ngay_tre", 0) > 30]
    late_count = sum(1 for m in history if m.get("trang_thai") == "tre_han")

    if cuong_che:
        d = 0;   mo_ta = "Đang bị cưỡng chế — HARD STOP trần BB"
    elif tax_ok == 24 and not severe_late:
        d = 60;  mo_ta = "Đúng hạn 24/24 tháng"
    elif len(severe_late) == 0 and late_count <= 2:
        d = 35;  mo_ta = f"Trễ ≤ 30 ngày, {late_count} lần"
    elif tax_ok >= 18:
        d = 10;  mo_ta = "Có nợ thuế đang xử lý"
    else:
        d = 0;   mo_ta = "Tuân thủ kém"
    detail["tax_compliance"] = {
        "diem": d, "max": 60,
        "gia_tri": f"{tax_ok}/24 tháng đúng hạn",
        "mo_ta": mo_ta,
    }

    # ── BHXH Compliance (50đ) ────────────────────────────────────────────────
    bhxh = compliance.get("bhxh", {})
    debt_months = bhxh.get("so_thang_no_bhxh", 0)
    if debt_months == 0:
        d = 50;  mo_ta = "Không nợ BHXH"
    elif debt_months <= 2:
        d = 25;  mo_ta = f"Nợ {debt_months} tháng"
    elif debt_months <= 6:
        d = 8;   mo_ta = f"Nợ {debt_months} tháng — đáng lo"
    else:
        d = 0;   mo_ta = f"Nợ {debt_months} tháng — leading indicator stress"
    detail["bhxh_compliance"] = {"diem": d, "max": 50, "gia_tri": f"Nợ {debt_months} tháng", "mo_ta": mo_ta}

    # ── Utility Compliance (30đ) ──────────────────────────────────────────────
    tien_ich = compliance.get("tien_ich", {})
    late_util = tien_ich.get("so_lan_tre_12t", 0)
    if late_util == 0:
        d = 30;  mo_ta = "Auto-debit đều, không trễ"
    elif late_util <= 2:
        d = 18;  mo_ta = f"{late_util} lần trễ"
    else:
        d = 5;   mo_ta = f"{late_util} lần trễ — nhiều lần thiếu số dư"
    detail["utility_compliance"] = {"diem": d, "max": 30, "gia_tri": f"{late_util} lần trễ/12T", "mo_ta": mo_ta}

    # ── Account Vitality (20đ) ───────────────────────────────────────────────
    ngan_hang = compliance.get("ngan_hang", {})
    products = ngan_hang.get("so_san_pham_dang_dung", 1)
    active_months = ngan_hang.get("so_thang_active_12t", 0)
    if active_months >= 11 and products >= 3:
        d = 20;  mo_ta = f"Active {active_months}T · {products} sản phẩm"
    elif products >= 2:
        d = 12;  mo_ta = f"{products} sản phẩm"
    else:
        d = 5;   mo_ta = "Chỉ tài khoản cơ bản"
    detail["account_vitality"] = {"diem": d, "max": 20, "gia_tri": f"{products} sản phẩm · {active_months}T active", "mo_ta": mo_ta}

    total = sum(v["diem"] for v in detail.values())
    return LayerResult(layer="L3B_COMPLIANCE", diem_tho=total, diem_max=160, available=True, chi_tiet=detail)
