import pytest
from src.utils import clean_filename, get_quality
from pathlib import Path

def test_clean_filename():
    assert clean_filename('bad:name?*/') == 'bad-name---'

def test_get_quality(tmp_path):
    # Mock file; actual ffprobe test needs video file, so test fallback
    file = tmp_path / "test.txt"
    file.write_text("data")
    assert get_quality(file) == 4  # size of "data" 