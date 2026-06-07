"""
SME/MSME Credit Scoring — Synthetic Data Generator v2
Two-stage: (1) sample from real Vietnamese MSME statistics, (2) adjust for MSME characteristics.

Usage:
    python generate_v2.py              # 5000 companies (default)
    python generate_v2.py --n 1000    # custom count
"""

import argparse
import json
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    BHXH_COMPLIANCE,
    CIC_PARAMS,
    DATA_AVAILABILITY,
    INDUSTRY_DIST,
    INDUSTRY_FINANCIALS,
    INDUSTRY_NAMES,
    PROVINCE_DIST,
    SEASONAL_FACTORS,
    SEGMENT_DISTRIBUTION,
    SEGMENT_EMPLOYEES,
    SEGMENT_HEALTH,
    SEGMENT_REVENUE,
    TAX_COMPLIANCE,
)

# ── Setup ─────────────────────────────────────────────────────────────────────
SEED = 42
BASE_DATE = date(2025, 12, 31)
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

random.seed(SEED)
np.random.seed(SEED)

# ── Vietnamese reference strings ──────────────────────────────────────────────
COMPANY_TYPES = {
    "Micro":  ["Doanh nghiệp tư nhân", "Công ty TNHH MTV", "Công ty TNHH"],
    "Small":  ["Công ty TNHH", "Công ty Cổ phần", "Công ty TNHH MTV"],
    "Medium": ["Công ty Cổ phần", "Công ty TNHH"],
}
SURNAMES = ["Nguyễn","Trần","Lê","Phạm","Hoàng","Huỳnh","Phan","Vũ","Đặng","Bùi",
            "Đỗ","Hồ","Ngô","Dương","Lý","Đinh","Lâm","Mai","Tô","Trịnh"]
GIVEN_NAMES = ["Văn An","Thị Bình","Văn Cường","Thị Dung","Văn Đức","Thị Hoa",
               "Văn Hùng","Thị Lan","Văn Minh","Thị Nga","Văn Nam","Thị Oanh",
               "Văn Phúc","Thị Quỳnh","Văn Sơn","Thị Tâm","Văn Toàn","Thị Uyên",
               "Văn Vinh","Thị Xuân","Văn Khoa","Thị Hằng","Văn Long","Thị Linh"]
BIZ_WORDS = ["Thương Mại","Dịch Vụ","Sản Xuất","Xây Dựng","Vận Tải","Đầu Tư",
             "Phát Triển","Kỹ Thuật","Tư Vấn","Giải Pháp","Công Nghệ","Kinh Doanh"]
BIZ_NOUNS = ["Thành Công","Phú Quý","An Khang","Minh Đức","Hưng Phát","Đại Việt",
             "Hoà Phát","Vạn Lộc","Kim Long","Thiên Phú","Đại Phát","Minh Hưng",
             "Phú Thịnh","Thái Bình","Việt Thắng","An Phú","Minh Tâm","Đức Phát",
             "Hưng Thịnh","Long Phát","Vĩnh Phát","Tân Phát","Bình Minh","Ánh Dương"]
STREETS = ["Lê Lợi","Trần Phú","Nguyễn Huệ","Hai Bà Trưng","Lý Thường Kiệt",
           "Đinh Tiên Hoàng","Bà Triệu","Trần Hưng Đạo","Nguyễn Trãi","Phan Bội Châu",
           "Lê Duẩn","Trường Chinh","Giải Phóng","Xô Viết Nghệ Tĩnh","Cách Mạng Tháng 8",
           "Nguyễn Văn Linh","Phạm Văn Đồng","Đinh Bộ Lĩnh","Hoàng Diệu","Đống Đa"]
WARDS = ["Phường 1","Phường 3","Phường Bến Nghé","Phường Cầu Ông Lãnh","Phường Hàng Bài",
         "Phường Tràng Tiền","Phường Hoàn Kiếm","Phường Đống Đa","Phường Cầu Giấy",
         "Phường Mỹ An","Phường Hải Châu","Phường Thanh Khê"]


# ── Utilities ─────────────────────────────────────────────────────────────────

def clip(v, lo, hi):
    return max(lo, min(hi, v))

def norm(mean, std, lo=None, hi=None):
    v = np.random.normal(mean, std)
    if lo is not None: v = max(lo, v)
    if hi is not None: v = min(hi, v)
    return v

def lognorm_sample(mode, lo, hi):
    """Sample from a log-normal distribution anchored to given mode and bounds."""
    log_mode = math.log(mode)
    log_std = (math.log(hi) - math.log(lo)) / 5
    v = np.random.normal(log_mode, log_std)
    return clip(math.exp(v), lo, hi)

def weighted_choice(items, weights):
    total = sum(weights)
    r = random.random() * total
    cumulative = 0
    for item, w in zip(items, weights):
        cumulative += w
        if r <= cumulative:
            return item
    return items[-1]

def months_back(n):
    result = []
    d = BASE_DATE
    for _ in range(n):
        result.append(f"{d.year}-{d.month:02d}")
        d = date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1)
    return list(reversed(result))

def gen_mst(province_code):
    digits = "".join(str(random.randint(0, 9)) for _ in range(8))
    return f"{province_code}{digits}"

def gen_name():
    return f"{random.choice(SURNAMES)} {random.choice(GIVEN_NAMES)}"

def gen_company_name():
    return f"{random.choice(BIZ_WORDS)} {random.choice(BIZ_NOUNS)}"

def gen_address(province):
    return f"Số {random.randint(1,200)} {random.choice(STREETS)}, {random.choice(WARDS)}, {province}"

