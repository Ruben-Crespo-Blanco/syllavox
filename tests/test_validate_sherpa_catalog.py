from __future__ import annotations

from scripts.validate_sherpa_catalog import (
    V042_MIMIC3_BUNDLES,
    _metadata_result,
)
from syllavox.tts.catalog_client import SherpaCatalogClient


def test_v042_validation_catalog_is_complete() -> None:
    entries = {
        entry.bundle_id: entry
        for entry in SherpaCatalogClient().fetch_catalog()
    }

    assert set(V042_MIMIC3_BUNDLES) <= entries.keys()
    assert all(
        _metadata_result(entries[bundle_id])["status"] == "ok"
        for bundle_id in V042_MIMIC3_BUNDLES
    )
