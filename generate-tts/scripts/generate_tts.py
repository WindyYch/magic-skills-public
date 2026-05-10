#!/usr/bin/env python3
"""Generate speech with the MiniMax synchronous HTTP TTS API."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://api.minimax.io/v1/t2a_v2"
DEFAULT_MODEL = "speech-2.8-hd"
DEFAULT_TIMEOUT = 60
DEFAULT_OUTPUT_FORMAT = "url"


class MiniMaxApiError(RuntimeError):
    """Raised when the MiniMax API request fails or returns bad data."""


def require_value(name: str, value: str | None) -> str:
    if value:
        return value
    raise MiniMaxApiError(f"Missing required value: {name}")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise MiniMaxApiError(f"Missing required environment variable: {name}")


def parse_json_object(name: str, raw_value: str | None) -> dict[str, Any]:
    if raw_value is None:
        return {}

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise MiniMaxApiError(f"{name} must be valid JSON: {exc.msg}") from exc

    if not isinstance(parsed, dict):
        raise MiniMaxApiError(f"{name} must decode to a JSON object")

    return parsed


def merge_settings(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    merged.update(override)
    return merged


def build_voice_setting(args: argparse.Namespace) -> dict[str, Any]:
    base = {
        "voice_id": require_value("--voice-id", args.voice_id),
        "speed": args.speed,
        "vol": args.vol,
        "pitch": args.pitch,
        "emotion": args.emotion,
    }
    return merge_settings(base, parse_json_object("--voice-setting-json", args.voice_setting_json))


def build_audio_setting(args: argparse.Namespace) -> dict[str, Any]:
    base = {
        "sample_rate": args.sample_rate,
        "bitrate": args.bitrate,
        "format": args.format,
        "channel": args.channel,
    }
    return merge_settings(base, parse_json_object("--audio-setting-json", args.audio_setting_json))


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": args.model,
        "text": require_value("--text", args.text),
        "stream": False,
        "output_format": args.output_format,
        "voice_setting": build_voice_setting(args),
        "audio_setting": build_audio_setting(args),
    }

    if args.subtitle_enable is not None:
        payload["subtitle_enable"] = args.subtitle_enable

    if args.language_boost is not None:
        payload["language_boost"] = args.language_boost

    if args.aigc_watermark:
        payload["aigc_watermark"] = True

    return payload


def build_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def build_request_url(base_url: str, group_id: str | None) -> str:
    if not group_id:
        return base_url

    parts = urlsplit(base_url)
    query_pairs = dict(parse_qsl(parts.query, keep_blank_values=True))
    query_pairs["GroupId"] = group_id
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_pairs), parts.fragment))


def is_certificate_verification_error(reason: object) -> bool:
    if isinstance(reason, ssl.SSLCertVerificationError):
        return True

    if isinstance(reason, ssl.SSLError):
        return "CERTIFICATE_VERIFY_FAILED" in str(reason)

    return "certificate verify failed" in str(reason).lower()


def build_insecure_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def read_response_body(request: Request, timeout: int) -> str:
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except URLError as exc:
        if not is_certificate_verification_error(exc.reason):
            raise

    with urlopen(request, timeout=timeout, context=build_insecure_ssl_context()) as response:
        return response.read().decode("utf-8")


def request_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=encoded, headers=headers, method="POST")

    try:
        body = read_response_body(request, timeout)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise MiniMaxApiError(f"HTTP {exc.code} from MiniMax API: {body}") from exc
    except URLError as exc:
        raise MiniMaxApiError(f"Failed to reach MiniMax API: {exc.reason}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MiniMaxApiError(f"MiniMax API returned invalid JSON: {body}") from exc

    if not isinstance(parsed, dict):
        raise MiniMaxApiError("MiniMax API response is not a JSON object")

    return parsed


def extract_success(response: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str | None]:
    base_resp = response.get("base_resp")
    if not isinstance(base_resp, dict):
        raise MiniMaxApiError("MiniMax API response is missing base_resp")

    status_code = base_resp.get("status_code")
    if status_code != 0:
        raise MiniMaxApiError(
            "MiniMax API error "
            f"status_code={status_code}: {base_resp.get('status_msg') or 'unknown error'}"
        )

    data = response.get("data")
    if not isinstance(data, dict):
        raise MiniMaxApiError("MiniMax API response is missing data")

    extra_info = response.get("extra_info")
    if extra_info is None:
        extra_info = {}
    elif not isinstance(extra_info, dict):
        raise MiniMaxApiError("MiniMax API response extra_info is not an object")

    trace_id = response.get("trace_id")
    if trace_id is not None and not isinstance(trace_id, str):
        raise MiniMaxApiError("MiniMax API response trace_id is not a string")

    return data, extra_info, trace_id


def decode_hex_audio(audio_hex: str) -> bytes:
    try:
        return bytes.fromhex(audio_hex)
    except ValueError as exc:
        raise MiniMaxApiError("MiniMax API returned invalid hex audio data") from exc


def write_audio_file(output_file: str, audio_bytes: bytes) -> str:
    output_path = Path(output_file).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(audio_bytes)
    return str(output_path)


def validate_args(args: argparse.Namespace) -> None:
    if args.output_format == "url" and args.output_file:
        raise MiniMaxApiError("--output-file is only supported when --output-format is hex")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate speech with the MiniMax synchronous HTTP TTS API.",
    )
    parser.add_argument("--text", required=True, help="Text to synthesize.")
    parser.add_argument(
        "--voice-id",
        required=True,
        help="MiniMax voice_setting.voice_id value.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="MiniMax TTS model name.",
    )
    parser.add_argument(
        "--group-id",
        help="Optional GroupId query parameter. Defaults to MINIMAX_GROUP_ID when set.",
    )
    parser.add_argument(
        "--output-format",
        choices=("hex", "url"),
        default=DEFAULT_OUTPUT_FORMAT,
        help="Non-stream output format.",
    )
    subtitle_group = parser.add_mutually_exclusive_group()
    subtitle_group.add_argument(
        "--subtitle-enable",
        dest="subtitle_enable",
        action="store_true",
        help="Enable subtitle generation.",
    )
    subtitle_group.add_argument(
        "--subtitle-disable",
        dest="subtitle_enable",
        action="store_false",
        help="Disable subtitle generation.",
    )
    parser.set_defaults(subtitle_enable=None)
    parser.add_argument(
        "--language-boost",
        help="Optional language boost value.",
    )
    parser.add_argument(
        "--aigc-watermark",
        action="store_true",
        help="Enable AIGC watermark output.",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="voice_setting.speed value.",
    )
    parser.add_argument(
        "--vol",
        type=float,
        default=1.0,
        help="voice_setting.vol value.",
    )
    parser.add_argument(
        "--pitch",
        type=int,
        default=0,
        help="voice_setting.pitch value.",
    )
    parser.add_argument(
        "--emotion",
        default="happy",
        help="voice_setting.emotion value.",
    )
    parser.add_argument(
        "--voice-setting-json",
        help="Raw JSON object merged into voice_setting after CLI defaults.",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=32000,
        help="audio_setting.sample_rate value.",
    )
    parser.add_argument(
        "--bitrate",
        type=int,
        default=128000,
        help="audio_setting.bitrate value.",
    )
    parser.add_argument(
        "--format",
        default="mp3",
        help="audio_setting.format value.",
    )
    parser.add_argument(
        "--channel",
        type=int,
        default=1,
        help="audio_setting.channel value.",
    )
    parser.add_argument(
        "--audio-setting-json",
        help="Raw JSON object merged into audio_setting after CLI defaults.",
    )
    parser.add_argument(
        "--output-file",
        help="Optional local output path for decoded audio bytes in hex mode.",
    )
    parser.add_argument(
        "--output-json",
        help=(
            "Optional path to write the raw JSON result before terminal redaction. "
            "Use this when downstream manifests need provider URLs exactly as returned."
        ),
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("MINIMAX_TTS_BASE_URL", DEFAULT_BASE_URL),
        help="MiniMax synchronous TTS endpoint URL.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="HTTP timeout in seconds.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        validate_args(args)
        api_key = require_env("MINIMAX_API_KEY")
        group_id = args.group_id or os.getenv("MINIMAX_GROUP_ID")
        payload = build_payload(args)
        response = request_json(
            url=build_request_url(args.base_url, group_id),
            headers=build_headers(api_key),
            payload=payload,
            timeout=args.timeout,
        )
        data, extra_info, trace_id = extract_success(response)

        audio_value = data.get("audio")
        if not isinstance(audio_value, str) or not audio_value:
            raise MiniMaxApiError("MiniMax API response is missing data.audio")

        audio_url: str | None = None
        audio_hex: str | None = None
        audio_bytes = 0
        output_path: str | None = None

        if args.output_format == "url":
            audio_url = audio_value
        else:
            audio_hex = audio_value
            decoded_audio = decode_hex_audio(audio_hex)
            audio_bytes = len(decoded_audio)
            if args.output_file:
                output_path = write_audio_file(args.output_file, decoded_audio)

        output = {
            "status": "success",
            "trace_id": trace_id,
            "audio_format": payload["audio_setting"].get("format"),
            "audio_url": audio_url,
            "audio_hex": audio_hex,
            "audio_bytes": audio_bytes,
            "output_path": output_path,
            "extra_info": extra_info,
            "raw_response": response,
        }
        if args.output_json:
            output_json_path = Path(args.output_json).expanduser()
            output_json_path.parent.mkdir(parents=True, exist_ok=True)
            output_json_path.write_text(
                json.dumps(output, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except MiniMaxApiError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
