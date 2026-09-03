"""OCR service for text recognition from images.

Supports multiple OCR backends:
- llm: Uses multimodal LLMs (OpenAI or Claude) for OCR
- paddleocr: Uses PaddleOCR for fast local inference
- easyocr: Uses EasyOCR for simple text recognition

References:
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
- EasyOCR: https://github.com/JaidedAI/EasyOCR
- Surya: https://github.com/VikParuchuri/surya
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

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
      "confidence": 0.95,
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


def _load_image_bytes(image: str) -> bytes:
    """Load image and return raw bytes.

    Args:
        image: Base64 data URI, local file path, or HTTP(S) URL.

    Returns:
        Image bytes.

    Raises:
        ValueError: If image format is invalid.
        FileNotFoundError: If local file not found.
    """
    import httpx

    # Handle data URI
    if image.startswith("data:"):
        # Extract base64 data from data URI
        _, b64data = image.split(",", 1)
        return base64.b64decode(b64data)

    # Handle HTTP(S) URL
    if image.startswith(("http://", "https://")):
        response = httpx.get(image, timeout=30)
        response.raise_for_status()
        return response.content

    # Handle local file
    path = Path(image).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")
    return path.read_bytes()


class PaddleOCRBackend:
    """PaddleOCR backend for fast local OCR inference.

    Requires: pip install paddlepaddle paddleocr
    """

    def __init__(self, languages: str = "ch") -> None:
        """Initialize PaddleOCR backend.

        Args:
            languages: Comma-separated language codes (e.g., "ch,en").
        """
        self._languages = [lang.strip() for lang in languages.split(",")]
        self._ocr = None

    def _get_ocr(self):
        """Lazy initialize PaddleOCR instance."""
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                # Use first language as primary
                self._ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=self._languages[0],
                    show_log=False,
                )
            except ImportError:
                raise RuntimeError(
                    "PaddleOCR is not installed. "
                    "Install with: pip install paddlepaddle paddleocr"
                )
        return self._ocr

    async def recognize(
        self,
        image: str,
        language: str = "zh",
    ) -> Dict[str, Any]:
        """Recognize text using PaddleOCR.

        Args:
            image: Image path or URL.
            language: Language code.

        Returns:
            OCR result dictionary.
        """
        import asyncio

        ocr = self._get_ocr()

        # Load image
        image_bytes = _load_image_bytes(image)

        # Run OCR in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: ocr.ocr(image_bytes, cls=True),
        )

        # Parse results
        texts = []
        full_text_parts = []

        if result and result[0]:
            for line in result[0]:
                bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text = line[1][0]  # Recognized text
                confidence = line[1][1]  # Confidence score

                texts.append({
                    "content": text,
                    "confidence": round(confidence, 4),
                    "bbox": bbox,
                    "type": "body",
                })
                full_text_parts.append(text)

        return {
            "texts": texts,
            "full_text": "\n".join(full_text_parts),
            "language": language,
            "has_text": len(texts) > 0,
            "backend": "paddleocr",
        }


class EasyOCRBackend:
    """EasyOCR backend for simple text recognition.

    Requires: pip install easyocr
    """

    def __init__(self, languages: str = "ch,en") -> None:
        """Initialize EasyOCR backend.

        Args:
            languages: Comma-separated language codes (e.g., "ch,en").
        """
        self._languages = [lang.strip() for lang in languages.split(",")]
        self._reader = None

    def _get_reader(self):
        """Lazy initialize EasyOCR reader."""
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(self._languages)
            except ImportError:
                raise RuntimeError(
                    "EasyOCR is not installed. "
                    "Install with: pip install easyocr"
                )
        return self._reader

    async def recognize(
        self,
        image: str,
        language: str = "zh",
    ) -> Dict[str, Any]:
        """Recognize text using EasyOCR.

        Args:
            image: Image path or URL.
            language: Language code.

        Returns:
            OCR result dictionary.
        """
        import asyncio

        reader = self._get_reader()

        # Load image
        image_bytes = _load_image_bytes(image)

        # Run OCR in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: reader.readtext(image_bytes),
        )

        # Parse results
        texts = []
        full_text_parts = []

        for (bbox, text, confidence) in result:
            texts.append({
                "content": text,
                "confidence": round(confidence, 4),
                "bbox": bbox,
                "type": "body",
            })
            full_text_parts.append(text)

        return {
            "texts": texts,
            "full_text": "\n".join(full_text_parts),
            "language": language,
            "has_text": len(texts) > 0,
            "backend": "easyocr",
        }


class LLMOCRBackend:
    """LLM-based OCR backend using multimodal models."""

    def __init__(self, provider: str, model: str | None = None) -> None:
        """Initialize LLM OCR backend.

        Args:
            provider: Provider name ("openai" or "claude").
            model: Model name.
        """
        self._provider_name = provider
        self._model_override = model

        if provider not in _PROVIDER_MAP:
            valid = ", ".join(sorted(_PROVIDER_MAP.keys()))
            raise ValueError(
                f"Unknown provider '{provider}'. Valid providers: {valid}"
            )

        service_cls = _PROVIDER_MAP[provider]
        self._service = service_cls()

    async def recognize(
        self,
        image: str,
        language: str = "zh",
        model: str | None = None,
    ) -> Dict[str, Any]:
        """Recognize text using multimodal LLM.

        Args:
            image: Base64 data URI or URL.
            language: Language code.
            model: Optional model override.

        Returns:
            OCR result dictionary.
        """
        import json

        prompt = f"{_OCR_SYSTEM_PROMPT}\n\nPlease analyze this image and extract all text content. The expected language is: {language}"

        resolved_model = model or self._model_override

        logger.info(
            "Recognizing text using %s/%s",
            self._provider_name,
            resolved_model or "default",
        )

        result = await self._service.analyze_image(
            image=image,
            prompt=prompt,
            model=resolved_model,
        )

        # Try to parse JSON response
        try:
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = result[json_start:json_end]
                parsed = json.loads(json_str)
                parsed["backend"] = "llm"
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback
        return {
            "texts": [],
            "full_text": result,
            "language": language,
            "has_text": bool(result.strip()),
            "backend": "llm",
        }


# Backend registry
_BACKEND_REGISTRY = {
    "paddleocr": PaddleOCRBackend,
    "easyocr": EasyOCRBackend,
    "llm": None,  # Special case, uses LLMOCRBackend
}


def get_available_backends() -> List[str]:
    """Get list of available OCR backends.

    Returns:
        List of backend names that can be used.
    """
    available = ["llm"]  # LLM is always available

    try:
        import paddleocr
        available.append("paddleocr")
    except ImportError:
        pass

    try:
        import easyocr
        available.append("easyocr")
    except ImportError:
        pass

    return available


class OCRService:
    """OCR service for text recognition from images.

    Supports multiple OCR backends:
    - llm: Uses multimodal LLMs (OpenAI or Claude)
    - paddleocr: Uses PaddleOCR for fast local inference
    - easyocr: Uses EasyOCR for simple text recognition

    Supports both local file paths and HTTP(S) URLs.
    """

    def __init__(
        self,
        backend: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        languages: str | None = None,
    ) -> None:
        """Initialize the OCR service.

        Args:
            backend: OCR backend ("llm", "paddleocr", "easyocr").
                     Falls back to config OCR_BACKEND or "llm".
            provider: LLM provider name (only for "llm" backend).
            model: Model name (only for "llm" backend).
            languages: Comma-separated language codes for local backends.
                      Falls back to config OCR_LANGUAGES or "ch,en".
        """
        config = get_config()
        self._backend_name = backend or config.ocr_backend or "llm"
        self._languages = languages or config.ocr_languages or "ch,en"

        # Initialize the appropriate backend
        if self._backend_name == "llm":
            resolved_provider, resolved_model = _resolve_provider(model)
            if provider:
                resolved_provider = provider.lower()
            self._backend = LLMOCRBackend(resolved_provider, resolved_model)
            self._provider_name = resolved_provider
        elif self._backend_name == "paddleocr":
            self._backend = PaddleOCRBackend(self._languages)
            self._provider_name = "paddleocr"
        elif self._backend_name == "easyocr":
            self._backend = EasyOCRBackend(self._languages)
            self._provider_name = "easyocr"
        else:
            valid = ", ".join(sorted(_BACKEND_REGISTRY.keys()))
            raise ValueError(
                f"Unknown OCR backend '{self._backend_name}'. Valid backends: {valid}"
            )

    @property
    def backend_name(self) -> str:
        """Get the current backend name."""
        return self._backend_name

    async def recognize_text(
        self,
        image: str,
        language: str = "zh",
        model: str | None = None,
    ) -> Dict[str, Any]:
        """Recognize text from an image.

        Args:
            image: Base64-encoded image data, HTTP(S) URL, or local file path.
            language: Expected language code (default: "zh" for Chinese).
            model: Optional model override (only for "llm" backend).

        Returns:
            Dictionary containing:
                - texts: List of text blocks with content, confidence, and bbox
                - full_text: Complete text in reading order
                - language: Detected language
                - has_text: Whether text was found
                - backend: OCR backend used

        Raises:
            ValueError: If the image format is invalid.
            RuntimeError: If the API call fails or backend not available.
        """
        logger.info(
            "Recognizing text from image using %s backend",
            self._backend_name,
        )

        # For local backends, convert data URI to bytes
        if self._backend_name in ("paddleocr", "easyocr") and image.startswith("data:"):
            image_bytes = base64.b64decode(image.split(",", 1)[1])
            result = await self._backend.recognize(image_bytes, language)
        else:
            result = await self._backend.recognize(image, language, model=model) \
                if self._backend_name == "llm" \
                else await self._backend.recognize(image, language)

        return result

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
                    "backend": self._backend_name,
                    "error": str(exc),
                })
        return results

    async def detect_text_regions(
        self,
        image: str,
        language: str = "zh",
    ) -> Dict[str, Any]:
        """Detect text regions in an image without full recognition.

        Args:
            image: Image path or URL.
            language: Language code.

        Returns:
            Dictionary with detected text regions and bounding boxes.
        """
        result = await self.recognize_text(image, language)

        # Extract just the regions
        regions = []
        for text_block in result.get("texts", []):
            if "bbox" in text_block:
                regions.append({
                    "bbox": text_block["bbox"],
                    "confidence": text_block.get("confidence", 0),
                })

        return {
            "regions": regions,
            "total_regions": len(regions),
            "image_size": None,  # Could be added if needed
        }
