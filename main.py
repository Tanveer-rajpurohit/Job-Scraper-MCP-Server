"""
Main entrypoint for the Job Scraper FastMCP server.

Initializes the MCP server, registers mode scrapers and storage readers,
and serves streamable HTTP for Gemini Spark integration.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

from starlette.requests import Request
from starlette.responses import JSONResponse

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


@mcp.tool()
async def scrape_jobs(mode: str = "mode2") -> dict[str, Any]:
    """
    Unified job scraper tool. Dispatches scraping runs based on the requested mode.

    Args:
        mode: Target scraping mode. Allowed values:
            - "mode1" (or "india_all"): Broad pan-India sweep across 13 engineering tracks.
            - "mode2" (or "location"): Location-focused sweep prioritizing Gujarat (Ahmedabad, Gandhinagar, Vadodara) and Tier-1 metros (Delhi NCR, Mumbai, Pune). Default.
            - "mode3" (or "remote"): 100% remote software engineering roles open to India-based candidates.

    Returns:
        Lightweight execution summary adhering to token safety limits with top preview matches,
        direct apply URLs, and permanent Google Drive download links.
    """
    normalized = mode.strip().lower()
    if normalized in ("mode1", "1", "india_all", "all_india"):
        return await mode1.run_mode1()
    if normalized in ("mode2", "2", "location", "gujarat"):
        return await mode2.run_mode2()
    if normalized in ("mode3", "3", "remote"):
        return await mode3.run_mode3()
    return {
        "status": "error",
        "error": f"Unknown mode '{mode}'. Supported values: 'mode1', 'mode2', 'mode3'.",
        "supported_modes": ["mode1", "mode2", "mode3"],
    }


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """
    Lightweight healthcheck endpoint for cron-job.org and uptime monitors.
    Responds in sub-10ms without triggering scrapes or generating files.
    """
    return JSONResponse({"status": "healthy", "service": "job-scraper-mcp"})


@mcp.custom_route("/", methods=["GET"])
async def root_ping(request: Request) -> JSONResponse:
    """
    Root endpoint for browser checks and uptime pings.
    """
    return JSONResponse({
        "status": "healthy",
        "service": "job-scraper-mcp",
        "mcp_endpoint": "/mcp",
    })


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
    mcp.run(transport="streamable-http", host="0.0.0.0", port=MCP_PORT)
