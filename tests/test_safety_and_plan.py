"""Safety-gate, planner, and manifest-generation tests."""
from pathlib import Path

import pytest

from chaos_lab import faults, litmus, loader, planner, readiness, safety

SAMPLE = Path(__file__).parent.parent / "examples" / "resources.json"


@pytest.fixture
def fleet():
    return loader.load(SAMPLE)


def _by(workloads, name):
    return next(w for w in workloads if w.name == name)


def _gate(fleet, workload, fault):
    workloads, pdbs = fleet
    w = _by(workloads, workload)
    return safety.assess(w, readiness.score(w, pdbs), faults.BY_NAME[fault])


def test_pod_delete_blocked_on_single_replica(fleet):
    v = _gate(fleet, "catalog-web", "pod-delete")
    assert not v.allowed
    assert any("single replica" in b for b in v.blockers)


def test_pod_delete_allowed_on_replicated(fleet):
    assert _gate(fleet, "analytics", "pod-delete").allowed
    assert _gate(fleet, "payments-api", "pod-delete").allowed


def test_cpu_hog_blocked_without_limits(fleet):
    v = _gate(fleet, "catalog-web", "pod-cpu-hog")
    assert not v.allowed
    assert any("limits" in b for b in v.blockers)


def test_network_loss_needs_replicas_and_probes(fleet):
    assert not _gate(fleet, "catalog-web", "pod-network-loss").allowed


def test_stateful_workload_gets_a_warning(fleet):
    v = _gate(fleet, "orders-db", "pod-delete")
    assert v.allowed  # it's resilient
    assert any("stateful" in w for w in v.warnings)


def test_guardrails_always_present(fleet):
    v = _gate(fleet, "payments-api", "pod-delete")
    assert any("abort" in g.lower() for g in v.guardrails)


def test_game_day_orders_by_resilience(fleet):
    workloads, pdbs = fleet
    plans = planner.game_day(workloads, pdbs)
    scores = [p.readiness.score for p in plans]
    assert scores == sorted(scores, reverse=True)
    # the fragile workload has nothing runnable and some blocked
    frag = next(p for p in plans if p.ref.endswith("catalog-web"))
    assert frag.runnable == []
    assert frag.blocked


def test_manifest_generated_only_when_safe(fleet):
    workloads, pdbs = fleet
    pay = _by(workloads, "payments-api")
    m = litmus.chaosengine(pay, faults.BY_NAME["pod-delete"])
    assert m["kind"] == "ChaosEngine"
    assert m["spec"]["appinfo"]["applabel"] == "app=payments-api"
    probe = m["spec"]["experiments"][0]["spec"]["probe"][0]
    assert probe["mode"] == "Continuous"
    assert probe["runProperties"]["stopOnFailure"] is True   # auto-abort baked in


def test_blast_ordering(fleet):
    workloads, pdbs = fleet
    plan = planner.plan_workload(_by(workloads, "analytics"), pdbs)
    blasts = [faults.BY_NAME[v.fault].blast.value for v in plan.runnable]
    order = {"low": 0, "medium": 1, "high": 2}
    assert [order[b] for b in blasts] == sorted(order[b] for b in blasts)
