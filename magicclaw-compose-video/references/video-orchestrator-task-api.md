# Video Orchestrator Task API

Use this reference when composing a complete video through `mc-task-api` and the `video-orchestrator` execution layer.

## Endpoints

Create:

```text
POST /taskapi/v1/task/gen/video-orchestrator-v2
```

Query:

```text
POST /taskapi/v1/task/batch/get
```

Default base URL:

```text
https://clawapi-test.magiclight.ai
```

Override with:

```text
MAGICCLAW_TASK_API_BASE_URL
```

## Authentication

The script reads:

```text
MAGICCLAW_TASK_TOKEN
```

It sends:

```text
Authorization: Bearer <token>
Content-Type: application/json
X-Trace-Id: <video_orchestrator_param_json.trace_id>
```

If `MAGICCLAW_TASK_TOKEN` already starts with `Bearer `, the value is used as-is.
For create requests, `X-Trace-Id` is always the same value as `video_orchestrator_param_json.trace_id`.

## Create Request Body

The script reads a canonical param object from `--video-orchestrator-param` and submits:

```json
{
  "source": "magicclaw_compose_video",
  "biz_callback_url": "https://example.com/callback",
  "biz_callback_extra_json": {
    "request_id": "req-123"
  },
  "video_orchestrator_param_json": {
    "job_kind": "render_from_edit_assets",
    "schema_version": "v1",
    "trace_id": "trace-...",
    "input_protocol": "video_remotion_renderer",
    "input_protocol_version": "v1",
    "project": {},
    "timeline": {
      "scenes": [
        {
          "scene_id": "S_01",
          "duration_sec": 2.5
        }
      ]
    },
    "assets": {
      "items": [
        {
          "asset_id": "IMG_S01",
          "asset_type": "image",
          "source_url": "https://example.com/image.png"
        }
      ]
    },
    "subtitles": {
      "alignment": {}
    },
    "render_options": {
      "output_format": "mp4",
      "fps": 25,
      "resolution": {
        "width": 1920,
        "height": 1080
      }
    }
  }
}
```

Trace ID:

- `--trace-id` is optional.
- If `--trace-id` is provided, the caller must ensure the value is unique.
- If omitted, the script uses `video_orchestrator_param_json.trace_id`.
- If both are omitted, the script auto-generates one as `trace-video-orchestrator-{12-char uuid}`.
- The resolved trace ID is written only to `video_orchestrator_param_json.trace_id` in the request body and to the HTTP `X-Trace-Id` header.

Canonical param requirements:

- `job_kind`: must be `render_from_edit_assets`.
- `schema_version`: required non-empty string.
- `project`: required JSON object.
- `timeline.scenes`: required non-empty array.
- `assets.items`: required non-empty array. Each item must define `asset_id` or `id`, `asset_type` or `type`, and one of `local_path`, `path`, `source_url`, or `url`.
- `render_options`: required non-empty JSON object.

## Output Contract

The script prints exactly one JSON object to stdout on success and stderr on failure.

Stable top-level fields:

```json
{
  "ok": true,
  "mode": "submit_and_wait",
  "task_id": "019e1529-1f7d-7c13-9bbf-156e49961c64",
  "status": "succeeded",
  "status_code": 2,
  "video_url": "https://example.com/final.mp4",
  "source_url": "https://example.com/final.mp4",
  "trace_id": "trace-demo-001",
  "elapsed_seconds": 123.45,
  "query_attempts": 13,
  "error": null,
  "debug": {}
}
```

`debug` contains raw API responses, `task_result`, `input_params`, and other diagnostic values. Normal orchestration should rely on the stable top-level fields instead.

## Status Values

Semantic status:

- `submitted`
- `running`
- `succeeded`
- `failed`
- `unknown`

Task platform status codes:

- `1`: submitted
- `2`: succeeded
- `3`: failed
- `4`: running

## Examples

Submit and wait:

```bash
MAGICCLAW_TASK_TOKEN="<token>" \
python3 "$SKILL_DIR/scripts/compose_video.py" \
  --video-orchestrator-param /path/to/video-orchestrator-param.json \
  --trace-id trace-demo-001
```

Submit only:

```bash
MAGICCLAW_TASK_TOKEN="<token>" \
python3 "$SKILL_DIR/scripts/compose_video.py" \
  --video-orchestrator-param /path/to/video-orchestrator-param.json \
  --trace-id trace-demo-001 \
  --no-wait
```

Query once:

```bash
MAGICCLAW_TASK_TOKEN="<token>" \
python3 "$SKILL_DIR/scripts/compose_video.py" \
  --task-id "019e1529-1f7d-7c13-9bbf-156e49961c64" \
  --no-wait
```

Resume polling:

```bash
MAGICCLAW_TASK_TOKEN="<token>" \
python3 "$SKILL_DIR/scripts/compose_video.py" \
  --task-id "019e1529-1f7d-7c13-9bbf-156e49961c64"
```

Preview request body:

```bash
python3 "$SKILL_DIR/scripts/compose_video.py" \
  --video-orchestrator-param /path/to/video-orchestrator-param.json \
  --preview
```

Dry run:

```bash
python3 "$SKILL_DIR/scripts/compose_video.py" \
  --video-orchestrator-param /path/to/video-orchestrator-param.json \
  --dry-run
```
