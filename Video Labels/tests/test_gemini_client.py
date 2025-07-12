import pytest
from src.gemini_client import identify_media

def test_identify_media(monkeypatch):
    # Mock API response
    class MockResponse:
        text = '{"type": "tv", "name": "Test Show", "season": 1, "episode": 1, "is_special": false}'
    
    def mock_generate(*args, **kwargs):
        return MockResponse()
    
    monkeypatch.setattr("google.generativeai.GenerativeModel.generate_content", mock_generate)
    result = identify_media("test.mp4")
    assert result["type"] == "tv" 