# Bobabricks Store Operations Demo, Script (Short Version)

*Solo presenter: Amber Roberts (Technical Marketing Engineer, Databricks), speaking in first person as a store/regional manager at Bobabricks, a boba tea company. This is the short version of the demo. The full version, with the weekly regional briefing, the approval moment, and the scheduled workflow, is archived in `archive/long-version/`.*

---

## Presenter Setup (do this before you run the demo)

This demo runs against the **fevm-worldtour-ai** Databricks workspace and the app `bobabricks-store-ops-demo`. The repo is `https://github.com/AstronomerAmber/WT26_AIbreakout`.

### One-time prerequisites

1. **Workspace access** to `https://fevm-worldtour-ai.cloud.databricks.com` (the demo app, Genie space, warehouse, and MCP apps already live here).
2. **Databricks CLI profile** named `fevm-worldtour-ai`:
   ```bash
   databricks auth login --host https://fevm-worldtour-ai.cloud.databricks.com --profile fevm-worldtour-ai
   ```
3. **Clone the repo** locally:
   ```bash
   git clone https://github.com/AstronomerAmber/WT26_AIbreakout.git
   ```
4. **Atlassian Confluence consent (one-time, per presenter).** The Confluence tool uses the managed connection `system_ai_agent_atlassian_mcp` with per-user OAuth. Authorize it once at:
   `https://fevm-worldtour-ai.cloud.databricks.com/explore/connections/system_ai_agent_atlassian_mcp` → **Sign in / Authorize** (Atlassian). Without this, the post-upgrade Confluence answer fails with an auth error.
5. **Omnigent** installed (`omni`/`omnigent` CLI).

### Stage the app at baseline (before each run)

The demo starts *without* Confluence so the gap is real. If a prior run left it upgraded, reset it:
```bash
cd WT26_AIbreakout
git checkout -- .           # ensure baseline repo state (no Confluence)
databricks sync --full . /Workspace/Users/<your-email>/WT26_AIbreakout --profile fevm-worldtour-ai
databricks apps deploy bobabricks-store-ops-demo \
  --profile fevm-worldtour-ai \
  --source-code-path /Workspace/Users/<your-email>/WT26_AIbreakout
```
Confirm in the app that "What tools do you have?" lists **Genie, StoreTime, OpsTask** only (no Confluence).

### Connect Omnigent (for Step 5)

1. Log in to the Omnigent server (browser flow):
   ```bash
   omnigent login https://fevm-worldtour-ai.cloud.databricks.com/api/2.0/omnigent
   ```
2. Register this machine as a host:
   ```bash
   omnigent host --server https://fevm-worldtour-ai.cloud.databricks.com/api/2.0/omnigent
   ```
3. In the Omnigent UI, start a session with: **host = this machine**, **working directory = your local `WT26_AIbreakout` clone**, **worktree branch = blank**, **agent = Codex**.

`AGENTS.md` in the repo tells Codex exactly how to make the one-tool Confluence upgrade and how to redeploy (profile `fevm-worldtour-ai`, sync + `apps deploy` against the workspace path). You don't need to memorize the commands — Codex follows that file.

---

## Step 0: Architecture Diagram

**Say:** Thank you, Patrick, for that introduction. Hello everyone, my name is Amber Roberts and I'm a technical marketing engineer at Databricks. Last month at the Data & AI summit Databricks released a lot of enhanced capabilities around building and maintaining AI systems, and I wanted to walk you though some of them. Let's get started!

*–slide–*

In this demo, I'm a regional manager of a company called Bobabricks. It's a boba tea company I invented for this demo. What I'm looking to do is get some context about my different stores, how they're operating, and have access to that data so I can ask questions of it directly.

At a high level, Agent Bricks is our enterprise agent development platform, and it's built to give you choice, context, and control.

Starting off with our Genie agent in here, this is my store operations data, so how are stores doing against their goals, how many people are working different shifts, information like that. I have two custom MCPs here, StoreTime and OpsTask. In my company, this is my own labor and scheduling system, which I built and deployed on Databricks apps. That's a really great option if you want to connect to your internal systems, but maybe you haven't built out an MCP server yet.

What I do not have connected yet is Confluence, which is where my overall FY26 goals and operating standards live as Bobabricks. That missing company context is the gap I'm going to hit and then fix live. We'll also see Lakebase memory as app context, plus platform services like MLflow, Unity AI Gateway, and Databricks Apps, but memory is not one of the tools the agent should list.

