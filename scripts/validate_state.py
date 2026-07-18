#!/usr/bin/env python3
import os
import sys
import re

def validate_frontmatter(skill_path):
    if not os.path.exists(skill_path):
        print(f"SKILL missing: {skill_path}")
        return False
        
    try:
        with open(skill_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Parse YAML frontmatter
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            print(f"Error: {skill_path} is missing standard frontmatter delimiter.")
            return False
            
        yaml_content = match.group(1)
        required_keys = ["name", "description"]
        missing = []
        for key in required_keys:
            if not re.search(rf"^{key}:", yaml_content, re.MULTILINE):
                missing.append(key)
                
        if missing:
            print(f"Error: {skill_path} frontmatter missing keys: {missing}")
            return False
            
        print(f"Frontmatter OK: {skill_path}")
        return True
    except Exception as e:
        print(f"Error reading {skill_path}: {e}")
        return False

def validate_artifact(workspace, filename, expected_headers):
    path = os.path.join(workspace, filename)
    if not os.path.exists(path):
        print(f"Artifact missing: {filename}")
        return False
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        missing_headers = []
        for header in expected_headers:
            if header not in content:
                missing_headers.append(header)
                
        if missing_headers:
            print(f"Error: {filename} missing expected sections/headers: {missing_headers}")
            return False
            
        print(f"Artifact OK: {filename}")
        return True
    except Exception as e:
        print(f"Error validating {filename}: {e}")
        return False

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    workspace = os.getcwd()
    
    success = True
    
    # 1. Validate skills frontmatter
    skills_dir = os.path.join(project_root, ".agents", "skills")
    if os.path.exists(skills_dir):
        for skill_name in os.listdir(skills_dir):
            skill_p = os.path.join(skills_dir, skill_name, "SKILL.md")
            if os.path.exists(skill_p):
                if not validate_frontmatter(skill_p):
                    success = False
                    
    # 2. Validate workspace artifacts if initialized
    state_path = os.path.join(workspace, ".deep-research", "session-state.json")
    if os.path.exists(state_path):
        artifacts = {
            "unknowns-registry.md": ["# Unknowns Registry", "## Open unknowns", "## Answered unknowns"],
            "time-budget.md": ["# Time Budget", "## Budget definition", "## Budget ledger", "## Current state"],
            "hypothesis-tree.md": ["# Hypothesis Tree", "## Active branches", "## Confidence scoring mapping"],
            "decision-log.md": ["# Decision Log", "## Key decisions"],
            "proxy-log.md": ["# Proxy Log", "## Proxy statuses", "## Trivial-proxy ban list"],
            "human-escalation-policy.md": ["# Human Escalation Policy", "## When to escalate", "## Preventive triggers", "## Reactive triggers"],
            "mega-plan.md": ["# Mega-Plan", "## 1. Goal restatement", "## 2. Selected approach", "## 3. Milestone plan"]
        }
        
        for filename, headers in artifacts.items():
            if not validate_artifact(workspace, filename, headers):
                success = False
    else:
        print("Note: Session not initialized in current directory. Skipping workspace artifact checks.")
        
    if not success:
        print("Validation FAILED.", file=sys.stderr)
        sys.exit(1)
        
    print("All validations PASSED successfully.")

if __name__ == "__main__":
    main()
