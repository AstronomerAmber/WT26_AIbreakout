from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone


TOKEN_REFRESH_MARGIN_SECONDS = 50 * 60


@dataclass(frozen=True)
class LakebaseMemoryStatus:
    enabled: bool
    message: str


class LakebaseMemoryClient:
    def __init__(self):
        self.instance_name = os.getenv("LAKEBASE_INSTANCE_NAME", "bobabricks")
        self.endpoint = os.getenv("LAKEBASE_ENDPOINT", "")
        self.host = os.getenv("LAKEBASE_HOST", "")
        self.database = os.getenv("LAKEBASE_DATABASE_NAME", "databricks_postgres")
        self.schema = os.getenv("LAKEBASE_MEMORY_SCHEMA", "bobabricks_app")
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._lock = threading.Lock()

    def status(self) -> LakebaseMemoryStatus:
        if not self.endpoint or not self.host:
            return LakebaseMemoryStatus(False, "Lakebase endpoint/host not configured for this app resource")
        if not self._dependencies_available():
            return LakebaseMemoryStatus(False, "Lakebase dependencies unavailable in this local environment")
        try:
            self._ensure_schema()
        except Exception as exc:
            return LakebaseMemoryStatus(False, f"Lakebase unavailable: {exc.__class__.__name__}")
        return LakebaseMemoryStatus(True, f"Lakebase connected to {self.database}.{self.schema}")

    def remember_preference(self, user_id: str, key: str, value: str) -> bool:
        if not self.endpoint or not self.host:
            return False
        if not self._dependencies_available():
            return False
        try:
            self._ensure_schema()
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        INSERT INTO {self.schema}.user_preferences (user_id, memory_key, memory_value, updated_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id, memory_key)
                        DO UPDATE SET memory_value = EXCLUDED.memory_value, updated_at = EXCLUDED.updated_at
                        """,
                        (user_id, key, value, datetime.now(timezone.utc)),
                    )
            return True
        except Exception:
            return False

    def load_preferences(self, user_id: str) -> dict[str, str]:
        if not self.endpoint or not self.host:
            return {}
        if not self._dependencies_available():
            return {}
        try:
            self._ensure_schema()
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"SELECT memory_key, memory_value FROM {self.schema}.user_preferences WHERE user_id = %s",
                        (user_id,),
                    )
                    return {key: value for key, value in cursor.fetchall()}
        except Exception:
            return {}

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.schema}.user_preferences (
                        user_id TEXT NOT NULL,
                        memory_key TEXT NOT NULL,
                        memory_value TEXT NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (user_id, memory_key)
                    )
                    """
                )

    def _connect(self):
        import psycopg2

        return psycopg2.connect(
            host=self.host,
            database=self.database,
            user=self._current_user_name(),
            password=self._database_token(),
            port=5432,
            sslmode="require",
            connect_timeout=10,
        )

    def _database_token(self) -> str:
        with self._lock:
            if self._token and time.time() < self._token_expires_at:
                return self._token

            from databricks.sdk import WorkspaceClient

            workspace = WorkspaceClient()
            response = workspace.api_client.do(
                "POST",
                "/api/2.0/postgres/credentials",
                body={"endpoint": self.endpoint},
            )
            self._token = response["token"]
            self._token_expires_at = time.time() + TOKEN_REFRESH_MARGIN_SECONDS
            return self._token

    @staticmethod
    def _current_user_name() -> str:
        from databricks.sdk import WorkspaceClient

        return WorkspaceClient().current_user.me().user_name

    @staticmethod
    def _dependencies_available() -> bool:
        try:
            import databricks.sdk  # noqa: F401
            import psycopg2  # noqa: F401
        except ImportError:
            return False
        return True
