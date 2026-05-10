#!/usr/bin/env python3
"""Generate image-to-video clips with the MagicLight open task API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://server-test.magiclight.ai"
DEFAULT_TIMEOUT = 60
DEFAULT_POLL_INTERVAL_SECONDS = 5
DEFAULT_MAX_WAIT_SECONDS = 300
RUNNING_STATUS = 1
SUCCESS_STATUS = 2


class MagicApiError(RuntimeError):
    """Raised when the MagicLight API request fails."""


def require_value(name: str, value: str | None) -> str:
    if value:
        return value
    raise MagicApiError(f"Missing required value: {name}")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise MagicApiError(f"Missing required environment variable: {name}")


def build_headers(svc_key: str, svc_auth: str) -> dict[str, str]:
    return {
        "Magic-Svc-Key": svc_key,
        "Magic-Svc-Auth": svc_auth,
        "Content-Type": "application/json",
    }


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

    request = Request(url, data=encoded, headers=headers, method=method)

    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise MagicApiError(f"HTTP {exc.code} from MagicLight API: {body}") from exc
    except URLError as exc:
        raise MagicApiError(f"Failed to reach MagicLight API: {exc.reason}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MagicApiError(f"MagicLight API returned invalid JSON: {body}") from exc

    if not isinstance(parsed, dict):
        raise MagicApiError("MagicLight API response is not a JSON object")

    return parsed


def extract_data(response: dict[str, Any]) -> dict[str, Any]:
    if response.get("biz_code") != 10000:
        raise MagicApiError(
            f"MagicLight API error biz_code={response.get('biz_code')}: {response.get('msg')}"
        )

    data = response.get("data")
    if not isinstance(data, dict):
        raise MagicApiError("MagicLight API response is missing a data object")

    return data


def build_query_url(base_url: str, user_id: str, task_id: str) -> str:
    query = urlencode({"user_id": user_id, "task_id": task_id})
    return f"{base_url.rstrip('/')}/task-schedule/open_task/get?{query}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a video with the MagicLight image-to-video API.",
    )
    parser.add_argument("--prompt", required=True, help="Prompt text for video generation.")
    parser.add_argument("--img-url", required=True, help="Source image URL.")
    parser.add_argument("--ratio", type=int, default=1, help="Ratio parameter sent to the API.")
    parser.add_argument(
        "--definition",
        default="720",
        help="Output definition sent to the API.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=5,
        help="Output duration in seconds.",
    )
    parser.add_argument(
        "--image2video-pro-type",
        default="seedance2_0",
        help="MagicLight i2v pro type.",
    )
    audio_group = parser.add_mutually_exclusive_group()
    audio_group.add_argument(
        "--enable-audio",
        dest="enable_audio",
        action="store_true",
        help="Enable audio generation.",
    )
    audio_group.add_argument(
        "--disable-audio",
        dest="enable_audio",
        action="store_false",
        help="Disable audio generation.",
    )
    parser.set_defaults(enable_audio=True)
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Polling interval when need_query=true.",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=DEFAULT_MAX_WAIT_SECONDS,
        help="Maximum total wait time when polling.",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Return immediately after task creation even if need_query=true.",
    )
    parser.add_argument(
        "--user-id",
        help="Optional user ID override. Defaults to MAGIC_USER_ID.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("MAGIC_API_BASE_URL", DEFAULT_BASE_URL),
        help="MagicLight API base URL.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="HTTP timeout in seconds.",
    )
    return parser


def fetch_video_result(
    base_url: str,
    headers: dict[str, str],
    user_id: str,
    task_id: str,
    poll_interval_seconds: int,
    max_wait_seconds: int,
    timeout: int,
) -> tuple[dict[str, Any], int, float]:
    deadline = time.time() + max_wait_seconds
    attempts = 0
    started = time.time()

    while time.time() <= deadline:
        attempts += 1
        response = request_json(
            url=build_query_url(base_url, user_id, task_id),
            method="GET",
            headers=headers,
            timeout=timeout,
        )
        data = extract_data(response)
        status = data.get("status")

        if status == SUCCESS_STATUS:
            return response, attempts, time.time() - started

        if status != RUNNING_STATUS:
            raise MagicApiError(
                "MagicLight video task failed with "
                f"status={status}, error_code={data.get('error_code')}, "
                f"error_message={data.get('error_message')}"
            )

        time.sleep(poll_interval_seconds)

    raise MagicApiError(
        f"MagicLight video task did not finish within {max_wait_seconds} seconds"
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        user_id = args.user_id or require_env("MAGIC_USER_ID")
        svc_key = require_env("MAGIC_SVC_KEY")
        svc_auth = require_env("MAGIC_SVC_AUTH")
        base_url = args.base_url.rstrip("/")
        headers = build_headers(svc_key, svc_auth)

        payload = {
            "type": "i2v",
            "user_id": user_id,
            "param": {
                "ratio": args.ratio,
                "definition": args.definition,
                "duration": args.duration,
                "image2video_pro_type": args.image2video_pro_type,
                "enable_audio": args.enable_audio,
                "prompt": require_value("--prompt", args.prompt),
                "img_url": require_value("--img-url", args.img_url),
            },
        }

        create_response = request_json(
            url=f"{base_url}/task-schedule/open_task/create",
            method="POST",
            headers=headers,
            payload=payload,
            timeout=args.timeout,
        )
        create_data = extract_data(create_response)
        task_id = create_data.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise MagicApiError("MagicLight create response is missing task_id")

        output = {
            "task_id": task_id,
            "status": create_data.get("status"),
            "need_query": create_data.get("need_query"),
            "video_url": None,
            "query_attempts": 0,
            "elapsed_seconds": 0.0,
            "raw_create_response": create_response,
            "raw_query_response": None,
        }

        if not create_data.get("need_query") or args.no_wait:
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0

        query_response, attempts, elapsed = fetch_video_result(
            base_url=base_url,
            headers=headers,
            user_id=user_id,
            task_id=task_id,
            poll_interval_seconds=args.poll_interval_seconds,
            max_wait_seconds=args.max_wait_seconds,
            timeout=args.timeout,
        )
        query_data = extract_data(query_response)
        result = query_data.get("result")
        if not isinstance(result, dict):
            raise MagicApiError("MagicLight query response is missing result data")

        video_url = result.get("video_url")
        if not isinstance(video_url, str) or not video_url:
            raise MagicApiError("MagicLight query response is missing video_url")

        output.update(
            {
                "status": query_data.get("status"),
                "video_url": video_url,
                "query_attempts": attempts,
                "elapsed_seconds": round(elapsed, 2),
                "raw_query_response": query_response,
            }
        )
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except MagicApiError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
