"""
Kết nối Neo4j — cấu hình qua biến môi trường (chạy được với Aura cloud hoặc local/Docker).

  NEO4J_URI       mặc định bolt://localhost:7687  (Aura: neo4j+s://xxxx.databases.neo4j.io)
  NEO4J_USER      mặc định neo4j
  NEO4J_PASSWORD  mặc định neo4jpassword
  NEO4J_DATABASE  mặc định neo4j

Driver là singleton lazy. `ping()` kiểm tra kết nối — dùng để fallback nhẹ nhàng
nếu Neo4j chưa chạy (demo không vỡ).
"""

from __future__ import annotations
import os
from functools import lru_cache

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
# Aura dùng NEO4J_USERNAME; local/Docker dùng NEO4J_USER — hỗ trợ cả hai
NEO4J_USER = os.environ.get("NEO4J_USERNAME") or os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "neo4jpassword")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")


@lru_cache(maxsize=1)
def get_driver():
    """Trả về Neo4j driver singleton (chưa kết nối tới khi chạy query đầu tiên)."""
    from neo4j import GraphDatabase
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def run_query(cypher: str, **params):
    """Chạy một Cypher query, trả về list các record (dict)."""
    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(cypher, **params)
        return [record.data() for record in result]


def run_write(cypher: str, **params):
    """Chạy Cypher ghi dữ liệu trong managed transaction."""
    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        return session.execute_write(lambda tx: tx.run(cypher, **params).consume())


def ping() -> bool:
    """True nếu kết nối Neo4j sống. Dùng để quyết định fallback."""
    try:
        driver = get_driver()
        driver.verify_connectivity()
        return True
    except Exception:
        return False


def close():
    try:
        get_driver().close()
        get_driver.cache_clear()
    except Exception:
        pass