And down here at the bottom, you can see I started from one of our app templates, built on the OpenAI Agents SDK, running on GPT models through Unity AI Gateway, and it comes with Codex and Omnigent already wired in. Omnigent is our new meta harness for using coding agents like Codex, and that's what's going to let me upgrade this agent myself later.

---

## Step 1: Open the Deployed Agent (the app)

**Say:** I mentioned the app templates which I used, so I quickly wanted to show you where I got it and where you can find a variety of templates https://github.com/databricks/app-templates across popular authoring frameworks.

Now let's open up Databricks Apps here and click on my Bobabricks agent here. [open app UI] You can see it's running, and it has some basic tools.

So what I'm going to do is go ahead and ask it, really quickly, what tools do you have? We'll see what it started out with.

**Expected response, agent lists:**
- Genie Space (store operations data)
- StoreTime (labor and scheduling)
- OpsTask (tickets and task tracking)

**Say (note the gap):** So we can see it already has the data and analytics Genie I mentioned, and the two MCPs, StoreTime and OpsTask. Under the hood, this is running on GPT-5.1, which is a really great agentic model. Notice it does not have Confluence yet, keep that in mind, that's going to matter in a few minutes.

---

## Step 2: Store Performance Question

**Ask the agent:** Show the average versus actual training hours for my stores in my Pacific region and flag any that are falling behind.

**What happens:** Agent queries the Genie Agent.

**Expected result:** Store 104 / Seattle Pike Place is flagged as falling behind, with regional scheduled and completed training-hour averages.

**Say:** So for Bobabricks, we have some training goals we want to meet this year, we want to make sure our employees are staying up to date with everything they should be doing. It's going to first query my Genie space here, so I didn't have to build out this UI, but you can customize it. I can see I do have a store falling behind, it was able to reach out to Genie, run that query for me, and return and format that response.

---

## Step 3: Diagnostic Follow-Up

**Ask the agent:** Why is Store 104 behind on training?

**What happens:** Agent uses StoreTime. It may call both schedule inspection and training-event lookup.

**Expected result:** Store 104 scheduled the training shifts, but 14 hours got converted to service coverage during rush windows, leaving 28 of 42 scheduled hours completed.

**Say:** Since I have that custom MCP, I'm able to query my scheduling system, so you can see it's going to get a store schedule summary, that way I'm really able to dig in deep with the data I already have and the tools already included here.

So let's look at Store 104. It's both a scheduling problem, but it's primarily a utilization problem. We can see they've actually been scheduling a whole lot of shifts, but some of them got flipped to service, so they were scheduling them, but then they ended up needing these people to work the stores. That's really helpful for me as an operations manager looking at my region, to understand how I may reach out to this person.

---

## Step 4: Expose the Context Gap (need a fix)

**Ask the agent:** What are our training goals for the year? How does Store 104 stack up?

**Expected result:** The agent can't answer fully, it doesn't have Confluence or company-plan context.

**Say:** Let's see if it has the context about what my goals are for the year. It's telling me it doesn't have a tool that exposes company training goals directly. So I had Genie and my two custom MCPs, but I didn't actually have my company context built in here just yet.

---

## Step 5: Fix With Omnigent

**Transition:** So what we're going to do is go back into Omnigent — the harness that wraps Codex, OpenAI's coding agent — and ask it for an upgrade.

**Prerequisite:** You've cloned the demo repo locally (`git clone https://github.com/AstronomerAmber/WT26_AIbreakout.git`) and connected your machine as an Omnigent host — see Presenter Setup.

**Before asking, in the Omnigent new-session screen, select:**
- **Host:** your connected host (your own machine, shown green)
- **Working directory:** your local `WT26_AIbreakout` clone
- **Git worktree branch:** leave **blank** (start directly in the working directory)
- **Agent:** **Codex**

**Ask Codex/Omnigent:** For the Bobabricks store operations agent, can you add our FY26 goals and store playbooks as context? Please add the Atlassian Confluence MCP so the agent can pull from Confluence directly, and redeploy the app.

**Say (while it works):** So it's going to start working on that for me, and we'll see here in a couple minutes when it redeploys the app. We can also see that smart routing automatically kicked off in order to keep costs down, Omnigent is finding the best GPT model for the task.

---

