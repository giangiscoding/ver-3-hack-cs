# Hướng dẫn tích hợp — dành cho UI Developer

> Tài liệu này mô tả cách gọi backend scoring từ code UI (Streamlit hoặc bất kỳ Python UI nào).
> Không cần hiểu ML hay Neo4j bên trong — chỉ cần biết gọi 3 hàm và đọc kết quả.

---

## 1. Setup môi trường

```bash
# Clone repo
git clone git@github.com:giangiscoding/ver-3-hack-cs.git
cd ver-3-hack-cs

# Cài dependencies
pip install lightgbm scikit-learn numpy pandas neo4j streamlit pyvis plotly

# Sinh dữ liệu 5.000 công ty (chỉ cần chạy 1 lần)
python data/generate_v2.py

# Train model (chỉ cần chạy 1 lần sau generate)
python -m ml.train
python -m ml.calibrate

# Cấu hình Neo4j Aura (lấy credentials từ người phụ trách backend)
export NEO4J_URI="neo4j+s://c2216676.databases.neo4j.io"
export NEO4J_USERNAME="c2216676"
export NEO4J_PASSWORD="<password>"
export NEO4J_DATABASE="c2216676"
```

> **Lưu ý:** Nếu không set env Neo4j, hệ thống vẫn chấm điểm bình thường — chỉ thiếu fraud detection.

---

## 2. Ba hàm cần biết

```python
from data import list_msts, load_company   # lấy danh sách + load dữ liệu DN
from scorer import score                    # chấm điểm
from graph import analyze, available        # phát hiện gian lận
```

### 2.1 Lấy danh sách MST

```python
from data import list_msts

msts = list_msts()   # list 5.000 MST string
# ["7921819600", "0185675104", ...]
```

### 2.2 Load dữ liệu một công ty

```python
from data import load_company

bundle = load_company("7921819600")   # CompanyBundle
# bundle.meta["ten"]         → "Công ty TNHH Dịch Vụ Hoà Phát"
# bundle.meta["phan_khuc"]   → "Small"
# bundle.meta["nganh"]       → "G"
```

### 2.3 Chấm điểm

```python
from scorer import score

report = score(bundle)
# Nếu có fraud flags từ graph:
# report = score(bundle, fraud_flags=["shared_controller"])
```

### 2.4 Phát hiện gian lận (cần Neo4j Aura đang chạy)

```python
from graph import analyze, available

if available():
    fraud = analyze("7921819600")
    fraud.fraud_flags        # ["shared_controller", "circular_transaction"]
    fraud.fraud_risk_score   # 0.0–1.0
    fraud.patterns           # chi tiết bằng chứng từng pattern
```

### 2.5 Gọi đầy đủ end-to-end

```python
from data import load_company
from scorer import score
from graph import analyze, available

def score_company(mst: str):
    bundle = load_company(mst)
    flags = analyze(mst).fraud_flags if available() else []
    return score(bundle, fraud_flags=flags)

report = score_company("7921819600")
```

---

## 3. Cấu trúc ScoreReport

`score()` trả về một object `ScoreReport` với các trường sau:

```python
report.mst              # "7921819600"
report.ten              # "Công ty TNHH Dịch Vụ Hoà Phát"
report.phan_khuc        # "Small" | "Micro" | "Medium"

# ── Kết quả chấm điểm ──────────────────────────────────────────
report.raw_score        # int, điểm ML thô [0–1000]
report.dri.dri          # float [0–1], chỉ số phong phú dữ liệu
report.dri.multiplier   # float, hệ số nhân (0.7 + 0.3×DRI)
report.final_score      # int, raw_score × multiplier

report.rating           # "AAA"|"AA"|"A"|"BBB"|"BB"|"B"|"CCC"|"D"
report.hard_stop        # None hoặc lý do (vd: "Fraud: circular_transaction")
report.approval_action  # "auto_approve"|"auto_reject"|"manual_review"

# ── Phân nhóm & phương pháp ─────────────────────────────────────
report.cluster          # "FULL"|"NO_CIC"|"NO_BCTC"|"L3_ONLY"
report.cluster_mo_ta    # mô tả cluster (hiển thị cho người dùng)
report.scoring_method   # "ml" | "rule_based"

# ── Chất lượng dữ liệu (DQI) ────────────────────────────────────
report.dqi              # dict
# {
#   "cic": 0.60, "bctc": 0.00, "einvoice": 0.83,
#   "bank": 1.00, "compliance": 1.00, "esg": 1.00,
#   "overall": 0.62
# }

# ── Breakdown từng lớp ──────────────────────────────────────────
report.layers           # dict[str, LayerResult]
# Các key: "L1_CIC", "L2_BCTC", "L3A_OPS", "L3B_COMPLIANCE", "L3C_ESG", "L3D_MATURITY"

report.layers["L1_CIC"].diem_tho   # int, điểm đạt
report.layers["L1_CIC"].diem_max   # int, điểm tối đa
report.layers["L1_CIC"].available  # bool, có dữ liệu lớp này không

# ── Top 3 yếu tố ảnh hưởng (SHAP) ──────────────────────────────
report.top_factors      # list[dict], độ dài 0–3
# Mỗi phần tử:
# {
#   "feature":      "l3a_inflow_outflow_ratio",
#   "display_name": "Ngân hàng — Tỷ lệ tiền vào/ra",
#   "shap_value":   144.7,          # đóng góp vào điểm (+ tăng, - giảm)
#   "feature_value": 1.2,           # giá trị thực tế của feature
#   "direction":    "positive",     # "positive" | "negative"
#   "mo_ta":        "... → tăng điểm 145đ"
# }

# ── Fraud ────────────────────────────────────────────────────────
report.fraud_flags      # list[str]
# [] nếu sạch
# ["shared_controller"]                          → giảm 1 bậc rating
# ["circular_transaction"]                       → giảm 1 bậc
# ["shared_controller", "circular_transaction"]  → override D
# ["shell_company"]                              → flag review
```

