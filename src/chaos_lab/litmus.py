"""Generate a LitmusChaos ChaosEngine manifest for an approved experiment.

The generated manifest bakes in the two things that make chaos safe: a
**steady-state probe** (the hypothesis — "the service stays healthy") running
continuously, with ``stopOnFailure`` so the experiment **auto-aborts** the moment
steady state breaks. You review it, then `kubectl apply` it in a controlled
window — the engine never runs it for you.
"""
from __future__ import annotations

import json

from .models import Fault, Workload


def _steady_state_probe(service_host: str) -> dict:
    """A continuous health probe that aborts the experiment if it fails."""
    return {
        "name": "app-stays-healthy",
        "type": "httpProbe",
        "mode": "Continuous",
        "httpProbe/inputs": {
            "url": f"http://{service_host}/healthz",
            "insecureSkipVerify": False,
            "method": {"get": {"criteria": "==", "responseCode": "200"}},
        },
        "runProperties": {
            "probeTimeout": "2s",
            "interval": "2s",
            "retry": 1,
            "stopOnFailure": True,   # <-- auto-abort when steady state breaks
        },
    }


def chaosengine(w: Workload, fault: Fault, service_host: str | None = None) -> dict:
    host = service_host or f"{w.app_label}.{w.namespace}.svc.cluster.local"
    env = [{"name": k, "value": str(v)} for k, v in fault.env.items()]
    return {
        "apiVersion": "litmuschaos.io/v1alpha1",
        "kind": "ChaosEngine",
        "metadata": {"name": f"{w.app_label}-{fault.name}", "namespace": w.namespace},
        "spec": {
            "appinfo": {"appns": w.namespace, "applabel": f"app={w.app_label}", "appkind": w.kind.lower()},
            "engineState": "active",
            "chaosServiceAccount": "litmus-admin",
            "experiments": [{
                "name": fault.litmus_experiment,
                "spec": {
                    "components": {"env": env},
                    "probe": [_steady_state_probe(host)],
                },
            }],
        },
    }


def to_yaml(manifest: dict) -> str:
    """YAML if PyYAML is available, otherwise JSON (kubectl accepts both)."""
    try:
        import yaml
        return yaml.safe_dump(manifest, sort_keys=False)
    except ImportError:  # pragma: no cover
        return json.dumps(manifest, indent=2)
