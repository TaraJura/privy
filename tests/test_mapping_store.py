from pathlib import Path

import pytest

from privy_cli.mapping_store import MappingData, MappingStoreError, read_encrypted_mapping, write_encrypted_mapping


def test_mapping_store_roundtrip(tmp_path: Path) -> None:
    mapping = MappingData.create_empty()
    mapping.placeholders["PERSON_001"] = {"label": "PERSON", "original": "Jane Doe"}

    map_path = tmp_path / "mapping.enc.json"
    write_encrypted_mapping(map_path, mapping, password="secret-123")

    loaded = read_encrypted_mapping(map_path, password="secret-123")
    assert loaded.placeholders == mapping.placeholders


def test_mapping_store_wrong_password(tmp_path: Path) -> None:
    mapping = MappingData.create_empty()
    mapping.placeholders["COMPANY_001"] = {"label": "COMPANY", "original": "Acme LLC"}

    map_path = tmp_path / "mapping.enc.json"
    write_encrypted_mapping(map_path, mapping, password="correct")

    with pytest.raises(MappingStoreError):
        read_encrypted_mapping(map_path, password="incorrect")
