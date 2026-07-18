import os
from pathlib import Path
import sys
import yaml
import re
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
    "5": {"category": "research", "transitions": ["6"], "required_artifacts": ["probe-registry.md"]},
    "6": {"category": "research", "transitions": ["7"]},
    "7": {"category": "execution", "transitions": ["4", "8"], "required_artifacts": ["mega-plan.md"]},
    "8": {"category": "execution", "transitions": ["9"], "required_artifacts": ["proxy-log.md"]},
    "9": {"category": "execution", "transitions": ["3.5", "10"]},
    "10": {"category": "execution", "transitions": []}
}

class UniqueSafeLoader(yaml.SafeLoader):
    """
    A custom SafeLoader that fails on duplicate YAML mapping keys
    to prevent silent overrides (e.g. key '2' and float key '2.0').
    """
    def construct_mapping(self, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(f"Duplicate mapping key detected: '{key}'")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return super().construct_mapping(node, deep=deep)

def normalize_phase_str(value: Any) -> str:
    text = str(value)
    if re.fullmatch(r"-?\d+\.0", text):
        return text[:-2]
    return text

def validate_graph_schema(phases_data: Dict[str, Any], initial_phase: str, terminal_phase: str, sprint_target: str):
    if not isinstance(phases_data, dict):
        raise ValueError("Root transitions config under 'phases' must be a dictionary mapping.")
        
    normalized_keys = {}
    for raw_phase in phases_data.keys():
        norm_phase = normalize_phase_str(raw_phase)
        if norm_phase in normalized_keys:
            raise ValueError(f"Graph schema contains duplicate normalized phase keys: '{raw_phase}' and '{normalized_keys[norm_phase]}' both normalize to '{norm_phase}'.")
        normalized_keys[norm_phase] = raw_phase
        
    all_phases = set(normalized_keys.keys())
    
    if initial_phase not in all_phases:
        raise ValueError(f"Graph schema initial_phase '{initial_phase}' does not exist in defined phases.")
    if terminal_phase not in all_phases:
        raise ValueError(f"Graph schema terminal_phase '{terminal_phase}' does not exist in defined phases.")
    if sprint_target not in all_phases:
        raise ValueError(f"Graph schema sprint_target '{sprint_target}' does not exist in defined phases.")
        
    terminal_key = normalized_keys[terminal_phase]
    terminal_cfg = phases_data[terminal_key]
    if terminal_cfg.get("transitions"):
        raise ValueError(f"terminal_phase '{terminal_phase}' must have no outgoing transitions.")
        
    sprint_key = normalized_keys[sprint_target]
    sprint_cfg = phases_data[sprint_key]
    if sprint_cfg.get("category", "execution") != "execution":
        raise ValueError(f"sprint_target '{sprint_target}' must have category 'execution'.")
        
    has_terminal = False
    for phase_name, cfg in phases_data.items():
        if not isinstance(cfg, dict):
            raise ValueError(f"Phase config for '{phase_name}' must be a dictionary.")
            
        # Validate category
        category = cfg.get("category", "execution")
        if category not in {"research", "execution"}:
            raise ValueError(f"Phase '{phase_name}' category must be 'research' or 'execution', got '{category}'.")
            
        # Validate required artifacts schema
        req_artifacts = cfg.get("required_artifacts", [])
        if not isinstance(req_artifacts, list):
            raise ValueError(f"required_artifacts for phase '{phase_name}' must be a list.")
        for art in req_artifacts:
            if not isinstance(art, str) or not art.strip():
                raise ValueError(f"required_artifacts entries in phase '{phase_name}' must be non-empty strings.")
            if os.path.isabs(art):
                raise ValueError(f"required_artifacts entry '{art}' in phase '{phase_name}' must be a relative path.")
                
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

def load_graph_config(workspace: str) -> Dict[str, Any]:
    custom_path = os.path.join(workspace, ".deep-research", "transitions.yaml")
    if os.path.exists(custom_path):
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                data = yaml.load(f, Loader=UniqueSafeLoader)
                if not isinstance(data, dict):
                    raise ValueError("Transitions config must be a dictionary mapping.")
                
                # Retrieve phase control metadata
                initial_phase = normalize_phase_str(data.get("initial_phase", "1"))
                terminal_phase = normalize_phase_str(data.get("terminal_phase", "10"))
                sprint_target = normalize_phase_str(data.get("sprint_target", "7"))
                
                phases_data = data.get("phases", {})
                validate_graph_schema(phases_data, initial_phase, terminal_phase, sprint_target)
                
                # Convert format
                config = {
                    "initial_phase": initial_phase,
                    "terminal_phase": terminal_phase,
                    "sprint_target": sprint_target,
                    "phases": {}
                }
                for phase, cfg in phases_data.items():
                    phase_norm = normalize_phase_str(phase)
                    config["phases"][phase_norm] = {
                        "category": cfg.get("category", "execution"),
                        "transitions": [normalize_phase_str(t) for t in cfg.get("transitions", [])],
                        "required_artifacts": cfg.get("required_artifacts", [])
                    }
                return config
        except Exception as e:
            # FAIL CLOSED: Raise exception on malformed transition config
            raise ValueError(f"Workflow execution blocked: Invalid transitions.yaml ({e})")
            
    # Normalize DEFAULT_PHASES
    normalized_defaults = {
        "initial_phase": "1",
        "terminal_phase": "10",
        "sprint_target": "7",
        "phases": {}
    }
    for phase, cfg in DEFAULT_PHASES.items():
        phase_norm = normalize_phase_str(phase)
        normalized_defaults["phases"][phase_norm] = {
            "category": cfg["category"],
            "transitions": [normalize_phase_str(t) for t in cfg["transitions"]],
            "required_artifacts": cfg.get("required_artifacts", [])
        }
    return normalized_defaults

def check_phase_exit_requirements(workspace: str, phase_config: Dict[str, Any]):
    req_artifacts = phase_config.get("required_artifacts", [])
    root = Path(workspace).resolve()
    
    for artifact in req_artifacts:
        try:
            artifact_path = (root / artifact).resolve(strict=False)
            artifact_path.relative_to(root)
        except ValueError:
            raise ValueError(f"Transition denied: Artifact path '{artifact}' escapes the workspace directory boundaries.")
            
        if not artifact_path.exists():
            raise ValueError(f"Transition denied: Phase exit requirement missing. Artifact '{artifact}' must exist.")
            
        if not artifact_path.is_file():
            raise ValueError(f"Transition denied: Required artifact '{artifact}' must be a regular file.")
            
        text_artifacts = {"unknowns-registry.md", "probe-registry.md", "proxy-log.md", "mega-plan.md"}
        if artifact in text_artifacts:
            with open(artifact_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Enforce structured evidence completion heuristics
            if artifact == "unknowns-registry.md":
                if "placeholder — replace with first real unknown" in content:
                    raise ValueError("Transition denied: 'unknowns-registry.md' still contains template placeholder. Extract and document the real unknowns.")
            elif artifact == "probe-registry.md":
                # Only require a probe if a provisional-high-risk unknown exists in unknowns-registry.md
                has_high_risk = False
                reg_path = root / "unknowns-registry.md"
                if reg_path.exists():
                    with open(reg_path, "r", encoding="utf-8") as rf:
                        reg_content = rf.read()
                    if "provisional-high-risk" in reg_content:
                        has_high_risk = True
                
                if has_high_risk and not re.search(r"### P\d+:", content):
                    raise ValueError("Transition denied: 'probe-registry.md' must document at least one probe script because a provisional-high-risk unknown exists.")
            elif artifact == "proxy-log.md":
                if "placeholder — replace with first real proxy" in content:
                    raise ValueError("Transition denied: 'proxy-log.md' still contains template placeholder. Define and record actual proxy metrics.")
            elif artifact == "mega-plan.md":
                if "[Project Title]" in content:
                    raise ValueError("Transition denied: 'mega-plan.md' still contains template placeholder ([Project Title]). Document the project plan details.")

def transition_phase(workspace: str, state: SessionState, from_p: str, to_p: str) -> str:
    # Normalize inputs
    from_p = normalize_phase_str(from_p)
    to_p = normalize_phase_str(to_p)
    
    # 1. Load configuration (fails closed if transitions.yaml is invalid)
    graph_config = load_graph_config(workspace)
    phases = graph_config["phases"]
    initial_phase = graph_config["initial_phase"]
    terminal_phase = graph_config["terminal_phase"]
    sprint_target = graph_config["sprint_target"]
    
    # 2. Get current phase
    current_phase = initial_phase
    if state.ledger:
        current_phase = normalize_phase_str(state.ledger[-1].phase)
            
    # Require the real current phase during transitions unconditionally (including halt mode)
    if current_phase != from_p:
        raise ValueError(f"Current phase is {current_phase}, but requested transition is from {from_p}.")

    # 3. Enforce budget modes during transitions
    if state.current_mode == "halt":
        if to_p != terminal_phase:
            raise ValueError(f"Transition denied: Current mode is 'halt' (budget exhausted). Cannot transition to Phase {to_p}. Run emergency reflection transition to {terminal_phase}.")
    else:
        # Check targets in normal mode
        phase_cfg = phases.get(from_p, {})
        allowed = list(phase_cfg.get("transitions", []))
        
        # Sprint escape edges: allows transitioning directly to sprint_target from current research phase
        if state.current_mode == "sprint":
            from_cfg = phases.get(from_p, {})
            if from_cfg.get("category") == "research" and sprint_target in phases:
                allowed.append(sprint_target)
                
        if to_p not in allowed:
            raise ValueError(f"Transition from Phase {from_p} to Phase {to_p} is not allowed by the workflow graph schema.")
            
        # Sprint mode prohibits moving back into research phases
        target_cfg = phases.get(to_p, {})
        if state.current_mode == "sprint" and target_cfg.get("category") == "research":
            raise ValueError(f"Transition denied: Current mode is 'sprint' (research prohibited). Cannot transition to research Phase {to_p}.")

    # 4. Check exit requirements of from_p (except in emergency halt mode)
    if state.current_mode != "halt" and from_p in phases:
        check_phase_exit_requirements(workspace, phases[from_p])

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
    category = phases.get(to_p, {}).get("category", "execution")
    
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
