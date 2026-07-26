# agent-chaos-readiness

**Resilience scoring, chaos safety gating, and LitmusChaos experiment generation
for GKE.** It scores how well a workload would survive a fault, decides *go/no-go*
for each experiment and why, generates the LitmusChaos manifest — with a
steady-state probe and auto-abort — and lays out a safest-first game-day plan.
**It never injects a fault.** It scores, gates, and generates; a human runs the
experiment in a controlled window.

<p>
  <img alt="CI" src="https://github.com/venkat-mandadi/agent-chaos-readiness/actions/workflows/ci.yml/badge.svg">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

> Modeled on the chaos-engineering practice I run in production with LitmusChaos:
> prove the system is resilient enough, gate the experiment behind that proof,
> then run it with a hypothesis and an automatic abort.

**Skill up front, engine underneath.** A thin Claude **skill**
([`SKILL.md`](SKILL.md)) orchestrates — score the fleet, gate a proposed
experiment, plan a game day, generate a manifest. The scoring and safety logic
sit in a Python **engine** (`src/chaos_lab/`), so the go/no-go decision is
deterministic and the model's job is to explain it, not to re-derive it.

---

## Why this exists

"Break things in production" is a great way to *cause* an outage instead of
learning from one. Chaos engineering done well has a discipline:

1. **Prove resilience first.** A pod-delete on a single-replica service isn't an
   experiment, it's an outage. Score readiness before you inject anything.
2. **Gate the experiment.** Only run a fault where the system can take it, and say
   exactly what's missing when it can't.
3. **Hypothesis + auto-abort.** Every experiment defines steady state and stops
   itself the moment steady state breaks.
4. **Escalate gently.** Start with the lowest-blast fault on the most resilient
   workload; widen from there.

This engine encodes all four — so a game day is safe by construction, and the
plan doubles as a hardening backlog.

## What it does

- **Resilience score (0–100)** per workload — replicas, PodDisruptionBudget,
  health probes, resource limits, topology spread — each weighted by how much it
  matters for surviving chaos.
- **Safety gate** per fault — go/no-go with the exact blockers ("single replica —
  the fault would take the whole service down"), warnings, and guardrails.
- **LitmusChaos manifest** — a ready-to-apply `ChaosEngine` with a continuous
  steady-state probe and `stopOnFailure` auto-abort. Refuses to generate one for
  an unsafe experiment.
- **Game-day plan** — every workload, its runnable faults ordered safest-first,
  and the blocked ones with what to fix.

## Fault catalog

| Fault | Blast | Requires (to run safely) | LitmusChaos |
| --- | --- | --- | --- |
| `pod-delete` | low | ≥2 replicas | pod-delete |
| `pod-cpu-hog` | medium | resource limits | pod-cpu-hog |
| `pod-memory-hog` | medium | resource limits | pod-memory-hog |
| `pod-network-latency` | medium | health probes | pod-network-latency |
| `pod-network-loss` | high | ≥2 replicas + probes | pod-network-loss |
| `disk-fill` | high | limits + ≥2 replicas | disk-fill |

## Quickstart

Runs offline against a bundled sample fleet — no cluster needed.

```bash
git clone https://github.com/venkat-mandadi/agent-chaos-readiness
cd agent-chaos-readiness
pip install -e ".[dev]"

python examples/run_plan.py                                   # plan + a gate + a manifest
chaos-plan examples/resources.json readiness                  # resilience scores
chaos-plan examples/resources.json plan                       # game-day plan
chaos-plan examples/resources.json gate catalog-web pod-delete   # go/no-go with reasons
chaos-plan examples/resources.json manifest payments-api pod-delete   # LitmusChaos YAML
```

Point it at your cluster: `kubectl get deploy,statefulset,daemonset,pdb -A -o json > fleet.json`.

### Sample output

```
🟡 Deployment/analytics-prod/analytics — resilience 60/100 (moderate)
    [✓] multiple_replicas: 3 replica(s)
    [✗] pod_disruption_budget: no PodDisruptionBudget
          → Add a PodDisruptionBudget so voluntary disruptions respect a floor.
    ...

⛔ BLOCKED — pod-delete on Deployment/catalog-prod/catalog-web
    blocker: single replica — the fault would take the whole service down
```

The generated `ChaosEngine` includes the guardrail that matters most:

```yaml
probe:
  - name: app-stays-healthy
    type: httpProbe
    mode: Continuous
    runProperties:
      stopOnFailure: true    # auto-abort the moment steady state breaks
```

## Running it as an agent

**As a Claude skill.** Drop the folder into your skills directory (or install the
packaged `.skill`). It triggers on chaos / resilience / game-day / LitmusChaos
requests, runs `scripts/chaos_plan.py`, and reports scores, gates, and plans —
never injecting anything. See [`SKILL.md`](SKILL.md).

**As an MCP tool:**

```bash
pip install -e ".[mcp]"
python -m chaos_lab.mcp_server examples/resources.json
```

Tools: `resilience_scores()`, `game_day_plan()`, `gate(workload, fault)`,
`generate_manifest(workload, fault)`.

## Design decisions

- **Prove, then break.** Readiness scoring gates every experiment — the engine
  refuses to generate a manifest for a fault the workload can't survive.
- **Auto-abort is not optional.** Generated manifests always carry a continuous
  steady-state probe with `stopOnFailure`, so a bad experiment stops itself.
- **Stateful gets extra caution.** StatefulSets earn integrity warnings and a
  backup guardrail; high-blast faults are pushed to staging first.
- **The plan is a backlog.** Blocked faults come with the exact fix, so a fragile
  workload's chaos plan is also its hardening to-do list.

## Roadmap

- [ ] Import live LitmusChaos results to close the hypothesis loop
- [ ] promProbe steady-state from your SLOs (error budget as the abort signal)
- [ ] Node/zone-level faults (node-drain, az-loss) with cluster-wide blast checks
- [ ] Schedule + PR-comment a game-day plan from a namespace label

## Tests

```bash
pytest -q      # readiness scoring + safety gate + planner + manifest generation
```

## License

MIT — see [LICENSE](LICENSE).
