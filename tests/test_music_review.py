from main import choose_candidate, review_tracks
from music.models import MusicTrack, VideoCandidate


def test_review_requires_user_confirmation(monkeypatch):
    answers = iter([""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    tracks = [MusicTrack(position=1, title="Faixa", artist="Artista")]

    assert review_tracks(tracks) == tracks


def test_ambiguous_track_must_be_edited_before_confirmation(monkeypatch):
    answers = iter(["", "editar 1", "Título corrigido", "Artista", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    tracks = [MusicTrack(position=1, title="", ambiguous=True, note="ilegível")]

    reviewed = review_tracks(tracks)

    assert reviewed == [
        MusicTrack(position=1, title="Título corrigido", artist="Artista")
    ]


def test_review_can_be_cancelled(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "sair")
    tracks = [MusicTrack(position=1, title="Faixa")]

    assert review_tracks(tracks) is None


def test_candidate_choice_is_explicit(monkeypatch):
    first = VideoCandidate("Vídeo A", "Canal A", "3:00", "", "https://youtube.com/watch?v=a")
    second = VideoCandidate("Vídeo B", "Canal B", "4:00", "", "https://youtube.com/watch?v=b")
    answers = iter(["inválido", "2"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    selected = choose_candidate(
        MusicTrack(position=1, title="Faixa"),
        [first, second],
    )

    assert selected == second


def test_candidate_can_be_left_pending(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "p")

    selected = choose_candidate(
        MusicTrack(position=1, title="Faixa"),
        [VideoCandidate("Vídeo", "Canal", "3:00", "", "https://youtube.com/watch?v=a")],
    )

    assert selected is None
