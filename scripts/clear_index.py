"""Script to clear all indexed documents from Supabase."""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.core.database import get_database
from src.utils.logger import get_logger

logger = get_logger()


async def clear_index() -> None:
    """Clear all documents from the therapy_chunks table."""
    database = get_database()
    
    try:
        # First, count existing rows
        count_result = database.client.table("therapy_chunks").select("id", count="exact").limit(1).execute()
        existing_count = count_result.count if hasattr(count_result, 'count') and count_result.count else 0
        
        if existing_count == 0:
            print("✓ No documents to clear. Database is already empty.")
            return
        
        # Delete all rows (Supabase requires a filter, so we use a condition that matches all UUIDs)
        # Using 'not.eq' with an impossible UUID value effectively matches all rows
        result = database.client.table("therapy_chunks").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        
        # Count deleted rows (Supabase returns deleted rows in data)
        deleted_count = len(result.data) if result.data else existing_count
        
        logger.info("index_cleared", deleted_count=deleted_count)
        print(f"✓ Cleared {deleted_count} document chunks from the database.")
        
    except Exception as e:
        logger.error("clear_index_failed", error=str(e))
        print(f"✗ Failed to clear index: {e}")
        raise


if __name__ == "__main__":
    print("⚠️  WARNING: This will delete ALL indexed documents from Supabase.")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() in ["yes", "y"]:
        asyncio.run(clear_index())
        print("\n✓ Index cleared. You can now run 'python scripts/index_data.py' to reindex.")
    else:
        print("Cancelled.")
