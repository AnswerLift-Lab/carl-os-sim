"""The seven Carl-OS layers.

Each layer is a small class with a single responsibility and a swappable
implementation. Layer boundaries are the point: Perception never decides,
Cognition never actuates, and Actuation structurally refuses any action that
does not carry a Governance stamp.
"""
from __future__ import annotations

import math
import random
import uuid
from typing import Any, Callable, Dict, List, Optional

from .types import (
    GovernedAction,
    LoopTrace,
    MemoryContext,
    Observation,
    Percept,
    ProposedAction,
)


# ---------------------------------------------------------------- environment
class Environment:
    """Layer 7: the operational context. Source of stimuli, recipient of acts."""

    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        self.state: Dict[str, Any] = dict(initial_state or {})
        self.tick = 0

    def sense(self) -> Observation:
        """Emit the current raw observation. Called every tick."""
        return Observation(tick=self.tick, state=dict(self.state))

    def apply(self, effects: List[Dict[str, Any]]) -> None:
        """Apply actuation effects (does not advance time)."""
        for effect in effects:
            self._apply_effect(effect)

    def evolve(self) -> None:
        """Advance the world one tick (dynamics independent of actuation)."""
        self.tick += 1

    def _apply_effect(self, effect: Dict[str, Any]) -> None:
        for key, value in effect.get("set", {}).items():
            self.state[key] = value
        for key, delta in effect.get("add", {}).items():
            self.state[key] = self.state.get(key, 0.0) + delta


class SignalEnvironment(Environment):
    """Environment emitting noisy signals with occasional genuine events.

    Used by exp1: most ticks are noise, some ticks carry genuine state
    changes that a threshold trigger must catch.
    """

    def __init__(self, n_features: int = 4, seed: int = 0,
                 n_events: int = 40, noise_std: float = 0.05):
        super().__init__({f"f{i}": 0.0 for i in range(n_features)})
        self.rng = random.Random(seed)
        self.noise_std = noise_std
        self.n_features = n_features
        self.n_events = n_events
        # Pre-schedule genuine events: (tick, feature, magnitude)
        self.events: List[tuple] = []
        self.event_ticks = set()
        self._fired: set = set()

    def schedule_events(self, horizon: int, tail: int = 0) -> None:
        # 'tail' reserves ticks at the horizon end so every event's response
        # window falls inside the run (an event on the final tick could never
        # be observed, which would fake a miss).
        span = max(1, horizon - tail)
        ticks = self.rng.sample(range(span), min(self.n_events, span))
        for t in ticks:
            f = self.rng.randrange(self.n_features)
            mag = self.rng.uniform(0.6, 1.0) * self.rng.choice([-1, 1])
            self.events.append((t, f, mag))
            self.event_ticks.add(t)

    def evolve(self) -> None:  # noqa: D102
        # world dynamics run every tick, whether or not the agent acted
        for i in range(self.n_features):
            key = f"f{i}"
            self.state[key] = self.state.get(key, 0.0) * 0.98  # mean reversion
            self.state[key] += self.rng.gauss(0.0, self.noise_std)
        for (t, f, mag) in self.events:
            if t == self.tick and (t, f) not in self._fired:
                self.state[f"f{f}"] += mag
                self._fired.add((t, f))
        self.tick += 1

    def genuine_event_at(self, tick: int) -> bool:
        return tick in self.event_ticks


