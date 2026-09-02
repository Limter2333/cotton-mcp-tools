"""OCR (Optical Character Recognition) tools for MCP server.

Provides tools to recognize and extract text content from images
using multimodal LLMs.
"""

from __future__ import annotations

import json
import logging

from mcp.server.fastmcp import FastMCP

from cotton_mcp_tools.services.ocr_service import OCRService

logger = logging.getLogger(__name__)


def _load_image(image: str) -> str:
    """Load an image and return it as a base64-encoded string or URL.

    Args:
        image: A file path (absolute or relative) or an HTTP(S) URL.

    Returns:
        The image as a base64 data URI string, or the original URL if it is
        already a remote URL.

    Raises:
        FileNotFoundError: If the local file does not exist.
        ValueError: If the path is not a recognized image type.
    """
    import base64
    import mimetypes
    from pathlib import Path

    if image.startswith(("http://", "https://")):
        return image

    path = Path(image).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    mime_type, _ = mimetypes.guess_type(str(path))
    if mime_type is None or not mime_type.startswith("image/"):
        # Try common image extensions
        ext_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        mime_type = ext_map.get(path.suffix.lower())

    if mime_type is None or not mime_type.startswith("image/"):
        raise ValueError(
            f"Unsupported image type for file '{path.name}'. "
            "Please provide a valid image file (PNG, JPG, GIF, WebP, BMP)."
        )

    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def register_ocr_tools(server: FastMCP) -> None:
    """Register OCR tools with the MCP server."""

    @server.tool()
    async def ocr_recognize_text(
        image: str,
        language: str = "zh",
        model: str | None = None,
    ) -> str:
        """Recognize and extract text content from an image.

        Uses multimodal LLM to perform OCR on the provided image.
        Supports local file paths and HTTP(S) URLs.

        Args:
            image: Path to a local image file or an HTTP(S) URL.
            language: Expected language code - "zh" (Chinese), "en" (English), etc.
                      Default is "zh".
            model: Optional model override. Can be a plain model name
                   (e.g. "gpt-4o") or a prefixed name (e.g. "openai/gpt-4o").

        Returns:
            JSON formatted OCR result with extracted text, confidence levels,
            and metadata.
        """
        # Load and prepare image
        try:
            image_data = _load_image(image)
        except FileNotFoundError as exc:
            return json.dumps({"error": str(exc), "has_text": False}, ensure_ascii=False)
        except ValueError as exc:
            return json.dumps({"error": str(exc), "has_text": False}, ensure_ascii=False)

        # Create OCR service
        try:
            service = OCRService(model=model)
        except ValueError as exc:
            return json.dumps({"error": str(exc), "has_text": False}, ensure_ascii=False)

        # Perform OCR
        try:
            result = await service.recognize_text(
                image=image_data,
                language=language,
            )
            return json.dumps(result, ensure_ascii=False, indent=2)
        except RuntimeError as exc:
            logger.error("OCR failed: %s", exc)
            return json.dumps(
                {"error": f"OCR failed: {exc}", "has_text": False},
                ensure_ascii=False,
            )
        except Exception as exc:
            logger.error("Unexpected OCR error: %s", exc)
            return json.dumps(
                {"error": f"Unexpected error: {exc}", "has_text": False},
                ensure_ascii=False,
            )

    @server.tool()
    async def ocr_recognize_batch(
        images: list[str],
        language: str = "zh",
        model: str | None = None,
    ) -> str:
        """Recognize text from multiple images in batch.

        Args:
            images: List of image paths or HTTP(S) URLs.
            language: Expected language code. Default is "zh".
            model: Optional model override.

        Returns:
            JSON formatted results with OCR results for each image.
        """
        # Load all images
        loaded_images = []
        for img in images:
            try:
                loaded_images.append(_load_image(img))
            except (FileNotFoundError, ValueError) as exc:
                loaded_images.append(None)
                logger.warning("Failed to load image %s: %s", img, exc)

        # Create OCR service
        try:
            service = OCRService(model=model)
        except ValueError as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

        # Perform batch OCR
        results = []
        for i, (original, loaded) in enumerate(zip(images, loaded_images)):
            if loaded is None:
                results.append({
                    "image": original,
                    "error": "Failed to load image",
                    "has_text": False,
                })
                continue

            try:
                result = await service.recognize_text(
                    image=loaded,
                    language=language,
                )
                result["image"] = original
                results.append(result)
            except Exception as exc:
                logger.error("OCR failed for image %s: %s", original, exc)
                results.append({
                    "image": original,
                    "error": str(exc),
                    "has_text": False,
                })

        return json.dumps({
            "total": len(results),
            "results": results,
        }, ensure_ascii=False, indent=2)
