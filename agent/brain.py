import json
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from config.settings import Settings

ALLOWED_ACTIONS = {"search_youtube", "open_url", "answer"}
MAX_HISTORY_MESSAGES = 10
MAX_MESSAGE_CHARS = 3000


@dataclass(frozen=True)
class AgentPlan:
    action: str
    query: str = ""
    url: str = ""
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
    url = payload.get("url", "")
    response = payload.get("response", "")
    reason = payload.get("reason", "")

    if not all(
        isinstance(value, str)
        for value in (query, url, response, reason)
    ):
        raise ValueError(
            "Os campos query, url, response e reason precisam ser textos."
        )

    if action == "search_youtube":
        query = query.strip()

        if not query or len(query) > 200:
            raise ValueError("A pesquisa precisa ter entre 1 e 200 caracteres.")

    if action == "open_url":
        url = url.strip()
        parsed_url = urlsplit(url)

        if (
            parsed_url.scheme not in {"http", "https"}
            or not parsed_url.hostname
            or parsed_url.username
            or parsed_url.password
        ):
            raise ValueError("A URL precisa ser HTTP ou HTTPS válida.")

    return AgentPlan(
        action=action,
        query=query,
        url=url,
        response=response.strip(),
        reason=reason.strip(),
    )


class AgentBrain:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.history: list[dict[str, str]] = []

    def add_context(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        if role not in {"user", "assistant"}:
            raise ValueError("O papel da mensagem precisa ser user ou assistant.")

        content = content.strip()

        if not content:
            return

        self.history.append(
            {
                "role": role,
                "content": content[:MAX_MESSAGE_CHARS],
            }
        )

        self.history = self.history[-MAX_HISTORY_MESSAGES:]

    def create_plan(self, instruction: str) -> AgentPlan:
        if not instruction.strip():
            raise ValueError("A instrução não pode estar vazia.")

        system_prompt = """
Você é o planejador de um agente de automação de navegador.

Você receberá o histórico da conversa. Use-o para compreender referências
como "esse", "outros parecidos", "agora" e "continue".

Considere a mensagem mais recente como a solicitação atual.
Não invente informações que não estejam no histórico.

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

        messages = [
            {"role": "system", "content": system_prompt},
            *self.history,
            {"role": "user", "content": instruction},
        ]

        response = httpx.post(
            f"{self.settings.ollama_base_url.rstrip('/')}/api/chat",
            json={
                "model": self.settings.ollama_model,
                "messages": messages,
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

        plan = parse_plan(content)

        # Registra a solicitação atual.
        self.add_context("user", instruction)

        # Registra o que o agente decidiu fazer.
        if plan.action == "search_youtube":
            assistant_message = (
                f"Decidi pesquisar no YouTube por: {plan.query}. "
                f"Motivo: {plan.reason}"
            )
        else:
            assistant_message = plan.response

        self.add_context("assistant", assistant_message)

        return plan

    def summarize_page(self, title: str, url: str, text: str) -> str:
        if not text.strip():
            return "Não foi possível encontrar texto na página."

        system_prompt = """
Você é o planejador de um agente de automação de navegador.

Você receberá o histórico da conversa. Use-o para compreender referências
como "esse", "outros parecidos", "agora" e "continue".

Considere a mensagem mais recente como a solicitação atual.

Responda SOMENTE com um objeto JSON válido, sem Markdown.

Ações permitidas:
1. search_youtube: pesquisar algo no YouTube.
2. open_url: abrir uma URL HTTP ou HTTPS fornecida pelo usuário.
3. answer: responder perguntas ou conversar.

Formato obrigatório:
{
  "action": "search_youtube, open_url ou answer",
  "query": "termo de pesquisa ou string vazia",
  "url": "URL ou string vazia",
  "response": "resposta ou string vazia",
  "reason": "explicação curta da decisão"
}

Regras:
- Só use open_url quando houver uma URL fornecida pelo usuário
  ou claramente identificada no contexto.
- Nunca invente URLs.
- Nunca invente outras ações.
- Nunca solicite execução de comandos do sistema.
"""

        response = httpx.post(
            f"{self.settings.ollama_base_url.rstrip('/')}/api/chat",
            json={
                "model": self.settings.ollama_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Título: {title}\n"
                            f"URL: {url}\n\n"
                            f"Conteúdo da página:\n{text}"
                        ),
                    },
                ],
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=120.0,
        )

        response.raise_for_status()

        summary = response.json().get("message", {}).get("content", "")

        if not summary.strip():
            raise ValueError("O modelo retornou um resumo vazio.")

        return summary.strip()