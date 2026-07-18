#!/usr/bin/env python3
import os
import sys
import json
import re
from datetime import datetime

def main():
    workspace = os.getcwd()
    state_path = os.path.join(workspace, ".deep-research", "session-state.json")
    time_budget_path = os.path.join(workspace, "time-budget.md")
    
    if not os.path.exists(state_path):
        print(f"Error: State file not found at {state_path}", file=sys.stderr)
        sys.exit(1)
        
    try:
        with open(state_path, "r") as f:
            state_data = json.load(f)
    except Exception as e:
        print(f"Error reading session-state JSON: {e}", file=sys.stderr)
        sys.exit(1)
        
    started_at = datetime.fromisoformat(state_data["started_at"].replace("Z", "+00:00"))
    now = datetime.now(started_at.tzinfo)
    
    elapsed_minutes = (now - started_at).total_seconds() / 60.0
    total_minutes = state_data["budget"]["total_minutes"]
    research_percent = state_data["budget"]["research_percent"]
    execution_percent = state_data["budget"]["execution_percent"]
    
    research_budget = total_minutes * (research_percent / 100.0)
    execution_budget = total_minutes * (execution_percent / 100.0)
    
    elapsed_pct = (elapsed_minutes / total_minutes) * 100.0
    
    # Calculate research/execution elapsed based on the ledger categories
    # In a simplified version, we attribute the elapsed time based on ratio or ledger records
    research_elapsed = 0.0
    execution_elapsed = 0.0
    for entry in state_data.get("ledger", []):
        duration = entry.get("duration_minutes", 0)
        if entry.get("category") == "research":
            research_elapsed += duration
        elif entry.get("category") == "execution":
            execution_elapsed += duration
            
    # Include current running duration in the active category
    if state_data.get("ledger"):
        last_entry = state_data["ledger"][-1]
        # If the last entry has not finished, we can add the current delta
        if last_entry.get("end_iso") == "<ISO-8601>":
            delta = (now - datetime.fromisoformat(last_entry["start_iso"].replace("Z", "+00:00"))).total_seconds() / 60.0
            if last_entry.get("category") == "research":
                research_elapsed += delta
            else:
                execution_elapsed += delta
                
    research_elapsed_pct = (research_elapsed / research_budget) * 100.0 if research_budget > 0 else 0
    execution_elapsed_pct = (execution_elapsed / execution_budget) * 100.0 if execution_budget > 0 else 0
    
    # Mode Transition Logic
    if elapsed_pct >= 100.0:
        mode = "halt"
        recommendation = "Hard stop. Run Phase 10 reflection and hand off."
    elif elapsed_pct >= 90.0:
        mode = "last-stand"
        recommendation = "Stop exploration; produce a submission/artifact from the best available branch immediately."
    elif elapsed_pct >= 75.0:
        mode = "sprint"
        recommendation = "No new research. Execute only the current best branch. Kill branches faster."
    elif elapsed_pct >= 50.0:
        mode = "commit"
        recommendation = "No new P2/P3 research. Only P0 blocking unknowns may be researched; execute best viable branch."
    else:
        mode = "explore"
        recommendation = "Normal operation. Investigate P0-P2 unknowns; research allowed."
        
    state_data["current_mode"] = mode
    state_data["last_updated_at"] = now.isoformat() + "Z"
    
    # Update thresholds
    for threshold in ["25", "50", "75", "90", "100"]:
        if elapsed_pct >= float(threshold):
            state_data["thresholds_reached"][threshold] = True
            
    # Save session state
    with open(state_path, "w") as f:
        json.dump(state_data, f, indent=2)
        
    # Update time-budget.md markdown file if exists
    if os.path.exists(time_budget_path):
        try:
            with open(time_budget_path, "r") as f:
                content = f.read()
                
            # Replace current state details
            content = re.sub(
                r"- \*\*Elapsed:\*\* .*?\n",
                f"- **Elapsed:** {elapsed_minutes:.1f} min ({elapsed_pct:.1f}% of T)\n",
                content
            )
            content = re.sub(
                r"- \*\*Research elapsed:\*\* .*?\n",
                f"- **Research elapsed:** {research_elapsed:.1f} min ({research_elapsed_pct:.1f}% of R)\n",
                content
            )
            content = re.sub(
                r"- \*\*Execution elapsed:\*\* .*?\n",
                f"- **Execution elapsed:** {execution_elapsed:.1f} min ({execution_elapsed_pct:.1f}% of E)\n",
                content
            )
            content = re.sub(
                r"- \*\*Current mode:\*\* .*?\n",
                f"- **Current mode:** `{mode}`\n",
                content
            )
            content = re.sub(
                r"- \*\*Recommended action:\*\* .*?\n",
                f"- **Recommended action:** {recommendation}\n",
                content
            )
            
            # Check off thresholds in the log
            for threshold in ["25", "50", "75", "90", "100"]:
                if state_data["thresholds_reached"][threshold]:
                    content = content.replace(f"- [ ] {threshold}%", f"- [x] {threshold}%")
            
            with open(time_budget_path, "w") as f:
                f.write(content)
                
            print(f"Updated time budget in {time_budget_path} (Mode: {mode}, Elapsed: {elapsed_minutes:.1f} min)")
        except Exception as e:
            print(f"Error updating time-budget.md: {e}", file=sys.stderr)
            
if __name__ == "__main__":
    main()
