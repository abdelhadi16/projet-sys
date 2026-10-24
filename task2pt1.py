from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any


class EventType(str, Enum):
    PRESS = "PRESS"
    RELEASE = "RELEASE"


class VerdictAction(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    MODIFY = "MODIFY"
    INJECT = "INJECT"


class Modifier(str, Enum):
    SHIFT = "SHIFT"
    CTRL = "CTRL"
    ALT = "ALT"
    WIN = "WIN"
    CAPS_LOCK = "CAPS_LOCK"


@dataclass(slots=True)
class RawEvent:
    key_code: int
    scan_code: int
    event_type: EventType
    timestamp: float = field(default_factory=time.time)
    is_injected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "key_code": self.key_code,
            "scan_code": self.scan_code,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "is_injected": self.is_injected,
        }


@dataclass(slots=True)
class DecodedEvent:
    raw: RawEvent
    key_name: str
    character: str
    modifiers: list[Modifier] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": self.raw.to_dict(),
            "key_name": self.key_name,
            "character": self.character,
            "modifiers": [m.value for m in self.modifiers],
        }


@dataclass(slots=True)
class Context:
    window_title: str
    process_name: str
    process_id: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_title": self.window_title,
            "process_name": self.process_name,
            "process_id": self.process_id,
        }


@dataclass(slots=True)
class EnrichedEvent:
    decoded: DecodedEvent
    context: Context

    def to_dict(self) -> dict[str, Any]:
        return {
            "decoded": self.decoded.to_dict(),
            "context": self.context.to_dict(),
        }


@dataclass(slots=True)
class Verdict:
    action: VerdictAction
    rule_id: Optional[str] = None
    replacement_key: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "rule_id": self.rule_id,
            "replacement_key": self.replacement_key,
        }


@dataclass(slots=True)
class Rule:
    id: str
    enabled: bool = True
    priority: int = 0
    match_key: list[str] = field(default_factory=list)
    match_modifiers: list[Modifier] = field(default_factory=list)
    match_process: Optional[str] = None
    action: VerdictAction = VerdictAction.PASS
    replacement_key: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "enabled": self.enabled,
            "priority": self.priority,
            "match_key": self.match_key,
            "match_modifiers": [m.value for m in self.match_modifiers],
            "match_process": self.match_process,
            "action": self.action.value,
            "replacement_key": self.replacement_key,
        }


@dataclass(slots=True)
class RuleStore:
    rules: list[Rule] = field(default_factory=list)
    observe_only: bool = False
    version: int = 1


@dataclass(slots=True)
class LogEntry:
    enriched_event: EnrichedEvent
    verdict: Verdict
    logged_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enriched_event": self.enriched_event.to_dict(),
            "verdict": self.verdict.to_dict(),
            "logged_at": self.logged_at,
        }


def decide_action(event: EnrichedEvent, store: RuleStore) -> Verdict:
    if store.observe_only:
        return Verdict(action=VerdictAction.PASS, rule_id="observe_only")

    sorted_rules = sorted(store.rules, key=lambda r: r.priority, reverse=True)

    for rule in sorted_rules:
        if not rule.enabled:
            continue

        if rule.match_key and event.decoded.key_name not in rule.match_key:
            continue

        if rule.match_process and event.context.process_name != rule.match_process:
            continue

        if rule.match_modifiers:
            event_mods = set(event.decoded.modifiers)
            required_mods = set(rule.match_modifiers)
            if not required_mods.issubset(event_mods):
                continue

        return Verdict(
            action=rule.action,
            rule_id=rule.id,
            replacement_key=rule.replacement_key,
        )

    return Verdict(action=VerdictAction.PASS, rule_id=None)