def sample_province():
    codes = [p[0] for p in PROVINCE_DIST]
    names = [p[1] for p in PROVINCE_DIST]
    weights = [p[2] for p in PROVINCE_DIST]
    idx = weighted_choice(range(len(codes)), weights)
    code = codes[idx]
    if code == "other":
        code = f"{random.randint(10, 90):02d}"
        name = "Tỉnh khác"
    else:
        name = names[idx]
    return code, name

def sample_industry(segment):
    dist = INDUSTRY_DIST[segment]
    return weighted_choice(list(dist.keys()), list(dist.values()))

def sample_segment():
    return weighted_choice(
        list(SEGMENT_DISTRIBUTION.keys()),
        list(SEGMENT_DISTRIBUTION.values())
    )

def health_to_dscr(h):
    """Map health [0,1] → DSCR. h=0 → 0.3, h=0.5 → 1.1, h=1 → 2.5"""
    return 0.3 + h * 2.2

def health_to_de(h, industry_mean):
    """Higher health → lower D/E. h=0 → 4.5, h=1 → 0.3"""
    base = industry_mean
    return clip(base * (1.8 - 1.4 * h), 0.1, 6.0)

def health_to_ebitda(h, industry_mean, industry_std):
    """h=0 → very low/negative, h=1 → top quartile"""
    low = industry_mean - 2 * industry_std
    high = industry_mean + 2 * industry_std
    return clip(low + h * (high - low) + norm(0, industry_std * 0.3), low - 0.05, high + 0.05)


# ── Population heterogeneity: fundamentals-driven health (cho cluster router) ──
# Mỗi DN có 5 "nền tảng" tiềm ẩn (fundamentals), mỗi cái sinh ra một nhóm feature:
#   fin   → BCTC (DSCR, D/E, EBITDA...)        credit → CIC (nhóm nợ, utilization...)
#   cashflow → bank (CV, in/out)               tax    → tuân thủ thuế
#   div   → đa dạng khách hàng (concentration)
#
# CREDITWORTHINESS THẬT (health) = tổ hợp có TRỌNG SỐ KHÁC NHAU theo archetype.
# Đây là giả định cốt lõi & thực tế: thin-file MSME có ĐỘNG LỰC RỦI RO khác hẳn —
# sống còn của micro phụ thuộc kỷ luật dòng tiền + tuân thủ thuế, còn DN lớn phụ
# thuộc tỷ số tài chính + lịch sử tín dụng. Cùng một feature (vd: tax) tác động
# tới health với trọng số KHÁC NHAU theo nhóm → global model phải "trung bình hóa"
# và mất tín hiệu; cluster router học được driver riêng từng nhóm.
HEALTH_DRIVER_WEIGHTS = {
    #            fin    credit  cashflow  tax    div
    "FULL":    {"fin": 0.34, "credit": 0.34, "cashflow": 0.14, "tax": 0.10, "div": 0.08},
    "NO_CIC":  {"fin": 0.42, "credit": 0.04, "cashflow": 0.26, "tax": 0.18, "div": 0.10},
    "NO_BCTC": {"fin": 0.05, "credit": 0.36, "cashflow": 0.36, "tax": 0.13, "div": 0.10},
    "L3_ONLY": {"fin": 0.05, "credit": 0.05, "cashflow": 0.40, "tax": 0.30, "div": 0.20},
}
_FUND_KEYS = ["fin", "credit", "cashflow", "tax", "div"]


def compute_archetype(avail) -> str:
    """Xác định archetype quần thể từ data availability (CIC, BCTC)."""
    has_cic, has_bctc = avail["has_cic"], avail["has_bctc"]
    if has_cic and has_bctc:
        return "FULL"
    elif has_bctc:
        return "NO_CIC"
    elif has_cic:
        return "NO_BCTC"
    return "L3_ONLY"


# Tương quan giữa các fundamentals với "chất lượng chung" (base).
# ρ cao → DN tốt đều mọi mặt (đồng nhất). ρ thấp → fundamentals độc lập hơn →
# thin-file là quần thể KHÁC BIỆT mạnh (vd: DN lời nhưng cẩu thả thuế) → cluster
# model có nhiều signal riêng hơn → stacked blend cải thiện rõ hơn.
# Công thức Gaussian tương quan: giữ NGUYÊN variance từng fundamental ở mọi ρ.
FUND_RHO = 0.40


def draw_fundamentals(segment):
    """
    Rút 5 fundamentals tiềm ẩn [0,1], mỗi cái tương quan ρ=FUND_RHO với base quality.
    ρ thấp → các mặt (tài chính/tín dụng/dòng tiền/thuế/đa dạng) ít đi cùng nhau.
    """
    cfg = SEGMENT_HEALTH[segment]
    mu, sd = cfg["mean"], cfg["std"]
    base = clip(norm(mu, sd), 0.0, 1.0)
    coef = math.sqrt(1.0 - FUND_RHO ** 2)
    funds = {}
    for k in _FUND_KEYS:
        eps = norm(0.0, sd)
        funds[k] = clip(mu + FUND_RHO * (base - mu) + coef * eps, 0.0, 1.0)
    return base, funds


def compute_health(funds, archetype):
    """Creditworthiness thật = tổ hợp fundamentals có trọng số theo archetype."""
    w = HEALTH_DRIVER_WEIGHTS[archetype]
    return clip(sum(w[k] * funds[k] for k in w), 0.0, 1.0)


# ── Stage 1: Sample company metadata ─────────────────────────────────────────

