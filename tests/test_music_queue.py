import pytest

from music.models import MusicTrack, QueueStatus, VideoCandidate
from music.queue import MusicQueue


def candidate(title: str = "Vídeo") -> VideoCandidate:
    return VideoCandidate(
        title=title,
        channel="Canal",
        duration="3:20",
        metadata="",
        url="https://www.youtube.com/watch?v=video123",
    )


def test_queue_sorts_by_original_position_and_starts_pending():
    queue = MusicQueue(
        [MusicTrack(position=2, title="Segunda"), MusicTrack(position=1, title="Primeira")]
    )

    assert [entry.track.title for entry in queue.entries] == ["Primeira", "Segunda"]
    assert [entry.status for entry in queue.entries] == [
        QueueStatus.PENDING,
        QueueStatus.PENDING,
    ]


def test_queue_associates_candidate_with_original_track():
    queue = MusicQueue([MusicTrack(position=1, title="Solicitada")])
    selected = candidate("Resultado escolhido")

    queue.select(1, selected)

    entry = queue.entries[0]
    assert entry.track.title == "Solicitada"
    assert entry.candidate == selected
    assert entry.status is QueueStatus.SELECTED


def test_queue_can_keep_unmatched_track_pending():
    queue = MusicQueue([MusicTrack(position=1, title="Sem resultado")])

    queue.leave_pending(1, "Sem correspondência")

    assert queue.entries[0].status is QueueStatus.PENDING
    assert queue.entries[0].candidate is None
    assert queue.entries[0].message == "Sem correspondência"


def test_queue_rejects_missing_or_duplicate_positions():
    with pytest.raises(ValueError, match="únicas e contínuas"):
        MusicQueue([MusicTrack(position=1, title="A"), MusicTrack(position=3, title="B")])


def test_only_selected_track_can_be_marked_played():
    queue = MusicQueue([MusicTrack(position=1, title="Faixa")])

    with pytest.raises(ValueError, match="Somente uma faixa selecionada"):
        queue.mark_played(1)

    queue.select(1, candidate())
    queue.mark_played(1)
    assert queue.entries[0].status is QueueStatus.PLAYED


def test_queue_records_failure_state():
    queue = MusicQueue([MusicTrack(position=1, title="Faixa")])

    queue.mark_failed(1, "erro ao pesquisar")

    assert queue.entries[0].status is QueueStatus.FAILED
    assert queue.entries[0].message == "erro ao pesquisar"
