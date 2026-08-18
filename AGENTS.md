# Bobabricks Demo Agent Instructions

These instructions apply to this repository. This repo targets the
**fevm-worldtour-ai** Databricks workspace (CLI profile `fevm-worldtour-ai`).

## Short-Demo Upgrade

When the user asks:

> For the Bobabricks store operations agent, can you add our FY26 goals and store playbooks as context? Please add the Atlassian Confluence MCP so the agent can pull from Confluence directly, and redeploy the app.

Treat that as the short-demo Confluence upgrade. Make only the small Confluence upgrade:

- Add the managed Atlassian/Confluence MCP to `agent-store-ops/mcp_servers.yaml`.
- Add exactly one new tool to `agent-store-ops/tools.yaml`: `search_confluence`.
- Set `CONFLUENCE_MCP_ENABLED=true` and `ATLASSIAN_MCP_URL` in both root app manifests: `app.yml` and `app.yaml`. In fevm-worldtour-ai the managed Atlassian MCP connection is `system_ai_agent_atlassian_mcp`, reached at:
  `https://fevm-worldtour-ai.cloud.databricks.com/api/2.0/mcp/external/system_ai_agent_atlassian_mcp`
- Preserve the existing baseline capabilities: Genie, StoreTime, OpsTask, and Lakebase sidebar/session context.
- Do not add long-demo features such as inventory risk, weekly regional briefing, task approvals, or scheduled workflow.

Notes for this workspace:
- The app must request OBO scopes `ai-gateway`, `genie`, `mcp.external` (set via `databricks apps update`); without `mcp.external` the Confluence MCP call fails.
- The managed Atlassian MCP is OAuth U2M — the demo user must have authorized the `system_ai_agent_atlassian_mcp` connection once (Catalog → Connections). The Confluence search tool uses the unified `search`/`fetch` tools (not the direct Confluence REST tools, which are blocked by the tenant IP allowlist).

## Deployment

This app must be deployed as the repo-root Databricks chat app. Do not infer a bundle-style deployment from `databricks.yml`. Do not deploy the `app/` directory; that is the Streamlit app, not the chat demo.

Before redeploying, ask:

```text
Approve redeploying bobabricks-store-ops-demo with the Confluence upgrade?
```

After approval, sync this repo to the workspace and deploy from that folder:

```bash
databricks sync --profile fevm-worldtour-ai . /Workspace/Users/amber.roberts@databricks.com/WT26_AIbreakout
databricks apps deploy bobabricks-store-ops-demo \
  --profile fevm-worldtour-ai \
  --source-code-path /Workspace/Users/amber.roberts@databricks.com/WT26_AIbreakout
```

Deployment guardrails:

- Use profile `fevm-worldtour-ai`, never `DEFAULT`.
- Do not run `databricks apps deploy --auto-approve`.
- Always deploy the app named `bobabricks-store-ops-demo`.
- Deploy from the synced workspace folder path, not `--source-code-path .`.
- Check deployment status after redeploying.
- Do not read app logs unless deployment fails or the app does not start.
