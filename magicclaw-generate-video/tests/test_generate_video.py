import contextlib
import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_video.py"


def load_module():
    spec = importlib.util.spec_from_file_location("magicclaw_generate_video", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MagicClawGenerateVideoCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def run_main(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(sys, "argv", ["generate_video.py", *argv]):
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

    def test_build_payload_for_seedance(self):
        parser = self.module.build_parser()
        args = parser.parse_args(
            [
                "--model-type",
                "bytedance_seedance",
                "--text",
                "the angel touches the devil face",
                "--image-url",
                "https://example.com/ref-1.png",
                "--image-url",
                "https://example.com/ref-2.png",
            ]
        )

        payload = self.module.build_payload(args)

        self.assertEqual(payload["model"], "doubao-seedance-2-0-260128")
        self.assertEqual(payload["model_type"], "bytedance_seedance")
        self.assertEqual(payload["duration"], 5)
        self.assertEqual(payload["source"], "gen-video-skill")
        self.assertEqual(payload["content"][0]["role"], "reference_image")
        self.assertEqual(payload["content"][2], {"type": "text", "text": "the angel touches the devil face"})

    def test_build_payload_for_seedance_with_extended_options(self):
        parser = self.module.build_parser()
        args = parser.parse_args(
            [
                "--model-type",
                "bytedance_seedance",
                "--text",
                "the angel touches the devil face",
                "--image-url",
                "https://example.com/ref-1.png",
                "--ratio",
                "16:9",
                "--duration",
                "12",
                "--resolution",
                "1080p",
                "--fps",
                "24",
                "--generate-audio",
                "false",
                "--seed",
                "123456",
                "--watermark",
                "true",
            ]
        )

        payload = self.module.build_payload(args)

        self.assertEqual(payload["ratio"], "16:9")
        self.assertEqual(payload["duration"], 12)
        self.assertEqual(payload["resolution"], "1080p")
        self.assertEqual(payload["fps"], 24)
        self.assertEqual(payload["generate_audio"], False)
        self.assertEqual(payload["seed"], 123456)
        self.assertEqual(payload["watermark"], True)

    def test_validate_args_allows_seedance_optional_fields_to_pass_through(self):
        parser = self.module.build_parser()
        args = parser.parse_args(
            [
                "--model-type",
                "bytedance_seedance",
                "--text",
                "the angel touches the devil face",
                "--image-url",
                "https://example.com/ref-1.png",
                "--duration",
                "2",
                "--ratio",
                "adaptive",
                "--resolution",
                "1080p",
                "--fps",
                "24",
            ]
        )

        validated = self.module.validate_args(args)

        self.assertEqual(validated.duration, 2)
        self.assertEqual(validated.ratio, "adaptive")
        self.assertEqual(validated.resolution, "1080p")
        self.assertEqual(validated.fps, 24)

    def test_build_payload_for_kling(self):
        parser = self.module.build_parser()
        args = parser.parse_args(
            [
                "--model-type",
                "duomi_kling",
                "--prompt",
                "the ghost becomes a goddess",
                "--img-url",
                "https://example.com/ref.png",
            ]
        )

        payload = self.module.build_payload(args)

        self.assertEqual(payload["model"], "kling-v3")
        self.assertEqual(payload["model_type"], "duomi_kling")
        self.assertEqual(payload["img_url"], "https://example.com/ref.png")
        self.assertEqual(payload["prompt"], "the ghost becomes a goddess")
        self.assertEqual(payload["source"], "video-gen-skill")

    def test_main_routes_to_video_endpoint_and_sets_video_url(self):
        result = {
            "task_id": "task-video-123",
            "status": 2,
            "source_url": "https://cdn.example.com/final-video.mp4",
        }

        with patch.object(self.module, "run_magicclaw_task", return_value=result) as run_magicclaw_task:
            exit_code, stdout, stderr = self.run_main(
                [
                    "--model-type",
                    "duomi_kling",
                    "--prompt",
                    "the ghost becomes a goddess",
                    "--img-url",
                    "https://example.com/ref.png",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        output = json.loads(stdout)
        self.assertEqual(output["video_url"], "https://cdn.example.com/final-video.mp4")
        self.assertEqual(run_magicclaw_task.call_args.kwargs["create_path"], "/taskapi/v1/task/gen/video")
        self.assertTrue(run_magicclaw_task.call_args.kwargs["no_wait"])


if __name__ == "__main__":
    unittest.main()
