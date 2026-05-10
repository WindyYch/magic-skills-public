import contextlib
import importlib.util
import io
import json
import os
import ssl
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_tts.py"


def load_module():
    spec = importlib.util.spec_from_file_location("generate_tts", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GenerateTtsCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def run_main(self, argv, env=None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        merged_env = {"MINIMAX_API_KEY": "test-api-key"} if env is None else env
        with patch.object(sys, "argv", ["generate_tts.py", *argv]):
            with patch.dict(os.environ, merged_env, clear=True):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    exit_code = self.module.main()
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_build_payload_uses_cli_flags_and_defaults(self):
        parser = self.module.build_parser()
        args = parser.parse_args(
            [
                "--text",
                "hello world",
                "--voice-id",
                "male-qn-qingse",
                "--sample-rate",
                "32000",
                "--bitrate",
                "128000",
                "--format",
                "mp3",
                "--channel",
                "1",
            ]
        )

        payload = self.module.build_payload(args)

        self.assertEqual(payload["model"], self.module.DEFAULT_MODEL)
        self.assertEqual(payload["text"], "hello world")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["output_format"], "url")
        self.assertEqual(
            payload["voice_setting"],
            {
                "voice_id": "male-qn-qingse",
                "speed": 1.0,
                "vol": 1.0,
                "pitch": 0,
                "emotion": "happy",
            },
        )
        self.assertEqual(
            payload["audio_setting"],
            {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
        )

    def test_build_payload_merges_json_overrides(self):
        parser = self.module.build_parser()
        args = parser.parse_args(
            [
                "--text",
                "hello world",
                "--voice-id",
                "male-qn-qingse",
                "--voice-setting-json",
                '{"speed": 1.25, "emotion": "sad", "english_normalization": true}',
                "--audio-setting-json",
                '{"format": "flac", "sample_rate": 44100}',
            ]
        )

        payload = self.module.build_payload(args)

        self.assertEqual(payload["voice_setting"]["speed"], 1.25)
        self.assertEqual(payload["voice_setting"]["emotion"], "sad")
        self.assertTrue(payload["voice_setting"]["english_normalization"])
        self.assertEqual(payload["audio_setting"]["format"], "flac")
        self.assertEqual(payload["audio_setting"]["sample_rate"], 44100)

    def test_build_request_url_appends_group_id(self):
        url = self.module.build_request_url(
            "https://api.minimaxi.com/v1/t2a_v2",
            "group-123",
        )

        self.assertEqual(url, "https://api.minimaxi.com/v1/t2a_v2?GroupId=group-123")

    def test_build_parser_defaults_to_official_https_base_url(self):
        with patch.dict(os.environ, {}, clear=True):
            parser = self.module.build_parser()
            args = parser.parse_args(
                [
                    "--text",
                    "hello world",
                    "--voice-id",
                    "male-qn-qingse",
                ]
            )

        self.assertEqual(args.base_url, "https://api.minimax.io/v1/t2a_v2")

    def test_request_json_retries_with_insecure_context_after_certificate_verify_failure(self):
        response_body = json.dumps({"ok": True}).encode("utf-8")
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
                url="https://api.minimax.io/v1/t2a_v2",
                headers={"Authorization": "Bearer test"},
                payload={"text": "hello"},
                timeout=30,
            )

        self.assertEqual(parsed, {"ok": True})
        self.assertEqual(len(call_kwargs), 2)
        self.assertNotIn("context", call_kwargs[0])
        self.assertIn("context", call_kwargs[1])
        self.assertFalse(call_kwargs[1]["context"].check_hostname)
        self.assertEqual(call_kwargs[1]["context"].verify_mode, ssl.CERT_NONE)

    def test_main_rejects_output_file_in_url_mode(self):
        exit_code, stdout, stderr = self.run_main(
            [
                "--text",
                "hello world",
                "--voice-id",
                "male-qn-qingse",
                "--output-format",
                "url",
                "--output-file",
                "/tmp/out.mp3",
            ]
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("--output-file is only supported when --output-format is hex", stderr)

    def test_main_returns_audio_url_without_writing_file(self):
        response = {
            "data": {
                "audio": "https://example.com/generated.mp3",
            },
            "trace_id": "trace-url-123",
            "extra_info": {"audio_length": 2.3},
            "base_resp": {"status_code": 0, "status_msg": "success"},
        }

        with patch.object(self.module, "request_json", return_value=response):
            exit_code, stdout, stderr = self.run_main(
                [
                    "--text",
                    "hello world",
                    "--voice-id",
                    "male-qn-qingse",
                    "--output-format",
                    "url",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        output = json.loads(stdout)
        self.assertEqual(output["trace_id"], "trace-url-123")
        self.assertEqual(output["audio_url"], "https://example.com/generated.mp3")
        self.assertIsNone(output["audio_hex"])
        self.assertIsNone(output["output_path"])
        self.assertEqual(output["audio_bytes"], 0)

    def test_main_saves_hex_audio_to_file_when_requested(self):
        response = {
            "data": {
                "audio": "6869",
            },
            "trace_id": "trace-hex-456",
            "extra_info": {"audio_length": 1.1},
            "base_resp": {"status_code": 0, "status_msg": "success"},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "speech.mp3"
            with patch.object(self.module, "request_json", return_value=response):
                exit_code, stdout, stderr = self.run_main(
                    [
                        "--text",
                        "hello world",
                        "--voice-id",
                        "male-qn-qingse",
                        "--output-format",
                        "hex",
                        "--output-file",
                        str(output_file),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr, "")
            self.assertEqual(output_file.read_bytes(), b"hi")
            output = json.loads(stdout)
            self.assertEqual(output["trace_id"], "trace-hex-456")
            self.assertEqual(output["audio_hex"], "6869")
            self.assertEqual(output["audio_bytes"], 2)
            self.assertEqual(output["output_path"], str(output_file))


if __name__ == "__main__":
    unittest.main()
