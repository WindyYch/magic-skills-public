#!/usr/bin/env python3
"""Compose videos through the MagicClaw video-orchestrator task API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_TASK_API_BASE_URL = "https://clawapi-test.magiclight.ai"
DEFAULT_ENDPOINT_PATH = "/taskapi/v1/task/gen/video-orchestrator-v2"
DEFAULT_QUERY_ENDPOINT_PATH = "/taskapi/v1/task/batch/get"
DEFAULT_SOURCE = "magicclaw_compose_video"
DEFAULT_RENDERER_PROTOCOL = "video_remotion_renderer"
DEFAULT_RENDERER_PROTOCOL_VERSION = "v1"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_WAIT_TIMEOUT_SECONDS = 1800
DEFAULT_POLL_INTERVAL_SECONDS = 10
SUCCESS_BIZ_CODE = 10000
SUCCESS_STATUS = "2"
RUNNING_STATUSES = {"1", "4"}
TASK_STATUS_LABELS = {
    "1": "submitted",
    "2": "succeeded",
    "3": "failed",
    "4": "running",
}


class SubmitError(RuntimeError):
    """Raised when request assembly or submission fails."""


class TaskTerminalError(SubmitError):
    """Raised when the remote task reaches a non-success terminal state."""

    def __init__(
        self,
        message: str,
        *,
        task_id: str,
        task: dict[str, Any],
        create_response: dict[str, Any] | None,
        query_response: dict[str, Any],
        query_attempts: int,
        elapsed_seconds: float,
    ) -> None:
        super().__init__(message)
        self.task_id = task_id
        self.task = task
        self.create_response = create_response
        self.query_response = query_response
        self.query_attempts = query_attempts
        self.elapsed_seconds = elapsed_seconds


def read_json(path: Path, *, required: bool = True) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise SubmitError(f"Missing required JSON file: {path}")
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SubmitError(f"Invalid JSON file {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise SubmitError(f"JSON file must contain an object: {path}")
    return payload


def auto_trace_id() -> str:
    return f"trace-video-orchestrator-{uuid.uuid4().hex[:12]}"


def build_request_body_from_param(args: argparse.Namespace, param: dict[str, Any]) -> dict[str, Any]:
    trace_id = args.trace_id or _string_value(param.get("trace_id")) or auto_trace_id()
    param = dict(param)
    param["trace_id"] = trace_id
    validate_video_orchestrator_param(param)

    body: dict[str, Any] = {
        "source": args.source,
        "trace_id": trace_id,
        "video_orchestrator_param_json": param,
    }
    if args.biz_callback_url:
        body["biz_callback_url"] = args.biz_callback_url
    if args.biz_callback_extra_json:
        body["biz_callback_extra_json"] = parse_json_object_text(
            args.biz_callback_extra_json,
            "--biz-callback-extra-json",
        )
    return body


def build_request_body(args: argparse.Namespace) -> dict[str, Any]:
    return build_request_body_from_param(args, read_json(args.video_orchestrator_param))


def parse_json_object_text(value: str, field_name: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise SubmitError(f"{field_name} must be valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SubmitError(f"{field_name} must decode to a JSON object")
    return payload


def validate_video_orchestrator_param(param: dict[str, Any]) -> None:
    if param.get("job_kind") != "render_from_edit_assets":
        raise SubmitError("video_orchestrator_param_json.job_kind must be render_from_edit_assets")
    if not _string_value(param.get("schema_version")):
        raise SubmitError("video_orchestrator_param_json.schema_version is required")
    if not isinstance(param.get("project"), dict):
        raise SubmitError("video_orchestrator_param_json.project must be an object")

    timeline = param.get("timeline")
    if not isinstance(timeline, dict):
        raise SubmitError("video_orchestrator_param_json.timeline must be an object")
    scenes = timeline.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise SubmitError("video_orchestrator_param_json.timeline.scenes must contain at least one scene")

    assets = param.get("assets")
    if not isinstance(assets, dict):
        raise SubmitError("video_orchestrator_param_json.assets must be an object")
    items = assets.get("items")
    if not isinstance(items, list) or not items:
        raise SubmitError("video_orchestrator_param_json.assets.items must contain at least one asset")
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise SubmitError(f"video_orchestrator_param_json.assets.items[{index}] must be an object")
        if not (_string_value(item.get("asset_id")) or _string_value(item.get("id"))):
            raise SubmitError(f"video_orchestrator_param_json.assets.items[{index}] must define asset_id or id")
        if not (_string_value(item.get("asset_type")) or _string_value(item.get("type"))):
            raise SubmitError(f"video_orchestrator_param_json.assets.items[{index}] must define asset_type or type")
        if not any(_string_value(item.get(key)) for key in ("local_path", "path", "source_url", "url")):
            raise SubmitError(
                f"video_orchestrator_param_json.assets.items[{index}] must define local_path/path/source_url/url"
            )

    render_options = param.get("render_options")
    if not isinstance(render_options, dict) or not render_options:
        raise SubmitError("video_orchestrator_param_json.render_options must be a non-empty object")


def _string_value(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def build_headers() -> dict[str, str]:
    token = os.getenv("MAGICCLAW_TASK_TOKEN", "").strip()

    headers = {"Content-Type": "application/json"}
    if not token:
        return headers

    authorization = token if token.lower().startswith("bearer ") else "Bearer " + token
    headers["Authorization"] = authorization
    return headers


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted = dict(headers)
    authorization = redacted.get("Authorization")
    if isinstance(authorization, str) and authorization:
        redacted["Authorization"] = "Bearer " if authorization.strip().lower() == "bearer" else "Bearer ***"
    return redacted


def join_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.strip("/")


def count_timeline_scenes(payload: dict[str, Any] | None) -> int:
    if not isinstance(payload, dict):
        return 0
    param = payload.get("video_orchestrator_param_json")
    if not isinstance(param, dict):
        return 0
    timeline = param.get("timeline")
    if not isinstance(timeline, dict):
        return 0
    scenes = timeline.get("scenes")
    return len(scenes) if isinstance(scenes, list) else 0


def count_manifest_assets(payload: dict[str, Any] | None) -> int:
    if not isinstance(payload, dict):
        return 0
    param = payload.get("video_orchestrator_param_json")
    if not isinstance(param, dict):
        return 0
    assets = param.get("assets")
    if not isinstance(assets, dict):
        return 0
    items = assets.get("items")
    return len(items) if isinstance(items, list) else 0


def scene_token(scene_id: str) -> str:
    return scene_id.strip().upper().replace("-", "").replace("_", "")


def scene_asset_candidates(scene_id: str, asset_type: str) -> list[str]:
    token = scene_token(scene_id)
    if asset_type == "video":
        return [f"T_VID_{token}", f"VID_{token}", f"VIDEO_{token}"]
    if asset_type == "image":
        return [f"IMG_{token}", f"IMAGE_{token}", f"STILL_{token}"]
    if asset_type == "audio":
        return [f"VO_{token}", f"AUDIO_{token}", f"BGM_{token}"]
    return []


def find_scene_asset_id(scene_id: str, asset_type: str, assets: dict[str, Any]) -> str | None:
    for candidate in scene_asset_candidates(scene_id, asset_type):
        asset = assets.get(candidate)
        if isinstance(asset, dict) and (asset.get("asset_type") or asset.get("type")) == asset_type:
            return candidate

    normalized_scene_token = scene_token(scene_id)
    for asset_id, asset in assets.items():
        if not isinstance(asset, dict) or (asset.get("asset_type") or asset.get("type")) != asset_type:
            continue
        normalized_asset_id = str(asset_id).upper().replace("-", "").replace("_", "")
        if normalized_scene_token in normalized_asset_id:
            return str(asset_id)
    return None


def build_body_validation(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        return {
            "available": False,
            "reason": "task_id mode does not include a create request body",
        }

    expected_top_level = {
        "source",
        "trace_id",
        "biz_callback_url",
        "biz_callback_extra_json",
        "video_orchestrator_param_json",
    }
    required_top_level = {
        "source",
        "video_orchestrator_param_json",
    }
    param = payload.get("video_orchestrator_param_json")
    if not isinstance(param, dict):
        param = {}
    project = param.get("project")
    if not isinstance(project, dict):
        project = {}
    timeline_object = param.get("timeline")
    if not isinstance(timeline_object, dict):
        timeline_object = {}
    assets_object = param.get("assets")
    if not isinstance(assets_object, dict):
        assets_object = {}
    subtitles_object = param.get("subtitles")
    if not isinstance(subtitles_object, dict):
        subtitles_object = {}
    subtitles = subtitles_object.get("alignment")
    if not isinstance(subtitles, dict):
        subtitles = {}
    render_options = param.get("render_options")
    if not isinstance(render_options, dict):
        render_options = {}

    scenes = timeline_object.get("scenes")
    scenes = scenes if isinstance(scenes, list) else []
    asset_map = build_asset_map(assets_object.get("items"))
    fps = render_options.get("fps") or project.get("fps")

    frame_mismatches: list[dict[str, Any]] = []
    scene_asset_resolution: list[dict[str, Any]] = []
    scene_ids: list[str] = []
    orders: list[Any] = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        scene_id = str(scene.get("scene_id") or "")
        scene_ids.append(scene_id)
        orders.append(scene.get("order"))
        duration_sec = scene.get("duration_sec")
        duration_frames = scene.get("duration_frames")
        if isinstance(duration_sec, (int, float)) and isinstance(fps, int):
            expected_frames = round(float(duration_sec) * fps)
            if duration_frames != expected_frames:
                frame_mismatches.append(
                    {
                        "scene_id": scene_id,
                        "duration_sec": duration_sec,
                        "duration_frames": duration_frames,
                        "expected_frames": expected_frames,
                    }
                )

        video_strategy = scene.get("video_strategy")
        if not isinstance(video_strategy, dict):
            video_strategy = {}
        primary_source_type = str(video_strategy.get("primary_source_type") or "").lower()
        fallback_source_type = str(video_strategy.get("fallback_source_type") or "").lower()
        preferred_types = source_type_to_asset_types(primary_source_type)
        fallback_types = source_type_to_asset_types(fallback_source_type)
        visual_types = preferred_types + [item for item in fallback_types if item not in preferred_types]
        if not visual_types:
            visual_types = ["video", "image"]

        selected_visual = None
        for visual_type in visual_types:
            selected_visual = find_scene_asset_id(scene_id, visual_type, asset_map)
            if selected_visual is not None:
                break

        scene_asset_resolution.append(
            {
                "scene_id": scene_id,
                "primary_source_type": primary_source_type,
                "fallback_source_type": fallback_source_type,
                "visual_asset_types_in_order": visual_types,
                "selected_visual_asset_id": selected_visual,
                "selected_audio_asset_id": find_scene_asset_id(scene_id, "audio", asset_map),
                "subtitle_present": scene_id in subtitles,
            }
        )

    asset_type_counts: dict[str, int] = {}
    asset_url_issues: list[dict[str, Any]] = []
    for asset_id, asset in asset_map.items():
        if not isinstance(asset, dict):
            asset_url_issues.append({"asset_id": asset_id, "issue": "asset_not_object"})
            continue
        asset_type = str(asset.get("asset_type") or asset.get("type") or "")
        asset_type_counts[asset_type] = asset_type_counts.get(asset_type, 0) + 1
        url = asset.get("source_url") or asset.get("url") or asset.get("local_path") or asset.get("path")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            asset_url_issues.append({"asset_id": asset_id, "url": url})

    subtitle_scene_ids = set(subtitles.keys())
    scene_id_set = set(scene_ids)
    return {
        "available": True,
        "top_level": {
            "required_present": sorted(required_top_level.intersection(payload.keys())),
            "required_missing": sorted(required_top_level.difference(payload.keys())),
            "optional_present": sorted(
                set(payload.keys()).intersection(expected_top_level.difference(required_top_level))
            ),
            "unexpected_keys": sorted(set(payload.keys()).difference(expected_top_level)),
        },
        "protocol": {
            "source_expected": payload.get("source") == DEFAULT_SOURCE,
            "job_kind_expected": param.get("job_kind") == "render_from_edit_assets",
            "input_protocol_expected": param.get("input_protocol") == DEFAULT_RENDERER_PROTOCOL,
            "input_protocol_version_expected": param.get("input_protocol_version")
            == DEFAULT_RENDERER_PROTOCOL_VERSION,
        },
        "timeline": {
            "scene_count": len(scene_ids),
            "scene_ids": scene_ids,
            "orders": orders,
            "orders_sequential": orders == list(range(1, len(scene_ids) + 1)),
            "fps": fps,
            "frame_mismatches": frame_mismatches,
            "total_duration_sec": sum(
                scene.get("duration_sec", 0) for scene in scenes if isinstance(scene, dict)
            ),
            "total_duration_frames": sum(
                scene.get("duration_frames", 0) for scene in scenes if isinstance(scene, dict)
            ),
        },
        "assets": {
            "asset_count": len(asset_map),
            "asset_type_counts": asset_type_counts,
            "url_issues": asset_url_issues,
            "scene_asset_resolution": scene_asset_resolution,
            "missing_visual_scene_ids": [
                row["scene_id"] for row in scene_asset_resolution if row["selected_visual_asset_id"] is None
            ],
            "missing_audio_scene_ids": [
                row["scene_id"] for row in scene_asset_resolution if row["selected_audio_asset_id"] is None
            ],
        },
        "subtitles": {
            "subtitle_count": len(subtitles),
            "missing_scene_ids": sorted(scene_id_set.difference(subtitle_scene_ids)),
            "extra_scene_ids": sorted(subtitle_scene_ids.difference(scene_id_set)),
        },
        "render_options": {
            "output_format": render_options.get("output_format"),
            "fps": render_options.get("fps"),
            "resolution": render_options.get("resolution"),
            "cover": render_options.get("cover"),
            "watermark": render_options.get("watermark"),
        },
    }


def build_asset_map(items: Any) -> dict[str, Any]:
    if not isinstance(items, list):
        return {}

    asset_map: dict[str, Any] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        asset_id = _string_value(item.get("asset_id")) or _string_value(item.get("id"))
        if asset_id:
            asset_map[asset_id] = item
    return asset_map


def _dict_value(payload: dict[str, Any], key: str, nested_key: str) -> Any:
    nested = payload.get(key)
    if not isinstance(nested, dict):
        return None
    return nested.get(nested_key)


def source_type_to_asset_types(raw_source_type: str) -> list[str]:
    if raw_source_type == "generated_video":
        return ["video"]
    if raw_source_type == "generated_image":
        return ["image"]
    return []


def build_dry_run_output(args: argparse.Namespace, payload: dict[str, Any] | None) -> dict[str, Any]:
    base_url = args.base_url or args.task_api_base_url
    headers = redact_headers(build_headers())
    create_url = join_url(base_url, args.endpoint_path)
    query_url = join_url(base_url, args.query_endpoint_path)
    query_body = {"task_ids": [args.task_id or "<created_task_id>"]}

    output: dict[str, Any] = {
        "mode": "dry_run",
        "network": False,
        "summary": {
            "base_url": base_url,
            "create_endpoint_path": args.endpoint_path,
            "query_endpoint_path": args.query_endpoint_path,
            "task_id": args.task_id,
            "will_create_task": args.task_id is None,
            "will_query_task": args.task_id is not None or not args.no_wait,
            "will_poll_until_success": not args.no_wait,
            "poll_interval_seconds": args.poll_interval_seconds,
            "max_wait_seconds": args.max_wait_seconds,
            "timeout_seconds": args.timeout,
            "trace_id": payload.get("trace_id") if isinstance(payload, dict) else None,
            "timeline_scene_count": count_timeline_scenes(payload),
            "manifest_asset_count": count_manifest_assets(payload),
        },
        "body_validation": build_body_validation(payload),
        "create_request": None,
        "query_request": None,
    }

    if payload is not None:
        output["create_request"] = {
            "method": "POST",
            "url": create_url,
            "headers": headers,
            "timeout_seconds": args.timeout,
            "body": payload,
        }

    if args.task_id is not None or not args.no_wait:
        output["query_request"] = {
            "method": "POST",
            "url": query_url,
            "headers": headers,
            "timeout_seconds": args.timeout,
            "body": query_body,
        }

    return output


def request_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=body, headers=build_headers(), method="POST")

    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise SubmitError(f"HTTP {exc.code} from mc-task-api: {response_body}") from exc
    except URLError as exc:
        raise SubmitError(f"Failed to reach mc-task-api: {exc.reason}") from exc

    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise SubmitError(f"mc-task-api returned invalid JSON: {response_body}") from exc

    if not isinstance(parsed, dict):
        raise SubmitError("mc-task-api response is not a JSON object")
    return parsed


def extract_data(response: dict[str, Any], context: str) -> dict[str, Any]:
    if response.get("biz_code") != SUCCESS_BIZ_CODE:
        raise SubmitError(
            f"mc-task-api {context} request failed with biz_code={response.get('biz_code')}: {response.get('msg')}"
        )
    data = response.get("data")
    if not isinstance(data, dict):
        raise SubmitError(f"mc-task-api {context} response is missing a data object")
    return data


def extract_task_id(response: dict[str, Any]) -> str:
    data = extract_data(response, "create")
    task_id = data.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise SubmitError("mc-task-api create response is missing task_id")
    return task_id.strip()


def extract_tasks(response: dict[str, Any]) -> list[dict[str, Any]]:
    data = extract_data(response, "query")
    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise SubmitError("mc-task-api query response is missing tasks")

    normalized: list[dict[str, Any]] = []
    for task in tasks:
        if isinstance(task, dict):
            normalized.append(task)
    return normalized


def query_task(
    base_url: str,
    endpoint_path: str,
    task_id: str,
    timeout: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    url = join_url(base_url, endpoint_path)
    response = request_json(url, {"task_ids": [task_id]}, timeout)
    tasks = extract_tasks(response)
    for task in tasks:
        if task.get("task_id") == task_id:
            return response, task
    raise SubmitError(f"mc-task-api query response does not contain task_id={task_id}")


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


def coerce_status_code(status: Any) -> int | None:
    normalized = coerce_status(status)
    if normalized is None:
        return None
    try:
        return int(normalized)
    except ValueError:
        return None


def status_label(status: Any) -> str:
    normalized = coerce_status(status)
    if normalized is None:
        return "unknown"
    return TASK_STATUS_LABELS.get(normalized, normalized)


def is_success_status(status: Any) -> bool:
    return coerce_status(status) == SUCCESS_STATUS


def is_running_status(status: Any) -> bool:
    return coerce_status(status) in RUNNING_STATUSES


def extract_result_url(task_result: Any) -> str | None:
    if not isinstance(task_result, dict):
        return None

    for key in ("result_url", "video_url", "url", "vendor_url"):
        value = task_result.get(key)
        if isinstance(value, str) and value:
            return value

    result_payload = task_result.get("result_payload")
    if isinstance(result_payload, dict):
        for key in ("result_url", "video_url", "url", "vendor_url"):
            value = result_payload.get(key)
            if isinstance(value, str) and value:
                return value

        items = result_payload.get("items")
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict):
                for key in ("result_url", "video_url", "url", "vendor_url"):
                    value = first.get(key)
                    if isinstance(value, str) and value:
                        return value
    return None


def extract_source_url(task: dict[str, Any], task_result: Any) -> str | None:
    source_url = task.get("source_url")
    if isinstance(source_url, str) and source_url:
        return source_url
    return extract_result_url(task_result)


def build_pending_output(task_id: str, create_response: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "mode": "submit_only",
        "task_id": task_id,
        "status": "submitted",
        "status_code": 1,
        "video_url": None,
        "source_url": None,
        "trace_id": create_response.get("trace_id"),
        "elapsed_seconds": 0.0,
        "query_attempts": 0,
        "error": None,
        "debug": {
            "task_type": None,
            "model_type": None,
            "source": None,
            "input_params": None,
            "input_params_raw": None,
            "task_result": None,
            "task_result_raw": None,
            "raw_create_response": create_response,
            "raw_query_response": None,
        },
    }


def build_task_output(
    task_id: str,
    task: dict[str, Any],
    create_response: dict[str, Any] | None,
    query_response: dict[str, Any],
    query_attempts: int,
    elapsed_seconds: float,
    *,
    mode: str,
) -> dict[str, Any]:
    input_params_raw = task.get("input_params")
    task_result_raw = task.get("task_result")
    input_params = parse_json_text(input_params_raw)
    task_result = parse_json_text(task_result_raw)
    raw_status = task.get("status")
    source_url = extract_source_url(task, task_result)
    failed = not is_success_status(raw_status) and not is_running_status(raw_status)

    return {
        "ok": not failed,
        "mode": mode,
        "task_id": task_id,
        "status": status_label(raw_status),
        "status_code": coerce_status_code(raw_status),
        "video_url": source_url if not failed else None,
        "source_url": source_url if not failed else None,
        "trace_id": query_response.get("trace_id") or (create_response or {}).get("trace_id"),
        "elapsed_seconds": round(elapsed_seconds, 2),
        "query_attempts": query_attempts,
        "error": (
            {
                "type": "TaskFailed",
                "message": f"mc-task-api task failed with status={raw_status}",
            }
            if failed
            else None
        ),
        "debug": {
            "task_type": task.get("task_type"),
            "model_type": task.get("model_type"),
            "source": task.get("source"),
            "input_params": input_params,
            "input_params_raw": input_params_raw,
            "task_result": task_result,
            "task_result_raw": task_result_raw,
            "raw_create_response": create_response,
            "raw_query_response": query_response,
        },
    }


def wait_for_task(
    *,
    base_url: str,
    query_endpoint_path: str,
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
        query_response, task = query_task(
            base_url,
            query_endpoint_path,
            task_id,
            timeout,
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
                mode="submit_and_wait" if create_response is not None else "query",
            )

        if not is_running_status(status):
            raise TaskTerminalError(
                f"mc-task-api task failed with status={status}: {task.get('task_result')}",
                task_id=task_id,
                task=task,
                create_response=create_response,
                query_response=query_response,
                query_attempts=attempts,
                elapsed_seconds=time.time() - started,
            )

        time.sleep(poll_interval_seconds)

    raise SubmitError(f"mc-task-api task did not finish within {max_wait_seconds} seconds")


def run_video_orchestrator_task(
    *,
    base_url: str,
    create_endpoint_path: str,
    query_endpoint_path: str,
    payload: dict[str, Any] | None,
    task_id: str | None,
    no_wait: bool,
    poll_interval_seconds: int,
    max_wait_seconds: int,
    timeout: int,
) -> dict[str, Any]:
    if timeout <= 0:
        raise SubmitError("--timeout must be greater than 0")
    if poll_interval_seconds < 0:
        raise SubmitError("--poll-interval-seconds must be greater than or equal to 0")
    if max_wait_seconds < 0:
        raise SubmitError("--max-wait-seconds must be greater than or equal to 0")
    if task_id is None and payload is None:
        raise SubmitError("payload is required when task_id is not provided")

    create_response = None
    resolved_task_id = task_id

    if resolved_task_id is None:
        create_response = request_json(
            join_url(base_url, create_endpoint_path),
            payload or {},
            timeout,
        )
        resolved_task_id = extract_task_id(create_response)
        if no_wait:
            return build_pending_output(resolved_task_id, create_response)

    if no_wait:
        query_response, task = query_task(base_url, query_endpoint_path, resolved_task_id, timeout)
        return build_task_output(
            task_id=resolved_task_id,
            task=task,
            create_response=create_response,
            query_response=query_response,
            query_attempts=1,
            elapsed_seconds=0.0,
            mode="query",
        )

    return wait_for_task(
        base_url=base_url,
        query_endpoint_path=query_endpoint_path,
        task_id=resolved_task_id,
        create_response=create_response,
        poll_interval_seconds=poll_interval_seconds,
        max_wait_seconds=max_wait_seconds,
        timeout=timeout,
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compose a complete video through MagicClaw's video-orchestrator task API.",
    )
    parser.add_argument("--task-id", help="Existing video-orchestrator task ID to query.")
    parser.add_argument(
        "--video-orchestrator-param",
        type=Path,
        help="Canonical video-orchestrator param JSON file prepared by the caller.",
    )
    parser.add_argument(
        "--trace-id",
        help=(
            "Optional trace ID. When provided, the caller must ensure it is unique. "
            "Auto-generated when omitted."
        ),
    )
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Request source.")
    parser.add_argument("--biz-callback-url", help="Optional business callback URL.")
    parser.add_argument("--biz-callback-extra-json", help="Optional business callback extra JSON object.")
    parser.add_argument(
        "--task-api-base-url",
        default=os.getenv("MAGICCLAW_TASK_API_BASE_URL", DEFAULT_TASK_API_BASE_URL),
        help="mc-task-api base URL.",
    )
    parser.add_argument("--base-url", help="Alias for --task-api-base-url.")
    parser.add_argument("--endpoint-path", default=DEFAULT_ENDPOINT_PATH)
    parser.add_argument("--query-endpoint-path", default=DEFAULT_QUERY_ENDPOINT_PATH)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Return immediately after creation instead of polling until success.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Compatibility alias. Polling is already enabled by default.",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=DEFAULT_WAIT_TIMEOUT_SECONDS,
        help="Maximum total seconds to wait for task completion.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Seconds between status queries when --wait is enabled.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print final HTTP request information without submitting.")
    parser.add_argument("--preview", action="store_true", help="Print request body without submitting.")
    parser.add_argument("--output-request", type=Path, help="Write assembled request body to a file.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if not args.task_id and args.video_orchestrator_param is None:
            raise SubmitError("--video-orchestrator-param is required when --task-id is not provided")

        payload = None if args.task_id else build_request_body(args)
        if args.output_request and payload is not None:
            write_json(args.output_request, payload)

        if args.preview:
            print(json.dumps(payload or {}, ensure_ascii=False, indent=2))
            return 0

        if args.dry_run:
            print(json.dumps(build_dry_run_output(args, payload), ensure_ascii=False, indent=2))
            return 0

        result = run_video_orchestrator_task(
            base_url=args.base_url or args.task_api_base_url,
            create_endpoint_path=args.endpoint_path,
            query_endpoint_path=args.query_endpoint_path,
            payload=payload,
            task_id=args.task_id,
            no_wait=args.no_wait,
            poll_interval_seconds=args.poll_interval_seconds,
            max_wait_seconds=args.max_wait_seconds,
            timeout=args.timeout,
        )
        output_stream = sys.stdout if result.get("ok") else sys.stderr
        print(json.dumps(result, ensure_ascii=False, indent=2), file=output_stream)
        return 0 if result.get("ok") else 1
    except TaskTerminalError as exc:
        result = build_task_output(
            task_id=exc.task_id,
            task=exc.task,
            create_response=exc.create_response,
            query_response=exc.query_response,
            query_attempts=exc.query_attempts,
            elapsed_seconds=exc.elapsed_seconds,
            mode="submit_and_wait" if exc.create_response is not None else "query",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    except SubmitError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "mode": "unknown",
                    "task_id": None,
                    "status": "failed",
                    "status_code": None,
                    "video_url": None,
                    "source_url": None,
                    "trace_id": None,
                    "elapsed_seconds": 0.0,
                    "query_attempts": 0,
                    "error": {
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                    },
                    "debug": {},
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
