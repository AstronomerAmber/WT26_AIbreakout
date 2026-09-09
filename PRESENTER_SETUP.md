# Presenter Setup

Complete these steps once before the event, and the quick auth refresh again on the
day of your talk. Everything targets the **fevm-worldtour-ai** Databricks workspace and
the app **bobabricks-store-ops-demo**.

## Access (should already be granted)

You need to be a member of the **`Agentbricks_speakers`** group. Membership gives you:

| Resource | Access | Purpose |
|---|---|---|
| App `bobabricks-store-ops-demo` | CAN_MANAGE | deploy / redeploy the agent |
| Genie space (store ops) | CAN_RUN | agent can query governed metrics |
| Catalog `worldtour_ai_catalog` | USE + SELECT | read the store-ops data |
| SQL warehouse | CAN_USE (via `users`) | run Genie/SQL |
| Confluence connection `system_ai_agent_atlassian_mcp` | USE (via `account users`) | company-context tool |

You also need to be able to **log in to** `https://fevm-worldtour-ai.cloud.databricks.com`.
If you can't reach the workspace or the app, ask the demo owner to confirm your group
membership and workspace access.

## One-time setup

1. **Databricks CLI** installed, with a profile named `fevm-worldtour-ai`:
   ```bash
   databricks auth login --host https://fevm-worldtour-ai.cloud.databricks.com --profile fevm-worldtour-ai
   ```

2. **Clone the repo** (public — no access needed):
   ```bash
   git clone https://github.com/AstronomerAmber/WT26_AIbreakout.git
   ```

3. **Authorize Confluence (one-time, per presenter).** The Confluence tool uses the
   managed connection with per-user OAuth — nobody can do this for you. Visit:
   `https://fevm-worldtour-ai.cloud.databricks.com/explore/connections/system_ai_agent_atlassian_mcp`
   → **Sign in / Authorize** (Atlassian). Without this, the post-upgrade Confluence
   answer fails with an auth error.

4. **Omnigent** installed (`omnigent` CLI) for the live upgrade step.

## Day-of refresh (tokens expire)

The Databricks token expires, so re-run the login before you present:
```bash
databricks auth login --host https://fevm-worldtour-ai.cloud.databricks.com --profile fevm-worldtour-ai
```
Then log in to Omnigent (browser flow):
```bash
omnigent login https://fevm-worldtour-ai.cloud.databricks.com/api/2.0/omnigent
omnigent host  --server https://fevm-worldtour-ai.cloud.databricks.com/api/2.0/omnigent
```

## You do NOT re-create any data

The catalog `worldtour_ai_catalog.bobabricks_store_ops` (12 tables), the Genie space,
the SQL warehouse, the StoreTime/OpsTask MCP apps, and the Confluence connection all
already exist in the shared workspace. **Never rebuild them.** Your only per-machine
job is to deploy the app code (below) — group membership already gives you read access
to the data.

## Reset to baseline before you present

The app `bobabricks-store-ops-demo` is **shared**, so whatever state the last person
deployed is what you'll see. The demo must **start Confluence-free** (Genie + StoreTime
+ OpsTask only) so the FY26-goals gap is real — adding Confluence is the live upgrade you
perform on stage. So reset to baseline right before your talk, every time.

## Deploy from your OWN workspace folder

Sync and deploy to **your own** personal home folder — substitute your login email for
`<your-email>`. (Do not use another presenter's folder; you can only write to your own.)
It's still the same shared app, so it deploys to the right target regardless of whose
folder it synced from.

```bash
cd WT26_AIbreakout
git checkout -- .   # clean baseline: Genie + StoreTime + OpsTask, Confluence OFF
databricks sync --full . /Workspace/Users/<your-email>/WT26_AIbreakout --profile fevm-worldtour-ai
databricks apps deploy bobabricks-store-ops-demo \
  --profile fevm-worldtour-ai \
  --source-code-path /Workspace/Users/<your-email>/WT26_AIbreakout
```

Confirm the app is **RUNNING** (not just "deploy SUCCEEDED"), then ask the agent
*"what tools do you have?"* — at baseline it should list **Genie, StoreTime, OpsTask**
only (no Confluence). Adding Confluence is the live upgrade you perform during the talk.
