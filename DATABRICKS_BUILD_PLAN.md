# Databricks Build Plan

This is the practical checklist for turning the WT26_AIbreakout scaffold into a Databricks-hosted demo.

## 1. Authenticate the Databricks CLI

Current local CLI is installed, but profiles must be valid before deployment.

```bash
databricks auth login --host <workspace-url> --profile <profile-name>
databricks auth profiles
```

Use the workspace where the Bobabricks demo assets, Genie space, Unity AI Gateway endpoint, Databricks-App MCPs, and Databricks App should live. For this demo, prefer the `fevm-worldtour-ai` CLI profile.

## 2. Provision Required Workspace Assets

Create or confirm these Databricks resources:

- SQL warehouse for store operations data.
- Genie space named `bobabricks_store_operations` or update `agent-store-ops/mcp_servers.yaml`.
- Unity AI Gateway endpoint named `bobabricks-store-ops` or update `agent-store-ops/agent.yaml`.
- App budget or usage policy for the guardrail demo moment.
- Databricks App MCP named `bobabricks-storetime-mcp` backed by demo Delta schedule/training tables.
- Databricks App MCP named `bobabricks-opstask-mcp` backed by demo Delta OpsTask tables.
- Optional Databricks App MCP named `bobabricks-inventory-mcp` — long version only (see `archive/long-version/`); the short demo keeps it disabled.

The MCP app source lives in `mcp-apps/`. For the short demo, deploy only StoreTime and OpsTask. Deploy Inventory only when running the long version, where inventory appears as a distinct tool.

## 3. Load Demo Data

Load the CSV/JSON files in `data/` into governed tables or demo-serving data locations:

- `data/store_metrics.csv`
- `data/schedules.csv`
- `data/inventory.csv`
- `data/ops_tasks.json`
- `data/confluence_playbooks.json` for local-only rehearsal fallback

For a live Genie demo, expose store metrics, training, customer experience, and first-pass inventory facts through tables that the Genie space can query. StoreTime and OpsTask should be real Databricks-App MCPs backed by demo Delta tables so the first pass has credible operational-tool integration without requiring external systems.

## 4. Configure External Context

Keep Confluence absent for `demo-start`: no Confluence MCP block in `agent-store-ops/mcp_servers.yaml`, no `search_confluence` entry in `agent-store-ops/tools.yaml`, and no Confluence env in the app manifest. During the live upgrade, add the real Databricks managed Atlassian/Confluence MCP connection used in the target environment:

- `CONFLUENCE_MCP_ENABLED=true`
- `ATLASSIAN_MCP_URL`
- `ATLASSIAN_MCP_BEARER_TOKEN` stored as a Databricks App secret named `atlassian_mcp_bearer_token`, not committed
- Required pages added to `agent-store-ops/mcp_servers.yaml`

Confirm the demo Bobabricks article/pages exist in the actual Confluence workspace:

- `FY26 Store Operations Goals`
- `Training Completion Operating Standard`
- `Inventory Stockout Escalation Playbook`
- `Pacific Region Weekly Review Playbook`

For the final WOW query, either keep inventory modeled in Genie or enable `INVENTORY_APP_MCP_ENABLED=true` with the optional `bobabricks-inventory-mcp` Databricks App.

## 5. Create the Databricks App

From this repo root:

```bash
cd /Users/amber.roberts/Documents/GitHub/WT26_AIbreakout
databricks apps create bobabricks-store-ops-demo \
  --description "Bobabricks Store Operations Agent app" \
  --profile <profile-name>
```

If demonstrating budget enforcement, include the workspace policy id supported by the environment:

```bash
databricks apps create bobabricks-store-ops-demo \
  --description "Bobabricks Store Operations Agent app" \
  --budget-policy-id <budget-policy-id> \
  --profile <profile-name>
```

## 6. Deploy the App Snapshot

Deploy from the repo root after environment/secrets are configured in the Databricks App settings. The root-level `app.yaml` starts `app/app.py` and keeps the agent/sample files available to the app runtime.

This workspace currently requires Databricks Apps deployments from Git. Commit and push the app changes first, then deploy the configured Git source:

```bash
cd /Users/amber.roberts/Documents/GitHub/WT26_AIbreakout
git push origin main

databricks apps deploy bobabricks-store-ops-demo \
  --profile <profile-name>
```

Use `databricks sync` only for supporting workspace files or MCP app source snapshots:

```bash
databricks sync . /Workspace/Users/<your-email>/WT26_AIbreakout \
  --profile <profile-name> \
  --exclude .git \
  --exclude .tmp
```

## 7. Validate the Demo Path

Before the live run:

```bash
python3 scripts/validate_demo.py
python3 scripts/generate_sample_briefing.py --region Pacific
```

In the deployed app, test:

```text
What tools do you have?
```

Then test the WOW query:

```text
Generate my weekly Pacific regional risk briefing and create follow-up tasks for high-severity items.
```

Expected behavior:

- Briefing includes store, severity, category, evidence, and recommended action.
- Issues use only `sales`, `labor`, `inventory`, `training`, or `customer_experience`.
- OpsTask creation pauses for explicit approval before writes.
- Post-approval response summarizes created task ids.

## 8. Demo Branch Flow

Use two branches if you want the live Codex upgrade moment:

```bash
git checkout -b demo-start
# keep Genie, StoreTime, and OpsTask available
# keep Confluence absent and Inventory MCP inactive for the live upgrade moment

git checkout main
git checkout -b demo-final
# add Confluence live; optionally enable Inventory MCP as a separate final-pass tool
```
