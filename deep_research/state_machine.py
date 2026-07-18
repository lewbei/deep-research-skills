import os
import sys
import yaml
from datetime import datetime
from typing import Dict, List, Set, Any
from deep_research.models import SessionState, LedgerEntry
from deep_research.storage import save_session_state

DEFAULT_PHASES = {
    "1": {"category": "research", "transitions": ["2"], "required_artifacts": ["unknowns-registry.md"]},
    "2": {"category": "research", "transitions": ["3"]},
    "3": {"category": "research", "transitions": ["3.5"]},
    "3.5": {"category": "research", "transitions": ["4"]},
    "4": {"category": "research", "transitions": ["5", "7"]},
    "5": {"category": "research", "transitions": ["6"]},
    "6": {"category": "research", "transitions": ["7"]},
    "7": {"category": "execution", "transitions": ["4", "8"], "required_artifacts": ["mega-plan.md"]},
    "8": {"category": "execution", "transitions": ["9"]},
    "9": {"category": "execution", "transitions": ["3.5", "10"]},
    "10": {"category": "execution", "transitions": []}
}

RESEARCH_PHASES = {"1", "2", "3", "3.5", "4", "5", "6", "research", "feasibility", "landscape", "verify"}

def normalize_phase_str(p: Any) -> str:
    s = str(p)
    if s.endswith(".0"):
        return s[:-2]
    return s

def validate_graph_schema(phases_data: Dict[str, Any]):
    if not isinstance(phases_data, dict):
        raise ValueError("Root transitions config under 'phases' must be a dictionary mapping.")
        
    all_phases = {normalize_phase_str(p) for p in phases_data.keys()}
    
    # Require initial phase "1" or "init" or custom defined initial phase
    if not any(p in all_phases for p in ["1", "init"]):
        raise ValueError("Graph schema must define an initial phase (labeled '1' or 'init').")
        
    has_terminal = False
    for phase_name, cfg in phases_data.items():
        if not isinstance(cfg, dict):
            raise ValueError(f"Phase config for '{phase_name}' must be a dictionary.")
            
        transitions = cfg.get("transitions", [])
        if not isinstance(transitions, list):
            raise ValueError(f"Transitions for phase '{phase_name}' must be a list of target strings. Got {type(transitions)}.")
            
        for target in transitions:
            target_norm = normalize_phase_str(target)
            if target_norm not in all_phases:
                raise ValueError(f"Transition target '{target}' in phase '{phase_name}' does not exist in defined phases.")
                
        if len(transitions) == 0:
            has_terminal = True
            
    if not has_terminal:
        raise ValueError("Graph schema must have at least one terminal phase (with no exit transitions).")

def load_graph_config(workspace: str) -> Dict[str, Dict[str, Any]]:
    custom_path = os.path.join(workspace, ".deep-research", "transitions.yaml")
    if os.path.exists(custom_path):
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if not isinstance(data, dict) or "phases" not in data:
                    raise ValueError("Root key 'phases' missing in custom transitions.yaml")
                phases_data = data["phases"]
                validate_graph_schema(phases_data)
                
                # Convert format
                config = {}
                for phase, cfg in phases_data.items():
                    phase_norm = normalize_phase_str(phase)
                    config[phase_norm] = {
                        "category": cfg.get("category", "execution"),
                        "transitions": [normalize_phase_str(t) for t in cfg.get("transitions", [])],
                        "required_artifacts": cfg.get("required_artifacts", [])
                    }
                return config
        except Exception as e:
            # FAIL CLOSED: Raise exception on malformed transition config
            raise ValueError(f"Workflow execution blocked: Invalid transitions.yaml ({e})")
            
    # Normalize DEFAULT_PHASES
    normalized_defaults = {}
    for phase, cfg in DEFAULT_PHASES.items():
        phase_norm = normalize_phase_str(phase)
        normalized_defaults[phase_norm] = {
            "category": cfg["category"],
            "transitions": [normalize_phase_str(t) for t in cfg["transitions"]],
            "required_artifacts": cfg.get("required_artifacts", [])
        }
    return normalized_defaults

def check_phase_exit_requirements(workspace: str, phase_config: Dict[str, Any]):
    req_artifacts = phase_config.get("required_artifacts", [])
    for artifact in req_artifacts:
        artifact_path = os.path.join(workspace, artifact)
        if not os.path.exists(artifact_path):
            raise ValueError(f"Transition denied: Phase exit requirement missing. Artifact '{artifact}' must exist.")

def transition_phase(workspace: str, state: SessionState, from_p: str, to_p: str) -> str:
    # Normalize inputs
    from_p = normalize_phase_str(from_p)
    to_p = normalize_phase_str(to_p)
    
    # 1. Load configuration (fails closed if transitions.yaml is invalid)
    phases_config = load_graph_config(workspace)
    
    # 2. Get current phase
    current_phase = "1"
    if state.ledger:
        current_phase = normalize_phase_str(state.ledger[-1].phase)
            
    if current_phase != from_p:
        # Emergency exception: allow termination from ANY phase if mode is 'halt'
        if state.current_mode == "halt" and to_p == "10":
            pass
        else:
            raise ValueError(f"Current phase is {current_phase}, but requested transition is from {from_p}.")

    # 3. Enforce budget modes during transitions
    if state.current_mode == "halt":
        if to_p != "10":
            raise ValueError(f"Transition denied: Current mode is 'halt' (budget exhausted). Cannot transition to Phase {to_p}. Run Phase 10 emergency reflection.")
    else:
        # Check targets in normal mode
        phase_cfg = phases_config.get(from_p, {})
        allowed = list(phase_cfg.get("transitions", []))
        
        # Sprint escape edges: allows transitioning directly to Phase 7 (Mega-Plan) from current research phase
        if state.current_mode == "sprint":
            if from_p in ["3.5", "4", "5", "6"] and to_p == "7":
                allowed.append("7")
                
        if to_p not in allowed:
            raise ValueError(f"Transition from Phase {from_p} to Phase {to_p} is not allowed by the workflow graph schema.")
            
        # Sprint mode prohibits moving back into research phases
        target_cfg = phases_config.get(to_p, {})
        if state.current_mode == "sprint" and target_cfg.get("category") == "research":
            raise ValueError(f"Transition denied: Current mode is 'sprint' (research prohibited). Cannot transition to research Phase {to_p}.")

    # 4. Check exit requirements of from_p (except in emergency halt mode)
    if state.current_mode != "halt" and from_p in phases_config:
        check_phase_exit_requirements(workspace, phases_config[from_p])

    # 5. Approve transition and update ledger
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
    category = phases_config.get(to_p, {}).get("category", "execution")
    
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
