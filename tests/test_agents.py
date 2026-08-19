import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import agents  # noqa: E402


class ReadAgentOutputTests(unittest.TestCase):
    @patch("agents.subprocess.run")
    def test_reads_current_plain_text_response(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="⏺ Current response\n", stderr=""
        )

        self.assertEqual(
            agents.read_agent_output("workspace:pane"),
            "⏺ Current response\n",
        )

    @patch("agents.subprocess.run")
    def test_supports_visible_snapshot_source(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="visible output\n", stderr=""
        )

        self.assertEqual(
            agents.read_agent_output("workspace:pane", source="visible"),
            "visible output\n",
        )
        self.assertEqual(
            run.call_args.args[0],
            [
                agents.HERDR,
                "agent",
                "read",
                "workspace:pane",
                "--source",
                "visible",
                "--lines",
                "150",
            ],
        )

    @patch("agents.subprocess.run")
    def test_reads_legacy_json_response(self, run):
        stdout = json.dumps(
            {"result": {"read": {"text": "⏺ Legacy response\n"}}}
        )
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=stdout, stderr=""
        )

        self.assertEqual(
            agents.read_agent_output("workspace:pane"),
            "⏺ Legacy response\n",
        )

    @patch("agents.subprocess.run")
    def test_raises_when_read_command_fails(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="pane not found"
        )

        with self.assertRaisesRegex(RuntimeError, "pane not found"):
            agents.read_agent_output("workspace:missing")


if __name__ == "__main__":
    unittest.main()
