"""Tests for OCR MCP tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cotton_mcp_tools.services.ocr_service import OCRService, _resolve_provider
from cotton_mcp_tools.tools.ocr import register_ocr_tools


# --- Fixtures ---


@pytest.fixture
def mock_server():
    """Create a mock FastMCP server."""
    server = MagicMock()
    server.tool = lambda: lambda func: func
    return server


@pytest.fixture
def sample_ocr_result():
    """Sample OCR result."""
    return {
        "texts": [
            {
                "content": "你好世界",
                "confidence": "high",
                "type": "header",
            },
            {
                "content": "这是一段测试文字",
                "confidence": "high",
                "type": "body",
            },
        ],
        "full_text": "你好世界\n这是一段测试文字",
        "language": "zh",
        "has_text": True,
    }


# --- Test _resolve_provider ---


class TestResolveProvider:
    """Tests for _resolve_provider function."""

    def test_none_returns_default(self):
        """Test that None returns default provider."""
        with patch("cotton_mcp_tools.services.ocr_service.get_config") as mock_config:
            mock_config.return_value = MagicMock(
                default_provider="openai",
                default_model="gpt-4o",
            )
            provider, model = _resolve_provider(None)
            assert provider == "openai"
            assert model is None

    def test_slash_syntax_openai(self):
        """Test provider/model syntax with openai."""
        provider, model = _resolve_provider("openai/gpt-4o")
        assert provider == "openai"
        assert model == "gpt-4o"

    def test_slash_syntax_claude(self):
        """Test provider/model syntax with claude."""
        provider, model = _resolve_provider("claude/claude-3-opus")
        assert provider == "claude"
        assert model == "claude-3-opus"

    def test_gpt_model_infers_openai(self):
        """Test that gpt models infer openai provider."""
        provider, model = _resolve_provider("gpt-4o")
        assert provider == "openai"
        assert model == "gpt-4o"

    def test_claude_model_infers_claude(self):
        """Test that claude models infer claude provider."""
        provider, model = _resolve_provider("claude-3-opus")
        assert provider == "claude"
        assert model == "claude-3-opus"


# --- Test OCRService ---


class TestOCRService:
    """Tests for OCRService class."""

    def test_service_creation_openai(self):
        """Test creating OCR service with OpenAI provider."""
        with patch("cotton_mcp_tools.services.ocr_service._PROVIDER_MAP", {"openai": MagicMock()}):
            service = OCRService(provider="openai")
            assert service._provider_name == "openai"

    def test_service_creation_claude(self):
        """Test creating OCR service with Claude provider."""
        with patch("cotton_mcp_tools.services.ocr_service._PROVIDER_MAP", {"claude": MagicMock()}):
            service = OCRService(provider="claude")
            assert service._provider_name == "claude"

    def test_service_creation_invalid_provider(self):
        """Test creating OCR service with invalid provider raises ValueError."""
        with patch("cotton_mcp_tools.services.ocr_service._PROVIDER_MAP", {"openai": MagicMock()}):
            with pytest.raises(ValueError, match="Unknown provider"):
                OCRService(provider="invalid")

    @pytest.mark.asyncio
    async def test_recognize_text(self, sample_ocr_result):
        """Test recognizing text from an image."""
        mock_service = MagicMock()
        mock_service.analyze_image = AsyncMock(
            return_value=json.dumps(sample_ocr_result)
        )

        with patch("cotton_mcp_tools.services.ocr_service._PROVIDER_MAP", {"openai": MagicMock(return_value=mock_service)}):
            service = OCRService(provider="openai")
            result = await service.recognize_text("https://example.com/image.jpg")

            assert result["has_text"] is True
            assert len(result["texts"]) == 2
            assert "你好世界" in result["full_text"]

    @pytest.mark.asyncio
    async def test_recognize_text_with_raw_response(self):
        """Test recognizing text when response is not JSON."""
        mock_service = MagicMock()
        mock_service.analyze_image = AsyncMock(
            return_value="This is raw text from image"
        )

        with patch("cotton_mcp_tools.services.ocr_service._PROVIDER_MAP", {"openai": MagicMock(return_value=mock_service)}):
            service = OCRService(provider="openai")
            result = await service.recognize_text("https://example.com/image.jpg")

            assert result["has_text"] is True
            assert result["full_text"] == "This is raw text from image"

    @pytest.mark.asyncio
    async def test_recognize_text_from_multiple(self, sample_ocr_result):
        """Test recognizing text from multiple images."""
        mock_service = MagicMock()
        mock_service.analyze_image = AsyncMock(
            return_value=json.dumps(sample_ocr_result)
        )

        with patch("cotton_mcp_tools.services.ocr_service._PROVIDER_MAP", {"openai": MagicMock(return_value=mock_service)}):
            service = OCRService(provider="openai")
            images = [
                "https://example.com/img1.jpg",
                "https://example.com/img2.jpg",
            ]
            results = await service.recognize_text_from_multiple(images)

            assert len(results) == 2
            assert all(r["has_text"] for r in results)

    @pytest.mark.asyncio
    async def test_recognize_text_from_multiple_with_error(self):
        """Test batch OCR with one image failing."""
        mock_service = MagicMock()
        mock_service.analyze_image = AsyncMock(
            side_effect=[RuntimeError("API error"), "Success"]
        )

        with patch("cotton_mcp_tools.services.ocr_service._PROVIDER_MAP", {"openai": MagicMock(return_value=mock_service)}):
            service = OCRService(provider="openai")
            images = [
                "https://example.com/img1.jpg",
                "https://example.com/img2.jpg",
            ]
            results = await service.recognize_text_from_multiple(images)

            assert len(results) == 2
            assert results[0]["has_text"] is False
            assert "error" in results[0]


# --- Test Tool Registration ---


class TestToolRegistration:
    """Tests for tool registration."""

    def test_register_ocr_tools(self, mock_server):
        """Test that OCR tools register without errors."""
        register_ocr_tools(mock_server)


# --- Test OCR Tool Functions ---


class TestOCRToolFunctions:
    """Tests for OCR tool functions."""

    @pytest.mark.asyncio
    async def test_ocr_recognize_text_success(self, sample_ocr_result):
        """Test successful OCR recognition."""
        with patch("cotton_mcp_tools.tools.ocr.OCRService") as mock_ocr_cls:
            mock_service = MagicMock()
            mock_service.recognize_text = AsyncMock(return_value=sample_ocr_result)
            mock_ocr_cls.return_value = mock_service

            from cotton_mcp_tools.tools.ocr import register_ocr_tools

            captured = {}
            server = MagicMock()

            def capture_tool():
                def decorator(func):
                    captured[func.__name__] = func
                    return func
                return decorator

            server.tool = capture_tool
            register_ocr_tools(server)

            result = await captured["ocr_recognize_text"](
                "https://example.com/image.jpg"
            )
            parsed = json.loads(result)
            assert parsed["has_text"] is True

    @pytest.mark.asyncio
    async def test_ocr_recognize_text_file_not_found(self):
        """Test OCR with non-existent file."""
        from cotton_mcp_tools.tools.ocr import register_ocr_tools

        captured = {}
        server = MagicMock()

        def capture_tool():
            def decorator(func):
                captured[func.__name__] = func
                return func
            return decorator

        server.tool = capture_tool
        register_ocr_tools(server)

        result = await captured["ocr_recognize_text"]("/nonexistent/image.jpg")
        parsed = json.loads(result)
        assert "error" in parsed
        assert parsed["has_text"] is False

    @pytest.mark.asyncio
    async def test_ocr_recognize_batch_success(self, sample_ocr_result):
        """Test batch OCR recognition."""
        with patch("cotton_mcp_tools.tools.ocr.OCRService") as mock_ocr_cls:
            mock_service = MagicMock()
            mock_service.recognize_text = AsyncMock(return_value=sample_ocr_result)
            mock_ocr_cls.return_value = mock_service

            from cotton_mcp_tools.tools.ocr import register_ocr_tools

            captured = {}
            server = MagicMock()

            def capture_tool():
                def decorator(func):
                    captured[func.__name__] = func
                    return func
                return decorator

            server.tool = capture_tool
            register_ocr_tools(server)

            images = [
                "https://example.com/img1.jpg",
                "https://example.com/img2.jpg",
            ]
            result = await captured["ocr_recognize_batch"](images)
            parsed = json.loads(result)
            assert parsed["total"] == 2


# --- Test XHS OCR Integration ---


class TestXHSOCRIntegration:
    """Tests for XHS OCR integration."""

    @pytest.mark.asyncio
    async def test_xhs_analyze_note_with_ocr(self, sample_ocr_result):
        """Test XHS note analysis with OCR."""
        with patch("cotton_mcp_tools.tools.xiaohongshu._create_service") as mock_xhs:
            mock_xhs_service = MagicMock()
            mock_xhs_service.get_note_detail = AsyncMock(return_value={
                "note_id": "test_123",
                "title": "Test Note",
                "desc": "Test description",
                "type": "normal",
                "user": {"user_id": "user_1", "nickname": "TestUser"},
                "image_list": [
                    {"url_default": "https://example.com/img1.jpg"},
                    {"url_default": "https://example.com/img2.jpg"},
                ],
                "tag_list": [{"name": "test", "type": "topic"}],
                "interact_info": {
                    "liked_count": 100,
                    "collected_count": 50,
                    "comment_count": 20,
                    "share_count": 10,
                },
                "time": 1700000000,
                "last_update_time": 1700001000,
            })
            mock_xhs.return_value = mock_xhs_service

            with patch("cotton_mcp_tools.tools.xiaohongshu.OCRService") as mock_ocr_cls:
                mock_ocr_service = MagicMock()
                mock_ocr_service.recognize_text = AsyncMock(return_value=sample_ocr_result)
                mock_ocr_cls.return_value = mock_ocr_service

                from cotton_mcp_tools.tools.xiaohongshu import register_xiaohongshu_tools

                captured = {}
                server = MagicMock()

                def capture_tool():
                    def decorator(func):
                        captured[func.__name__] = func
                        return func
                    return decorator

                server.tool = capture_tool
                register_xiaohongshu_tools(server)

                result = await captured["xhs_analyze_note_with_ocr"]("test_123")
                parsed = json.loads(result)

                assert "note" in parsed
                assert "ocr_analysis" in parsed
                assert "summary" in parsed
                assert parsed["note"]["note_id"] == "test_123"
                assert parsed["ocr_analysis"]["total_images"] == 2
                assert parsed["ocr_analysis"]["analyzed_images"] == 2

    @pytest.mark.asyncio
    async def test_xhs_analyze_note_not_found(self):
        """Test XHS note analysis when note not found."""
        with patch("cotton_mcp_tools.tools.xiaohongshu._create_service") as mock_xhs:
            mock_xhs_service = MagicMock()
            mock_xhs_service.get_note_detail = AsyncMock(return_value={})
            mock_xhs.return_value = mock_xhs_service

            from cotton_mcp_tools.tools.xiaohongshu import register_xiaohongshu_tools

            captured = {}
            server = MagicMock()

            def capture_tool():
                def decorator(func):
                    captured[func.__name__] = func
                    return func
                return decorator

            server.tool = capture_tool
            register_xiaohongshu_tools(server)

            result = await captured["xhs_analyze_note_with_ocr"]("nonexistent")
            parsed = json.loads(result)
            assert "error" in parsed
