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

if __name__ == "__main__":
    unittest.main()
