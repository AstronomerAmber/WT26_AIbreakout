# Bobabricks Store Operations Agent — Engineering Guide

These instructions apply to this repository. The live demo runs in the
**data-ai-lakehouse** Databricks workspace
(`https://data-ai-lakehouse.cloud.databricks.com`), reached with the CLI profile
`DEFAULT`. (Locally, `data-ai-lakehouse` is the same workspace; in a Databricks
sandbox only `DEFAULT` exists.)

IMPORTANT: the root `app.yaml` / `app.yml` committed in this repo contain
**fevm-worldtour-ai** values (warehouse, catalog, MCP URLs). They are wrong for
data-ai-lakehouse and must never be deployed there. The correct data-ai-lakehouse
manifests are the ones already in the workspace folder; always start from those
(see Deployment below).

## Adding Confluence Context

When the user asks:

> For the Bobabricks store operations agent, can you add our FY26 goals and store playbooks as context? Please add the Atlassian Confluence MCP so the agent can pull from Confluence directly, and redeploy the app.

Give the agent Confluence context by making only this small, scoped change:

- Add the managed Atlassian/Confluence MCP to `agent-store-ops/mcp_servers.yaml`.
- Add exactly one new tool to `agent-store-ops/tools.yaml`: `search_confluence`.
- Enable the connector in the app manifests by adding exactly these two env vars
  (to the workspace manifests, as described in Deployment — not the repo copies):
  - `CONFLUENCE_MCP_ENABLED` = `"true"`
  - `ATLASSIAN_MCP_URL` = `https://data-ai-lakehouse.cloud.databricks.com/api/2.0/mcp/external/system_ai_agent_atlassian_mcp`
- Preserve the existing baseline capabilities: Genie, StoreTime, OpsTask, and Lakebase sidebar/session context.
- Do not add out-of-scope features such as inventory risk, weekly regional briefing, task approvals, or scheduled workflow.

Notes for this workspace:
- The app already requests OBO scopes `ai-gateway`, `genie`, `mcp.external`; do not change them.
- The managed Atlassian MCP is OAuth U2M — the user must have authorized the `system_ai_agent_atlassian_mcp` connection once (Catalog → Connections). The Confluence search tool uses the unified `search`/`fetch` tools (not the direct Confluence REST tools, which are blocked by the tenant IP allowlist).

## Deployment

This app must be deployed as the repo-root Databricks chat app. Do not infer a bundle-style deployment from `databricks.yml`. Do not deploy the `app/` directory; that is the Streamlit app, not the chat app.

Before redeploying, ask:

```text
Approve redeploying bobabricks-store-ops-demo with the Confluence upgrade?
```

After approval, run these steps from the repo root. Substitute your own login
email for `<your-email>` (do not hardcode another user's home folder).

```bash
WS=/Workspace/Users/<your-email>/WT26_AIbreakout

# 1. Save the correct data-ai-lakehouse manifests BEFORE syncing (sync overwrites them).
databricks workspace export $WS/app.yaml --format AUTO --file /tmp/dal-app.yaml -p DEFAULT
databricks workspace export $WS/app.yml  --format AUTO --file /tmp/dal-app.yml  -p DEFAULT

# 2. Add ONLY the two Confluence env vars (above) to /tmp/dal-app.yaml and /tmp/dal-app.yml.
#    Change nothing else in them.

# 3. Sync the code changes (mcp_servers.yaml, tools.yaml).
databricks sync --full . $WS -p DEFAULT

# 4. Put the data-ai-lakehouse manifests back over the synced fevm ones.
databricks workspace import $WS/app.yaml --file /tmp/dal-app.yaml --format RAW --overwrite -p DEFAULT
databricks workspace import $WS/app.yml  --file /tmp/dal-app.yml  --format RAW --overwrite -p DEFAULT

# 5. Deploy.
databricks apps deploy bobabricks-store-ops-demo -p DEFAULT --source-code-path $WS
```

Use `--full`. A plain `databricks sync` can print "Initial Sync Complete" while
uploading nothing, in which case the deploy ships the previous `app.yaml` and
Confluence stays off even though the deploy reports SUCCEEDED.

Deployment guardrails:

- Use profile `DEFAULT` (data-ai-lakehouse).
- Never deploy the repo's own `app.yaml` / `app.yml` to data-ai-lakehouse.
- Do not run `databricks apps deploy --auto-approve`.
- Always deploy the app named `bobabricks-store-ops-demo`.
- Deploy from the synced workspace folder path, not `--source-code-path .`.
- Check deployment status after redeploying, then confirm the new config actually
  shipped: export `app.yaml` from the deployment snapshot path
  (`/Workspace/Users/<app-service-principal-id>/src/<deployment_id>/app.yaml`) and
  check it contains `CONFLUENCE_MCP_ENABLED` and `DATABRICKS_WAREHOUSE_ID` = `8561deb2ea8d55c9`.
  A SUCCEEDED status alone does not prove the upgrade shipped.
- Do not read app logs unless deployment fails or the app does not start.

## fevm-worldtour-ai (secondary workspace)

Only if the user explicitly asks for fevm-worldtour-ai: use profile
`fevm-worldtour-ai`, the repo's own `app.yaml` / `app.yml` as-is (they hold fevm
values), and `ATLASSIAN_MCP_URL` =
`https://fevm-worldtour-ai.cloud.databricks.com/api/2.0/mcp/external/system_ai_agent_atlassian_mcp`.
Skip the export/import steps.
