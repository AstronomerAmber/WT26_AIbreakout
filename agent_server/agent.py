import functools
import json
import logging
import os
import re
from contextlib import AsyncExitStack
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator
from uuid import uuid4

import httpx
import mlflow
from agents import Agent, FunctionTool, ModelSettings, RunContextWrapper, Runner, function_tool, set_default_openai_api, set_default_openai_client
from agents.tracing import set_trace_processors
from databricks.sdk import WorkspaceClient
from databricks_openai import AsyncDatabricksOpenAI
from databricks_openai.agents import AsyncDatabricksSession, McpServer
from fastapi import HTTPException
from mlflow.genai.agent_server import get_request_headers, invoke, stream
from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentResponse, ResponsesAgentStreamEvent

from agent_server.utils import (
    deduplicate_input,
    get_databricks_host_from_env,
    get_session_id,
    lakebase_access_message,
    lakebase_config,
    process_agent_stream_events,
)

set_default_openai_client(AsyncDatabricksOpenAI())
set_default_openai_api("chat_completions")
set_trace_processors([])


def _configure_uc_trace_location() -> None:
    """Bind the active MLflow experiment to a Unity Catalog trace location so traces
    are governed and queryable in UC (and appear in UC-backed trace views), instead of
    the legacy workspace/DBFS trace store. No-op unless the UC trace env vars are set.

    trace_location can only be set when the experiment is created, so MLFLOW_EXPERIMENT_NAME
    must point at a new experiment name (not a pre-existing legacy one)."""
    catalog = os.environ.get("MLFLOW_TRACE_UC_CATALOG")
    schema = os.environ.get("MLFLOW_TRACE_UC_SCHEMA")
    experiment_name = os.environ.get("MLFLOW_EXPERIMENT_NAME")
    if not (catalog and schema and experiment_name):
        return
    from mlflow.entities.trace_location import UnityCatalog

    mlflow.set_experiment(
        experiment_name=experiment_name,
        trace_location=UnityCatalog(
            catalog_name=catalog,
            schema_name=schema,
            table_prefix=os.environ.get("MLFLOW_TRACE_UC_TABLE_PREFIX", "bobabricks"),
        ),
    )


try:
    _configure_uc_trace_location()
except Exception as exc:  # non-fatal: fall back to default tracing so the app still starts
    logging.getLogger(__name__).warning(
        "UC trace location setup failed; continuing with default tracing: %s", exc, exc_info=True
    )

mlflow.openai.autolog()
logging.getLogger("mlflow.utils.autologging_utils").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


def _enrich_agent_spans() -> None:
    try:
        from mlflow.openai import _agent_tracer as tracer

        orig_name = tracer._get_span_name
        orig_parse = tracer._parse_span_data

        def friendly_tool_name(value):
            if not value:
                return value
            text = str(value)
            if re.fullmatch(r"query_space_[0-9a-f]+", text):
                return "Genie Agent [bobabricks_store_operations]"
            if re.fullmatch(r"poll_response_[0-9a-f]+", text):
                return "Genie Agent [bobabricks_store_operations]"
            if text in {"inspect_schedule", "list_training_events"}:
                return "MCP[bobabricks-storetime-mcp]"
            if text in {"list_existing_ops_tasks", "create_ops_task"}:
                return "MCP[bobabricks-opstask-mcp]"
            return value

        def name(span_data):
            span_type = getattr(span_data, "type", "")
            if span_type == "turn":
                return f"Turn #{getattr(span_data, 'turn', '?')}"
            if span_type == "mcp_tools":
                return f"MCP: list tools ({getattr(span_data, 'server', '?')})"
            existing = getattr(span_data, "name", None)
            existing = friendly_tool_name(existing)
            return existing if existing else orig_name(span_data)

        def parse(span_data):
            inputs, outputs, attributes = orig_parse(span_data)
            attributes = dict(attributes or {})
            span_type = getattr(span_data, "type", "")
            if span_type == "mcp_tools":
                tools = [
                    friendly_tool_name(tool)
                    for tool in list(getattr(span_data, "result", None) or [])
                ]
                attributes["server"] = getattr(span_data, "server", None)
                attributes["tool_count"] = len(tools)
                outputs = {"tools": tools}
            elif span_type == "turn":
                attributes["turn"] = getattr(span_data, "turn", None)
                attributes["agent"] = getattr(span_data, "agent_name", None)
                if getattr(span_data, "usage", None):
                    attributes["usage"] = span_data.usage
            if attributes.get("name"):
                attributes["name"] = friendly_tool_name(attributes["name"])
            if isinstance(inputs, dict):
                inputs = {
                    key: friendly_tool_name(value) if key in {"name", "tool", "tool_name"} else value
                    for key, value in inputs.items()
                }
            return inputs, outputs, attributes

        tracer._get_span_name = name
        tracer._parse_span_data = parse
    except Exception:
        logger.debug("Could not enrich openai-agents spans.", exc_info=True)


_enrich_agent_spans()

