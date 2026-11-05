import json
from dataclasses import dataclass

import httpx

from config.settings import Settings

ALLOWED_ACTIONS = {"search_youtube", "answer"}


@dataclass(frozen=True)
class AgentPlan:
    action: str
    query: str = ""
    response: str = ""
    reason: str = ""


def parse_plan(raw_content: str) -> AgentPlan:
    """Parse and validate the model's JSON response."""
    try:
        payload = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise ValueError("O modelo retornou um plano que não é JSON válido.") from exc

    if not isinstance(payload, dict):
        raise TypeError("O plano precisa ser um objeto JSON.")

    action = payload.get("action")
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"Ação não permitida: {action!r}")

    query = payload.get("query", "")
    response = payload.get("response", "")
    reason = payload.get("reason", "")

    if not all(isinstance(value, str) for value in (query, response, reason)):
        raise ValueError("Os campos query, response e reason precisam ser textos.")

    if action == "search_youtube":
        query = query.strip()
        if not query or len(query) > 200:
            raise ValueError("A pesquisa precisa ter entre 1 e 200 caracteres.")

    return AgentPlan(
        action=action,
        query=query,
        response=response.strip(),
        reason=reason.strip(),
    )


class AgentBrain:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create_plan(self, instruction: str) -> AgentPlan:
        if not instruction.strip():
            raise ValueError("A instrução não pode estar vazia.")

        system_prompt = """
Você é o planejador de um agente de automação de navegador.
Responda SOMENTE com um objeto JSON válido, sem Markdown.
Você só pode escolher uma destas ações:
1. search_youtube: quando o usuário pedir para pesquisar algo no YouTube.
2. answer: para perguntas, conversa ou pedidos que não sejam pesquisa no YouTube.

Formato obrigatório:
{
  "action": "search_youtube" ou "answer",
  "query": "termo de pesquisa ou string vazia",
  "response": "resposta curta ou string vazia",
  "reason": "explicação curta da decisão"
}

Nunca invente outras ações. Nunca solicite execução de comandos do sistema.
"""
        response = httpx.post(
            f"{self.settings.ollama_base_url.rstrip('/')}/api/chat",
            json={
                "model": self.settings.ollama_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": instruction},
                ],
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.1},
            },
            timeout=120.0,
        )
        response.raise_for_status()
        content = response.json().get("message", {}).get("content", "")
        if not content:
            raise ValueError("Ollama retornou uma resposta vazia.")
        return parse_plan(content)
