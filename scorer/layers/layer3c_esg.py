"""Layer 3C — ESG Behavioral Proxy (120 điểm)"""

from scorer.models import LayerResult


def score(esg: dict) -> LayerResult:
    if not esg.get("available"):
        return LayerResult(
            layer="L3C_ESG", diem_tho=0, diem_max=120,
            available=False,
            chi_tiet={"ly_do": "Không có dữ liệu ESG"},
        )

    detail = {}

    # ── Environmental (40đ) ──────────────────────────────────────────────────
    moi_truong = esg.get("moi_truong", {})
    violations = moi_truong.get("so_vi_pham_24t", 0)
    serious = moi_truong.get("trong_danh_sach_o_nhiem_nghiem_trong", False)
    if serious:
        d = 0;   mo_ta = "Trong danh sách ô nhiễm nghiêm trọng — HARD STOP trần BB"
    elif violations == 0:
        d = 40;  mo_ta = "Không vi phạm môi trường 24T"
    else:
        d = 15;  mo_ta = f"Bị xử phạt {violations} lần"
    detail["environmental"] = {"diem": d, "max": 40, "gia_tri": f"{violations} vi phạm", "mo_ta": mo_ta}

    # ── Social / Labor (40đ) ─────────────────────────────────────────────────
    lao_dong = esg.get("lao_dong", {})
    disputes = lao_dong.get("so_tranh_chap_24t", 0)
    dinh_cong = lao_dong.get("dang_dinh_cong", False)
    if dinh_cong:
        d = 0;   mo_ta = "Đang đình công"
    elif disputes == 0:
        d = 40;  mo_ta = "Không tranh chấp lao động 24T"
    else:
        d = 20;  mo_ta = f"{disputes} tranh chấp đã giải quyết"
    detail["social_labor"] = {"diem": d, "max": 40, "gia_tri": f"{disputes} tranh chấp", "mo_ta": mo_ta}

    # ── Governance (40đ) ─────────────────────────────────────────────────────
    phap_ly = esg.get("phap_ly", {})
    cases = phap_ly.get("so_vu_kien_kinh_te_active", 0)
    bi_don = phap_ly.get("la_bi_don", False)
    if cases == 0:
        d = 40;  mo_ta = "Không có vụ kiện kinh tế"
    elif not bi_don:
        d = 20;  mo_ta = f"{cases} vụ — bị đơn, đã xử xong"
    else:
        d = 5;   mo_ta = f"{cases} vụ đang tranh chấp"
    detail["governance"] = {"diem": d, "max": 40, "gia_tri": f"{cases} vụ kiện active", "mo_ta": mo_ta}

    total = sum(v["diem"] for v in detail.values())
    return LayerResult(layer="L3C_ESG", diem_tho=total, diem_max=120, available=True, chi_tiet=detail)