MODEL = os.getenv("AGENT_MODEL", "databricks-gpt-5")
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID", "01f1968067e81bd09eacb0d88bcc57de")
STORETIME_MCP_URL = os.getenv("STORETIME_MCP_URL", "https://bobabricks-storetime-mcp-7474657163903557.aws.databricksapps.com/mcp")
OPSTASK_MCP_URL = os.getenv("OPSTASK_MCP_URL", "https://bobabricks-opstask-mcp-7474657163903557.aws.databricksapps.com/mcp")
ATLASSIAN_MCP_URL = os.getenv("ATLASSIAN_MCP_URL")
ATLASSIAN_OFF_SENTINELS = {"", "off", "none", "disabled", "false"}
ATLASSIAN_FRIENDLY_NAME = "Atlassian Confluence"
CONFLUENCE_MCP_ENABLED = os.getenv("CONFLUENCE_MCP_ENABLED", "false").strip().lower() in {"1", "true", "on", "yes"}
USE_SDK_MCP_SERVERS = os.getenv("USE_SDK_MCP_SERVERS", "false").strip().lower() in {"1", "true", "on", "yes"}
CONFLUENCE_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "data" / "confluence_playbooks.json"

AGENT_INSTRUCTIONS = """\
You are the Bobabricks Store Operations Agent for regional store leaders.

Use the attached tools directly:
- Genie Agent for governed Bobabricks store metrics, training completion, wait time, and regional performance.
- StoreTime for schedules, training blocks, converted hours, and coverage reasons.
- OpsTask for existing follow-up tickets and task tracking.
- Confluence/Atlassian for FY26 goals, operating standards, and playbooks when Confluence is connected.

Do not invent stores, metrics, targets, task ids, or policy. Every store number,
store name, schedule fact, and task in an answer must come from a tool call made
in this turn. Never answer store data from memory, from earlier turns, or from
these instructions; if a question needs store data, call the tool even if you
think you know the answer. Call read-only tools without asking the user first;
only create/write tools need approval. If a Genie query returns "Query is still
processing", call its poll_response tool with the returned conversation_id and
message_id before answering, and keep polling until it returns data. Attribute
every number only to the tool whose output contained it; when Genie and
StoreTime report different numbers, show each with its own source instead of
merging them. If the tool you need fails or is not attached this
turn, say in one short line that that data source did not respond, and do not
fill in the numbers. Otherwise keep demo answers natural: do not add
missing-source diagnostics or reconnect instructions unless the user explicitly
asks about tool health. Lead with the answer, then give the evidence
compactly. Preserve markdown tables returned by tools for training-hour
comparisons.
Never put source tags in the answer: no bracketed tags such as "[Genie]" or
"[StoreTime inspect_schedule]", no "— Genie Agent" suffixes, no "Evidence:
Genie Agent ..." or "Evidence (StoreTime):" lines, and no tool or space names.
The app adds the source line. When Genie and StoreTime return the same figure,
state it once. Only if they disagree, show both values in one bullet, for
example "42 scheduled hours (StoreTime) vs 40 (Genie)".

When asked what tools you have, answer from the configured Bobabricks tool
context in a clean demo style. Do not call a tool for this question. Do not use
the phrase "Bobabricks tool inventory." Do not use "Available" or "Unavailable"
headings. Do not add temporary-availability caveats unless the user's request is
blocked by a failed tool call. List only the connected data and MCP tools; do not
list Confluence/Atlassian unless Confluence is connected. Never list
Lakebase memory or a current-time utility as tools.
Use one compact markdown table and normal body text only. Do not use markdown
headings, bold labels, bullet lists, or repeated "what it contains / what it can
do / what it cannot do" sections. The table columns should be: Tool, Name,
Contains, Can do, Cannot do. Keep each cell short enough to scan.
For the baseline state, use these rows:
- Tool Genie Agent; Name bobabricks_store_operations; Contains governed store
  metrics, region, training completion, scheduled/completed hours, wait time;
  Can do analytics, comparisons, completion tables; Cannot do tasks, schedule
  updates, approvals, or policy.
- Tool StoreTime; Name bobabricks-storetime-mcp; Contains schedules, protected
  training blocks, completed/converted hours, coverage reasons; Can do training
  root-cause diagnostics; Cannot change schedules or create tasks.
- Tool OpsTask; Name bobabricks-opstask-mcp; Contains follow-up lookup and task
  creation tools; Can list follow-ups and create tasks after approval; Cannot
  create silently or diagnose root cause alone.

For Bobabricks demo questions, prefer compact answer-first output. Do not print a
separate hardcoded "Tool call order" section; the trace is the source of truth for
tool order. If asked about OpsTask creation, describe what you would create and wait
for explicit approval before calling a create/write tool.

# Demo response style
Keep responses polished and easy to scan. Use the cleaner demo format:
- Start with a one-sentence summary.
- For store comparisons, use a compact markdown table with clear columns.
- Use status markers in tables and callouts: 🚩 for behind/high risk, ⚠️ for watch,
  ✅ for on track, and 🧋 only when referring to Bobabricks as a brand.
- For training-hour questions, include regional averages/totals before the table
  when the tools return enough data to compute them.
- For training-hour comparison or Store 104 training diagnostics, always use both
  Genie and StoreTime when available. If Genie returns no rows for a requested
  window, immediately query StoreTime/training events and answer from StoreTime
  rows before saying data is missing. Prefer the most recent period returned by
  the tools; do not invent a stricter date window than the user asked for.
- Interpret "average versus actual training hours" as scheduled/target training
  hours versus actual/completed training hours. Do not compare actual hours to
  the regional average as the behind/on-track test. Assign each store's marker
  from completed hours divided by scheduled/target hours, using exactly these
  bands: 95% or more is ✅ on track (so 39 of 40 is ✅); 80% to under 95% is ⚠️
  watch (so 37 of 40 is ⚠️); under 80% is 🚩 behind (so 28 of 42 is 🚩). Stores
  with the same hours always get the same marker. When the user asks to "flag
  any stores falling behind," list only 🚩 stores as flagged.
- For the question "Show average versus actual training hours for my Pacific
  stores and flag any stores falling behind", keep the visible answer short:
  one summary sentence, then one table with every Pacific store returned, one
  row per store, ordered 🚩 first, then ⚠️, then ✅. Columns: Store, Scheduled
  hrs, Completed hrs, Status. Nothing after the table: no "Flagged store",
  "Also in range", or "Watch" lists repeating table rows, no Notes section,
  root-cause analysis, next steps, "if you want" offers, or mention of empty
  StoreTime results.
- For Store 104 "why", "behind", or "falling behind" training questions in the
  upgraded state, use Confluence for the company goal/standard first, then use
  StoreTime for schedule/training evidence and Genie when available for the
  completion readout. The complete answer is the comparison: company standard
  from Confluence plus Store 104's scheduled, completed, and converted training
  hours as returned by StoreTime, and its training completion readout as
  returned by Genie.
- For FY26 goals, company training goals, operating standards, or playbook
  questions, use Confluence for the goal/policy context. Then compare those
  goals to Store 104's Genie and StoreTime evidence. If Confluence is not
  connected, you have no source for the company goal: do not state, paraphrase,
  summarize, or infer any FY26 goal, target, percentage, or operating standard,
  not even a generic one such as "complete scheduled training as planned" or
  "keep conversion to coverage minimal". Genie and StoreTime hold store
  metrics, not company goals: ask Genie only for Store 104's metrics, and never
  present a company-wide total or average as an FY26 goal, readout, benchmark,
  or standard, or say Store 104 is behind one. Answer the operational part only, with
  Store 104's status framed against its own schedule evidence rather than
  against a goal, and add one short caveat after the evidence: "I don't have the
  official company training goal connected yet."
  Do not make missing company context the headline. Do not claim Store 104 data
  is missing. Do not write "Short answer", "What's missing", "What I do have",
  "share the FY26 goals", "reconnect Confluence", or phrases like "I'm
  answering from Genie and StoreTime data only".
- For the final demo question "What are our FY26 training goals, and how does
  Store 104 stack up?", always call Genie and StoreTime for Store 104 before
  answering, whether or not Confluence is connected. Read-only tools never need
  the user's permission: never ask whether to fetch data, just fetch it. Do not
  include a recommendation or next step unless the user asks for one. When Confluence is connected, use this structure: one
  sentence with the goal and Store 104 status, then 2-3 bullets with the
  evidence. When Confluence is not connected, the opening sentence states
  Store 104's training status only and names no goal.
- For follow-up action questions such as "What should I do next?" or "What
  should I do about Store 104?", call Confluence for the training playbook and
  StoreTime for Store 104 schedule/conversion context before answering. Then
  provide the operational next step in this exact compact format:
  "Recommended next steps:"
  1. "Add coverage:" Use the StoreTime district schedule and partner availability
     view to identify available coverage from a nearby store, ideally a
     cross-trained partner or shift lead, or add one extra rush-window floor
     coverage shift in StoreTime.
  2. "Protect training:" Re-book the missed training block outside peak hours so
     the training-coded partner can stay in training.
  3. "Confirm ownership:" Have the manager confirm the coverage plan with the
     district scheduler.
  4. "Make it repeatable:" Turn this into a weekly training-risk report that
     checks each store against FY26 completion and utilization goals, flags
     stores below target, and highlights schedule conversions that need action.
  Do not create an OpsTask or ask for approval in this short demo flow unless
  the user explicitly asks to create a follow-up task.
- Keep follow-up explanation to 2-4 bullets. Avoid long missing-source sections
  unless the user explicitly asks why a tool failed.
- Do not write a "Source:" or "Sources:" line yourself. The app appends one
  after your answer, built from the tools that actually ran this turn.
  Do not expose raw table names, MCP tool ids, or generated tool names unless the
  user explicitly asks for technical details.
"""

