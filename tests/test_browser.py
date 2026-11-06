import pytest

from browser.controller import BrowserController, parse_video_data


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost",
        "http://127.0.0.1",
        "http://192.168.1.1",
        "file:///etc/passwd",
    ],
)
def test_open_url_rejects_local_or_invalid_addresses(url):
    browser = BrowserController(headless=True)

    with pytest.raises(ValueError):
        browser.open_url(url)   

def test_parse_video_data_returns_video():
    raw_data = [
        {
            "title": "Gostava Tanto de Você",
            "channel": "Tim Maia",
            "duration": "3:45",
            "metadata": "1 milhão de visualizações",
            "url": "https://www.youtube.com/watch?v=example",
        }
    ]

    videos = parse_video_data(raw_data)

    assert len(videos) == 1
    assert videos[0].title == "Gostava Tanto de Você"
    assert videos[0].channel == "Tim Maia"
    assert videos[0].duration == "3:45"


def test_parse_video_data_ignores_empty_titles():
    raw_data = [
        {"title": ""},
        {"title": "   "},
        {"title": "Vídeo válido"},
    ]

    videos = parse_video_data(raw_data)

    assert len(videos) == 1
    assert videos[0].title == "Vídeo válido"


def test_parse_video_data_handles_missing_fields():
    videos = parse_video_data([{"title": "Vídeo sem metadados"}])

    assert videos[0].channel == "Canal desconhecido"
    assert videos[0].duration == "Não informada"
    assert videos[0].metadata == ""
