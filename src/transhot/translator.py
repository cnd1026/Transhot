import os

from deep_translator import GoogleTranslator
from openai import OpenAI

from transhot.models import TextRegion, TranslatedRegion
from transhot.settings import get_openai_api_key, get_translation_provider


class TranslationError(RuntimeError):
    def __init__(self, source_text: str, original_error: Exception, provider: str) -> None:
        super().__init__(str(original_error))
        self.source_text = source_text
        self.original_error = original_error
        self.provider = provider


class OpenAiTranslator:
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self._provider = get_translation_provider()
        self._model = model
        self._client: OpenAI | None = None
        self._google_translator: GoogleTranslator | None = None

        if self._provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY") or get_openai_api_key()
            if not api_key:
                raise RuntimeError("OpenAI API Key가 설정되어 있지 않습니다.")
            self._client = OpenAI(api_key=api_key)

    def translate_regions(self, regions: list[TextRegion]) -> list[TranslatedRegion]:
        translated: list[TranslatedRegion] = []

        for region in regions:
            try:
                translated_text = self._translate(str(region.text))
            except Exception as exc:
                raise TranslationError(str(region.text), exc, self._provider) from exc
            translated.append(
                TranslatedRegion(
                    original=region.text,
                    translated=translated_text,
                    bbox=region.bbox,
                )
            )

        return translated

    def _translate(self, text: str) -> str:
        if self._provider == "google_free":
            return self._translate_with_google_free(text)
        return self._translate_with_openai(text)

    def _translate_with_openai(self, text: str) -> str:
        if self._client is None:
            raise RuntimeError("OpenAI translator is not initialized.")

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

    def _translate_with_google_free(self, text: str) -> str:
        if self._google_translator is None:
            self._google_translator = GoogleTranslator(source="auto", target="ko")
        return str(self._google_translator.translate(text))


def get_translation_provider_label(provider: str | None = None) -> str:
    provider = provider or get_translation_provider()
    if provider == "openai":
        return "OpenAI"
    return "Google Free Test"
