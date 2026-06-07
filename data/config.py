"""
Statistical anchors for Vietnamese MSME data generation.
Sources: GSO 2022-2023, SBV Annual Report 2023, GDT statistics, World Bank Vietnam SME report.
"""

# ── Segment distribution (SBV 2023) ──────────────────────────────────────────
SEGMENT_DISTRIBUTION = {
    "Micro":  0.50,   # Siêu nhỏ: doanh thu <3 tỷ, <10 nhân viên
    "Small":  0.35,   # Nhỏ: 3-50 tỷ, 10-50 nhân viên
    "Medium": 0.15,   # Vừa: 50-200 tỷ, 50-200 nhân viên
}

# Revenue range in billion VND/year per segment (log-normal params: mean, std of log)
SEGMENT_REVENUE = {
    "Micro":  {"lo": 0.2,   "hi": 3.0,   "mode": 0.8},
    "Small":  {"lo": 3.0,   "hi": 50.0,  "mode": 12.0},
    "Medium": {"lo": 50.0,  "hi": 200.0, "mode": 90.0},
}

SEGMENT_EMPLOYEES = {
    "Micro":  {"lo": 1,  "hi": 9,   "mode": 4},
    "Small":  {"lo": 10, "hi": 50,  "mode": 22},
    "Medium": {"lo": 51, "hi": 200, "mode": 90},
}

# ── Industry distribution conditional on segment (GSO 2022) ──────────────────
# Format: {industry_code: weight}
INDUSTRY_DIST = {
    "Micro": {
        "G": 0.38,   # Bán buôn, bán lẻ
        "I": 0.18,   # Dịch vụ lưu trú, ăn uống
        "F": 0.12,   # Xây dựng
        "C": 0.12,   # Chế biến chế tạo
        "M": 0.08,   # Chuyên môn, khoa học
        "H": 0.07,   # Vận tải, kho bãi
        "J": 0.03,   # Thông tin truyền thông
        "N": 0.02,   # Hành chính, hỗ trợ
    },
    "Small": {
        "G": 0.33,
        "C": 0.22,
        "F": 0.15,
        "H": 0.09,
        "I": 0.07,
        "M": 0.07,
        "J": 0.05,
        "N": 0.02,
    },
    "Medium": {
        "C": 0.30,   # Manufacturing dominant ở Medium
        "G": 0.25,
        "F": 0.18,
        "H": 0.10,
        "M": 0.08,
        "J": 0.06,
        "I": 0.02,
        "N": 0.01,
    },
}

INDUSTRY_NAMES = {
    "G": "Bán buôn và bán lẻ; sửa chữa ô tô, mô tô, xe máy",
    "C": "Công nghiệp chế biến, chế tạo",
    "F": "Xây dựng",
    "H": "Vận tải, kho bãi",
    "I": "Dịch vụ lưu trú và ăn uống",
    "J": "Thông tin và truyền thông",
    "M": "Hoạt động chuyên môn, khoa học và công nghệ",
    "N": "Hoạt động hành chính và dịch vụ hỗ trợ",
}

# ── Geographic distribution (GSO 2022) ───────────────────────────────────────
# (province_code, province_name, weight)
PROVINCE_DIST = [
    ("79", "TP. Hồ Chí Minh",  0.35),
    ("01", "Hà Nội",            0.20),
    ("74", "Bình Dương",        0.08),
    ("75", "Đồng Nai",          0.06),
    ("48", "Đà Nẵng",           0.05),
    ("02", "Hải Phòng",         0.05),
    ("36", "Khánh Hòa",         0.03),
    ("92", "Cần Thơ",           0.03),
    ("52", "Bình Định",         0.02),
    ("56", "Phú Yên",           0.02),
    ("77", "Bà Rịa - Vũng Tàu", 0.02),
    ("72", "Tây Ninh",          0.02),
    ("60", "Gia Lai",           0.01),
    ("31", "Thanh Hóa",         0.02),
    ("38", "Nghệ An",           0.02),
    ("other", "Các tỉnh khác",  0.02),
]

# ── Industry-specific financial ratio anchors ─────────────────────────────────
# (mean, std) tuples — based on SBV/World Bank Vietnam data
INDUSTRY_FINANCIALS = {
    "G": {  # Trade — thin margins, fast turnover
        "ebitda_margin": (0.055, 0.025),
        "ccc_days":      (38, 12),
        "de_ratio":      (1.8, 0.6),
        "current_ratio": (1.25, 0.3),
        "customer_conc": (0.55, 0.15),   # Fewer, larger buyers
    },
    "C": {  # Manufacturing — capital intensive, moderate margins
        "ebitda_margin": (0.095, 0.04),
        "ccc_days":      (72, 18),
        "de_ratio":      (2.3, 0.7),
        "current_ratio": (1.35, 0.3),
        "customer_conc": (0.48, 0.15),
    },
    "F": {  # Construction — project-based, slow cash
        "ebitda_margin": (0.065, 0.03),
        "ccc_days":      (95, 25),
        "de_ratio":      (2.6, 0.8),
        "current_ratio": (1.15, 0.25),
        "customer_conc": (0.75, 0.12),   # Few big project clients
    },
    "H": {  # Transport — asset heavy, steady
        "ebitda_margin": (0.075, 0.03),
        "ccc_days":      (45, 15),
        "de_ratio":      (2.8, 0.8),
        "current_ratio": (1.10, 0.25),
        "customer_conc": (0.52, 0.15),
    },
    "I": {  # F&B — high turnover, cash-heavy
        "ebitda_margin": (0.085, 0.04),
        "ccc_days":      (22, 8),
        "de_ratio":      (1.5, 0.5),
        "current_ratio": (1.20, 0.3),
        "customer_conc": (0.28, 0.12),   # Many small customers
    },
    "J": {  # IT — high margin, fast receivables
        "ebitda_margin": (0.18, 0.06),
        "ccc_days":      (35, 12),
        "de_ratio":      (0.8, 0.4),
        "current_ratio": (1.80, 0.4),
        "customer_conc": (0.45, 0.15),
    },
    "M": {  # Professional services
        "ebitda_margin": (0.15, 0.05),
        "ccc_days":      (40, 15),
        "de_ratio":      (0.9, 0.4),
        "current_ratio": (1.65, 0.4),
        "customer_conc": (0.50, 0.15),
    },
    "N": {  # Admin support
        "ebitda_margin": (0.10, 0.04),
        "ccc_days":      (32, 10),
        "de_ratio":      (1.2, 0.5),
        "current_ratio": (1.40, 0.35),
        "customer_conc": (0.60, 0.15),
    },
}

