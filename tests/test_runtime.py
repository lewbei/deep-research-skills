import os
import sys
import json
import shutil
import unittest
import subprocess
import tempfile
from datetime import datetime, timedelta

# Import target scripts dynamically or execute via subprocess for end-to-end correctness
class TestDeepResearchRuntime(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Install skills to temporary directory
        install_script = os.path.join(self.project_root, "install.py")
        subprocess.run([sys.executable, install_script], cwd=self.test_dir, check=True, capture_output=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def run_script(self, script_name, args, cwd=None):
        if cwd is None:
            cwd = self.test_dir
        script_path = os.path.join(self.test_dir, "scripts", script_name)
        result = subprocess.run([sys.executable, script_path] + args, cwd=cwd, capture_output=True, text=True)
        return result

    def test_01_initialization(self):
        # Run initialize_session
        res = self.run_script("initialize_session.py", ["--total-minutes", "60", "--kind", "hard"])
        self.assertEqual(res.returncode, 0, f"Init failed: {res.stderr}")
        self.assertIn("Deep Research session successfully initialized", res.stdout)

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
        self.run_script("initialize_session.py", [])

        # Legal: Phase 1 -> Phase 2
        res = self.run_script("advance_phase.py", ["1", "2"])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Transition approved: Phase 1 -> Phase 2", res.stdout)

        # Verify state updated
        state_path = os.path.join(self.test_dir, ".deep-research", "session-state.json")
        with open(state_path, "r") as f:
            state = json.load(f)
        self.assertEqual(len(state["ledger"]), 2)
        self.assertEqual(state["ledger"][-1]["phase"], 2)
        self.assertIsNotNone(state["ledger"][0]["end_iso"])
        self.assertGreaterEqual(state["ledger"][0]["duration_minutes"], 0.0)

        # Illegal: requested transition from incorrect current phase
        res = self.run_script("advance_phase.py", ["1", "2"])
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Error: Current recorded phase is 2", res.stderr)

        # Illegal: transition path not in graph
        res = self.run_script("advance_phase.py", ["2", "4"])
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("is not allowed by the workflow graph schema", res.stderr)

    def test_03_time_budget_calculations(self):
        # Initialize
        self.run_script("initialize_session.py", ["--total-minutes", "10"])

        # Advance to 3.5 and calculate budget
        self.run_script("advance_phase.py", ["1", "2"])
        self.run_script("advance_phase.py", ["2", "3"])
        self.run_script("advance_phase.py", ["3", "3.5"])
        
        res = self.run_script("calculate_budget.py", [])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Updated time budget in", res.stdout)

        # Check time-budget.md content is updated
        tb_path = os.path.join(self.test_dir, "time-budget.md")
        with open(tb_path, "r") as f:
            content = f.read()
        self.assertIn("Elapsed:", content)
        self.assertIn("Research elapsed:", content)

    def test_04_spearman_correlation_and_ties(self):
        self.run_script("initialize_session.py", [])

        # Adding 4 observations (should remain candidate)
        for i in range(4):
            val = float(i)
            res = self.run_script("calculate_proxy.py", ["PX1", "--add", f"{val}:{val * 10}"])
            self.assertEqual(res.returncode, 0)
            self.assertIn("Status=candidate", res.stdout)

        # 5th observation: triggers calculation
        res = self.run_script("calculate_proxy.py", ["PX1", "--add", "4.0:40.0"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Status=validated", res.stdout)
        self.assertIn("Spearman rho = 1.000", res.stdout)

        # Check math on ties
        # Adding observations for a second proxy PX2 with tied ranks
        # X = [1, 2, 2, 3, 4] -> ranks = [1, 2.5, 2.5, 4, 5]
        # Y = [2, 4, 4, 8, 10] -> ranks = [1, 2.5, 2.5, 4, 5]
        # Since ranks match, correlation should be exactly 1.0
        self.run_script("calculate_proxy.py", ["PX2", "--add", "1:2"])
        self.run_script("calculate_proxy.py", ["PX2", "--add", "2:4"])
        self.run_script("calculate_proxy.py", ["PX2", "--add", "2:4"])
        self.run_script("calculate_proxy.py", ["PX2", "--add", "3:8"])
        res = self.run_script("calculate_proxy.py", ["PX2", "--add", "4:10"])
        
        self.assertEqual(res.returncode, 0)
        self.assertIn("Spearman rho = 1.000", res.stdout)

    def test_05_validation_script(self):
        self.run_script("initialize_session.py", [])
        
        res = self.run_script("validate_state.py", [])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("All validations PASSED successfully", res.stdout)

        # Check state validation fails if artifact header is corrupted
        tb_path = os.path.join(self.test_dir, "time-budget.md")
        with open(tb_path, "w") as f:
            f.write("# Corrupted Time Budget\n")
            
        res = self.run_script("validate_state.py", [])
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Validation FAILED", res.stdout + res.stderr)

if __name__ == "__main__":
    unittest.main()
