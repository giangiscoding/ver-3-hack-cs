"""
Training pipeline — STACKED BLEND architecture.

  score = w_cluster · global(x) + (1 - w_cluster) · cluster_model(x)

  - Global LightGBM: 1 model, FULL feature set, NaN-native → nền khử nhiễu (pool toàn bộ data)
  - Per-cluster model: auto-chọn loại tốt nhất theo CV (ml/registry.py) → tinh chỉnh riêng nhóm
  - w_cluster: trọng số blend, tune trên VALIDATION (không leak test). Thin-file → w cao
    (dựa nhiều vào global vì ít data); FULL → w thấp (cluster model đóng góp nhiều).

Target: health_score × 1000 (proxy creditworthiness; production thay bằng PD lịch sử).

Chạy: python -m ml.train
"""

from __future__ import annotations
import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

sys.path.insert(0, str(Path(__file__).parent.parent))

from data import load_company, list_msts
from scorer.cluster import ALL_CLUSTERS, classify
from ml.features import extract, CLUSTER_FEATURE_COLS, ALL_FEATURE_COLS
from ml import registry

MODELS_DIR = Path(__file__).parent / "models"
SEED = 42

GLOBAL_PARAMS = dict(n_estimators=400, learning_rate=0.05, max_depth=6, num_leaves=63,
                     min_child_samples=20, subsample=0.8, colsample_bytree=0.8,
                     reg_alpha=0.1, reg_lambda=1.0, random_state=SEED, verbose=-1)

WEIGHT_GRID = np.linspace(0.0, 1.0, 21)


def build_dataset() -> pd.DataFrame:
    flat = pd.read_csv(
        Path(__file__).parent.parent / "data" / "output" / "analytics_flat.csv",
        dtype={"mst": str},
    ).set_index("mst")

    records = []
    for mst in list_msts():
        b = load_company(mst)
        feats = extract(b)
        feats["mst"] = mst
        feats["cluster"] = classify(b)
        feats["target"] = round(flat.loc[mst, "health_score"] * 1000, 1)
        records.append(feats)
    df = pd.DataFrame(records).set_index("mst")
    print("  Cluster distribution:")
    for c, n in df["cluster"].value_counts().sort_index().items():
        print(f"    {c}: {n}")
    return df


def _fit_global(train_df) -> lgb.LGBMRegressor:
    m = lgb.LGBMRegressor(**GLOBAL_PARAMS)
    m.fit(train_df[ALL_FEATURE_COLS].astype(float), train_df["target"].values)
    return m


def _fit_cluster(train_df, cid: str, model_name: str):
    cols = CLUSTER_FEATURE_COLS[cid]
    sub = train_df[train_df["cluster"] == cid]
    m = registry.build(model_name)
    m.fit(sub[cols].astype(float), sub["target"].values)
    return m


def run():
    print("=" * 64)
    print("STACKED BLEND training — global + per-cluster + blend weights")
    print("=" * 64)
    df = build_dataset()

    # ── Tách validation để (1) chọn model type, (2) tune blend weight — không leak test
    train_df, val_df = train_test_split(df, test_size=0.20, random_state=SEED, stratify=df["cluster"])

    # ── 1) Chọn loại model tốt nhất mỗi cluster (CV trên train) ───────────────
    print("\n[1] Auto-select model type per cluster (CV):")
    chosen = {}
    for cid in ALL_CLUSTERS:
        cols = CLUSTER_FEATURE_COLS[cid]
        sub = train_df[train_df["cluster"] == cid]
        name, cv_mae = registry.select_best(sub[cols].astype(float), sub["target"].values)
        chosen[cid] = name
        print(f"    {cid:<10} → {name:<12} (CV MAE={cv_mae:.1f})")

    # ── 2) Tune blend weight mỗi cluster trên validation ──────────────────────
    print("\n[2] Tune blend weight per cluster (validation):")
    g_val = _fit_global(train_df)
    pg_val = g_val.predict(val_df[ALL_FEATURE_COLS].astype(float))
    weights = {}
    for cid in ALL_CLUSTERS:
        cm = _fit_cluster(train_df, cid, chosen[cid])
        mask = (val_df["cluster"] == cid).values
        if mask.sum() == 0:
            weights[cid] = 0.6
            continue
        cols = CLUSTER_FEATURE_COLS[cid]
        pc = cm.predict(val_df[mask][cols].astype(float))
        y = val_df[mask]["target"].values
        best_w, best_mae = 0.6, float("inf")
        for w in WEIGHT_GRID:
            mae = mean_absolute_error(y, w * pg_val[mask] + (1 - w) * pc)
            if mae < best_mae:
                best_w, best_mae = float(w), mae
        weights[cid] = round(best_w, 2)
        g_only = mean_absolute_error(y, pg_val[mask])
        print(f"    {cid:<10} w_global={best_w:.2f}  blend MAE={best_mae:.1f}  (global={g_only:.1f})")

    # ── 3) Refit global + cluster trên TOÀN BỘ data cho production ─────────────
    print("\n[3] Refit on full dataset & save...")
    MODELS_DIR.mkdir(exist_ok=True)
    g_full = _fit_global(df)
    joblib.dump(g_full, MODELS_DIR / "global.pkl")
    for cid in ALL_CLUSTERS:
        cm = _fit_cluster(df, cid, chosen[cid])
        joblib.dump(cm, MODELS_DIR / f"cluster_{cid}.pkl")

    blend_meta = {
        "architecture": "stacked_blend",
        "formula": "score = w·global(x) + (1-w)·cluster(x)",
        "weights": weights,
        "model_types": chosen,
        "feature_cols": {cid: CLUSTER_FEATURE_COLS[cid] for cid in ALL_CLUSTERS},
        "global_feature_cols": ALL_FEATURE_COLS,
    }
    with open(MODELS_DIR / "blend.json", "w", encoding="utf-8") as f:
        json.dump(blend_meta, f, ensure_ascii=False, indent=2)

    # ── 4) Report blend vs global trên validation ─────────────────────────────
    print("\n[4] Validation summary (blend vs global):")
    blend_pred = np.zeros(len(val_df))
    cm_val = {cid: _fit_cluster(train_df, cid, chosen[cid]) for cid in ALL_CLUSTERS}
    for cid in ALL_CLUSTERS:
        mask = (val_df["cluster"] == cid).values
        if mask.sum() == 0:
            continue
        cols = CLUSTER_FEATURE_COLS[cid]
        pc = cm_val[cid].predict(val_df[mask][cols].astype(float))
        blend_pred[mask] = weights[cid] * pg_val[mask] + (1 - weights[cid]) * pc
    yv = val_df["target"].values
    print(f"    Global  MAE={mean_absolute_error(yv, pg_val):.1f}  R²={r2_score(yv, pg_val):.3f}")
    print(f"    Blend   MAE={mean_absolute_error(yv, blend_pred):.1f}  R²={r2_score(yv, blend_pred):.3f}")

    print("\nSaved: global.pkl, cluster_*.pkl, blend.json")


if __name__ == "__main__":
    run()
