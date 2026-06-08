"""
Chấm điểm hàng loạt — chạy score() trên nhiều công ty, lưu kết quả ra file.

  python3 score_batch.py            # chấm toàn bộ 5.000 công ty
  python3 score_batch.py --n 100    # chấm 100 công ty đầu

Output (trong data/output/):
  batch_scores.csv   — bảng tổng hợp (1 dòng/công ty), dễ mở Excel/quan sát
  batch_scores.json  — chi tiết đầy đủ (DQI, layers, SHAP) từng công ty
"""

from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path

from data import list_msts, load_company
from scorer import score

OUTPUT_DIR = Path(__file__).parent / "data" / "output"

RATING_ORDER = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "D"]


def run(n: int | None = None):
    msts = list_msts()
    if n:
        msts = msts[:n]

    print(f"Chấm điểm {len(msts)} công ty...")

    rows = []          # cho CSV — tổng hợp
    details = []       # cho JSON — chi tiết
    rating_count = Counter()
    cluster_count = Counter()

    for i, mst in enumerate(msts):
        r = score(load_company(mst))

        rating_count[r.rating] += 1
        cluster_count[r.cluster] += 1

        rows.append({
            "mst":             r.mst,
            "ten":             r.ten,
            "phan_khuc":       r.phan_khuc,
            "cluster":         r.cluster,
            "raw_score":       r.raw_score,
            "dri":             round(r.dri.dri, 3),
            "final_score":     r.final_score,
            "rating":          r.rating,
            "approval_action": r.approval_action,
            "hard_stop":       r.hard_stop or "",
            "scoring_method":  r.scoring_method,
            "dqi_overall":     round(r.dqi.get("overall", 0), 3),
        })

        details.append({
            "mst":             r.mst,
            "ten":             r.ten,
            "rating":          r.rating,
            "final_score":     r.final_score,
            "cluster":         r.cluster,
            "dqi":             r.dqi,
            "layers": {
                name: {"diem_tho": lr.diem_tho, "diem_max": lr.diem_max, "available": lr.available}
                for name, lr in r.layers.items()
            },
            "top_factors":     r.top_factors,
            "hard_stop":       r.hard_stop,
        })

        if (i + 1) % 500 == 0:
            print(f"  [{i + 1}/{len(msts)}]")

    # ── Lưu CSV ───────────────────────────────────────────────────────────────
    import csv
    csv_path = OUTPUT_DIR / "batch_scores.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ── Lưu JSON chi tiết ─────────────────────────────────────────────────────
    json_path = OUTPUT_DIR / "batch_scores.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=2)

    # ── In thống kê ───────────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print(f"  Đã chấm {len(rows)} công ty")
    print("=" * 50)
    print("\n  Phân phối RATING:")
    for grade in RATING_ORDER:
        cnt = rating_count.get(grade, 0)
        pct = cnt / len(rows) * 100
        bar = "█" * int(pct / 2)
        print(f"    {grade:<4} {cnt:>5}  {pct:>5.1f}%  {bar}")

    print("\n  Phân phối CLUSTER:")
    for cl, cnt in cluster_count.most_common():
        pct = cnt / len(rows) * 100
        print(f"    {cl:<10} {cnt:>5}  {pct:>5.1f}%")

    avg = sum(r["final_score"] for r in rows) / len(rows)
    print(f"\n  Điểm cuối trung bình: {avg:.0f}")
    print(f"\n  Lưu:")
    print(f"    {csv_path}")
    print(f"    {json_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=None, help="Số công ty (mặc định: tất cả)")
    args = ap.parse_args()
    run(args.n)
