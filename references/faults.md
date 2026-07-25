# Fault catalog & resilience model — reference

Load this only to add a fault, change the resilience weights, or adjust safety
requirements. A normal plan/gate doesn't need it.

## Contents
- [Resilience scoring](#resilience-scoring)
- [Fault definitions](#fault-definitions)
- [The safety gate](#the-safety-gate)
- [Generated manifest](#generated-manifest)
- [Adding a fault](#adding-a-fault)

## Resilience scoring

`src/chaos_lab/readiness.py`. Each check is weighted by how much it matters for
surviving a fault (total 100):

| Check | Weight | Passes when |
| --- | ---: | --- |
| `multiple_replicas` | 25 | `spec.replicas >= 2` |
| `pod_disruption_budget` | 20 | a PDB in the namespace selects the workload's labels |
| `health_probes` | 20 | every container has liveness **and** readiness probes |
| `resource_limits` | 15 | every container sets cpu+memory limits |
| `topology_spread` | 20 | `topologySpreadConstraints` or `podAntiAffinity` present |

Levels: **resilient** ≥ 80, **moderate** ≥ 50, **fragile** < 50.

## Fault definitions

`src/chaos_lab/faults.py`. Each `Fault` declares:

- `litmus_experiment` — the LitmusChaos experiment name
- `blast` — low / medium / high (drives game-day ordering)
- `required` — readiness checks that **must** pass, or the fault is blocked
- `recommended` — checks that **should** pass, surfaced as warnings
- `env` — default experiment parameters

## The safety gate

`src/chaos_lab/safety.py`. A verdict is **blocked** if any `required` check fails,
with a human-readable reason per gap. Warnings come from failed `recommended`
checks and from stateful/high-blast context. Guardrails (steady-state probe +
auto-abort, start small, scheduled window, backups for stateful) are always
attached — they make an allowed experiment safe.

## Generated manifest

`src/chaos_lab/litmus.py` emits a `ChaosEngine` with the experiment's env and a
continuous `httpProbe` steady-state check. `stopOnFailure: true` makes the
experiment **auto-abort** when the probe fails. Point the probe at a promProbe on
your SLO to use error-budget burn as the abort signal. YAML if PyYAML is
installed, otherwise JSON (kubectl accepts both).

## Adding a fault

1. Add a `Fault` to `CATALOG` with its LitmusChaos experiment name, blast radius,
   and the readiness checks it requires/recommends. Choose `required` checks by
   asking "what would make this fault an outage instead of a test?"
2. If it needs a new resilience signal, add a `Check` in `readiness.py` (and a
   weight) so the gate can reason about it.
3. Add tests: a workload that should pass the gate and one that should be blocked.
