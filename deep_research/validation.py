import os
import re
from typing import Dict, List, Tuple

def validate_frontmatter(skill_path: str) -> Tuple[bool, str]:
    if not os.path.exists(skill_path):
        return False, f"SKILL file missing: {skill_path}"
        
    try:
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
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
