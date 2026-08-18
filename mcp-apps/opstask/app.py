from __future__ import annotations

import datetime as dt
import uuid

from bobabricks_mcp import DatabricksTableClient, JsonRpcMcpApp, McpTool

db = DatabricksTableClient()


def list_existing_ops_tasks(arguments: dict) -> list[dict]:
    store_id = arguments.get("store_id")
    status = arguments.get("status")
    table = db.table_name("ops_tasks")
    where = []
    params = {}
    if store_id is not None:
        where.append("store_id = CAST(:store_id AS INT)")
        params["store_id"] = store_id
    if status:
        where.append("lower(status) = lower(:status)")
        params["status"] = status
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    return db.query(
        f"""
        SELECT task_id, store_id, title, description, category, severity, status, created_date, owner
        FROM {table}
        {where_sql}
        ORDER BY created_date DESC, task_id
        LIMIT 100
        """,
        params,
    )


def create_ops_task(arguments: dict) -> dict:
    table = db.table_name("ops_tasks")
    task_id = arguments.get("task_id") or f"OPS-{uuid.uuid4().hex[:6].upper()}"
    created_date = arguments.get("created_date") or dt.date.today().isoformat()
    status = arguments.get("status") or "open"
    owner = arguments.get("owner") or "Maria Chen"
    db.query(
        f"""
        INSERT INTO {table} (task_id, store_id, title, description, category, severity, status, created_date, owner)
        VALUES (:task_id, CAST(:store_id AS INT), :title, :description, :category, :severity, :status, DATE(:created_date), :owner)
        """,
        {
            "task_id": task_id,
            "store_id": arguments["store_id"],
            "title": arguments["title"],
            "description": arguments.get("description", ""),
            "category": arguments["category"],
            "severity": arguments["severity"],
            "status": status,
            "created_date": created_date,
            "owner": owner,
        },
    )
    return {"task_id": task_id, "status": status, "created_date": created_date, "owner": owner}


server = JsonRpcMcpApp(
    "bobabricks-opstask-mcp",
    [
        McpTool(
            name="list_existing_ops_tasks",
            description="Find existing OpsTask tickets for a store or status.",
            input_schema={
                "type": "object",
                "properties": {"store_id": {"type": "integer"}, "status": {"type": "string"}},
            },
            handler=list_existing_ops_tasks,
        ),
        McpTool(
            name="create_ops_task",
            description="Create an approved OpsTask follow-up ticket.",
            input_schema={
                "type": "object",
                "required": ["store_id", "title", "category", "severity"],
                "properties": {
                    "store_id": {"type": "integer"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {"type": "string"},
                    "severity": {"type": "string"},
                    "owner": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
            handler=create_ops_task,
        ),
    ],
)

app = server.app


if __name__ == "__main__":
    server.run()
