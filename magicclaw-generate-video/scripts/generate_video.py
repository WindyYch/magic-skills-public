#!/usr/bin/env python3
"""Generate videos through the MagicClaw async task API."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

CREATE_PATH = "/taskapi/v1/task/gen/video"
QUERY_PATH = "/taskapi/v1/task/batch/get"
DEFAULT_TIMEOUT = 60
DEFAULT_POLL_INTERVAL_SECONDS = 10
DEFAULT_MAX_WAIT_SECONDS = 1800
SUCCESS_BIZ_CODE = 10000
SUCCESS_STATUS = "2"
RUNNING_STATUSES = {"0", "1"}
DOMAIN_ENV_NAMES = ("MagicClawDomain", "MAGIC_CLAW_DOMAIN")
AUTH_ENV_NAMES = ("MagicClawAuthorization", "MAGIC_CLAW_AUTHORIZATION")
SEEDANCE_MODEL_TYPE = "bytedance_seedance"
SEEDANCE_MODEL = "doubao-seedance-2-0-260128"
SEEDANCE_SOURCE = "gen-video-skill"
KLING_MODEL_TYPE = "duomi_kling"
KLING_MODEL = "kling-v3"
KLING_MODE = "std"
KLING_SOURCE = "video-gen-skill"
SEEDANCE_FPS = 24


class MagicClawApiError(RuntimeError):
    """Raised when a MagicClaw API request or response is invalid."""


def parse_bool_arg(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "0", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("Expected a boolean value: true or false")


def require_env(names: tuple[str, ...]) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    joined = " or ".join(names)
    raise MagicClawApiError(f"Missing required environment variable: {joined}")


def build_headers(authorization: str) -> dict[str, str]:
    return {
        "Authorization": authorization,
        "Content-Type": "application/json",
    }


def should_retry_insecure(error: BaseException) -> bool:
    reason = getattr(error, "reason", error)
    if isinstance(reason, ssl.SSLCertVerificationError):
        return True
    return "CERTIFICATE_VERIFY_FAILED" in str(reason)


def open_url(request: Request, timeout: int):
    try:
        return urlopen(request, timeout=timeout)
    except (URLError, ssl.SSLError) as exc:
        if not should_retry_insecure(exc):
            raise

    insecure_context = ssl._create_unverified_context()
    return urlopen(request, timeout=timeout, context=insecure_context)


def request_json(
    url: str,
    method: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    encoded = None
    if payload is not None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    try:
        request = Request(url, data=encoded, headers=headers, method=method)
    except ValueError as exc:
        raise MagicClawApiError(f"Invalid MagicClaw request URL: {url}") from exc

    try:
        with open_url(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise MagicClawApiError(f"HTTP {exc.code} from MagicClaw API: {body}") from exc
    except (URLError, ssl.SSLError) as exc:
        reason = getattr(exc, "reason", exc)
        raise MagicClawApiError(f"Failed to reach MagicClaw API: {reason}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MagicClawApiError(f"MagicClaw API returned invalid JSON: {body}") from exc

    if not isinstance(parsed, dict):
        raise MagicClawApiError("MagicClaw API response is not a JSON object")
    return parsed


def normalize_base_url(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise MagicClawApiError("MagicClaw base URL must not be empty")

    parsed = urlparse(normalized)
    if not parsed.scheme:
        normalized = f"https://{normalized}"
        parsed = urlparse(normalized)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise MagicClawApiError(
            "MagicClaw base URL must be an absolute http:// or https:// URL or a bare domain"
        )
    return normalized.rstrip("/")


def resolve_base_url(base_url: str | None) -> str:
    if base_url:
        return normalize_base_url(base_url)
    return normalize_base_url(require_env(DOMAIN_ENV_NAMES))


def join_url(base_url: str, path: str) -> str:
    if path.startswith("/"):
        return f"{base_url}{path}"
    return f"{base_url}/{path}"


def extract_data(response: dict[str, Any], context: str) -> dict[str, Any]:
    if response.get("biz_code") != SUCCESS_BIZ_CODE:
        raise MagicClawApiError(
            f"MagicClaw {context} request failed with biz_code={response.get('biz_code')}: {response.get('msg')}"
        )

    data = response.get("data")
    if not isinstance(data, dict):
        raise MagicClawApiError(f"MagicClaw {context} response is missing a data object")
    return data


def extract_create_task_id(response: dict[str, Any]) -> str:
    data = extract_data(response, "create")
    task_id = data.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        raise MagicClawApiError("MagicClaw create response is missing task_id")
    return task_id


def parse_json_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


def coerce_status(status: Any) -> str | None:
    if status is None:
        return None
    return str(status)


def is_success_status(status: Any) -> bool:
    return coerce_status(status) == SUCCESS_STATUS


def is_running_status(status: Any) -> bool:
    normalized = coerce_status(status)
    return normalized in RUNNING_STATUSES


def extract_result_url(task_result: Any) -> str | None:
    if not isinstance(task_result, dict):
        return None

    direct_url = task_result.get("url")
    if isinstance(direct_url, str) and direct_url:
        return direct_url

    result_payload = task_result.get("result_payload")
    if not isinstance(result_payload, dict):
        return None

    items = result_payload.get("items")
    if not isinstance(items, list) or not items:
        return None

    first = items[0]
    if not isinstance(first, dict):
        return None

    for key in ("result_url", "vendor_url"):
        value = first.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def extract_source_url(task: dict[str, Any], task_result: Any) -> str | None:
    source_url = task.get("source_url")
    if isinstance(source_url, str) and source_url:
        return source_url
    return extract_result_url(task_result)


def extract_task_record(response: dict[str, Any], task_id: str) -> dict[str, Any]:
    data = extract_data(response, "query")
    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise MagicClawApiError("MagicClaw query response is missing tasks")

    for item in tasks:
        if isinstance(item, dict) and item.get("task_id") == task_id:
            return item
    raise MagicClawApiError(f"MagicClaw query response does not contain task_id={task_id}")


def build_pending_output(task_id: str, create_response: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "status": None,
        "source_url": None,
        "query_attempts": 0,
        "elapsed_seconds": 0.0,
        "trace_id": create_response.get("trace_id"),
    }


def build_task_output(
    task_id: str,
    task: dict[str, Any],
    create_response: dict[str, Any] | None,
    query_response: dict[str, Any],
    query_attempts: int,
    elapsed_seconds: float,
) -> dict[str, Any]:
    task_result_raw = task.get("task_result")
    task_result = parse_json_text(task_result_raw)

    return {
        "task_id": task_id,
        "status": task.get("status"),
        "source_url": extract_source_url(task, task_result),
        "query_attempts": query_attempts,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "trace_id": query_response.get("trace_id") or (create_response or {}).get("trace_id"),
    }


def query_task_once(
    base_url: str,
    headers: dict[str, str],
    task_id: str,
    timeout: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    response = request_json(
        url=join_url(base_url, QUERY_PATH),
        method="POST",
        headers=headers,
        payload={"task_ids": [task_id]},
        timeout=timeout,
    )
    task = extract_task_record(response, task_id)
    return response, task


def wait_for_task(
    base_url: str,
    headers: dict[str, str],
    task_id: str,
    create_response: dict[str, Any] | None,
    poll_interval_seconds: int,
    max_wait_seconds: int,
    timeout: int,
) -> dict[str, Any]:
    started = time.time()
    deadline = started + max_wait_seconds
    attempts = 0

    while time.time() <= deadline:
        attempts += 1
        query_response, task = query_task_once(
            base_url=base_url,
            headers=headers,
            task_id=task_id,
            timeout=timeout,
        )
        status = task.get("status")

        if is_success_status(status):
            return build_task_output(
                task_id=task_id,
                task=task,
                create_response=create_response,
                query_response=query_response,
                query_attempts=attempts,
                elapsed_seconds=time.time() - started,
            )

        if not is_running_status(status):
            raise MagicClawApiError(
                f"MagicClaw task failed with status={status}: {task.get('task_result')}"
            )

        time.sleep(poll_interval_seconds)

    raise MagicClawApiError(
        f"MagicClaw task did not finish within {max_wait_seconds} seconds"
    )


def run_magicclaw_task(
    *,
    create_path: str,
    payload: dict[str, Any] | None,
    task_id: str | None,
    no_wait: bool,
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
    max_wait_seconds: int = DEFAULT_MAX_WAIT_SECONDS,
    timeout: int = DEFAULT_TIMEOUT,
    base_url: str | None = None,
) -> dict[str, Any]:
    if timeout <= 0:
        raise MagicClawApiError("--timeout must be greater than 0")
    if poll_interval_seconds < 0:
        raise MagicClawApiError("--poll-interval-seconds must be greater than or equal to 0")
    if max_wait_seconds < 0:
        raise MagicClawApiError("--max-wait-seconds must be greater than or equal to 0")
    if task_id is None and payload is None:
        raise MagicClawApiError("payload is required when task_id is not provided")

    resolved_base_url = resolve_base_url(base_url)
    headers = build_headers(require_env(AUTH_ENV_NAMES))

    create_response = None
    resolved_task_id = task_id

    if resolved_task_id is None:
        create_response = request_json(
            url=join_url(resolved_base_url, create_path),
            method="POST",
            headers=headers,
            payload=payload,
            timeout=timeout,
        )
        resolved_task_id = extract_create_task_id(create_response)
        if no_wait:
            return build_pending_output(resolved_task_id, create_response)

    if no_wait:
        query_response, task = query_task_once(
            base_url=resolved_base_url,
            headers=headers,
            task_id=resolved_task_id,
            timeout=timeout,
        )
        return build_task_output(
            task_id=resolved_task_id,
            task=task,
            create_response=create_response,
            query_response=query_response,
            query_attempts=1,
            elapsed_seconds=0.0,
        )

    return wait_for_task(
        base_url=resolved_base_url,
        headers=headers,
        task_id=resolved_task_id,
        create_response=create_response,
        poll_interval_seconds=poll_interval_seconds,
        max_wait_seconds=max_wait_seconds,
        timeout=timeout,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a video with the MagicClaw async task API.",
    )
    parser.add_argument("--task-id", help="Existing MagicClaw task ID to query.")
    parser.add_argument(
        "--model-type",
        choices=[SEEDANCE_MODEL_TYPE, KLING_MODEL_TYPE],
        help="Video generation schema to use when creating a task.",
    )
    parser.add_argument("--model", help="Optional model override for the selected model_type.")
    parser.add_argument("--duration", type=int, default=5, help="Output duration in seconds.")
    parser.add_argument("--mode", help="Optional mode value sent to MagicClaw.")
    parser.add_argument("--source", help="Optional source tag override.")
    parser.add_argument(
        "--ratio",
        help="Aspect ratio for bytedance_seedance.",
    )
    parser.add_argument(
        "--resolution",
        help="Output resolution for bytedance_seedance.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=SEEDANCE_FPS,
        help="Frame rate for bytedance_seedance.",
    )
    parser.add_argument(
        "--generate-audio",
        type=parse_bool_arg,
        help="Whether bytedance_seedance should generate background music: true or false.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Optional random seed for bytedance_seedance consistency control.",
    )
    parser.add_argument(
        "--watermark",
        type=parse_bool_arg,
        help="Whether bytedance_seedance should include a watermark: true or false.",
    )
    parser.add_argument(
        "--image-url",
        action="append",
        dest="image_urls",
        help="Reference image URL for bytedance_seedance. Repeat this flag for multiple references.",
    )
    parser.add_argument("--text", help="Narrative text for bytedance_seedance content mode.")
    parser.add_argument("--img-url", help="Source image URL for duomi_kling.")
    parser.add_argument("--prompt", help="Prompt text for duomi_kling.")
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Seconds to wait between task status checks.",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=DEFAULT_MAX_WAIT_SECONDS,
        help="Maximum total seconds to wait for task completion.",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Deprecated compatibility flag. Async submit is now the default.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Poll until the task reaches success and return the final asset URL.",
    )
    parser.add_argument("--base-url", help="Optional MagicClaw domain override.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="HTTP timeout in seconds for each request.",
    )
    return parser


def validate_args(args: argparse.Namespace) -> argparse.Namespace:
    if args.task_id:
        for field in ("model_type", "image_urls", "text", "img_url", "prompt"):
            value = getattr(args, field)
            if value:
                flag = f"--{field.replace('_', '-')}"
                raise MagicClawApiError(f"{flag} cannot be used with --task-id")
        return args

    if not args.model_type:
        raise MagicClawApiError("--model-type is required unless --task-id is provided")

    if args.model_type == SEEDANCE_MODEL_TYPE:
        if not args.image_urls:
            raise MagicClawApiError(
                "At least one --image-url is required for --model-type bytedance_seedance"
            )
        if not args.text or not args.text.strip():
            raise MagicClawApiError("--text is required for --model-type bytedance_seedance")
        return args

    if not args.img_url or not args.img_url.strip():
        raise MagicClawApiError("--img-url is required for --model-type duomi_kling")
    if not args.prompt or not args.prompt.strip():
        raise MagicClawApiError("--prompt is required for --model-type duomi_kling")
    return args


def build_payload(args: argparse.Namespace) -> dict[str, object]:
    if args.model_type == SEEDANCE_MODEL_TYPE:
        content = [
            {
                "image_url": image_url,
                "type": "image_url",
                "role": "reference_image",
            }
            for image_url in args.image_urls
        ]
        content.append({"type": "text", "text": args.text})
        payload: dict[str, object] = {
            "content": content,
            "duration": args.duration,
            "fps": args.fps,
            "model": args.model or SEEDANCE_MODEL,
            "model_type": SEEDANCE_MODEL_TYPE,
            "source": args.source or SEEDANCE_SOURCE,
        }
        if args.mode:
            payload["mode"] = args.mode
        if args.ratio:
            payload["ratio"] = args.ratio
        if args.resolution:
            payload["resolution"] = args.resolution
        if args.generate_audio is not None:
            payload["generate_audio"] = args.generate_audio
        if args.seed is not None:
            payload["seed"] = args.seed
        if args.watermark is not None:
            payload["watermark"] = args.watermark
        return payload

    payload = {
        "duration": args.duration,
        "img_url": args.img_url,
        "mode": args.mode or KLING_MODE,
        "model": args.model or KLING_MODEL,
        "model_type": KLING_MODEL_TYPE,
        "prompt": args.prompt,
        "source": args.source or KLING_SOURCE,
    }
    return payload


def main() -> int:
    parser = build_parser()
    args = validate_args(parser.parse_args())

    try:
        payload = None if args.task_id else build_payload(args)
        output = run_magicclaw_task(
            create_path=CREATE_PATH,
            payload=payload,
            task_id=args.task_id,
            no_wait=args.no_wait or not args.wait,
            poll_interval_seconds=args.poll_interval_seconds,
            max_wait_seconds=args.max_wait_seconds,
            timeout=args.timeout,
            base_url=args.base_url,
        )
        output["video_url"] = output.get("source_url")
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except MagicClawApiError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
