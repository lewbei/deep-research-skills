import os
import json
import shutil
import tempfile
from typing import Dict, Any
from deep_research.models import SessionState

def get_session_state_path(workspace: str) -> str:
    return os.path.join(workspace, ".deep-research", "session-state.json")

def atomic_write_text(file_path: str, content: str):
    dir_name = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as f:
        temp_name = f.name
        f.write(content)
    os.replace(temp_name, file_path)

def atomic_write_json(file_path: str, data: Any):
    dir_name = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as f:
        temp_name = f.name
        json.dump(data, f, indent=2)
    os.replace(temp_name, file_path)

def load_session_state(workspace: str) -> SessionState:
    path = get_session_state_path(workspace)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Session state file not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return SessionState.from_dict(data)

def save_session_state(workspace: str, state: SessionState):
    path = get_session_state_path(workspace)
    atomic_write_json(path, state.to_dict())

def get_templates_dir() -> str:
    package_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(package_dir)
    return os.path.realpath(os.path.join(project_root, ".agents", "skills", "research-loop", "templates"))

def atomic_copy(src_path: str, dst_path: str):
    dir_name = os.path.dirname(os.path.abspath(dst_path))
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as f:
        temp_name = f.name
        with open(src_path, "r", encoding="utf-8") as src:
            f.write(src.read())
    os.replace(temp_name, dst_path)
