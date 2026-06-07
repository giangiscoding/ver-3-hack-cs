# Graph Fraud Detection Module

**Vị trí:** `graph/`  
**Vai trò:** Phân tích mạng quan hệ doanh nghiệp → phát hiện gian lận → trả về `FraudReport`

← [README](../README.md) · [01_data.md](01_data.md)  
→ Output sang: [05_rating.md](05_rating.md) · [06_ui.md](06_ui.md)

---

## Vị trí trong kiến trúc modular monolith

> **Graph DB = Neo4j.** Phát hiện gian lận bằng **Cypher** chạy trên Neo4j (không
> phải xử lý in-memory). Kết nối cấu hình qua biến môi trường `NEO4J_*` → chạy được
> với **Neo4j Aura (cloud)** hoặc Neo4j local/Docker.

```
graph/
├── __init__.py              ← public API: analyze, analyze_all, available, FraudReport
├── connection.py            ← Neo4j driver (env-config) + ping/run_query/run_write
├── queries.py               ← Cypher: schema · load · 3 fraud patterns
├── loader.py                ← nạp graph.json → Neo4j (python -m graph.loader)
├── detector.py              ← chạy Cypher → FraudReport + risk score
├── models.py                ← FraudReport
└── smoke_test.py            ← test offline (shaping) + online (Neo4j)
```

**Public API:**

```python
from graph import analyze, available

if available():                       # Neo4j đang chạy?
    report = analyze("7921819600")    # FraudReport
    report.fraud_flags                # ["shared_controller", "circular_transaction"]
    report.fraud_risk_score           # 0.0–1.0
    report.connected_msts             # DN liên đới trong cluster
    report.patterns                   # bằng chứng từng pattern
```

Tích hợp scorer: `score(bundle, fraud_flags=analyze(mst).fraud_flags)`.
Flags khớp `scorer/rating.py`: circular_transaction + shared_controller → **D**;
shared_controller đơn lẻ → **giảm 1 bậc**.

---

## Mô hình đồ thị Neo4j

```
(:Company {mst, phan_khuc, nganh})
(:Owner   {id, ten, flag})
(:Owner)-[:OWNS {phan_tram}]->(:Company)          # sở hữu thường
(:Owner)-[:OWNS_CROSS {phan_tram}]->(:Company)    # sở hữu chéo → shadow controller
(:Company)-[:SAME_ADDRESS]->(:Company)            # cùng địa chỉ → shell
(:Company)-[:INTERNAL_TXN {gia_tri}]->(:Company)  # giao dịch nội bộ → circular
(:Company)-[:TRADE {gia_tri}]->(:Company)         # giao dịch thương mại hợp lệ
```

3 Cypher phát hiện (xem `graph/queries.py`):

```cypher
-- 1. Shadow controller: chủ sở hữu nắm chéo >= 2 DN
MATCH (o:Owner)-[:OWNS_CROSS]->(:Company {mst:$mst})
MATCH (o)-[:OWNS_CROSS]->(other:Company)
WITH o, collect(DISTINCT other.mst) AS companies
WHERE size(companies) >= 2 RETURN o.id, companies

-- 2. Shell: chia sẻ địa chỉ
MATCH (c:Company {mst:$mst})-[:SAME_ADDRESS]-(other:Company)
RETURN collect(DISTINCT other.mst) AS companies

-- 3. Circular: vòng giao dịch nội bộ quay về chính nó
MATCH path = (c:Company {mst:$mst})-[:INTERNAL_TXN*1..10]->(c)
RETURN [n IN nodes(path) | n.mst] AS ring LIMIT 1
```

---

## Chạy Neo4j

**Cách A — Docker (máy có Docker):**

```bash
docker compose up -d                    # Neo4j tại bolt://localhost:7687
python -m graph.loader --clear          # nạp graph.json
python -m graph.smoke_test              # kiểm tra phát hiện
```

**Cách B — Neo4j Aura (cloud, không cần cài gì):**

```bash
export NEO4J_URI="neo4j+s://<id>.databases.neo4j.io"
export NEO4J_USER=neo4j
export NEO4J_PASSWORD="<password>"
python -m graph.loader --clear
```

Browser xem đồ thị: `http://localhost:7474` (Docker) hoặc console Aura.

