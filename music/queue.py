from dataclasses import dataclass, replace

from music.models import MusicTrack, QueueStatus, VideoCandidate


@dataclass(frozen=True)
class QueueEntry:
    track: MusicTrack
    status: QueueStatus = QueueStatus.PENDING
    candidate: VideoCandidate | None = None
    message: str = ""


class MusicQueue:
    """Ordered playback queue whose state does not depend on a browser."""

    def __init__(self, tracks: list[MusicTrack]) -> None:
        if not tracks:
            raise ValueError("A fila precisa conter ao menos uma faixa.")

        ordered_tracks = sorted(tracks, key=lambda track: track.position)
        positions = [track.position for track in ordered_tracks]
        if positions != list(range(1, len(ordered_tracks) + 1)):
            raise ValueError("As posições da fila precisam ser únicas e contínuas.")

        self._entries = [QueueEntry(track=track) for track in ordered_tracks]

    @property
    def entries(self) -> tuple[QueueEntry, ...]:
        return tuple(self._entries)

    def select(self, position: int, candidate: VideoCandidate) -> None:
        self._update(
            position,
            QueueEntry(
                track=self._entry(position).track,
                status=QueueStatus.SELECTED,
                candidate=candidate,
            ),
        )

    def leave_pending(self, position: int, message: str = "") -> None:
        entry = self._entry(position)
        self._update(
            position,
            replace(entry, status=QueueStatus.PENDING, candidate=None, message=message),
        )

    def mark_played(self, position: int) -> None:
        entry = self._entry(position)
        if entry.status is not QueueStatus.SELECTED:
            raise ValueError("Somente uma faixa selecionada pode ser marcada como reproduzida.")
        self._update(position, replace(entry, status=QueueStatus.PLAYED, message=""))

    def mark_failed(self, position: int, message: str) -> None:
        entry = self._entry(position)
        self._update(
            position,
            replace(entry, status=QueueStatus.FAILED, message=message.strip()),
        )

    def _entry(self, position: int) -> QueueEntry:
        if type(position) is not int or not 1 <= position <= len(self._entries):
            raise ValueError(f"Posição inexistente na fila: {position!r}")
        return self._entries[position - 1]

    def _update(self, position: int, entry: QueueEntry) -> None:
        self._entries[position - 1] = entry
