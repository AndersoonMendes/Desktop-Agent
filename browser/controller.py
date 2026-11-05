from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright


class BrowserController:
    def __init__(self, headless: bool = False) -> None:
        self.headless = headless

    def search_youtube(self, query: str) -> None:
        if not query.strip():
            raise ValueError("O termo de pesquisa não pode estar vazio.")

        search_url = (
            "https://www.youtube.com/results?search_query="
            f"{quote_plus(query.strip())}"
        )

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.headless)
            page = browser.new_page()
            page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            print(f"\nNavegador aberto: {search_url}")

            if not self.headless:
                input("Pressione Enter aqui no terminal para fechar o navegador...")

            browser.close()
