"""
MCP Tool: get_cost_center_rows
Lookup specific cost center data.
"""

from typing import Any


async def get_cost_center_rows(
    chunks: list[Any], cost_center_id: str, period: str | None = None
) -> dict:
    """
    Get all rows for a specific cost center, optionally filtered by period.

    Args:
        chunks: List of all data chunks
        cost_center_id: Cost center ID to look up
        period: Optional period filter (e.g., "2026-Q3")

    Returns:
        Dictionary with matching rows
    """
    matching = []

    for chunk in chunks:
        if chunk.source_row.get("cost_center") == cost_center_id:
            if period is None or chunk.source_row.get("period") == period:
                matching.append(chunk.source_row)

    return {
        "cost_center_id": cost_center_id,
        "period": period,
        "row_count": len(matching),
        "rows": matching,
    }