---

## Schema graph.json

### Nodes

| Field | Type | Mô tả |
| ----- | ---- | ------ |
| `id` | str | MST hoặc `owner_<mst>` hoặc `shadow_controller_<n>` |
| `type` | str | `doanh_nghiep` · `chu_so_huu` |
| `phan_khuc` | str | Micro / Small / Medium (chỉ cho DN node) |
| `nganh` | str | Mã ngành (chỉ cho DN node) |
| `flag` | str? | `shadow_controller` nếu là node gian lận |

### Edges

| `type` | Ý nghĩa | Flag gian lận |
| ------ | -------- | ------------- |
| `so_huu` | Chủ sở hữu hợp pháp | Không |
| `so_huu_cheo` | Cùng controller ẩn | ✅ `shadow_controller` |
| `cung_dia_chi` | Cùng địa chỉ | ✅ `possible_shell` |
| `giao_dich_noi_bo` | Giao dịch vòng | ✅ `circular_transaction` |
| `giao_dich_thuong_mai` | Giao dịch thông thường | Không |

---

## Ba fraud patterns — Cypher trên Neo4j

Toàn bộ detection chạy bằng **Cypher** trong `graph/detector.py`. Không dùng xử lý in-memory.

### Pattern 1 — Shadow Controller (Chủ ẩn chung)

**Định nghĩa:** Một cá nhân/tổ chức kiểm soát ngầm ≥ 2 DN, không công bố (sở hữu chéo 15–49%).

```cypher
MATCH (o:Owner)-[:OWNS_CROSS]->(:Company {mst: $mst})
MATCH (o)-[:OWNS_CROSS]->(other:Company)
WITH o, collect(DISTINCT other.mst) AS companies
WHERE size(companies) >= 2
RETURN o.id AS controller, o.ten AS ten, companies
ORDER BY size(companies) DESC LIMIT 1
```

**Risk score:** +0.45

---

### Pattern 2 — Shell Company (Công ty vỏ)

**Định nghĩa:** DN dùng chung địa chỉ với DN khác — dấu hiệu địa chỉ ảo.

```cypher
MATCH (c:Company {mst: $mst})-[:SAME_ADDRESS]-(other:Company)
RETURN collect(DISTINCT other.mst) AS companies
```

**Risk score:** +0.30

---

### Pattern 3 — Circular Transaction (Giao dịch vòng)

**Định nghĩa:** Nhóm DN A → B → … → A, thổi phồng doanh thu lẫn nhau. Cypher duyệt tới 10 hop (vòng trong data dài tới 8 DN).

```cypher
MATCH path = (c:Company {mst: $mst})-[:INTERNAL_TXN*1..10]->(c)
RETURN [n IN nodes(path) | n.mst] AS ring, length(path) AS len
ORDER BY len LIMIT 1
```

**Risk score:** +0.55

---

## Tính Fraud Risk Score

```text
risk_score = W_CIRCULAR·circular + W_SHADOW·shadow + W_SHELL·shell   (capped 1.0)
           = 0.55·{0,1} + 0.45·{0,1} + 0.30·{0,1}
```

| Risk Score | Mức độ | Hành động |
| ---------- | ------ | --------- |
| 0.0–0.2 | Thấp | Không tác động |
| 0.2–0.5 | Trung bình | Flag để review thủ công |
| 0.5–0.8 | Cao | Giảm hạng 1 bậc |
| > 0.8 | Rất cao | Override → D |

**Kết quả smoke test thực tế (Neo4j Aura):**

```text
analyze(0276783908) → flags=['shared_controller', 'circular_transaction']  risk=1.00 → D
analyze(7988437136) → flags=['shared_controller']                          risk=0.45 → giảm 1 bậc
```

---

## Output: FraudReport

```python
@dataclass
class FraudReport:
    mst: str
    fraud_flags: list[str]        # ["shared_controller", "circular_transaction", "shell_company"]
    fraud_risk_score: float       # 0.0–1.0
    patterns: dict                # bằng chứng từng pattern (MST liên đới, ring...)
    connected_msts: list[str]     # DN liên đới trong cluster

    @property
    def is_high_risk(self) -> bool:
        return self.fraud_risk_score >= 0.8
```
