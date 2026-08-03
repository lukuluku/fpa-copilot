"""
Load and chunk finance data from CSV for embedding and retrieval.
Each row becomes a searchable chunk with context.
"""

import csv
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Chunk:
    """A searchable unit of finance data."""
    chunk_id: str
    text: str  # Full text for embedding
    source_row: dict  # Original CSV row for citation


def load_csv(csv_path: str) -> list[dict]:
    """Load CSV file into list of dicts."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    rows = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def create_chunks(rows: list[dict]) -> list[Chunk]:
    """
    Convert CSV rows into searchable chunks.
    Each row becomes one chunk with context that makes it embeddable.
    """
    chunks = []
    for idx, row in enumerate(rows):
        # Format the row as readable text for embedding
        text = (
            f"Cost Center: {row['cost_center_name']} (ID: {row['cost_center']}). "
            f"Category: {row['category']}. "
            f"Period: {row['period']}. "
            f"Budget: ${row['budget']}, Actuals: ${row['actuals']}, "
            f"Variance: {row['variance_pct']}%"
        )

        chunk = Chunk(
            chunk_id=f"chunk_{idx:03d}",
            text=text,
            source_row=row,
        )
        chunks.append(chunk)

    return chunks


if __name__ == "__main__":
    # Quick test
    rows = load_csv("data/sample_budget_data.csv")
    print(f"Loaded {len(rows)} rows")
    chunks = create_chunks(rows)
    print(f"Created {len(chunks)} chunks")
    print("\nFirst chunk:")
    print(f"  ID: {chunks[0].chunk_id}")
    print(f"  Text: {chunks[0].text}")
