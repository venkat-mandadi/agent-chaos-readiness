"""Domain models for the chaos-engineering planner.

Chaos engineering done well is not "break things and see" — it's: prove the
system is resilient *enough* to survive a fault, gate the experiment behind that
proof, then run it with a steady-state hypothesis and an automatic abort. This
engine models exactly that: a ``Workload``'s resilience ``Readiness``, a
``Fault``'s requirements, and the ``SafetyVerdict`` that decides go/no-go.

Nothing here destroys anything — it scores, gates, and *generates* the
LitmusChaos manifest a human runs in a controlled window.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# Readiness check ids — referenced by faults as requirements.
REPLICAS = "multiple_replicas"
PDB = "pod_disruption_budget"
PROBES = "health_probes"
LIMITS = "resource_limits"
SPREAD = "topology_spread"


class Blast(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class Workload:
    raw: dict

    @property
    def kind(self) -> str:
        return self.raw.get("kind", "")

    @property
    def name(self) -> str:
        return self.raw.get("metadata", {}).get("name", "<unnamed>")

    @property
    def namespace(self) -> str:
        return self.raw.get("metadata", {}).get("namespace", "default")

    @property
    def labels(self) -> dict:
        return self.raw.get("metadata", {}).get("labels", {}) or {}

    @property
    def app_label(self) -> str:
        return self.labels.get("app") or self.name

    @property
    def spec(self) -> dict:
        return self.raw.get("spec", {}) or {}

    @property
    def replicas(self) -> int:
        if self.kind == "Pod":
            return 1
        return int(self.spec.get("replicas", 1))

    @property
    def stateful(self) -> bool:
        return self.kind == "StatefulSet"

    @property
    def pod_spec(self) -> dict:
        return self.spec.get("template", {}).get("spec", {}) or {}

    @property
    def containers(self) -> list[dict]:
        return self.pod_spec.get("containers", []) or []

    @property
    def has_spread(self) -> bool:
        if self.pod_spec.get("topologySpreadConstraints"):
            return True
        aff = self.pod_spec.get("affinity", {}) or {}
        return bool(aff.get("podAntiAffinity"))

    @property
    def ref(self) -> str:
        return f"{self.kind}/{self.namespace}/{self.name}"


@dataclass(frozen=True)
class Check:
    id: str
    passed: bool
    weight: int
    note: str
    remediation: str = ""


@dataclass(frozen=True)
class Readiness:
    ref: str
    score: int
    level: str            # resilient | moderate | fragile
    checks: list[Check]

    def passed(self, check_id: str) -> bool:
        return any(c.id == check_id and c.passed for c in self.checks)

    def as_dict(self) -> dict:
        return {
            "resource": self.ref, "score": self.score, "level": self.level,
            "checks": [{"id": c.id, "passed": c.passed, "note": c.note,
                        "remediation": c.remediation} for c in self.checks],
        }


@dataclass(frozen=True)
class Fault:
    name: str                       # our id, e.g. "pod-delete"
    litmus_experiment: str          # LitmusChaos experiment name
    category: str                   # pod | resource | network | disk
    blast: Blast
    description: str
    required: tuple[str, ...]       # readiness checks that MUST pass
    recommended: tuple[str, ...]    # checks that SHOULD pass
    env: dict = field(default_factory=dict)  # default experiment env


@dataclass(frozen=True)
class SafetyVerdict:
    fault: str
    ref: str
    allowed: bool
    blockers: list[str]
    warnings: list[str]
    guardrails: list[str]

    def as_dict(self) -> dict:
        return {
            "fault": self.fault, "resource": self.ref, "allowed": self.allowed,
            "blockers": self.blockers, "warnings": self.warnings, "guardrails": self.guardrails,
        }
