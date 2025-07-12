import pytest
from src.file_scanner import scan_videos
from pathlib import Path

def test_scan_videos(tmp_path):
    (tmp_path / "video.mp4").touch()
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "movie.mkv").touch()
    files = scan_videos(str(tmp_path))
    assert len(files) == 2 