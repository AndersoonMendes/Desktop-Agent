import ipaddress
import re
import shutil
import subprocess
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from queue import Empty as QueueEmpty
from urllib.parse import parse_qs, quote_plus, urlencode, urlsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from browser.youtube_player import YouTubePlaylistServer
from music.models import QueueStatus, VideoCandidate
from music.queue import MusicQueue

# Compatibility name used by the existing generic search feature.
VideoResult = VideoCandidate


@dataclass(frozen=True)
class PageSnapshot:
    title: str
    url: str
    text: str
    videos: list[VideoResult]


def parse_video_data(data: list[dict]) -> list[VideoResult]:
    """Convert raw browser data into structured video results."""
    videos = []

    for item in data:
        title = str(item.get("title") or "").strip()

        if not title:
            continue

        videos.append(
            VideoResult(
                title=title,
                channel=str(item.get("channel") or "Canal desconhecido").strip(),
                duration=str(item.get("duration") or "Não informada").strip(),
                metadata=str(item.get("metadata") or "").strip(),
                url=str(item.get("url") or "").strip(),
            )
        )

    return videos


def normalize_youtube_watch_url(url: str) -> str | None:
    """Return a canonical YouTube watch URL, rejecting non-video links."""
    candidate = url.strip()
    if candidate.startswith("/watch?"):
        candidate = f"https://www.youtube.com{candidate}"

    parsed = urlsplit(candidate)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"www.youtube.com", "youtube.com", "m.youtube.com"}
        or parsed.path != "/watch"
        or parsed.username
        or parsed.password
        or not parse_qs(parsed.query).get("v", [""])[0]
    ):
        return None

    video_id = parse_qs(parsed.query).get("v", [""])[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", video_id):
        return None
    return f"https://www.youtube.com/watch?{urlencode({'v': video_id})}"


def normalize_youtube_playlist_url(url: str) -> str | None:
    """Accept standard YouTube playlist links and return their canonical URL."""
    parsed = urlsplit(url.strip())
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"www.youtube.com", "youtube.com", "m.youtube.com"}
        or parsed.path not in {"/playlist", "/watch"}
        or parsed.username
        or parsed.password
    ):
        return None
    playlist_id = parse_qs(parsed.query).get("list", [""])[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,100}", playlist_id):
        return None
    return f"https://www.youtube.com/playlist?{urlencode({'list': playlist_id})}"