def sample_company_meta(segment, idx):
    province_code, province_name = sample_province()
    industry = sample_industry(segment)
    company_type = random.choice(COMPANY_TYPES[segment])
    rev_cfg = SEGMENT_REVENUE[segment]
    revenue_bn = lognorm_sample(rev_cfg["mode"], rev_cfg["lo"], rev_cfg["hi"])
    emp_cfg = SEGMENT_EMPLOYEES[segment]
    employees = int(clip(norm(emp_cfg["mode"], (emp_cfg["hi"] - emp_cfg["lo"]) / 4),
                         emp_cfg["lo"], emp_cfg["hi"]))

    # Founding year distribution: skewed recent for Micro, older for Medium
    if segment == "Micro":
        years_ago = lognorm_sample(3, 0.5, 15)
    elif segment == "Small":
        years_ago = lognorm_sample(6, 1, 25)
    else:
        years_ago = lognorm_sample(10, 3, 35)

    founded = BASE_DATE.replace(year=max(1990, BASE_DATE.year - int(years_ago)))
    mst = gen_mst(province_code)

    return {
        "id": idx,
        "mst": mst,
        "ten_doanh_nghiep": f"{company_type} {gen_company_name()}",
        "loai_hinh": company_type,
        "phan_khuc": segment,
        "nganh_chinh": industry,
        "mo_ta_nganh": INDUSTRY_NAMES[industry],
        "tinh_thanh_pho": province_name,
        "ma_tinh": province_code,
        "dia_chi": gen_address(province_name),
        "nguoi_dai_dien": gen_name(),
        "email": f"info@{mst}.vn",
        "sdt": f"0{random.randint(300000000, 999999999)}",
        "doanh_thu_bn_vnd": round(revenue_bn, 2),
        "so_nhan_vien": employees,
        "ngay_thanh_lap": founded.strftime("%Y-%m-%d"),
        "tuoi_doanh_nghiep_nam": round(years_ago, 1),
    }


# ── Stage 2: Adjust and generate layered data ─────────────────────────────────

def decide_data_availability(segment):
    avail = DATA_AVAILABILITY[segment]
    return {k: random.random() < v for k, v in avail.items()}


# ── Layer 1: CIC ──────────────────────────────────────────────────────────────

def gen_layer1_cic(meta, funds, avail):
    segment = meta["phan_khuc"]
    cic_cfg = CIC_PARAMS[segment]
    health = funds["credit"]   # CIC sinh từ nền tảng tín dụng

    if not avail["has_cic"]:
        return {"available": False, "ly_do": "Thin-file — chưa có lịch sử tín dụng TCTD"}

    # Debt group from health score
    bad_debt_roll = random.random()
    if health > 0.75:
        debt_group = 1
    elif health > 0.50:
        debt_group = 1 if bad_debt_roll > cic_cfg["bad_debt_rate"] * 0.3 else 2
    elif health > 0.25:
        debt_group = 1 if bad_debt_roll > cic_cfg["bad_debt_rate"] else (2 if bad_debt_roll > cic_cfg["bad_debt_rate"] * 0.4 else 3)
    else:
        debt_group = 1 if bad_debt_roll > 0.6 else (2 if bad_debt_roll > 0.3 else (3 if bad_debt_roll > 0.15 else 4))

    # 24-month history
    history = []
    worst_past = 1
    for i in range(24):
        if health > 0.6:
            g = 1
        elif health > 0.35:
            g = 1 if random.random() > 0.08 else 2
        elif health > 0.15:
            g = random.choices([1, 2, 3], weights=[0.65, 0.25, 0.10])[0]
        else:
            g = random.choices([1, 2, 3, 4], weights=[0.30, 0.30, 0.25, 0.15])[0]
        history.append(g)
        worst_past = max(worst_past, g)

    utilization = clip(norm(
        0.3 + (1 - health) * 0.55,
        0.12
    ), 0.01, 1.3)

    num_tctd_cfg = cic_cfg["avg_num_tctd"]
    num_tctd = max(1, int(round(norm(*num_tctd_cfg))))
    if health < 0.3:
        num_tctd = min(num_tctd + random.randint(0, 3), 9)

    debt_growth = clip(norm(
        0.05 + (1 - health) * 0.70,
        0.15
    ), -0.2, 1.5)

    return {
        "available": True,
        "debt_group_current": debt_group,
        "debt_group_history_24m": history,
        "worst_debt_group_24m": worst_past,
        "credit_utilization_pct": round(utilization * 100, 1),
        "num_financial_institutions": num_tctd,
        "debt_growth_12m_pct": round(debt_growth * 100, 1),
    }


# ── Layer 2: BCTC ─────────────────────────────────────────────────────────────

