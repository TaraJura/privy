from pathlib import Path

from privy_cli.mapping_store import MappingData, MappingStoreError, read_mapping, write_mapping

import pytest


def test_mapping_store_roundtrip(tmp_path: Path) -> None:
    mapping = MappingData.create_empty()
    mapping.placeholders["PERSON_001"] = {"label": "PERSON", "original": "Jane Doe"}

    map_path = tmp_path / "mapping.json"
    write_mapping(map_path, mapping)

    loaded = read_mapping(map_path)
    assert loaded.placeholders == mapping.placeholders


def test_mapping_store_missing_file(tmp_path: Path) -> None:
    with pytest.raises(MappingStoreError):
        read_mapping(tmp_path / "does_not_exist.json")
