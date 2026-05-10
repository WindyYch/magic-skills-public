#!/usr/bin/env python3
"""Generate images with the MagicLight open task API."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://server-test.magiclight.ai"
DEFAULT_MODEL = "gemini-2.5-flash-image"
DEFAULT_ASPECT_RATIO = "1:1"
DEFAULT_TIMEOUT = 60


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


def auto_task_id() -> str:
    millis = int(time.time() * 1000)
    suffix = secrets.randbelow(1000)
    return f"{millis}{suffix:03d}"


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


def choose_task_type(image_url: str | None) -> str:
    return "i2i" if image_url else "t2i"


def primary_image_url(data: dict[str, Any]) -> str | None:
    source_url = data.get("source_url")
    if isinstance(source_url, str) and source_url:
        return source_url

    result = data.get("result")
    if not isinstance(result, dict):
        return None

    images = result.get("images")
    if not isinstance(images, list) or not images:
        return None

    first = images[0]
    if not isinstance(first, dict):
        return None

    url = first.get("url")
    if isinstance(url, str) and url:
        return url

    return None


def build_payload(args: argparse.Namespace, user_id: str) -> dict[str, Any]:
    task_type = choose_task_type(args.image_url)
    payload: dict[str, Any] = {
        "type": task_type,
        "user_id": user_id,
        "task_id": args.task_id or auto_task_id(),
        "param": {
            "prompt": require_value("--prompt", args.prompt),
            "aspect_ratio": args.aspect_ratio,
            "model": args.model,
        },
    }

    if task_type == "i2i":
        payload["param"]["image_url"] = require_value("--image-url", args.image_url)
        payload["param"]["image_mime_type"] = args.image_mime_type

    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate images with the MagicLight API.",
    )
    parser.add_argument("--prompt", required=True, help="Prompt text for image generation.")
    parser.add_argument(
        "--image-url",
        help="Source image URL. When provided the request is sent as i2i instead of t2i.",
    )
    parser.add_argument(
        "--image-mime-type",
        default="image/jpeg",
        help="MIME type for the source image in i2i mode.",
    )
    parser.add_argument(
        "--aspect-ratio",
        default=DEFAULT_ASPECT_RATIO,
        help="Aspect ratio for the generated image, for example 1:1, 16:9, or 9:16.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="MagicLight image model to use.",
    )
    parser.add_argument("--task-id", help="Optional task ID. Auto-generated when omitted.")
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


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        user_id = args.user_id or require_env("MAGIC_USER_ID")
        svc_key = require_env("MAGIC_SVC_KEY")
        svc_auth = require_env("MAGIC_SVC_AUTH")

        payload = build_payload(args, user_id)
        base_url = args.base_url.rstrip("/")
        url = f"{base_url}/task-schedule/open_task/create"

        response = request_json(
            url=url,
            method="POST",
            headers=build_headers(svc_key, svc_auth),
            payload=payload,
            timeout=args.timeout,
        )
        data = extract_data(response)
        result = data.get("result") if isinstance(data.get("result"), dict) else {}

        output = {
            "type": data.get("type"),
            "task_id": data.get("task_id"),
            "status": data.get("status"),
            "need_query": data.get("need_query"),
            "primary_image_url": primary_image_url(data),
            "images": result.get("images") if isinstance(result, dict) else None,
            "text": result.get("text") if isinstance(result, dict) else None,
            "raw_response": response,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except MagicApiError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
