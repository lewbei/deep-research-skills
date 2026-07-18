#!/usr/bin/env python3
import os
import sys
import json
import re

def get_ranks(x):
    n = len(x)
    temp = [(val, i) for i, val in enumerate(x)]
    temp.sort()
    ranks = [0] * n
    i = 0
    while i < n:
        j = i
        while j < n and temp[j][0] == temp[i][0]:
            j += 1
        # average rank for ties
        mean_rank = (i + j + 1) / 2.0
        for k in range(i, j):
            ranks[temp[k][1]] = mean_rank
        i = j
    return ranks

def spearman_correlation(x, y):
    n = len(x)
    if n < 2:
        return 0.0
    rx = get_ranks(x)
    ry = get_ranks(y)
    
    d2 = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    rho = 1.0 - (6.0 * d2) / (n * (n**2 - 1))
    return rho

def main():
    if len(sys.argv) < 2:
        print("Usage: calculate_proxy.py <proxy_id> [--add <proxy_val>:<true_val>]", file=sys.stderr)
        sys.exit(1)
        
    proxy_id = sys.argv[1]
    workspace = os.getcwd()
    obs_path = os.path.join(workspace, ".deep-research", "proxy-observations.json")
    proxy_log_path = os.path.join(workspace, "proxy-log.md")
    
    # Load observations
    obs_data = {}
    if os.path.exists(obs_path):
        try:
            with open(obs_path, "r") as f:
                obs_data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load observations from {obs_path}: {e}", file=sys.stderr)
            
    if proxy_id not in obs_data:
        obs_data[proxy_id] = []
        
    # Check if we need to add a new observation
    if "--add" in sys.argv:
        try:
            idx = sys.argv.index("--add")
            val_str = sys.argv[idx + 1]
            p_val, t_val = map(float, val_str.split(":"))
            obs_data[proxy_id].append({"proxy": p_val, "true": t_val})
            
            # Save observations
            os.makedirs(os.path.dirname(obs_path), exist_ok=True)
            with open(obs_path, "w") as f:
                json.dump(obs_data, f, indent=2)
            print(f"Added observation for {proxy_id}: Proxy={p_val}, True={t_val}")
        except Exception as e:
            print(f"Error parsing --add value: {e}", file=sys.stderr)
            sys.exit(1)
            
    observations = obs_data[proxy_id]
    n = len(observations)
    
    print(f"Proxy: {proxy_id}, Observations count: {n}")
    
    if n < 5:
        status = "candidate"
        verdict = f"Provisional (needs at least 5 paired observations, currently has {n})."
        rho = 0.0
    else:
        x = [o["proxy"] for o in observations]
        y = [o["true"] for o in observations]
        rho = spearman_correlation(x, y)
        
        # Check standard thresholds
        if rho >= 0.7:
            status = "validated"
            verdict = f"Validated (Spearman rho = {rho:.3f}, strong correlation)."
        elif 0.4 <= rho < 0.7:
            status = "degraded"
            verdict = f"Degraded (Spearman rho = {rho:.3f}, weak correlation)."
        else:
            status = "rejected"
            verdict = f"Rejected (Spearman rho = {rho:.3f}, lack of correlation)."
            
    print(f"Calculation Result: Status={status}, Details={verdict}")
    
    # Update proxy-log.md if it exists
    if os.path.exists(proxy_log_path):
        try:
            with open(proxy_log_path, "r") as f:
                content = f.read()
                
            # Find the section for proxy_id
            pattern = re.compile(rf"### {proxy_id}:(.*?)(?=\n###|\n---|\Z)", re.DOTALL)
            match = pattern.search(content)
            
            if match:
                section_text = match.group(1)
                
                # Replace status, correlation strength, validation evidence
                new_section = re.sub(
                    r"- \*\*Status:\*\* (.*?)\n",
                    f"- **Status:** {status}\n",
                    section_text
                )
                
                obs_list_str = ", ".join([f"({o['proxy']},{o['true']})" for o in observations])
                new_section = re.sub(
                    r"- \*\*Validation evidence:\*\* (.*?)\n",
                    f"- **Validation evidence:** {obs_list_str if obs_list_str else 'none'}\n",
                    new_section
                )
                new_section = re.sub(
                    r"- \*\*Correlation strength:\*\* (.*?)\n",
                    f"- **Correlation strength:** SPEARMAN r = {rho:.3f} ({status})\n",
                    new_section
                )
                
                content = content.replace(match.group(0), f"### {proxy_id}:{new_section}")
                
                with open(proxy_log_path, "w") as f:
                    f.write(content)
                print(f"Updated {proxy_log_path} for {proxy_id}")
            else:
                print(f"Warning: Could not find section for {proxy_id} in {proxy_log_path}", file=sys.stderr)
        except Exception as e:
            print(f"Error updating proxy-log.md: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
