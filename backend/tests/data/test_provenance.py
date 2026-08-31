"""F4 smoke tests — provenance sidecar roundtrip + audit."""

from __future__ import annotations

from pathlib import Path

import pytest

from oohscout.data import (
    SIDECAR_EXTENSION,
    SourceRecord,
    audit_provenance,
    read_source_yaml,
    sidecar_path_for,
    write_source_yaml,
)


def _make_dummy_data_file(tmp_path: Path, name: str = "dummy.gpkg") -> Path:
    """Create a placeholder file — content doesn't matter, only extension does."""
    path = tmp_path / name
    path.write_bytes(b"placeholder - real .gpkg not needed for provenance tests")
    return path


def _sample_record() -> SourceRecord:
    return SourceRecord(
        source_name="Test Source",
        source_url="https://example.com/data",
        record_count=42,
        license="CC-BY 4.0",
        commercial_use_allowed=True,
        redistribution_allowed=True,
        authority="Example Authority",
        notes="synthetic record for tests",
    )


def test_sidecar_path_swaps_extension(tmp_path: Path) -> None:
    data = tmp_path / "mclennan_boundary.gpkg"
    assert sidecar_path_for(data) == tmp_path / f"mclennan_boundary{SIDECAR_EXTENSION}"


def test_write_and_read_roundtrip(tmp_path: Path) -> None:
    data = _make_dummy_data_file(tmp_path)
    record = _sample_record()

    sidecar = write_source_yaml(data, record)

    assert sidecar.exists()
    loaded = read_source_yaml(data)
    assert loaded["source_name"] == "Test Source"
    assert loaded["record_count"] == 42
    assert loaded["commercial_use_allowed"] is True
    assert loaded["retrieval_date"]  # auto-filled with today's date


def test_read_missing_sidecar_raises(tmp_path: Path) -> None:
    data = _make_dummy_data_file(tmp_path)
    with pytest.raises(FileNotFoundError):
        read_source_yaml(data)


def test_audit_finds_missing(tmp_path: Path) -> None:
    covered = _make_dummy_data_file(tmp_path, "covered.gpkg")
    uncovered = _make_dummy_data_file(tmp_path, "uncovered.geojson")

    write_source_yaml(covered, _sample_record())

    data_files, missing = audit_provenance(tmp_path)

    assert set(data_files) == {covered, uncovered}
    assert missing == [uncovered]


def test_audit_passes_when_all_covered(tmp_path: Path) -> None:
    a = _make_dummy_data_file(tmp_path, "a.gpkg")
    b = _make_dummy_data_file(tmp_path, "b.geojson")

    write_source_yaml(a, _sample_record())
    write_source_yaml(b, _sample_record())

    data_files, missing = audit_provenance(tmp_path)

    assert len(data_files) == 2
    assert missing == []


def test_audit_ignores_the_sidecars_themselves(tmp_path: Path) -> None:
    """Sidecar files must never be treated as datasets needing their own sidecars."""
    data = _make_dummy_data_file(tmp_path, "real.gpkg")
    write_source_yaml(data, _sample_record())

    data_files, missing = audit_provenance(tmp_path)

    assert data_files == [data]  # only the .gpkg, not the .source.yaml
    assert missing == []


def test_project_processed_dir_is_fully_covered() -> None:
    """The real backend/data/processed/ folder must have zero missing sidecars.

    This is the F4 completion gate. If someone adds a new .gpkg without a
    matching .source.yaml, this test fails and the build breaks.
    """
    processed = Path("backend/data/processed")
    if not processed.exists():
        pytest.skip("backend/data/processed/ does not exist yet on this checkout")

    data_files, missing = audit_provenance(processed)
    assert missing == [], (
        f"Missing provenance sidecars for {len(missing)} data files: "
        + ", ".join(f.name for f in missing)
    )
