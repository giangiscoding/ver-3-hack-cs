"""DRI — Data Richness Index"""

from scorer.models import CompanyBundle, DRIResult


def compute(bundle: CompanyBundle) -> DRIResult:
    coverage  = _coverage(bundle)
    depth     = _depth(bundle)
    freshness = _freshness(bundle)
    cross_val = _cross_validation(bundle)

    dri = 0.35 * coverage + 0.30 * depth + 0.15 * freshness + 0.20 * cross_val
    return DRIResult(dri=round(dri, 3), coverage=coverage, depth=depth, freshness=freshness, cross_val=cross_val)


def _coverage(bundle: CompanyBundle) -> float:
    # CIC và BCTC có trọng số 2 (quan trọng hơn); L3 sources trọng số 1
    sources = [
        (bundle.cic.get("available", False),        2),
        (bundle.bctc.get("available", False),       2),
        (bundle.einvoices.get("available", False),  1),
        (bundle.bank.get("available", False),       1),
        (bundle.compliance.get("available", False), 1),
        (bundle.esg.get("available", False),        1),
    ]
    score = sum(w for avail, w in sources if avail)
    return score / 8.0


def _depth(bundle: CompanyBundle) -> float:
    scores = []

    if bundle.einvoices.get("available"):
        months = bundle.einvoices.get("so_thang_co_hoa_don", 0)
        scores.append(min(months / 12, 1.0))

    if bundle.bank.get("available"):
        months = len(bundle.bank.get("du_lieu_theo_thang", []))
        scores.append(min(months / 12, 1.0))

    if bundle.compliance.get("available"):
        history = bundle.compliance.get("thue", {}).get("lich_su_24_thang", [])
        scores.append(min(len(history) / 24, 1.0))

    if bundle.bctc.get("available"):
        rev = bundle.bctc.get("revenue_bn_vnd", {})
        years = sum(1 for v in rev.values() if v and v > 0)
        scores.append(min(years / 3, 1.0))

    return sum(scores) / len(scores) if scores else 0.0


def _freshness(bundle: CompanyBundle) -> float:
    scores = []

    if bundle.einvoices.get("available"):
        monthly = bundle.einvoices.get("du_lieu_theo_thang", [])
        if monthly:
            last = monthly[-1]["thang"]
            y, m = map(int, last.split("-"))
            # 2025-12 là BASE_DATE; stale sau 6 tháng
            months_ago = (2025 - y) * 12 + (12 - m)
            scores.append(max(0.0, 1.0 - months_ago / 6))

    if bundle.compliance.get("available"):
        history = bundle.compliance.get("thue", {}).get("lich_su_24_thang", [])
        scores.append(1.0 if len(history) >= 12 else len(history) / 12)

    if bundle.bctc.get("available"):
        scores.append(1.0)   # assume BCTC là năm hiện tại

    return sum(scores) / len(scores) if scores else 0.5


def _cross_validation(bundle: CompanyBundle) -> float:
    checks = []

    # BCTC revenue vs E-Invoice revenue
    if bundle.bctc.get("available") and bundle.einvoices.get("available"):
        bctc_rev = bundle.bctc.get("revenue_bn_vnd", {}).get("year_n", 0) * 1000
        inv_rev = sum(
            m.get("tong_doanh_thu_mn_vnd", 0)
            for m in bundle.einvoices.get("du_lieu_theo_thang", [])
        )
        if bctc_rev > 0 and inv_rev > 0:
            ratio = inv_rev / bctc_rev
            checks.append(1.0 if 0.5 <= ratio <= 1.5 else max(0.0, 1.0 - abs(ratio - 1.0)))

    # BHXH nhân viên vs nhân viên master
    if bundle.compliance.get("available"):
        reported = bundle.compliance.get("bhxh", {}).get("so_nhan_vien_dong_bhxh", 0)
        actual = bundle.meta.get("so_nhan_vien", 1)
        if actual > 0:
            ratio = reported / actual
            checks.append(1.0 if ratio >= 0.8 else ratio / 0.8)

    # Bank inflow vs E-Invoice revenue
    if bundle.bank.get("available") and bundle.einvoices.get("available"):
        bank_in = sum(m.get("tong_thu_mn_vnd", 0) for m in bundle.bank.get("du_lieu_theo_thang", []))
        inv_rev = sum(m.get("tong_doanh_thu_mn_vnd", 0) for m in bundle.einvoices.get("du_lieu_theo_thang", []))
        if bank_in > 0 and inv_rev > 0:
            ratio = inv_rev / bank_in
            checks.append(1.0 if 0.4 <= ratio <= 1.2 else max(0.0, 1.0 - abs(ratio - 0.8)))

    return sum(checks) / len(checks) if checks else 0.5
