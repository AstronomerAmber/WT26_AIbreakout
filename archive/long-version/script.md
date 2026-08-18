# Bobabricks Store Operations Demo, Script

*Solo presenter: Amber Roberts (Technical Marketing Engineer, Databricks), speaking in first person as a store/regional manager at Bobabricks, a boba tea company. Wording follows the reference transcript closely, adapted to the Bobabricks persona; step order and content follow the outline.*

---

## Step 0: Architecture Diagram

**Say:**
Thank you, Patrick, for that introduction. Hello everyone, my name is Amber Roberts, I'm a technical marketing engineer at Databricks. We've been building out the Agent Bricks developer platform, and what I want to show you here is the store operations agent that I'll be using today.

In this example, I'm a regional manager of a company called Bobabricks. It's a boba tea company I invented for this demo. What I'm looking to do is get some context about my different stores, how they're operating, and have access to that data so I can ask questions of it directly.

At a high level, Agent Bricks is our enterprise agent development platform, and it's built to give you choice, context, and control. There's a lot on this diagram, but the two pieces I really want you to focus on today are Apps and Gateway, that's where most of what you'll see live.

So as we walk through this, what you'll be able to see is that I have a Genie agent in here. This is my store operations data, so how are stores doing against their goals, how many people are working different shifts, information like that. I have two custom MCPs here, StoreTime and OpsTask. In my company, this is my own labor and scheduling system, which I built and deployed on Databricks apps. That's a really great option if you want to connect to your internal systems, but maybe you haven't built out an MCP server yet.

And then I have Confluence, a built-in tool, because that has context for my overall FY26 goals as Bobabricks. It'll come built in with memory too, split into short-term and long-term memory APIs, I'll show you that as well. And we'll also get a glimpse of some of these platform services, like MLflow and Unity AI Gateway, along with Genie Spaces, Workflows, Databricks Apps, and governance.

And down here at the bottom, you can see I started from one of our app templates, built on the OpenAI Agents SDK, running on GPT models through Unity AI Gateway, and it comes with Codex and Omnigent already wired in. Omnigent is our new meta harness for using coding agents like Codex, and that's what's going to let me upgrade this agent myself later.

So let me jump in here.

---

## Step 1: Open the Deployed Agent

**Say:**
So as we look at the agent, I've already started from one of our app templates. We have a number of different examples to help you get started, across frameworks like LangGraph and OpenAI, these are the two most popular ones we see today, but you can use any of the popular authoring frameworks you'd like.

Let me jump into Databricks Apps here. This is our new home for apps, and I have quick access because I have a number of agents already deployed. So we're going to load my Bobabricks agent here. [open app UI] You can see it's running, and it has some basic tools.

So what I'm going to do is jump in and ask it, really quickly, what tools do you have? We'll see what it started out with. I've preceded it with a few of these tools, but we'll also end up adding some during this session together.

**Expected response, agent lists:**
- Genie Agent (store operations data)
- StoreTime (labor and scheduling)
- OpsTask (tickets and task tracking)
- Current time utility
- Memory

**Say (note the gap):**
So we can see it already has the data and analytics Genie I mentioned, the two MCPs, StoreTime and OpsTask, and a utility to get the current time, that way if I ask about the last 12 weeks, it'll actually know what that means. Under the hood, this is running on GPT-5.1, which is a really great agentic model. Notice it does not have Confluence yet, keep that in mind, that's going to matter in a few minutes.

---

## Step 2: Store Performance Question

**Ask the agent:**
Show the average versus actual training hours for my stores in my Pacific region and flag any that are falling behind.

**What happens:** Agent queries the Genie Agent.

**Expected result:** A named store (e.g., Store 104) comes back behind on training, with a short table or bullet summary.

**Say:**
So for Bobabricks, we have some training goals we want to meet this year, we want to make sure our employees are staying up to date with everything they should be doing. It's going to first query my Genie space here, so I didn't have to build out this UI, but you can customize it. Let me scroll down so we can see Pacific region, training hours, last 12 weeks. I can see I do have a store falling behind, it was able to reach out to Genie, run that query for me, and return and format that response.

---

## Step 3: Diagnostic Follow-Up

**Ask the agent:**
Why is Store 104 behind on training? Is it a scheduling problem or a completion problem?

**What happens:** Agent uses StoreTime, possibly OpsTask, potentially in parallel.

