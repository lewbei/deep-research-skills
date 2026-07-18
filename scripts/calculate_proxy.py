#!/usr/bin/env python3
import os
import sys
import json
import re
import tempfile

def get_ranks(x):
    n = len(x)
    sorted_pairs = sorted(enumerate(x), key=lambda pair: pair[1])
    ranks = [0.0] * n
    
    i = 0
    while i < n:
        j = i
        while j < n and sorted_pairs[j][1] == sorted_pairs[i][1]:
            j += 1
        
        # Average rank for elements from index i to j-1 (1-based ranking)
        total_ranks_sum = sum(range(i + 1, j + 1))
        avg_rank = total_ranks_sum / (j - i)
        
        for k in range(i, j):
            original_index = sorted_pairs[k][0]
            ranks[original_index] = avg_rank
        
        i = j
    return ranks

def pearson_correlation(x, y):
    n = len(x)
    if n < 2:
        return 0.0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den_x = sum((x[i] - mean_x) ** 2 for i in range(n))
    den_y = sum((y[i] - mean_y) ** 2 for i in range(n))
    
    if den_x == 0.0 or den_y == 0.0:
        return 0.0
    return num / ((den_x * den_y) ** 0.5)

def spearman_correlation(x, y):
    rx = get_ranks(x)
    ry = get_ranks(y)
    return pearson_correlation(rx, ry)

def atomic_write_text(file_path, content):
    dir_name = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as f:
        temp_name = f.name
        f.write(content)
    os.replace(temp_name, file_path)

def atomic_write_json(file_path, data):
    dir_name = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as f:
        temp_name = f.name
        json.dump(data, f, indent=2)
    os.replace(temp_name, file_path)

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
            
            # Save observations atomically
            atomic_write_json(obs_path, obs_data)
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
                
                # Replace status, correlation strength, validation evidence robustly
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
                
                # Write proxy-log.md atomically
                atomic_write_text(proxy_log_path, content)
                print(f"Updated {proxy_log_path} for {proxy_id}")
            else:
                print(f"Warning: Could not find section for {proxy_id} in {proxy_log_path}", file=sys.stderr)
        except Exception as e:
            print(f"Error updating proxy-log.md: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
