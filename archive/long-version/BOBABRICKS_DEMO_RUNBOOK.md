# Bobabricks Store Operations Demo Runbook

## Goal
Demonstrate an enterprise-grade Store Operations Agent built with OpenAI/GPT/Codex/Omnigent that evolves live from Q&A into an approval-governed operations workflow on Databricks.

## Narrative Arc
The demo should feel like a clear progression:

```text
answer questions → expose missing enterprise context → repair the agent live → redeploy → prove the fix → take governed action
```

The intentional live failure is not a broken UI. The baseline agent can answer store
operations questions from governed metrics and scheduling evidence, but it cannot fully
answer company-standard questions until Codex wires in the missing enterprise context.
That sets up a production-style repair: inspect the app and resources, change code/config,
validate, redeploy, show traces, then rerun the same question successfully.

## Useful Links
- Original demo reference: https://github.com/aravind-segu_data/store_ops_demo_aravind
- Target repo for new demo assets: https://github.com/amber-roberts_data/Omnigent_demos
- Databricks app templates: https://github.com/databricks/app-templates/tree/main

## 0. Show Architecture Diagram
Explain the architecture left to right:
- Bobabricks employee uses a chat interface.
- Store Operations Agent sits in the middle as the reasoning layer.
- Tools include Genie Agent, StoreTime, OpsTask, Confluence, Inventory MCP, and Lakebase Memory.
- Platform services include Agent Bricks, Genie Spaces, MLflow, Unity AI Gateway, Workflows, Databricks Apps, and Governance.

Message:

```text
This is not just a chatbot. It is an operational agent connected to governed enterprise data, internal tools, memory, and production platform services.
```

## 1. Pre-Demo Setup
- Authenticate the Databricks CLI with the `bigrock` profile.
- Sync and deploy BigRock assets into the Databricks workspace.
- Confirm the demo app, Genie space, SQL warehouse, Unity AI Gateway endpoint, MLflow experiment, and budget policy are available.
- For local trace generation only, export Databricks auth and MLflow settings before running the app:

```bash
export DATABRICKS_HOST=https://data-ai-lakehouse.cloud.databricks.com
export DATABRICKS_TOKEN=<personal-access-token>
export MLFLOW_TRACKING_URI=databricks
export MLFLOW_REGISTRY_URI=databricks-uc
export MLFLOW_EXPERIMENT_ID=1247045021302485
```

- The deployed Databricks App should set `MLFLOW_TRACKING_URI`, `MLFLOW_REGISTRY_URI`, and `MLFLOW_EXPERIMENT_ID` in `app.yml`. Do not commit local access tokens.
- Decide the live-upgrade shape:
  - Recommended first pass: real Genie for Bobabricks metrics, real Databricks-App MCPs for StoreTime and OpsTask, real Lakebase memory, Confluence disabled, and inventory represented in Genie.
  - Final WOW pass: enable the real Databricks managed Atlassian/Confluence MCP, pointed at the demo Bobabricks article in the actual Confluence workspace; optionally enable a small `mcp-inventory` Databricks App if inventory should appear as a separate tool.

## 2. Start With Baseline Agent
Open the Bobabricks Store Operations Agent app.

Ask:

```text
What tools do you have?
```

Expected baseline tools:
- Genie Agent for governed store operations metrics.
- StoreTime for labor and scheduling diagnostics.
- OpsTask for tickets and task tracking.
- Current time utility.
- Lakebase memory.

Keep Confluence and the optional Inventory MCP missing or inactive if you want the live upgrade moment.

Message:

```text
The baseline agent has operational systems, but it does not yet have the corporate operating-standard source attached.
```

## 3. Show Basic Store Ops Q&A
Ask:

```text
Show average versus actual training hours for my Pacific stores and flag any stores falling behind.
```

Expected result:
- Agent identifies Store 104 or a similar training risk.
- Agent gives a short table or bullet summary.

Message:

```text
The agent can reason over governed operational metrics.
```

## 4. Show Diagnostic Follow-Up
Ask:

```text
Why is Store 104 behind on training? Is it a scheduling problem or a completion problem?
```

Expected result:
- Agent combines Genie and StoreTime.
- Agent explains that training shifts were converted to service coverage during rush windows.

Message:

```text
The agent can combine analytics with operational systems.
```

## 5. Expose The Gap
Ask:

```text
What are our FY26 training goals, and how does Store 104 stack up?
```

Expected result:
- Baseline agent fails, answers incompletely, or gives a generic response because it lacks Confluence/company context.
- It may know Store 104 is behind from metrics and StoreTime, but it should not be able to cite the FY26 training target, operating standard, or company playbook evidence.

Message:

```text
This is a realistic enterprise-agent failure: the agent has operational data, but not the governed company context it needs to answer the business question correctly. This is where Codex upgrades the production app.
```