def gen_layer2_bctc(meta, funds, avail):
    segment = meta["phan_khuc"]
    industry = meta["nganh_chinh"]
    revenue_bn = meta["doanh_thu_bn_vnd"]
    health = funds["fin"]   # BCTC sinh từ nền tảng tài chính

    if not avail["has_bctc"]:
        return {"available": False, "ly_do": "Không có BCTC (phổ biến ở Micro/SME chưa kiểm toán)"}

    fin = INDUSTRY_FINANCIALS[industry]

    dscr = clip(health_to_dscr(health) + norm(0, 0.12), 0.1, 3.5)
    de = health_to_de(health, fin["de_ratio"][0])
    ebitda_m = health_to_ebitda(health, fin["ebitda_margin"][0], fin["ebitda_margin"][1])

    # MSME adjustment: inflate D/E slightly vs large enterprises
    msme_de_adj = {"Micro": 1.25, "Small": 1.10, "Medium": 1.0}[segment]
    de = clip(de * msme_de_adj, 0.1, 8.0)

    ccc = clip(norm(fin["ccc_days"][0] * (1.4 - 0.4 * health), fin["ccc_days"][1]), 5, 200)
    cr = clip(norm(fin["current_ratio"][0] * (0.7 + 0.5 * health), fin["current_ratio"][1] * 0.8), 0.3, 4.0)

    cagr = clip(norm(-0.15 + health * 0.45, 0.08), -0.4, 0.6)

    r_n = revenue_bn
    r_n1 = round(r_n / (1 + cagr), 2) if cagr > -1 else r_n
    r_n2 = round(r_n1 / (1 + cagr), 2) if cagr > -1 else r_n1

    vcsh = round(r_n * 0.35 / (1 + de), 2)
    total_debt = round(vcsh * de, 2)
    ebitda = round(r_n * ebitda_m, 2)
    annual_ds = round(ebitda / dscr, 3) if dscr > 0 else 0

    return {
        "available": True,
        "revenue_bn_vnd": {"year_n_2": r_n2, "year_n_1": r_n1, "year_n": round(r_n, 2)},
        "cagr_3y_pct": round(cagr * 100, 1),
        "ebitda_bn_vnd": ebitda,
        "ebitda_margin_pct": round(ebitda_m * 100, 1),
        "vcsh_bn_vnd": vcsh,
        "total_debt_bn_vnd": total_debt,
        "de_ratio": round(de, 2),
        "current_ratio": round(cr, 2),
        "cash_conversion_cycle_days": int(ccc),
        "dscr": round(dscr, 2),
        "annual_debt_service_bn_vnd": round(annual_ds, 2),
    }


# ── Layer 3A: E-Invoices ──────────────────────────────────────────────────────

def gen_layer3a_einvoices(meta, funds, avail):
    segment = meta["phan_khuc"]
    industry = meta["nganh_chinh"]
    revenue_bn = meta["doanh_thu_bn_vnd"]
    mst = meta["mst"]
    health = funds["_health"]   # vitality phản ánh sức khỏe tổng thể
    div_q = funds["div"]        # đa dạng khách hàng là nền tảng riêng

    if not avail["has_einvoice"]:
        return {"available": False, "du_lieu_theo_thang": []}

    # Active months: Micro may have gaps
    max_active = {"Micro": 10, "Small": 11, "Medium": 12}[segment]
    active_months = int(clip(norm(max_active * (0.5 + 0.5 * health), 1.5), 1, 12))

    seasonal = SEASONAL_FACTORS[industry]
    monthly_base = revenue_bn * 1000 / 12  # million VND

    months = months_back(12)
    revenues = []
    for i, month in enumerate(months):
        cal_month = int(month.split("-")[1])
        season_factor = seasonal[cal_month - 1]
        if i < (12 - active_months):
            revenues.append(0.0)
        else:
            noise = norm(1.0, 0.10, 0.5, 1.8)
            # Health affects trend: good = slight growth, bad = declining
            trend = 1 + (health - 0.5) * 0.02 * (i - (12 - active_months))
            revenues.append(round(monthly_base * season_factor * trend * noise, 1))

    # Customer concentration — from industry profile + nền tảng đa dạng hóa (div).
    fin = INDUSTRY_FINANCIALS[industry]
    base_conc = norm(fin["customer_conc"][0], fin["customer_conc"][1], 0.1, 0.99)
    # Kém đa dạng (div thấp) → tập trung vào ít khách hàng hơn
    conc = clip(base_conc + (1 - div_q) * 0.20, 0.1, 0.99)

    # Build buyer pool — số khách hàng phản ánh nền tảng đa dạng hóa (div)
    n_buyers = max(3, int(norm(18 * div_q + 5, 5, 3, 40)))
    buyer_pool = []
    for _ in range(n_buyers):
        bp_code, _ = sample_province()
        buyer_pool.append({"mst": gen_mst(bp_code), "ten": gen_company_name()})

    invoices = []
    all_buyer_rev: dict = {}
    for i, (month, rev) in enumerate(zip(months, revenues)):
        if rev <= 0:
            continue
        n_inv = max(1, int(rev / norm(15, 8, 3, 100)))
        n_active_buyers = max(1, min(len(buyer_pool), int(norm(n_buyers * 0.6, n_buyers * 0.2, 1, n_buyers))))
        active_buyers = random.sample(buyer_pool, n_active_buyers)
        shares = np.random.dirichlet(np.ones(n_active_buyers) * (0.5 + div_q))
        shares = sorted(shares, reverse=True)
        # Enforce concentration
        top5_sum = sum(shares[:5])
        if top5_sum > 0:
            scale = conc / top5_sum
            shares = [min(s * scale, 1.0) for s in shares]
            total_s = sum(shares)
            shares = [s / total_s for s in shares]

        buyers_detail = []
        remaining = rev
        for j, (buyer, share) in enumerate(zip(active_buyers, shares)):
            amt = round(remaining * share, 1) if j < len(shares) - 1 else round(remaining, 1)
            remaining = max(0, remaining - amt)
            if amt > 0:
                buyers_detail.append({
                    "mst_nguoi_mua": buyer["mst"],
                    "ten_nguoi_mua": buyer["ten"],
                    "so_tien_mn_vnd": amt,
                })
                all_buyer_rev[buyer["mst"]] = all_buyer_rev.get(buyer["mst"], 0) + amt

        invoices.append({
            "thang": month,
            "tong_doanh_thu_mn_vnd": rev,
            "so_hoa_don": n_inv,
            "chi_tiet_nguoi_mua": buyers_detail,
        })

    total_rev = sum(r for r in revenues if r > 0)
    sorted_buyers = sorted(all_buyer_rev.values(), reverse=True)
    top5_rev = sum(sorted_buyers[:5])
    conc_actual = round(top5_rev / total_rev * 100, 1) if total_rev > 0 else 0

    return {
        "available": True,
        "mst_doanh_nghiep": mst,
        "so_thang_co_hoa_don": active_months,
        "customer_concentration_top5_pct": conc_actual,
        "du_lieu_theo_thang": invoices,
    }


