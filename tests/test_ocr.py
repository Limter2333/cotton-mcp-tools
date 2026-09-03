"""Tests for OCR MCP tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cotton_mcp_tools.services.ocr_service import (
    EasyOCRBackend,
    LLMOCRBackend,
    OCRService,
    PaddleOCRBackend,
    _resolve_provider,
    get_available_backends,
)
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
                "confidence": 0.95,
                "type": "header",
                "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]],
            },
            {
                "content": "这是一段测试文字",
                "confidence": 0.92,
                "type": "body",
                "bbox": [[10, 40], [200, 40], [200, 60], [10, 60]],
            },
        ],
        "full_text": "你好世界\n这是一段测试文字",
        "language": "zh",
        "has_text": True,
        "backend": "paddleocr",
    }


@pytest.fixture
def sample_paddleocr_raw():
    """Sample raw PaddleOCR output."""
    return [
        [
            [[[10, 10], [100, 10], [100, 30], [10, 30]], ("你好世界", 0.95)],
            [[[10, 40], [200, 40], [200, 60], [10, 60]], ("这是一段测试文字", 0.92)],
        ]
    ]


@pytest.fixture
def sample_easyocr_raw():
    """Sample raw EasyOCR output."""
    return [
        ([[10, 10], [100, 10], [100, 30], [10, 30]], "你好世界", 0.95),
        ([[10, 40], [200, 40], [200, 60], [10, 60]], "这是一段测试文字", 0.92),
    ]


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


# --- Test get_available_backends ---


class TestGetAvailableBackends:
    """Tests for get_available_backends function."""

    def test_llm_always_available(self):
        """Test that LLM backend is always available."""
        backends = get_available_backends()
        assert "llm" in backends

    def test_paddleocr_availability(self):
        """Test PaddleOCR availability detection."""
        with patch.dict("sys.modules", {"paddleocr": MagicMock()}):
            backends = get_available_backends()
            assert "paddleocr" in backends

    def test_easyocr_availability(self):
        """Test EasyOCR availability detection."""
        with patch.dict("sys.modules", {"easyocr": MagicMock()}):
            backends = get_available_backends()
            assert "easyocr" in backends


# --- Test PaddleOCRBackend ---


class TestPaddleOCRBackend:
    """Tests for PaddleOCRBackend class."""

    @pytest.mark.asyncio
    async def test_recognize_success(self, sample_paddleocr_raw):
        """Test successful PaddleOCR recognition."""
        with patch("cotton_mcp_tools.services.ocr_service._load_image_bytes") as mock_load:
            mock_load.return_value = b"fake image bytes"

            backend = PaddleOCRBackend(languages="ch")
            backend._ocr = MagicMock()
            backend._ocr.ocr.return_value = sample_paddleocr_raw

            result = await backend.recognize("https://example.com/image.jpg")

            assert result["has_text"] is True
            assert len(result["texts"]) == 2
            assert result["backend"] == "paddleocr"
            assert "你好世界" in result["full_text"]

    @pytest.mark.asyncio
    async def test_recognize_empty_image(self):
        """Test PaddleOCR with empty/no text image."""
        with patch("cotton_mcp_tools.services.ocr_service._load_image_bytes") as mock_load:
            mock_load.return_value = b"fake image bytes"

            backend = PaddleOCRBackend(languages="ch")
            backend._ocr = MagicMock()
            backend._ocr.ocr.return_value = [[]]

            result = await backend.recognize("https://example.com/image.jpg")

            assert result["has_text"] is False
            assert len(result["texts"]) == 0

    def test_import_error(self):
        """Test ImportError when PaddleOCR not installed."""
        backend = PaddleOCRBackend()
        backend._ocr = None

        with patch.dict("sys.modules", {"paddleocr": None}):
            with pytest.raises(RuntimeError, match="PaddleOCR is not installed"):
                backend._get_ocr()


# --- Test EasyOCRBackend ---


class TestEasyOCRBackend:
    """Tests for EasyOCRBackend class."""

    @pytest.mark.asyncio
    async def test_recognize_success(self, sample_easyocr_raw):
        """Test successful EasyOCR recognition."""
        with patch("cotton_mcp_tools.services.ocr_service._load_image_bytes") as mock_load:
            mock_load.return_value = b"fake image bytes"

            backend = EasyOCRBackend(languages="ch,en")
            backend._reader = MagicMock()
            backend._reader.readtext.return_value = sample_easyocr_raw

            result = await backend.recognize("https://example.com/image.jpg")

            assert result["has_text"] is True
            assert len(result["texts"]) == 2
            assert result["backend"] == "easyocr"

    def test_import_error(self):
        """Test ImportError when EasyOCR not installed."""
        backend = EasyOCRBackend()
        backend._reader = None

        with patch.dict("sys.modules", {"easyocr": None}):
            with pytest.raises(RuntimeError, match="EasyOCR is not installed"):
                backend._get_reader()


# --- Test LLMOCRBackend ---


class TestLLMOCRBackend:
    """Tests for LLMOCRBackend class."""

    @pytest.mark.asyncio
    async def test_recognize_success(self, sample_ocr_result):
        """Test successful LLM OCR recognition."""
        mock_service = MagicMock()
        mock_service.analyze_image = AsyncMock(
            return_value=json.dumps(sample_ocr_result)
        )

        with patch("cotton_mcp_tools.services.ocr_service._PROVIDER_MAP", {"openai": MagicMock(return_value=mock_service)}):
            backend = LLMOCRBackend("openai")
            backend._service = mock_service

            result = await backend.recognize("https://example.com/image.jpg")

            assert result["has_text"] is True
            assert result["backend"] == "llm"

    @pytest.mark.asyncio
    async def test_recognize_with_raw_response(self):
        """Test LLM OCR with non-JSON response."""
        mock_service = MagicMock()
        mock_service.analyze_image = AsyncMock(return_value="Raw text response")

        with patch("cotton_mcp_tools.services.ocr_service._PROVIDER_MAP", {"openai": MagicMock(return_value=mock_service)}):
            backend = LLMOCRBackend("openai")
            backend._service = mock_service

            result = await backend.recognize("https://example.com/image.jpg")

            assert result["has_text"] is True
            assert result["full_text"] == "Raw text response"
            assert result["backend"] == "llm"

    def test_invalid_provider(self):
        """Test invalid provider raises ValueError."""
        with patch("cotton_mcp_tools.services.ocr_service._PROVIDER_MAP", {"openai": MagicMock()}):
            with pytest.raises(ValueError, match="Unknown provider"):
                LLMOCRBackend("invalid")


# --- Test OCRService ---


class TestOCRService:
    """Tests for OCRService class."""

    def test_service_creation_llm_backend(self):
        """Test creating OCR service with LLM backend."""
        with patch("cotton_mcp_tools.services.ocr_service._PROVIDER_MAP", {"openai": MagicMock()}):
            service = OCRService(backend="llm", provider="openai")
            assert service.backend_name == "llm"

    def test_service_creation_paddleocr_backend(self):
        """Test creating OCR service with PaddleOCR backend."""
        service = OCRService(backend="paddleocr")
        assert service.backend_name == "paddleocr"

    def test_service_creation_easyocr_backend(self):
        """Test creating OCR service with EasyOCR backend."""
        service = OCRService(backend="easyocr")
        assert service.backend_name == "easyocr"

    def test_service_creation_invalid_backend(self):
        """Test creating OCR service with invalid backend raises ValueError."""
        with pytest.raises(ValueError, match="Unknown OCR backend"):
            OCRService(backend="invalid")

    def test_service_creation_from_config(self):
        """Test creating OCR service from config."""
        with patch("cotton_mcp_tools.services.ocr_service.get_config") as mock_config:
            mock_config.return_value = MagicMock(
                ocr_backend="paddleocr",
                ocr_languages="ch,en",
                default_provider="openai",
            )
            service = OCRService()
            assert service.backend_name == "paddleocr"

    @pytest.mark.asyncio
    async def test_recognize_text(self, sample_ocr_result):
        """Test recognizing text from an image."""
        mock_service = MagicMock()
        mock_service.analyze_image = AsyncMock(
            return_value=json.dumps(sample_ocr_result)
        )

        with patch("cotton_mcp_tools.services.ocr_service._PROVIDER_MAP", {"openai": MagicMock(return_value=mock_service)}):
            service = OCRService(backend="llm", provider="openai")
            result = await service.recognize_text("https://example.com/image.jpg")

            assert result["has_text"] is True
            assert len(result["texts"]) == 2

    @pytest.mark.asyncio
    async def test_recognize_text_from_multiple(self, sample_ocr_result):
        """Test recognizing text from multiple images."""
        mock_service = MagicMock()
        mock_service.analyze_image = AsyncMock(
            return_value=json.dumps(sample_ocr_result)
        )

        with patch("cotton_mcp_tools.services.ocr_service._PROVIDER_MAP", {"openai": MagicMock(return_value=mock_service)}):
            service = OCRService(backend="llm", provider="openai")
            images = [
                "https://example.com/img1.jpg",
                "https://example.com/img2.jpg",
            ]
            results = await service.recognize_text_from_multiple(images)

            assert len(results) == 2
            assert all(r["has_text"] for r in results)

    @pytest.mark.asyncio
    async def test_detect_text_regions(self, sample_ocr_result):
        """Test detecting text regions."""
        mock_service = MagicMock()
        mock_service.analyze_image = AsyncMock(
            return_value=json.dumps(sample_ocr_result)
        )

        with patch("cotton_mcp_tools.services.ocr_service._PROVIDER_MAP", {"openai": MagicMock(return_value=mock_service)}):
            service = OCRService(backend="llm", provider="openai")
            # Override backend for region detection
            service._backend_name = "paddleocr"
            service._backend = MagicMock()
            service._backend.recognize = AsyncMock(return_value=sample_ocr_result)

            result = await service.detect_text_regions("https://example.com/image.jpg")

            assert "regions" in result


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
                "https://example.com/image.jpg",
                backend="llm",
            )
            parsed = json.loads(result)
            assert parsed["has_text"] is True

    @pytest.mark.asyncio
    async def test_ocr_recognize_text_invalid_backend(self):
        """Test OCR with invalid backend."""
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
            "https://example.com/image.jpg",
            backend="invalid",
        )
        parsed = json.loads(result)
        assert "error" in parsed
        assert "Invalid backend" in parsed["error"]

    @pytest.mark.asyncio
    async def test_ocr_recognize_text_unavailable_backend(self):
        """Test OCR with unavailable backend."""
        with patch("cotton_mcp_tools.tools.ocr.get_available_backends", return_value=["llm"]):
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
                "https://example.com/image.jpg",
                backend="paddleocr",
            )
            parsed = json.loads(result)
            assert "error" in parsed
            assert "not installed" in parsed["error"]

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
            result = await captured["ocr_recognize_batch"](images, backend="llm")
            parsed = json.loads(result)
            assert parsed["total"] == 2
            assert parsed["backend"] == "llm"

    @pytest.mark.asyncio
    async def test_ocr_detect_text_regions(self, sample_ocr_result):
        """Test text region detection."""
        with patch("cotton_mcp_tools.tools.ocr.OCRService") as mock_ocr_cls:
            mock_service = MagicMock()
            mock_service.detect_text_regions = AsyncMock(return_value={
                "regions": [{"bbox": [[10, 10], [100, 10], [100, 30], [10, 30]], "confidence": 0.95}],
                "total_regions": 1,
            })
            mock_ocr_cls.return_value = mock_service

            with patch("cotton_mcp_tools.tools.ocr.get_available_backends", return_value=["llm", "paddleocr"]):
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

                result = await captured["ocr_detect_text_regions"](
                    "https://example.com/image.jpg",
                    backend="paddleocr",
                )
                parsed = json.loads(result)
                assert "regions" in parsed
                assert parsed["total_regions"] == 1

    @pytest.mark.asyncio
    async def test_ocr_detect_text_regions_llm_not_supported(self):
        """Test that region detection rejects LLM backend."""
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

        result = await captured["ocr_detect_text_regions"](
            "https://example.com/image.jpg",
            backend="llm",
        )
        parsed = json.loads(result)
        assert "error" in parsed
        assert "requires" in parsed["error"]

    @pytest.mark.asyncio
    async def test_ocr_list_backends(self):
        """Test listing available backends."""
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

        result = await captured["ocr_list_backends"]()
        parsed = json.loads(result)
        assert "backends" in parsed
        assert parsed["total"] == 3
        # LLM should always be available
        llm_backend = next(b for b in parsed["backends"] if b["name"] == "llm")
        assert llm_backend["available"] is True


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
