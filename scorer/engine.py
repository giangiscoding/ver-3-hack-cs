"""
Scoring engine — orchestrates:
  1. DQI-based cluster classification
  2. LightGBM scoring per cluster (primary path)
  3. Rule-based fallback nếu models chưa được train
  4. DRI confidence multiplier
  5. Rating + hard stops
"""

from __future__ import annotations

from scorer import cluster as cluster_module
from scorer import dri as dri_module
from scorer import rating as rating_module
from scorer.data_quality import compute as compute_dqi
from scorer.layers import layer1_cic, layer2_bctc, layer3a_ops, layer3b_compliance, layer3c_esg, layer3d_maturity
from scorer.models import CompanyBundle, ScoreReport


def score(bundle: CompanyBundle, fraud_flags: list[str] | None = None) -> ScoreReport:
    fraud_flags = fraud_flags or []

    # ── Bước 1: DQI + Cluster classification ─────────────────────────────────
    cluster_id, dqi = cluster_module.classify_with_dqi(bundle)
    cfg = cluster_module.CLUSTER_CONFIGS[cluster_id]

    # ── Bước 2: Chấm điểm theo ML hoặc rule-based ────────────────────────────
    raw_score, top_factors, scoring_method = _score_company(bundle, cluster_id, cfg)

    # ── Bước 3: DRI confidence multiplier ────────────────────────────────────
    dri_result = dri_module.compute(bundle)
    final_score = int(round(raw_score * dri_result.multiplier))

    # ── Bước 4: Rule-based layers (cho display / explanation) ────────────────
    layers = _run_layers(bundle)

    # ── Bước 5: Rating với bands và trần của cluster ──────────────────────────
    rating, hard_stop = rating_module.apply_hard_stops(
        final_score,
        bundle,
        fraud_flags,
        rating_cap=cfg.tran_rating,
    )
    approval = rating_module.APPROVAL_ACTIONS[rating]

    # Nếu top_factors rỗng (fallback), dùng gap analysis từ rule-based layers
    if not top_factors:
        top_factors = _gap_factors(layers, cfg)

    return ScoreReport(
        mst=bundle.meta.get("mst", ""),
        ten=bundle.meta.get("ten_doanh_nghiep", ""),
        phan_khuc=bundle.meta.get("phan_khuc", ""),
        cluster=cluster_id,
        cluster_mo_ta=cfg.mo_ta,
        dqi=dqi.as_dict(),
        raw_score=raw_score,
        dri=dri_result,
        final_score=final_score,
        rating=rating,
        hard_stop=hard_stop,
        approval_action=approval,
        scoring_method=scoring_method,
        layers=layers,
        top_factors=top_factors,
        fraud_flags=fraud_flags,
    )


# ── Scoring strategies ────────────────────────────────────────────────────────

def _score_company(
    bundle: CompanyBundle,
    cluster_id: str,
    cfg: cluster_module.ClusterConfig,
) -> tuple[int, list[dict], str]:
    """
    Ưu tiên ML scoring, fallback về rule-based nếu models chưa có.
    Returns: (raw_score_on_1000_scale, top_factors, scoring_method)
    """
    try:
        from ml.predict import predict, models_available
        if models_available():
            raw, factors = predict(bundle, cluster_id)
            return raw, factors, "ml"
    except ImportError:
        pass

    # Fallback: rule-based cluster scoring
    return _rule_based_score(bundle, cfg), [], "rule_based"


def _rule_based_score(bundle: CompanyBundle, cfg: cluster_module.ClusterConfig) -> int:
    """
    Rule-based scoring với cluster weights.
    Dùng khi ML models chưa được train.
    """
    layers = _run_layers(bundle)
    cluster_raw = 0.0
    for layer_name, result in layers.items():
        cluster_max = cfg.layer_max.get(layer_name, 0)
        if result.available and result.diem_max > 0 and cluster_max > 0:
            cluster_raw += (result.diem_tho / result.diem_max) * cluster_max
    return round(cluster_raw)


def _run_layers(bundle: CompanyBundle) -> dict:
    """Chạy tất cả rule-based layers — dùng cho display và fallback."""
    return {
        "L1_CIC":         layer1_cic.score(bundle.cic),
        "L2_BCTC":        layer2_bctc.score(bundle.bctc),
        "L3A_OPS":        layer3a_ops.score(bundle.einvoices, bundle.bank, bundle.contracts),
        "L3B_COMPLIANCE": layer3b_compliance.score(bundle.compliance),
        "L3C_ESG":        layer3c_esg.score(bundle.esg),
        "L3D_MATURITY":   layer3d_maturity.score(bundle.maturity),
    }


def _gap_factors(layers: dict, cfg: cluster_module.ClusterConfig) -> list[dict]:
    """Gap analysis từ rule-based layers — fallback cho top_factors."""
    factors = []
    for layer_name, result in layers.items():
        if not result.available:
            continue
        cluster_max = cfg.layer_max.get(layer_name, 0)
        if cluster_max == 0 or result.diem_max == 0:
            continue
        scale = cluster_max / result.diem_max

        for crit_name, detail in result.chi_tiet.items():
            if not isinstance(detail, dict) or "diem" not in detail:
                continue
            gap = (detail["max"] - detail["diem"]) * scale
            if gap > 0:
                factors.append({
                    "feature":      f"{result.layer}.{crit_name}",
                    "display_name": crit_name,
                    "shap_value":   round(gap),
                    "feature_value": detail.get("gia_tri"),
                    "direction":    "negative",
                    "mo_ta":        detail.get("mo_ta", ""),
                })
    return sorted(factors, key=lambda x: abs(x["shap_value"]), reverse=True)[:3]
