"""
Standalone test script for the GitHub Remote MCP Server.
Port of mcp/githubMcpClient.js.

Usage:
    python -m app.mcp.github_mcp_client
"""

import asyncio
import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv

load_dotenv()

import httpx


MCP_URL = "https://api.githubcopilot.com/mcp/"


async def test() -> None:
    """Test the GitHub Remote MCP Server with a get_me call."""
    try:
        pat = os.getenv("GITHUB_MCP_PAT")
        if not pat:
            raise RuntimeError("GITHUB_MCP_PAT is missing.")

        async with httpx.AsyncClient(
            base_url=MCP_URL,
            timeout=httpx.Timeout(30.0),
            headers={
                "Authorization": f"Bearer {pat}",
                "Content-Type": "application/json",
            },
        ) as client:
            response = await client.post(
                "",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "get_me",
                        "arguments": {},
                    },
                },
            )
            response.raise_for_status()
            print(json.dumps(response.json(), indent=2))

    except Exception as e:
        print(f"\n========== TEST ERROR ==========\n")
        print(str(e))
        print(f"\n================================\n")


if __name__ == "__main__":
    asyncio.run(test())
