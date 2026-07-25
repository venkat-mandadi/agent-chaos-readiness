#!/usr/bin/env python3
"""Entry point the skill calls. Wires ``src/`` onto the path so a fresh clone
runs without a ``pip install``.

    python scripts/chaos_plan.py <resources.json> plan
    python scripts/chaos_plan.py <resources.json> gate <workload> <fault>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from chaos_lab.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
