"""The Carl-OS recursive control loop.

Event-driven: the environment is sensed every tick, but the full
Perception -> Memory -> Cognition -> Governance -> Orchestration ->
Actuation sequence only runs when the perceived change meets the
meaningful-state-change threshold. Actuation's effects become the next
tick's environment, which is the recursion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .layers import default_layers
from .types import LoopTrace


@dataclass
class LoopStats:
    ticks: int = 0
    runs: int = 0       # full loop executions
    skips: int = 0      # ticks below threshold (perception only)
    traces: List[LoopTrace] = field(default_factory=list)


class ControlLoop:
    """One Carl-OS agent: seven layers + threshold-gated recursive loop."""

    LAYER_ORDER = ("perception", "memory", "cognition", "governance",
                   "orchestration", "actuation")

    def __init__(self, layers: Optional[Dict[str, Any]] = None,
                 threshold: float = 0.3):
        self.layers: Dict[str, Any] = layers or default_layers()
        self.threshold = threshold
        self.stats = LoopStats()
        self._check_wiring()

    def _check_wiring(self) -> None:
        missing = [k for k in ("environment", *self.LAYER_ORDER)
                   if k not in self.layers]
        if missing:
            raise ValueError(f"missing layers: {missing}")

    def tick(self, force: bool = False) -> Optional[LoopTrace]:
        L = self.layers
        obs = L["environment"].sense()
        percept = L["perception"].process(obs)
        self.stats.ticks += 1

        if not force and percept.change < self.threshold:
            self.stats.skips += 1
            # environment still evolves; the agent simply does not engage
            L["environment"].evolve()
            L["memory"].store_percept(percept)
            return None

        self.stats.runs += 1
        L["memory"].store_percept(percept)
        ctx = L["memory"].recall(percept)
        proposals = L["cognition"].decide(percept, ctx)
        governed = L["governance"].validate(proposals, percept)
        plan = L["orchestration"].sequence(governed)
        effects = L["actuation"].execute(plan)
        L["environment"].apply(effects)
        L["environment"].evolve()
        for a in plan:
            L["memory"].store_action(a)

        trace = LoopTrace(tick=obs.tick, percept=percept,
                          proposals=proposals, governed=governed,
                          executed=plan)
        self.stats.traces.append(trace)
        return trace

    def run(self, ticks: int, force: bool = False) -> LoopStats:
        for _ in range(ticks):
            self.tick(force=force)
        return self.stats

    # -- live layer replacement (modularity: layers are swappable) --
    def swap_layer(self, name: str, new_layer: Any) -> Any:
        if name not in self.layers:
            raise KeyError(f"unknown layer: {name}")
        old = self.layers[name]
        self.layers[name] = new_layer
        self._check_wiring()
        return old
