from queue import Empty, Queue
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from browser.controller import (
    BrowserController,
    normalize_youtube_watch_url,
    parse_video_data,
)
from browser.youtube_player import YouTubePlaylistServer, render_playlist_page
from music.models import MusicTrack, QueueStatus, VideoCandidate
from music.queue import MusicQueue


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


def test_normalize_youtube_watch_url_accepts_relative_video_url():
    assert normalize_youtube_watch_url("/watch?v=abc123") == (
        "https://www.youtube.com/watch?v=abc123"
    )


def test_normalize_youtube_watch_url_removes_playlist_autoplay_parameters():
    url = (
        "https://www.youtube.com/watch?v=abc123&list=RDabc123"
        "&start_radio=1&feature=share"
    )

    assert normalize_youtube_watch_url(url) == "https://www.youtube.com/watch?v=abc123"


@pytest.mark.parametrize(
    "url",
    [
        "https://youtube.com/playlist?list=abc",
        "https://example.com/watch?v=abc",
        "https://www.youtube.com/watch",
        "https://www.youtube.com/watch?v=abc%26start=1",
        "javascript:alert(1)",
    ],
)
def test_normalize_youtube_watch_url_rejects_non_video_urls(url):
    assert normalize_youtube_watch_url(url) is None


def test_browser_uses_isolated_context_for_youtube_search():
    class FakeChromium:
        options = None

        def launch(self, **kwargs):
            self.options = kwargs
            return object()

    chromium = FakeChromium()
    browser = BrowserController()
    browser._launch_browser(type("FakePlaywright", (), {"chromium": chromium})())

    assert chromium.options["channel"] == "chrome"


def test_login_youtube_opens_system_browser(monkeypatch):
    urls = []
    monkeypatch.setattr(BrowserController, "_open_external_url", lambda _self, url: urls.append(url))

    BrowserController().login_youtube()

    assert urls == ["https://www.youtube.com/"]


def test_external_url_uses_windows_default_browser_in_wsl(monkeypatch):
    from types import SimpleNamespace

    captured = {}
    monkeypatch.setattr(BrowserController, "_is_wsl", staticmethod(lambda: True))
    monkeypatch.setattr(
        "browser.controller.shutil.which",
        lambda name: "/usr/bin/cmd.exe" if name == "cmd.exe" else None,
    )

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("browser.controller.subprocess.run", fake_run)
    BrowserController()._open_external_url("https://www.youtube.com/watch?v=abc")

    assert captured["args"] == [
        "/usr/bin/cmd.exe",
        "/c",
        "start",
        "",
        "https://www.youtube.com/watch?v=abc",
    ]


