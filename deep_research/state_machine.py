import os
import sys
import yaml
from datetime import datetime
from typing import Dict, List
from deep_research.models import SessionState, LedgerEntry
from deep_research.storage import save_session_state

DEFAULT_TRANSITIONS = {
    "1": ["2"],
    "2": ["3"],
    "3": ["3.5"],
    "3.5": ["4"],
    "4": ["5", "7"],
    "5": ["6"],
    "6": ["7"],
    "7": ["4", "8"],
    "8": ["9"],
    "9": ["3.5", "10"],
    "10": []
}

RESEARCH_PHASES = {"1", "2", "3", "3.5", "4", "5", "6", "research", "feasibility", "landscape", "verify"}

def load_graph_transitions(workspace: str) -> Dict[str, List[str]]:
    custom_path = os.path.join(workspace, ".deep-research", "transitions.yaml")
    if os.path.exists(custom_path):
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if not isinstance(data, dict) or "phases" not in data:
                    raise ValueError("Root key 'phases' missing in custom transitions.yaml")
                transitions = {}
                for phase, cfg in data["phases"].items():
                    transitions[str(phase)] = [str(t) for t in cfg.get("transitions", [])]
                return transitions
        except Exception as e:
            # FAIL CLOSED: Raise exception on malformed transition config
            raise ValueError(f"Workflow execution blocked: Invalid transitions.yaml ({e})")
    return DEFAULT_TRANSITIONS

def transition_phase(workspace: str, state: SessionState, from_p: str, to_p: str) -> str:
    # 1. Load transitions map (fails closed if transitions.yaml is invalid)
    transitions = load_graph_transitions(workspace)
    
    # 2. Enforce budget modes during transitions
    if state.current_mode == "halt" and to_p != "10":
        raise ValueError(f"Transition denied: Current mode is 'halt' (budget exhausted). Cannot transition to Phase {to_p}. Run Phase 10 reflection.")
        
    if state.current_mode == "sprint" and to_p in RESEARCH_PHASES:
        raise ValueError(f"Transition denied: Current mode is 'sprint' (research prohibited). Cannot transition to research Phase {to_p}.")

    # 3. Get current phase
    current_phase = "1"
    if state.ledger:
        current_phase = str(state.ledger[-1].phase)
        # Strip float suffix if formatting slipped
        if current_phase.endswith(".0"):
            current_phase = current_phase[:-2]
            
    if current_phase != from_p:
        raise ValueError(f"Current phase is {current_phase}, but requested transition is from {from_p}.")
        
    allowed = transitions.get(from_p, [])
    if to_p not in allowed:
        raise ValueError(f"Transition from Phase {from_p} to Phase {to_p} is not allowed by the workflow graph schema.")
        
    # 4. Approve transition and update ledger
    now_str = datetime.utcnow().isoformat() + "Z"
    if state.ledger:
        last_entry = state.ledger[-1]
        if last_entry.end_iso is None:
            last_entry.end_iso = now_str
            start_t = datetime.fromisoformat(last_entry.start_iso.replace("Z", "+00:00"))
            end_t = datetime.fromisoformat(now_str.replace("Z", "+00:00"))
            last_entry.duration_minutes = (end_t - start_t).total_seconds() / 60.0
            
    # Add new phase entry to ledger
    new_iteration = state.ledger[-1].iteration + 1 if state.ledger else 0
    category = "research" if to_p in RESEARCH_PHASES else "execution"
    
    new_entry = LedgerEntry(
        iteration=new_iteration,
        phase=to_p,  # Stored strictly as string phase ID
        start_iso=now_str,
        category=category,
        mode=state.current_mode
    )
    state.ledger.append(new_entry)
    state.last_updated_at = now_str
    
    save_session_state(workspace, state)
    return f"Workflow advanced. Current phase: {to_p}"