CONTEXT_INSTRUCTIONS = """\

# Company policy & documentation
Use Confluence as the source of truth for FY26 training goals, operating standards,
thresholds, and required actions. Always ground store metrics in Genie or StoreTime.
For any user question containing "FY26", "training goals", "company goals",
"operating standards", "playbook", "stack up", "falling behind", "behind on
training", "what should I do", "recommended next steps", "next steps", or
"why is Store 104 behind", call the Confluence tool before answering. For action
or next-step questions about Store 104, also call StoreTime before answering so
the recommendation is grounded in the current schedule/conversion context. Do
not write a source line or Confluence link yourself; the app appends the
Confluence page link from the search_confluence result.
When asked what tools you have, the app is now in the upgraded Confluence state.
Answer with exactly these four rows in one compact markdown table:
- Tool Genie Agent; Name bobabricks_store_operations; Contains governed store
  metrics, region, training completion, scheduled/completed hours, wait time;
  Can do analytics, comparisons, completion tables; Cannot do tasks, schedule
  updates, approvals, or policy.
- Tool StoreTime; Name bobabricks-storetime-mcp; Contains schedules, protected
  training blocks, completed/converted hours, coverage reasons; Can do training
  root-cause diagnostics; Cannot change schedules or create tasks.
- Tool OpsTask; Name bobabricks-opstask-mcp; Contains follow-up lookup and task
  creation tools; Can list follow-ups and create tasks after approval; Cannot
  create silently or diagnose root cause alone.
- Tool Confluence; Name managed Atlassian MCP; Contains FY26 goals, operating
  standards, training playbooks; Can do company context lookup; Cannot change
  store data or tasks.
"""


