"""Resilience-scoring tests against the sample fleet."""
from pathlib import Path

import pytest

from chaos_lab import loader, readiness
from chaos_lab.models import PDB, REPLICAS, SPREAD

SAMPLE = Path(__file__).parent.parent / "examples" / "resources.json"


@pytest.fixture
def fleet():
    return loader.load(SAMPLE)   # (workloads, pdbs)


def _by(workloads, name):
    return next(w for w in workloads if w.name == name)


def test_loads_workloads_and_pdbs(fleet):
    workloads, pdbs = fleet
    assert len(workloads) == 4
    assert len(pdbs) == 2


def test_resilient_workload_scores_full(fleet):
    workloads, pdbs = fleet
    r = readiness.score(_by(workloads, "payments-api"), pdbs)
    assert r.score == 100 and r.level == "resilient"


def test_fragile_workload_scores_zero(fleet):
    workloads, pdbs = fleet
    r = readiness.score(_by(workloads, "catalog-web"), pdbs)
    assert r.level == "fragile"
    assert not r.passed(REPLICAS)


def test_moderate_workload_missing_pdb_and_spread(fleet):
    workloads, pdbs = fleet
    r = readiness.score(_by(workloads, "analytics"), pdbs)
    assert r.level == "moderate"
    assert not r.passed(PDB)
    assert not r.passed(SPREAD)
    assert r.passed(REPLICAS)


def test_pdb_matching_by_labels(fleet):
    workloads, pdbs = fleet
    assert loader.has_pdb(_by(workloads, "payments-api"), pdbs)
    assert not loader.has_pdb(_by(workloads, "analytics"), pdbs)
