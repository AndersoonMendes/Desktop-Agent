from agent.brain import AgentPlan
from browser.controller import BrowserController, PageSnapshot
from config.settings import Settings
from music.models import MusicTrack, VideoCandidate
from music.queue import MusicQueue


class ToolDispatcher:
    """Dispatch only explicitly supported agent actions."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def execute(self, plan: AgentPlan) -> PageSnapshot:
        browser = BrowserController(
            headless=self.settings.browser_headless,
            channel=self.settings.browser_channel,
        )

        if plan.action == "search_youtube":
            return browser.search_youtube(plan.query)

        if plan.action == "open_url":
            return browser.open_url(plan.url)

        raise ValueError(
            f"Nenhuma ferramenta implementada para: {plan.action}"
        )

    def search_track_candidates(self, track: MusicTrack) -> list[VideoCandidate]:
        query = f"{track.title} {track.artist}".strip()
        browser = BrowserController(
            headless=self.settings.browser_headless,
            channel=self.settings.browser_channel,
        )
        return browser.search_track_candidates(query)

    def play_queue(self, queue: MusicQueue) -> None:
        browser = BrowserController(
            headless=self.settings.browser_headless,
            channel=self.settings.browser_channel,
        )
        browser.play_queue(queue)

    def login_youtube(self) -> None:
        browser = BrowserController(
            headless=self.settings.browser_headless,
            channel=self.settings.browser_channel,
        )
        browser.login_youtube()