**Expected result:** Something like, Store 104 scheduled the training shifts, but those shifts got converted to service coverage during rush windows.

**Say:**
Since I have that custom MCP, I'm able to query my scheduling system, so you can see it's going to get a store schedule summary, that way I'm really able to dig in deep with the data I already have and the tools already included here. Both of these are actually running in parallel, so I'll get answers a bit faster.

So let's look at Store 104. It's both a scheduling problem, but it's primarily a utilization problem. We can see they've actually been scheduling a whole lot of shifts, but some of them got flipped to service, so they were scheduling them, but then they ended up needing these people to work the stores. That's really helpful for me as an operations manager looking at my region, to understand how I may reach out to this person.

---

## Step 4: Expose the Context Gap

**Ask the agent:**
What are our training goals for the year? How does Store 104 stack up?

**Expected result:** The agent can't answer fully, it doesn't have Confluence or company-plan context.

**Say:**
Let's see if it has the context about what my goals are for the year. It's telling me it doesn't have a tool that exposes company training goals directly. So I had Genie, my two custom MCPs, and the time tool, but I didn't actually have my company context built in here just yet.

---

## Step 5: Upgrade the Agent with Codex / Omnigent

**Transition:**
So what we're going to do is go back into Omnigent, and I'm going to ask Codex, OpenAI's coding agent, for a bigger upgrade here.

**Ask Codex/Omnigent:**
For the Bobabricks store operations agent, can you add a regional risk briefing capability?

Please:
1. Add the Atlassian Confluence MCP for FY26 goals and store playbooks.
2. Add inventory risk analysis using the Inventory MCP.
3. Update the system prompt so the agent classifies issues as sales, labor, inventory, training, or customer experience.
4. Add approval-gated OpsTask follow-up creation for high-severity risks.
5. Add a Generate Weekly Regional Briefing action in the app.
6. Redeploy the app.

**Say (while it works):**
So it's going to start working on that for me, and we'll see here in a couple minutes when it redeploys the app. That's what's really nice about using Databricks Apps as a backend, it's actually really quick to spin up an app, and it's also really quick to modify and redeploy, so it makes your development cycle much easier. Let's let it work and come back.

---

## Step 6: Show the Code Diff

**Say (once ready, or when returning to it):**
So it's made some of these updates for me, and I can actually see that within the change view here in Omnigent.

**Show the Omnigent change view, and call out:**
- Confluence MCP added
- Inventory MCP added
- System prompt updated with the new issue-classification categories
- Approval-gated task creation added
- Weekly briefing command/UI action added

**Say:**
So I can see it's modified my configuration, added the new tools, updated my system prompt, added that approval step, and added the new briefing action, all of that is the configuration you need, and it's built in, and again, we have the skills in here to help you build this out.

---

## Step 7: Platform Services During Redeploy

**Say (while the redeploy finishes):**
So while that's running, let me show you a couple of things that are also built into the template for you. The other thing that helps you here is MLflow tracing. So I'm in the Databricks workspace under experiments, and I found my store ops agent experiment where I'm storing my traces. I can see the different questions I've asked, and I can see it's listing tools first, so you want your agent to be aware, this is all actually built into the template for you, so it's not something you have to think about.

The other thing that's already built in is on behalf of user auth. As you're building out your app, you can decide if you want service principal based auth, so everyone is treated the same, or if you want to query data on behalf of the user, so the data I'm querying is the data I'm allowed to query. That's already built in for you as well.

The next thing I'll show you is Unity AI Gateway. Under AI and ML, we have our AI Gateway, and we have a number of MCPs and LLMs available to you, including the full lineup of GPT models. You can see agent integrations, featured models, and importantly here, we also see MCPs, Genie, and Atlassian built in, this is the connection I'm adding to my agent so I can bring in that Confluence context. And again, all of this operates on behalf of your identity, and this is also where our IT team can set budgets and policies so I can't accidentally run up a huge bill just by asking a lot of questions.

---

## Step 8: Return to the Agent

**Say:**
So let's go back and see where our agent is. Looks like the redeploy is done, let's launch our agent again.

**Ask the agent:**
What tools do you have?

**Confirm it now lists:**
- Genie Agent
- StoreTime
- OpsTask
- Confluence
- Inventory MCP
- Memory