def test_external_url_falls_back_to_powershell_when_cmd_fails(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(BrowserController, "_is_wsl", staticmethod(lambda: True))
    monkeypatch.setattr(
        "browser.controller.shutil.which",
        lambda name: f"/usr/bin/{name}" if name in {"cmd.exe", "powershell.exe"} else None,
    )
    commands = []

    def fake_run(args, **_kwargs):
        commands.append(args)
        return SimpleNamespace(returncode=1 if "cmd.exe" in args[0] else 0)

    monkeypatch.setattr("browser.controller.subprocess.run", fake_run)
    BrowserController()._open_external_url("https://www.youtube.com/watch?v=abc")

    assert len(commands) == 2
    assert commands[1][0] == "/usr/bin/powershell.exe"


def test_external_url_uses_default_browser_outside_wsl(monkeypatch):
    opened = []
    monkeypatch.setattr(BrowserController, "_is_wsl", staticmethod(lambda: False))
    monkeypatch.setattr("browser.controller.webbrowser.open_new_tab", lambda url: opened.append(url) or True)

    BrowserController()._open_external_url("https://www.youtube.com/watch?v=abc")

    assert opened == ["https://www.youtube.com/watch?v=abc"]


def video_candidate(video_id):
    return VideoCandidate(
        title=f"Vídeo {video_id}",
        channel="Canal",
        duration="3:00",
        metadata="",
        url=f"https://www.youtube.com/watch?v={video_id}",
    )


class FakePlaylistServer:
    def __init__(self, items, events, empty_polls=0):
        self.items = items
        self.events = FakeEventQueue(empty_polls)
        for event in events:
            self.events.put(event)
        self.url = "http://127.0.0.1:12345/"

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class FakeEventQueue(Queue):
    def __init__(self, empty_polls=0):
        super().__init__()
        self.empty_polls = empty_polls

    def get(self, block=True, timeout=None):
        if self.empty_polls:
            self.empty_polls -= 1
            raise Empty
        return super().get(block=block, timeout=timeout)


def install_fake_playlist_server(monkeypatch, events, empty_polls=0):
    servers = []

    def create_server(items):
        server = FakePlaylistServer(items, events, empty_polls)
        servers.append(server)
        return server

    monkeypatch.setattr("browser.controller.YouTubePlaylistServer", create_server)
    return servers


def test_render_playlist_page_uses_iframe_api_and_escapes_external_titles():
    page = render_playlist_page(
        [
            {
                "index": 0,
                "track_title": "Música </script><script>alert(1)</script>",
                "video_title": "Vídeo",
                "channel": "Canal",
                "video_id": "abc123",
                "url": "https://www.youtube.com/watch?v=abc123",
            }
        ],
        "local-token",
    )

    assert "https://www.youtube.com/iframe_api" in page
    assert "loadPlaylist(TRACKS.map(track => track.video_id), 0, 0)" in page
    assert "onPlayerStateChange" in page
    assert "Música </script>" not in page
    assert "\\u003c/script\\u003e" in page


def test_local_playlist_server_serves_page_and_accepts_tokenized_events():
    item = {
        "index": 0,
        "position": 1,
        "track_title": "Faixa",
        "video_title": "Vídeo",
        "channel": "Canal",
        "video_id": "abc123",
        "url": "https://www.youtube.com/watch?v=abc123",
    }

    with YouTubePlaylistServer([item]) as server:
        with urlopen(server.url) as response:
            page = response.read().decode("utf-8")
            assert response.status == 200
            assert "Fila de músicas" in page

        endpoint = f"{server.url}event?{urlencode({'token': server.token})}"
        request = Request(
            endpoint,
            data=b'{"type":"ended","index":0}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            assert response.status == 204
        assert server.events.get_nowait() == {"type": "ended", "index": 0}

        bad_token = Request(
            f"{server.url}event?token=invalid",
            data=b'{"type":"ended","index":0}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError, match="403"):
            urlopen(bad_token)


def test_play_queue_tracks_iframe_ended_events_in_original_order(monkeypatch):
    queue = MusicQueue(
        [
            MusicTrack(position=1, title="Primeira"),
            MusicTrack(position=2, title="Pendente"),
            MusicTrack(position=3, title="Terceira"),
        ]
    )
    queue.select(1, video_candidate("one"))
    queue.select(3, video_candidate("three"))
    servers = install_fake_playlist_server(
        monkeypatch,
        [
            {"type": "playing", "index": 0},
            {"type": "ended", "index": 0},
            {"type": "playing", "index": 1},
            {"type": "ended", "index": 1},
        ],
    )
    opened = []
    monkeypatch.setattr(
        BrowserController,
        "_open_external_url",
        lambda _self, url: opened.append(url),
    )

    BrowserController().play_queue(queue)

    assert opened == ["http://127.0.0.1:12345/"]
    assert [item["video_id"] for item in servers[0].items] == ["one", "three"]
    assert [item["position"] for item in servers[0].items] == [1, 3]
    assert [entry.status for entry in queue.entries] == [
        QueueStatus.PLAYED,
        QueueStatus.PENDING,
        QueueStatus.PLAYED,
    ]


def test_play_queue_survives_empty_event_poll_before_player_responds(monkeypatch):
    queue = MusicQueue([MusicTrack(position=1, title="Faixa")])
    queue.select(1, video_candidate("one"))
    install_fake_playlist_server(
        monkeypatch,
        [
            {"type": "ready"},
            {"type": "playing", "index": 0, "video_id": "one"},
            {"type": "ended", "index": 0, "video_id": "one"},
        ],
        empty_polls=1,
    )
    monkeypatch.setattr(BrowserController, "_open_external_url", lambda _self, _url: None)

    BrowserController().play_queue(queue)

    assert queue.entries[0].status is QueueStatus.PLAYED


def test_play_queue_marks_embed_error_and_continues(monkeypatch):
    queue = MusicQueue(
        [MusicTrack(position=1, title="Bloqueada"), MusicTrack(position=2, title="Próxima")]
    )
    queue.select(1, video_candidate("blocked"))
    queue.select(2, video_candidate("next"))
    install_fake_playlist_server(
        monkeypatch,
        [
            {"type": "error", "index": 0, "code": 101},
            {"type": "playing", "index": 1},
            {"type": "ended", "index": 1},
        ],
    )
    monkeypatch.setattr(BrowserController, "_open_external_url", lambda _self, _url: None)

    BrowserController().play_queue(queue)

    assert queue.entries[0].status is QueueStatus.FAILED
    assert "101" in queue.entries[0].message
    assert queue.entries[1].status is QueueStatus.PLAYED


def test_play_queue_local_player_open_failure_marks_all_selected_failed(monkeypatch):
    queue = MusicQueue(
        [MusicTrack(position=1, title="Primeira"), MusicTrack(position=2, title="Segunda")]
    )
    queue.select(1, video_candidate("one"))
    queue.select(2, video_candidate("two"))
    install_fake_playlist_server(monkeypatch, [])

    def fail_to_open(_self, _url):
        raise OSError("browser launch failed")

    monkeypatch.setattr(BrowserController, "_open_external_url", fail_to_open)

    BrowserController().play_queue(queue)

    assert all(entry.status is QueueStatus.FAILED for entry in queue.entries)


def test_play_queue_stops_without_marking_unfinished_tracks_played(monkeypatch):
    queue = MusicQueue(
        [MusicTrack(position=1, title="Atual"), MusicTrack(position=2, title="Próxima")]
    )
    queue.select(1, video_candidate("current"))
    queue.select(2, video_candidate("next"))
    install_fake_playlist_server(monkeypatch, [{"type": "stopped", "index": 0}])
    monkeypatch.setattr(BrowserController, "_open_external_url", lambda _self, _url: None)

    BrowserController().play_queue(queue)

    assert [entry.status for entry in queue.entries] == [
        QueueStatus.SELECTED,
        QueueStatus.SELECTED,
    ]
