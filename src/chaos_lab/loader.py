"""Load workloads and PodDisruptionBudgets from a kubectl -o json dump.

Workloads and PDBs come from the same dump; PDBs are matched to workloads by
namespace + label selector so the readiness check knows whether a workload is
protected during voluntary disruption.
"""
from __future__ import annotations

import json
from pathlib import Path

from .models import Workload

WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet"}


def _items(text: str) -> list[dict]:
    data = json.loads(text)
    if isinstance(data, dict) and data.get("kind") == "List":
        return data.get("items", [])
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return []


def load(path: str | Path) -> tuple[list[Workload], list[dict]]:
    """Return (workloads, pdbs) parsed from the dump."""
    items = _items(Path(path).read_text())
    workloads = [Workload(x) for x in items if x.get("kind") in WORKLOAD_KINDS]
    pdbs = [x for x in items if x.get("kind") == "PodDisruptionBudget"]
    return workloads, pdbs


def has_pdb(w: Workload, pdbs: list[dict]) -> bool:
    """True if a PDB in the same namespace selects this workload's pods."""
    for pdb in pdbs:
        meta = pdb.get("metadata", {})
        if meta.get("namespace", "default") != w.namespace:
            continue
        match = (pdb.get("spec", {}).get("selector", {}) or {}).get("matchLabels", {}) or {}
        if match and all(w.labels.get(k) == v for k, v in match.items()):
            return True
    return False
