"""Command-line entry point.

    chaos-plan <resources.json> readiness
    chaos-plan <resources.json> plan [--format text|markdown]
    chaos-plan <resources.json> gate <workload> <fault>
    chaos-plan <resources.json> manifest <workload> <fault>
    chaos-plan <resources.json> faults

Runs offline against a kubectl -o json dump. It never injects a fault — it
scores, gates, and generates manifests for a human to apply.
"""
from __future__ import annotations

import argparse

from . import faults as fault_catalog
from . import litmus, loader, planner, readiness, report, safety


def _find(workloads, name):
    for w in workloads:
        if w.name == name or w.ref == name:
            return w
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="chaos-plan",
                                description="Score resilience, gate chaos experiments, and generate LitmusChaos manifests.")
    p.add_argument("resources", help="kubectl -o json dump (workloads + PDBs)")
    p.add_argument("mode", choices=["readiness", "plan", "gate", "manifest", "faults"])
    p.add_argument("workload", nargs="?", help="workload name (gate/manifest)")
    p.add_argument("fault", nargs="?", help="fault name (gate/manifest)")
    p.add_argument("--format", choices=["text", "markdown"], default="text")
    args = p.parse_args(argv)

    if args.mode == "faults":
        for f in fault_catalog.CATALOG:
            print(f"{f.name:20} [{f.blast.value:6}] {f.description}")
        return 0

    workloads, pdbs = loader.load(args.resources)

    if args.mode == "readiness":
        for w in workloads:
            print(report.readiness_text(readiness.score(w, pdbs)))
            print()
        return 0

    if args.mode == "plan":
        plans = planner.game_day(workloads, pdbs)
        print(report.plan_markdown(plans) if args.format == "markdown" else report.plan_text(plans))
        return 0

    # gate / manifest need a workload + fault
    w = _find(workloads, args.workload)
    if w is None:
        p.error(f"unknown workload '{args.workload}'")
    f = fault_catalog.BY_NAME.get(args.fault)
    if f is None:
        p.error(f"unknown fault '{args.fault}'. Try: {', '.join(sorted(fault_catalog.BY_NAME))}")

    ready = readiness.score(w, pdbs)
    verdict = safety.assess(w, ready, f)

    if args.mode == "gate":
        print(report.verdict_text(verdict))
        for g in verdict.guardrails:
            print(f"    guardrail: {g}")
        return 0

    # manifest
    if not verdict.allowed:
        print(f"# ⛔ Refusing to generate a manifest — {f.name} is unsafe on {w.ref}:")
        for b in verdict.blockers:
            print(f"#   - {b}")
        return 1
    print(litmus.to_yaml(litmus.chaosengine(w, f)))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
