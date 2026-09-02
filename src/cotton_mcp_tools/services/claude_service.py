"""Claude (Anthropic) multimodal service implementation."""

from __future__ import annotations

import base64
import logging
import re

from cotton_mcp_tools.services.base import MultimodalService
from cotton_mcp_tools.utils.config import get_config

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-20250514"

# Map common extensions / MIME types to Anthropic media_type values
_MIME_MAP: dict[str, str] = {
    "image/png": "image/png",
    "image/jpeg": "image/jpeg",
    "image/gif": "image/gif",
    "image/webp": "image/webp",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}


class ClaudeService(MultimodalService):
    """Anthropic Claude vision API service.

    Supports both base64-encoded images and HTTP(S) image URLs.
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
    ) -> None:
        """Initialize the Claude service.

        Args:
            api_key: Anthropic API key. Falls back to config if not provided.
            default_model: Default model name. Falls back to config if not provided.
        """
        config = get_config()
        self._api_key = api_key or config.anthropic_api_key
        self._default_model = default_model or _DEFAULT_MODEL

        if not self._api_key:
            raise ValueError(
                "Anthropic API key is required. "
                "Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key to the constructor."
            )

    async def analyze_image(
        self,
        image: str,
        prompt: str,
        model: str | None = None,
    ) -> str:
        """Analyze an image using Claude's vision API.

        Args:
            image: Base64-encoded image data (with or without data URI prefix)
                   or an HTTP(S) URL pointing to an image.
            prompt: Text prompt describing what to analyze.
            model: Optional model override.

        Returns:
            The model's text response.

        Raises:
            ValueError: If the image format is invalid.
            RuntimeError: If the API call fails.
        """
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self._api_key)
        resolved_model = model or self._default_model

        image_block = self._build_image_block(image)

        logger.info("Calling Claude vision API with model=%s", resolved_model)
        try:
            response = await client.messages.create(
                model=resolved_model,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [image_block, {"type": "text", "text": prompt}],
                    }
                ],
            )
        except Exception as exc:
            logger.error("Claude API call failed: %s", exc)
            raise RuntimeError(f"Claude API call failed: {exc}") from exc

        # Anthropic returns a list of content blocks; concatenate text blocks
        result = "".join(
            block.text for block in response.content if block.type == "text"
        )
        logger.debug("Claude response length: %d chars", len(result))
        return result

    @staticmethod
    def _build_image_block(image: str) -> dict:
        """Build the image content block for the Anthropic API.

        Args:
            image: Base64-encoded image (raw or with data URI) or HTTP(S) URL.

        Returns:
            A dict suitable for the ``image`` content part.

        Raises:
            ValueError: If the image string is empty.
        """
        if not image:
            raise ValueError("Image must not be empty.")

        if image.startswith(("http://", "https://")):
            # Use URL-based source
            return {
                "type": "image",
                "source": {"type": "url", "url": image},
            }

        # Parse data URI or raw base64
        media_type = "image/png"
        base64_data = image

        if image.startswith("data:"):
            match = re.match(r"data:([^;]+);base64,(.*)", image, re.DOTALL)
            if not match:
                raise ValueError(f"Invalid data URI format: {image[:80]}...")
            media_type = match.group(1)
            base64_data = match.group(2)
        else:
            # Validate that it looks like base64
            try:
                base64.b64decode(base64_data, validate=True)
            except Exception as exc:
                raise ValueError(
                    f"Image is neither a valid URL nor valid base64: {exc}"
                ) from exc

        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64_data,
            },
        }