# ── Layer 3A: Bank Statement ──────────────────────────────────────────────────

def gen_layer3a_bank(meta, funds, avail):
    segment = meta["phan_khuc"]
    revenue_bn = meta["doanh_thu_bn_vnd"]
    mst = meta["mst"]
    health = funds["cashflow"]   # bank sinh từ nền tảng kỷ luật dòng tiền

    if not avail["has_bank_stmt"]:
        return {"available": False, "du_lieu_theo_thang": []}

    # Coefficient of variation: healthy = stable, distressed = volatile
    cv = clip(norm(0.12 + (1 - health) * 0.40, 0.06), 0.04, 0.80)
    monthly_avg = revenue_bn * 1000 / 12  # million VND

    months = months_back(12)
    records = []
    balance = monthly_avg * norm(0.8 + health * 0.6, 0.2, 0.1, 3.0)

    for month in months:
        inflow = max(0.1, norm(monthly_avg, monthly_avg * cv))
        # Outflow ratio: healthy companies spend less than they earn
        out_ratio = norm(0.82 + (1 - health) * 0.18, 0.05, 0.5, 1.15)
        outflow = max(0.1, inflow * out_ratio)
        balance = max(0.1, balance + inflow - outflow)
        records.append({
            "thang": month,
            "tong_thu_mn_vnd": round(inflow, 1),
            "tong_chi_mn_vnd": round(outflow, 1),
            "so_du_cuoi_thang_mn_vnd": round(balance, 1),
            "so_giao_dich": random.randint(8, 250),
        })

    inflows = [r["tong_thu_mn_vnd"] for r in records]
    outflows = [r["tong_chi_mn_vnd"] for r in records]
    mean_in = np.mean(inflows)
    cv_actual = np.std(inflows) / mean_in if mean_in > 0 else 0
    io_ratio = mean_in / (np.mean(outflows) + 0.01)

    return {
        "available": True,
        "mst_doanh_nghiep": mst,
        "cashflow_cv": round(cv_actual, 3),
        "inflow_outflow_ratio": round(io_ratio, 2),
        "du_lieu_theo_thang": records,
    }


# ── Layer 3A: Anchor contracts ────────────────────────────────────────────────

def gen_layer3a_contracts(meta, health, avail):
    segment = meta["phan_khuc"]
    mst = meta["mst"]
    # health ở đây là composite (anchor network phản ánh sức khỏe & vị thế tổng thể)

    if not avail["has_contracts"]:
        return {"available": False, "so_anchor": 0, "hop_dong": []}

    max_anchors = {"Micro": 1, "Small": 3, "Medium": 5}[segment]
    n_anchors = int(clip(norm(max_anchors * health, 0.8), 0, max_anchors + 1))

    contracts = []
    for _ in range(n_anchors):
        pc, _ = sample_province()
        contracts.append({
            "ten_anchor": gen_company_name(),
            "mst_anchor": gen_mst(pc),
            "loai_hop_dong": random.choice(["Hợp đồng cung cấp hàng hóa", "Hợp đồng dịch vụ", "Hợp đồng phân phối"]),
            "thoi_han_thang": random.choice([12, 24, 36, 48]),
            "gia_tri_hop_dong_mn_vnd": round(random.uniform(50, 5000 * health + 100), 0),
            "ngay_ky": (BASE_DATE - timedelta(days=random.randint(30, 400))).strftime("%Y-%m-%d"),
        })

    return {"available": True, "mst_doanh_nghiep": mst, "so_anchor": n_anchors, "hop_dong": contracts}


# ── Layer 3B: Compliance ──────────────────────────────────────────────────────

