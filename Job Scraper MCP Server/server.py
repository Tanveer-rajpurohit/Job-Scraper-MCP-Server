"""
Job Scraper MCP Server - Backward compatibility entrypoint.
Points directly to main.py.
"""
from main import mcp, MCP_PORT, log

if __name__ == "__main__":
    log.info("Starting Job Scraper MCP server (via server.py) on port %d", MCP_PORT)
    mcp.run(transport="streamable-http", port=MCP_PORT)
