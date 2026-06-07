"""Shared data types for the scoring engine."""

from dataclasses import dataclass, field


@dataclass
class LayerResult:
    layer: str
    diem_tho: int
    diem_max: int
    available: bool
    chi_tiet: dict = field(default_factory=dict)


@dataclass
class DRIResult:
    dri: float
    coverage: float
    depth: float
    freshness: float
    cross_val: float

    @property
    def multiplier(self) -> float:
        return 0.7 + 0.3 * self.dri


@dataclass
class CompanyBundle:
    meta: dict
    cic: dict
    bctc: dict
    einvoices: dict
    bank: dict
    contracts: dict
    compliance: dict
    esg: dict
    maturity: dict


@dataclass
class ScoreReport:
    mst: str
    ten: str
    phan_khuc: str
    cluster: str          # FULL | NO_CIC | NO_BCTC | L3_ONLY
    cluster_mo_ta: str
    dqi: dict             # DQI profile: {cic, bctc, einvoice, bank, compliance, esg, overall}
    raw_score: int        # điểm ML thô [0,1000]
    dri: DRIResult
    final_score: int      # raw × DRI multiplier
    rating: str
    hard_stop: str | None
    approval_action: str
    scoring_method: str   # "ml" | "rule_based"
    layers: dict[str, LayerResult]
    top_factors: list[dict]
    fraud_flags: list[str] = field(default_factory=list)
