"""Tests for the UI analyzer tool."""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from cotton_mcp_tools.tools.ui_analyzer import (
    _FRAMEWORK_PROMPTS,
    _load_image,
    _resolve_provider,
)

# ---------------------------------------------------------------------------
# _load_image tests
# ---------------------------------------------------------------------------


class TestLoadImage:
    """Tests for the _load_image helper."""

    def test_http_url_passthrough(self):
        """HTTP URLs should be returned as-is."""
        url = "https://example.com/screenshot.png"
        assert _load_image(url) == url

    def test_https_url_passthrough(self):
        """HTTPS URLs should be returned as-is."""
        url = "http://example.com/img.jpg"
        assert _load_image(url) == url

    def test_local_file_not_found(self, tmp_path: Path):
        """Non-existent local files should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="not found"):
            _load_image(str(tmp_path / "missing.png"))

    def test_local_png_file(self, tmp_path: Path):
        """A local PNG file should be loaded and base64-encoded."""
        png_file = tmp_path / "test.png"
        # Minimal valid PNG header + data
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        png_file.write_bytes(png_data)

        result = _load_image(str(png_file))

        assert result.startswith("data:image/png;base64,")
        # Verify the base64 payload is correct
        b64_part = result.split(",", 1)[1]
        decoded = base64.b64decode(b64_part)
        assert decoded == png_data

    def test_local_jpg_file(self, tmp_path: Path):
        """A local JPEG file should be detected by MIME type."""
        jpg_file = tmp_path / "photo.jpg"
        jpg_data = b"\xff\xd8\xff\xe0" + b"\x00" * 32
        jpg_file.write_bytes(jpg_data)

        result = _load_image(str(jpg_file))

        assert result.startswith("data:image/jpeg;base64,")

    def test_unknown_extension_raises_value_error(self, tmp_path: Path):
        """Files with unknown extensions should raise ValueError."""
        img_file = tmp_path / "image.xyz"
        img_data = b"\x00" * 16
        img_file.write_bytes(img_data)

        with pytest.raises(ValueError, match="Unsupported image type"):
            _load_image(str(img_file))

    def test_non_image_file_raises_value_error(self, tmp_path: Path):
        """Non-image files (e.g. .txt) should raise ValueError."""
        txt_file = tmp_path / "secret.txt"
        txt_file.write_text("sensitive data")

        with pytest.raises(ValueError, match="Unsupported image type"):
            _load_image(str(txt_file))

    def test_webp_file_accepted(self, tmp_path: Path):
        """A local WebP file should be loaded correctly."""
        webp_file = tmp_path / "image.webp"
        webp_data = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 16
        webp_file.write_bytes(webp_data)

        result = _load_image(str(webp_file))

        assert result.startswith("data:image/webp;base64,")

    def test_file_too_large_raises_value_error(self, tmp_path: Path):
        """Files exceeding the size limit should raise ValueError."""
        large_file = tmp_path / "huge.png"
        # Write just past the 20 MB limit (create sparse-like content)
        with large_file.open("wb") as f:
            f.seek(20 * 1024 * 1024)  # 20 MB
            f.write(b"\x00")  # 20 MB + 1 byte

        with pytest.raises(ValueError, match="too large"):
            _load_image(str(large_file))

    def test_file_at_size_limit_accepted(self, tmp_path: Path):
        """Files exactly at the 20 MB limit should be accepted."""
        limit_file = tmp_path / "exact_limit.png"
        with limit_file.open("wb") as f:
            f.seek(20 * 1024 * 1024 - 1)  # exactly 20 MB
            f.write(b"\x00")

        result = _load_image(str(limit_file))

        assert result.startswith("data:image/png;base64,")

    def test_relative_path_resolution(self, tmp_path: Path, monkeypatch):
        """Relative paths should be resolved against cwd."""
        img_file = tmp_path / "rel.png"
        img_data = b"\x89PNG" + b"\x00" * 16
        img_file.write_bytes(img_data)

        monkeypatch.chdir(tmp_path)
        result = _load_image("rel.png")
        assert result.startswith("data:image/png;base64,")


# ---------------------------------------------------------------------------
# _resolve_provider tests
# ---------------------------------------------------------------------------


class TestResolveProvider:
    """Tests for the _resolve_provider helper."""

    def test_none_returns_default(self):
        """None model should return the configured default provider."""
        provider, model = _resolve_provider(None)
        assert provider == "openai"  # default from config
        assert model is None

    def test_slash_syntax_openai(self):
        """'openai/gpt-4o' should resolve to openai provider."""
        provider, model = _resolve_provider("openai/gpt-4o")
        assert provider == "openai"
        assert model == "gpt-4o"

    def test_slash_syntax_claude(self):
        """'claude/claude-sonnet-4-20250514' should resolve to claude provider."""
        provider, model = _resolve_provider("claude/claude-sonnet-4-20250514")
        assert provider == "claude"
        assert model == "claude-sonnet-4-20250514"

    def test_gpt_model_infers_openai(self):
        """A model starting with 'gpt' should infer openai provider."""
        provider, model = _resolve_provider("gpt-4o-mini")
        assert provider == "openai"
        assert model == "gpt-4o-mini"

    def test_claude_model_infers_claude(self):
        """A model starting with 'claude' should infer claude provider."""
        provider, model = _resolve_provider("claude-sonnet-4-20250514")
        assert provider == "claude"
        assert model == "claude-sonnet-4-20250514"

    def test_o1_model_infers_openai(self):
        """A model starting with 'o1' should infer openai provider."""
        provider, model = _resolve_provider("o1-preview")
        assert provider == "openai"
        assert model == "o1-preview"

    def test_o3_model_infers_openai(self):
        """A model starting with 'o3' should infer openai provider."""
        provider, model = _resolve_provider("o3-mini")
        assert provider == "openai"
        assert model == "o3-mini"

    def test_empty_model_uses_default_provider(self):
        """An empty model string should use the default provider."""
        provider, model = _resolve_provider("")
        assert provider == "openai"  # default
        assert model == ""

    def test_unknown_model_uses_default_provider(self):
        """An unrecognized model should use the default provider."""
        provider, model = _resolve_provider("some-custom-model")
        assert provider == "openai"  # default
        assert model == "some-custom-model"


# ---------------------------------------------------------------------------
# Framework validation tests
# ---------------------------------------------------------------------------


class TestFrameworkValidation:
    """Tests for framework parameter validation."""

    def test_valid_frameworks(self):
        """All expected frameworks should have prompt templates."""
        assert "html" in _FRAMEWORK_PROMPTS
        assert "react" in _FRAMEWORK_PROMPTS
        assert "vue" in _FRAMEWORK_PROMPTS

    def test_framework_prompts_are_strings(self):
        """All framework prompts should be non-empty strings."""
        for fw, prompt in _FRAMEWORK_PROMPTS.items():
            assert isinstance(prompt, str) and len(prompt) > 0, f"Empty prompt for {fw}"

    def test_anthropic_model_infers_claude(self):
        """A model starting with 'anthropic' should infer claude provider."""
        provider, model = _resolve_provider("anthropic/claude-3-opus")
        assert provider == "claude"
        # When 'anthropic' is not in PROVIDER_MAP, the full model string is returned
        assert model == "anthropic/claude-3-opus"


# ---------------------------------------------------------------------------
# Tool registration tests
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """Tests for verifying the tool registers correctly with FastMCP."""

    def test_register_ui_analyzer_tools_does_not_raise(self):
        """register_ui_analyzer_tools should not raise when called with a server."""
        from mcp.server.fastmcp import FastMCP

        from cotton_mcp_tools.tools.ui_analyzer import register_ui_analyzer_tools

        server = FastMCP(name="test-server")
        # Should not raise
        register_ui_analyzer_tools(server)

    def test_register_all_tools_includes_ui_analyzer(self):
        """register_all_tools should include the ui_analyzer registration."""
        from mcp.server.fastmcp import FastMCP

        from cotton_mcp_tools.tools import register_all_tools

        server = FastMCP(name="test-server")
        # Should not raise
        register_all_tools(server)


# ---------------------------------------------------------------------------
# Service construction tests
# ---------------------------------------------------------------------------


class TestServiceConstruction:
    """Tests for service instantiation."""

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key-123"})
    def test_openai_service_from_env(self):
        """OpenAIService should pick up OPENAI_API_KEY from env."""
        # Reset config singleton to pick up new env
        import cotton_mcp_tools.utils.config as cfg_mod
        cfg_mod._config = None

        from cotton_mcp_tools.services.openai_service import OpenAIService

        service = OpenAIService()
        assert service._api_key == "test-key-123"

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key-456"})
    def test_claude_service_from_env(self):
        """ClaudeService should pick up ANTHROPIC_API_KEY from env."""
        import cotton_mcp_tools.utils.config as cfg_mod
        cfg_mod._config = None

        from cotton_mcp_tools.services.claude_service import ClaudeService

        service = ClaudeService()
        assert service._api_key == "test-key-456"

    def test_openai_service_missing_key_raises(self):
        """OpenAIService should raise ValueError when no API key is set."""
        import cotton_mcp_tools.utils.config as cfg_mod
        cfg_mod._config = None

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            from cotton_mcp_tools.services.openai_service import OpenAIService

            with pytest.raises(ValueError, match="API key is required"):
                OpenAIService()

    def test_claude_service_missing_key_raises(self):
        """ClaudeService should raise ValueError when no API key is set."""
        import cotton_mcp_tools.utils.config as cfg_mod
        cfg_mod._config = None

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False):
            from cotton_mcp_tools.services.claude_service import ClaudeService

            with pytest.raises(ValueError, match="API key is required"):
                ClaudeService()


# ---------------------------------------------------------------------------
# Image content building tests
# ---------------------------------------------------------------------------


class TestOpenAIImageContent:
    """Tests for OpenAIService._build_image_content."""

    def test_http_url(self):
        """HTTP URLs should produce image_url blocks."""
        from cotton_mcp_tools.services.openai_service import OpenAIService

        result = OpenAIService._build_image_content("https://example.com/img.png")
        assert result["type"] == "image_url"
        assert result["image_url"]["url"] == "https://example.com/img.png"

    def test_data_uri_passthrough(self):
        """Data URIs should be passed through as-is."""
        from cotton_mcp_tools.services.openai_service import OpenAIService

        uri = "data:image/png;base64,abc123"
        result = OpenAIService._build_image_content(uri)
        assert result["image_url"]["url"] == uri

    def test_raw_base64_wrapped(self):
        """Raw base64 should be wrapped with a data URI prefix."""
        from cotton_mcp_tools.services.openai_service import OpenAIService

        result = OpenAIService._build_image_content("abc123")
        assert result["image_url"]["url"] == "data:image/png;base64,abc123"

    def test_empty_raises(self):
        """Empty string should raise ValueError."""
        from cotton_mcp_tools.services.openai_service import OpenAIService

        with pytest.raises(ValueError, match="must not be empty"):
            OpenAIService._build_image_content("")


class TestClaudeImageBlock:
    """Tests for ClaudeService._build_image_block."""

    def test_http_url(self):
        """HTTP URLs should produce URL-based source blocks."""
        from cotton_mcp_tools.services.claude_service import ClaudeService

        result = ClaudeService._build_image_block("https://example.com/img.png")
        assert result["type"] == "image"
        assert result["source"]["type"] == "url"
        assert result["source"]["url"] == "https://example.com/img.png"

    def test_data_uri_parsed(self):
        """Data URIs should be parsed into base64 source blocks."""
        from cotton_mcp_tools.services.claude_service import ClaudeService

        uri = "data:image/jpeg;base64,/9j/4AAQ"
        result = ClaudeService._build_image_block(uri)
        assert result["source"]["type"] == "base64"
        assert result["source"]["media_type"] == "image/jpeg"
        assert result["source"]["data"] == "/9j/4AAQ"

    def test_raw_base64(self):
        """Raw valid base64 should be wrapped with default png media type."""
        from cotton_mcp_tools.services.claude_service import ClaudeService

        valid_b64 = base64.b64encode(b"\x00" * 16).decode()
        result = ClaudeService._build_image_block(valid_b64)
        assert result["source"]["type"] == "base64"
        assert result["source"]["media_type"] == "image/png"

    def test_empty_raises(self):
        """Empty string should raise ValueError."""
        from cotton_mcp_tools.services.claude_service import ClaudeService

        with pytest.raises(ValueError, match="must not be empty"):
            ClaudeService._build_image_block("")

    def test_invalid_base64_raises(self):
        """Invalid base64 that is not a URL should raise ValueError."""
        from cotton_mcp_tools.services.claude_service import ClaudeService

        with pytest.raises(ValueError, match="neither a valid URL nor valid base64"):
            ClaudeService._build_image_block("not-valid!!!base64")


# ---------------------------------------------------------------------------
# analyze_ui tool function tests
# ---------------------------------------------------------------------------


class TestAnalyzeUi:
    """Tests for the analyze_ui MCP tool function."""

    @pytest.fixture()
    def tool_func(self):
        """Get the analyze_ui function by registering tools on a test server."""
        from mcp.server.fastmcp import FastMCP

        from cotton_mcp_tools.tools.ui_analyzer import register_ui_analyzer_tools

        server = FastMCP(name="test-server")
        register_ui_analyzer_tools(server)

        # Extract the registered tool function
        # FastMCP stores tools internally; we access via the tool manager
        tools = server._tool_manager._tools
        return tools["analyze_ui"].fn

    @pytest.mark.asyncio
    async def test_invalid_framework_returns_error(self, tool_func):
        """An unsupported framework should return an error string."""
        result = await tool_func(
            image="https://example.com/img.png",
            framework="angular",
        )
        assert "Error" in result
        assert "angular" in result

    @pytest.mark.asyncio
    async def test_framework_case_insensitive(self, tool_func, tmp_path):
        """Framework parameter should be case-insensitive."""
        # Create a valid image file
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        # Mock the service to avoid real API calls
        mock_service = AsyncMock()
        mock_service.analyze_image = AsyncMock(return_value="<html></html>")

        with patch.dict(
            "cotton_mcp_tools.tools.ui_analyzer.PROVIDER_MAP",
            {"openai": lambda: mock_service},
        ):
            result = await tool_func(
                image=str(png_file),
                framework="HTML",
            )

        assert result == "<html></html>"

    @pytest.mark.asyncio
    async def test_framework_whitespace_stripped(self, tool_func, tmp_path):
        """Framework parameter should have whitespace stripped."""
        # Create a valid image file
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        # Mock the service to avoid real API calls
        mock_service = AsyncMock()
        mock_service.analyze_image = AsyncMock(return_value="<html></html>")

        with patch.dict(
            "cotton_mcp_tools.tools.ui_analyzer.PROVIDER_MAP",
            {"openai": lambda: mock_service},
        ):
            result = await tool_func(
                image=str(png_file),
                framework="  html  ",
            )

        assert result == "<html></html>"

    @pytest.mark.asyncio
    async def test_empty_framework_returns_error(self, tool_func):
        """An empty framework should return an error string."""
        result = await tool_func(
            image="https://example.com/img.png",
            framework="",
        )
        assert "Error" in result
        assert "Unsupported framework" in result

    @pytest.mark.asyncio
    async def test_image_not_found_returns_error(self, tool_func):
        """A missing image file should return an error string."""
        result = await tool_func(
            image="/nonexistent/path/image.png",
            framework="html",
        )
        assert "Error" in result
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_unsupported_image_type_returns_error(self, tool_func, tmp_path):
        """An unsupported image type should return an error string."""
        txt_file = tmp_path / "file.txt"
        txt_file.write_text("not an image")

        result = await tool_func(
            image=str(txt_file),
            framework="html",
        )
        assert "Error" in result
        assert "Unsupported image type" in result

    @pytest.mark.asyncio
    async def test_image_too_large_returns_error(self, tool_func, tmp_path):
        """An image exceeding size limit should return an error string."""
        large_file = tmp_path / "huge.png"
        with large_file.open("wb") as f:
            f.seek(20 * 1024 * 1024)
            f.write(b"\x00")

        result = await tool_func(
            image=str(large_file),
            framework="html",
        )
        assert "Error" in result
        assert "too large" in result.lower()

    @pytest.mark.asyncio
    async def test_unknown_provider_returns_error(self, tool_func, tmp_path):
        """An unknown provider should return an error string."""
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        with patch(
            "cotton_mcp_tools.tools.ui_analyzer._resolve_provider",
            return_value=("unknown_provider", "some-model"),
        ):
            result = await tool_func(
                image=str(png_file),
                framework="html",
            )

        assert "Error" in result
        assert "unknown_provider" in result

    @pytest.mark.asyncio
    async def test_service_creation_failure_returns_error(self, tool_func, tmp_path):
        """A service creation ValueError should return an error string."""
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        def raise_value_error():
            raise ValueError("API key is required")

        with patch.dict(
            "cotton_mcp_tools.tools.ui_analyzer.PROVIDER_MAP",
            {"openai": raise_value_error},
        ):
            result = await tool_func(
                image=str(png_file),
                framework="html",
            )

        assert "Error" in result
        assert "API key" in result

    @pytest.mark.asyncio
    async def test_api_runtime_error_returns_error(self, tool_func, tmp_path):
        """A RuntimeError from the API should return an error string."""
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        mock_service = AsyncMock()
        mock_service.analyze_image = AsyncMock(
            side_effect=RuntimeError("Rate limit exceeded")
        )

        with patch.dict(
            "cotton_mcp_tools.tools.ui_analyzer.PROVIDER_MAP",
            {"openai": lambda: mock_service},
        ):
            result = await tool_func(
                image=str(png_file),
                framework="html",
            )

        assert "Error" in result
        assert "Rate limit exceeded" in result

    @pytest.mark.asyncio
    async def test_api_value_error_returns_error(self, tool_func, tmp_path):
        """A ValueError from the API should return an error string."""
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        mock_service = AsyncMock()
        mock_service.analyze_image = AsyncMock(
            side_effect=ValueError("Invalid image format")
        )

        with patch.dict(
            "cotton_mcp_tools.tools.ui_analyzer.PROVIDER_MAP",
            {"openai": lambda: mock_service},
        ):
            result = await tool_func(
                image=str(png_file),
                framework="html",
            )

        assert "Error" in result
        assert "Invalid image format" in result

    @pytest.mark.asyncio
    async def test_successful_html_analysis(self, tool_func, tmp_path):
        """A successful analysis should return the generated code."""
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        expected_code = "<!DOCTYPE html><html><body>Hello</body></html>"

        mock_service = AsyncMock()
        mock_service.analyze_image = AsyncMock(return_value=expected_code)

        with patch.dict(
            "cotton_mcp_tools.tools.ui_analyzer.PROVIDER_MAP",
            {"openai": lambda: mock_service},
        ):
            result = await tool_func(
                image=str(png_file),
                framework="html",
            )

        assert result == expected_code

    @pytest.mark.asyncio
    async def test_successful_react_analysis(self, tool_func, tmp_path):
        """A successful React analysis should return the generated component."""
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        expected_code = "export default function App() { return <div/>; }"

        mock_service = AsyncMock()
        mock_service.analyze_image = AsyncMock(return_value=expected_code)

        with patch.dict(
            "cotton_mcp_tools.tools.ui_analyzer.PROVIDER_MAP",
            {"openai": lambda: mock_service},
        ):
            result = await tool_func(
                image=str(png_file),
                framework="react",
            )

        assert result == expected_code

    @pytest.mark.asyncio
    async def test_successful_vue_analysis(self, tool_func, tmp_path):
        """A successful Vue analysis should return the generated SFC."""
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        expected_code = "<template><div/></template><script setup></script>"

        mock_service = AsyncMock()
        mock_service.analyze_image = AsyncMock(return_value=expected_code)

        with patch.dict(
            "cotton_mcp_tools.tools.ui_analyzer.PROVIDER_MAP",
            {"claude": lambda: mock_service},
        ):
            result = await tool_func(
                image=str(png_file),
                framework="vue",
                model="claude/claude-sonnet-4-20250514",
            )

        assert result == expected_code

    @pytest.mark.asyncio
    async def test_url_image_passed_to_service(self, tool_func):
        """A URL image should be passed through to the service as-is."""
        url = "https://example.com/screenshot.png"
        expected_code = "<html></html>"

        mock_service = AsyncMock()
        mock_service.analyze_image = AsyncMock(return_value=expected_code)

        with patch.dict(
            "cotton_mcp_tools.tools.ui_analyzer.PROVIDER_MAP",
            {"openai": lambda: mock_service},
        ):
            await tool_func(
                image=url,
                framework="html",
            )

        # Verify the URL was passed to the service (not base64-encoded)
        call_args = mock_service.analyze_image.call_args
        assert call_args.kwargs["image"] == url

    @pytest.mark.asyncio
    async def test_custom_prompt_included(self, tool_func, tmp_path):
        """A custom prompt should be included in the full prompt."""
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        custom_prompt = "Make it dark mode with rounded corners"

        mock_service = AsyncMock()
        mock_service.analyze_image = AsyncMock(return_value="<html></html>")

        with patch.dict(
            "cotton_mcp_tools.tools.ui_analyzer.PROVIDER_MAP",
            {"openai": lambda: mock_service},
        ):
            await tool_func(
                image=str(png_file),
                framework="html",
                prompt=custom_prompt,
            )

        # Verify the custom prompt is in the full prompt
        call_args = mock_service.analyze_image.call_args
        assert custom_prompt in call_args.kwargs["prompt"]

    @pytest.mark.asyncio
    async def test_provider_model_override_passed(self, tool_func, tmp_path):
        """A model override should be passed to the service."""
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        mock_service = AsyncMock()
        mock_service.analyze_image = AsyncMock(return_value="<html></html>")

        with patch.dict(
            "cotton_mcp_tools.tools.ui_analyzer.PROVIDER_MAP",
            {"openai": lambda: mock_service},
        ):
            await tool_func(
                image=str(png_file),
                framework="html",
                model="openai/gpt-4o-mini",
            )

        # Verify the model was passed to the service
        call_args = mock_service.analyze_image.call_args
        assert call_args.kwargs["model"] == "gpt-4o-mini"
