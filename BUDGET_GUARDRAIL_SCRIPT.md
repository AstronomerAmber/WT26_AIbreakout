# Budget Guardrail Script (No Live Model Change)

## Objective
Demonstrate cost control with policy enforcement while keeping the model unchanged.

## Talk Track
"Instead of changing models in the middle of the demo, we govern spend at the platform layer using Unity AI Gateway budget policies."

## On Screen
1. Open Unity AI Gateway policy/budget controls.
2. Show configured budget threshold for this agent/app.
3. Trigger a run or projected usage condition that crosses policy threshold.
4. Show guardrail behavior (warning/block) and explain enforcement.

## Narration During Trigger
- "The policy evaluates projected usage against budget."
- "When threshold is exceeded, the guardrail intervenes."
- "This keeps costs predictable without modifying application logic."

## Acceptance Signal
- A visible budget/policy event appears (warning or block) and is explained.
- You continue the demo with approved/within-budget execution path.

## Fallback if Trigger Is Inconsistent
- Show a prior recorded policy event in trace/logs.
- State:
  "This environment is already under threshold right now; here is the same guardrail event from an earlier run."
