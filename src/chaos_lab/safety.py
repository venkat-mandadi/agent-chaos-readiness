"""The pre-flight safety gate.

Given a workload's readiness and a fault, decide go/no-go and say exactly why.
A blocker means "this experiment would likely cause a real outage — fix the gap
first." Warnings and guardrails make an allowed experiment safer.
"""
from __future__ import annotations

from . import readiness as rd
from .models import Fault, Readiness, SafetyVerdict, Workload

# Human-readable reason per failed check, in the context of running chaos.
_BLOCK_REASON = {
    "multiple_replicas": "single replica — the fault would take the whole service down",
    "resource_limits": "no resource limits — a resource-hog fault could starve the node",
    "health_probes": "no liveness/readiness probes — failures wouldn't be detected or drained",
    "topology_spread": "no spread constraints — a node/zone fault hits every pod at once",
    "pod_disruption_budget": "no PodDisruptionBudget — nothing bounds how many pods go down",
}


def _reason(check_id: str) -> str:
    return _BLOCK_REASON.get(check_id, f"required check '{check_id}' not met")


def assess(w: Workload, ready: Readiness, fault: Fault) -> SafetyVerdict:
    blockers = [_reason(cid) for cid in fault.required if not ready.passed(cid)]
    warnings = [_reason(cid) for cid in fault.recommended if not ready.passed(cid)]

    guardrails = [
        "Attach a steady-state probe (SLO / health) with an automatic abort.",
        "Start small — low PODS_AFFECTED_PERC / short duration — then widen.",
        "Run in a scheduled game-day window with the owning team watching.",
    ]
    if w.stateful:
        warnings.append("stateful workload — validate data integrity; prefer network faults over pod-delete")
        guardrails.append("Take/verify a backup before disk or pod faults on stateful data.")
    if fault.blast.value == "high":
        guardrails.append("High blast radius — run in staging first, then a single prod cell.")

    return SafetyVerdict(fault.name, w.ref, allowed=not blockers,
                         blockers=blockers, warnings=warnings, guardrails=guardrails)


def assess_all(w: Workload, pdbs: list[dict], faults: list[Fault]) -> tuple[Readiness, list[SafetyVerdict]]:
    ready = rd.score(w, pdbs)
    return ready, [assess(w, ready, f) for f in faults]
