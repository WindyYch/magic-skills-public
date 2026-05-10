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
    spec = importlib.util.spec_from_file_location("imgs_to_img", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ImgsToImgCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def run_main(self, argv, env=None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        merged_env = {"DUOMI_API_AUTHORIZATION": "Bearer test-token"} if env is None else env
        with patch.object(sys, "argv", ["imgs_to_img.py", *argv]):
            with patch.dict(os.environ, merged_env, clear=True):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    exit_code = self.module.main()
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_create_with_no_wait_returns_task_id_without_querying(self):
        create_response = {
            "code": 200,
            "msg": "success",
            "data": {"task_id": "task-create-123"},
        }

        with patch.object(self.module, "request_json", return_value=create_response) as request_json:
            exit_code, stdout, stderr = self.run_main(
                [
                    "--prompt",
                    "blend these images",
                    "--image-url",
                    "https://example.com/1.png",
                    "--image-url",
                    "https://example.com/2.png",
                    "--no-wait",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        output = json.loads(stdout)
        self.assertEqual(output["task_id"], "task-create-123")
        self.assertIsNone(output["state"])
        self.assertIsNone(output["raw_query_response"])
        self.assertEqual(request_json.call_count, 1)
        self.assertTrue(request_json.call_args.kwargs["url"].endswith("/api/gemini/nano-banana-edit"))

    def test_existing_task_id_can_be_polled_until_succeeded(self):
        running_response = {
            "code": 200,
            "msg": "success",
            "data": {
                "task_id": "task-existing-456",
                "state": "running",
                "status": "1",
                "msg": "",
                "data": {},
            },
        }
        succeeded_response = {
            "code": 200,
            "msg": "success",
            "data": {
                "task_id": "task-existing-456",
                "state": "succeeded",
                "status": "3",
                "msg": "",
                "data": {
                    "images": [{"url": "https://example.com/final.png", "file_name": "final.png"}],
                    "description": "merged result",
                },
            },
        }

        with patch.object(
            self.module,
            "request_json",
            side_effect=[running_response, succeeded_response],
        ) as request_json:
            with patch.object(self.module.time, "sleep") as sleep:
                with patch.object(
                    self.module.time,
                    "time",
                    side_effect=[100.0, 100.0, 101.0, 102.5],
                ):
                    exit_code, stdout, stderr = self.run_main(
                        [
                            "--task-id",
                            "task-existing-456",
                            "--poll-interval-seconds",
                            "0",
                            "--max-wait-seconds",
                            "10",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        output = json.loads(stdout)
        self.assertEqual(output["task_id"], "task-existing-456")
        self.assertEqual(output["state"], "succeeded")
        self.assertEqual(output["primary_image_url"], "https://example.com/final.png")
        self.assertEqual(output["query_attempts"], 2)
        self.assertEqual(output["elapsed_seconds"], 2.5)
        self.assertIsNone(output["raw_create_response"])
        self.assertEqual(request_json.call_count, 2)
        self.assertTrue(
            all("/api/gemini/nano-banana/task-existing-456" in call.kwargs["url"] for call in request_json.call_args_list)
        )
        sleep.assert_called_once_with(0)

    def test_existing_task_id_uses_ten_second_default_poll_interval(self):
        running_response = {
            "code": 200,
            "msg": "success",
            "data": {
                "task_id": "task-default-interval-789",
                "state": "running",
                "status": "1",
                "msg": "",
                "data": {},
            },
        }
        succeeded_response = {
            "code": 200,
            "msg": "success",
            "data": {
                "task_id": "task-default-interval-789",
                "state": "succeeded",
                "status": "3",
                "msg": "",
                "data": {
                    "images": [{"url": "https://example.com/final-2.png", "file_name": "final-2.png"}],
                    "description": "merged result",
                },
            },
        }

        with patch.object(
            self.module,
            "request_json",
            side_effect=[running_response, succeeded_response],
        ):
            with patch.object(self.module.time, "sleep") as sleep:
                with patch.object(
                    self.module.time,
                    "time",
                    side_effect=[200.0, 200.0, 201.0, 203.0],
                ):
                    exit_code, stdout, stderr = self.run_main(
                        [
                            "--task-id",
                            "task-default-interval-789",
                            "--max-wait-seconds",
                            "30",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        output = json.loads(stdout)
        self.assertEqual(output["task_id"], "task-default-interval-789")
        self.assertEqual(output["state"], "succeeded")
        sleep.assert_called_once_with(10)

    def test_preview_params_uses_nano_banana_pro_defaults_without_network(self):
        exit_code, stdout, stderr = self.run_main(["--preview-params"], env={})

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout), {
            "model": "nano-banana-pro",
            "aspect_ratio": "",
            "image_size": "1K",
        })

    def test_preview_params_does_not_require_duomi_authorization(self):
        with patch.object(self.module, "request_json") as request_json:
            exit_code, stdout, stderr = self.run_main(["--preview-params"], env={})

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout), {
            "model": "nano-banana-pro",
            "aspect_ratio": "",
            "image_size": "1K",
        })
        request_json.assert_not_called()

    def test_preview_params_rejects_task_id(self):
        exit_code, stdout, stderr = self.run_main(["--preview-params", "--task-id", "task-123"], env={})

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("--preview-params cannot be used with --task-id", stderr)

    def test_preview_params_rejects_prompt(self):
        exit_code, stdout, stderr = self.run_main(["--preview-params", "--prompt", "blend these images"], env={})

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("--preview-params cannot be used with --prompt", stderr)

    def test_preview_params_rejects_image_url(self):
        exit_code, stdout, stderr = self.run_main(
            ["--preview-params", "--image-url", "https://example.com/1.png"],
            env={},
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("--preview-params cannot be used with --image-url", stderr)

    def test_preview_params_validates_base_url_without_network(self):
        exit_code, stdout, stderr = self.run_main(["--preview-params", "--base-url", "not-a-url"], env={})

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("--base-url must be an absolute http:// or https:// URL", stderr)

    def test_create_uses_confirmed_generation_parameters(self):
        create_response = {
            "code": 200,
            "msg": "success",
            "data": {"task_id": "task-create-123"},
        }

        with patch.object(self.module, "request_json", return_value=create_response) as request_json:
            exit_code, stdout, stderr = self.run_main(
                [
                    "--prompt",
                    "blend these images",
                    "--image-url",
                    "https://example.com/1.png",
                    "--image-url",
                    "https://example.com/2.png",
                    "--model",
                    "nano-banana-pro",
                    "--aspect-ratio",
                    "16:9",
                    "--image-size",
                    "2K",
                    "--no-wait",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        output = json.loads(stdout)
        self.assertEqual(output["task_id"], "task-create-123")
        self.assertIsNone(output["state"])
        self.assertIsNone(output["raw_query_response"])
        self.assertEqual(request_json.call_count, 1)
        self.assertTrue(request_json.call_args.kwargs["url"].endswith("/api/gemini/nano-banana-edit"))
        self.assertEqual(
            request_json.call_args.kwargs["payload"],
            {
                "model": "nano-banana-pro",
                "prompt": "blend these images",
                "image_urls": ["https://example.com/1.png", "https://example.com/2.png"],
                "aspect_ratio": "16:9",
                "image_size": "2K",
            },
        )

    def test_create_defaults_model_to_nano_banana_pro_when_omitted(self):
        create_response = {
            "code": 200,
            "msg": "success",
            "data": {"task_id": "task-create-default-model"},
        }

        with patch.object(self.module, "request_json", return_value=create_response) as request_json:
            exit_code, stdout, stderr = self.run_main(
                [
                    "--prompt",
                    "blend these images",
                    "--image-url",
                    "https://example.com/1.png",
                    "--image-url",
                    "https://example.com/2.png",
                    "--no-wait",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        output = json.loads(stdout)
        self.assertEqual(output["task_id"], "task-create-default-model")
        self.assertIsNone(output["state"])
        self.assertIsNone(output["raw_query_response"])
        self.assertEqual(request_json.call_count, 1)
        self.assertEqual(
            request_json.call_args.kwargs["payload"],
            {
                "model": "nano-banana-pro",
                "prompt": "blend these images",
                "image_urls": ["https://example.com/1.png", "https://example.com/2.png"],
                "aspect_ratio": "",
                "image_size": "1K",
            },
        )


if __name__ == "__main__":
    unittest.main()
