#!/usr/bin/env python
"""
MCP Server for FP&A data access.
Exposes financial data search and lookups as MCP tools.

Usage:
    python mcp-server/server.py
    Starts an MCP server on stdio (ready for SSE/TCP bridge)
"""

import sys
import json
import asyncio
from pathlib import Path

# Add parent directory to path so we can import from src/
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data_loader import load_csv, create_chunks
from src.embedding_service import EmbeddingService
from src.retrieval import FAISSRetrieval

# Import tools (relative to server directory)
server_dir = Path(__file__).parent
tools_dir = server_dir / "tools"
sys.path.insert(0, str(server_dir))

from tools.search_financial_data import search_financial_data
from tools.cost_center_lookup import get_cost_center_rows
from tools.get_audit_log import get_audit_log


class DataAccessServer:
    """MCP server for financial data access."""

    def __init__(self):
        """Initialize the server with data and indices."""
        print("Initializing MCP data server...", file=sys.stderr)

        # Load and index data
        rows = load_csv("data/sample_budget_data.csv")
        chunks = create_chunks(rows)
        embedding_service = EmbeddingService()
        self.faiss_retrieval = FAISSRetrieval(chunks, embedding_service)
        self.chunks = chunks

        print(f"  Loaded {len(rows)} rows, created {len(chunks)} chunks", file=sys.stderr)
        print(f"  FAISS index ready", file=sys.stderr)

    async def handle_search(self, args: dict) -> dict:
        """Handle search_financial_data tool call."""
        query = args.get("query")
        top_k = args.get("top_k", 5)

        if not query:
            return {"error": "query parameter required"}

        result = await search_financial_data(self.faiss_retrieval, query, top_k)
        return result

    async def handle_cost_center_lookup(self, args: dict) -> dict:
        """Handle get_cost_center_rows tool call."""
        cost_center_id = args.get("cost_center_id")
        period = args.get("period")

        if not cost_center_id:
            return {"error": "cost_center_id parameter required"}

        result = await get_cost_center_rows(self.chunks, cost_center_id, period)
        return result

    async def handle_audit_log(self, args: dict) -> dict:
        """Handle get_audit_log tool call."""
        session_id = args.get("session_id")
        limit = args.get("limit", 50)

        if not session_id:
            return {"error": "session_id parameter required"}

        result = await get_audit_log(session_id, limit)
        return result

    async def process_request(self, request: dict) -> dict:
        """Process a tool call request."""
        method = request.get("method")
        args = request.get("params", {})

        if method == "search_financial_data":
            return await self.handle_search(args)
        elif method == "get_cost_center_rows":
            return await self.handle_cost_center_lookup(args)
        elif method == "get_audit_log":
            return await self.handle_audit_log(args)
        else:
            return {"error": f"Unknown method: {method}"}

    async def run(self):
        """Run the server (read requests from stdin, write responses to stdout)."""
        print("MCP server ready.", file=sys.stderr)

        try:
            # Read one request from stdin
            line = sys.stdin.readline()
            if line:
                request = json.loads(line)
                response = await self.process_request(request)
                print(json.dumps(response))
                sys.stdout.flush()
            else:
                error_response = {"error": "No input received"}
                print(json.dumps(error_response))
                sys.stdout.flush()

        except json.JSONDecodeError as e:
            error_response = {"error": f"JSON decode error: {e}"}
            print(json.dumps(error_response))
            sys.stdout.flush()
        except Exception as e:
            error_response = {"error": f"Server error: {e}"}
            print(json.dumps(error_response))
            sys.stdout.flush()


if __name__ == "__main__":
    server = DataAccessServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("MCP server shutting down.", file=sys.stderr)
        sys.exit(0)
