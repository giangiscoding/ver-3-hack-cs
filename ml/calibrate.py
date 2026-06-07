"""
Master scale calibration — suy ra ngưỡng rating từ phân phối điểm thực.

Phương pháp (theo S&P/Moody's master scale):
  1. Chấm ML + DRI cho toàn bộ portfolio
  2. Đặt target credit pyramid (tỷ lệ % mỗi hạng — thực tế cho MSME VN)
  3. Lấy cutoff = percentile tương ứng → ngưỡng rating

Chạy: python -m ml.calibrate
  → in ra RATING_BANDS đã calibrate để dán vào scorer/rating.py
  → lưu ml/models/master_scale.json để kiểm chứng
"""

from __future__ import annotations
import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

sys.path.insert(0, str(Path(__file__).parent.parent))

from data import load_company, list_msts
from scorer.cluster import classify, ALL_CLUSTERS
from scorer import dri as dri_module
from ml.features import extract, CLUSTER_FEATURE_COLS, ALL_FEATURE_COLS

MODELS_DIR = Path(__file__).parent / "models"

# Target credit pyramid cho MSME Việt Nam (% portfolio mỗi hạng).
# Phản ánh: ít DN xuất sắc (AAA/AA), phần lớn ở giữa (BB/B), đuôi rủi ro (CCC/D).
TARGET_PYRAMID = [
    ("AAA",  1),
    ("AA",   4),
    ("A",   12),
    ("BBB", 20),
    ("BB",  21),
    ("B",   19),
    ("CCC", 12),
    ("D",   11),
]


def _round_to(x: float, base: int = 10) -> int:
    return int(round(x / base) * base)


def compute_scores() -> np.ndarray:
    """Chấm blended ML + DRI cho toàn bộ portfolio → mảng final scores."""
    with open(MODELS_DIR / "blend.json", encoding="utf-8") as f:
        blend = json.load(f)
    weights = blend["weights"]
    global_model = joblib.load(MODELS_DIR / "global.pkl")
    cluster_models = {c: joblib.load(MODELS_DIR / f"cluster_{c}.pkl") for c in ALL_CLUSTERS}

    finals = []
    for mst in list_msts():
        b = load_company(mst)
        cid = classify(b)
        feats = extract(b)
        Xg = pd.DataFrame([{c: feats.get(c) for c in ALL_FEATURE_COLS}], columns=ALL_FEATURE_COLS).astype(float)
        Xc = pd.DataFrame([{c: feats.get(c) for c in CLUSTER_FEATURE_COLS[cid]}], columns=CLUSTER_FEATURE_COLS[cid]).astype(float)
        w = weights.get(cid, 0.6)
        raw = w * float(global_model.predict(Xg)[0]) + (1 - w) * float(cluster_models[cid].predict(Xc)[0])
        mult = dri_module.compute(b).multiplier
        finals.append(raw * mult)
    return np.array(finals)


def calibrate(scores: np.ndarray) -> list[tuple[int, int, str]]:
    """Suy ra rating bands từ target pyramid + phân phối điểm."""
    # Cộng dồn từ hạng thấp nhất (D) lên → cutoff dưới của mỗi hạng
    grades_low_to_high = list(reversed(TARGET_PYRAMID))  # D, CCC, ... AAA
    cum = 0
    cutoffs = {}  # grade → lower cutoff
    for grade, pct in grades_low_to_high:
        cutoffs[grade] = _round_to(np.percentile(scores, cum)) if cum > 0 else 0
        cum += pct

    # Tạo bands (lo, hi, grade) từ cao xuống thấp
    bands = []
    ordered = [g for g, _ in TARGET_PYRAMID]  # AAA → D
    for i, grade in enumerate(ordered):
        lo = cutoffs[grade]
        hi = 1001 if i == 0 else cutoffs[ordered[i - 1]]
        bands.append((lo, hi, grade))
    return bands


def run():
    print("=" * 60)
    print("Master scale calibration")
    print("=" * 60)
    print("Computing portfolio scores (ML × DRI)...")
    scores = compute_scores()
    print(f"  n={len(scores)} | mean={scores.mean():.0f} | std={scores.std():.0f}")
    print(f"  range: [{scores.min():.0f}, {scores.max():.0f}]")

    bands = calibrate(scores)

    print("\nCalibrated RATING_BANDS (dán vào scorer/rating.py):")
    print("RATING_BANDS = [")
    for lo, hi, grade in bands:
        print(f"    ({lo:>4}, {hi:>4}, {grade!r}),")
    print("]")

    # Kiểm chứng phân phối thực tế
    print("\nVerify distribution:")
    print(f"  {'Grade':<6}{'target%':>8}{'actual%':>9}{'n':>7}")
    for lo, hi, grade in bands:
        n = int(((scores >= lo) & (scores < hi)).sum())
        target = dict(TARGET_PYRAMID)[grade]
        print(f"  {grade:<6}{target:>7}%{n/len(scores)*100:>8.1f}%{n:>7}")

    # Lưu
    out = {
        "method": "S&P/Moody's master scale calibration",
        "target_pyramid": dict(TARGET_PYRAMID),
        "bands": [[lo, hi, g] for lo, hi, g in bands],
        "portfolio_stats": {
            "n": len(scores), "mean": round(float(scores.mean()), 1),
            "std": round(float(scores.std()), 1),
        },
    }
    MODELS_DIR.mkdir(exist_ok=True)
    with open(MODELS_DIR / "master_scale.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n→ Saved: {MODELS_DIR / 'master_scale.json'}")


if __name__ == "__main__":
    run()