@function_tool
def get_current_time() -> str:
    """Get the current date and time in ISO 8601 format."""
    return datetime.now().isoformat()


def _genie_mcp_url() -> str:
    return f"{get_databricks_host_from_env()}/api/2.0/mcp/genie/{GENIE_SPACE_ID}"


def _atlassian_url() -> str:
    if not CONFLUENCE_MCP_ENABLED:
        return ""
    if ATLASSIAN_MCP_URL is None:
        return ""
    if ATLASSIAN_MCP_URL.strip().lower() in ATLASSIAN_OFF_SENTINELS:
        return ""
    return ATLASSIAN_MCP_URL


class DirectMcpClient:
    def __init__(self, url: str, token: str, timeout: float = 30.0) -> None:
        self.url = url
        self.token = token
        self.session_id: str | None = None
        self._next_id = 1
        self._client = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self) -> "DirectMcpClient":
        await self.initialize()
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Mcp-Protocol-Version": "2025-03-26",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _parse_body(self, response: httpx.Response) -> dict[str, Any]:
        content_type = response.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            for raw in response.text.splitlines():
                if raw.startswith("data:"):
                    payload = raw[len("data:"):].strip()
                    if payload:
                        return json.loads(payload)
            raise RuntimeError(f"MCP response did not include a JSON-RPC frame: {response.text[:300]!r}")
        return response.json()

    async def _send(self, method: str, params: dict[str, Any] | None = None, expect_response: bool = True):
        body: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if expect_response:
            body["id"] = self._next_id
            self._next_id += 1
        if params is not None:
            body["params"] = params
        response = await self._client.post(self.url, headers=self._headers(), json=body)
        if method == "initialize":
            self.session_id = response.headers.get("Mcp-Session-Id")
        if response.status_code >= 400:
            raise RuntimeError(f"MCP {method} HTTP {response.status_code}: {response.text[:400]}")
        if not expect_response:
            return None
        return self._parse_body(response)

    async def initialize(self) -> None:
        await self._send(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "bobabricks-direct-client", "version": "0.1"},
            },
        )
        await self._send("notifications/initialized", expect_response=False)

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self._send("tools/list", {})
        if result is None or "error" in result:
            raise RuntimeError(f"MCP tools/list error: {result}")
        return result.get("result", {}).get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        result = await self._send("tools/call", {"name": name, "arguments": arguments})
        if result is None:
            return json.dumps({"error": "empty response"})
        if "error" in result:
            return json.dumps({"error": result["error"]})
        inner = result.get("result", {})
        content = inner.get("content")
        if isinstance(content, list):
            chunks = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    chunks.append(item.get("text", ""))
                else:
                    chunks.append(json.dumps(item) if isinstance(item, dict) else str(item))
            if chunks:
                return "\n".join(chunks)
        return json.dumps(inner)


def _sanitize_schema(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _sanitize_schema(v) for k, v in obj.items() if k != "$schema"}
    if isinstance(obj, list):
        return [_sanitize_schema(item) for item in obj]
    return obj


def _make_function_tool(client: DirectMcpClient, meta: dict[str, Any]) -> FunctionTool:
    tool_name = meta["name"]
    schema = _sanitize_schema(meta.get("inputSchema") or {"type": "object", "properties": {}})

    async def _invoke(ctx: RunContextWrapper, args_json: str, _tool: str = tool_name) -> str:
        try:
            args = json.loads(args_json) if args_json else {}
        except Exception:
            args = {}
        try:
            return await client.call_tool(_tool, args)
        except Exception as exc:
            return f"Tool error ({_tool}): {type(exc).__name__}: {exc}"

    return FunctionTool(
        name=tool_name,
        description=meta.get("description") or tool_name,
        params_json_schema=schema,
        on_invoke_tool=_invoke,
        strict_json_schema=False,
    )


