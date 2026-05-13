import contextlib
import importlib.util
import io
import json
import os
import ssl
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_image.py"


def load_module():
    spec = importlib.util.spec_from_file_location("magicclaw_generate_image", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MagicClawGenerateImageCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def run_main(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(sys, "argv", ["generate_image.py", *argv]):
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
                "make an angel",
                "--image-url",
                "https://example.com/ref-1.png",
                "--image-url",
                "https://example.com/ref-2.png",
            ]
        )

        payload = self.module.build_payload(args)

        self.assertEqual(payload["model"], "gpt-image-2")
        self.assertEqual(payload["model_type"], "duomi_img_gen")
        self.assertEqual(payload["prompt"], "make an angel")
        self.assertEqual(
            payload["image"],
            ["https://example.com/ref-1.png", "https://example.com/ref-2.png"],
        )
        self.assertEqual(payload["quality"], "high")
        self.assertEqual(payload["size"], "1024x1024")
        self.assertEqual(payload["source"], "img_gen_skills")

    def test_resolve_base_url_uses_https_when_env_has_bare_domain(self):
        with patch.dict(os.environ, {"MagicClawDomain": "api.example.com"}, clear=True):
            self.assertEqual(self.module.resolve_base_url(None), "https://api.example.com")

    def test_request_json_retries_with_insecure_context_after_certificate_verify_failure(self):
        response_body = json.dumps({"biz_code": 10000, "data": {}}).encode("utf-8")
        call_kwargs = []

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return response_body

        def fake_urlopen(request, timeout=0, **kwargs):
            call_kwargs.append(kwargs)
            if len(call_kwargs) == 1:
                raise URLError(ssl.SSLCertVerificationError("self-signed certificate in certificate chain"))
            return FakeResponse()

        with patch.object(self.module, "urlopen", side_effect=fake_urlopen):
            parsed = self.module.request_json(
                url="https://api.example.com/taskapi/v1/task/gen/img",
                method="POST",
                headers={"Authorization": "Bearer test"},
                payload={"prompt": "hello"},
                timeout=30,
            )

        self.assertEqual(parsed, {"biz_code": 10000, "data": {}})
        self.assertEqual(len(call_kwargs), 2)
        self.assertNotIn("context", call_kwargs[0])
        self.assertIn("context", call_kwargs[1])
        self.assertFalse(call_kwargs[1]["context"].check_hostname)
        self.assertEqual(call_kwargs[1]["context"].verify_mode, ssl.CERT_NONE)

    def test_run_magicclaw_task_creates_and_returns_pending_when_no_wait(self):
        create_response = {
            "biz_code": 10000,
            "msg": "Success",
            "data": {"task_id": "task-create-123"},
            "trace_id": "trace-create-123",
        }

        with patch.dict(
            os.environ,
            {
                "MagicClawDomain": "https://api.example.com",
                "MagicClawAuthorization": "Bearer token-123",
            },
            clear=True,
        ):
            with patch.object(self.module, "request_json", return_value=create_response) as request_json:
                output = self.module.run_magicclaw_task(
                    create_path="/taskapi/v1/task/gen/img",
                    payload={"prompt": "make an image"},
                    task_id=None,
                    no_wait=True,
                    poll_interval_seconds=10,
                    max_wait_seconds=120,
                    timeout=30,
                )

        self.assertEqual(output["task_id"], "task-create-123")
        self.assertIsNone(output["source_url"])
        self.assertEqual(output["query_attempts"], 0)
        self.assertEqual(output["elapsed_seconds"], 0.0)
        self.assertNotIn("raw_create_response", output)
        self.assertNotIn("raw_query_response", output)
        self.assertNotIn("task_result", output)
        self.assertNotIn("input_params", output)
        self.assertEqual(request_json.call_count, 1)
        self.assertEqual(
            request_json.call_args.kwargs["url"],
            "https://api.example.com/taskapi/v1/task/gen/img",
        )
        self.assertEqual(
            request_json.call_args.kwargs["headers"]["Authorization"],
            "Bearer token-123",
        )
        self.assertEqual(request_json.call_args.kwargs["payload"], {"prompt": "make an image"})

    def test_run_magicclaw_task_polls_until_success_and_parses_result_fields(self):
        running_response = {
            "biz_code": 10000,
            "msg": "Success",
            "data": {
                "tasks": [
                    {
                        "task_id": "task-existing-456",
                        "status": 1,
                        "task_type": "txt2img",
                        "model_type": "duomi_img_gen",
                        "input_params": "{\"prompt\":\"hello\"}",
                        "task_result": "",
                        "source_url": "",
                    }
                ]
            },
            "trace_id": "trace-running",
        }
        succeeded_response = {
            "biz_code": 10000,
            "msg": "Success",
            "data": {
                "tasks": [
                    {
                        "task_id": "task-existing-456",
                        "status": 2,
                        "task_type": "txt2img",
                        "model_type": "duomi_img_gen",
                        "input_params": "{\"prompt\":\"hello\"}",
                        "task_result": "{\"url\":\"https://cdn.example.com/result.png\",\"result_payload\":{\"items\":[{\"result_url\":\"https://cdn.example.com/result.png\"}]}}",
                        "source": "img_gen_skills",
                        "source_url": "https://cdn.example.com/result.png",
                    }
                ]
            },
            "trace_id": "trace-succeeded",
        }

        with patch.dict(
            os.environ,
            {
                "MagicClawDomain": "api.example.com",
                "MagicClawAuthorization": "Bearer token-456",
            },
            clear=True,
        ):
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
                        output = self.module.run_magicclaw_task(
                            create_path="/taskapi/v1/task/gen/img",
                            payload=None,
                            task_id="task-existing-456",
                            no_wait=False,
                            poll_interval_seconds=10,
                            max_wait_seconds=120,
                            timeout=30,
                        )

        self.assertEqual(output["task_id"], "task-existing-456")
        self.assertEqual(output["status"], 2)
        self.assertEqual(output["source_url"], "https://cdn.example.com/result.png")
        self.assertEqual(output["query_attempts"], 2)
        self.assertEqual(output["elapsed_seconds"], 2.5)
        self.assertEqual(output["trace_id"], "trace-succeeded")
        self.assertNotIn("task_type", output)
        self.assertNotIn("model_type", output)
        self.assertNotIn("input_params", output)
        self.assertNotIn("task_result", output)
        self.assertNotIn("task_result_raw", output)
        self.assertNotIn("raw_query_response", output)
        self.assertEqual(request_json.call_count, 2)
        self.assertEqual(
            request_json.call_args_list[0].kwargs["url"],
            "https://api.example.com/taskapi/v1/task/batch/get",
        )
        sleep.assert_called_once_with(10)

    def test_main_routes_to_image_endpoint_and_sets_primary_image_url(self):
        result = {
            "task_id": "task-image-123",
            "status": 2,
            "source_url": "https://cdn.example.com/final-image.png",
        }

        with patch.object(self.module, "run_magicclaw_task", return_value=result) as run_magicclaw_task:
            exit_code, stdout, stderr = self.run_main(["--prompt", "make an angel"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        output = json.loads(stdout)
        self.assertEqual(output["task_id"], "task-image-123")
        self.assertEqual(output["primary_image_url"], "https://cdn.example.com/final-image.png")
        self.assertEqual(run_magicclaw_task.call_args.kwargs["create_path"], "/taskapi/v1/task/gen/img")
        self.assertTrue(run_magicclaw_task.call_args.kwargs["no_wait"])

    def test_main_wait_flag_polls_until_success(self):
        result = {
            "task_id": "task-image-123",
            "status": 2,
            "source_url": "https://cdn.example.com/final-image.png",
        }

        with patch.object(self.module, "run_magicclaw_task", return_value=result) as run_magicclaw_task:
            exit_code, stdout, stderr = self.run_main(["--prompt", "make an angel", "--wait"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertFalse(run_magicclaw_task.call_args.kwargs["no_wait"])


if __name__ == "__main__":
    unittest.main()
