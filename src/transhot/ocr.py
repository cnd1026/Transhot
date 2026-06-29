from pathlib import Path

import easyocr

from transhot.models import TextRegion


class EasyOcrService:
    def __init__(self) -> None:
        self._reader: easyocr.Reader | None = None

    def extract(self, image_path: Path) -> list[TextRegion]:
        reader = self._get_reader()
        results = reader.readtext(str(image_path), detail=1, paragraph=False)
        regions: list[TextRegion] = []

        for box, text, confidence in results:
            if not text.strip() or confidence < 0.2:
                continue

            xs = [int(point[0]) for point in box]
            ys = [int(point[1]) for point in box]
            regions.append(
                TextRegion(
                    text=text.strip(),
                    bbox=(min(xs), min(ys), max(xs), max(ys)),
                )
            )

        return regions

    def _get_reader(self) -> easyocr.Reader:
        if self._reader is None:
            self._reader = easyocr.Reader(["en", "ko"], gpu=False)
        return self._reader
