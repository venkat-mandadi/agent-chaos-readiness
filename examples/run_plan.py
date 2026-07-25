"""Runnable demo — no cluster needed.

    python examples/run_plan.py

Scores resilience, prints the game-day plan, and shows one generated
LitmusChaos manifest for an experiment that passed the safety gate.
"""
from pathlib import Path

from chaos_lab import faults, litmus, loader, planner, readiness, report, safety

HERE = Path(__file__).parent


def main() -> None:
    workloads, pdbs = loader.load(HERE / "resources.json")

    print(report.plan_text(planner.game_day(workloads, pdbs)))

    print("\n\n### EXAMPLE GATE (unsafe) ###")
    catalog = next(w for w in workloads if w.name == "catalog-web")
    print(report.verdict_text(safety.assess(catalog, readiness.score(catalog, pdbs),
                                            faults.BY_NAME["pod-delete"])))

    print("\n### GENERATED LITMUSCHAOS MANIFEST (payments-api / pod-delete) ###")
    pay = next(w for w in workloads if w.name == "payments-api")
    print(litmus.to_yaml(litmus.chaosengine(pay, faults.BY_NAME["pod-delete"])))


if __name__ == "__main__":
    main()