def gen_layer3b_compliance(meta, funds, avail):
    segment = meta["phan_khuc"]
    employees = meta["so_nhan_vien"]
    mst = meta["mst"]

    tc = TAX_COMPLIANCE[segment]
    bc = BHXH_COMPLIANCE[segment]
    tax_q = funds["tax"]         # tuân thủ thuế là nền tảng riêng
    cash_q = funds["cashflow"]   # nợ BHXH là chỉ báo stress dòng tiền
    health = funds["_health"]    # sức khỏe tổng thể cho các phần còn lại

    # Tax on-time months out of 24 — sinh từ nền tảng tax (coupling liên tục)
    tax_drop = (1 - tax_q) * 14
    tax_ok = int(clip(norm(24 - tax_drop, 2.5), 0, 24))
    if tax_q > 0.65:
        enforcement = False
    elif tax_q > 0.35:
        enforcement = random.random() < tc["enforcement_rate"]
    else:
        enforcement = random.random() < tc["enforcement_rate"] * 3

    # BHXH debt months — sinh từ nền tảng dòng tiền
    if random.random() < bc["no_debt_rate"] * (0.5 + 0.5 * cash_q):
        bhxh_debt = 0
    elif cash_q < 0.3 and random.random() < bc["long_debt_rate"]:
        bhxh_debt = int(clip(norm(7, 2), 4, 12))
    else:
        bhxh_debt = int(clip(norm(2, 1), 1, 6))

    # Tax history (24 months)
    tax_history = []
    late_budget = 24 - tax_ok
    for i, month in enumerate(months_back(24)):
        if late_budget > 0 and random.random() < late_budget / (24 - i + 0.5):
            days = random.randint(5, 60)
            tax_history.append({"thang": month, "trang_thai": "tre_han", "so_ngay_tre": days})
            late_budget -= 1
        else:
            tax_history.append({"thang": month, "trang_thai": "dung_han", "so_ngay_tre": 0})

    # Utility late count — kỷ luật thanh toán cùng nền tảng với tuân thủ thuế
    max_utility_late = {"Micro": 6, "Small": 3, "Medium": 1}[segment]
    utility_late = int(clip(norm(max_utility_late * (1 - tax_q), 1.0), 0, 12))

    util_history = []
    late_left = utility_late
    for i, month in enumerate(months_back(12)):
        if late_left > 0 and random.random() < late_left / (12 - i + 0.5):
            util_history.append({"thang": month, "trang_thai": "tre_han_hoac_thieu_so_du"})
            late_left -= 1
        else:
            util_history.append({"thang": month, "trang_thai": "dung_han_auto_debit"})

    # Bank products
    max_products = {"Micro": 2, "Small": 3, "Medium": 5}[segment]
    bank_products = max(1, int(clip(norm(1 + health * (max_products - 1), 0.7), 1, max_products)))
    bank_active_months = max(bank_products * 2, int(clip(norm(10 * health + 4, 2), 1, 12)))

    return {
        "available": True,
        "mst_doanh_nghiep": mst,
        "thue": {
            "so_thang_dung_han_24t": tax_ok,
            "co_cuong_che": enforcement,
            "lich_su_24_thang": tax_history,
        },
        "bhxh": {
            "so_thang_no_bhxh": bhxh_debt,
            "co_no_bhxh": bhxh_debt > 0,
            "so_nhan_vien_dong_bhxh": max(0, int(employees * clip(norm(0.7 + 0.3 * health, 0.1), 0, 1))),
        },
        "tien_ich": {
            "so_lan_tre_12t": utility_late,
            "lich_su_12_thang": util_history,
        },
        "ngan_hang": {
            "so_san_pham_dang_dung": bank_products,
            "so_thang_active_12t": bank_active_months,
        },
    }


# ── Layer 3C: ESG ─────────────────────────────────────────────────────────────

def gen_layer3c_esg(meta, health, avail):
    industry = meta["nganh_chinh"]
    mst = meta["mst"]

    # Industry-specific ESG risk
    env_risk = {"C": 0.15, "F": 0.10, "H": 0.08, "G": 0.03, "I": 0.04, "J": 0.01, "M": 0.01, "N": 0.02}
    labor_risk = {"C": 0.10, "F": 0.08, "H": 0.07, "G": 0.05, "I": 0.08, "J": 0.03, "M": 0.03, "N": 0.05}

    env_base = env_risk.get(industry, 0.05) * (1.5 - health)
    env_violations = 0
    if random.random() < env_base:
        env_violations = random.randint(1, 3) if health < 0.3 else 1

    labor_base = labor_risk.get(industry, 0.05) * (1.5 - health)
    labor_disputes = 0
    if random.random() < labor_base:
        labor_disputes = 1

    legal_cases = 0
    if health < 0.25 and random.random() < 0.20:
        legal_cases = random.randint(1, 2)
    elif health < 0.45 and random.random() < 0.07:
        legal_cases = 1

    return {
        "available": True,
        "mst_doanh_nghiep": mst,
        "moi_truong": {
            "so_vi_pham_24t": env_violations,
            "trong_danh_sach_o_nhiem_nghiem_trong": env_violations >= 2,
        },
        "lao_dong": {
            "so_tranh_chap_24t": labor_disputes,
            "dang_dinh_cong": labor_disputes > 1,
        },
        "phap_ly": {
            "so_vu_kien_kinh_te_active": legal_cases,
            "la_bi_don": legal_cases > 0 and health < 0.35,
        },
    }


# ── Layer 3D: Maturity ────────────────────────────────────────────────────────

def gen_layer3d_maturity(meta, avail):
    mst = meta["mst"]
    years_ago = meta["tuoi_doanh_nghiep_nam"]
    segment = meta["phan_khuc"]

    has_hkd_prob = {"Micro": 0.45, "Small": 0.30, "Medium": 0.20}[segment]
    has_hkd = random.random() < has_hkd_prob

    hkd_conditions = None
    if has_hkd:
        match = random.random()
        hkd_conditions = {
            "cung_dia_diem": match > 0.15,
            "cung_nganh_nghe": match > 0.10,
            "cung_chu": match > 0.05,
        }

    return {
        "available": True,
        "mst_doanh_nghiep": mst,
        "ngay_dang_ky": meta["ngay_thanh_lap"],
        "tuoi_phap_nhan_nam": round(years_ago, 1),
        "co_hkd_tien_than": has_hkd,
        "dieu_kien_hkd": hkd_conditions,
    }


# ── Graph: relationships ──────────────────────────────────────────────────────

