import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3.5:4b"
    browser_headless: bool = False
    browser_channel: str | None = "chrome"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            ollama_base_url=os.getenv(
                "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
            ),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3.5:4b"),
            browser_headless=os.getenv("BROWSER_HEADLESS", "false").lower()
            in {"1", "true", "yes"},
            browser_channel=os.getenv("BROWSER_CHANNEL", "chrome").strip() or None,
        )