def _make_confluence_search_tool(client: DirectMcpClient, tool_metas: list[dict[str, Any]]) -> FunctionTool:
    names = [str(meta.get("name", "")) for meta in tool_metas]
    names_lower = {name.lower(): name for name in names}

    # Tool preference order. The managed Atlassian MCP exposes both direct
    # Confluence REST tools (searchConfluenceUsingCql/getConfluencePage) and the
    # cross-product Rovo tools (search/fetch). On tenants with a Confluence IP
    # allowlist, the direct REST tools fail ("permission to connect from this IP
    # address") because they hit the tenant host, while search/fetch go through
    # api.atlassian.com and work. Prefer the unified `search` here.
    search_tool = (
        names_lower.get("search_confluence_pages")
        or names_lower.get("search")
        or next((name for name in names if "search" in name.lower()), "")
    )
    fetch_tool = names_lower.get("fetch")

    async def _invoke(ctx: RunContextWrapper, args_json: str) -> str:
        try:
            args = json.loads(args_json) if args_json else {}
        except Exception:
            args = {}

        query = str(args.get("query", "")).strip()
        limit = int(args.get("limit", 5) or 5)
        if not search_tool:
            return "Tool error (search_confluence): Atlassian Confluence MCP did not expose a search tool."
        try:
            raw = await client.call_tool(search_tool, {"query": query, "limit": limit})
        except Exception as exc:
            return f"Tool error (search_confluence): {type(exc).__name__}: {exc}"

        # When the unified `search` tool is used, results carry only a short
        # snippet. Fetch the full body of the top Confluence page(s) so the agent
        # can ground on the complete FY26 goals/standards text.
        if not (search_tool.lower() == "search" and fetch_tool):
            return raw
        try:
            parsed = json.loads(raw)
        except Exception:
            return raw
        results = parsed.get("results") if isinstance(parsed, dict) else None
        if not isinstance(results, list):
            return raw
        fetched = []
        # Carry the page title/url of every page we actually read so the agent can
        # render a clickable citation instead of a bare "Confluence" source label.
        citations = []
        for result in results:
            if not isinstance(result, dict):
                continue
            result_id = str(result.get("id", ""))
            if ":page/" not in result_id:
                continue
            try:
                fetched.append(await client.call_tool(fetch_tool, {"id": result_id}))
            except Exception:
                continue
            url = str(result.get("url", "")).strip()
            if url:
                citations.append({"title": str(result.get("title", "")).strip(), "url": url})
            if len(fetched) >= 2:
                break
        if not fetched:
            return raw
        return json.dumps({"search_results": parsed, "pages": fetched, "citations": citations})

    return FunctionTool(
        name="search_confluence",
        description="Search Atlassian Confluence for Bobabricks FY26 goals, operating standards, and store playbooks.",
        params_json_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search text for FY26 goals, training standards, or store playbooks.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of Confluence results to return.",
                    "default": 5,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        on_invoke_tool=_invoke,
        strict_json_schema=False,
    )


def _atlassian_token() -> str:
    try:
        headers = get_request_headers() or {}
        token = headers.get("x-forwarded-access-token")
        if not token:
            authorization = headers.get("authorization", "")
            if authorization.lower().startswith("bearer "):
                token = authorization.split(" ", 1)[1]
        if token:
            return token
    except Exception:
        pass
    return os.getenv("ATLASSIAN_MCP_BEARER_TOKEN", "")


def _databricks_mcp_token() -> str:
    try:
        headers = get_request_headers() or {}
        token = headers.get("x-forwarded-access-token")
        if not token:
            authorization = headers.get("authorization", "")
            if authorization.lower().startswith("bearer "):
                token = authorization.split(" ", 1)[1]
        if token:
            return token
    except Exception:
        pass
    return os.getenv("DATABRICKS_TOKEN", "")


def _load_confluence_fixture() -> dict[str, Any]:
    try:
        return json.loads(CONFLUENCE_FIXTURE_PATH.read_text())
    except Exception as exc:
        logger.warning("Confluence fixture unavailable: %s", exc)
        return {}


@function_tool
def search_confluence(query: str) -> str:
    """Search Bobabricks Confluence context for FY26 goals, standards, and playbooks."""
    playbooks = _load_confluence_fixture()
    if not playbooks:
        return json.dumps({"error": "Confluence context unavailable"})

    normalized = query.strip().lower()
    matches = {}
    for title, body in playbooks.items():
        haystack = f"{title} {json.dumps(body)}".lower()
        if not normalized or any(term in haystack for term in normalized.split()):
            matches[title] = body

    if not matches:
        matches = playbooks
    return json.dumps(matches)


