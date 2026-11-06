
from dataclasses import dataclass
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright


@dataclass(frozen=True)
class PageSnapshot:
    title: str
    url: str
    text: str


class BrowserController:
    def __init__(self, headless: bool = False) -> None:
        self.headless = headless

    def search_youtube(self, query: str) -> PageSnapshot:
        if not query.strip():
            raise ValueError("O termo de pesquisa não pode estar vazio.")

        search_url = (
            "https://www.youtube.com/results?search_query="
            f"{quote_plus(query.strip())}"
        )

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=self.headless
            )

            try:
                page = browser.new_page()
                page.goto(
                    search_url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )

                page.locator("body").inner_text(timeout=15000)
                page.wait_for_timeout(2000)

                snapshot = PageSnapshot(
                    title=page.title(),
                    url=page.url,
                    text=page.locator("body").inner_text()[:6000],
                )

                print(f"\nPágina aberta: {snapshot.title}")
                print(f"URL: {snapshot.url}")

                if not self.headless:
                    input(
                        "\nPressione Enter no terminal "
                        "para fechar o navegador..."
                    )

                return snapshot

            finally:
                browser.close()
