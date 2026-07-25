"""Catalog of chaos faults, mapped to LitmusChaos experiments.

Each fault declares the readiness checks that *must* pass to run it safely
(`required`) and those that *should* (`recommended`). That's what turns "inject
chaos" into "inject chaos only where the system can take it."
"""
from __future__ import annotations

from .models import LIMITS, PROBES, REPLICAS, SPREAD, Blast, Fault

CATALOG: list[Fault] = [
    Fault(
        "pod-delete", "pod-delete", "pod", Blast.LOW,
        "Kill a percentage of the workload's pods to test self-healing and traffic draining.",
        required=(REPLICAS,), recommended=(PROBES,),
        env={"TOTAL_CHAOS_DURATION": "60", "CHAOS_INTERVAL": "10", "PODS_AFFECTED_PERC": "25", "FORCE": "false"},
    ),
    Fault(
        "pod-cpu-hog", "pod-cpu-hog", "resource", Blast.MEDIUM,
        "Saturate CPU inside a pod to test throttling, autoscaling, and latency SLOs.",
        required=(LIMITS,), recommended=(REPLICAS,),
        env={"TOTAL_CHAOS_DURATION": "60", "CPU_CORES": "1"},
    ),
    Fault(
        "pod-memory-hog", "pod-memory-hog", "resource", Blast.MEDIUM,
        "Consume memory inside a pod to test OOM handling and limits.",
        required=(LIMITS,), recommended=(REPLICAS,),
        env={"TOTAL_CHAOS_DURATION": "60", "MEMORY_CONSUMPTION": "500"},
    ),
    Fault(
        "pod-network-latency", "pod-network-latency", "network", Blast.MEDIUM,
        "Inject network latency to test timeouts, retries, and dependency resilience.",
        required=(PROBES,), recommended=(REPLICAS,),
        env={"TOTAL_CHAOS_DURATION": "60", "NETWORK_LATENCY": "2000", "JITTER": "0"},
    ),
    Fault(
        "pod-network-loss", "pod-network-loss", "network", Blast.HIGH,
        "Drop a percentage of packets to test partition tolerance and failover.",
        required=(REPLICAS, PROBES), recommended=(SPREAD,),
        env={"TOTAL_CHAOS_DURATION": "60", "NETWORK_PACKET_LOSS_PERCENTAGE": "100"},
    ),
    Fault(
        "disk-fill", "disk-fill", "disk", Blast.HIGH,
        "Fill ephemeral storage to test disk-pressure handling and eviction.",
        required=(LIMITS, REPLICAS), recommended=(SPREAD,),
        env={"TOTAL_CHAOS_DURATION": "60", "FILL_PERCENTAGE": "80"},
    ),
]

BY_NAME = {f.name: f for f in CATALOG}
