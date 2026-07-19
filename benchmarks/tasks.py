import os
import yaml
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class RubricCriterion:
    text: str
    criterion_type: str           # "positive" or "negative"
    axis: str                     # factual_accuracy | breadth_depth | presentation | citation
    weight: int                   # positive for desired, negative for undesired

@dataclass
class BenchmarkTask:
    task_id: str
    domain: str
    prompt: str
    criteria: List[RubricCriterion]

def load_tasks_from_yaml(yaml_path: str) -> List[BenchmarkTask]:
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"Task file not found: {yaml_path}")
        
    with open(yaml_path, "r", encoding="utf-8") as f:
        raw_tasks = yaml.safe_load(f)
        
    tasks = []
    for item in raw_tasks:
        criteria = []
        for crit in item.get("criteria", []):
            criteria.append(RubricCriterion(
                text=crit["text"],
                criterion_type=crit["type"],
                axis=crit["axis"],
                weight=crit["weight"]
            ))
        tasks.append(BenchmarkTask(
            task_id=item["task_id"],
            domain=item["domain"],
            prompt=item["prompt"],
            criteria=criteria
        ))
    return tasks
