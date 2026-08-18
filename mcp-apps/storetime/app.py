from __future__ import annotations

from bobabricks_mcp import DatabricksTableClient, JsonRpcMcpApp, McpTool

db = DatabricksTableClient()


def inspect_schedule(arguments: dict) -> list[dict]:
    store_id = arguments.get("store_id")
    week = arguments.get("week")
    schedule_table = db.table_name("schedules")
    shift_table = db.table_name("storetime_shifts")
    where = []
    params = {}
    if store_id is not None:
        where.append("s.store_id = CAST(:store_id AS INT)")
        params["store_id"] = store_id
    if week:
        where.append("s.week = :week")
        params["week"] = week
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    return db.query(
        f"""
        SELECT s.store_id, s.week, s.scheduled_training_hours, s.completed_training_hours,
               s.converted_training_hours, s.conversion_reason,
               count(sh.shift_id) AS shift_count,
               sum(sh.scheduled_partners) AS scheduled_partners,
               sum(sh.actual_partners) AS actual_partners
        FROM {schedule_table} s
        LEFT JOIN {shift_table} sh ON s.store_id = sh.store_id
        {where_sql}
        GROUP BY s.store_id, s.week, s.scheduled_training_hours, s.completed_training_hours,
                 s.converted_training_hours, s.conversion_reason
        ORDER BY s.store_id
        LIMIT 100
        """,
        params,
    )


def list_training_events(arguments: dict) -> list[dict]:
    store_id = arguments.get("store_id")
    week = arguments.get("week")
    table = db.table_name("training_events")
    where = []
    params = {}
    if store_id is not None:
        where.append("store_id = CAST(:store_id AS INT)")
        params["store_id"] = store_id
    if week:
        where.append("week = :week")
        params["week"] = week
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    return db.query(
        f"""
        SELECT store_id, week, scheduled_training_hours, completed_training_hours,
               converted_training_hours, conversion_reason
        FROM {table}
        {where_sql}
        ORDER BY store_id, week
        LIMIT 100
        """,
        params,
    )


server = JsonRpcMcpApp(
    "bobabricks-storetime-mcp",
    [
        McpTool(
            name="inspect_schedule",
            description="Inspect training schedule conversion and rush-window coverage by store.",
            input_schema={
                "type": "object",
                "properties": {"store_id": {"type": "integer"}, "week": {"type": "string"}},
            },
            handler=inspect_schedule,
        ),
        McpTool(
            name="list_training_events",
            description="List StoreTime training events for a store or week.",
            input_schema={
                "type": "object",
                "properties": {"store_id": {"type": "integer"}, "week": {"type": "string"}},
            },
            handler=list_training_events,
        ),
    ],
)

app = server.app


if __name__ == "__main__":
    server.run()
