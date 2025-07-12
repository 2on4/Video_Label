import pytest
from src.media_organiser import organize_files
# TODO: Add comprehensive tests with mocks for scan_videos, identify_media, etc.
def test_organize_files(tmp_path):
    # Basic smoke test; expand with mocks
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    organize_files(str(source), str(target), dry_run=True)  # Should not raise 