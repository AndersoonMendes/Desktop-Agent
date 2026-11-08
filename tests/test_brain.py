from types import SimpleNamespace

import pytest

from agent.brain import AgentBrain, parse_plan, parse_song_list


def test_parse_youtube_search_plan() -> None:
    plan = parse_plan(
        '{"action":"search_youtube","query":"jazz","response":"","reason":"Pesquisa solicitada"}'
    )
    assert plan.action == "search_youtube"
    assert plan.query == "jazz"


def test_parse_answer_plan() -> None:
    plan = parse_plan(
        '{"action":"answer","query":"","response":"Olá!","reason":"É uma saudação"}'
    )
    assert plan.action == "answer"
    assert plan.response == "Olá!"


def test_reject_unknown_action() -> None:
    with pytest.raises(ValueError, match="Ação não permitida"):
        parse_plan('{"action":"run_shell","query":"whoami"}')


def test_reject_empty_youtube_query() -> None:
    with pytest.raises(ValueError, match="pesquisa"):
        parse_plan('{"action":"search_youtube","query":"   "}')


def test_reject_invalid_json() -> None:
    with pytest.raises(ValueError, match="JSON válido"):
        parse_plan("not-json")

def test_conversation_history_stores_messages():
    brain = AgentBrain(settings=SimpleNamespace())

    brain.add_context("user", "Pesquise músicas de Tim Maia")
    brain.add_context("assistant", "Encontrei alguns resultados")

    assert len(brain.history) == 2
    assert brain.history[0]["role"] == "user"
    assert brain.history[0]["content"] == "Pesquise músicas de Tim Maia"


def test_conversation_history_is_limited():
    brain = AgentBrain(settings=SimpleNamespace())

    for index in range(12):
        role = "user" if index % 2 == 0 else "assistant"
        brain.add_context(role, f"Mensagem {index}")

    assert len(brain.history) == 10
    assert brain.history[0]["content"] == "Mensagem 2"
    assert brain.history[-1]["content"] == "Mensagem 11"


def test_conversation_history_limits_message_size():
    brain = AgentBrain(settings=SimpleNamespace())

    brain.add_context("user", "A" * 4000)

    assert len(brain.history[0]["content"]) == 3000


def test_conversation_history_rejects_invalid_role():
    brain = AgentBrain(settings=SimpleNamespace())

    with pytest.raises(ValueError, match="user ou assistant"):
        brain.add_context("system", "Mensagem inválida")

def test_parse_open_url_plan():
    plan = parse_plan(
        '{"action":"open_url",'
        '"query":"",'
        '"url":"https://www.python.org",'
        '"response":"",'
        '"reason":"Abrir documentação"}'
    )

    assert plan.action == "open_url"
    assert plan.url == "https://www.python.org"


def test_reject_invalid_open_url():
    with pytest.raises(ValueError, match="HTTP ou HTTPS"):
        parse_plan(
            '{"action":"open_url",'
            '"url":"javascript:alert(1)"}'
        )


def test_reject_open_url_without_hostname():
    with pytest.raises(ValueError, match="HTTP ou HTTPS"):
        parse_plan(
            '{"action":"open_url",'
            '"url":"https:///pagina"}'
        )


def test_parse_song_list_preserves_order():
    songs = parse_song_list(
        '{"songs":['
        '{"position":1,"title":"Primeira música","artist":"Artista A",'
        '"ambiguous":false,"note":""},'
        '{"position":2,"title":"Segunda música","artist":"Artista B",'
        '"ambiguous":false,"note":""}]}'
    )

    assert [(song.position, song.title, song.artist) for song in songs] == [
        (1, "Primeira música", "Artista A"),
        (2, "Segunda música", "Artista B"),
    ]


def test_parse_song_list_retains_ambiguous_item_in_original_position():
    songs = parse_song_list(
        '{"songs":['
        '{"position":1,"title":"Faixa A","artist":"","ambiguous":false},'
        '{"position":2,"title":"","artist":"","ambiguous":true,'
        '"note":"título ilegível"},'
        '{"position":3,"title":"Faixa C","artist":"","ambiguous":false}]}'
    )

    assert [song.position for song in songs] == [1, 2, 3]
    assert songs[1].ambiguous
    assert songs[1].note == "título ilegível"


@pytest.mark.parametrize(
    "content",
    [
        "not-json",
        '{"titles":["Música"]}',
        '{"songs":[]}',
        '{"songs":[{"position":1,"title":"","ambiguous":false}]}',
        '{"songs":[{"position":2,"title":"Faixa","ambiguous":false}]}',
        '{"songs":[{"position":1,"title":42,"ambiguous":false}]}',
    ],
)
def test_parse_song_list_rejects_invalid_response(content):
    with pytest.raises((TypeError, ValueError)):
        parse_song_list(content)


def test_recognize_songs_sends_image_to_ollama(tmp_path, monkeypatch):
    from agent.brain import AgentBrain

    image = tmp_path / "lista.png"
    image.write_bytes(b"image-bytes")
    captured = {}

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "message": {
                    "content": (
                        '{"songs":[{"position":1,"title":"Música A",'
                        '"artist":"Artista A","ambiguous":false},'
                        '{"position":2,"title":"Música B",'
                        '"artist":"","ambiguous":false}]}'
                    )
                }
            }

    def mock_post(url, **kwargs):
        captured["url"] = url
        captured["request"] = kwargs["json"]
        return MockResponse()

    monkeypatch.setattr("agent.brain.httpx.post", mock_post)
    brain = AgentBrain(
        settings=SimpleNamespace(
            ollama_base_url="http://localhost:11434",
            ollama_model="vision-model",
        )
    )

    tracks = brain.recognize_songs(str(image))
    assert [track.title for track in tracks] == ["Música A", "Música B"]
    assert tracks[0].artist == "Artista A"
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["request"]["messages"][1]["images"]


def test_recognize_songs_retries_when_model_returns_invalid_json(tmp_path, monkeypatch):
    image = tmp_path / "lista.png"
    image.write_bytes(b"image-bytes")
    responses = iter(
        [
            "Não consigo produzir o formato solicitado.",
            (
                '{"songs":[{"position":1,"title":"Faixa A","artist":"Artista",'
                '"ambiguous":false,"note":""}]}'
            ),
        ]
    )
    requests = []

    class MockResponse:
        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": self.content}}

    def mock_post(_url, **kwargs):
        requests.append(kwargs["json"])
        return MockResponse(next(responses))

    monkeypatch.setattr("agent.brain.httpx.post", mock_post)
    brain = AgentBrain(
        settings=SimpleNamespace(
            ollama_base_url="http://localhost:11434",
            ollama_model="vision-model",
        )
    )

    tracks = brain.recognize_songs(str(image))

    assert len(requests) == 2
    assert "tentativa anterior" in requests[1]["messages"][0]["content"]
    assert tracks[0].title == "Faixa A"
