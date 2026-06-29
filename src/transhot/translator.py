import os

from openai import OpenAI

from transhot.models import TextRegion, TranslatedRegion
from transhot.settings import get_openai_api_key


class TranslationError(RuntimeError):
    def __init__(self, source_text: str, original_error: Exception) -> None:
        super().__init__(str(original_error))
        self.source_text = source_text
        self.original_error = original_error


class OpenAiTranslator:
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        api_key = os.getenv("OPENAI_API_KEY") or get_openai_api_key()
        if not api_key:
            raise RuntimeError("OpenAI API Key가 설정되어 있지 않습니다.")

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def translate_regions(self, regions: list[TextRegion]) -> list[TranslatedRegion]:
        translated: list[TranslatedRegion] = []

        for region in regions:
            try:
                translated_text = self._translate(str(region.text))
            except Exception as exc:
                raise TranslationError(str(region.text), exc) from exc
            translated.append(
                TranslatedRegion(
                    original=region.text,
                    translated=translated_text,
                    bbox=region.bbox,
                )
            )

        return translated

    def _translate(self, text: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Translate the user's text into natural Korean. "
                        "Return only the translated Korean text."
                    ),
                },
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content.strip()
