import httpx
from playwright.sync_api import Error as PlaywrightError

from agent.brain import AgentBrain
from agent.tools import ToolDispatcher
from config.settings import Settings
from music.models import MusicTrack, QueueStatus, VideoCandidate
from music.queue import MusicQueue


def review_tracks(tracks: list[MusicTrack]) -> list[MusicTrack] | None:
    """Let the user confirm or correct recognized tracks before any search."""
    reviewed = list(tracks)

    while True:
        print("\nMúsicas identificadas, na ordem da imagem:")
        for track in reviewed:
            status = " [ambígua]" if track.ambiguous else ""
            artist = f" — {track.artist}" if track.artist else ""
            title = track.title or "[título ilegível]"
            note = f" ({track.note})" if track.note else ""
            print(f"{track.position}. {title}{artist}{status}{note}")

        has_ambiguity = any(track.ambiguous for track in reviewed)
        if has_ambiguity:
            print("Resolva os itens ambíguos antes de pesquisar.")
            prompt = "Digite 'editar <posição>' ou 'sair' para cancelar > "
        else:
            prompt = "Enter confirma; 'editar <posição>' corrige; 'sair' cancela > "

        command = input(prompt).strip().lower()
        if command in {"sair", "cancelar"}:
            return None
        if not command and not has_ambiguity:
            return reviewed

        parts = command.split()
        if len(parts) != 2 or parts[0] != "editar" or not parts[1].isdigit():
            print("Comando inválido. Use 'editar <posição>' ou 'sair'.")
            continue

        position = int(parts[1])
        if not 1 <= position <= len(reviewed):
            print("Essa posição não existe na lista.")
            continue

        current = reviewed[position - 1]
        title = input(f"Título [{current.title}] > ").strip() or current.title
        artist = input(f"Artista [{current.artist}] > ").strip() or current.artist
        if not title:
            print("Informe um título para resolver esse item.")
            continue

        reviewed[position - 1] = MusicTrack(
            position=current.position,
            title=title,
            artist=artist,
            ambiguous=False,
            note="",
        )


def choose_candidate(
    track: MusicTrack,
    candidates: list[VideoCandidate],
) -> VideoCandidate | None:
    """Ask the user to choose one candidate or leave this track pending."""
    if not candidates:
        print("Nenhum candidato confiável foi encontrado; faixa ficará pendente.")
        return None

    while True:
        artist = f" — {track.artist}" if track.artist else ""
        print(f"\nResultados para {track.position}. {track.title}{artist}")
        for index, candidate in enumerate(candidates, start=1):
            print(f"{index}. {candidate.title}")
            print(f"   Canal: {candidate.channel} | Duração: {candidate.duration}")
            print(f"   URL: {candidate.url}")

        print(
            "Esta escolha associa um vídeo à faixa. A reprodução começa somente "
            "depois de concluir a seleção e confirmar a fila."
        )
        choice = input(
            f"Escolha 1–{len(candidates)} para a faixa {track.position}, "
            "ou 'p' para deixá-la pendente > "
        ).strip().lower()
        if choice in {"p", "pendente", "sem correspondência"}:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(candidates):
            return candidates[int(choice) - 1]
        print("Escolha inválida. Informe um número listado ou 'p'.")


def print_queue(queue: MusicQueue) -> None:
    print("\nEstado atual da fila:")
    for entry in queue.entries:
        track = entry.track
        artist = f" — {track.artist}" if track.artist else ""
        print(f"{track.position}. {track.title}{artist} [{entry.status.value}]")
        if entry.candidate:
            print(
                f"   Vídeo: {entry.candidate.title} | {entry.candidate.channel}"
            )
            print(f"   URL: {entry.candidate.url}")
        if entry.message:
            print(f"   Observação: {entry.message}")


def main() -> None:
    settings = Settings.from_env()
    brain = AgentBrain(settings)
    tools = ToolDispatcher(settings)

    print("\n🤖 Desktop AI Agent")
    browser_name = "Google Chrome" if settings.browser_channel else "Chromium do Playwright"
    print(f"Navegador configurado: {browser_name}")
    print("Digite uma tarefa em linguagem natural ou 'sair' para encerrar.")
    print("Exemplo: Pesquise músicas eletrônicas no YouTube")
    print("Para tocar músicas de uma imagem: /imagem caminho/da/imagem.png\n")
    print("Para abrir o YouTube no navegador: /login_youtube\n")

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
            if instruction.lower() == "/login_youtube":
                tools.login_youtube()
                continue

            if instruction.lower() == "/imagem" or instruction.lower().startswith(
                "/imagem "
            ):
                image_path = instruction[len("/imagem") :].strip()
                if not image_path:
                    image_path = input("Caminho da imagem > ").strip()
                if not image_path:
                    print("Erro > Informe o caminho da imagem.\n")
                    continue

                tracks = brain.recognize_songs(image_path)
                reviewed_tracks = review_tracks(tracks)
                if reviewed_tracks is None:
                    print("Revisão cancelada; nenhuma pesquisa foi iniciada.\n")
                    continue

                queue = MusicQueue(reviewed_tracks)
                print("\nPesquisando candidatos na ordem da lista aprovada...")
                for index, track in enumerate(queue.entries, start=1):
                    artist = f" — {track.track.artist}" if track.track.artist else ""
                    print(
                        f"\nBusca {index}/{len(queue.entries)}: "
                        f"{track.track.title}{artist}"
                    )
                    try:
                        candidates = tools.search_track_candidates(track.track)
                    except (
                        ValueError,
                        OSError,
                        httpx.HTTPError,
                        PlaywrightError,
                    ) as exc:
                        queue.mark_failed(track.track.position, f"Falha na pesquisa: {exc}")
                        print(
                            f"Faixa {track.track.position} ficou com falha de pesquisa: {exc}"
                        )
                        continue

                    selected = choose_candidate(track.track, candidates)
                    if selected is None:
                        queue.leave_pending(
                            track.track.position,
                            "Sem correspondência confirmada pelo usuário.",
                        )
                        print(
                            f"Faixa {track.track.position} pendente; "
                            "seguindo para a próxima busca."
                        )
                    else:
                        queue.select(track.track.position, selected)
                        print(
                            f"Vídeo associado à faixa {track.track.position}; "
                            "seguindo para a próxima busca."
                        )

                print_queue(queue)
                selected_count = sum(
                    entry.status is QueueStatus.SELECTED for entry in queue.entries
                )
                if not selected_count:
                    print("Nenhuma faixa selecionada para reproduzir.\n")
                    continue

                print(
                    f"\nSeleção concluída: {selected_count} vídeo(s) escolhido(s). "
                    "Faixas pendentes serão puladas; as selecionadas tocarão na ordem original."
                )
                start_playback = input(
                    "Digite 's' para iniciar a reprodução ou Enter para parar aqui > "
                ).strip().lower()
                if start_playback not in {"s", "sim"}:
                    print("Fila mantida sem iniciar a reprodução.\n")
                    continue

                tools.play_queue(queue)
                print_queue(queue)
                continue

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
            brain.add_context(
                "assistant",
                f"Resumo da pesquisa anterior:\n{summary}",
            )

        except KeyboardInterrupt:
            print("\nFluxo atual cancelado. Nenhuma faixa será reproduzida.\n")
        except (
            ValueError,
            TypeError,
            OSError,
            httpx.HTTPError,
            PlaywrightError,
        ) as exc:
            print(f"\nErro > {exc}\n")


if __name__ == "__main__":
    main()
