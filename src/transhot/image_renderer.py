from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from transhot.models import TranslatedRegion


class ImageRenderer:
    def __init__(self, font_path: Path | None = None) -> None:
        self._font_path = font_path or self._find_default_korean_font()

    def render(
        self,
        image_path: Path,
        regions: list[TranslatedRegion],
        output_dir: Path,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)

        image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(image)

        for region in regions:
            self._paint_region(draw, region)

        output_path = output_dir / f"{image_path.stem}_translated{image_path.suffix}"
        image.save(output_path)
        return output_path

    def _paint_region(self, draw: ImageDraw.ImageDraw, region: TranslatedRegion) -> None:
        x1, y1, x2, y2 = region.bbox
        padding = max(3, int(min(x2 - x1, y2 - y1) * 0.08))
        draw.rectangle(region.bbox, fill="white")

        inner_width = max(1, x2 - x1 - padding * 2)
        inner_height = max(1, y2 - y1 - padding * 2)
        font, lines = self._fit_text(draw, region.translated, inner_width, inner_height)

        line_heights = [self._text_size(draw, line, font)[1] for line in lines]
        total_height = sum(line_heights) + max(0, len(lines) - 1) * 2
        current_y = y1 + padding + max(0, (inner_height - total_height) // 2)

        for line, line_height in zip(lines, line_heights):
            line_width, _ = self._text_size(draw, line, font)
            draw.text(
                (x1 + padding + max(0, (inner_width - line_width) // 2), current_y),
                line,
                fill="black",
                font=font,
            )
            current_y += line_height + 2

    def _fit_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        max_width: int,
        max_height: int,
    ) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, list[str]]:
        for font_size in range(28, 7, -1):
            font = self._load_font(font_size)
            lines = self._wrap_text(draw, text, font, max_width)
            width = max((self._text_size(draw, line, font)[0] for line in lines), default=0)
            height = sum(self._text_size(draw, line, font)[1] for line in lines)
            height += max(0, len(lines) - 1) * 2
            if width <= max_width and height <= max_height:
                return font, lines

        font = self._load_font(8)
        return font, self._wrap_text(draw, text, font, max_width)

    def _wrap_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> list[str]:
        words = text.split()
        if not words:
            return [""]

        lines: list[str] = []
        current = ""

        for word in words:
            candidate = f"{current} {word}".strip()
            if self._text_size(draw, candidate, font)[0] <= max_width:
                current = candidate
                continue

            if current:
                lines.append(current)
            current = word

            while self._text_size(draw, current, font)[0] > max_width and len(current) > 1:
                split_at = self._find_split_index(draw, current, font, max_width)
                lines.append(current[:split_at])
                current = current[split_at:]

        if current:
            lines.append(current)

        return lines

    def _find_split_index(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> int:
        for index in range(1, len(text) + 1):
            if self._text_size(draw, text[:index], font)[0] > max_width:
                return max(1, index - 1)
        return len(text)

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        if self._font_path and self._font_path.exists():
            return ImageFont.truetype(str(self._font_path), size=size)
        return ImageFont.load_default()

    def _find_default_korean_font(self) -> Path | None:
        candidates = [
            Path("C:/Windows/Fonts/malgun.ttf"),
            Path("C:/Windows/Fonts/NotoSansCJK-Regular.ttc"),
            Path("C:/Windows/Fonts/gulim.ttc"),
        ]
        return next((path for path in candidates if path.exists()), None)

    def _text_size(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ) -> tuple[int, int]:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