**Say:**
There it is, we still have Genie, we still have labor and scheduling, and now I also have my memory store over here, this is Lakebase again, something we offer out of the box for you, and Confluence and inventory are in there now too. I didn't have to file a single ticket.

And look right here, there's a button that wasn't there five minutes ago, Generate Weekly Regional Briefing. That's not just a new tool the agent has, that's a new capability sitting right in my app.

Now let's go back to the question that broke it a few minutes ago.

**Ask the agent (same question as Step 4):**
What are our FY26 training goals, and how does Store 104 stack up?

**Expected result:** The agent now answers fully, pulling the FY26 goals from Confluence and comparing them against Store 104's actual numbers.

**Say:**
That's the exact question that stumped it a minute ago. This isn't working, and now it's fixed.

---

## Step 9: Put the Fix to Work

**Ask the agent:**
Generate my weekly regional risk briefing for the Pacific region, and create follow-up tasks for anything high severity.

**What happens (narrate as it runs):**
So now it's kicking off a query to Genie, it's going to get some information there, then it's going to query Confluence, get my FY26 training page, get all that information from the Confluence MCP server. It's also checking StoreTime for labor and scheduling issues, the Inventory tool for anything at risk of a stockout, and OpsTask to see what's already an open issue. So it's really able to dig in deep with the data I already have and the tools already included here, and put all of that into one prioritized briefing for me.

---

## Step 10: Approval Moment

**Say:**
And we also have approvals built in. So if it wants to call one of my custom MCP servers to create a task, it's going to surface that in the UI first.

**Expected agent response:**
I found 3 high-severity risks. I recommend creating follow-up tasks for Store 104 and Store 117. Do you approve creating these OpsTask tickets?

**Action:** Click **Approve**. Agent creates the tasks.

**Say:**
So governance is built in here. Once I click allow, the agent continues and produces the final result. It did all that analysis on its own, but the moment it wants to create real tickets that someone's going to have to act on, it stops and asks me first.

---

## Step 12: Background / Scheduled Workflow

**Say:**
The last thing I wanted to show you is a schedule feature. This basically allows you to schedule this agent on a trigger or schedule basis using our new agentic task on Databricks Jobs.

**Show:** a scheduled workflow, e.g., Generate Pacific regional risk briefing every Monday at 7 AM.

**Explain:**
When you come into Databricks Jobs and click add a task, you now have a new task type called agent. This is backed by the same APIs, so you get all the bells and whistles of jobs, you can schedule them, you can have triggers, you can build your own DAG. Everything is configurable through the UI, you select your model, any system prompts, and the tools, these are all the same tools we've talked about today. You can also configure trace destinations, so every run still shows up in MLflow, I'm not trading away visibility just because I'm not the one clicking the button.

---

## Step 13: Wrap

**Say:**
So to round us out here, as I covered, Agent Bricks is our agent developer platform. It gives you choice, context, and control, all of this is built in for you, running on OpenAI's GPT models with Codex to help you build. I started with an agent that could answer basic questions about my stores. When I hit something it couldn't do, I didn't file a ticket and wait, I asked Codex for the upgrade myself, in plain English, and it connected me directly to the tools, models, and context I needed, while I still had auditability, traceability, and control the whole way through.

The last thing I'll leave you with, we'd love for you to deploy an agent today. This leads you to our Databricks Apps template repo, and we'd love to see the agents you build. Thank you so much for your time.

---

### Presenter notes
- **Persona consistency:** you're speaking as a Bobabricks store/regional manager throughout, avoid language like our platform or we built this feature, which reads as vendor/engineering voice. Stick to the agent our team set up for me framing.
- **Boba-specific flavor (optional):** if you want the demo to feel more concretely boba tea rather than generic food-service, consider naming a couple of boba-specific SKUs when the Inventory MCP comes up in Steps 5 through 9 (e.g., tapioca pearls, brown sugar syrup, specific milk tea bases) rather than leaving inventory risk abstract.
- **Timing risk points:** Step 5 (Codex build) and Step 7 (redeploy) are the two places things can lag, the MLflow/Gateway tour in Step 7 is there as filler if the redeploy is slow, same trick used in the reference demo.
- **Fallback line** if a tool call errors live: This is how you know it's a live demo, acknowledge it, retry once, move on.
- **Consider naming Store 117** consistently in Step 2 as well, so the 3 high-severity risks in Step 10 doesn't introduce a new store name out of nowhere.