def gen_graph(companies_list):
    nodes = []
    edges = []
    n = len(companies_list)

    for c in companies_list:
        nodes.append({"id": c["mst"], "type": "doanh_nghiep", "phan_khuc": c["phan_khuc"], "nganh": c["nganh_chinh"]})
        owner_id = f"owner_{c['mst']}"
        nodes.append({"id": owner_id, "type": "chu_so_huu", "ten": c["nguoi_dai_dien"]})
        edges.append({"source": owner_id, "target": c["mst"], "type": "so_huu", "phan_tram": random.randint(51, 100)})

    # Target: ~6% of total companies in fraud clusters (realistic Vietnamese MSME fraud rate)
    target_fraud_companies = max(10, int(n * 0.06))

    # Pool: distressed companies, shuffle and take only what we need
    distressed = [c for c in companies_list if c.get("health", 0.5) < 0.25]
    random.shuffle(distressed)
    fraud_pool = distressed[:target_fraud_companies]

    # Fraud pattern 1: shared controller — clusters of 2-4 companies
    used = set()
    fraud_clusters = []
    i = 0
    while i < len(fraud_pool):
        size = random.randint(2, 4)
        cluster = fraud_pool[i:i + size]
        cluster_msts = [c["mst"] for c in cluster if c["mst"] not in used]
        if len(cluster_msts) >= 2:
            shared_id = f"shadow_controller_{i}"
            nodes.append({"id": shared_id, "type": "chu_so_huu", "ten": gen_name(), "flag": "shadow_controller"})
            for mst in cluster_msts:
                edges.append({"source": shared_id, "target": mst, "type": "so_huu_cheo",
                              "phan_tram": random.randint(15, 49)})
                used.add(mst)
            fraud_clusters.append(cluster_msts)
        i += size

    # Fraud pattern 2: address sharing — pick 5-10 small shell groups from fraud pool
    shell_candidates = [c for c in fraud_pool if c["mst"] in used]
    n_shell_groups = min(10, len(shell_candidates) // 3)
    random.shuffle(shell_candidates)
    for g in range(n_shell_groups):
        group = shell_candidates[g*3:(g+1)*3]
        if len(group) >= 2:
            for c in group[1:]:
                edges.append({"source": group[0]["mst"], "target": c["mst"],
                              "type": "cung_dia_chi", "flag": "possible_shell"})

    # Fraud pattern 3: circular transactions — small ring among worst offenders
    very_bad = [c for c in fraud_pool if c.get("health", 0.5) < 0.12][:8]
    for j in range(len(very_bad)):
        src = very_bad[j]["mst"]
        tgt = very_bad[(j + 1) % len(very_bad)]["mst"]
        if src != tgt:
            edges.append({"source": src, "target": tgt, "type": "giao_dich_noi_bo",
                          "flag": "circular_transaction",
                          "gia_tri_mn_vnd": round(random.uniform(50, 3000), 0)})

    # Legitimate supply chain edges
    msts = [c["mst"] for c in companies_list]
    for _ in range(int(n * 0.15)):
        src, tgt = random.sample(msts, 2)
        edges.append({"source": src, "target": tgt, "type": "giao_dich_thuong_mai",
                      "gia_tri_mn_vnd": round(random.uniform(10, 500), 0)})

    return {
        "nodes": nodes,
        "edges": edges,
        "fraud_clusters": fraud_clusters,
        "fraud_edge_count": sum(1 for e in edges if e.get("flag")),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main(n_companies: int):
    print(f"Generating {n_companies} companies (2-stage MSME generator)...")
    print("Stage 1: Sample from Vietnamese MSME statistical distributions")
    print("Stage 2: Apply MSME segment adjustments (thin-file, ratios, seasonality)\n")

    companies_master = []
    all_cic = {}
    all_bctc = {}
    all_einvoices = {}
    all_bank = {}
    all_compliance = {}
    all_esg = {}
    all_maturity = {}
    all_contracts = {}

    segment_counts = {k: 0 for k in ["Micro", "Small", "Medium"]}
    health_scores = {}

    for idx in range(n_companies):
        if idx % 500 == 0:
            print(f"  [{idx}/{n_companies}] generating...")

        segment = sample_segment()
        meta = sample_company_meta(segment, idx)
        avail = decide_data_availability(segment)
        archetype = compute_archetype(avail)   # quần thể: FULL/NO_CIC/NO_BCTC/L3_ONLY

        # Fundamentals → creditworthiness thật (trọng số driver theo archetype)
        base_quality, funds = draw_fundamentals(segment)
        health = compute_health(funds, archetype)
        funds["_health"] = health   # composite cho các feature phản ánh sức khỏe tổng thể

        # Store health for graph later
        meta["health"] = health
        health_scores[meta["mst"]] = health

        mst = meta["mst"]
        companies_master.append(meta)
        segment_counts[segment] += 1

        all_cic[mst]        = gen_layer1_cic(meta, funds, avail)
        all_bctc[mst]       = gen_layer2_bctc(meta, funds, avail)
        all_einvoices[mst]  = gen_layer3a_einvoices(meta, funds, avail)
        all_bank[mst]       = gen_layer3a_bank(meta, funds, avail)
        all_contracts[mst]  = gen_layer3a_contracts(meta, health, avail)
        all_compliance[mst] = gen_layer3b_compliance(meta, funds, avail)
        all_esg[mst]        = gen_layer3c_esg(meta, health, avail)
        all_maturity[mst]   = gen_layer3d_maturity(meta, avail)

    print("\nBuilding graph network...")
    graph = gen_graph(companies_master)

    # ── Write outputs ─────────────────────────────────────────────────────────
    print("Writing output files...")

    # Remove health field from master before saving (internal use only)
    for c in companies_master:
        c.pop("health", None)

    def write_json(name, obj):
        path = OUTPUT_DIR / name
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        size_kb = path.stat().st_size / 1024
        print(f"  {name:45s} {size_kb:8.1f} KB")

    write_json("companies_master.json", companies_master)
    write_json("layer1_cic.json", all_cic)
    write_json("layer2_bctc.json", all_bctc)
    write_json("layer3a_einvoices.json", all_einvoices)
    write_json("layer3a_bank_statements.json", all_bank)
    write_json("layer3a_contracts.json", all_contracts)
    write_json("layer3b_compliance.json", all_compliance)
    write_json("layer3c_esg.json", all_esg)
    write_json("layer3d_maturity.json", all_maturity)
    write_json("graph.json", graph)

    # Flat CSV for analysis
    rows = []
    for c in companies_master:
        mst = c["mst"]
        cic  = all_cic[mst]
        bctc = all_bctc[mst]
        comp = all_compliance[mst]
        esg  = all_esg[mst]
        mat  = all_maturity[mst]
        inv  = all_einvoices[mst]
        bank = all_bank[mst]

        rows.append({
            "mst": mst,
            "ten": c["ten_doanh_nghiep"],
            "phan_khuc": c["phan_khuc"],
            "nganh": c["nganh_chinh"],
            "tinh": c["tinh_thanh_pho"],
            "doanh_thu_bn": c["doanh_thu_bn_vnd"],
            "so_nhan_vien": c["so_nhan_vien"],
            "tuoi_dn_nam": c["tuoi_doanh_nghiep_nam"],
            "health_score": round(health_scores.get(mst, 0.5), 3),
            # CIC
            "cic_available": cic.get("available", False),
            "cic_debt_group": cic.get("debt_group_current") if cic.get("available") else None,
            "cic_worst_24m": cic.get("worst_debt_group_24m") if cic.get("available") else None,
            "cic_utilization_pct": cic.get("credit_utilization_pct") if cic.get("available") else None,
            "cic_num_tctd": cic.get("num_financial_institutions") if cic.get("available") else None,
            "cic_debt_growth_pct": cic.get("debt_growth_12m_pct") if cic.get("available") else None,
            # BCTC
            "bctc_available": bctc.get("available", False),
            "bctc_dscr": bctc.get("dscr") if bctc.get("available") else None,
            "bctc_de_ratio": bctc.get("de_ratio") if bctc.get("available") else None,
            "bctc_ebitda_margin_pct": bctc.get("ebitda_margin_pct") if bctc.get("available") else None,
            "bctc_ccc_days": bctc.get("cash_conversion_cycle_days") if bctc.get("available") else None,
            "bctc_current_ratio": bctc.get("current_ratio") if bctc.get("available") else None,
            "bctc_cagr_pct": bctc.get("cagr_3y_pct") if bctc.get("available") else None,
            # Layer 3
            "l3a_invoice_available": inv.get("available", False),
            "l3a_active_months": inv.get("so_thang_co_hoa_don") if inv.get("available") else None,
            "l3a_customer_conc_top5_pct": inv.get("customer_concentration_top5_pct") if inv.get("available") else None,
            "l3a_cashflow_cv": bank.get("cashflow_cv") if bank.get("available") else None,
            "l3a_inflow_outflow_ratio": bank.get("inflow_outflow_ratio") if bank.get("available") else None,
            "l3b_tax_on_time_months": comp["thue"]["so_thang_dung_han_24t"] if comp.get("available") else None,
            "l3b_tax_cuong_che": comp["thue"]["co_cuong_che"] if comp.get("available") else None,
            "l3b_bhxh_debt_months": comp["bhxh"]["so_thang_no_bhxh"] if comp.get("available") else None,
            "l3b_utility_late_count": comp["tien_ich"]["so_lan_tre_12t"] if comp.get("available") else None,
            "l3b_bank_products": comp["ngan_hang"]["so_san_pham_dang_dung"] if comp.get("available") else None,
            "l3c_env_violations": esg["moi_truong"]["so_vi_pham_24t"] if esg.get("available") else None,
            "l3c_labor_disputes": esg["lao_dong"]["so_tranh_chap_24t"] if esg.get("available") else None,
            "l3c_legal_cases": esg["phap_ly"]["so_vu_kien_kinh_te_active"] if esg.get("available") else None,
            "l3d_age_years": mat.get("tuoi_phap_nhan_nam") if mat.get("available") else None,
            "l3d_has_hkd": mat.get("co_hkd_tien_than") if mat.get("available") else None,
        })

    df = pd.DataFrame(rows)
    csv_path = OUTPUT_DIR / "analytics_flat.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  {'analytics_flat.csv':45s} {csv_path.stat().st_size/1024:8.1f} KB")

    # Summary stats
    print(f"\n{'─'*55}")
    print("Segment distribution:")
    for seg, cnt in segment_counts.items():
        print(f"  {seg:8s}: {cnt:5d}  ({cnt/n_companies*100:.1f}%)")

    print("\nData availability (avg across all companies):")
    cic_avail = sum(1 for v in all_cic.values() if v.get("available")) / n_companies
    bctc_avail = sum(1 for v in all_bctc.values() if v.get("available")) / n_companies
    inv_avail = sum(1 for v in all_einvoices.values() if v.get("available")) / n_companies
    print(f"  CIC available   : {cic_avail:.1%}")
    print(f"  BCTC available  : {bctc_avail:.1%}")
    print(f"  E-Invoice avail : {inv_avail:.1%}")

    print(f"\nGraph: {len(graph['nodes'])} nodes | {len(graph['edges'])} edges | {len(graph['fraud_clusters'])} fraud clusters")
    print(f"\nDone. All files in: {OUTPUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=5000, help="Number of companies to generate")
    args = parser.parse_args()
    main(args.n)