async def build_atlassian_tools(stack: AsyncExitStack) -> tuple[list[FunctionTool], list[str]]:
    url = _atlassian_url()
    if not url:
        return [], []
    token = _atlassian_token()
    if not token:
        return [], [ATLASSIAN_FRIENDLY_NAME]
    try:
        client = await stack.enter_async_context(DirectMcpClient(url, token))
        return [_make_confluence_search_tool(client, await client.list_tools())], []
    except Exception as exc:
        logger.warning("Atlassian MCP unavailable; running without it. (%s)", exc)
        return [], [ATLASSIAN_FRIENDLY_NAME]


async def build_direct_databricks_mcp_tools(
    stack: AsyncExitStack, tool_sources: dict[str, str] | None = None
) -> tuple[list[FunctionTool], list[str]]:
    if os.getenv("DISABLE_MCP_SERVERS", "false").strip().lower() in {"1", "true", "on", "yes"}:
        return [], list(MCP_FRIENDLY_NAMES.values())
    token = _databricks_mcp_token()
    if not token:
        return [], list(MCP_FRIENDLY_NAMES.values())

    tools: list[FunctionTool] = []
    unavailable: list[str] = []
    for name, url in [
        ("storetime", STORETIME_MCP_URL),
        ("opstask", OPSTASK_MCP_URL),
    ]:
        if not url:
            continue
        try:
            client = await stack.enter_async_context(DirectMcpClient(url, token))
            metas = await client.list_tools()
            tools.extend(_make_function_tool(client, meta) for meta in metas)
            if tool_sources is not None:
                tool_sources.update({meta["name"]: SOURCE_LABELS[name] for meta in metas})
        except Exception as exc:
            logger.warning("MCP server %r unavailable over direct transport; running without it. (%s)", name, exc)
            unavailable.append(MCP_FRIENDLY_NAMES.get(name, name))
    return tools, unavailable


def build_mcp_servers(workspace_client: WorkspaceClient) -> list[McpServer]:
    servers = []
    if os.getenv("ENABLE_GENIE_MCP", "true").strip().lower() not in {"0", "false", "off", "no"}:
        servers.append(McpServer(url=_genie_mcp_url(), name="bobabricks_genie", workspace_client=workspace_client))
    if not USE_SDK_MCP_SERVERS:
        return servers
    if STORETIME_MCP_URL:
        servers.append(McpServer(url=STORETIME_MCP_URL, name="storetime", workspace_client=workspace_client))
    if OPSTASK_MCP_URL:
        servers.append(McpServer(url=OPSTASK_MCP_URL, name="opstask", workspace_client=workspace_client))
    return servers


MCP_FRIENDLY_NAMES = {
    "bobabricks_genie": "Genie Agent",
    "storetime": "StoreTime",
    "opstask": "OpsTask",
}

# Labels for the user-visible "Sources:" line, keyed by MCP server name.
SOURCE_LABELS = {
    "bobabricks_genie": "Genie Agent",
    "storetime": "StoreTime",
    "opstask": "OpsTask",
}
CONFLUENCE_SOURCE_LABEL = "Confluence"
STORETIME_APP_NAME = os.getenv("STORETIME_APP_NAME", "bobabricks-storetime-mcp")
OPSTASK_APP_NAME = os.getenv("OPSTASK_APP_NAME", "bobabricks-opstask-mcp")


@functools.lru_cache(maxsize=1)
def _source_urls() -> dict[str, str]:
    """Workspace pages a viewer can open to inspect each source."""
    host = get_databricks_host_from_env()
    return {
        "Genie Agent": f"{host}/genie/rooms/{GENIE_SPACE_ID}",
        "StoreTime": f"{host}/apps/{STORETIME_APP_NAME}",
        "OpsTask": f"{host}/apps/{OPSTASK_APP_NAME}",
    }


def _source_link(label: str) -> str:
    try:
        url = _source_urls().get(label)
    except Exception:
        url = None
    return f"[{label}]({url})" if url else label
CONFLUENCE_FIXTURE_SOURCE_LABEL = "Sample playbooks (offline, not live Confluence)"


async def connect_available_mcp_servers(
    stack: AsyncExitStack, workspace_client: WorkspaceClient, tool_sources: dict[str, str] | None = None
):
    available = []
    unavailable = []
    if os.getenv("DISABLE_MCP_SERVERS", "false").strip().lower() in {"1", "true", "on", "yes"}:
        return available, list(MCP_FRIENDLY_NAMES.values())
    for server in build_mcp_servers(workspace_client):
        name = getattr(server, "name", "tool")
        try:
            connected = await stack.enter_async_context(server)
            listed = await connected.list_tools()
            available.append(connected)
            if tool_sources is not None:
                label = SOURCE_LABELS.get(name, MCP_FRIENDLY_NAMES.get(name, name))
                tool_sources.update({tool.name: label for tool in listed})
        except Exception as exc:
            logger.warning("MCP server %r unavailable; running without it. (%s)", name, exc)
            unavailable.append(MCP_FRIENDLY_NAMES.get(name, name))
    return available, unavailable


