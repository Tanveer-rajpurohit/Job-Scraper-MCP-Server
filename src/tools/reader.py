"""
Reader tool for paginated retrieval from mode1.json, mode2.json, or mode3.json.

Allows Gemini Spark to fetch jobs in small, token-safe windows (e.g. 20 to 50 items)
with full job descriptions and application links.
"""
from __future__ import annotations

from typing import Any

from src.storage import read_mode_jobs


def register(mcp: Any) -> None:
    """
    Registers the get_saved_jobs tool on the FastMCP server.
    """

    @mcp.tool()
    async def get_saved_jobs(mode: str = "mode1", offset: int = 0, limit: int = 50) -> dict[str, Any]:
        """
        Retrieves a paginated slice of full job postings from a saved mode file.

        Args:
            mode: Which dataset to read ("mode1", "mode2", or "mode3").
            offset: Starting index for pagination (0-indexed). Default is 0.
            limit: Number of items to retrieve (default: 50, recommended 20-50).

        Returns:
            Dictionary containing mode name, total jobs stored, pagination window,
            has_more flag, and the requested list of complete job objects.
        """
        return read_mode_jobs(mode, offset=offset, limit=limit)
