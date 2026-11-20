import pytest
from ews.artifacts import month_key, publication, seal, verify_artifacts

def test_directory_is_visible_only_after_success(tmp_path):
    destination = tmp_path / "result"
    with pytest.raises(RuntimeError), publication(destination) as staging:
        (staging / "scored.csv").write_text("partial")
        raise RuntimeError("simulated failure")
    assert not destination.exists()
    with publication(destination) as staging:
        (staging / "scored.csv").write_text("complete")
        seal(staging, "snapshot")
    assert verify_artifacts(destination, "snapshot")["kind"] == "snapshot"
    with pytest.raises(ValueError, match="đã tồn tại"), publication(destination):
        pytest.fail("Existing results must be preserved")
    (destination / "scored.csv").write_text("changed")
    with pytest.raises(ValueError, match="Checksum"):
        verify_artifacts(destination)

@pytest.mark.parametrize("value", ["2024-9", "2024-13", "2024-09-01", "09/2024"])
def test_month_must_use_canonical_format(value):
    with pytest.raises(ValueError, match="YYYY-MM"):
        month_key(value)