## Step 6: Show the Code Diff (redeploy)

**Say (once ready, or when returning to it):** So it's made the update for me, and I can actually see that within the change view here in Omnigent.

Show the Omnigent change view, and call out:
- Managed Atlassian/Confluence MCP added
- One new `search_confluence` tool added
- App env updated so Confluence is enabled on redeploy
- Redeploy approval requested

**Say:** So I can see it's modified my configuration and added the one new tool I actually needed. It added the managed Confluence MCP, wired one new Confluence search tool, and updated the app configuration. Now it's asking me to approve redeploying the app. I'll approve that, and let's give it a moment to redeploy.

---

## Step 7: Check the Redeployment

**Say:** So let's go back and see where our agent is. Looks like the redeploy is done, let's launch our agent again.

**Ask the agent:** What tools do you have?

**Confirm it now lists:**
- Genie Agent
- StoreTime
- OpsTask
- Confluence

**Say:** There it is, we still have Genie, we still have labor and scheduling, and now Confluence is in there too. I didn't have to file a single ticket.

Now let's go back to the question that broke it a few minutes ago.

**Ask the agent (same question as Step 4):** What are our FY26 training goals, and how does Store 104 stack up?

**Expected result:** The agent now answers fully, pulling the FY26 goals from Confluence and comparing them against Store 104's actual numbers.

**Say:** That's the exact question that stumped it a minute ago has now been fixed.

---

## Step 8: Traces and AI Gateway

**Say:** So now that we've confirmed the fix is actually working, let's see what's going on behind the scenes with tracing and observability.

I'm in the Databricks workspace under the experiments tab, and I've got my store ops agent experiment here, where all of my traces are being logged. I can see every question I've asked today, step by step, what tools got called, in what order, this is all built into the template for you, so it's not something you have to think about separately.

Now let's go into Unity AI Gateway. Under AI and ML, we have our AI Gateway, and this is really where the rest of the governance lives. First, models, you can see the GPT models available to me here. Then providers, so you can see where those models are actually coming from. Then MCPs, this is where I can see Genie, Atlassian, and the rest of the connections we've talked about today, and this is also where policies get set for each one of them. And then agents, so you can see the actual agents registered here, including the one I've been using today.

Up in the top right, let's look at budgets. This is where our IT team can cap spend, per agent, per team, however they want to slice it, so I can't accidentally run up a huge bill just by asking a lot of questions.

And last, the usage dashboard, so you can actually see consumption over time, broken down by model, by agent, by whoever's using it. All of this operates on behalf of your identity, so it's not just governed, it's governed and attributed correctly.

---

## Step 9: Wrap

**Say:** So to round us out here, as I covered, Agent Bricks is our agent developer platform. It gives you choice, context, and control, all of this is built in for you, running on OpenAI's GPT models with Codex to help you build. I started with an agent that could answer basic questions about my stores. When I hit something it couldn't do, I didn't file a ticket and wait, I asked Codex for the upgrade myself, in plain English, and it connected me directly to the tool and context I needed, while I still had auditability, traceability, and governance through AI Gateway the whole way through.

Thank you everyone, back to you Patrick.

---

## Presenter Notes

- **What this version cuts, and why:** the weekly regional briefing query, the approval moment, and the scheduled workflow are all gone. Those three showed off orchestration and governance, but they diluted the aha moment, which is really just: the agent couldn't answer a real question, I asked for one fix in plain English, and now it can. This version makes that the whole spine of the demo.
- **Step 5/6 is intentionally small now:** one capability added (Confluence), one new tool, one redeploy. Resist the urge to add more back in here, the smaller the ask, the more obvious it is that Codex did real work fast, and the cleaner Step 7's payoff lands.
- **Persona consistency:** you're speaking as a Bobabricks store/regional manager throughout, avoid language like "our platform" or "we built this feature," which reads as vendor/engineering voice.
- **Boba-specific flavor (optional):** if you want a boba-specific detail somewhere, Confluence's FY26 goals doc is a good spot to name something concrete, like a training goal tied to a specific drink prep standard.
- **Fallback line if a tool call errors live:** This is how you know it's a live demo, acknowledge it, retry once, move on.
- **If you want to go back to the long version:** it's saved in `archive/long-version/` and still has the full weekly briefing, approval, and scheduled workflow arc, useful for a longer session or a more technical audience that wants to see orchestration and governance in more depth.
