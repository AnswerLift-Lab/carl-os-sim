"""Shared data types for the Carl-OS reference implementation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Observation:
    """Raw signal emitted by the Environment each tick."""
    tick: int
    state: Dict[str, Any]


@dataclass
class Percept:
    """Structured interpretation produced by the Perception layer."""
    tick: int
    features: Dict[str, Any]
    change: float  # magnitude of change vs the previous percept
    triggered: bool = False


@dataclass
class MemoryContext:
    """What Memory recalls for the current percept."""
    recent_percepts: List[Percept] = field(default_factory=list)
    recent_actions: List["GovernedAction"] = field(default_factory=list)
    similar_past: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ProposedAction:
    """Candidate action produced by the Cognition layer (pre-governance)."""
    tick: int
    kind: str
    params: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""


@dataclass
class GovernedAction:
    """Action after Governance validation. Only stamped actions may execute."""
    tick: int
    kind: str
    approved: bool
    params: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    stamp: str = ""  # non-empty iff approved; checked structurally by Actuation
    modifications: Dict[str, Any] = field(default_factory=dict)
    veto_reason: str = ""


@dataclass
class LoopTrace:
    """Record of one full control-loop pass (for audit / transparency)."""
    tick: int
    percept: Percept
    proposals: List[ProposedAction] = field(default_factory=list)
    governed: List[GovernedAction] = field(default_factory=list)
    executed: List[GovernedAction] = field(default_factory=list)
    skipped: bool = False
