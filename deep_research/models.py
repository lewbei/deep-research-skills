import os
import sys
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict

@dataclass
class BudgetConfig:
    total_minutes: int = 120
    kind: str = "soft"
    research_percent: int = 40
    execution_percent: int = 60

@dataclass
class LedgerEntry:
    iteration: int
    phase: float
    start_iso: str
    end_iso: Optional[str] = None
    duration_minutes: float = 0.0
    category: str = "research"
    mode: str = "explore"

@dataclass
class SessionState:
    session_id: Optional[str] = None
    started_at: Optional[str] = None
    last_updated_at: Optional[str] = None
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    ledger: List[LedgerEntry] = field(default_factory=list)
    current_mode: str = "explore"
    thresholds_reached: Dict[str, bool] = field(default_factory=lambda: {
        "25": False,
        "50": False,
        "75": False,
        "90": False,
        "100": False
    })
    extensions: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        budget_data = data.get("budget", {})
        budget = BudgetConfig(
            total_minutes=budget_data.get("total_minutes", 120),
            kind=budget_data.get("kind", "soft"),
            research_percent=budget_data.get("research_percent", 40),
            execution_percent=budget_data.get("execution_percent", 60)
        )
        
        ledger = []
        for entry in data.get("ledger", []):
            ledger.append(LedgerEntry(
                iteration=entry.get("iteration"),
                phase=entry.get("phase"),
                start_iso=entry.get("start_iso"),
                end_iso=entry.get("end_iso"),
                duration_minutes=entry.get("duration_minutes", 0.0),
                category=entry.get("category", "research"),
                mode=entry.get("mode", "explore")
            ))
            
        return cls(
            session_id=data.get("session_id"),
            started_at=data.get("started_at"),
            last_updated_at=data.get("last_updated_at"),
            budget=budget,
            ledger=ledger,
            current_mode=data.get("current_mode", "explore"),
            thresholds_reached=data.get("thresholds_reached", {
                "25": False, "50": False, "75": False, "90": False, "100": False
            }),
            extensions=data.get("extensions", [])
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
