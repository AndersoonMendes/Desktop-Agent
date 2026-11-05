import pytest

from agent.brain import parse_plan


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
