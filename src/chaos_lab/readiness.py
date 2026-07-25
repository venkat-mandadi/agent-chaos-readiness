"""Score a workload's resilience readiness.

The score answers: how well would this survive a fault *before* we inject one?
Each check is weighted by how much it matters for surviving chaos — enough
replicas and a disruption budget matter most, because without them a single pod
kill is a full outage.
"""
from __future__ import annotations

from . import loader
from .models import LIMITS, PDB, PROBES, REPLICAS, SPREAD, Check, Readiness, Workload

_WEIGHTS = {REPLICAS: 25, PDB: 20, PROBES: 20, LIMITS: 15, SPREAD: 20}


def _probes_ok(w: Workload) -> bool:
    conts = w.containers
    return bool(conts) and all("livenessProbe" in c and "readinessProbe" in c for c in conts)


def _limits_ok(w: Workload) -> bool:
    conts = w.containers
    return bool(conts) and all(
        (c.get("resources", {}) or {}).get("limits", {}).get("cpu")
        and (c.get("resources", {}) or {}).get("limits", {}).get("memory")
        for c in conts
    )


def score(w: Workload, pdbs: list[dict]) -> Readiness:
    checks = [
        Check(REPLICAS, w.replicas >= 2, _WEIGHTS[REPLICAS],
              f"{w.replicas} replica(s)",
              "Run at least 2 replicas so losing one isn't an outage."),
        Check(PDB, loader.has_pdb(w, pdbs), _WEIGHTS[PDB],
              "PodDisruptionBudget present" if loader.has_pdb(w, pdbs) else "no PodDisruptionBudget",
              "Add a PodDisruptionBudget so voluntary disruptions respect a floor."),
        Check(PROBES, _probes_ok(w), _WEIGHTS[PROBES],
              "liveness + readiness probes" if _probes_ok(w) else "missing liveness/readiness probes",
              "Add both probes so failures are detected and traffic drains."),
        Check(LIMITS, _limits_ok(w), _WEIGHTS[LIMITS],
              "cpu+memory limits set" if _limits_ok(w) else "missing resource limits",
              "Set cpu/memory limits so a resource-hog fault stays contained."),
        Check(SPREAD, w.has_spread, _WEIGHTS[SPREAD],
              "topology spread / anti-affinity" if w.has_spread else "no spread constraints",
              "Add topologySpreadConstraints or podAntiAffinity to survive a node/zone loss."),
    ]
    s = sum(c.weight for c in checks if c.passed)
    level = "resilient" if s >= 80 else "moderate" if s >= 50 else "fragile"
    return Readiness(w.ref, s, level, checks)
