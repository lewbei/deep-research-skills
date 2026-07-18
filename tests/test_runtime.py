import os
import sys
import json
import shutil
import unittest
import subprocess
import tempfile

class TestDeepResearchRuntime(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Install skills and CLI tool to temporary directory
        install_script = os.path.join(self.project_root, "install.py")
        subprocess.run([sys.executable, install_script], cwd=self.test_dir, check=True, capture_output=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def run_drs(self, args, cwd=None):
        if cwd is None:
            cwd = self.test_dir
        # Run deep_research.cli module directly using Python to ensure cross-platform compatibility
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.pathsep.join([self.test_dir, env.get("PYTHONPATH", "")])
        result = subprocess.run([sys.executable, "-m", "deep_research.cli"] + args, cwd=cwd, env=env, capture_output=True, text=True)
        return result

    def clear_placeholders(self):
        # Clear unknowns-registry placeholder
        registry_path = os.path.join(self.test_dir, "unknowns-registry.md")
        if os.path.exists(registry_path):
            with open(registry_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace("placeholder — replace with first real unknown", "Real unknown U1 description")
            with open(registry_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        # Clear mega-plan placeholder
        plan_path = os.path.join(self.test_dir, "mega-plan.md")
        if os.path.exists(plan_path):
            with open(plan_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace("[Project Title]", "Real Project Title")
            with open(plan_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        # Clear probe-registry placeholder
        probe_path = os.path.join(self.test_dir, "probe-registry.md")
        if os.path.exists(probe_path):
            with open(probe_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Append a mock probe definition to Pending Probes section
            content = content.replace("<!-- Add pending probes here. The orchestrator runs these before any Phase 8 implementation step. -->", 
                                      "### P1: Real test script\n- **Status:** pending\n- **Probe path:** probes/test.py")
            with open(probe_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        # Clear proxy-log placeholder
        proxy_path = os.path.join(self.test_dir, "proxy-log.md")
        if os.path.exists(proxy_path):
            with open(proxy_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace("placeholder — replace with first real proxy", "Real proxy PX1 description")
            with open(proxy_path, "w", encoding="utf-8") as f:
                f.write(content)

    def test_01_initialization(self):
        # Run `./drs init`
        res = self.run_drs(["init", "--total-minutes", "60", "--kind", "hard"])
        self.assertEqual(res.returncode, 0, f"Init failed: {res.stderr}")
        self.assertIn("Initialized Deep Research session", res.stdout)

        # Check session-state.json
        state_path = os.path.join(self.test_dir, ".deep-research", "session-state.json")
        self.assertTrue(os.path.exists(state_path))
        with open(state_path, "r") as f:
            state = json.load(f)
        
        self.assertIsNotNone(state["session_id"])
        self.assertIsNotNone(state["started_at"])
        self.assertEqual(state["budget"]["total_minutes"], 60)
        self.assertEqual(state["budget"]["kind"], "hard")
        self.assertEqual(state["current_mode"], "explore")
        
        # Check start_iso is initialized
        self.assertEqual(state["ledger"][0]["start_iso"], state["started_at"])
        self.assertIsNone(state["ledger"][0]["end_iso"])

        # Check copy of markdown templates
        expected_artifacts = [
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
        for name in expected_artifacts:
            self.assertTrue(os.path.exists(os.path.join(self.test_dir, name)), f"Missing artifact: {name}")

    def test_02_phase_transitions(self):
        # Initialize
        self.run_drs(["init"])
        self.clear_placeholders()

        # Legal: Phase 1 -> Phase 2
        res = self.run_drs(["transition", "1", "2"])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Workflow advanced. Current phase: 2", res.stdout)

        # Verify state updated
        state_path = os.path.join(self.test_dir, ".deep-research", "session-state.json")
        with open(state_path, "r") as f:
            state = json.load(f)
        self.assertEqual(len(state["ledger"]), 2)
        self.assertEqual(state["ledger"][-1]["phase"], "2")
        self.assertIsNotNone(state["ledger"][0]["end_iso"])
        self.assertGreaterEqual(state["ledger"][0]["duration_minutes"], 0.0)

        # Illegal: requested transition from incorrect current phase
        res = self.run_drs(["transition", "1", "2"])
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Error: Current phase is 2", res.stderr)

        # Illegal: transition path not in graph
        res = self.run_drs(["transition", "2", "4"])
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("is not allowed by the workflow graph schema", res.stderr)

    def test_03_time_budget_calculations(self):
        # Initialize
        self.run_drs(["init", "--total-minutes", "10"])
        self.clear_placeholders()

        # Advance to 3.5 and calculate budget
        self.run_drs(["transition", "1", "2"])
        self.run_drs(["transition", "2", "3"])
        self.run_drs(["transition", "3", "3.5"])
        
        res = self.run_drs(["budget"])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Updated time budget", res.stdout)

        # Check time-budget.md content is updated
        tb_path = os.path.join(self.test_dir, "time-budget.md")
        with open(tb_path, "r") as f:
            content = f.read()
        self.assertIn("Elapsed:", content)
        self.assertIn("Research elapsed:", content)

    def test_04_spearman_correlation_and_ties(self):
        self.run_drs(["init"])

        # Adding 4 observations (should remain candidate)
        for i in range(4):
            val = float(i)
            res = self.run_drs(["proxy", "PX1", "--add", f"{val}:{val * 10}"])
            self.assertEqual(res.returncode, 0)
            self.assertIn("Status:   candidate", res.stdout)

        # 5th observation: triggers calculation
        res = self.run_drs(["proxy", "PX1", "--add", "4.0:40.0"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Status:   validated", res.stdout)

        # Check math on ties
        self.run_drs(["proxy", "PX2", "--add", "1:2"])
        self.run_drs(["proxy", "PX2", "--add", "2:4"])
        self.run_drs(["proxy", "PX2", "--add", "2:4"])
        self.run_drs(["proxy", "PX2", "--add", "3:8"])
        res = self.run_drs(["proxy", "PX2", "--add", "4:10"])
        
        self.assertEqual(res.returncode, 0)
        self.assertIn("Status:   validated", res.stdout)

    def test_05_validation_script(self):
        self.run_drs(["init"])
        
        res = self.run_drs(["validate"])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("All validations PASSED successfully", res.stdout)

        # Check state validation fails if artifact header is corrupted
        tb_path = os.path.join(self.test_dir, "time-budget.md")
        with open(tb_path, "w") as f:
            f.write("# Corrupted Time Budget\n")
            
        res = self.run_drs(["validate"])
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Validation FAILED", res.stdout + res.stderr)

    def test_06_budget_mode_enforcement(self):
        self.run_drs(["init"])
        
        # Manually alter state mode to 'sprint' (to test transition block)
        state_path = os.path.join(self.test_dir, ".deep-research", "session-state.json")
        with open(state_path, "r") as f:
            state = json.load(f)
        state["current_mode"] = "sprint"
        with open(state_path, "w") as f:
            json.dump(state, f)
            
        # Illegal transition: Sprint mode prohibits moving back into research phases (like phase 2)
        res = self.run_drs(["transition", "1", "2"])
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Transition denied: Current mode is 'sprint'", res.stderr)

    def test_07_fail_closed_transitions(self):
        self.run_drs(["init"])
        
        # Write corrupted transitions.yaml
        yaml_path = os.path.join(self.test_dir, ".deep-research", "transitions.yaml")
        with open(yaml_path, "w") as f:
            f.write("phases:\n  - malformed_list_instead_of_dict\n")
            
        # Transition must fail closed
        res = self.run_drs(["transition", "1", "2"])
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Workflow execution blocked: Invalid transitions.yaml", res.stderr)

    def test_08_advanced_control_flow(self):
        # 1. Test invalid arguments during init fails before writing
        res_fail = self.run_drs(["init", "--total-minutes", "-10"])
        self.assertNotEqual(res_fail.returncode, 0)
        self.assertIn("Validation Error", res_fail.stderr + res_fail.stdout)
        
        res_fail_pct = self.run_drs(["init", "--research-percent", "150"])
        self.assertNotEqual(res_fail_pct.returncode, 0)
        self.assertIn("Validation Error", res_fail_pct.stderr + res_fail_pct.stdout)

        # 2. Test sprint mode escape transition to Phase 7
        self.run_drs(["init"])
        self.clear_placeholders()
        state_path = os.path.join(self.test_dir, ".deep-research", "session-state.json")
        with open(state_path, "r") as f:
            state = json.load(f)
        state["current_mode"] = "sprint"
        with open(state_path, "w") as f:
            json.dump(state, f)
        
        # In sprint mode, transition from 1 -> 2 is blocked (requires research)
        res_block = self.run_drs(["transition", "1", "2"])
        self.assertNotEqual(res_block.returncode, 0)
        
        # But emergency/sprint bypass transition directly from Phase 3.5 to Phase 7 is allowed!
        # First transition 1 -> 2 -> 3 -> 3.5 (requires resetting mode to explore first)
        with open(state_path, "r") as f:
            state = json.load(f)
        state["current_mode"] = "explore"
        with open(state_path, "w") as f:
            json.dump(state, f)
            
        self.run_drs(["transition", "1", "2"])
        self.run_drs(["transition", "2", "3"])
        self.run_drs(["transition", "3", "3.5"])
        
        # Set to sprint mode at phase 3.5
        with open(state_path, "r") as f:
            state = json.load(f)
        state["current_mode"] = "sprint"
        with open(state_path, "w") as f:
            json.dump(state, f)
            
        # Sprint escape transition 3.5 -> 7
        res_escape = self.run_drs(["transition", "3.5", "7"])
        self.assertEqual(res_escape.returncode, 0, res_escape.stderr)
        self.assertIn("Workflow advanced. Current phase: 7", res_escape.stdout)
        
        # Run validation check to ensure bypass is correctly accepted
        res_val = self.run_drs(["validate"])
        self.assertEqual(res_val.returncode, 0, res_val.stderr)

        # 3. Test halt emergency transition to Phase 10 from any phase
        with open(state_path, "r") as f:
            state = json.load(f)
        state["current_mode"] = "halt"
        with open(state_path, "w") as f:
            json.dump(state, f)
            
        # Emergency transition directly to 10 is approved even if current phase is 7 (not normally allowed 7 -> 10)
        res_halt = self.run_drs(["transition", "7", "10"])
        self.assertEqual(res_halt.returncode, 0, res_halt.stderr)
        self.assertIn("Workflow advanced. Current phase: 10", res_halt.stdout)
        
        # Run validation check to ensure halt bypass is correctly accepted
        res_val2 = self.run_drs(["validate"])
        self.assertEqual(res_val2.returncode, 0, res_val2.stderr)

    def test_09_regression_tests(self):
        # 1. Halt mode bypass when exit gate artifact is missing
        self.run_drs(["init"])
        self.clear_placeholders()
        state_path = os.path.join(self.test_dir, ".deep-research", "session-state.json")
        
        # Delete required artifact for phase 1 (unknowns-registry.md)
        os.remove(os.path.join(self.test_dir, "unknowns-registry.md"))
        
        # In explore mode, transition fails because artifact is missing
        res_fail_gate = self.run_drs(["transition", "1", "2"])
        self.assertNotEqual(res_fail_gate.returncode, 0)
        self.assertIn("Phase exit requirement missing", res_fail_gate.stderr)
        
        # Set mode to halt
        with open(state_path, "r") as f:
            state = json.load(f)
        state["current_mode"] = "halt"
        with open(state_path, "w") as f:
            json.dump(state, f)
            
        # In halt mode, transition from 1 -> 10 succeeds even though artifact is missing!
        res_halt_gate = self.run_drs(["transition", "1", "10"])
        self.assertEqual(res_halt_gate.returncode, 0, res_halt_gate.stderr)

        # 2. Incorrect from_p during halt fails
        self.run_drs(["init"])
        self.clear_placeholders()
        with open(state_path, "r") as f:
            state = json.load(f)
        state["current_mode"] = "halt"
        with open(state_path, "w") as f:
            json.dump(state, f)
        # Attempt halt transition from incorrect phase 2 (actual current phase is 1)
        res_wrong_from = self.run_drs(["transition", "2", "10"])
        self.assertNotEqual(res_wrong_from.returncode, 0)
        self.assertIn("requested transition is from 2", res_wrong_from.stderr)

        # 3. Custom YAML numeric phase normalization, collisions, escapes, and initial phase checks
        yaml_dir = os.path.join(self.test_dir, ".deep-research")
        os.makedirs(yaml_dir, exist_ok=True)
        yaml_path = os.path.join(yaml_dir, "transitions.yaml")
        
        # Test custom initial phase initialization
        with open(yaml_path, "w") as f:
            f.write("initial_phase: init\nterminal_phase: done\nsprint_target: done\nphases:\n  init:\n    category: research\n    transitions: [done]\n  done:\n    category: execution\n    transitions: []\n")
        res_custom_init = self.run_drs(["init"])
        self.assertEqual(res_custom_init.returncode, 0, res_custom_init.stderr)
        
        # Verify ledger initialized with 'init' instead of default '1'
        with open(state_path, "r") as f:
            state = json.load(f)
        self.assertEqual(state["ledger"][0]["phase"], "init")
        
        # Clean up custom transitions to reset
        os.remove(yaml_path)
        self.run_drs(["init"])
        self.clear_placeholders()
        
        # Custom YAML with floats as keys/targets, defining phase metadata
        with open(yaml_path, "w") as f:
            f.write("initial_phase: 1.0\nterminal_phase: 2.0\nsprint_target: 2.0\nphases:\n  1.0:\n    category: research\n    transitions: [2.0]\n  2.0:\n    category: execution\n    transitions: []\n")
            
        # Normal transition 1 -> 2 should work under float normalization
        res_norm = self.run_drs(["transition", "1", "2"])
        self.assertEqual(res_norm.returncode, 0, res_norm.stderr)
        
        # Custom YAML collision check (quoted string keys)
        with open(yaml_path, "w") as f:
            f.write("initial_phase: '1'\nterminal_phase: '2'\nsprint_target: '2'\nphases:\n  '1':\n    category: research\n    transitions: []\n  '2':\n    category: research\n    transitions: []\n  '2.0':\n    category: execution\n    transitions: []\n")
        res_collision = self.run_drs(["transition", "1", "2"])
        self.assertNotEqual(res_collision.returncode, 0)
        self.assertIn("duplicate normalized phase keys", res_collision.stderr + res_collision.stdout)
        
        # Custom YAML collision check (unquoted numeric duplicates)
        with open(yaml_path, "w") as f:
            f.write("initial_phase: '1'\nterminal_phase: '2'\nsprint_target: '2'\nphases:\n  1:\n    category: research\n    transitions: []\n  2:\n    category: research\n    transitions: []\n  2.0:\n    category: execution\n    transitions: []\n")
        res_unquoted_collision = self.run_drs(["transition", "1", "2"])
        self.assertNotEqual(res_unquoted_collision.returncode, 0)
        self.assertIn("Duplicate mapping key detected", res_unquoted_collision.stderr + res_unquoted_collision.stdout)
        
        # Clean up unquoted duplicate config
        os.remove(yaml_path)
        
        # Custom YAML directory escape check (required artifact tries to traverse outside workspace)
        self.run_drs(["init"])
        self.clear_placeholders()
        with open(yaml_path, "w") as f:
            f.write("initial_phase: '1'\nterminal_phase: '2'\nsprint_target: '2'\nphases:\n  '1':\n    category: research\n    transitions: ['2']\n    required_artifacts: ['../outside.txt']\n  '2':\n    category: execution\n    transitions: []\n")
        res_escape_gate = self.run_drs(["transition", "1", "2"])
        self.assertNotEqual(res_escape_gate.returncode, 0)
        self.assertIn("escapes the workspace directory boundaries", res_escape_gate.stderr + res_escape_gate.stdout)
        
        # Clean up custom YAML to prevent pollution in subsequent tests
        os.remove(yaml_path)

        # 4. Null ledger phase fails load
        with open(state_path, "r") as f:
            state = json.load(f)
        state["ledger"][0]["phase"] = None
        with open(state_path, "w") as f:
            json.dump(state, f)
        res_null = self.run_drs(["status"])
        self.assertNotEqual(res_null.returncode, 0)
        self.assertIn("missing phase attribute", res_null.stderr + res_null.stdout)

        # 5. CRLF line endings frontmatter verification
        self.run_drs(["init"])
        skill_dir = os.path.join(self.test_dir, ".agents", "skills", "mock_skill")
        os.makedirs(skill_dir, exist_ok=True)
        with open(os.path.join(skill_dir, "SKILL.md"), "wb") as f:
            # Write frontmatter using CRLF (\r\n) line endings
            f.write(b"---\r\nname: mock_skill\r\ndescription: Mock\r\n---\r\nContent\r\n")
        res_crlf = self.run_drs(["validate"])
        self.assertEqual(res_crlf.returncode, 0, res_crlf.stderr)

        # 6. Terminal phase must be terminal validator check
        with open(yaml_path, "w") as f:
            f.write("initial_phase: '1'\nterminal_phase: '1'\nsprint_target: '2'\nphases:\n  '1':\n    category: research\n    transitions: ['2']\n  '2':\n    category: execution\n    transitions: []\n")
        res_term_fail = self.run_drs(["validate"])
        self.assertNotEqual(res_term_fail.returncode, 0)
        self.assertIn("must have no outgoing transitions", res_term_fail.stderr + res_term_fail.stdout)

        # 7. Sprint target must be category execution validator check
        with open(yaml_path, "w") as f:
            f.write("initial_phase: '1'\nterminal_phase: '2'\nsprint_target: '1'\nphases:\n  '1':\n    category: research\n    transitions: ['2']\n  '2':\n    category: execution\n    transitions: []\n")
        res_sprint_fail = self.run_drs(["validate"])
        self.assertNotEqual(res_sprint_fail.returncode, 0)
        self.assertIn("must have category 'execution'", res_sprint_fail.stderr + res_sprint_fail.stdout)

        # Clean up config to restore normal state
        os.remove(yaml_path)

        # 8. Directory as artifact fails exit requirements
        self.run_drs(["init"])
        self.clear_placeholders()
        with open(yaml_path, "w") as f:
            f.write("initial_phase: '1'\nterminal_phase: '2'\nsprint_target: '2'\nphases:\n  '1':\n    category: research\n    transitions: ['2']\n    required_artifacts: ['my_dir']\n  '2':\n    category: execution\n    transitions: []\n")
        
        # Create directory instead of regular file
        os.makedirs(os.path.join(self.test_dir, "my_dir"), exist_ok=True)
        res_dir_art = self.run_drs(["transition", "1", "2"])
        self.assertNotEqual(res_dir_art.returncode, 0)
        self.assertIn("must be a regular file", res_dir_art.stderr)
        
        # Clean up directory and config
        shutil.rmtree(os.path.join(self.test_dir, "my_dir"))
        os.remove(yaml_path)

        # 9. Symlink containment escape check
        self.run_drs(["init"])
        self.clear_placeholders()
        with open(yaml_path, "w") as f:
            f.write("initial_phase: '1'\nterminal_phase: '2'\nsprint_target: '2'\nphases:\n  '1':\n    category: research\n    transitions: ['2']\n    required_artifacts: ['escape_symlink']\n  '2':\n    category: execution\n    transitions: []\n")
        
        # Create a symlink pointing to a file outside the workspace
        outside_file = tempfile.mktemp()
        with open(outside_file, "w") as f:
            f.write("outside")
        os.symlink(outside_file, os.path.join(self.test_dir, "escape_symlink"))
        
        res_sym_escape = self.run_drs(["transition", "1", "2"])
        self.assertNotEqual(res_sym_escape.returncode, 0)
        self.assertIn("escapes the workspace directory boundaries", res_sym_escape.stderr)
        
        # Clean up symlink, outside file, and config
        os.remove(os.path.join(self.test_dir, "escape_symlink"))
        os.remove(outside_file)
        os.remove(yaml_path)

        # 10. Ledger initial phase matching and category validation
        self.run_drs(["init"])
        self.clear_placeholders()
        with open(state_path, "r") as f:
            state = json.load(f)
            
        # Corrupt first ledger phase and category
        state["ledger"][0]["phase"] = "2"
        state["ledger"][0]["category"] = "execution"
        with open(state_path, "w") as f:
            json.dump(state, f)
            
        res_ledger_fail = self.run_drs(["validate"])
        self.assertNotEqual(res_ledger_fail.returncode, 0)
        self.assertIn("does not match graph initial_phase", res_ledger_fail.stdout + res_ledger_fail.stderr)
        self.assertIn("category 'execution' does not match graph category", res_ledger_fail.stdout + res_ledger_fail.stderr)

        # 11. Enforce completion heuristics (phase completion vs artifact presence)
        # Delete templates to force fresh copy containing placeholders
        for t in ["unknowns-registry.md", "mega-plan.md", "probe-registry.md", "proxy-log.md"]:
            path = os.path.join(self.test_dir, t)
            if os.path.exists(path):
                os.remove(path)
        self.run_drs(["init"])
        
        # Transition 1 -> 2 fails immediately after init because unknowns-registry.md still has placeholder!
        res_place_fail = self.run_drs(["transition", "1", "2"])
        self.assertNotEqual(res_place_fail.returncode, 0)
        self.assertIn("still contains template placeholder", res_place_fail.stderr)
        
        # Now clear placeholders for unknowns-registry to allow advancing to 3.5 -> 4 -> 5
        self.clear_placeholders()
        
        # Advance state to Phase 5
        self.run_drs(["transition", "1", "2"])
        self.run_drs(["transition", "2", "3"])
        self.run_drs(["transition", "3", "3.5"])
        self.run_drs(["transition", "3.5", "4"])
        self.run_drs(["transition", "4", "5"])
        
        # 11.1. No high-risk open entry + empty probe registry -> succeeds
        # Populating unknowns-registry with P3 open unknown (not high risk) and empty probe registry
        with open(os.path.join(self.test_dir, "unknowns-registry.md"), "w", encoding="utf-8") as f:
            f.write("# Unknowns Registry\n## Open unknowns\n- **Status:** open\n- **Priority:** P3\n## Answered unknowns\n")
        with open(os.path.join(self.test_dir, "probe-registry.md"), "w", encoding="utf-8") as f:
            f.write("# Probe Registry\n## Pending probes\n<!-- Add pending probes here. -->\n")
            
        res_probe_ok1 = self.run_drs(["transition", "5", "6"])
        self.assertEqual(res_probe_ok1.returncode, 0, res_probe_ok1.stderr)
        
        # Rollback transition 5 -> 6 by modifying state to run next tests
        with open(state_path, "r") as f:
            state = json.load(f)
        if state["ledger"] and state["ledger"][-1]["phase"] == "6":
            state["ledger"].pop()
            state["ledger"][-1]["end_iso"] = None
        with open(state_path, "w") as f:
            json.dump(state, f)

        # 11.2. High-risk entry under Answered unknowns + empty probe registry -> succeeds
        with open(os.path.join(self.test_dir, "unknowns-registry.md"), "w", encoding="utf-8") as f:
            f.write("# Unknowns Registry\n## Open unknowns\n- **Status:** open\n- **Priority:** P3\n## Answered unknowns\n- **Status:** provisional-high-risk\n")
        with open(os.path.join(self.test_dir, "probe-registry.md"), "w", encoding="utf-8") as f:
            f.write("# Probe Registry\n## Pending probes\n<!-- Add pending probes here. -->\n")
            
        res_probe_ok2 = self.run_drs(["transition", "5", "6"])
        self.assertEqual(res_probe_ok2.returncode, 0, res_probe_ok2.stderr)

        # Rollback transition 5 -> 6 by modifying state
        with open(state_path, "r") as f:
            state = json.load(f)
        if state["ledger"] and state["ledger"][-1]["phase"] == "6":
            state["ledger"].pop()
            state["ledger"][-1]["end_iso"] = None
        with open(state_path, "w") as f:
            json.dump(state, f)

        # 11.3. High-risk entry under Open unknowns + empty probe registry -> fails
        with open(os.path.join(self.test_dir, "unknowns-registry.md"), "w", encoding="utf-8") as f:
            f.write("# Unknowns Registry\n## Open unknowns\n- **Status:** provisional-high-risk\n- **Priority:** P0\n## Answered unknowns\n")
        with open(os.path.join(self.test_dir, "probe-registry.md"), "w", encoding="utf-8") as f:
            f.write("# Probe Registry\n## Pending probes\n<!-- Add pending probes here. -->\n")
            
        res_probe_fail = self.run_drs(["transition", "5", "6"])
        self.assertNotEqual(res_probe_fail.returncode, 0)
        self.assertIn("must document at least one probe script", res_probe_fail.stderr)
        
        # 12. Binary custom artifacts should not raise decode errors
        self.run_drs(["init"])
        self.clear_placeholders()
        with open(yaml_path, "w") as f:
            f.write("initial_phase: '1'\nterminal_phase: '2'\nsprint_target: '2'\nphases:\n  '1':\n    category: research\n    transitions: ['2']\n    required_artifacts: ['binary.bin']\n  '2':\n    category: execution\n    transitions: []\n")
            
        # Write non-UTF-8 binary bytes to binary.bin
        with open(os.path.join(self.test_dir, "binary.bin"), "wb") as f:
            f.write(b"\x80\x81\xff\x00\x01\x02")
            
        res_binary_trans = self.run_drs(["transition", "1", "2"])
        self.assertEqual(res_binary_trans.returncode, 0, res_binary_trans.stderr)
        
        # Clean up binary file and custom transitions
        os.remove(os.path.join(self.test_dir, "binary.bin"))
        os.remove(yaml_path)

if __name__ == "__main__":
    unittest.main()
