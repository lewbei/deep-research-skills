import os
import re
from datetime import datetime
from deep_research.models import SessionState
from deep_research.storage import save_session_state, atomic_write_text

def calculate_time_budget(workspace: str, state: SessionState) -> str:
    started_at = datetime.fromisoformat(state.started_at.replace("Z", "+00:00"))
    now = datetime.now(started_at.tzinfo)
    
    elapsed_minutes = (now - started_at).total_seconds() / 60.0
    total_minutes = state.budget.total_minutes
    research_percent = state.budget.research_percent
    execution_percent = state.budget.execution_percent
    
    research_budget = total_minutes * (research_percent / 100.0)
    execution_budget = total_minutes * (execution_percent / 100.0)
    
    elapsed_pct = (elapsed_minutes / total_minutes) * 100.0
    
    # Calculate research/execution elapsed based on the ledger categories
    research_elapsed = 0.0
    execution_elapsed = 0.0
    for entry in state.ledger:
        duration = entry.duration_minutes
        if entry.category == "research":
            research_elapsed += duration
        elif entry.category == "execution":
            execution_elapsed += duration
            
    # Include current running duration in the active category
    if state.ledger:
        last_entry = state.ledger[-1]
        if last_entry.end_iso is None:
            delta = (now - datetime.fromisoformat(last_entry.start_iso.replace("Z", "+00:00"))).total_seconds() / 60.0
            if last_entry.category == "research":
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
        
    state.current_mode = mode
    state.last_updated_at = now.isoformat() + "Z"
    
    # Update thresholds
    for threshold in ["25", "50", "75", "90", "100"]:
        if elapsed_pct >= float(threshold):
            state.thresholds_reached[threshold] = True
            
    # Save session state
    save_session_state(workspace, state)
    
    # Update time-budget.md markdown file if exists
    time_budget_path = os.path.join(workspace, "time-budget.md")
    if os.path.exists(time_budget_path):
        try:
            with open(time_budget_path, "r", encoding="utf-8") as f:
                content = f.read()
                
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
            
            for threshold in ["25", "50", "75", "90", "100"]:
                if state.thresholds_reached[threshold]:
                    content = content.replace(f"- [ ] {threshold}%", f"- [x] {threshold}%")
            
            atomic_write_text(time_budget_path, content)
        except Exception as e:
            return f"Error updating time-budget.md: {e}"
            
    return f"Updated time budget. Mode: {mode}, Elapsed: {elapsed_minutes:.1f} min"