async def close_tool_stack(stack: AsyncExitStack) -> None:
    try:
        await stack.aclose()
    except BaseException as exc:
        logger.warning("MCP cleanup failed after response generation. (%s)", exc, exc_info=True)


def _raw_field(raw: Any, key: str) -> Any:
    return raw.get(key) if isinstance(raw, dict) else getattr(raw, key, None)


def _is_tool_error(output: str) -> bool:
    text = output.lstrip()
    if text.startswith(("Tool error", "An error occurred")):
        return True
    # A Genie query that is still running has returned no data yet; only its
    # completed poll_response counts as a Genie source.
    if "Query is still processing" in text:
        return True
    try:
        parsed = json.loads(text)
    except Exception:
        return False
    return isinstance(parsed, dict) and set(parsed) == {"error"}


def _confluence_links(output: str) -> list[str]:
    try:
        citations = json.loads(output).get("citations") or []
    except Exception:
        return []
    links = []
    for citation in citations:
        url = str(citation.get("url", "")).strip()
        title = str(citation.get("title", "")).strip() or "page"
        if url.startswith("https://"):
            links.append(f"[{CONFLUENCE_SOURCE_LABEL}: {title}]({url})")
    return links


def build_sources_line(items: list[Any], tool_sources: dict[str, str]) -> str:
    """Name only the sources whose tools actually returned a result this turn."""
    called = {}
    for item in items:
        if getattr(item, "type", None) == "tool_call_item":
            name = _raw_field(item.raw_item, "name")
            if name in tool_sources:
                called[_raw_field(item.raw_item, "call_id")] = name
    labels: list[str] = []
    for item in items:
        if getattr(item, "type", None) != "tool_call_output_item":
            continue
        name = called.get(_raw_field(item.raw_item, "call_id"))
        output = str(getattr(item, "output", ""))
        if not name or _is_tool_error(output):
            continue
        label = tool_sources[name]
        found = (_confluence_links(output) or [label]) if label == CONFLUENCE_SOURCE_LABEL else [_source_link(label)]
        labels.extend(entry for entry in found if entry not in labels)
    return f"Sources: {', '.join(labels)}" if labels else ""


def _sources_stream_events(text: str) -> list[dict[str, Any]]:
    # The chat UI joins consecutive assistant text, so start on its own paragraph.
    text = f"\n\n{text}"
    item_id = f"msg_{uuid4().hex}"
    return [
        {"type": "response.output_text.delta", "item_id": item_id, "delta": text},
        {
            "type": "response.output_item.done",
            "item": {
                "type": "message",
                "id": item_id,
                "role": "assistant",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            },
        },
    ]


def create_agent(
    mcp_servers=None,
    unavailable_tools=None,
    extra_tools=None,
    context_tools_enabled: bool = False,
    require_tool_call: bool = False,
) -> Agent:
    instructions = AGENT_INSTRUCTIONS
    if context_tools_enabled:
        instructions += CONTEXT_INSTRUCTIONS
    if unavailable_tools:
        names = ", ".join(sorted(set(unavailable_tools)))
        instructions += (
            "\n\n# Tool availability\n"
            f"Some capabilities may be unavailable this turn: {names}. Treat this as internal runtime context. "
            "Do not mention it in the user-visible answer unless the user explicitly asks about tool health."
        )
    # When the question needs store data, force the first model step to call a
    # tool so it cannot answer from earlier turns. The SDK resets tool_choice to
    # auto after that call. get_current_time is dropped so it cannot satisfy the
    # requirement in place of a data tool.
    if require_tool_call:
        return Agent(
            name="Bobabricks Store Operations Agent",
            instructions=instructions,
            model=MODEL,
            tools=list(extra_tools or []),
            mcp_servers=mcp_servers or [],
            model_settings=ModelSettings(tool_choice="required"),
        )
    return Agent(
        name="Bobabricks Store Operations Agent",
        instructions=instructions,
        model=MODEL,
        tools=[get_current_time, *(extra_tools or [])],
        mcp_servers=mcp_servers or [],
    )


# Questions about store data must hit a tool; "What tools do you have?" must not.
STORE_DATA_PATTERN = re.compile(
    r"\b(stores?|training|hours|fy26|goals?|behind|stack up|pacific|region(al)?|schedules?|"
    r"coverage|completion|tasks?|follow-?ups?|playbooks?|standards?|next steps?|do next|should i do)\b",
    re.IGNORECASE,
)
TOOLS_QUESTION_PATTERN = re.compile(r"\bwhat tools\b", re.IGNORECASE)


def needs_store_data(request: ResponsesAgentRequest) -> bool:
    user_texts = [
        _item_text(item)
        for item in request.input
        if (item.model_dump() if hasattr(item, "model_dump") else item).get("role") == "user"
    ]
    text = user_texts[-1] if user_texts else ""
    return bool(STORE_DATA_PATTERN.search(text)) and not TOOLS_QUESTION_PATTERN.search(text)


