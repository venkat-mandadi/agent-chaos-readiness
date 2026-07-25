"""Render readiness, safety verdicts, and the game-day plan."""
from __future__ import annotations

from .models import Readiness, SafetyVerdict
from .planner import WorkloadPlan

_LEVEL_MARK = {"resilient": "🟢", "moderate": "🟡", "fragile": "🔴"}


def readiness_text(r: Readiness) -> str:
    mark = _LEVEL_MARK.get(r.level, "")
    lines = [f"{mark} {r.ref} — resilience {r.score}/100 ({r.level})"]
    for c in r.checks:
        lines.append(f"    [{'✓' if c.passed else '✗'}] {c.id}: {c.note}")
        if not c.passed:
            lines.append(f"          → {c.remediation}")
    return "\n".join(lines)


def verdict_text(v: SafetyVerdict) -> str:
    head = "✅ SAFE" if v.allowed else "⛔ BLOCKED"
    lines = [f"{head} — {v.fault} on {v.ref}"]
    for b in v.blockers:
        lines.append(f"    blocker: {b}")
    for w in v.warnings:
        lines.append(f"    warning: {w}")
    return "\n".join(lines)


def plan_text(plans: list[WorkloadPlan]) -> str:
    out = ["CHAOS GAME-DAY PLAN", "=" * 72]
    for p in plans:
        out.append("")
        out.append(readiness_text(p.readiness))
        if p.runnable:
            out.append("  Run (safest first):")
            for v in p.runnable:
                out.append(f"    → {v.fault}")
        if p.blocked:
            out.append("  Fix before running:")
            for v in p.blocked:
                out.append(f"    ⛔ {v.fault} — {v.blockers[0] if v.blockers else 'blocked'}")
    return "\n".join(out)


def plan_markdown(plans: list[WorkloadPlan]) -> str:
    out = ["# 🧨 Chaos game-day plan", ""]
    for p in plans:
        r = p.readiness
        out.append(f"## {r.ref} — resilience **{r.score}/100** ({r.level})")
        if p.runnable:
            out.append("**Runnable (safest first):** " + ", ".join(f"`{v.fault}`" for v in p.runnable))
        if p.blocked:
            out.append("")
            out.append("| Blocked fault | Fix first |")
            out.append("| --- | --- |")
            for v in p.blocked:
                out.append(f"| `{v.fault}` | {v.blockers[0] if v.blockers else 'blocked'} |")
        out.append("")
    return "\n".join(out)
