import httpx
from playwright.sync_api import Error as PlaywrightError

from agent.brain import AgentBrain
from agent.tools import ToolDispatcher
from config.settings import Settings


def main() -> None:
    settings = Settings.from_env()
    brain = AgentBrain(settings)
    tools = ToolDispatcher(settings)

    print("\n🤖 Desktop AI Agent")
    print("Digite uma tarefa em linguagem natural ou 'sair' para encerrar.")
    print("Exemplo: Pesquise músicas eletrônicas no YouTube\n")

    while True:
        try:
            instruction = input("Você > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando o agente.")
            break

        if instruction.lower() in {"sair", "exit", "quit"}:
            print("Até a próxima!")
            break
        if not instruction:
            continue

        try:
            plan = brain.create_plan(instruction)
            print(f"\nAgente > {plan.reason}")

            if plan.action == "answer":
                print(f"Resposta > {plan.response}\n")
                continue

            snapshot = tools.execute(plan)

            if not snapshot.videos:
                print("\nNenhum vídeo foi identificado na página.")
            else:
                print("\nResultados encontrados:\n")

                for index, video in enumerate(snapshot.videos, start=1):
                    print(f"{index}. {video.title}")
                    print(f"   Canal: {video.channel}")
                    print(f"   Duração: {video.duration}")
                    print(f"   Informações: {video.metadata}")
                    print(f"   URL: {video.url}\n")

            summary = brain.summarize_page(
                title=snapshot.title,
                url=snapshot.url,
                text=snapshot.text,
            )

            print(f"\nResumo do agente >\n{summary}\n")

        except (
            ValueError,
            TypeError,
            httpx.HTTPError,
            PlaywrightError,
        ) as exc:
            print(f"\nErro > {exc}\n")


if __name__ == "__main__":
    main()
