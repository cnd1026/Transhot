from pathlib import Path

import easyocr
import numpy as np
from PIL import Image, UnidentifiedImageError

from transhot.models import TextRegion


class EasyOcrService:
    def __init__(self) -> None:
        self._reader: easyocr.Reader | None = None

    def extract(self, image_path: Path) -> list[TextRegion]:
        image_array = self._load_image(image_path)
        reader = self._get_reader()
        results = reader.readtext(image_array, detail=1, paragraph=False)
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

    def _load_image(self, image_path: Path) -> np.ndarray:
        if not image_path.exists():
            raise RuntimeError(f"이미지 파일을 읽을 수 없습니다: {image_path}")

        try:
            with Image.open(image_path) as image:
                return np.array(image.convert("RGB"))
        except (OSError, UnidentifiedImageError) as exc:
            raise RuntimeError(f"이미지 파일을 읽을 수 없습니다: {image_path}") from exc

    def _get_reader(self) -> easyocr.Reader:
        if self._reader is None:
            self._reader = easyocr.Reader(["en", "ko"], gpu=False)
        return self._reader