class BrowserController:
    def __init__(
        self,
        headless: bool = False,
        channel: str | None = "chrome",
    ) -> None:
        self.headless = headless
        self.channel = channel

    def _launch_browser(self, playwright):
        """Launch an isolated browser context for public YouTube searches."""
        return playwright.chromium.launch(
            headless=self.headless,
            channel=self.channel,
        )

    def login_youtube(self) -> None:
        """Open YouTube in the normal system browser for user-managed sign-in."""
        self._open_external_url("https://www.youtube.com/")
        print("YouTube aberto no navegador normal do sistema.")

    @staticmethod
    def _is_wsl() -> bool:
        release_file = Path("/proc/sys/kernel/osrelease")
        try:
            release = release_file.read_text(encoding="utf-8").lower()
        except OSError:
            release = ""
        return "microsoft" in release or bool(shutil.which("cmd.exe"))

    def _open_external_url(self, url: str) -> None:
        """Open a URL outside Playwright in the user's normal browser."""
        if self._is_wsl():
            launchers = []
            wslview = shutil.which("wslview")
            if wslview:
                launchers.append([wslview, url])
            command = shutil.which("cmd.exe")
            if command:
                launchers.append([command, "/c", "start", "", url])
            powershell = shutil.which("powershell.exe")
            if powershell:
                launchers.append(
                    [
                        powershell,
                        "-NoProfile",
                        "-Command",
                        f"Start-Process -FilePath '{url}'",
                    ]
                )
            if not launchers:
                raise OSError(
                    "Não encontrei wslview, cmd.exe ou powershell.exe para abrir "
                    "o navegador do Windows."
                )
            last_code = None
            for launcher in launchers:
                result = subprocess.run(
                    launcher,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if result.returncode == 0:
                    return
                last_code = result.returncode
            raise OSError(
                f"O Windows não conseguiu abrir o vídeo no navegador "
                f"(último código {last_code})."
            )

        if not webbrowser.open_new_tab(url):
            raise OSError("Não foi possível abrir o navegador padrão do sistema.")

    def search_youtube(
        self,
        query: str,
        max_results: int = 5,
    ) -> PageSnapshot:
        if not query.strip():
            raise ValueError("O termo de pesquisa não pode estar vazio.")

        if not 1 <= max_results <= 20:
            raise ValueError("A quantidade de resultados deve estar entre 1 e 20.")

        search_url = (
            "https://www.youtube.com/results?search_query="
            f"{quote_plus(query.strip())}"
        )

        with sync_playwright() as playwright:
            browser = self._launch_browser(playwright)

            try:
                page = browser.new_page()
                page.goto(
                    search_url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )

                try:
                    page.locator("ytd-video-renderer").first.wait_for(
                        state="attached",
                        timeout=15000,
                    )
                except PlaywrightTimeoutError:
                    pass

                raw_videos = page.locator("ytd-video-renderer").evaluate_all(
                    """
                    cards => cards.map(card => {
                        const titleLink = card.querySelector('a#video-title');
                        const channelLink = card.querySelector(
                            'ytd-channel-name a'
                        );
                        const durationElement = card.querySelector(
                            'ytd-thumbnail-overlay-time-status-renderer span'
                        );
                        const metadataElements = card.querySelectorAll(
                            '#metadata-line span'
                        );

                        return {
                            title: titleLink?.getAttribute('title')
                                || titleLink?.textContent?.trim()
                                || '',
                            channel: channelLink?.textContent?.trim() || '',
                            duration: durationElement?.textContent?.trim() || '',
                            metadata: Array.from(metadataElements)
                                .map(element => element.textContent.trim())
                                .join(' • '),
                            url: titleLink?.href || ''
                        };
                    })
                    """
                )

                videos = parse_video_data(raw_videos[:max_results])

                snapshot = PageSnapshot(
                    title=page.title(),
                    url=page.url,
                    text=page.locator("body").inner_text()[:6000],
                    videos=videos,
                )

                print(f"\nPágina aberta: {snapshot.title}")
                print(f"Vídeos encontrados: {len(snapshot.videos)}")

                if not self.headless:
                    input(
                        "\nPressione Enter no terminal "
                        "para fechar o navegador..."
                    )

                return snapshot

            finally:
                browser.close()

    def search_track_candidates(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[VideoCandidate]:
        """Search YouTube and return validated video candidates without selecting one."""
        if not query.strip():
            raise ValueError("O termo de pesquisa não pode estar vazio.")
        if not 1 <= max_results <= 20:
            raise ValueError("A quantidade de candidatos deve estar entre 1 e 20.")

        search_url = (
            "https://www.youtube.com/results?search_query="
            f"{quote_plus(query.strip())}"
        )

        with sync_playwright() as playwright:
            browser = self._launch_browser(playwright)
            try:
                page = browser.new_page()
                page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                try:
                    page.locator("ytd-video-renderer").first.wait_for(
                        state="attached",
                        timeout=15000,
                    )
                except PlaywrightTimeoutError:
                    return []

                raw_videos = page.locator("ytd-video-renderer").evaluate_all(
                    """
                    cards => cards.map(card => {
                        const titleLink = card.querySelector('a#video-title');
                        const channelLink = card.querySelector('ytd-channel-name a');
                        const duration = card.querySelector(
                            'ytd-thumbnail-overlay-time-status-renderer span'
                        );
                        const metadata = card.querySelectorAll('#metadata-line span');
                        return {
                            title: titleLink?.getAttribute('title')
                                || titleLink?.textContent?.trim() || '',
                            channel: channelLink?.textContent?.trim() || '',
                            duration: duration?.textContent?.trim() || '',
                            metadata: Array.from(metadata)
                                .map(item => item.textContent.trim()).join(' • '),
                            url: titleLink?.href || ''
                        };
                    })
                    """
                )

                candidates = []
                for video in parse_video_data(raw_videos):
                    valid_url = normalize_youtube_watch_url(video.url)
                    if valid_url:
                        candidates.append(
                            VideoCandidate(
                                title=video.title,
                                channel=video.channel,
                                duration=video.duration,
                                metadata=video.metadata,
                                url=valid_url,
                            )
                        )
                    if len(candidates) == max_results:
                        break
                return candidates
            finally:
                browser.close()

    def get_playlist_videos(self, url: str) -> list[VideoCandidate]:
        """Read the visible videos of a public YouTube playlist in page order."""
        playlist_url = normalize_youtube_playlist_url(url)
        if not playlist_url:
            raise ValueError("Informe um link válido de playlist do YouTube.")

        with sync_playwright() as playwright:
            browser = self._launch_browser(playwright)
            try:
                page = browser.new_page()
                page.goto(playlist_url, wait_until="domcontentloaded", timeout=60000)
                rows = page.locator("ytd-playlist-video-renderer")
                try:
                    rows.first.wait_for(state="attached", timeout=15000)
                except PlaywrightTimeoutError:
                    return []

                # Playlist rows are lazy-loaded; scroll until the visible count stops growing.
                previous_count = -1
                stable_rounds = 0
                while stable_rounds < 3:
                    count = rows.count()
                    stable_rounds = stable_rounds + 1 if count == previous_count else 0
                    previous_count = count
                    page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                    page.wait_for_timeout(700)

                raw_videos = rows.evaluate_all(
                    """
                    items => items.map(item => {
                        const link = item.querySelector('a#video-title');
                        const channel = item.querySelector('ytd-channel-name a');
                        const duration = item.querySelector(
                            'ytd-thumbnail-overlay-time-status-renderer span'
                        );
                        return {
                            title: link?.getAttribute('title') || link?.textContent?.trim() || '',
                            channel: channel?.textContent?.trim() || 'Canal desconhecido',
                            duration: duration?.textContent?.trim() || 'Não informada',
                            metadata: '',
                            url: link?.href || ''
                        };
                    })
                    """
                )
                videos = []
                for video in parse_video_data(raw_videos):
                    video_url = normalize_youtube_watch_url(video.url)
                    if video_url:
                        videos.append(VideoCandidate(
                            title=video.title,
                            channel=video.channel,
                            duration=video.duration,
                            metadata=video.metadata,
                            url=video_url,
                        ))
                return videos
            finally:
                browser.close()

    def play_queue(self, queue: MusicQueue) -> None:
        """Play approved candidates through YouTube's supported IFrame API."""
        selected_entries = [
            entry for entry in queue.entries if entry.status is QueueStatus.SELECTED
        ]
        if not selected_entries:
            print("A fila não contém faixas selecionadas para reprodução.")
            return

        valid_entries = []
        player_items = []
        for entry in selected_entries:
            track = entry.track
            candidate = entry.candidate
            if candidate is None:
                queue.mark_failed(
                    track.position,
                    "A faixa selecionada não possui vídeo associado.",
                )
                continue

            video_url = normalize_youtube_watch_url(candidate.url)
            if video_url is None:
                message = "A URL selecionada não é um vídeo válido do YouTube."
                queue.mark_failed(track.position, message)
                print(f"Faixa {track.position}: {message}")
                continue
            video_id = parse_qs(urlsplit(video_url).query)["v"][0]
            valid_entries.append(entry)
            player_items.append(
                {
                    "index": len(player_items),
                    "position": track.position,
                    "track_title": track.title,
                    "video_title": candidate.title,
                    "channel": candidate.channel,
                    "video_id": video_id,
                    "url": video_url,
                }
            )

        if not valid_entries:
            print("Nenhuma faixa selecionada possui uma URL de vídeo válida.")
            return

        position_by_index = {
            index: entry.track.position for index, entry in enumerate(valid_entries)
        }
        indices_by_video_id: dict[str, list[int]] = {}
        for item in player_items:
            indices_by_video_id.setdefault(item["video_id"], []).append(item["index"])
        print("\nAbrindo o player oficial do YouTube com a fila aprovada...")
        try:
            with YouTubePlaylistServer(player_items) as player_server:
                try:
                    self._open_external_url(player_server.url)
                except (OSError, subprocess.SubprocessError, ValueError) as exc:
                    for entry in valid_entries:
                        queue.mark_failed(entry.track.position, str(exc))
                    print(f"Falha ao abrir o player local: {exc}")
                    return

                print(
                    "No navegador, clique em ‘Iniciar reprodução’ uma vez. "
                    "Depois disso, o YouTube avança pela fila automaticamente. "
                    "Ctrl+C interrompe o acompanhamento."
                )
                completed = set()
                page_ready = False
                connect_deadline = time.monotonic() + 60
                while len(completed) < len(valid_entries):
                    try:
                        event = player_server.events.get(timeout=1)
                    except QueueEmpty:
                        if not page_ready and time.monotonic() >= connect_deadline:
                            message = "O navegador não conseguiu conectar ao player local."
                            for entry in valid_entries:
                                if queue.entries[entry.track.position - 1].status is QueueStatus.SELECTED:
                                    queue.mark_failed(entry.track.position, message)
                            print(message)
                            break
                        continue

                    event_type = event.get("type")
                    if event_type == "ready":
                        page_ready = True
                        print("Player do YouTube pronto; aguardando o clique em Iniciar.")
                        continue
                    if event_type == "fatal":
                        message = str(
                            event.get("message")
                            or "O player do YouTube não pôde ser iniciado."
                        )
                        for entry in valid_entries:
                            if queue.entries[entry.track.position - 1].status is QueueStatus.SELECTED:
                                queue.mark_failed(entry.track.position, message)
                        completed.update(position_by_index)
                        print(f"Falha no player: {message}")
                        continue

                    index = event.get("index")
                    video_id = event.get("video_id")
                    matching_indices = indices_by_video_id.get(video_id, [])
                    if matching_indices and index not in matching_indices:
                        unfinished_matches = [
                            match
                            for match in matching_indices
                            if match not in completed
                            and queue.entries[position_by_index[match] - 1].status
                            is QueueStatus.SELECTED
                        ]
                        if unfinished_matches:
                            index = unfinished_matches[0]
                    if type(index) is not int or index not in position_by_index:
                        if event_type in {"stopped", "closed"}:
                            print("\nPlayer fechado ou fila interrompida pelo usuário.")
                            return
                        continue

                    position = position_by_index[index]
                    entry = queue.entries[position - 1]
                    if event_type == "playing":
                        print(f"Faixa {position}: reprodução iniciada.")
                    elif event_type == "paused":
                        print(f"Faixa {position}: pausada.")
                    elif event_type == "ended" and entry.status is QueueStatus.SELECTED:
                        queue.mark_played(position)
                        completed.add(index)
                        print(f"Faixa {position}: reprodução concluída.")
                    elif event_type == "error" and entry.status is QueueStatus.SELECTED:
                        error_code = event.get("code", "desconhecido")
                        queue.mark_failed(
                            position,
                            f"Player incorporado do YouTube reportou erro {error_code}.",
                        )
                        completed.add(index)
                        print(
                            f"Faixa {position}: erro {error_code}; "
                            "a fila tentará seguir para a próxima."
                        )
                    elif event_type in {"stopped", "closed"}:
                        print("\nPlayer fechado ou fila interrompida pelo usuário.")
                        return
        except KeyboardInterrupt:
            print("\nFila interrompida pelo usuário.")
        except OSError as exc:
            for entry in valid_entries:
                if queue.entries[entry.track.position - 1].status is QueueStatus.SELECTED:
                    queue.mark_failed(entry.track.position, str(exc))
            print(f"Não foi possível iniciar o player local: {exc}")

    def open_url(self, url: str) -> PageSnapshot:
        """Open a public HTTP/HTTPS page and capture its content."""
        parsed_url = urlsplit(url.strip())

        if (
            parsed_url.scheme not in {"http", "https"}
            or not parsed_url.hostname
            or parsed_url.username
            or parsed_url.password
        ):
            raise ValueError("A URL precisa ser HTTP ou HTTPS válida.")

        hostname = parsed_url.hostname.lower()

        if hostname == "localhost" or hostname.endswith(".localhost"):
            raise ValueError("Endereços locais não são permitidos.")

        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            address = None

        if address is not None and not address.is_global:
            raise ValueError("Endereços IP privados não são permitidos.")

        with sync_playwright() as playwright:
            browser = self._launch_browser(playwright)

            try:
                page = browser.new_page()
                page.goto(
                    url.strip(),
                    wait_until="domcontentloaded",
                    timeout=30000,
                )

                snapshot = PageSnapshot(
                    title=page.title(),
                    url=page.url,
                    text=page.locator("body").inner_text()[:12000],
                    videos=[],
                )

                print(f"\nPágina aberta: {snapshot.title}")

                if not self.headless:
                    input(
                        "\nPressione Enter no terminal "
                        "para fechar o navegador..."
                    )

                return snapshot

            finally:
                browser.close()