---

## 4. Dữ liệu bổ sung — load_all_flat()

Để build dashboard tổng hợp (phân phối rating, histogram, v.v.):

```python
from data import load_all_flat

df = load_all_flat()   # pandas DataFrame, ~5000 rows
# Các cột: mst, phan_khuc, nganh, cluster, dqi_overall,
#          raw_score, final_score, rating, fraud_flags, ...
```

---

## 5. Ví dụ code cho từng page UI

### Page 1 — Chọn DN demo

```python
import pandas as pd
from data import list_msts, load_all_flat

df = load_all_flat()

# Filter theo phân khúc
seg = st.selectbox("Phân khúc", ["Tất cả", "Micro", "Small", "Medium"])
if seg != "Tất cả":
    df = df[df["phan_khuc"] == seg]

# Một số case demo thú vị
DEMO_CASES = {
    "DN AAA điển hình":           df[df["rating"] == "AAA"]["mst"].iloc[0],
    "DN D — Fraud cluster":       df[df["fraud_flags"].str.len() > 2]["mst"].iloc[0],
    "Thin-file (chỉ có L3)":     df[df["cluster"] == "L3_ONLY"]["mst"].iloc[0],
    "Bị cưỡng chế thuế":         "lọc từ compliance layer",
}

mst = st.selectbox("Chọn MST", df["mst"].tolist())
```

### Page 2 — Hiển thị score report

```python
report = score_company(mst)

# Rating badge
st.metric("Rating", report.rating)
st.metric("Điểm cuối", report.final_score)
st.write(f"**Action:** {report.approval_action}")

# Nếu bị hard stop → cảnh báo đỏ
if report.hard_stop:
    st.error(f"⛔ {report.hard_stop}")

# Progress bar từng lớp
for name, lr in report.layers.items():
    pct = lr.diem_tho / lr.diem_max if lr.diem_max else 0
    st.write(f"{name}: {lr.diem_tho}/{lr.diem_max}")
    st.progress(pct)

# Top factors
for f in report.top_factors:
    arrow = "↑" if f["direction"] == "positive" else "↓"
    st.write(f"{arrow} {f['display_name']}: {f['mo_ta']}")

# DQI radar/bar
import plotly.express as px
dqi = {k: v for k, v in report.dqi.items() if k != "overall"}
fig = px.bar(x=list(dqi.keys()), y=list(dqi.values()), range_y=[0, 1])
st.plotly_chart(fig)
```

### Page 3 — Graph view

```python
from graph import analyze, available
from pyvis.network import Network
import streamlit.components.v1 as components

if available():
    fraud = analyze(mst)

    net = Network(height="500px", directed=True, bgcolor="#0e1117", font_color="white")

    # Load subgraph của MST từ graph.json
    import json
    g = json.load(open("data/output/graph.json"))

    # Lấy các node liên quan (DN đang xem + connected)
    relevant = {mst} | set(fraud.connected_msts)

    for node in g["nodes"]:
        nid = node["id"]
        if nid not in relevant:
            continue
        if nid == mst:
            color = "#FF4B4B"        # đỏ — DN đang xem
        elif node.get("flag") == "shadow_controller":
            color = "#FFA500"        # cam — shadow controller
        elif nid in fraud.connected_msts:
            color = "#FFD700"        # vàng — liên đới
        else:
            color = "#90EE90"
        net.add_node(nid, label=nid[:8], color=color, title=node.get("type",""))

    for edge in g["edges"]:
        if edge["source"] in relevant or edge["target"] in relevant:
            is_fraud = edge["type"] in ("so_huu_cheo", "giao_dich_noi_bo", "cung_dia_chi")
            net.add_edge(edge["source"], edge["target"],
                         color="#FF0000" if is_fraud else "#555555",
                         width=3 if is_fraud else 1,
                         title=edge["type"])

    net.save_graph("/tmp/graph.html")
    components.html(open("/tmp/graph.html").read(), height=520)

    # Fraud summary
    if fraud.fraud_flags:
        st.error(f"⚠️ Phát hiện: {', '.join(fraud.fraud_flags)}")
        st.write(f"Risk score: {fraud.fraud_risk_score:.2f}")
else:
    st.info("Neo4j chưa kết nối — không có graph view")
```

---

## 6. Lưu ý

| Vấn đề | Giải pháp |
|---|---|
| `available()` trả False | Set env `NEO4J_URI/USERNAME/PASSWORD/DATABASE` trước khi chạy |
| Chưa có data | Chạy `python data/generate_v2.py` |
| Chưa có model | Chạy `python -m ml.train && python -m ml.calibrate` |
| `score()` dùng rule_based thay vì ml | Model chưa train — chạy `ml.train` |
| Import lỗi | Đảm bảo chạy từ root repo, không phải trong subfolder |

Chạy app:
```bash
streamlit run app/main.py
```
