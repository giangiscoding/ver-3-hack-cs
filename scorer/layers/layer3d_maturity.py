"""Layer 3D — Business Maturity (30 điểm)"""

from scorer.models import LayerResult


def score(maturity: dict) -> LayerResult:
    if not maturity.get("available"):
        return LayerResult(
            layer="L3D_MATURITY", diem_tho=0, diem_max=30,
            available=False,
            chi_tiet={"ly_do": "Không có dữ liệu maturity"},
        )

    detail = {}

    # ── Tuổi pháp nhân (20đ) ─────────────────────────────────────────────────
    age = maturity.get("tuoi_phap_nhan_nam", 0)
    if age >= 10:
        d = 20;  mo_ta = "≥ 10 năm"
    elif age >= 5:
        d = 15;  mo_ta = "5–10 năm"
    elif age >= 3:
        d = 10;  mo_ta = "3–5 năm"
    elif age >= 1:
        d = 5;   mo_ta = "1–3 năm"
    else:
        d = 0;   mo_ta = "< 1 năm"
    detail["legal_entity_age"] = {"diem": d, "max": 20, "gia_tri": f"{age:.1f} năm", "mo_ta": mo_ta}

    # ── HKD tiền thân — bonus additive (10đ) ─────────────────────────────────
    has_hkd = maturity.get("co_hkd_tien_than", False)
    conditions = maturity.get("dieu_kien_hkd") or {}
    if not has_hkd:
        d = 0;   mo_ta = "Không có HKD tiền thân"
    else:
        met = sum([
            bool(conditions.get("cung_dia_diem")),
            bool(conditions.get("cung_nganh_nghe")),
            bool(conditions.get("cung_chu")),
        ])
        if met == 3:
            d = 10;  mo_ta = "HKD tiền thân — xác minh đủ 3 điều kiện"
        elif met == 2:
            d = 5;   mo_ta = f"HKD tiền thân — xác minh {met}/3 điều kiện"
        else:
            d = 0;   mo_ta = "HKD tiền thân — không đủ điều kiện xác minh"
    detail["hkd_continuity"] = {"diem": d, "max": 10, "gia_tri": f"HKD: {'Có' if has_hkd else 'Không'}", "mo_ta": mo_ta}

    total = sum(v["diem"] for v in detail.values())
    return LayerResult(layer="L3D_MATURITY", diem_tho=total, diem_max=30, available=True, chi_tiet=detail)