## 6. Run The Codex Upgrade
In Codex/Omnigent, ask it to upgrade `agent-store-ops`.

Use the prompt captured in `CODEX_UPGRADE_PROMPT.txt`.

Suggested live prompt:

```text
The Bobabricks agent can answer store metrics and StoreTime diagnostics, but it cannot answer FY26 operating-standard questions because the Confluence context is missing. Update the app/agent so the FY26 goals question uses the real Confluence MCP/company playbook context, preserves StoreTime and Genie evidence, enables MLflow tracing, validates locally, commits, pushes, and redeploys the Databricks App.
```

The upgrade adds:
- Real managed Confluence MCP access to the demo Bobabricks operating article.
- Inventory risk analysis.
- Risk categories.
- Weekly regional briefing format.
- Approval-gated OpsTask creation.
- App shortcut: `Generate Weekly Regional Briefing`.
- MLflow/OpenAI autologging so model calls and latency can be inspected while the app redeploys.

## 7. Show The Diff
Highlight changes in:
- `agent-store-ops/mcp_servers.yaml`
- `agent-store-ops/tools.yaml`
- `agent-store-ops/system_prompt.md`
- `agent-store-ops/policies.yaml`
- `app/app.py`

Message:

```text
Codex changed config, tools, policy, prompt, and app UX together.
```

## 8. Redeploy In Databricks
Deploy the upgraded app from the repo root:

```bash
cd /Users/amber.roberts/Documents/GitHub/BigRock
git push origin main
databricks apps deploy bobabricks-store-ops-demo --profile bigrock
```

The target workspace currently requires Databricks Apps deployments from Git. Use `databricks sync` only for supporting workspace files or MCP app source snapshots, not for the main app deployment.

While deployment runs, show:
- MLflow traces from earlier questions and the failed FY26 prompt.
- Unity AI Gateway model/tool configuration.
- Unity AI Gateway budget and usage guardrails.
- Databricks Apps deployment logs showing the Git-backed release.

## 9. Confirm Upgraded Agent
Return to the app.

Ask:

```text
What tools do you have?
```

Confirm it now has:
- Genie Agent.
- StoreTime.
- OpsTask.
- Confluence through the real Databricks managed MCP.
- Inventory MCP, if enabled as the final-pass separate tool.
- Current time utility.
- Lakebase memory.

Then rerun the failed question:

```text
What are our FY26 training goals, and how does Store 104 stack up?
```

Expected upgraded result:
- Agent cites the FY26 training completion target and operating standard from Confluence.
- Agent compares Store 104 against the target using Genie/store metrics.
- Agent cites StoreTime evidence for converted training hours and rush-window coverage.
- Agent recommends a governed follow-up without creating an OpsTask until approval.

## 10. Run The WOW Query
Ask:

```text
Generate my weekly Pacific regional risk briefing and create follow-up tasks for high-severity items.
```

Expected output includes:
- Store 104: training/labor risk.
- Store 117: inventory stockout risk.
- Store 122: customer experience risk.
- Required fields: store, severity, category, evidence, recommended action.

## 11. Approval Moment
Agent says something like:

```text
I found 2 high-severity risks. Do you approve creating OpsTask tickets?
```

Action:
- Click approve.
- Agent creates only approved tasks.

Message:

```text
The agent can take action, but governed write operations require approval.
```

## 12. Show Background / Scheduled Workflow
Show a weekly report workflow:

```text
Generate Pacific regional risk briefing every Monday at 7 AM.
```

Explain:
- Long-running analysis can run in background mode.
- Scheduled jobs can use the same agent/tools.
- Traces still land in MLflow.

Message:

```text
The same governed agent can run interactively or as a scheduled operating workflow.
```

## 13. Show Budget Guardrail
Open Unity AI Gateway budget/policy controls.

Show threshold, warning, block behavior, or a prior recorded event.

Message:

```text
Cost control is enforced at the platform layer without changing app logic.
```

## 14. Wrap
Closing story:

```text
We started with a Q&A agent, used Codex to upgrade it live, connected it to company context and operational systems, and turned it into an approval-gated workflow running on Databricks.
```

## Backup Prompts
- `Summarize Pacific store risks this week by severity.`
- `Classify Store 104 issues as sales, labor, inventory, training, or customer experience with evidence.`
- `Propose actions only; do not create tasks yet.`
- `Now create tasks for high-severity items.`

## Success Checklist
- [ ] Pre-demo Databricks resources confirmed.
- [ ] Baseline Q&A shown.
- [ ] Diagnostic follow-up shown.
- [ ] Company-context gap exposed.
- [ ] Live Codex upgrade shown.
- [ ] Code diff shown.
- [ ] Redeploy completed.
- [ ] Post-upgrade WOW query succeeds.
- [ ] Approval-gated write shown.
- [ ] Memory behavior shown.
- [ ] Budget guardrail shown.
- [ ] MLflow trace shown.
