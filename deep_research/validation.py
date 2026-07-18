import os
import re
import json
from typing import Dict, List, Tuple
from deep_research.models import SessionState

def validate_frontmatter(skill_path: str) -> Tuple[bool, str]:
    if not os.path.exists(skill_path):
        return False, f"SKILL file missing: {skill_path}"
        
    try:
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        match = re.match(r"^---\r?\n(.*?)\r?\n---", content, re.DOTALL)
        if not match:
            return False, "Missing standard frontmatter delimiter (---)."
            
        yaml_content = match.group(1)
        required_keys = ["name", "description"]
        missing = []
        for key in required_keys:
            if not re.search(rf"^{key}:", yaml_content, re.MULTILINE):
                missing.append(key)
                
        if missing:
            return False, f"Frontmatter missing keys: {missing}"
            
        return True, "Frontmatter OK"
    except Exception as e:
        return False, f"Error reading {skill_path}: {e}"

def validate_artifact(workspace: str, filename: str, expected_headers: List[str]) -> Tuple[bool, str]:
    path = os.path.join(workspace, filename)
    if not os.path.exists(path):
        return False, f"Artifact missing: {filename}"
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        missing_headers = []
        for header in expected_headers:
            if header not in content:
                missing_headers.append(header)
                
        if missing_headers:
            return False, f"{filename} missing expected headers: {missing_headers}"
            
        return True, f"Artifact OK: {filename}"
    except Exception as e:
        return False, f"Error validating {filename}: {e}"

def validate_session_state_schema(workspace: str) -> List[str]:
    from deep_research.storage import get_session_state_path, load_session_state
    from deep_research.state_machine import load_graph_config
    
    path = get_session_state_path(workspace)
    if not os.path.exists(path):
        return ["session-state.json file is missing"]
        
    errors = []
    try:
        # Loading states instantiates dataclass validation checks
        state = load_session_state(workspace)
        
        # Verify budget constraints
        if state.budget.research_percent + state.budget.execution_percent != 100:
            errors.append(f"Invalid budget percentages: R={state.budget.research_percent}% and E={state.budget.execution_percent}% must sum to 100%")
            
        # Verify ledger consistency
        graph_config = load_graph_config(workspace)
        phases_map = graph_config.get("phases", {})
        initial_phase = graph_config.get("initial_phase", "1")
        sprint_target = graph_config.get("sprint_target", "7")
        terminal_phase = graph_config.get("terminal_phase", "10")
        
        if state.ledger:
            first_entry = state.ledger[0]
            if first_entry.phase != initial_phase:
                errors.append(f"Ledger error: Initial ledger entry phase '{first_entry.phase}' does not match graph initial_phase '{initial_phase}'")
        
        last_phase = None
        for i, entry in enumerate(state.ledger):
            if entry.iteration != i:
                errors.append(f"Ledger inconsistency: iteration index {entry.iteration} does not match slot {i}")
            current_phase = entry.phase
            
            # Verify phase is defined in active graph
            if current_phase not in phases_map:
                errors.append(f"Ledger error: phase '{current_phase}' does not exist in the active graph config")
            else:
                expected_cat = phases_map[current_phase].get("category", "execution")
                if entry.category != expected_cat:
                    errors.append(f"Ledger error: phase '{current_phase}' category '{entry.category}' does not match graph category '{expected_cat}'")
            
            if i > 0 and last_phase is not None:
                allowed_next = phases_map.get(last_phase, {}).get("transitions", [])
                
                # Check sprint mode bypasses: allows research phases to escape directly to sprint_target
                last_cfg = phases_map.get(last_phase, {})
                is_sprint_bypass = (entry.mode == "sprint" and last_cfg.get("category") == "research" and current_phase == sprint_target)
                # Check halt mode emergency reflections: allows any phase to escape to terminal_phase
                is_halt_bypass = (entry.mode == "halt" and current_phase == terminal_phase)
                
                if not (is_sprint_bypass or is_halt_bypass or current_phase in allowed_next):
                    errors.append(f"Ledger transition error: phase {current_phase} is not an approved edge from phase {last_phase} in the active graph config")
            last_phase = current_phase
            
    except Exception as e:
        errors.append(f"State schema validation error: {e}")
        
    return errors

def validate_session_workspace(workspace: str, project_root: str) -> Tuple[bool, List[str]]:
    errors = []
    
    # 1. Validate skills frontmatter
    skills_dir = os.path.join(project_root, ".agents", "skills")
    if os.path.exists(skills_dir):
        for skill_name in os.listdir(skills_dir):
            skill_p = os.path.join(skills_dir, skill_name, "SKILL.md")
            if os.path.exists(skill_p):
                ok, msg = validate_frontmatter(skill_p)
                if not ok:
                    errors.append(f"{skill_name} skill error: {msg}")
                    
    # 2. Validate workspace artifacts
    state_path = os.path.join(workspace, ".deep-research", "session-state.json")
    if os.path.exists(state_path):
        # Validate state JSON structure and ledger integrity
        state_errors = validate_session_state_schema(workspace)
        errors.extend(state_errors)
        
        artifacts = {
            "unknowns-registry.md": ["# Unknowns Registry", "## Open unknowns", "## Answered unknowns"],
            "time-budget.md": ["# Time Budget", "## Budget definition", "## Budget ledger", "## Current state"],
            "hypothesis-tree.md": ["# Hypothesis Tree", "## Branch statuses", "## Entry format", "## Active / selected branches"],
            "decision-log.md": ["# Decision Log", "## Entry format", "## Decisions"],
            "proxy-log.md": ["# Proxy Log", "## Proxy statuses", "## Trivial-proxy ban list"],
            "human-escalation-policy.md": ["# Human Escalation Policy", "## When to escalate", "## Preventive triggers", "## Reactive triggers"],
            "mega-plan.md": ["# Mega-Plan", "## 1. Goal restatement", "## 2. Selected approach", "## 3. Milestone plan"]
        }
        
        for filename, headers in artifacts.items():
            ok, msg = validate_artifact(workspace, filename, headers)
            if not ok:
                errors.append(msg)
    else:
        errors.append("Session state not initialized in this workspace directory.")
        
    return len(errors) == 0, errors
