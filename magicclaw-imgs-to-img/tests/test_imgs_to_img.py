import contextlib
import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "imgs_to_img.py"


def load_module():
    spec = importlib.util.spec_from_file_location("magicclaw_imgs_to_img", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MagicClawImgsToImgCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def run_main(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(sys, "argv", ["imgs_to_img.py", *argv]):
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
                "--prompt",
                "merge two people",
                "--image-url",
                "https://example.com/ref-1.png",
                "--image-url",
                "https://example.com/ref-2.png",
            ]
        )

        payload = self.module.build_payload(args)

        self.assertEqual(payload["model"], "gemini-2.5-flash-image")
        self.assertEqual(payload["model_type"], "minimax_imgs2img")
        self.assertEqual(payload["prompt"], "merge two people")
        self.assertEqual(
            payload["img_list"],
            ["https://example.com/ref-1.png", "https://example.com/ref-2.png"],
        )
        self.assertEqual(payload["aspect_ratio"], "16:9")
        self.assertEqual(payload["image_size"], "2K")
        self.assertEqual(payload["source"], "img_gen_skills")

    def test_main_routes_to_image_endpoint_and_sets_primary_image_url(self):
        result = {
            "task_id": "task-compose-123",
            "status": 2,
            "source_url": "https://cdn.example.com/final-compose.png",
        }

        with patch.object(self.module, "run_magicclaw_task", return_value=result) as run_magicclaw_task:
            exit_code, stdout, stderr = self.run_main(
                [
                    "--prompt",
                    "merge two people",
                    "--image-url",
                    "https://example.com/ref-1.png",
                    "--image-url",
                    "https://example.com/ref-2.png",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        output = json.loads(stdout)
        self.assertEqual(output["primary_image_url"], "https://cdn.example.com/final-compose.png")
        self.assertEqual(run_magicclaw_task.call_args.kwargs["create_path"], "/taskapi/v1/task/gen/img")
        self.assertTrue(run_magicclaw_task.call_args.kwargs["no_wait"])


if __name__ == "__main__":
    unittest.main()
