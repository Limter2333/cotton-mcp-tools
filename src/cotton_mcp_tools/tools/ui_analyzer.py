"""UI Analyzer tool - analyze UI screenshots and generate frontend code."""

from __future__ import annotations

import base64
import logging
import mimetypes
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from cotton_mcp_tools.services.claude_service import ClaudeService
from cotton_mcp_tools.services.openai_service import OpenAIService
from cotton_mcp_tools.utils.config import get_config

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a senior frontend engineer specializing in UI implementation.
Analyze the provided UI screenshot and generate clean, production-ready code.

Guidelines:
- Write semantic, accessible HTML with proper ARIA attributes when needed.
- Use modern CSS (flexbox/grid) for layout. Avoid floats.
- Keep styles scoped and well-organized.
- Use realistic placeholder text and icons where content is missing.
- Ensure the code is responsive and works across common screen sizes.
- Add brief comments explaining key layout decisions.

Output format:
- Wrap the complete code in a single fenced code block
  with the appropriate language tag.
- If the framework is "html", output a single self-contained
  HTML file (<!DOCTYPE html>).
- If the framework is "react", output a single React component
  using JSX and inline styles or CSS modules.
- If the framework is "vue", output a single Vue 3 SFC
  (<template>, <script setup>, <style scoped>).
"""

_FRAMEWORK_PROMPTS: dict[str, str] = {
    "html": (
        "Generate a single, self-contained HTML file "
        "with embedded CSS and JavaScript."
    ),
    "react": (
        "Generate a React functional component using hooks. "
        "Include all necessary imports."
    ),
    "vue": (
        "Generate a Vue 3 Single File Component (SFC) "
        "using the Composition API with <script setup>."
    ),
}

PROVIDER_MAP: dict[str, type] = {
    "openai": OpenAIService,
    "claude": ClaudeService,
}


_ALLOWED_IMAGE_MIME_TYPES: frozenset[str] = frozenset({
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff",
    "image/svg+xml",
})

# Fallback mapping for extensions that mimetypes may not know on all platforms.
_EXT_TO_MIME: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".svg": "image/svg+xml",
    ".svgz": "image/svg+xml",
}

_MAX_IMAGE_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB


def _load_image(image: str) -> str:
    """Load an image and return it as a base64-encoded string or URL.

    Args:
        image: A file path (absolute or relative) or an HTTP(S) URL.

    Returns:
        The image as a base64 data URI string, or the original URL if it is
        already a remote URL.

    Raises:
        FileNotFoundError: If the local file does not exist.
        ValueError: If the path is not a recognized image type or the file
            exceeds the size limit.
    """
    if image.startswith(("http://", "https://")):
        return image

    path = Path(image).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    mime_type, _ = mimetypes.guess_type(str(path))
    # Fall back to extension-based lookup if mimetypes doesn't recognise it.
    if mime_type is None:
        mime_type = _EXT_TO_MIME.get(path.suffix.lower())
    if mime_type is None or mime_type not in _ALLOWED_IMAGE_MIME_TYPES:
        raise ValueError(
            f"Unsupported image type '{mime_type}' for file '{path.name}'. "
            f"Allowed types: {', '.join(sorted(_ALLOWED_IMAGE_MIME_TYPES))}"
        )

    file_size = path.stat().st_size
    if file_size > _MAX_IMAGE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        limit_mb = _MAX_IMAGE_SIZE_BYTES / (1024 * 1024)
        raise ValueError(
            f"Image file '{path.name}' is too large ({size_mb:.1f} MB). "
            f"Maximum allowed size is {limit_mb:.0f} MB."
        )

    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def _resolve_provider(model: str | None) -> tuple[str, str | None]:
    """Resolve the provider and model from the given model string.

    Args:
        model: An optional model string. Can be prefixed with provider name
               (e.g. "openai/gpt-4o") or just a model name.

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
        if provider in PROVIDER_MAP:
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


def register_ui_analyzer_tools(server: FastMCP) -> None:
    """Register UI analyzer tools with the MCP server."""

    @server.tool()
    async def analyze_ui(
        image: str,
        prompt: str = (
            "Analyze this UI screenshot and generate "
            "the corresponding frontend code."
        ),
        framework: str = "html",
        model: str | None = None,
    ) -> str:
        """Analyze a UI screenshot and generate frontend code.

        Takes a UI screenshot (local file path or URL) and uses a
        multimodal LLM to produce production-ready frontend code
        that recreates the design.

        Args:
            image: Path to a local image file or an HTTP(S) URL.
            prompt: Additional analysis instructions.
            framework: Target framework - "html", "react", or "vue".
            model: Optional model override. Can be a plain model
                name (e.g. "gpt-4o") or a prefixed name
                (e.g. "openai/gpt-4o").

        Returns:
            Generated frontend code as a string.
        """
        # Validate framework
        framework = framework.lower().strip()
        if framework not in _FRAMEWORK_PROMPTS:
            valid = ", ".join(sorted(_FRAMEWORK_PROMPTS))
            return f"Error: Unsupported framework '{framework}'. Valid options: {valid}"

        # Load and prepare image
        try:
            image_data = _load_image(image)
        except FileNotFoundError as exc:
            return f"Error: {exc}"
        except ValueError as exc:
            return f"Error: {exc}"

        # Build the full prompt
        full_prompt = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"Framework: {framework}\n"
            f"{_FRAMEWORK_PROMPTS[framework]}\n\n"
            f"User instructions: {prompt}"
        )

        # Resolve provider
        provider_name, model_name = _resolve_provider(model)

        # Create service
        service_cls = PROVIDER_MAP.get(provider_name)
        if service_cls is None:
            valid = ", ".join(sorted(PROVIDER_MAP))
            return (
                f"Error: Unknown provider '{provider_name}'. "
                f"Valid providers: {valid}"
            )

        try:
            service = service_cls()
        except ValueError as exc:
            return f"Error: {exc}"

        # Call the multimodal API
        try:
            result = await service.analyze_image(
                image=image_data,
                prompt=full_prompt,
                model=model_name,
            )
        except (RuntimeError, ValueError) as exc:
            logger.error("analyze_ui failed: %s", exc)
            return f"Error analyzing UI: {exc}"

        return result
