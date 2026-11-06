from types import SimpleNamespace

import pytest

from agent.brain import AgentBrain, parse_plan


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