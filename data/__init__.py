"""Public API for the data module."""

import json
from pathlib import Path

import pandas as pd

from scorer.models import CompanyBundle

_OUTPUT = Path(__file__).parent / "output"

_cache: dict = {}


def _load(name: str) -> dict | list:
    if name not in _cache:
        with open(_OUTPUT / name, encoding="utf-8") as f:
            _cache[name] = json.load(f)
    return _cache[name]


def load_company(mst: str) -> CompanyBundle:
    master_list = _load("companies_master.json")
    meta = next((c for c in master_list if c["mst"] == mst), {"mst": mst})

    return CompanyBundle(
        meta=meta,
        cic=_load("layer1_cic.json").get(mst, {"available": False}),
        bctc=_load("layer2_bctc.json").get(mst, {"available": False}),
        einvoices=_load("layer3a_einvoices.json").get(mst, {"available": False}),
        bank=_load("layer3a_bank_statements.json").get(mst, {"available": False}),
        contracts=_load("layer3a_contracts.json").get(mst, {"available": False}),
        compliance=_load("layer3b_compliance.json").get(mst, {"available": False}),
        esg=_load("layer3c_esg.json").get(mst, {"available": False}),
        maturity=_load("layer3d_maturity.json").get(mst, {"available": False}),
    )


def load_all_flat() -> pd.DataFrame:
    return pd.read_csv(_OUTPUT / "analytics_flat.csv")


def list_msts() -> list[str]:
    return [c["mst"] for c in _load("companies_master.json")]
