#!/usr/bin/env python3
"""Compose multiple images into one generated image via the Duomi API."""

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

DEFAULT_BASE_URL = "https://duomiapi.com"
DEFAULT_MODEL = "nano-banana-pro"
DEFAULT_IMAGE_SIZE = "1K"
DEFAULT_TIMEOUT = 60
DEFAULT_POLL_INTERVAL_SECONDS = 10
DEFAULT_MAX_WAIT_SECONDS = 1800
SUCCESS_CODE = 200
SUCCESS_MSG = "success"
TERMINAL_FAILURE_STATES = {"failed", "error", "cancelled"}
RUNNING_STATES = {"pending", "queued", "running", "processing"}


class DuomiApiError(RuntimeError):
    """Raised when a Duomi API request fails."""


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise DuomiApiError(f"Missing required environment variable: {name}")


def build_headers(token: str) -> dict[str, str]:
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }
    cookie = os.getenv("DUOMI_API_COOKIE")
    if cookie:
        headers["Cookie"] = cookie
    return headers


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
        raise DuomiApiError(f"Invalid Duomi request URL: {url}") from exc

    try:
        with open_url(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise DuomiApiError(f"HTTP {exc.code} from Duomi API: {body}") from exc
    except (URLError, ssl.SSLError) as exc:
        reason = getattr(exc, "reason", exc)
        raise DuomiApiError(f"Failed to reach Duomi API: {reason}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise DuomiApiError(f"Duomi API returned invalid JSON: {body}") from exc

    if not isinstance(parsed, dict):
        raise DuomiApiError("Duomi API response is not a JSON object")

    return parsed


def extract_response_data(response: dict[str, Any], context: str) -> dict[str, Any]:
    if response.get("code") != SUCCESS_CODE or response.get("msg") != SUCCESS_MSG:
        raise DuomiApiError(
            f"Duomi {context} request failed with code={response.get('code')}: {response.get('msg')}"
        )

    data = response.get("data")
    if not isinstance(data, dict):
        raise DuomiApiError(f"Duomi {context} response is missing a data object")

    return data


def extract_task_id(response: dict[str, Any]) -> str:
    data = extract_response_data(response, "create")
    task_id = data.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        raise DuomiApiError("Duomi create response is missing task_id")
    return task_id


def extract_query_data(response: dict[str, Any]) -> dict[str, Any]:
    return extract_response_data(response, "query")


def extract_task_state(query_data: dict[str, Any]) -> str:
    state = query_data.get("state")
    if not isinstance(state, str) or not state.strip():
        raise DuomiApiError("Duomi query response is missing task state")
    return state.strip()


def extract_result_data(query_data: dict[str, Any]) -> dict[str, Any]:
    result_data = query_data.get("data")
    if not isinstance(result_data, dict):
        raise DuomiApiError("Duomi query response is missing result data")
    return result_data


def primary_image_url(query_data: dict[str, Any]) -> str | None:
    result_data = query_data.get("data")
    if not isinstance(result_data, dict):
        return None

    images = result_data.get("images")
    if not isinstance(images, list) or not images:
        return None

    first = images[0]
    if not isinstance(first, dict):
        return None

    url = first.get("url")
    if isinstance(url, str) and url:
        return url

    return None


def validate_base_url(base_url: str) -> str:
    normalized = base_url.strip()
    if not normalized:
        raise DuomiApiError("--base-url must not be empty")

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise DuomiApiError("--base-url must be an absolute http:// or https:// URL")

    return normalized.rstrip("/")


def resolve_generation_params(args: argparse.Namespace) -> dict[str, str]:
    return {
        "model": args.model,
        "aspect_ratio": args.aspect_ratio,
        "image_size": args.image_size,
    }


def validate_args(args: argparse.Namespace) -> argparse.Namespace:
    if args.timeout <= 0:
        raise DuomiApiError("--timeout must be greater than 0")
    if args.poll_interval_seconds < 0:
        raise DuomiApiError("--poll-interval-seconds must be greater than or equal to 0")
    if args.max_wait_seconds < 0:
        raise DuomiApiError("--max-wait-seconds must be greater than or equal to 0")

    if args.preview_params:
        if args.task_id is not None:
            raise DuomiApiError("--preview-params cannot be used with --task-id")
        if args.prompt is not None:
            raise DuomiApiError("--preview-params cannot be used with --prompt")
        if args.image_urls:
            raise DuomiApiError("--preview-params cannot be used with --image-url")
        args.base_url = validate_base_url(args.base_url)
        return args

    if args.task_id is not None:
        args.task_id = args.task_id.strip()
        if not args.task_id:
            raise DuomiApiError("--task-id must not be empty")
        if args.prompt is not None:
            raise DuomiApiError("--prompt cannot be used with --task-id")
        if args.image_urls:
            raise DuomiApiError("--image-url cannot be used with --task-id")
    else:
        if args.prompt is None or not args.prompt.strip():
            raise DuomiApiError("--prompt is required unless --task-id is provided")
        if not args.image_urls:
            raise DuomiApiError("At least one --image-url is required unless --task-id is provided")

    args.base_url = validate_base_url(args.base_url)
    return args


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compose multiple images into one generated image with the Duomi API.",
    )
    parser.add_argument(
        "--task-id",
        help="Existing Duomi task ID to query instead of creating a new task.",
    )
    parser.add_argument(
        "--prompt",
        help="Prompt text describing the target edit.",
    )
    parser.add_argument(
        "--image-url",
        action="append",
        dest="image_urls",
        help="Source image URL. Repeat this flag to provide multiple images.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Duomi Gemini image model to use.",
    )
    parser.add_argument(
        "--aspect-ratio",
        default="",
        help="Optional output aspect ratio, for example 1:1 or 16:9.",
    )
    parser.add_argument(
        "--image-size",
        default=DEFAULT_IMAGE_SIZE,
        help="Output image size sent to the Duomi API.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Seconds to wait between Duomi task status checks.",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=DEFAULT_MAX_WAIT_SECONDS,
        help="Maximum total seconds to wait for a succeeded task state.",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Return after task creation instead of polling for the final image.",
    )
    parser.add_argument(
        "--preview-params",
        action="store_true",
        help="Print effective generation parameters without creating a Duomi task.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("DUOMI_API_BASE_URL", DEFAULT_BASE_URL),
        help="Duomi API base URL.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="HTTP timeout in seconds for each Duomi API request.",
    )
    return parser


def build_pending_output(task_id: str, create_response: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "state": None,
        "status": None,
        "primary_image_url": None,
        "images": None,
        "description": None,
        "query_attempts": 0,
        "elapsed_seconds": 0.0,
        "raw_create_response": create_response,
        "raw_query_response": None,
    }


def build_preview_output(args: argparse.Namespace) -> dict[str, str]:
    return resolve_generation_params(args)


def build_running_output(
    task_id: str,
    state: str,
    status: Any,
    query_attempts: int,
    elapsed_seconds: float,
    create_response: dict[str, Any] | None,
    query_response: dict[str, Any],
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "state": state,
        "status": status,
        "primary_image_url": None,
        "images": None,
        "description": None,
        "query_attempts": query_attempts,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "raw_create_response": create_response,
        "raw_query_response": query_response,
    }


def build_succeeded_output(
    task_id: str,
    create_response: dict[str, Any] | None,
    query_response: dict[str, Any],
    query_attempts: int,
    elapsed_seconds: float,
) -> dict[str, Any]:
    query_data = extract_query_data(query_response)
    result_data = extract_result_data(query_data)
    return {
        "task_id": task_id,
        "state": query_data.get("state"),
        "status": query_data.get("status"),
        "primary_image_url": primary_image_url(query_data),
        "images": result_data.get("images"),
        "description": result_data.get("description"),
        "query_attempts": query_attempts,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "raw_create_response": create_response,
        "raw_query_response": query_response,
    }


def query_task(
    base_url: str,
    headers: dict[str, str],
    task_id: str,
    timeout: int,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    query_response = request_json(
        url=f"{base_url}/api/gemini/nano-banana/{task_id}",
        method="GET",
        headers=headers,
        timeout=timeout,
    )
    query_data = extract_query_data(query_response)
    state = extract_task_state(query_data)
    return query_response, query_data, state


def wait_for_result(
    base_url: str,
    headers: dict[str, str],
    task_id: str,
    poll_interval_seconds: int,
    max_wait_seconds: int,
    timeout: int,
) -> tuple[dict[str, Any], int, float]:
    started = time.time()
    deadline = started + max_wait_seconds
    attempts = 0

    while time.time() <= deadline:
        attempts += 1
        query_response, data, state = query_task(
            base_url=base_url,
            headers=headers,
            task_id=task_id,
            timeout=timeout,
        )
        if state == "succeeded":
            return query_response, attempts, time.time() - started
        if state in TERMINAL_FAILURE_STATES:
            raise DuomiApiError(f"Duomi task failed with state={state}: {data.get('msg')}")
        if state not in RUNNING_STATES:
            raise DuomiApiError(f"Duomi query response has unexpected task state: {state}")
        time.sleep(poll_interval_seconds)

    raise DuomiApiError(f"Duomi task did not finish within {max_wait_seconds} seconds")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        args = validate_args(args)
        if args.preview_params:
            print(json.dumps(build_preview_output(args), ensure_ascii=False, indent=2))
            return 0

        token = require_env("DUOMI_API_AUTHORIZATION")
        base_url = args.base_url
        headers = build_headers(token)

        create_response = None
        task_id = args.task_id

        if task_id is None:
            payload = {
                **resolve_generation_params(args),
                "prompt": args.prompt,
                "image_urls": args.image_urls,
            }
            create_response = request_json(
                url=f"{base_url}/api/gemini/nano-banana-edit",
                method="POST",
                headers=headers,
                payload=payload,
                timeout=args.timeout,
            )
            task_id = extract_task_id(create_response)

            output = build_pending_output(task_id=task_id, create_response=create_response)
            if args.no_wait:
                print(json.dumps(output, ensure_ascii=False, indent=2))
                return 0

        if args.task_id is not None and args.no_wait:
            query_response, query_data, state = query_task(
                base_url=base_url,
                headers=headers,
                task_id=task_id,
                timeout=args.timeout,
            )
            if state == "succeeded":
                output = build_succeeded_output(
                    task_id=task_id,
                    create_response=None,
                    query_response=query_response,
                    query_attempts=1,
                    elapsed_seconds=0.0,
                )
            elif state in TERMINAL_FAILURE_STATES:
                raise DuomiApiError(f"Duomi task failed with state={state}: {query_data.get('msg')}")
            elif state in RUNNING_STATES:
                output = build_running_output(
                    task_id=task_id,
                    state=state,
                    status=query_data.get("status"),
                    query_attempts=1,
                    elapsed_seconds=0.0,
                    create_response=None,
                    query_response=query_response,
                )
            else:
                raise DuomiApiError(f"Duomi query response has unexpected task state: {state}")
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0

        query_response, attempts, elapsed = wait_for_result(
            base_url=base_url,
            headers=headers,
            task_id=task_id,
            poll_interval_seconds=args.poll_interval_seconds,
            max_wait_seconds=args.max_wait_seconds,
            timeout=args.timeout,
        )
        output = build_succeeded_output(
            task_id=task_id,
            create_response=create_response,
            query_response=query_response,
            query_attempts=attempts,
            elapsed_seconds=elapsed,
        )
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except DuomiApiError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
