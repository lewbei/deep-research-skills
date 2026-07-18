#!/usr/bin/env python3
import os
import sys
import shutil

def main():
    workspace = os.getcwd()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_skills = os.path.join(script_dir, ".agents", "skills")
    
    if not os.path.exists(src_skills):
        print(f"Error: Source skills directory not found at {src_skills}", file=sys.stderr)
        sys.exit(1)
        
    dst_skills = os.path.join(workspace, ".agents", "skills")
    os.makedirs(dst_skills, exist_ok=True)
    
    print(f"Installing Deep Research Skills to workspace: {workspace}")
    
    for skill_name in os.listdir(src_skills):
        src_path = os.path.join(src_skills, skill_name)
        dst_path = os.path.join(dst_skills, skill_name)
        
        if os.path.isdir(src_path):
            if os.path.exists(dst_path):
                print(f"Skill {skill_name} already exists. Overwriting...")
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
            print(f"Installed skill: {skill_name}")
            
    # Copy scripts to target workspace (optional, but convenient)
    src_scripts = os.path.join(script_dir, "scripts")
    dst_scripts = os.path.join(workspace, "scripts")
    if os.path.exists(src_scripts):
        os.makedirs(dst_scripts, exist_ok=True)
        for script_file in os.listdir(src_scripts):
            shutil.copy2(os.path.join(src_scripts, script_file), os.path.join(dst_scripts, script_file))
        print("Installed supporting control scripts to scripts/")
        
    print("\nInstallation complete! You can now use the following skills:")
    print("  - @skills:research-loop")
    print("  - @skills:landscape-scan")
    print("  - @skills:deep-dive")
    print("  - @skills:verify")
    print("\nTo start a session, run:")
    print("  python3 scripts/initialize_session.py --total-minutes 120")

if __name__ == "__main__":
    main()
