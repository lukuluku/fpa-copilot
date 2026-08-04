"""
MCP Client — calls the fpa-data-mcp server for data access.
Wraps data access behind a service boundary.
"""

import json
import subprocess
import time
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MCPSearchResult:
    """Result from search_financial_data tool."""
    query: str
    results: list[dict]
    best_match_score: float


class MCPClient:
    """Client for communicating with the fpa-data-mcp server."""

    def __init__(self, server_process=None):
        """
        Initialize MCP client.

        Args:
            server_process: Optional subprocess.Popen for the server.
                           If None, start the server.
        """
        self.server_process = server_process
        self.request_id = 0

    def _send_request(self, method: str, params: dict) -> dict:
        """
        Send a request to the MCP server via subprocess.
        For Phase 5, we'll use a simple subprocess call approach.
        Production would use stdio/SSE/TCP bridges.
        """
        request = {"method": method, "params": params}

        # Start server subprocess for this request
        server_script = Path(__file__).parent.parent.parent / "mcp-server" / "server.py"
        server_script = str(server_script)

        try:
            process = subprocess.Popen(
                [sys.executable, server_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Send request and read response
            stdout, stderr = process.communicate(
                input=json.dumps(request) + "\n", timeout=30
            )

            # Parse JSON from stdout (skip any non-JSON lines)
            for line in stdout.split('\n'):
                line = line.strip()
                if line.startswith('{'):
                    try:
                        response = json.loads(line)
                        return response
                    except json.JSONDecodeError:
                        continue

            # If no JSON found, return error
            return {"error": "No JSON response from server"}

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "MCP server timeout"}
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse server response: {e}"}
        except Exception as e:
            return {"error": f"MCP client error: {e}"}

    def search_financial_data(self, query: str, top_k: int = 5) -> MCPSearchResult:
        """
        Search financial data via MCP.

        Args:
            query: Natural language query
            top_k: Number of results to return

        Returns:
            MCPSearchResult with retrieved chunks
        """
        start = time.time()
        response = self._send_request(
            "search_financial_data", {"query": query, "top_k": top_k}
        )
        latency_ms = (time.time() - start) * 1000

        if "error" in response:
            # Return empty result on error
            return MCPSearchResult(query=query, results=[], best_match_score=0.0)

        return MCPSearchResult(
            query=response.get("query"),
            results=response.get("results", []),
            best_match_score=response.get("best_match_score", 0.0),
        )

    def get_cost_center_rows(self, cost_center_id: str, period: str | None = None) -> dict:
        """Get rows for a specific cost center via MCP."""
        response = self._send_request(
            "get_cost_center_rows",
            {"cost_center_id": cost_center_id, "period": period},
        )
        return response

    def get_audit_log(self, session_id: str, limit: int = 50) -> dict:
        """Get audit log for a session via MCP."""
        response = self._send_request("get_audit_log", {"session_id": session_id, "limit": limit})
        return response


if __name__ == "__main__":
    # Quick test
    client = MCPClient()
    result = client.search_financial_data("What was the engineering variance?", top_k=3)
    print(f"Query: {result.query}")
    print(f"Results: {len(result.results)}")
    print(f"Best match: {result.best_match_score:.3f}")
