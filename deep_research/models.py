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

    def __post_init__(self):
        if self.total_minutes <= 0:
            raise ValueError(f"total_minutes must be positive, got {self.total_minutes}")
        if self.kind not in ["hard", "soft"]:
            raise ValueError(f"kind must be 'hard' or 'soft', got '{self.kind}'")
        if not (0 <= self.research_percent <= 100):
            raise ValueError(f"research_percent must be between 0 and 100, got {self.research_percent}")
        if not (0 <= self.execution_percent <= 100):
            raise ValueError(f"execution_percent must be between 0 and 100, got {self.execution_percent}")
        if self.research_percent + self.execution_percent != 100:
            raise ValueError(f"research_percent + execution_percent must equal 100, got {self.research_percent + self.execution_percent}")

@dataclass
class LedgerEntry:
    iteration: int
    phase: str  # Phase ID is now strictly a string
    start_iso: str
    end_iso: Optional[str] = None
    duration_minutes: float = 0.0
    category: str = "research"
    mode: str = "explore"

    def __post_init__(self):
        if self.iteration < 0:
            raise ValueError(f"iteration must be non-negative, got {self.iteration}")
        if not isinstance(self.phase, str) or not self.phase:
            raise ValueError(f"phase must be a non-empty string, got '{self.phase}'")
        for ts_name, ts_val in [("start_iso", self.start_iso), ("end_iso", self.end_iso)]:
            if ts_val is not None:
                try:
                    datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
                except ValueError:
                    raise ValueError(f"Invalid {ts_name} ISO-8601 format: '{ts_val}'")
        if self.duration_minutes < 0:
            raise ValueError(f"duration_minutes must be non-negative, got {self.duration_minutes}")
        if self.category not in ["research", "execution"]:
            raise ValueError(f"category must be 'research' or 'execution', got '{self.category}'")

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

    def __post_init__(self):
        if self.session_id is not None:
            try:
                uuid.UUID(self.session_id)
            except ValueError:
                raise ValueError(f"Invalid session_id UUID format: '{self.session_id}'")
                
        for ts_name, ts_val in [("started_at", self.started_at), ("last_updated_at", self.last_updated_at)]:
            if ts_val is not None:
                try:
                    datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
                except ValueError:
                    raise ValueError(f"Invalid {ts_name} ISO-8601 format: '{ts_val}'")
                    
        allowed_modes = ["explore", "commit", "sprint", "last-stand", "halt"]
        if self.current_mode not in allowed_modes:
            raise ValueError(f"current_mode must be one of {allowed_modes}, got '{self.current_mode}'")

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
            phase_raw = entry.get("phase")
            if phase_raw is None:
                raise ValueError("Ledger entry missing phase attribute.")
            phase_val = str(phase_raw)
            ledger.append(LedgerEntry(
                iteration=entry.get("iteration"),
                phase=phase_val,
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
