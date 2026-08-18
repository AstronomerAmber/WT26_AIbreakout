# Bobabricks Databricks App MCPs

This directory contains small Databricks App MCP services for the Store Operations demo. Each app directory is self-contained for Databricks App deployment; `shared/` is the source copy of the small JSON-RPC helper package.

## Apps

- `storetime` exposes `inspect_schedule` and `list_training_events` over `schedules`, `training_events`, and `storetime_shifts`.
- `opstask` exposes `list_existing_ops_tasks` and `create_ops_task` over `ops_tasks`.
- `inventory` exposes `assess_inventory_risk` over `inventory`. **Long version only** — the short demo keeps this disabled (`INVENTORY_APP_MCP_ENABLED=false`) and never surfaces Inventory as a tool. Deploy it only when running the `archive/long-version/` demo.

Each service exposes a JSON-RPC MCP endpoint at `/mcp` and a health check at `/`.

## Prerequisites

Provision the demo Delta tables first:

```bash
python3 scripts/provision_databricks_assets.py \
  --profile fevm-worldtour-ai \
  --warehouse-id 88fd32ee6d9438ac \
  --catalog bobabricks_demo \
  --schema store_ops
```

## Deploy

Create one Databricks App per MCP service. This workspace requires Databricks Apps to be Git-backed:

```bash
databricks apps create --json '{"name":"bobabricks-storetime-mcp","description":"Bobabricks StoreTime MCP","git_repository":{"provider":"github","url":"https://github.com/AstronomerAmber/WT26_AIbreakout.git"}}' --profile fevm-worldtour-ai
databricks apps create --json '{"name":"bobabricks-opstask-mcp","description":"Bobabricks OpsTask MCP","git_repository":{"provider":"github","url":"https://github.com/AstronomerAmber/WT26_AIbreakout.git"}}' --profile fevm-worldtour-ai
databricks apps create --json '{"name":"bobabricks-inventory-mcp","description":"Bobabricks Inventory MCP","git_repository":{"provider":"github","url":"https://github.com/AstronomerAmber/WT26_AIbreakout.git"}}' --profile fevm-worldtour-ai
```

If the app already exists, make sure the repository provider is normalized to `github`:

```bash
databricks apps update bobabricks-storetime-mcp --json '{"name":"bobabricks-storetime-mcp","description":"Bobabricks StoreTime MCP","git_repository":{"provider":"github","url":"https://github.com/AstronomerAmber/WT26_AIbreakout.git"}}' --profile fevm-worldtour-ai
databricks apps update bobabricks-opstask-mcp --json '{"name":"bobabricks-opstask-mcp","description":"Bobabricks OpsTask MCP","git_repository":{"provider":"github","url":"https://github.com/AstronomerAmber/WT26_AIbreakout.git"}}' --profile fevm-worldtour-ai
```

Deploy each app from Git after the MCP source has been committed and pushed to `main`:

```bash
databricks apps deploy bobabricks-storetime-mcp \
  --json '{"git_source":{"branch":"main","source_code_path":"mcp-apps/storetime"}}' \
  --profile fevm-worldtour-ai

databricks apps deploy bobabricks-opstask-mcp \
  --json '{"git_source":{"branch":"main","source_code_path":"mcp-apps/opstask"}}' \
  --profile fevm-worldtour-ai

databricks apps deploy bobabricks-inventory-mcp \
  --json '{"git_source":{"branch":"main","source_code_path":"mcp-apps/inventory"}}' \
  --profile fevm-worldtour-ai
```

If deployment fails with `No Git credential configured`, open Databricks User Settings > Git Integration and re-authorize GitHub for `https://github.com/AstronomerAmber/WT26_AIbreakout.git`. Workspace-file deployments are rejected in this workspace.

The app names match `agent-store-ops/mcp_servers.yaml` defaults.

## Smoke Test

After deployment, call each app health check and then the MCP `tools/list` method:

```bash
curl -X POST "$STORETIME_APP_URL/mcp" \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```
