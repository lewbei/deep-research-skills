import os
import re
import json
from typing import List, Dict, Tuple
from deep_research.storage import atomic_write_json, atomic_write_text

def get_ranks(x: List[float]) -> List[float]:
    n = len(x)
    sorted_pairs = sorted(enumerate(x), key=lambda pair: pair[1])
    ranks = [0.0] * n
    
    i = 0
    while i < n:
        j = i
        while j < n and sorted_pairs[j][1] == sorted_pairs[i][1]:
            j += 1
        
        total_ranks_sum = sum(range(i + 1, j + 1))
        avg_rank = total_ranks_sum / (j - i)
        
        for k in range(i, j):
            original_index = sorted_pairs[k][0]
            ranks[original_index] = avg_rank
        
        i = j
    return ranks

def pearson_correlation(x: List[float], y: List[float]) -> float:
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

def spearman_correlation(x: List[float], y: List[float]) -> float:
    rx = get_ranks(x)
    ry = get_ranks(y)
    return pearson_correlation(rx, ry)

def add_proxy_observation(workspace: str, proxy_id: str, p_val: float, t_val: float) -> Tuple[str, str, float]:
    obs_path = os.path.join(workspace, ".deep-research", "proxy-observations.json")
    proxy_log_path = os.path.join(workspace, "proxy-log.md")
    
    obs_data = {}
    if os.path.exists(obs_path):
        try:
            with open(obs_path, "r", encoding="utf-8") as f:
                obs_data = json.load(f)
        except Exception:
            pass
            
    if proxy_id not in obs_data:
        obs_data[proxy_id] = []
        
    obs_data[proxy_id].append({"proxy": p_val, "true": t_val})
    atomic_write_json(obs_path, obs_data)
    
    observations = obs_data[proxy_id]
    n = len(observations)
    
    if n < 5:
        status = "candidate"
        verdict = f"Provisional (needs at least 5 paired observations, currently has {n})."
        rho = 0.0
    else:
        x = [o["proxy"] for o in observations]
        y = [o["true"] for o in observations]
        rho = spearman_correlation(x, y)
        
        if rho >= 0.7:
            status = "validated"
            verdict = f"Validated (Spearman rho = {rho:.3f}, strong correlation)."
        elif 0.4 <= rho < 0.7:
            status = "degraded"
            verdict = f"Degraded (Spearman rho = {rho:.3f}, weak correlation)."
        else:
            status = "rejected"
            verdict = f"Rejected (Spearman rho = {rho:.3f}, lack of correlation)."
            
    if os.path.exists(proxy_log_path):
        try:
            with open(proxy_log_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            pattern = re.compile(rf"### {proxy_id}:(.*?)(?=\n###|\n---|\Z)", re.DOTALL)
            match = pattern.search(content)
            
            if match:
                section_text = match.group(1)
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
                atomic_write_text(proxy_log_path, content)
        except Exception as e:
            print(f"Warning: Failed to update proxy-log.md: {e}")
            
    return status, verdict, rho
