"""MCP server (FastMCP 4). Two read-only tools. The agent cannot write or delete anything.

Run:  python mcp_server.py        (stdio, used by graph.py)
      python mcp_server.py http   (http://127.0.0.1:8000/mcp)
"""
import json, sys
from pathlib import Path
from fastmcp import FastMCP

HERE = Path(__file__).parent
mcp = FastMCP("QUGateTools")
CFR = json.loads((HERE / "data" / "cfr211.json").read_text())
PRECEDENTS = json.loads((HERE / "data" / "precedents.json").read_text())


@mcp.tool
def get_cfr_section(section: str) -> dict:
    """Return title and text of one 21 CFR 211 section, e.g. '211.100'. Returns found=false if it does not exist."""
    hit = CFR.get(section)
    return {"found": bool(hit), "section": section, **(hit or {})}


@mcp.tool
def search_precedents(cfr_section: str, limit: int = 3) -> dict:
    """Return FDA warning-letter excerpts that cite the given 21 CFR 211 section. hits is empty when there are none."""
    return {"cfr_section": cfr_section, "hits": [p for p in PRECEDENTS if cfr_section in p["cfr_sections"]][:limit]}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        mcp.run(transport="http", host="127.0.0.1", port=8000)
    else:
        mcp.run(show_banner=False)
