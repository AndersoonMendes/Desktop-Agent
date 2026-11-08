from config.settings import Settings


def test_settings_default_to_google_chrome(monkeypatch):
    monkeypatch.delenv("BROWSER_CHANNEL", raising=False)

    assert Settings.from_env().browser_channel == "chrome"


def test_settings_can_select_bundled_chromium(monkeypatch):
    monkeypatch.setenv("BROWSER_CHANNEL", "")

    assert Settings.from_env().browser_channel is None


def test_settings_default_image_inbox_is_images(monkeypatch):
    monkeypatch.delenv("IMAGE_INBOX", raising=False)

    assert Settings.from_env().image_inbox == "images"


def test_settings_can_select_image_inbox(monkeypatch):
    monkeypatch.setenv("IMAGE_INBOX", "/mnt/c/Users/Anderson/Downloads")

    assert Settings.from_env().image_inbox == "/mnt/c/Users/Anderson/Downloads"


