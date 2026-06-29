from pathlib import Path

from transhot.image_renderer import ImageRenderer
from transhot.ocr import EasyOcrService
from transhot.translator import OpenAiTranslator


class ImageTranslationProcessor:
    def __init__(
        self,
        ocr_service: EasyOcrService | None = None,
        translator: OpenAiTranslator | None = None,
        renderer: ImageRenderer | None = None,
    ) -> None:
        self._ocr_service = ocr_service or EasyOcrService()
        self._translator = translator
        self._renderer = renderer or ImageRenderer()

    def process(self, image_path: Path, output_dir: Path) -> Path:
        regions = self._ocr_service.extract(image_path)
        if not regions:
            raise RuntimeError("이미지에서 텍스트를 찾지 못했습니다.")

        translator = self._translator or OpenAiTranslator()
        translated_regions = translator.translate_regions(regions)
        return self._renderer.render(image_path, translated_regions, output_dir)
