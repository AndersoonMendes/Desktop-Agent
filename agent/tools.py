
from agent.brain import AgentPlan
from browser.controller import BrowserController, PageSnapshot
from config.settings import Settings


class ToolDispatcher:
    """Dispatch only explicitly supported agent actions."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def execute(self, plan: AgentPlan) -> PageSnapshot:
        if plan.action == "search_youtube":
            browser = BrowserController(
                headless=self.settings.browser_headless
            )
            return browser.search_youtube(plan.query)

        raise ValueError(
            f"Nenhuma ferramenta implementada para: {plan.action}"
        )
