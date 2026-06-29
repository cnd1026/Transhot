from dataclasses import dataclass


@dataclass(frozen=True)
class TextRegion:
    text: str
    bbox: tuple[int, int, int, int]


@dataclass(frozen=True)
class TranslatedRegion:
    original: str
    translated: str
    bbox: tuple[int, int, int, int]
