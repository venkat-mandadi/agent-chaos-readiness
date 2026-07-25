"""Build a game-day plan: which experiments to run, safest first.

For each workload it evaluates every fault, keeps the ones that pass the safety
gate, and orders them by blast radius (low → high) so a game day starts gentle
and escalates. Blocked faults are reported with what to fix first — the plan is
as much a hardening backlog as a run sheet.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import faults as fault_catalog
from . import safety
from .models import Blast, Readiness, SafetyVerdict, Workload

_BLAST_ORDER = {Blast.LOW: 0, Blast.MEDIUM: 1, Blast.HIGH: 2}


@dataclass(frozen=True)
class WorkloadPlan:
    ref: str
    readiness: Readiness
    runnable: list[SafetyVerdict]     # allowed, ordered safest-first
    blocked: list[SafetyVerdict]      # not allowed, with blockers

    def as_dict(self) -> dict:
        return {
            "resource": self.ref,
            "readiness": self.readiness.as_dict(),
            "runnable": [v.as_dict() for v in self.runnable],
            "blocked": [v.as_dict() for v in self.blocked],
        }


def plan_workload(w: Workload, pdbs: list[dict]) -> WorkloadPlan:
    ready, verdicts = safety.assess_all(w, pdbs, fault_catalog.CATALOG)
    runnable = sorted(
        (v for v in verdicts if v.allowed),
        key=lambda v: _BLAST_ORDER[fault_catalog.BY_NAME[v.fault].blast],
    )
    blocked = [v for v in verdicts if not v.allowed]
    return WorkloadPlan(w.ref, ready, runnable, blocked)


def game_day(workloads: list[Workload], pdbs: list[dict]) -> list[WorkloadPlan]:
    """Plan across the fleet, most-resilient workloads first (safest to start on)."""
    plans = [plan_workload(w, pdbs) for w in workloads]
    plans.sort(key=lambda p: p.readiness.score, reverse=True)
    return plans
