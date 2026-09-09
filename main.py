"""
Main entrypoint for the Job Scraper FastMCP server.

Initializes the MCP server, registers mode scrapers and storage readers,
and serves streamable HTTP for Gemini Spark integration.
"""
from __future__ import annotations

import logging
from pathlib import Path

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

from src.config import MCP_PORT
from src.tools import mode1, mode2, mode3, reader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("job-scraper")

mcp = FastMCP("job-scraper")

mode1.register(mcp)
mode2.register(mcp)
mode3.register(mcp)
reader.register(mcp)


@mcp.resource("jobs://{mode}")
def get_mode_resource(mode: str) -> str:
    """
    Exposes raw JSON content of mode1, mode2, or mode3 as an MCP Resource.
    Allows Gemini Spark to read the complete dataset without token tool constraints.
    """
    clean_mode = mode.lower().replace(".json", "")
    target = Path("data") / f"{clean_mode}.json"
    if not target.exists():
        return f'{{"error": "Dataset {clean_mode}.json not found. Run scraper first."}}'
    return target.read_text(encoding="utf-8")


if __name__ == "__main__":
    log.info("Starting Job Scraper MCP server on port %d", MCP_PORT)
    mcp.run(transport="streamable-http", port=MCP_PORT)
