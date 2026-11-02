"""Runtime configuration identities and separation of online and final review."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vlm.settings import role_settings  # noqa: E402
from evaluation import providers  # noqa: E402


class ConfigurationTests(unittest.TestCase):
    def test_role_identity_uses_the_actual_factory_credential_file(self):
        with tempfile.TemporaryDirectory() as directory:
            credentials = Path(directory) / "api.env"
            credentials.write_text("LHA_API_PLANNER_MODEL=fixture/from-file\n")
            config = {"models": {"planner": {"options": {"credential_file": str(credentials)}}}}
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(role_settings(config, "planner")["model"], "fixture/from-file")
                config["models"]["planner"]["options"].update(
                    model="fixture/explicit", reasoning_effort=None
                )
                self.assertEqual(
                    role_settings(config, "planner"),
                    {"model": "fixture/explicit", "reasoning_effort": None},
                )

    def test_judge_configuration_controls_wire_model_and_frozen_final_identity(self):
        from evaluation.low_high import profile

        baseline = profile()
        rows = copy.deepcopy(providers.configuration())
        rows[0]["provider_model"] = "fixture/independent-judge"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evaluation.json"
            path.write_text(json.dumps({"judges": rows}))
            with (
                patch.object(providers, "CONFIG_PATH", path),
                patch.dict(
                    os.environ,
                    {
                        "OPENROUTER_API_KEY": "fixture",
                        "LHA_API_ENV_FILE": str(path.parent / "absent"),
                    },
                ),
            ):
                judge = providers.make_judge(rows[0]["model"])
                self.assertEqual(judge.api_model, "fixture/independent-judge")
                self.assertEqual(
                    providers.judge_identity(judge.model)["provider_model"], judge.api_model
                )
                updated = profile()
                self.assertEqual(updated["judges"], rows)
                self.assertNotEqual(baseline["sha256"], updated["sha256"])

    def test_online_import_has_no_formal_judge_or_optional_backend_dependency(self):
        code = """
import sys
from critic_harness.one_shot import frozen_profile
from vlm.openrouter import OpenRouterVisionModel
frozen_profile(model='fixture/model', reasoning_effort=None)
assert 'evaluation.validation' not in sys.modules
assert 'evaluation.providers' not in sys.modules
assert 'vlm.litellm_vlm' not in sys.modules
assert 'vlm.local_qwen' not in sys.modules
"""
        result = subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_provider_import_remains_explicit(self):
        from evaluation.creative import ParateraJudge
        from evaluation.legacy_providers import ParateraJudge as HistoricalJudge

        self.assertIs(ParateraJudge, HistoricalJudge)


if __name__ == "__main__":
    unittest.main()
