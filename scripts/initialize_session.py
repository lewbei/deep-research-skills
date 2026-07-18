#!/usr/bin/env python3
import os
import sys
import json
import shutil
import argparse
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description="Initialize Deep Research session and artifacts.")
    parser.add_argument("--total-minutes", type=int, default=120, help="Total time budget in minutes.")
    parser.add_argument("--kind", choices=["hard", "soft"], default="soft", help="Budget type.")
    parser.add_argument("--research-percent", type=int, default=40, help="Percent of budget allocated to research.")
    parser.add_argument("--workspace", default=os.getcwd(), help="Target workspace path.")
    return parser.parse_args()

def main():
    args = parse_args()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(os.path.dirname(script_dir), ".agents", "skills", "research-loop", "templates")
    
    if not os.path.exists(templates_dir):
        print(f"Error: Templates directory not found at {templates_dir}", file=sys.stderr)
        sys.exit(1)
        
    dr_dir = os.path.join(args.workspace, ".deep-research")
    os.makedirs(dr_dir, exist_ok=True)
    
    # 1. Instantiate session-state.json
    state_template_path = os.path.join(templates_dir, "session-state.json")
    state_target_path = os.path.join(dr_dir, "session-state.json")
    
    try:
        with open(state_template_path, "r") as f:
            state_data = json.load(f)
    except Exception as e:
        print(f"Error loading session-state template: {e}", file=sys.stderr)
        sys.exit(1)
        
    state_data["started_at"] = datetime.utcnow().isoformat() + "Z"
    state_data["last_updated_at"] = state_data["started_at"]
    state_data["budget"]["total_minutes"] = args.total_minutes
    state_data["budget"]["kind"] = args.kind
    state_data["budget"]["research_percent"] = args.research_percent
    state_data["budget"]["execution_percent"] = 100 - args.research_percent
    state_data["current_mode"] = "explore"
    
    with open(state_target_path, "w") as f:
        json.dump(state_data, f, indent=2)
    print(f"Initialized state at {state_target_path}")
    
    # 2. Copy other markdown templates to workspace root if they don't exist
    templates_to_copy = [
        "unknowns-registry.md",
        "landscape-table.md",
        "hypothesis-tree.md",
        "decision-log.md",
        "archive.md",
        "probe-registry.md",
        "time-budget.md",
        "proxy-log.md",
        "human-escalation-policy.md",
        "mega-plan.md"
    ]
    
    for filename in templates_to_copy:
        src = os.path.join(templates_dir, filename)
        dst = os.path.join(args.workspace, filename)
        if not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
                print(f"Created artifact: {filename}")
            except Exception as e:
                print(f"Error copying {filename}: {e}", file=sys.stderr)
        else:
            print(f"Artifact {filename} already exists. Skipping.")

    print("Deep Research session successfully initialized.")

if __name__ == "__main__":
    main()
