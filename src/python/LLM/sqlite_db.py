from __future__ import annotations

import sqlite3
from pathlib import Path


def create_llm_models_sqlite_db(db_path: str | Path) -> Path:
    """Create a SQLite database with a table representing LLMModel data.

    The function creates parent directories when needed, creates the SQLite file,
    and initializes the `llm_models` table plus supporting indexes.
    """
    path = Path(db_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_models (
                id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                display_name TEXT,
                version TEXT,
                provider TEXT NOT NULL,
                description TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                capabilities_json TEXT NOT NULL DEFAULT '[]',

                token_context_window INTEGER NOT NULL,
                token_max_output_tokens INTEGER,
                token_max_input_tokens INTEGER,
                token_embedding_dimensions INTEGER,

                pricing_input_cost REAL,
                pricing_output_cost REAL,
                pricing_unit TEXT,
                pricing_currency TEXT,
                pricing_free_tier_tokens INTEGER,

                connection_base_url TEXT,
                connection_api_key TEXT,
                connection_api_version TEXT,
                connection_organization_id TEXT,
                connection_deployment_id TEXT,
                connection_timeout_seconds REAL NOT NULL DEFAULT 30.0,
                connection_max_retries INTEGER NOT NULL DEFAULT 3,
                connection_extra_headers_json TEXT NOT NULL DEFAULT '{}',
                connection_proxy_url TEXT,

                rate_requests_per_minute INTEGER,
                rate_tokens_per_minute INTEGER,
                rate_tokens_per_day INTEGER,
                rate_concurrent_requests INTEGER,

                status TEXT NOT NULL,
                execution_backend TEXT NOT NULL,

                tokenizer_name TEXT,
                tokenizer_library TEXT,
                tokenizer_vocab_size INTEGER,
                tokenizer_supports_special_tokens INTEGER,
                tokenizer_bos_token TEXT,
                tokenizer_eos_token TEXT,
                tokenizer_pad_token TEXT,
                tokenizer_chat_template TEXT,

                usage_total_requests INTEGER NOT NULL DEFAULT 0,
                usage_successful_requests INTEGER NOT NULL DEFAULT 0,
                usage_failed_requests INTEGER NOT NULL DEFAULT 0,
                usage_total_input_tokens INTEGER NOT NULL DEFAULT 0,
                usage_total_output_tokens INTEGER NOT NULL DEFAULT 0,
                usage_total_embedding_tokens INTEGER NOT NULL DEFAULT 0,
                usage_total_latency_seconds REAL NOT NULL DEFAULT 0.0,
                usage_last_request_at TEXT,

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deprecated_at TEXT,
                expires_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            """
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_llm_models_model_id ON llm_models(model_id);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_models_provider ON llm_models(provider);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_models_is_active ON llm_models(is_active);"
        )
        conn.commit()

    return path
