"""OCR service for text recognition from images.

Uses multimodal LLMs (OpenAI or Claude) to recognize and extract
text content from images.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from cotton_mcp_tools.services.claude_service import ClaudeService
from cotton_mcp_tools.services.openai_service import OpenAIService
from cotton_mcp_tools.utils.config import get_config

logger = logging.getLogger(__name__)

_PROVIDER_MAP = {
    "openai": OpenAIService,
    "claude": ClaudeService,
}

_OCR_SYSTEM_PROMPT = """\
You are an expert OCR (Optical Character Recognition) system.
Your task is to accurately extract ALL text content from the provided image.

Guidelines:
1. Extract ALL visible text, including headers, body text, captions, watermarks, etc.
2. Preserve the logical reading order of the text.
3. Maintain the original language (Chinese, English, etc.) without translation.
4. If there are tables or structured data, represent them in a readable format.
5. If the image contains no text, return an empty result.
6. For each text block, estimate your confidence level (high/medium/low).

Output format (JSON):
{
  "texts": [
    {
      "content": "extracted text",
      "confidence": "high|medium|low",
      "type": "header|body|caption|other"
    }
  ],
  "full_text": "complete text concatenated in reading order",
  "language": "detected language",
  "has_text": true|false
}
"""


def _resolve_provider(model: str | None = None) -> tuple[str, str | None]:
    """Resolve the provider and model from the given model string.

    Args:
        model: An optional model string.

    Returns:
        A tuple of (provider_name, model_name_or_None).
    """
    config = get_config()

    if model is None:
        return config.default_provider, None

    # Support "provider/model" syntax
    if "/" in model:
        provider, _, model_name = model.partition("/")
        provider = provider.strip().lower()
        if provider in _PROVIDER_MAP:
            return provider, model_name.strip() or None

    # Infer provider from model name
    model_lower = model.lower()
    if model_lower.startswith("claude") or model_lower.startswith("anthropic"):
        return "claude", model
    if (
        model_lower.startswith("gpt")
        or model_lower.startswith("o1")
        or model_lower.startswith("o3")
    ):
        return "openai", model

    # Fall back to default provider with the given model
    return config.default_provider, model


class OCRService:
    """OCR service for text recognition from images.

    Uses multimodal LLMs to extract text content from images.
    Supports both local file paths and HTTP(S) URLs.
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize the OCR service.

        Args:
            provider: Provider name ("openai" or "claude"). Auto-detected if None.
            model: Model name. Uses provider default if None.
        """
        self._provider_name, self._model_override = _resolve_provider(model)

        if provider:
            self._provider_name = provider.lower()

        if self._provider_name not in _PROVIDER_MAP:
            valid = ", ".join(sorted(_PROVIDER_MAP.keys()))
            raise ValueError(
                f"Unknown provider '{self._provider_name}'. Valid providers: {valid}"
            )

        service_cls = _PROVIDER_MAP[self._provider_name]
        self._service = service_cls()

    async def recognize_text(
        self,
        image: str,
        language: str = "zh",
        model: str | None = None,
    ) -> Dict[str, Any]:
        """Recognize text from an image.

        Args:
            image: Base64-encoded image data or HTTP(S) URL.
            language: Expected language code (default: "zh" for Chinese).
            model: Optional model override.

        Returns:
            Dictionary containing:
                - texts: List of text blocks with content, confidence, and type
                - full_text: Complete text in reading order
                - language: Detected language
                - has_text: Whether text was found

        Raises:
            ValueError: If the image format is invalid.
            RuntimeError: If the API call fails.
        """
        prompt = f"{_OCR_SYSTEM_PROMPT}\n\nPlease analyze this image and extract all text content. The expected language is: {language}"

        resolved_model = model or self._model_override

        logger.info(
            "Recognizing text from image using %s/%s",
            self._provider_name,
            resolved_model or "default",
        )

        result = await self._service.analyze_image(
            image=image,
            prompt=prompt,
            model=resolved_model,
        )

        # Try to parse JSON response
        import json

        try:
            # Find JSON in the response
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = result[json_start:json_end]
                parsed = json.loads(json_str)
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: return raw text as full_text
        return {
            "texts": [],
            "full_text": result,
            "language": language,
            "has_text": bool(result.strip()),
        }

    async def recognize_text_from_multiple(
        self,
        images: List[str],
        language: str = "zh",
        model: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Recognize text from multiple images.

        Args:
            images: List of image paths or URLs.
            language: Expected language code.
            model: Optional model override.

        Returns:
            List of recognition results, one per image.
        """
        results = []
        for image in images:
            try:
                result = await self.recognize_text(
                    image=image,
                    language=language,
                    model=model,
                )
                results.append(result)
            except Exception as exc:
                logger.error("Failed to recognize text from image %s: %s", image, exc)
                results.append({
                    "texts": [],
                    "full_text": "",
                    "language": language,
                    "has_text": False,
                    "error": str(exc),
                })
        return results
