---
name: agentic-chaos
description: >-
  Plan chaos-engineering / destructive-testing experiments safely for GKE
  workloads. Scores each workload's resilience (replicas, PodDisruptionBudget,
  probes, resource limits, topology spread), gates a proposed fault behind that
  score with go/no-go reasons, generates a LitmusChaos manifest with a
  steady-state probe and auto-abort, and lays out a safest-first game-day plan.
  Use this whenever the user mentions chaos engineering, LitmusChaos, fault
  injection, destructive/resilience/failure testing, game days, pod-delete or
  network or resource-hog experiments, or asks whether it's safe to inject a
  fault or how resilient a service is. It never injects a fault — it scores,
  gates, and generates. Prefer this over hand-writing chaos manifests.
---

# agentic-chaos — safe chaos planning for GKE

Chaos engineering done well is disciplined: prove a workload is resilient enough,
gate the experiment behind that proof, run it with a hypothesis and an automatic
abort, and escalate gently. Your job with this skill is to apply that discipline
and communicate it — **never to run a destructive experiment.** The engine
scores, gates, and generates manifests; a human applies them in a controlled
window. **Do not evaluate manifests or decide safety by hand** — delegate to the
engine and reason over its verdicts.

## When to use this

Anything chaos/resilience related: "is it safe to run a pod-delete on payments,"
"plan a game day for the payments namespace," "how resilient is this service,"
"generate a LitmusChaos experiment for network latency," "what should we harden
before chaos testing."

## Workflow

1. **Get the fleet.** The engine reads a `kubectl -o json` dump of workloads and
   PodDisruptionBudgets. If the user hasn't provided one:
   `kubectl get deploy,statefulset,daemonset,pdb -A -o json > fleet.json`
   or offer to run against the bundled sample (`examples/resources.json`).

2. **Pick the question and run the engine — don't judge safety yourself.**

   ```bash
   python scripts/chaos_plan.py <fleet.json> readiness            # resilience scores
   python scripts/chaos_plan.py <fleet.json> plan                 # game-day plan
   python scripts/chaos_plan.py <fleet.json> gate <wl> <fault>    # go/no-go + reasons
   python scripts/chaos_plan.py <fleet.json> manifest <wl> <fault> # LitmusChaos YAML (safe only)
   ```
   `... faults` lists the catalog; `--format markdown` for a PR/Slack.

3. **Communicate the result as a decision aid.**
   - For a **gate**, lead with SAFE/BLOCKED and the reason. If blocked, the fix is
     the point — "add a second replica and a PDB, then it's safe."
   - For a **plan**, start with the resilience score, list runnable faults
     safest-first, and surface blocked ones as a hardening backlog.
   - Always carry the **guardrails** (steady-state probe + auto-abort, start
     small, scheduled window) — they're what make a yes safe.

4. **Never run it.** The `manifest` output is for a human to review and
   `kubectl apply` during a game day. Refuse to imply the experiment has been
   executed, and the engine refuses to generate a manifest for an unsafe fault.

## What the engine encodes (so you can explain it)

- **Prove, then break.** Readiness gates every experiment; a pod-delete on a
  single-replica service is an outage, not a test — the engine blocks it.
- **Auto-abort is baked in.** Every generated manifest has a continuous
  steady-state probe with `stopOnFailure`.
- **Escalate gently.** Runnable faults are ordered low → high blast radius.
- **Stateful is handled with care** — integrity warnings and a backup guardrail.

## Going deeper

- To add faults, tune the resilience weights, or change the safety requirements,
  read [`references/faults.md`](references/faults.md) — load it only when
  modifying behavior.
- To run interactively as MCP tools: `pip install -e ".[mcp]"` then
  `python -m chaos_lab.mcp_server <fleet.json>`.

## Don't

- Don't inject faults or imply an experiment ran — this skill only plans.
- Don't decide safety by eyeballing manifests — run the gate and report it.
- Don't generate a manifest for a blocked fault — surface the blockers and the
  fix instead.
