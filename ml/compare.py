"""
So sánh 3 kiến trúc scoring trên CÙNG held-out test set (công bằng, tái lập được).

  [1] Global LightGBM    — 1 model, full feature set, NaN-native
  [2] Pure router        — model riêng mỗi cluster (auto-chọn loại theo CV), KHÔNG global
  [3] Stacked blend      — w·global + (1-w)·cluster, w tune trên validation

KẾT QUẢ (đã chạy nhiều lần, vững):
  - Pure router THUA global ~3-6%: global pool toàn bộ data → khử nhiễu bước
    feature→fundamental tốt hơn, nhất là thin-file (ít data riêng).
  - Stacked blend THẮNG global ~3%: cluster model tinh chỉnh trên nền global.
    Trọng số blend: FULL/NO_CIC dựa nhiều vào cluster; L3_ONLY dựa thuần global
    (thin-file thật sự cần pooling).

Chạy: python -m ml.compare
"""

from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

sys.path.insert(0, str(Path(__file__).parent.parent))

from data import load_company, list_msts
from scorer.cluster import ALL_CLUSTERS, classify
from ml.features import extract, CLUSTER_FEATURE_COLS, ALL_FEATURE_COLS
from ml import registry
from ml.train import GLOBAL_PARAMS, WEIGHT_GRID

SEED = 42


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
        feats["target"] = flat.loc[mst, "health_score"] * 1000
        records.append(feats)
    return pd.DataFrame(records).set_index("mst")


def run():
    print("=" * 66)
    print("So sánh 3 kiến trúc: Global / Pure-router / Stacked-blend")
    print("=" * 66)
    df = build_dataset()
    trainval, test = train_test_split(df, test_size=0.20, random_state=SEED, stratify=df["cluster"])
    train, val = train_test_split(trainval, test_size=0.20, random_state=SEED, stratify=trainval["cluster"])
    print(f"Train {len(train)} | Val {len(val)} | Test {len(test)}\n")
    y_test = test["target"].values
    tc = test["cluster"].values

    # [1] Global ----------------------------------------------------------------
    g = lgb.LGBMRegressor(**GLOBAL_PARAMS)
    g.fit(trainval[ALL_FEATURE_COLS].astype(float), trainval["target"].values)
    pg = g.predict(test[ALL_FEATURE_COLS].astype(float))

    # [2] Pure router (auto-select model per cluster) ---------------------------
    chosen, cmodels = {}, {}
    for cid in ALL_CLUSTERS:
        cols = CLUSTER_FEATURE_COLS[cid]
        sub = trainval[trainval["cluster"] == cid]
        name, _ = registry.select_best(sub[cols].astype(float), sub["target"].values)
        chosen[cid] = name
        cmodels[cid] = registry.build(name).fit(sub[cols].astype(float), sub["target"].values)
    pr = np.zeros(len(test))
    for i, (idx, row) in enumerate(test.iterrows()):
        cid = row["cluster"]
        X = pd.DataFrame([row[CLUSTER_FEATURE_COLS[cid]]], columns=CLUSTER_FEATURE_COLS[cid]).astype(float)
        pr[i] = cmodels[cid].predict(X)[0]

    # [3] Stacked blend (weights tuned on val) ----------------------------------
    g_tr = lgb.LGBMRegressor(**GLOBAL_PARAMS).fit(train[ALL_FEATURE_COLS].astype(float), train["target"].values)
    pg_val = g_tr.predict(val[ALL_FEATURE_COLS].astype(float))
    weights = {}
    cmodels_tr = {}
    for cid in ALL_CLUSTERS:
        cols = CLUSTER_FEATURE_COLS[cid]
        sub = train[train["cluster"] == cid]
        cmodels_tr[cid] = registry.build(chosen[cid]).fit(sub[cols].astype(float), sub["target"].values)
        mask = (val["cluster"] == cid).values
        pc = cmodels_tr[cid].predict(val[mask][cols].astype(float))
        yv = val[mask]["target"].values
        best_w, best_mae = 0.6, float("inf")
        for w in WEIGHT_GRID:
            mae = mean_absolute_error(yv, w * pg_val[mask] + (1 - w) * pc)
            if mae < best_mae:
                best_w, best_mae = float(w), mae
        weights[cid] = round(best_w, 2)
    pb = np.zeros(len(test))
    for i, (idx, row) in enumerate(test.iterrows()):
        cid = row["cluster"]; w = weights[cid]
        X = pd.DataFrame([row[CLUSTER_FEATURE_COLS[cid]]], columns=CLUSTER_FEATURE_COLS[cid]).astype(float)
        pb[i] = w * pg[i] + (1 - w) * cmodels[cid].predict(X)[0]

    # ── Report ─────────────────────────────────────────────────────────────────
    def line(name, pred):
        return f"{name:<16}{mean_absolute_error(y_test, pred):>9.1f}{r2_score(y_test, pred):>9.3f}"
    print(f"{'Architecture':<16}{'MAE':>9}{'R²':>9}")
    print("-" * 36)
    print(line("Global", pg))
    print(line("Pure router", pr))
    print(line("Stacked blend", pb))
    mae_g = mean_absolute_error(y_test, pg)
    print(f"\n  Pure router  vs global: {(mae_g - mean_absolute_error(y_test, pr)) / mae_g * 100:+.1f}%")
    print(f"  Stacked blend vs global: {(mae_g - mean_absolute_error(y_test, pb)) / mae_g * 100:+.1f}%")

    print(f"\n{'Cluster':<10}{'model':>12}{'w_global':>10}{'global':>9}{'blend':>9}{'Δ%':>8}")
    print("-" * 60)
    for cid in ALL_CLUSTERS:
        m = tc == cid
        a = mean_absolute_error(y_test[m], pg[m]); b = mean_absolute_error(y_test[m], pb[m])
        print(f"{cid:<10}{chosen[cid]:>12}{weights[cid]:>10.2f}{a:>9.1f}{b:>9.1f}{(a-b)/a*100:>7.1f}%")


if __name__ == "__main__":
    run()
