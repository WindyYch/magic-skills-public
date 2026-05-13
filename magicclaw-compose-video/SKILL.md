---
name: magicclaw-compose-video
description: Use when a user wants to compose a complete video through MagicClaw's video-orchestrator task API, submit canonical video-orchestrator param JSON to mc-task-api, poll by task_id, or resume querying a video composition task for the final video_url.
required_environment_variables:
  - name: MAGICCLAW_TASK_API_BASE_URL
    prompt: Optional mc-task-api base URL
    required_for: Local or non-default MagicClaw task API environments
  - name: MAGICCLAW_TASK_TOKEN
    prompt: Optional mc-task-api Authorization token
    required_for: Auth-enabled MagicClaw task API environments
---

# MagicClaw Compose Video

## Overview

Use this skill to submit complete video composition jobs to MagicClaw's `video-orchestrator` through `mc-task-api`.

The skill accepts a canonical `video-orchestrator` param JSON object, creates a task through `/taskapi/v1/task/gen/video-orchestrator-v2`, and either returns immediately with a `task_id` or polls `/taskapi/v1/task/batch/get` until the final `video_url` is available.

This is a cloud task skill. Do not use it for local Remotion rendering; use `video-remotion-renderer` for `render-input.json`, `render-report.json`, and local `final.mp4` workflows.

## When To Use

- The user wants a complete video composed from project files.
- The workflow needs a stable task API result with `task_id`, `status`, and `video_url`.
- The user has an existing video composition `task_id` and wants to query or resume polling it.
- The request explicitly mentions `video-orchestrator`, cloud video composition, or submitting render work to `mc-task-api`.

## Inputs

Create mode requires:

- `--video-orchestrator-param`: path to a JSON object that is already in the `video-orchestrator` canonical input format.

Create mode optionally uses:

- `--trace-id`: optional trace ID. If provided, it overwrites `video_orchestrator_param_json.trace_id`. If omitted, the script uses the param file trace ID or auto-generates one.
- `--source`: upstream source, default `magicclaw_compose_video`.
- `--biz-callback-url`: optional business callback URL.
- `--biz-callback-extra-json`: optional JSON object forwarded as business callback extra.

Query mode requires:

- `--task-id`

Environment:

- `MAGICCLAW_TASK_API_BASE_URL`: defaults to `https://clawapi-test.magiclight.ai`.
- `MAGICCLAW_TASK_TOKEN`: sent as `Authorization: Bearer <token>` unless it already starts with `Bearer `.

## Commands

Preview the assembled request body without network:

```bash
python3 "$SKILL_DIR/scripts/compose_video.py" \
  --video-orchestrator-param /path/to/video-orchestrator-param.json \
  --preview
```

Dry-run the HTTP request and polling shape without network:

```bash
python3 "$SKILL_DIR/scripts/compose_video.py" \
  --video-orchestrator-param /path/to/video-orchestrator-param.json \
  --dry-run
```

Submit and wait for the final video:

```bash
MAGICCLAW_TASK_TOKEN="<token>" \
python3 "$SKILL_DIR/scripts/compose_video.py" \
  --video-orchestrator-param /path/to/video-orchestrator-param.json \
  --trace-id trace-demo-001
```

Submit only and return a `task_id`:

```bash
MAGICCLAW_TASK_TOKEN="<token>" \
python3 "$SKILL_DIR/scripts/compose_video.py" \
  --video-orchestrator-param /path/to/video-orchestrator-param.json \
  --trace-id trace-demo-001 \
  --no-wait
```

Query an existing task once:

```bash
MAGICCLAW_TASK_TOKEN="<token>" \
python3 "$SKILL_DIR/scripts/compose_video.py" \
  --task-id "019e1529-1f7d-7c13-9bbf-156e49961c64" \
  --no-wait
```

Poll an existing task until success or failure:

```bash
MAGICCLAW_TASK_TOKEN="<token>" \
python3 "$SKILL_DIR/scripts/compose_video.py" \
  --task-id "019e1529-1f7d-7c13-9bbf-156e49961c64"
```

## Output

The script prints one JSON object. Stable top-level fields:

- `ok`: boolean success flag for the command.
- `mode`: `submit_and_wait`, `submit_only`, `query`, or `unknown`.
- `task_id`: task platform ID.
- `status`: semantic status such as `submitted`, `running`, `succeeded`, or `failed`.
- `status_code`: task platform numeric status when available.
- `video_url`: final video URL when available.
- `source_url`: source result URL when available.
- `trace_id`
- `elapsed_seconds`
- `query_attempts`
- `error`: `null` on success, otherwise an object with `type` and `message`.
- `debug`: raw API responses and diagnostic fields for troubleshooting.

Do not depend on fields inside `debug` for normal orchestration.

For detailed request and output examples, read `references/video-orchestrator-task-api.md`.
