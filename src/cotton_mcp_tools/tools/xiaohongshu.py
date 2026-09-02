"""Xiaohongshu (XHS) crawler tools for MCP server.

Provides tools to search notes, get note details, comments,
and creator information from Xiaohongshu. Also provides tools
for analyzing note images with OCR.
"""

from __future__ import annotations

import json
import logging

from mcp.server.fastmcp import FastMCP

from cotton_mcp_tools.services.ocr_service import OCRService
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

    @server.tool()
    async def xhs_analyze_note_with_ocr(
        note_id: str,
        max_images: int = 5,
        language: str = "zh",
        model: str | None = None,
    ) -> str:
        """Get Xiaohongshu note detail and analyze text in images using OCR.

        Fetches the note details, extracts image URLs, performs OCR on each
        image to recognize text content, and returns a comprehensive analysis
        combining the note content with OCR results.

        Args:
            note_id: The note ID to fetch and analyze.
            max_images: Maximum number of images to analyze (default: 5).
            language: Expected language for OCR (default: "zh" for Chinese).
            model: Optional model override for OCR.

        Returns:
            JSON formatted result with note details, OCR results for each
            image, and a comprehensive summary.
        """
        try:
            xhs_service = _create_service()
        except ValueError as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

        # Step 1: Get note details
        try:
            note = await xhs_service.get_note_detail(note_id)
            if not note:
                return json.dumps({
                    "error": f"Note not found with ID '{note_id}'",
                }, ensure_ascii=False)
        except XHSError as exc:
            logger.error("xhs_analyze_note_with_ocr failed to get note: %s", exc)
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

        # Step 2: Format note data
        formatted_note = format_note_data(note)
        image_urls = formatted_note.get("image_list", [])

        # Limit images
        images_to_analyze = image_urls[:max_images]

        # Step 3: Perform OCR on each image
        ocr_results = []
        all_ocr_text = []

        if images_to_analyze:
            try:
                ocr_service = OCRService(model=model)

                for i, img_url in enumerate(images_to_analyze):
                    if not img_url:
                        continue

                    try:
                        logger.info("Analyzing image %d/%d: %s", i + 1, len(images_to_analyze), img_url[:50])
                        ocr_result = await ocr_service.recognize_text(
                            image=img_url,
                            language=language,
                        )
                        ocr_result["image_url"] = img_url
                        ocr_result["image_index"] = i + 1
                        ocr_results.append(ocr_result)

                        if ocr_result.get("full_text"):
                            all_ocr_text.append(ocr_result["full_text"])
                    except Exception as exc:
                        logger.warning("OCR failed for image %d: %s", i + 1, exc)
                        ocr_results.append({
                            "image_url": img_url,
                            "image_index": i + 1,
                            "error": str(exc),
                            "has_text": False,
                        })
            except ValueError as exc:
                logger.warning("Failed to create OCR service: %s", exc)

        # Step 4: Generate comprehensive summary
        note_desc = formatted_note.get("desc", "")
        note_title = formatted_note.get("title", "")
        note_tags = formatted_note.get("tag_list", [])

        # Combine all text sources
        combined_text_parts = []
        if note_title:
            combined_text_parts.append(f"标题: {note_title}")
        if note_desc:
            combined_text_parts.append(f"描述: {note_desc}")
        if note_tags:
            combined_text_parts.append(f"标签: {', '.join(note_tags)}")
        if all_ocr_text:
            combined_text_parts.append(f"图片文字内容:\n" + "\n---\n".join(all_ocr_text))

        combined_text = "\n\n".join(combined_text_parts)

        # Build final result
        result = {
            "note": formatted_note,
            "ocr_analysis": {
                "total_images": len(image_urls),
                "analyzed_images": len(images_to_analyze),
                "images_with_text": sum(1 for r in ocr_results if r.get("has_text")),
                "results": ocr_results,
            },
            "summary": {
                "title": note_title,
                "description": note_desc,
                "tags": note_tags,
                "ocr_text_count": len(all_ocr_text),
                "combined_text": combined_text,
                "engagement": {
                    "likes": formatted_note.get("liked_count", 0),
                    "collects": formatted_note.get("collected_count", 0),
                    "comments": formatted_note.get("comment_count", 0),
                    "shares": formatted_note.get("share_count", 0),
                },
            },
        }

        return json.dumps(result, ensure_ascii=False, indent=2)
