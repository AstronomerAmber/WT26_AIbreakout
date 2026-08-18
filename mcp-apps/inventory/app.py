from __future__ import annotations

from bobabricks_mcp import DatabricksTableClient, JsonRpcMcpApp, McpTool

db = DatabricksTableClient()


def assess_inventory_risk(arguments: dict) -> list[dict]:
    store_id = arguments.get("store_id")
    risk = arguments.get("stockout_risk")
    table = db.table_name("inventory")
    return db.query(
        f"""
        SELECT store_id, ingredient, on_hand_units, forecast_7d_units, reorder_eta_days,
               stockout_risk, supplier,
               forecast_7d_units - on_hand_units AS projected_shortfall_units
        FROM {table}
        WHERE (:store_id IS NULL OR store_id = CAST(:store_id AS INT))
          AND (:stockout_risk IS NULL OR lower(stockout_risk) = lower(:stockout_risk))
        ORDER BY CASE lower(stockout_risk) WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                 projected_shortfall_units DESC
        LIMIT 100
        """,
        {"store_id": store_id, "stockout_risk": risk},
    )


server = JsonRpcMcpApp(
    "bobabricks-inventory-mcp",
    [
        McpTool(
            name="assess_inventory_risk",
            description="Detect ingredient stockout risks and depletion shortfalls by store.",
            input_schema={
                "type": "object",
                "properties": {"store_id": {"type": "integer"}, "stockout_risk": {"type": "string"}},
            },
            handler=assess_inventory_risk,
        )
    ],
)


if __name__ == "__main__":
    server.run()
