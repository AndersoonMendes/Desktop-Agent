from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class MusicTrack:
    """A song identified in an image, with its original visual position."""

    position: int
    title: str
    artist: str = ""
    ambiguous: bool = False
    note: str = ""

    def __post_init__(self) -> None:
        if type(self.position) is not int or self.position < 1:
            raise ValueError("A posição da música precisa ser maior que zero.")
        if not all(isinstance(value, str) for value in (self.title, self.artist, self.note)):
            raise TypeError("Título, artista e observação precisam ser textos.")
        if not isinstance(self.ambiguous, bool):
            raise TypeError("A ambiguidade precisa ser indicada com verdadeiro ou falso.")
        if not self.title.strip() and not self.ambiguous:
            raise ValueError("Uma música sem título precisa estar marcada como ambígua.")


@dataclass(frozen=True)
class VideoCandidate:
    """A YouTube result explicitly associated with a requested music track."""

    title: str
    channel: str
    duration: str
    metadata: str
    url: str


class QueueStatus(str, Enum):
    PENDING = "pendente"
    SELECTED = "selecionada"
    PLAYED = "reproduzida"
    FAILED = "falha"