# ---------------------------------------------------------------- perception
class Perception:
    """Layer 4: raw signals -> structured percept + change magnitude."""

    def __init__(self):
        self._previous: Optional[Dict[str, Any]] = None
        self.calls = 0

    def process(self, obs: Observation) -> Percept:
        self.calls += 1
        features = self._interpret(obs.state)
        change = self._change_magnitude(features)
        self._previous = features
        return Percept(tick=obs.tick, features=features, change=change)

    def _interpret(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {k: (float(v) if isinstance(v, (int, float)) else v)
                for k, v in state.items()}

    def _change_magnitude(self, features: Dict[str, Any]) -> float:
        if self._previous is None:
            return 0.0
        sq = 0.0
        for k, v in features.items():
            if isinstance(v, (int, float)) and isinstance(
                    self._previous.get(k), (int, float)):
                sq += (v - self._previous[k]) ** 2
        return math.sqrt(sq)


# -------------------------------------------------------------------- memory
class Memory:
    """Layer 3: contextual state storage. Every percept/action is recorded;
    recall provides the temporal comparator for the current percept."""

    def __init__(self, window: int = 50):
        self.window = window
        self.percepts: List[Percept] = []
        self.actions: List[GovernedAction] = []
        self.calls = 0

    def store_percept(self, percept: Percept) -> None:
        self.percepts.append(percept)
        self.percepts = self.percepts[-self.window:]

    def store_action(self, action: GovernedAction) -> None:
        self.actions.append(action)
        self.actions = self.actions[-self.window:]

    def recall(self, percept: Percept) -> MemoryContext:
        self.calls += 1
        return MemoryContext(
            recent_percepts=list(self.percepts[-5:]),
            recent_actions=list(self.actions[-5:]),
            similar_past=self._find_similar(percept),
        )

    def _find_similar(self, percept: Percept) -> List[Dict[str, Any]]:
        # naive similarity: past percepts whose feature vector is close
        out = []
        for p in self.percepts:
            d = 0.0
            n = 0
            for k, v in percept.features.items():
                if isinstance(v, (int, float)) and isinstance(
                        p.features.get(k), (int, float)):
                    d += (v - p.features[k]) ** 2
                    n += 1
            if n and math.sqrt(d) < 0.2 and p.tick != percept.tick:
                out.append({"tick": p.tick, "distance": math.sqrt(d)})
        return out[-3:]


# ----------------------------------------------------------------- cognition
class Cognition:
    """Layer 1: reasoning & planning. Proposes actions; never executes."""

    def __init__(self, policy: Optional[Callable] = None):
        self.policy = policy or (lambda percept, ctx: [])
        self.calls = 0

    def decide(self, percept: Percept, ctx: MemoryContext) -> List[ProposedAction]:
        self.calls += 1
        proposals = self.policy(percept, ctx)
        for p in proposals:
            p.tick = percept.tick
        return proposals


# ---------------------------------------------------------------- governance
class Governance:
    """Layer 5: policy & constraints. Validates every proposal BEFORE it can
    be sequenced or executed. Approved actions carry a stamp; the stamp is
    what Actuation checks, so governance cannot be bypassed by wiring."""

    def __init__(self, constraints: Optional[List[Callable]] = None):
        # Each constraint: fn(proposal) -> (ok: bool, reason: str, fix: dict)
        self.constraints: List[Callable] = list(constraints or [])
        self.calls = 0
        self.audit: List[Dict[str, Any]] = []
        self.vetoes = 0
        self.approvals = 0

    def validate(self, proposals: List[ProposedAction],
                 percept: Percept) -> List[GovernedAction]:
        self.calls += 1
        out: List[GovernedAction] = []
        for p in proposals:
            approved, reasons, fixes = True, [], {}
            for constraint in self.constraints:
                ok, reason, fix = constraint(p)
                fixes.update(fix or {})  # repairs apply even when approved
                if not ok:
                    approved = False
                    reasons.append(reason)
            params = dict(p.params)
            params.update(fixes)  # governance may clamp/repair, not just veto
            action = GovernedAction(
                tick=p.tick, kind=p.kind, approved=approved,
                params=params, rationale=p.rationale,
                stamp=uuid.uuid4().hex if approved else "",
                modifications=fixes, veto_reason="; ".join(reasons),
            )
            if approved:
                self.approvals += 1
            else:
                self.vetoes += 1
            self.audit.append({
                "tick": p.tick, "kind": p.kind, "approved": approved,
                "reasons": reasons, "fixes": fixes,
            })
            out.append(action)
        return out


# -------------------------------------------------------------- orchestration
class Orchestration:
    """Layer 2: task coordination. Sequences approved actions only."""

    def __init__(self):
        self.calls = 0

    def sequence(self, actions: List[GovernedAction]) -> List[GovernedAction]:
        self.calls += 1
        # Only stamped actions may be sequenced; ordering by priority param.
        approved = [a for a in actions if a.approved and a.stamp]
        approved.sort(key=lambda a: a.params.get("priority", 0), reverse=True)
        return approved


# ----------------------------------------------------------------- actuation
class Actuation:
    """Layer 6: execution. STRUCTURAL INVARIANT: refuses any action without
    a valid governance stamp. There is no code path from proposal to effect
    that skips Governance."""

    def __init__(self, effect_fn: Optional[Callable] = None):
        self.effect_fn = effect_fn or (lambda a: {"set": {}, "add": {}})
        self.calls = 0
        self.refusals = 0
        self.executed: List[GovernedAction] = []

    def execute(self, actions: List[GovernedAction]) -> List[Dict[str, Any]]:
        self.calls += 1
        effects = []
        for a in actions:
            if not (a.approved and a.stamp):
                # structural refusal: ungoverned actions cannot execute
                self.refusals += 1
                continue
            self.executed.append(a)
            effects.append(self.effect_fn(a))
        return effects


# ------------------------------------------------------------- layer bundle
def default_layers(**overrides) -> Dict[str, Any]:
    """Assemble the seven layers; any layer may be overridden (modularity)."""
    layers = {
        "environment": Environment(),
        "perception": Perception(),
        "memory": Memory(),
        "cognition": Cognition(),
        "governance": Governance(),
        "orchestration": Orchestration(),
        "actuation": Actuation(),
    }
    layers.update(overrides)
    return layers
