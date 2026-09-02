"""Tests for Xiaohongshu MCP tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cotton_mcp_tools.services.xhs_service import (
    DataFetchError,
    IPBlockError,
    NoteNotFoundError,
    PlatformAccessError,
    XiaoHongShuService,
    XHSError,
    format_comment_data,
    format_note_data,
)
from cotton_mcp_tools.tools.xiaohongshu import register_xiaohongshu_tools


# --- Fixtures ---


@pytest.fixture
def mock_server():
    """Create a mock FastMCP server."""
    server = MagicMock()
    server.tool = lambda: lambda func: func
    return server


@pytest.fixture
def sample_note():
    """Sample note data from XHS API."""
    return {
        "note_id": "test_note_123",
        "title": "Test Note Title",
        "desc": "This is a test note description",
        "type": "normal",
        "user": {
            "user_id": "user_123",
            "nickname": "TestUser",
        },
        "image_list": [
            {"url_default": "https://example.com/img1.jpg", "url": ""},
            {"url_default": "https://example.com/img2.jpg", "url": ""},
        ],
        "video": None,
        "tag_list": [
            {"name": "test", "type": "topic"},
            {"name": "note", "type": "topic"},
            {"name": "other", "type": "other"},
        ],
        "interact_info": {
            "liked_count": 100,
            "collected_count": 50,
            "comment_count": 20,
            "share_count": 10,
        },
        "time": 1700000000,
        "last_update_time": 1700001000,
    }


@pytest.fixture
def sample_video_note():
    """Sample video note data from XHS API."""
    return {
        "note_id": "video_note_456",
        "title": "Test Video Title",
        "desc": "This is a test video description",
        "type": "video",
        "user": {
            "user_id": "user_456",
            "nickname": "VideoUser",
        },
        "image_list": [],
        "video": {
            "consumer": {
                "origin_video_key": "video_key_123",
            },
        },
        "tag_list": [],
        "interact_info": {
            "liked_count": 200,
            "collected_count": 100,
            "comment_count": 50,
            "share_count": 30,
        },
        "time": 1700002000,
        "last_update_time": 1700003000,
    }


@pytest.fixture
def sample_comment():
    """Sample comment data from XHS API."""
    return {
        "id": "comment_789",
        "content": "This is a test comment",
        "user_info": {
            "user_id": "commenter_123",
            "nickname": "Commenter",
        },
        "create_time": 1700004000,
        "like_count": 5,
        "sub_comment_count": 2,
        "target_comment": {"id": ""},
        "pictures": [
            {"url_default": "https://example.com/pic1.jpg"},
        ],
    }


# --- Test format_note_data ---


class TestFormatNoteData:
    """Tests for format_note_data function."""

    def test_format_normal_note(self, sample_note):
        """Test formatting a normal note."""
        result = format_note_data(sample_note)

        assert result["note_id"] == "test_note_123"
        assert result["title"] == "Test Note Title"
        assert result["desc"] == "This is a test note description"
        assert result["type"] == "normal"
        assert result["user"]["user_id"] == "user_123"
        assert result["user"]["nickname"] == "TestUser"
        assert len(result["image_list"]) == 2
        assert result["video_url"] == ""
        assert result["tag_list"] == ["test", "note"]
        assert result["liked_count"] == 100
        assert result["collected_count"] == 50
        assert result["comment_count"] == 20
        assert result["share_count"] == 10
        assert result["time"] == 1700000000
        assert result["last_update_time"] == 1700001000
        assert "test_note_123" in result["note_url"]

    def test_format_video_note(self, sample_video_note):
        """Test formatting a video note."""
        result = format_note_data(sample_video_note)

        assert result["note_id"] == "video_note_456"
        assert result["type"] == "video"
        assert "video_key_123" in result["video_url"]
        assert result["image_list"] == []

    def test_format_note_with_empty_fields(self):
        """Test formatting a note with empty fields."""
        note = {"note_id": "empty_note"}
        result = format_note_data(note)

        assert result["note_id"] == "empty_note"
        assert result["title"] == ""
        assert result["desc"] == ""
        assert result["type"] == "normal"
        assert result["user"]["user_id"] == ""
        assert result["image_list"] == []
        assert result["video_url"] == ""
        assert result["tag_list"] == []
        assert result["liked_count"] == 0


# --- Test format_comment_data ---


class TestFormatCommentData:
    """Tests for format_comment_data function."""

    def test_format_comment(self, sample_comment):
        """Test formatting a comment."""
        result = format_comment_data(sample_comment)

        assert result["comment_id"] == "comment_789"
        assert result["content"] == "This is a test comment"
        assert result["user"]["user_id"] == "commenter_123"
        assert result["user"]["nickname"] == "Commenter"
        assert result["create_time"] == 1700004000
        assert result["like_count"] == 5
        assert result["sub_comment_count"] == 2
        assert result["parent_comment_id"] == ""
        assert len(result["pictures"]) == 1

    def test_format_comment_with_empty_fields(self):
        """Test formatting a comment with empty fields."""
        comment = {"id": "empty_comment"}
        result = format_comment_data(comment)

        assert result["comment_id"] == "empty_comment"
        assert result["content"] == ""
        assert result["user"]["user_id"] == ""
        assert result["like_count"] == 0


# --- Test XiaoHongShuService ---


class TestXiaoHongShuService:
    """Tests for XiaoHongShuService class."""

    def test_service_creation_with_cookie(self):
        """Test creating service with explicit cookie."""
        with patch("cotton_mcp_tools.services.xhs_service.get_config") as mock_config:
            mock_config.return_value = MagicMock(xhs_cookie="", xhs_proxy="")
            service = XiaoHongShuService(cookie="test_cookie")
            assert service._cookie == "test_cookie"

    def test_service_creation_from_config(self):
        """Test creating service from config."""
        with patch("cotton_mcp_tools.services.xhs_service.get_config") as mock_config:
            mock_config.return_value = MagicMock(
                xhs_cookie="config_cookie",
                xhs_proxy="http://proxy:8080",
            )
            service = XiaoHongShuService()
            assert service._cookie == "config_cookie"
            assert service._proxy == "http://proxy:8080"

    def test_service_creation_without_cookie_raises(self):
        """Test that creating service without cookie raises ValueError."""
        with patch("cotton_mcp_tools.services.xhs_service.get_config") as mock_config:
            mock_config.return_value = MagicMock(xhs_cookie="", xhs_proxy="")
            with pytest.raises(ValueError, match="XHS cookie is required"):
                XiaoHongShuService()

    def test_build_headers(self):
        """Test building request headers."""
        with patch("cotton_mcp_tools.services.xhs_service.get_config") as mock_config:
            mock_config.return_value = MagicMock(xhs_cookie="", xhs_proxy="")
            service = XiaoHongShuService(cookie="test_cookie")
            headers = service._build_headers()

            assert headers["Cookie"] == "test_cookie"
            assert "User-Agent" in headers
            assert headers["Origin"] == "https://www.xiaohongshu.com"

    def test_build_query_string(self):
        """Test building query string."""
        with patch("cotton_mcp_tools.services.xhs_service.get_config") as mock_config:
            mock_config.return_value = MagicMock(xhs_cookie="", xhs_proxy="")
            service = XiaoHongShuService(cookie="test_cookie")

            params = {"key1": "value1", "key2": "value2"}
            result = service._build_query_string(params)
            assert "key1=value1" in result
            assert "key2=value2" in result
            assert "&" in result

    @pytest.mark.asyncio
    async def test_search_notes(self, sample_note):
        """Test searching notes."""
        with patch("cotton_mcp_tools.services.xhs_service.get_config") as mock_config:
            mock_config.return_value = MagicMock(xhs_cookie="", xhs_proxy="")
            service = XiaoHongShuService(cookie="test_cookie")

            mock_response = {
                "success": True,
                "data": {
                    "items": [
                        {"id": "note_1", "note_card": sample_note},
                    ],
                },
            }

            with patch.object(service, "_request", return_value=mock_response["data"]):
                result = await service.search_notes("test keyword")
                assert "items" in result
                assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_note_detail(self, sample_note):
        """Test getting note detail."""
        with patch("cotton_mcp_tools.services.xhs_service.get_config") as mock_config:
            mock_config.return_value = MagicMock(xhs_cookie="", xhs_proxy="")
            service = XiaoHongShuService(cookie="test_cookie")

            mock_response = {
                "items": [{"note_card": sample_note}],
            }

            with patch.object(service, "_request", return_value=mock_response):
                result = await service.get_note_detail("test_note_123")
                assert result["note_id"] == "test_note_123"

    @pytest.mark.asyncio
    async def test_get_note_comments(self, sample_comment):
        """Test getting note comments."""
        with patch("cotton_mcp_tools.services.xhs_service.get_config") as mock_config:
            mock_config.return_value = MagicMock(xhs_cookie="", xhs_proxy="")
            service = XiaoHongShuService(cookie="test_cookie")

            mock_response = {
                "comments": [sample_comment],
                "has_more": False,
                "cursor": "",
            }

            with patch.object(service, "_request", return_value=mock_response):
                result = await service.get_note_comments("test_note_123")
                assert "comments" in result
                assert len(result["comments"]) == 1

    @pytest.mark.asyncio
    async def test_get_creator_notes(self, sample_note):
        """Test getting creator notes."""
        with patch("cotton_mcp_tools.services.xhs_service.get_config") as mock_config:
            mock_config.return_value = MagicMock(xhs_cookie="", xhs_proxy="")
            service = XiaoHongShuService(cookie="test_cookie")

            mock_response = {
                "notes": [sample_note],
                "has_more": False,
                "cursor": "",
            }

            with patch.object(service, "_request", return_value=mock_response):
                result = await service.get_creator_notes("user_123")
                assert "notes" in result
                assert len(result["notes"]) == 1


# --- Test Tool Registration ---


class TestToolRegistration:
    """Tests for tool registration."""

    def test_register_xiaohongshu_tools(self, mock_server):
        """Test that tools register without errors."""
        register_xiaohongshu_tools(mock_server)


# --- Test Error Handling ---


class TestErrorHandling:
    """Tests for error handling in tools."""

    def test_search_notes_with_invalid_sort(self, mock_server):
        """Test search with invalid sort type."""
        # Capture the registered tool function
        captured_tools = {}
        original_tool = mock_server.tool

        def capture_tool():
            def decorator(func):
                captured_tools[func.__name__] = func
                return func
            return decorator

        mock_server.tool = capture_tool
        register_xiaohongshu_tools(mock_server)
        mock_server.tool = original_tool

        # Get the tool function and call it
        import asyncio
        search_fn = captured_tools.get("xhs_search_notes")
        assert search_fn is not None
        result = asyncio.run(search_fn("test", sort="invalid"))
        assert "Error" in result
        assert "Invalid sort type" in result

    def test_search_notes_with_invalid_note_type(self, mock_server):
        """Test search with invalid note type."""
        captured_tools = {}
        original_tool = mock_server.tool

        def capture_tool():
            def decorator(func):
                captured_tools[func.__name__] = func
                return func
            return decorator

        mock_server.tool = capture_tool
        register_xiaohongshu_tools(mock_server)
        mock_server.tool = original_tool

        import asyncio
        search_fn = captured_tools.get("xhs_search_notes")
        result = asyncio.run(search_fn("test", note_type="invalid"))
        assert "Error" in result
        assert "Invalid note type" in result

    def test_search_notes_without_cookie(self, mock_server):
        """Test search without cookie configured."""
        captured_tools = {}
        original_tool = mock_server.tool

        def capture_tool():
            def decorator(func):
                captured_tools[func.__name__] = func
                return func
            return decorator

        mock_server.tool = capture_tool

        with patch("cotton_mcp_tools.tools.xiaohongshu._create_service") as mock_create:
            mock_create.side_effect = ValueError("XHS cookie is required")
            register_xiaohongshu_tools(mock_server)
            mock_server.tool = original_tool

            import asyncio
            search_fn = captured_tools.get("xhs_search_notes")
            result = asyncio.run(search_fn("test"))
            assert "Error" in result
            assert "XHS cookie is required" in result

    def test_search_notes_with_api_error(self, mock_server):
        """Test search with API error."""
        captured_tools = {}
        original_tool = mock_server.tool

        def capture_tool():
            def decorator(func):
                captured_tools[func.__name__] = func
                return func
            return decorator

        mock_server.tool = capture_tool

        with patch("cotton_mcp_tools.tools.xiaohongshu._create_service") as mock_create:
            mock_service = MagicMock()
            mock_service.search_notes = AsyncMock(side_effect=DataFetchError("API error"))
            mock_create.return_value = mock_service
            register_xiaohongshu_tools(mock_server)
            mock_server.tool = original_tool

            import asyncio
            search_fn = captured_tools.get("xhs_search_notes")
            result = asyncio.run(search_fn("test"))
            assert "Error" in result
            assert "API error" in result

    def test_get_note_detail_not_found(self, mock_server):
        """Test getting detail for non-existent note."""
        captured_tools = {}
        original_tool = mock_server.tool

        def capture_tool():
            def decorator(func):
                captured_tools[func.__name__] = func
                return func
            return decorator

        mock_server.tool = capture_tool

        with patch("cotton_mcp_tools.tools.xiaohongshu._create_service") as mock_create:
            mock_service = MagicMock()
            mock_service.get_note_detail = AsyncMock(return_value={})
            mock_create.return_value = mock_service
            register_xiaohongshu_tools(mock_server)
            mock_server.tool = original_tool

            import asyncio
            detail_fn = captured_tools.get("xhs_get_note_detail")
            result = asyncio.run(detail_fn("nonexistent"))
            assert "Error" in result
            assert "not found" in result


# --- Test Integration ---


class TestIntegration:
    """Integration tests for the complete flow."""

    @pytest.mark.asyncio
    async def test_search_and_format_flow(self, sample_note):
        """Test complete search and format flow."""
        with patch("cotton_mcp_tools.services.xhs_service.get_config") as mock_config:
            mock_config.return_value = MagicMock(xhs_cookie="", xhs_proxy="")
            service = XiaoHongShuService(cookie="test_cookie")

            mock_response = {
                "items": [
                    {"id": "note_1", "note_card": sample_note},
                ],
            }

            with patch.object(service, "_request", return_value=mock_response):
                result = await service.search_notes("test")
                items = result.get("items", [])
                assert len(items) == 1

                note_card = items[0].get("note_card", {})
                formatted = format_note_data(note_card)
                assert formatted["note_id"] == "test_note_123"
                assert formatted["liked_count"] == 100
