#!/usr/bin/env python3
import os
import sys
import argparse
from datetime import datetime
from deep_research.models import SessionState, BudgetConfig
from deep_research.storage import (
    load_session_state,
    save_session_state,
    get_templates_dir,
    atomic_copy
)
from deep_research.state_machine import transition_phase
from deep_research.budget import calculate_time_budget
from deep_research.proxies import add_proxy_observation
from deep_research.validation import validate_session_workspace

def drs_init(args):
    workspace = os.getcwd()
    templates_dir = get_templates_dir()
    
    if not os.path.exists(templates_dir):
        print(f"Error: Templates directory not found at {templates_dir}", file=sys.stderr)
        sys.exit(1)
        
    dr_dir = os.path.join(workspace, ".deep-research")
    os.makedirs(dr_dir, exist_ok=True)
    
    state_template_path = os.path.join(templates_dir, "session-state.json")
    
    try:
        import uuid
        with open(state_template_path, "r", encoding="utf-8") as f:
            import json
            data = json.load(f)
            
        state = SessionState.from_dict(data)
    except Exception as e:
        print(f"Error loading session-state template: {e}", file=sys.stderr)
        sys.exit(1)
        
    state.session_id = str(uuid.uuid4())
    state.started_at = datetime.utcnow().isoformat() + "Z"
    state.last_updated_at = state.started_at
    if state.ledger:
        state.ledger[0].start_iso = state.started_at
        state.ledger[0].end_iso = None
    state.budget.total_minutes = args.total_minutes
    state.budget.kind = args.kind
    state.budget.research_percent = args.research_percent
    state.budget.execution_percent = 100 - args.research_percent
    state.current_mode = "explore"
    
    save_session_state(workspace, state)
    print(f"Initialized Deep Research session (UUID: {state.session_id})")
    
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
        dst = os.path.join(workspace, filename)
        if not os.path.exists(dst):
            try:
                atomic_copy(src, dst)
                print(f"Created artifact: {filename}")
            except Exception as e:
                print(f"Error copying {filename}: {e}", file=sys.stderr)
        else:
            print(f"Artifact {filename} already exists. Skipping.")

def drs_status(args):
    workspace = os.getcwd()
    try:
        state = load_session_state(workspace)
        print(f"Session UUID: {state.session_id}")
        print(f"Started at:   {state.started_at}")
        print(f"Last updated: {state.last_updated_at}")
        print(f"Budget:       {state.budget.total_minutes} min ({state.budget.kind})")
        print(f"Current Mode: {state.current_mode}")
        if state.ledger:
            last_entry = state.ledger[-1]
            print(f"Current Phase:{last_entry.phase} ({last_entry.category})")
            print(f"Iteration:    {last_entry.iteration}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def drs_transition(args):
    workspace = os.getcwd()
    try:
        state = load_session_state(workspace)
        msg = transition_phase(workspace, state, args.from_phase, args.to_phase)
        print(msg)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def drs_budget(args):
    workspace = os.getcwd()
    try:
        state = load_session_state(workspace)
        msg = calculate_time_budget(workspace, state)
        print(msg)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def drs_proxy(args):
    workspace = os.getcwd()
    if args.add:
        try:
            p_val, t_val = map(float, args.add.split(":"))
            status, verdict, rho = add_proxy_observation(workspace, args.proxy_id, p_val, t_val)
            print(f"Proxy ID: {args.proxy_id}")
            print(f"Verdict:  {verdict}")
            print(f"Status:   {status}")
        except Exception as e:
            print(f"Error adding proxy observation: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Usage: drs proxy <proxy_id> --add <val>:<true>", file=sys.stderr)
        sys.exit(1)

def drs_validate(args):
    workspace = os.getcwd()
    package_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(package_dir)
    
    ok, errors = validate_session_workspace(workspace, project_root)
    if not ok:
        print("Validation FAILED with errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    print("All validations PASSED successfully.")

def main():
    parser = argparse.ArgumentParser(description="Deep Research state-machine runtime CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # init
    init_parser = subparsers.add_parser("init", help="Initialize deep research session")
    init_parser.add_argument("--total-minutes", type=int, default=120, help="Total minutes budget")
    init_parser.add_argument("--kind", choices=["hard", "soft"], default="soft", help="Budget kind")
    init_parser.add_argument("--research-percent", type=int, default=40, help="Allocated research percent")
    
    # status
    subparsers.add_parser("status", help="Show current state status")
    
    # transition
    trans_parser = subparsers.add_parser("transition", help="Transition phase in state machine")
    trans_parser.add_argument("from_phase", help="Current active phase")
    trans_parser.add_argument("to_phase", help="Target transition phase")
    
    # budget
    subparsers.add_parser("budget", help="Recalculate budget consumption and update targets")
    
    # proxy
    proxy_parser = subparsers.add_parser("proxy", help="Add proxy observations")
    proxy_parser.add_argument("proxy_id", help="Target Proxy ID (e.g. PX1)")
    proxy_parser.add_argument("--add", help="Data point as 'proxy_val:true_val'")
    
    # validate
    subparsers.add_parser("validate", help="Validate templates and frontmatter integrity")
    
    args = parser.parse_args()
    
    if args.command == "init":
        drs_init(args)
    elif args.command == "status":
        drs_status(args)
    elif args.command == "transition":
        drs_transition(args)
    elif args.command == "budget":
        drs_budget(args)
    elif args.command == "proxy":
        drs_proxy(args)
    elif args.command == "validate":
        drs_validate(args)

if __name__ == "__main__":
    main()
