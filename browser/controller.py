import ipaddress
from dataclasses import dataclass
from urllib.parse import quote_plus, urlsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


@dataclass(frozen=True)
class VideoResult:
    title: str
    channel: str
    duration: str
    metadata: str
    url: str


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


class BrowserController:
    def __init__(self, headless: bool = False) -> None:
        self.headless = headless

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
            browser = playwright.chromium.launch(headless=self.headless)

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
            browser = playwright.chromium.launch(headless=self.headless)

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