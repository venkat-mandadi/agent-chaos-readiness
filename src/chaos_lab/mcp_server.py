"""MCP server exposing chaos planning as agent tools.

Lets a Claude agent score resilience, gate a proposed experiment, plan a game
day, and generate a LitmusChaos manifest — while the safety logic stays
deterministic and tested. It never injects a fault.

    python -m chaos_lab.mcp_server examples/resources.json

``mcp`` is an optional dependency (pip install "agent-chaos-readiness[mcp]").
"""
from __future__ import annotations

import sys

from . import faults as fault_catalog
from . import litmus, loader, planner, readiness, safety

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    FastMCP = None


def build_server(resources_path: str) -> FastMCP:
    if FastMCP is None:  # pragma: no cover
        raise SystemExit('The "mcp" package is required. Install: pip install "agent-chaos-readiness[mcp]"')

    mcp = FastMCP("agent-chaos-readiness")

    def _load():
        return loader.load(resources_path)

    def _find(workloads, name):
        return next((w for w in workloads if w.name == name or w.ref == name), None)

    @mcp.tool()
    def resilience_scores() -> list[dict]:
        """Resilience readiness score for every workload."""
        workloads, pdbs = _load()
        return [readiness.score(w, pdbs).as_dict() for w in workloads]

    @mcp.tool()
    def game_day_plan() -> list[dict]:
        """A safest-first chaos game-day plan across the fleet."""
        workloads, pdbs = _load()
        return [p.as_dict() for p in planner.game_day(workloads, pdbs)]

    @mcp.tool()
    def gate(workload: str, fault: str) -> dict:
        """Go/no-go for running `fault` on `workload`, with reasons and guardrails."""
        workloads, pdbs = _load()
        w = _find(workloads, workload)
        f = fault_catalog.BY_NAME.get(fault)
        if w is None or f is None:
            return {"error": "unknown workload or fault"}
        return safety.assess(w, readiness.score(w, pdbs), f).as_dict()

    @mcp.tool()
    def generate_manifest(workload: str, fault: str) -> dict:
        """Generate a LitmusChaos ChaosEngine — only if the experiment is safe."""
        workloads, pdbs = _load()
        w = _find(workloads, workload)
        f = fault_catalog.BY_NAME.get(fault)
        if w is None or f is None:
            return {"error": "unknown workload or fault"}
        v = safety.assess(w, readiness.score(w, pdbs), f)
        if not v.allowed:
            return {"refused": True, "blockers": v.blockers}
        return litmus.chaosengine(w, f)

    return mcp


def main() -> None:  # pragma: no cover
    if len(sys.argv) < 2:
        print("usage: python -m chaos_lab.mcp_server <resources.json>", file=sys.stderr)
        raise SystemExit(2)
    build_server(sys.argv[1]).run()


if __name__ == "__main__":  # pragma: no cover
    main()