# ── Seasonal revenue multipliers by industry (month 1-12) ────────────────────
SEASONAL_FACTORS = {
    "G": [1.35, 0.65, 0.85, 0.90, 0.92, 0.95, 0.88, 0.85, 1.00, 1.05, 1.15, 1.45],
    "C": [0.88, 0.72, 0.95, 1.00, 1.02, 1.05, 1.05, 1.08, 1.12, 1.10, 1.05, 0.98],
    "F": [0.60, 0.55, 0.85, 1.05, 1.10, 1.05, 1.00, 0.98, 1.12, 1.15, 1.10, 0.95],
    "H": [0.90, 0.80, 0.95, 1.00, 1.02, 1.02, 1.05, 1.05, 1.05, 1.05, 1.05, 1.01],
    "I": [1.30, 0.75, 0.88, 0.90, 0.85, 1.05, 1.12, 1.08, 0.95, 0.95, 1.00, 1.17],
    "J": [0.92, 0.85, 0.98, 1.02, 1.05, 1.02, 1.00, 1.00, 1.05, 1.05, 1.03, 1.03],
    "M": [0.88, 0.80, 0.98, 1.05, 1.05, 1.02, 0.98, 0.98, 1.05, 1.08, 1.08, 1.05],
    "N": [0.92, 0.85, 1.00, 1.02, 1.02, 1.00, 1.00, 1.00, 1.03, 1.05, 1.05, 1.06],
}

# ── Data availability (DRI) by segment (thin-file adjustment) ─────────────────
# Probability that each data source is available
DATA_AVAILABILITY = {
    "Micro": {
        "has_cic":         0.58,   # 42% thin-file
        "has_bctc":        0.32,   # 68% no formal financial statement
        "has_einvoice":    0.85,   # Mandatory since 2022, but some gaps
        "has_bank_stmt":   0.90,
        "has_bhxh":        0.72,   # Some micro don't register BHXH
        "has_contracts":   0.25,   # Few have formal anchor contracts
    },
    "Small": {
        "has_cic":         0.82,
        "has_bctc":        0.70,
        "has_einvoice":    0.95,
        "has_bank_stmt":   0.97,
        "has_bhxh":        0.90,
        "has_contracts":   0.55,
    },
    "Medium": {
        "has_cic":         0.95,
        "has_bctc":        0.95,
        "has_einvoice":    0.99,
        "has_bank_stmt":   0.99,
        "has_bhxh":        0.98,
        "has_contracts":   0.80,
    },
}

# ── Financial health distribution per segment ─────────────────────────────────
# Maps to a 0-1 health score used to interpolate between bad/good financials
# (mean, std) of health score per segment
SEGMENT_HEALTH = {
    "Micro":  {"mean": 0.38, "std": 0.22},   # Skewed toward distressed
    "Small":  {"mean": 0.52, "std": 0.22},   # Centered, wide spread
    "Medium": {"mean": 0.65, "std": 0.18},   # Skewed toward healthy
}

# ── CIC availability and characteristics ─────────────────────────────────────
CIC_PARAMS = {
    "Micro": {
        "thin_file_rate":   0.42,
        "bad_debt_rate":    0.22,   # % with current group 2+
        "nợ_xấu_rate":     0.12,   # % with history of group 3+
        "avg_num_tctd":    (1.5, 0.8),
    },
    "Small": {
        "thin_file_rate":   0.15,
        "bad_debt_rate":    0.15,
        "nợ_xấu_rate":     0.07,
        "avg_num_tctd":    (2.5, 1.0),
    },
    "Medium": {
        "thin_file_rate":   0.05,
        "bad_debt_rate":    0.08,
        "nợ_xấu_rate":     0.03,
        "avg_num_tctd":    (3.2, 1.2),
    },
}

# ── Tax/Compliance rates (GDT 2023) ──────────────────────────────────────────
TAX_COMPLIANCE = {
    "Micro":  {"on_time_rate": 0.52, "enforcement_rate": 0.08},
    "Small":  {"on_time_rate": 0.68, "enforcement_rate": 0.04},
    "Medium": {"on_time_rate": 0.82, "enforcement_rate": 0.01},
}

BHXH_COMPLIANCE = {
    "Micro":  {"no_debt_rate": 0.48, "long_debt_rate": 0.25},
    "Small":  {"no_debt_rate": 0.65, "long_debt_rate": 0.12},
    "Medium": {"no_debt_rate": 0.82, "long_debt_rate": 0.04},
}
