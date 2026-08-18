# Bobabricks Store Operations Demo

A self-contained demo scaffold for a Bobabricks Store Operations Agent that starts as a Q&A agent, hits a real question it can't answer, and gets upgraded live with Codex/Omnigent by adding one tool: the managed Atlassian/Confluence MCP.

The demo script lives in:

- `script.md` — the short demo script (the active version).
- `CODEX_UPGRADE_PROMPT.txt` — the one-tool upgrade prompt used in the live fix.
- `archive/long-version/` — the full version, with the weekly regional briefing, the approval moment, and the scheduled workflow, plus its runbook and upgrade prompt.

## Demo Shape

The repo supports a live Codex/Omnigent-style upgrade moment:

- `agent-store-ops/` contains the agent configuration, prompt, tool contracts, and policy notes.
- `app/` contains the Streamlit Databricks app plus local service adapters for the tool-status view and deterministic Q&A behavior. `scripts/start_app.py` runs the deployed React chat frontend against the `agent_server` backend.
- `data/` contains sample Bobabricks operating data for deterministic local/demo behavior and Delta table seeding.
- `mcp-apps/` contains Databricks App MCP services for StoreTime and OpsTask. An Inventory MCP is also present but is disabled for the short demo (`INVENTORY_APP_MCP_ENABLED=false`) and only used by the long version.
- `scripts/` contains local validation helpers.

## The Spine

1. Baseline agent has Genie, StoreTime, and OpsTask — no Confluence.
2. It answers store-performance and diagnostic questions (e.g., Store 104 training).
3. It cannot answer "What are our FY26 training goals, and how does Store 104 stack up?" because it has no company-context tool.
4. Codex adds the managed Atlassian/Confluence MCP and redeploys.
5. The same question now answers fully, grounded in Confluence and compared against Genie/StoreTime.

## Key Demo Query

```text
What are our FY26 training goals, and how does Store 104 stack up?
```

Expected behavior:

1. Before the upgrade: the agent says plainly that it has no tool exposing company training goals.
2. After the upgrade: the agent cites the FY26 training completion target from Confluence and compares Store 104 against it using Genie/StoreTime evidence.

## Local Smoke Test

```bash
python3 scripts/validate_demo.py
python3 -m unittest tests/test_store_ops.py
```

The app uses CSV/JSON-backed adapters in `app/services/store_ops.py` for deterministic demo behavior.

## Databricks App MCPs

The StoreTime and OpsTask MCP services live in `mcp-apps/`. Deploy them as separate Databricks Apps named `bobabricks-storetime-mcp` and `bobabricks-opstask-mcp` after provisioning the demo Delta tables. See `mcp-apps/README.md` for commands. The `mcp-apps/inventory` service is only needed for the long version.

## Notes

This scaffold is oriented around a real Databricks-first demo path. Local sample data remains available for deterministic rehearsal. The baseline app expects Genie plus the StoreTime and OpsTask Databricks-App MCPs; Lakebase can appear as app/session context in the sidebar, but it is not listed as an agent tool. The managed Atlassian/Confluence MCP is enabled during the live Codex/Omnigent upgrade.

## Long Version

To run the full demo (weekly regional briefing, approval-gated OpsTask creation, Inventory MCP as its own tool, and a scheduled workflow), see `archive/long-version/`. Re-enabling those surfaces requires `INVENTORY_APP_MCP_ENABLED=true` and restoring the briefing/approval UI blocks.
