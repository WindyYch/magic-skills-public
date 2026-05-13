import contextlib
import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_tts.py"


def load_module():
    spec = importlib.util.spec_from_file_location("magicclaw_generate_tts", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MagicClawGenerateTtsCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def run_main(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(sys, "argv", ["generate_tts.py", *argv]):
            with patch.dict(
                os.environ,
                {
                    "MagicClawDomain": "https://api.example.com",
                    "MagicClawAuthorization": "Bearer test-token",
                },
                clear=True,
            ):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    exit_code = self.module.main()
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_build_payload_uses_expected_magicclaw_defaults(self):
        parser = self.module.build_parser()
        args = parser.parse_args(
            [
                "--text",
                "hello world",
                "--voice-id",
                "female-yujie",
            ]
        )

        payload = self.module.build_payload(args)

        self.assertEqual(payload["model"], "speech-2.8-hd")
        self.assertEqual(payload["output_format"], "hex")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["source"], "gen-tts-skill")
        self.assertEqual(
            payload["audio_setting"],
            {
                "format": "mp3",
                "sample_rate": 32000,
                "bitrate": 128000,
            },
        )
        self.assertEqual(
            payload["voice_setting"],
            {
                "voice_id": "female-yujie",
                "speed": 1.0,
                "vol": 1.0,
                "pitch": 0,
            },
        )

    def test_main_routes_to_tts_endpoint_and_sets_audio_url(self):
        result = {
            "task_id": "task-tts-123",
            "status": 2,
            "source_url": "https://cdn.example.com/final-audio.mp3",
        }

        with patch.object(self.module, "run_magicclaw_task", return_value=result) as run_magicclaw_task:
            exit_code, stdout, stderr = self.run_main(
                [
                    "--text",
                    "hello world",
                    "--voice-id",
                    "female-yujie",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        output = json.loads(stdout)
        self.assertEqual(output["audio_url"], "https://cdn.example.com/final-audio.mp3")
        self.assertEqual(run_magicclaw_task.call_args.kwargs["create_path"], "/taskapi/v1/task/gen/tts")
        self.assertTrue(run_magicclaw_task.call_args.kwargs["no_wait"])


if __name__ == "__main__":
    unittest.main()
