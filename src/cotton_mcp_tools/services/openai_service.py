"""OpenAI multimodal service implementation."""

from __future__ import annotations

import logging

from cotton_mcp_tools.services.base import MultimodalService
from cotton_mcp_tools.utils.config import get_config

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gpt-4o"


class OpenAIService(MultimodalService):
    """OpenAI vision API service.

    Supports both base64-encoded images and HTTP(S) image URLs.
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
    ) -> None:
        """Initialize the OpenAI service.

        Args:
            api_key: OpenAI API key. Falls back to config if not provided.
            default_model: Default model name. Falls back to config if not provided.
        """
        config = get_config()
        self._api_key = api_key or config.openai_api_key
        self._default_model = default_model or config.default_model or _DEFAULT_MODEL

        if not self._api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
                "or pass api_key to the constructor."
            )

    async def analyze_image(
        self,
        image: str,
        prompt: str,
        model: str | None = None,
    ) -> str:
        """Analyze an image using OpenAI's vision API.

        Args:
            image: Base64-encoded image data (with or without data URI prefix)
                   or an HTTP(S) URL pointing to an image.
            prompt: Text prompt describing what to analyze.
            model: Optional model override (e.g. "gpt-4o", "gpt-4o-mini").

        Returns:
            The model's text response.

        Raises:
            ValueError: If the image format is invalid.
            RuntimeError: If the API call fails.
        """
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key)
        resolved_model = model or self._default_model

        image_content = self._build_image_content(image)

        logger.info("Calling OpenAI vision API with model=%s", resolved_model)
        try:
            response = await client.chat.completions.create(
                model=resolved_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            image_content,
                        ],
                    }
                ],
                max_tokens=4096,
            )
        except Exception as exc:
            logger.error("OpenAI API call failed: %s", exc)
            raise RuntimeError(f"OpenAI API call failed: {exc}") from exc

        result = response.choices[0].message.content or ""
        logger.debug("OpenAI response length: %d chars", len(result))
        return result

    @staticmethod
    def _build_image_content(image: str) -> dict:
        """Build the image content block for the OpenAI API.

        Args:
            image: Base64-encoded image or HTTP(S) URL.

        Returns:
            A dict suitable for the ``image_url`` content part.

        Raises:
            ValueError: If the image string is empty.
        """
        if not image:
            raise ValueError("Image must not be empty.")

        if image.startswith(("http://", "https://")):
            return {
                "type": "image_url",
                "image_url": {"url": image},
            }

        # Assume base64-encoded data
        if image.startswith("data:"):
            # Already has a data URI prefix
            url = image
        else:
            # Raw base64 — wrap with a default data URI
            url = f"data:image/png;base64,{image}"

        return {
            "type": "image_url",
            "image_url": {"url": url},
        }
