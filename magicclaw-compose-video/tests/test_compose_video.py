import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "compose_video.py"


def load_module():
    spec = importlib.util.spec_from_file_location("magicclaw_compose_video", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MagicClawComposeVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def write_param(self, project_dir: Path) -> Path:
        param_path = project_dir / "video-orchestrator-param.json"
        param_path.write_text(
            json.dumps(
                {
                    "job_kind": "render_from_edit_assets",
                    "schema_version": "v1",
                    "trace_id": "trace-from-param",
                    "input_protocol": "video_remotion_renderer",
                    "input_protocol_version": "v1",
                    "project": {
                        "project_id": "demo-project",
                        "aspect_ratio": "9:16",
                    },
                    "timeline": {
                        "scenes": [
                            {
                                "scene_id": "S_01",
                                "duration_sec": 2.0,
                            }
                        ],
                    },
                    "assets": {
                        "items": [
                            {
                                "asset_id": "IMG_S01",
                                "asset_type": "image",
                                "source_url": "https://example.com/image.png",
                            }
                        ],
                    },
                    "subtitles": {
                        "alignment": {},
                    },
                    "render_options": {
                        "output_format": "mp4",
                        "fps": 30,
                        "resolution": {
                            "width": 1080,
                            "height": 1920,
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        return param_path

    def test_build_request_body_from_video_orchestrator_param(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            param_path = self.write_param(project_dir)
            parser = self.module.build_parser()
            args = parser.parse_args(
                [
                    "--video-orchestrator-param",
                    str(param_path),
                    "--trace-id",
                    "trace-demo",
                    "--biz-callback-extra-json",
                    '{"request_id":"req-123"}',
                ]
            )

            payload = self.module.build_request_body(args)

        self.assertNotIn("trace_id", payload)
        self.assertEqual(payload["source"], "magicclaw_compose_video")
        self.assertEqual(payload["biz_callback_extra_json"], {"request_id": "req-123"})
        self.assertEqual(payload["video_orchestrator_param_json"]["trace_id"], "trace-demo")
        self.assertEqual(self.module.payload_trace_id(payload), "trace-demo")
        with patch.dict("os.environ", {"MAGICCLAW_TASK_TOKEN": "token-demo"}):
            self.assertEqual(self.module.build_headers("trace-demo")["X-Trace-Id"], "trace-demo")
        self.assertEqual(
            payload["video_orchestrator_param_json"]["input_protocol"],
            "video_remotion_renderer",
        )
        self.assertEqual(
            payload["video_orchestrator_param_json"]["render_options"]["resolution"],
            {"width": 1080, "height": 1920},
        )
        self.assertEqual(payload["video_orchestrator_param_json"]["subtitles"]["alignment"], {})

    def test_default_create_endpoint_uses_v2(self):
        parser = self.module.build_parser()
        args = parser.parse_args(["--task-id", "task-123", "--no-wait"])

        self.assertEqual(args.endpoint_path, "/taskapi/v1/task/gen/video-orchestrator-v2")

    def test_submit_only_output_contract(self):
        result = self.module.build_pending_output(
            "task-123",
            {"biz_code": 10000, "trace_id": "trace-demo", "data": {"task_id": "task-123"}},
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "submit_only")
        self.assertEqual(result["task_id"], "task-123")
        self.assertEqual(result["status"], "submitted")
        self.assertEqual(result["status_code"], 1)
        self.assertIsNone(result["video_url"])
        self.assertIsNone(result["error"])
        self.assertIn("raw_create_response", result["debug"])

    def test_success_output_contract(self):
        result = self.module.build_task_output(
            task_id="task-456",
            task={
                "task_id": "task-456",
                "status": 2,
                "source_url": "https://cdn.example.com/final.mp4",
                "task_type": "video",
                "model_type": "video-orchestrator",
                "source": "magicclaw_compose_video",
                "input_params": "{}",
                "task_result": '{"url":"https://fallback.example.com/final.mp4"}',
            },
            create_response=None,
            query_response={"trace_id": "trace-query", "data": {"tasks": []}},
            query_attempts=3,
            elapsed_seconds=12.345,
            mode="query",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "query")
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["status_code"], 2)
        self.assertEqual(result["video_url"], "https://cdn.example.com/final.mp4")
        self.assertEqual(result["elapsed_seconds"], 12.35)
        self.assertIsNone(result["error"])
        self.assertEqual(result["debug"]["task_result"], {"url": "https://fallback.example.com/final.mp4"})

    def test_failed_task_output_contract(self):
        result = self.module.build_task_output(
            task_id="task-789",
            task={
                "task_id": "task-789",
                "status": 3,
                "source_url": "https://cdn.example.com/failed.mp4",
                "task_result": '{"error_code":"render_failed"}',
            },
            create_response=None,
            query_response={"trace_id": "trace-query", "data": {"tasks": []}},
            query_attempts=1,
            elapsed_seconds=0.0,
            mode="query",
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["status_code"], 3)
        self.assertIsNone(result["video_url"])
        self.assertEqual(result["error"]["type"], "TaskFailed")

    def test_main_validation_error_uses_stable_error_schema(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(sys, "argv", ["compose_video.py"]):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = self.module.main()

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        output = json.loads(stderr.getvalue())
        self.assertFalse(output["ok"])
        self.assertEqual(output["status"], "failed")
        self.assertEqual(output["error"]["type"], "SubmitError")


if __name__ == "__main__":
    unittest.main()
