#!/usr/bin/env python3
import os
import sys
import json
import tempfile
from datetime import datetime

ALLOWED_TRANSITIONS = {
    "1": ["2"],
    "2": ["3"],
    "3": ["3.5"],
    "3.5": ["4"],
    "4": ["5", "7"],
    "5": ["6"],
    "6": ["7"],
    "7": ["8", "4"], # Phase 7 can go back to Phase 4 if no branch is ready for execution
    "8": ["9"],
    "9": ["3.5", "10"],
    "10": []
}

def atomic_write_json(file_path, data):
    dir_name = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as f:
        temp_name = f.name
        json.dump(data, f, indent=2)
    os.replace(temp_name, file_path)

def main():
    if len(sys.argv) < 3:
        print("Usage: advance_phase.py <from_phase> <to_phase>", file=sys.stderr)
        sys.exit(1)
        
    from_p = sys.argv[1]
    to_p = sys.argv[2]
    
    workspace = os.getcwd()
    state_path = os.path.join(workspace, ".deep-research", "session-state.json")
    
    if not os.path.exists(state_path):
        print(f"Error: Session state not initialized. Run initialize_session.py first.", file=sys.stderr)
        sys.exit(1)
        
    try:
        with open(state_path, "r") as f:
            state_data = json.load(f)
    except Exception as e:
        print(f"Error reading session-state: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Get current active phase from ledger
    current_phase = str(state_data.get("ledger", [{}])[-1].get("phase", "1"))
    
    # Strict graph validation check (no bypass)
    if current_phase != from_p:
        print(f"Error: Current recorded phase is {current_phase}, but requested transition is from {from_p}.", file=sys.stderr)
        sys.exit(1)
        
    allowed = ALLOWED_TRANSITIONS.get(from_p, [])
    if to_p not in allowed:
        print(f"Error: Transition from Phase {from_p} to Phase {to_p} is not allowed by the workflow graph schema.", file=sys.stderr)
        sys.exit(1)
            
    print(f"Transition approved: Phase {from_p} -> Phase {to_p}")
    
    # Close current phase in ledger if any entry is open
    now_str = datetime.utcnow().isoformat() + "Z"
    if state_data.get("ledger"):
        last_entry = state_data["ledger"][-1]
        if last_entry.get("end_iso") is None:
            last_entry["end_iso"] = now_str
            start_t = datetime.fromisoformat(last_entry["start_iso"].replace("Z", "+00:00"))
            end_t = datetime.fromisoformat(now_str.replace("Z", "+00:00"))
            last_entry["duration_minutes"] = (end_t - start_t).total_seconds() / 60.0
            
    # Add new phase entry to ledger
    new_entry = {
        "iteration": state_data["ledger"][-1]["iteration"] + 1 if state_data.get("ledger") else 0,
        "phase": float(to_p) if "." in to_p else int(to_p),
        "start_iso": now_str,
        "end_iso": None,
        "duration_minutes": 0,
        "category": "research" if to_p in ["1", "2", "3", "3.5", "4", "5", "6"] else "execution",
        "mode": state_data.get("current_mode", "explore")
    }
    state_data["ledger"].append(new_entry)
    state_data["last_updated_at"] = now_str
    
    # Save updated session state atomically
    atomic_write_json(state_path, state_data)
        
    print(f"Workflow advanced. Current phase: {to_p}")

if __name__ == "__main__":
    main()
