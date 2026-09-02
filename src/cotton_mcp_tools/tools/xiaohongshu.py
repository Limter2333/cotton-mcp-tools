"""Xiaohongshu (XHS) crawler tools for MCP server.

Provides tools to search notes, get note details, comments,
and creator information from Xiaohongshu.
"""

from __future__ import annotations

import json
import logging

from mcp.server.fastmcp import FastMCP

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

logger = logging.getLogger(__name__)


def _create_service() -> XiaoHongShuService:
    """Create an XHS service instance.

    Returns:
        XiaoHongShuService instance.

    Raises:
        ValueError: If configuration is invalid.
    """
    return XiaoHongShuService()


def register_xiaohongshu_tools(server: FastMCP) -> None:
    """Register Xiaohongshu tools with the MCP server."""

    @server.tool()
    async def xhs_search_notes(
        keyword: str,
        page: int = 1,
        sort: str = "general",
        note_type: str = "all",
    ) -> str:
        """Search Xiaohongshu notes by keyword.

        Args:
            keyword: Search keyword.
            page: Page number (default: 1).
            sort: Sort type - "general" (default), "latest", "popularity_descending".
            note_type: Note type - "all" (default), "video", "image".

        Returns:
            JSON formatted search results with notes list.
        """
        # Validate sort type
        sort_map = {
            "general": "general",
            "latest": "time_descending",
            "popularity_descending": "popularity_descending",
        }
        sort_value = sort_map.get(sort.lower())
        if sort_value is None:
            valid = ", ".join(sorted(sort_map.keys()))
            return f"Error: Invalid sort type '{sort}'. Valid options: {valid}"

        # Validate note type
        note_type_map = {"all": 0, "video": 1, "image": 2}
        note_type_value = note_type_map.get(note_type.lower())
        if note_type_value is None:
            valid = ", ".join(sorted(note_type_map.keys()))
            return f"Error: Invalid note type '{note_type}'. Valid options: {valid}"

        try:
            service = _create_service()
        except ValueError as exc:
            return f"Error: {exc}"

        try:
            result = await service.search_notes(
                keyword=keyword,
                page=page,
                sort=sort_value,
                note_type=note_type_value,
            )
            notes = result.get("items", [])
            formatted_notes = []
            for item in notes:
                note_card = item.get("note_card", {})
                if note_card:
                    note_card["note_id"] = item.get("id", "")
                    formatted_notes.append(format_note_data(note_card))

            return json.dumps({
                "keyword": keyword,
                "page": page,
                "total": len(formatted_notes),
                "notes": formatted_notes,
            }, ensure_ascii=False, indent=2)
        except XHSError as exc:
            logger.error("xhs_search_notes failed: %s", exc)
            return f"Error: {exc}"

    @server.tool()
    async def xhs_get_note_detail(note_id: str) -> str:
        """Get Xiaohongshu note detail by note ID.

        Args:
            note_id: The note ID to fetch.

        Returns:
            JSON formatted note detail including title, description,
            engagement metrics, images, and video URL.
        """
        try:
            service = _create_service()
        except ValueError as exc:
            return f"Error: {exc}"

        try:
            note = await service.get_note_detail(note_id)
            if not note:
                return f"Error: Note not found with ID '{note_id}'"

            formatted = format_note_data(note)
            return json.dumps(formatted, ensure_ascii=False, indent=2)
        except XHSError as exc:
            logger.error("xhs_get_note_detail failed: %s", exc)
            return f"Error: {exc}"

    @server.tool()
    async def xhs_get_note_comments(
        note_id: str,
        max_comments: int = 20,
    ) -> str:
        """Get comments for a Xiaohongshu note.

        Args:
            note_id: The note ID to fetch comments for.
            max_comments: Maximum number of comments to return (default: 20).

        Returns:
            JSON formatted comments list with user info and engagement metrics.
        """
        try:
            service = _create_service()
        except ValueError as exc:
            return f"Error: {exc}"

        try:
            comments = await service.get_note_all_comments(
                note_id=note_id,
                max_comments=max_comments,
            )
            formatted_comments = [format_comment_data(c) for c in comments]

            return json.dumps({
                "note_id": note_id,
                "total": len(formatted_comments),
                "comments": formatted_comments,
            }, ensure_ascii=False, indent=2)
        except XHSError as exc:
            logger.error("xhs_get_note_comments failed: %s", exc)
            return f"Error: {exc}"

    @server.tool()
    async def xhs_get_creator_notes(
        user_id: str,
        max_notes: int = 20,
    ) -> str:
        """Get notes by a Xiaohongshu creator.

        Args:
            user_id: Creator's user ID.
            max_notes: Maximum number of notes to return (default: 20).

        Returns:
            JSON formatted notes list from the creator.
        """
        try:
            service = _create_service()
        except ValueError as exc:
            return f"Error: {exc}"

        try:
            notes = await service.get_creator_all_notes(
                user_id=user_id,
                max_notes=max_notes,
            )
            formatted_notes = [format_note_data(n) for n in notes]

            return json.dumps({
                "user_id": user_id,
                "total": len(formatted_notes),
                "notes": formatted_notes,
            }, ensure_ascii=False, indent=2)
        except XHSError as exc:
            logger.error("xhs_get_creator_notes failed: %s", exc)
            return f"Error: {exc}"
