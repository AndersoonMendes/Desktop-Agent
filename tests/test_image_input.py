import os

import pytest

from agent.image_input import find_latest_image


def test_find_latest_image_selects_newest_supported_file(tmp_path):
    older = tmp_path / "primeira.PNG"
    newest = tmp_path / "foto-whatsapp.jpeg"
    ignored_text = tmp_path / "nota.txt"
    ignored_hidden = tmp_path / ".hidden.png"
    for path in (older, newest, ignored_text, ignored_hidden):
        path.write_bytes(b"image")

    os.utime(older, ns=(1_000_000_000, 1_000_000_000))
    os.utime(newest, ns=(2_000_000_000, 2_000_000_000))
    os.utime(ignored_text, ns=(3_000_000_000, 3_000_000_000))
    os.utime(ignored_hidden, ns=(4_000_000_000, 4_000_000_000))

    assert find_latest_image(tmp_path) == newest


def test_find_latest_image_reports_missing_folder(tmp_path):
    with pytest.raises(ValueError, match="Pasta de imagens não encontrada"):
        find_latest_image(tmp_path / "missing")


def test_find_latest_image_reports_empty_folder(tmp_path):
    (tmp_path / "readme.txt").write_text("não é uma imagem", encoding="utf-8")

    with pytest.raises(ValueError, match="Nenhuma imagem compatível"):
        find_latest_image(tmp_path)
