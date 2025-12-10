"""SQLite-backed persistence for unsent batches with startup recovery and pruning.

Persists failed write batches for durability across restarts and flushes them
on next startup, pruning oldest entries when exceeding configured limits.
"""

import json
import logging
import os
import sqlite3
import time
from typing import Any, Sequence, Tuple

from .config import get


_db_path = get("persistence.db_path")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", _db_path)
MAX_PERSISTED_BATCHES = get("persistence.max_batches")


def _init_db() -> None:
    """Ensure persistence database and table exist (idempotent)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
			CREATE TABLE IF NOT EXISTS unsent_batches (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				persisted_at REAL NOT NULL,
				batch_json TEXT NOT NULL
			)
		""")
        conn.commit()
        conn.close()
    except Exception:
        logging.exception("Failed to initialize persistence database")


def persist_batch(batch: Sequence[dict[str, Any]]) -> None:
    """Store a batch of points for later retry; noop if batch empty."""
    if not batch:
        return
    try:
        _init_db()  # Ensure table exists before inserting
        conn = sqlite3.connect(DB_PATH)
        batch_json = json.dumps(batch)
        conn.execute(
            "INSERT INTO unsent_batches (persisted_at, batch_json) VALUES (?, ?)",
            (time.time(), batch_json),
        )
        conn.commit()
        conn.close()
        logging.info(f"Persisted batch of {len(batch)} points to database")
        _prune_old_batches()
    except Exception:
        logging.exception("Failed to persist batch to database")


def _prune_old_batches() -> None:
    """Prune oldest rows when count exceeds maximum configured limit."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT COUNT(*) FROM unsent_batches")
        count = cursor.fetchone()[0]
        if count <= MAX_PERSISTED_BATCHES:
            conn.close()
            return
        # Delete oldest rows to bring count down to 80% of max
        target = int(MAX_PERSISTED_BATCHES * 0.8)
        to_remove = count - target
        conn.execute(
            "DELETE FROM unsent_batches WHERE id IN "
            "(SELECT id FROM unsent_batches ORDER BY persisted_at ASC LIMIT ?)",
            (to_remove,),
        )
        conn.commit()
        logging.info(f"Pruned {to_remove} old persisted batches")
        conn.close()
    except Exception:
        logging.exception("Failed to prune old persisted batches")


def load_and_flush_persisted_batches(db_adapter) -> Tuple[int, int]:
    """Flush persisted batches (oldest first) removing successful or invalid ones.

    Args:
        db_adapter: Database adapter instance (TimeSeriesDB implementation)

    Returns:
        (success_count, failure_count) counts of flushed and failed attempts.
    """
    _init_db()
    success_count = 0
    failure_count = 0
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT id, batch_json FROM unsent_batches ORDER BY persisted_at ASC")
        rows = cursor.fetchall()
        conn.close()
        for row_id, batch_json in rows:
            try:
                batch = json.loads(batch_json)
                db_adapter.write_points(batch)
                logging.info(f"Flushed persisted batch {row_id} to database")
                # Remove from database
                conn = sqlite3.connect(DB_PATH)
                conn.execute("DELETE FROM unsent_batches WHERE id = ?", (row_id,))
                conn.commit()
                conn.close()
                success_count += 1
            except json.JSONDecodeError as e:
                # Malformed JSON: log and drop the batch
                logging.error(f"Malformed JSON in persisted batch {row_id}: {e}; dropping batch")
                conn = sqlite3.connect(DB_PATH)
                conn.execute("DELETE FROM unsent_batches WHERE id = ?", (row_id,))
                conn.commit()
                conn.close()
                failure_count += 1
            except Exception as e:
                # Check if it's an HTTP 400 error (bad request) - database-agnostic
                error_msg = str(e).lower()
                if "400" in error_msg or "bad request" in error_msg or "invalid" in error_msg:
                    logging.error(
                        f"Database rejected batch {row_id} (bad request): {e}; dropping batch"
                    )
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("DELETE FROM unsent_batches WHERE id = ?", (row_id,))
                    conn.commit()
                    conn.close()
                    failure_count += 1
                else:
                    logging.exception(f"Failed to flush persisted batch {row_id}: {e}")
                    failure_count += 1
    except Exception:
        logging.exception("Failed to load persisted batches for flushing")
    return success_count, failure_count


def recover_persisted_batches() -> None:
    """Recover and flush persisted batches from previous runs.

    This function handles the complete persistence recovery workflow:
    - Loads database configuration
    - Creates appropriate database adapter
    - Flushes persisted batches
    - Closes database connection
    - Skips recovery if data collection is disabled or database type is 'none'
    """
    from .config import get
    from .databases import create_database_adapter
    from .database_writer import get_database_config

    try:
        logging.info("Loading persisted batches from previous runs...")

        # Create database adapter for persistence recovery
        db_type = get("database.type")
        db_config = get_database_config(db_type)

        if get("data_collection.enabled") and db_type != "none":
            db_adapter = create_database_adapter(db_type, db_config)
            success, failure = load_and_flush_persisted_batches(db_adapter)
            logging.info(f"Persisted batch recovery: {success} flushed, {failure} failed/pending")
            db_adapter.close()
        else:
            logging.info(
                "Data collection disabled or database type is 'none' - skipping persistence recovery"
            )
    except Exception as e:
        logging.exception(f"Error during persisted batch recovery: {e}")