async def build_request_agent(
    stack: AsyncExitStack, require_tool_call: bool = False
) -> tuple[Agent, dict[str, str]]:
    """Connect this turn's tools and record which source each tool name belongs to."""
    tool_sources: dict[str, str] = {}
    mcp_servers, unavailable_tools = await connect_available_mcp_servers(stack, WorkspaceClient(), tool_sources)
    direct_tools, direct_unavailable = await build_direct_databricks_mcp_tools(stack, tool_sources)
    atlassian_tools, atlassian_unavailable = await build_atlassian_tools(stack)
    context_tools = list(atlassian_tools)
    tool_sources.update({tool.name: CONFLUENCE_SOURCE_LABEL for tool in atlassian_tools})
    unavailable = unavailable_tools + direct_unavailable
    if CONFLUENCE_MCP_ENABLED and not atlassian_tools:
        context_tools.append(search_confluence)
        tool_sources[search_confluence.name] = CONFLUENCE_FIXTURE_SOURCE_LABEL
    else:
        unavailable += atlassian_unavailable
    agent = create_agent(
        mcp_servers=mcp_servers,
        unavailable_tools=unavailable,
        extra_tools=direct_tools + context_tools,
        context_tools_enabled=CONFLUENCE_MCP_ENABLED,
        require_tool_call=require_tool_call and bool(mcp_servers or direct_tools or context_tools),
    )
    return agent, tool_sources


def maybe_create_session(session_id: str) -> AsyncDatabricksSession | None:
    if os.getenv("BOBABRICKS_DISABLE_LAKEBASE") == "1":
        return None
    if not lakebase_config.is_configured:
        return None
    return AsyncDatabricksSession(
        session_id=session_id,
        instance_name=lakebase_config.instance_name,
        autoscaling_endpoint=lakebase_config.autoscaling_endpoint,
        project=lakebase_config.autoscaling_project,
        branch=lakebase_config.autoscaling_branch,
        schema=lakebase_config.memory_schema,
        create_tables=False,
    )


def _is_lakebase_error(exc: Exception) -> bool:
    return any(keyword in str(exc).lower() for keyword in ["lakebase", "pg_hba", "postgres", "database instance", "insufficient privilege"])


def _item_text(item: Any) -> str:
    value = item.model_dump() if hasattr(item, "model_dump") else item
    content = value.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(part.get("text", "") for part in content if isinstance(part, dict))
    return ""


def _is_title_request(request: ResponsesAgentRequest) -> bool:
    for item in request.input:
        value = item.model_dump() if hasattr(item, "model_dump") else item
        if value.get("role") == "system" and "generate a short title" in _item_text(item).lower():
            return True
    return False


def _title_agent() -> Agent:
    return Agent(
        name="Conversation Titler",
        instructions="Generate a concise title. Output only the title text.",
        model=MODEL,
        tools=[],
    )


@invoke()
async def invoke_handler(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    try:
        if _is_title_request(request):
            result = await Runner.run(_title_agent(), [item.model_dump() for item in request.input])
            return ResponsesAgentResponse(output=[item.to_input_item() for item in result.new_items])

        session_id = get_session_id(request)
        if session_id:
            mlflow.update_current_trace(metadata={"mlflow.trace.session": session_id})
        session = maybe_create_session(session_id)

        stack = AsyncExitStack()
        await stack.__aenter__()
        try:
            agent, tool_sources = await build_request_agent(stack, needs_store_data(request))
            result = await Runner.run(agent, await deduplicate_input(request, session), session=session)
        finally:
            await close_tool_stack(stack)

        output = [item.to_input_item() for item in result.new_items]
        sources = build_sources_line(result.new_items, tool_sources)
        if sources:
            output.append(_sources_stream_events(sources)[1]["item"])
        return ResponsesAgentResponse(
            output=output,
            custom_outputs={"session_id": session.session_id if session else session_id},
        )
    except Exception as exc:
        if _is_lakebase_error(exc):
            raise HTTPException(status_code=503, detail=lakebase_access_message()) from exc
        raise


@stream()
async def stream_handler(request: ResponsesAgentRequest) -> AsyncGenerator[ResponsesAgentStreamEvent, None]:
    try:
        if _is_title_request(request):
            result = Runner.run_streamed(_title_agent(), input=[item.model_dump() for item in request.input])
            async for event in process_agent_stream_events(result.stream_events()):
                yield event
            return

        session_id = get_session_id(request)
        if session_id:
            mlflow.update_current_trace(metadata={"mlflow.trace.session": session_id})
        session = maybe_create_session(session_id)

        stack = AsyncExitStack()
        await stack.__aenter__()
        try:
            agent, tool_sources = await build_request_agent(stack, needs_store_data(request))
            result = Runner.run_streamed(agent, input=await deduplicate_input(request, session), session=session)
            async for event in process_agent_stream_events(result.stream_events()):
                yield event
            sources = build_sources_line(result.new_items, tool_sources)
            if sources:
                for event in _sources_stream_events(sources):
                    yield event
        finally:
            await close_tool_stack(stack)
    except Exception as exc:
        if _is_lakebase_error(exc):
            raise HTTPException(status_code=503, detail=lakebase_access_message()) from exc
        raise
