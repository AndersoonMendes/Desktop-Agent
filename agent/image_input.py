from pathlib import Path

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def find_latest_image(directory: str | Path) -> Path:
    """Return the newest supported image directly inside an inbox folder."""
    inbox = Path(directory).expanduser()
    if not inbox.is_dir():
        raise ValueError(f"Pasta de imagens não encontrada: {inbox}")

    images = [
        path
        for path in inbox.iterdir()
        if path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    ]
    if not images:
        raise ValueError(f"Nenhuma imagem compatível encontrada em: {inbox}")

    return max(images, key=lambda path: path.stat().st_mtime_ns)
