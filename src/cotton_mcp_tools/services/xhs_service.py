"""Xiaohongshu (XHS) API client service.

Provides methods to interact with Xiaohongshu's backend APIs for
searching notes, fetching note details, comments, and creator information.
Uses xhshow library for request signing.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

from cotton_mcp_tools.utils.config import get_config

logger = logging.getLogger(__name__)


class XHSError(Exception):
    """Base exception for XHS API errors."""


class DataFetchError(XHSError):
    """Raised when data fetching fails."""


class IPBlockError(XHSError):
    """Raised when IP is blocked by XHS."""


class PlatformAccessError(XHSError):
    """Raised when access is restricted (auth/rate limit)."""


class NoteNotFoundError(XHSError):
    """Raised when a note is not found or abnormal."""


def _sign_with_xhshow(
    uri: str,
    data: Optional[Dict] = None,
    cookie_str: str = "",
    method: str = "POST",
) -> Dict[str, str]:
    """Generate signed headers using xhshow pure-algorithm library.

    Args:
        uri: API path.
        data: Request data (GET params dict or POST payload dict).
        cookie_str: Cookie string.
        method: Request method (GET or POST).

    Returns:
        Dictionary containing x-s, x-t, x-s-common, x-b3-traceid.
    """
    from xhshow import Xhshow

    xhshow_client = Xhshow()

    if method.upper() == "POST":
        headers = xhshow_client.sign_headers_post(
            uri=uri,
            cookies=cookie_str,
            payload=data if isinstance(data, dict) else {},
        )
    else:
        headers = xhshow_client.sign_headers_get(
            uri=uri,
            cookies=cookie_str,
            params=data if isinstance(data, dict) else {},
        )

    # Generate trace ID
    trace_id = f"{int(time.time() * 1000):x}{int(time.time() * 1000) % 10000:04x}"

    return {
        "x-s": headers.get("x-s", ""),
        "x-t": headers.get("x-t", ""),
        "x-s-common": headers.get("x-s-common", ""),
        "x-b3-traceid": headers.get("x-b3-traceid", trace_id),
    }


class XiaoHongShuService:
    """Xiaohongshu API client service.

    Provides methods to search notes, get note details, comments,
    and creator information from Xiaohongshu.
    """

    _BASE_URL = "https://edith.xiaohongshu.com"
    _DOMAIN = "https://www.xiaohongshu.com"

    # Error codes
    _IP_ERROR_CODE = 300012
    _SECURITY_LIMIT_CODE = 300011
    _NOTE_NOT_FOUND_CODE = -510000
    _NOTE_ABNORMAL_CODE = -510001

    def __init__(
        self,
        cookie: str | None = None,
        proxy: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the XHS service.

        Args:
            cookie: Xiaohongshu cookie string. Falls back to config if not provided.
            proxy: HTTP proxy URL. Falls back to config if not provided.
            timeout: Request timeout in seconds.

        Raises:
            ValueError: If cookie is not provided and not set in config.
        """
        config = get_config()
        self._cookie = cookie or config.xhs_cookie
        self._proxy = proxy or config.xhs_proxy or None
        self._timeout = timeout

        if not self._cookie:
            raise ValueError(
                "XHS cookie is required. Set XHS_COOKIE environment variable "
                "or pass cookie to the constructor."
            )

    def _build_headers(self) -> Dict[str, str]:
        """Build base request headers."""
        return {
            "Cookie": self._cookie,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": self._DOMAIN,
            "Referer": f"{self._DOMAIN}/",
        }

    def _build_query_string(self, params: Dict) -> str:
        """Build URL query string with encoding matching browser behavior."""
        parts = []
        for key, value in params.items():
            value_str = str(value) if value is not None else ""
            parts.append(f"{key}={quote(value_str, safe=',')}")
        return "&".join(parts)

    async def _request(
        self,
        method: str,
        uri: str,
        params: Optional[Dict] = None,
        payload: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make a signed request to XHS API.

        Args:
            method: HTTP method (GET or POST).
            uri: API path.
            params: GET request parameters.
            payload: POST request payload.

        Returns:
            API response data.

        Raises:
            DataFetchError: If data fetching fails.
            IPBlockError: If IP is blocked.
            PlatformAccessError: If access is restricted.
            NoteNotFoundError: If note is not found.
        """
        headers = self._build_headers()

        # Sign the request
        sign_data = params if method.upper() == "GET" else payload
        signs = _sign_with_xhshow(
            uri=uri,
            data=sign_data,
            cookie_str=self._cookie,
            method=method,
        )
        headers.update(signs)

        # Build URL
        if method.upper() == "GET" and params:
            url = f"{self._BASE_URL}{uri}?{self._build_query_string(params)}"
        else:
            url = f"{self._BASE_URL}{uri}"

        async with httpx.AsyncClient(proxy=self._proxy) as client:
            try:
                if method.upper() == "POST" and payload:
                    json_str = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
                    response = await client.request(
                        method=method,
                        url=url,
                        content=json_str,
                        headers=headers,
                        timeout=self._timeout,
                    )
                else:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        timeout=self._timeout,
                    )
            except httpx.HTTPError as exc:
                raise DataFetchError(f"HTTP request failed: {exc}") from exc

        # Check HTTP status codes
        if response.status_code in {401, 403, 429}:
            raise PlatformAccessError(
                f"XHS request blocked with HTTP {response.status_code}"
            )

        # Parse response
        try:
            data = response.json()
        except (TypeError, ValueError) as exc:
            raise DataFetchError(f"Failed to parse response: {exc}") from exc

        # Check response code
        response_code = data.get("code")
        if response_code == self._IP_ERROR_CODE:
            raise IPBlockError("Network connection error, please check network settings")
        if response_code == self._SECURITY_LIMIT_CODE:
            raise PlatformAccessError(
                f"XHS account security restriction, code: {self._SECURITY_LIMIT_CODE}"
            )
        if response_code in (self._NOTE_NOT_FOUND_CODE, self._NOTE_ABNORMAL_CODE):
            raise NoteNotFoundError(f"Note not found or abnormal, code: {response_code}")

        # Check success flag
        if data.get("success"):
            return data.get("data", data.get("success", {}))

        err_msg = data.get("msg", str(data))
        raise DataFetchError(err_msg)

    async def search_notes(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
        sort: str = "general",
        note_type: int = 0,
    ) -> Dict[str, Any]:
        """Search notes by keyword.

        Args:
            keyword: Search keyword.
            page: Page number (default: 1).
            page_size: Results per page (default: 20).
            sort: Sort type - "general", "popularity_descending", "time_descending".
            note_type: Note type - 0 (all), 1 (video), 2 (image).

        Returns:
            Search results with notes list.
        """
        uri = "/api/sns/web/v1/search/notes"
        payload = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_id": f"{int(time.time() * 1000):x}{int(time.time() * 1000) % 10000:04x}",
            "sort": sort,
            "note_type": note_type,
        }
        return await self._request("POST", uri, payload=payload)

    async def get_note_detail(self, note_id: str) -> Dict[str, Any]:
        """Get note detail by note ID.

        Args:
            note_id: The note ID.

        Returns:
            Note detail data including title, description, engagement metrics, etc.
        """
        uri = "/api/sns/web/v1/feed"
        payload = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": 1},
            "xsec_source": "pc_search",
            "xsec_token": "",
        }
        res = await self._request("POST", uri, payload=payload)
        if res and res.get("items"):
            return res["items"][0].get("note_card", {})
        return {}

    async def get_note_comments(
        self,
        note_id: str,
        cursor: str = "",
        max_comments: int = 20,
    ) -> Dict[str, Any]:
        """Get comments for a note.

        Args:
            note_id: The note ID.
            cursor: Pagination cursor for fetching next page.
            max_comments: Maximum number of comments to return.

        Returns:
            Comments data with comments list and pagination info.
        """
        uri = "/api/sns/web/v2/comment/page"
        params = {
            "note_id": note_id,
            "cursor": cursor,
            "top_comment_id": "",
            "image_formats": "jpg,webp,avif",
            "xsec_token": "",
        }
        return await self._request("GET", uri, params=params)

    async def get_note_all_comments(
        self,
        note_id: str,
        max_comments: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get all comments for a note with pagination.

        Args:
            note_id: The note ID.
            max_comments: Maximum number of comments to return.

        Returns:
            List of comment data.
        """
        result = []
        cursor = ""
        has_more = True

        while has_more and len(result) < max_comments:
            comments_res = await self.get_note_comments(
                note_id=note_id,
                cursor=cursor,
                max_comments=max_comments - len(result),
            )
            has_more = comments_res.get("has_more", False)
            cursor = comments_res.get("cursor", "")

            comments = comments_res.get("comments", [])
            if not comments:
                break

            result.extend(comments)

        return result[:max_comments]

    async def get_creator_notes(
        self,
        user_id: str,
        cursor: str = "",
        page_size: int = 30,
    ) -> Dict[str, Any]:
        """Get notes by a creator.

        Args:
            user_id: Creator's user ID.
            cursor: Pagination cursor.
            page_size: Results per page.

        Returns:
            Creator's notes with pagination info.
        """
        uri = "/api/sns/web/v1/user_posted"
        params = {
            "num": page_size,
            "cursor": cursor,
            "user_id": user_id,
            "image_formats": "jpg,webp,avif",
            "xsec_token": "",
            "xsec_source": "pc_feed",
        }
        return await self._request("GET", uri, params=params)

    async def get_creator_all_notes(
        self,
        user_id: str,
        max_notes: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get all notes by a creator with pagination.

        Args:
            user_id: Creator's user ID.
            max_notes: Maximum number of notes to return.

        Returns:
            List of note data.
        """
        result = []
        cursor = ""
        has_more = True

        while has_more and len(result) < max_notes:
            notes_res = await self.get_creator_notes(
                user_id=user_id,
                cursor=cursor,
            )
            has_more = notes_res.get("has_more", False)
            cursor = notes_res.get("cursor", "")

            notes = notes_res.get("notes", [])
            if not notes:
                break

            result.extend(notes)

        return result[:max_notes]


def format_note_data(note: Dict[str, Any]) -> Dict[str, Any]:
    """Format note data for output.

    Args:
        note: Raw note data from XHS API.

    Returns:
        Formatted note data with key fields.
    """
    user_info = note.get("user", {})
    interact_info = note.get("interact_info", {})
    image_list = note.get("image_list", [])
    tag_list = note.get("tag_list", [])

    # Extract video URL
    video_url = ""
    if note.get("type") == "video":
        video_dict = note.get("video", {})
        if video_dict:
            consumer = video_dict.get("consumer", {})
            origin_video_key = consumer.get("origin_video_key", "")
            if not origin_video_key:
                origin_video_key = consumer.get("originVideoKey", "")
            if origin_video_key:
                video_url = f"http://sns-video-bd.xhscdn.com/{origin_video_key}"

    return {
        "note_id": note.get("note_id", ""),
        "title": note.get("title") or note.get("desc", "")[:255],
        "desc": note.get("desc", ""),
        "type": note.get("type", "normal"),
        "user": {
            "user_id": user_info.get("user_id", ""),
            "nickname": user_info.get("nickname", ""),
        },
        "image_list": [img.get("url_default", img.get("url", "")) for img in image_list],
        "video_url": video_url,
        "tag_list": [tag.get("name", "") for tag in tag_list if tag.get("type") == "topic"],
        "liked_count": interact_info.get("liked_count", 0),
        "collected_count": interact_info.get("collected_count", 0),
        "comment_count": interact_info.get("comment_count", 0),
        "share_count": interact_info.get("share_count", 0),
        "time": note.get("time", 0),
        "last_update_time": note.get("last_update_time", 0),
        "note_url": f"https://www.xiaohongshu.com/explore/{note.get('note_id', '')}",
    }


def format_comment_data(comment: Dict[str, Any]) -> Dict[str, Any]:
    """Format comment data for output.

    Args:
        comment: Raw comment data from XHS API.

    Returns:
        Formatted comment data with key fields.
    """
    user_info = comment.get("user_info", {})
    target_comment = comment.get("target_comment", {})

    return {
        "comment_id": comment.get("id", ""),
        "content": comment.get("content", ""),
        "user": {
            "user_id": user_info.get("user_id", ""),
            "nickname": user_info.get("nickname", ""),
        },
        "create_time": comment.get("create_time", 0),
        "like_count": comment.get("like_count", 0),
        "sub_comment_count": comment.get("sub_comment_count", 0),
        "parent_comment_id": target_comment.get("id", ""),
        "pictures": [pic.get("url_default", "") for pic in comment.get("pictures", [])],
    }
