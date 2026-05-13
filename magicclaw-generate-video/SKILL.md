---
name: magicclaw-generate-video
description: Use when a user wants MagicClaw video generation through the async task API, defaulting to task creation and later status querying by task ID.
required_environment_variables:
  - name: MagicClawDomain
    prompt: MagicClaw API domain or base URL
    required_for: MagicClaw video generation
  - name: MagicClawAuthorization
    prompt: MagicClaw Authorization header value
    required_for: MagicClaw video generation
---

# MagicClaw Generate Video

## Overview

Use this skill to submit MagicClaw video tasks to `/taskapi/v1/task/gen/video`. By default, the script returns immediately with a provider `task_id`; pass `--wait` only when you explicitly need to poll `/taskapi/v1/task/batch/get` until the final video URL is ready.

The script supports both documented payload shapes:

- `bytedance_seedance`
- `duomi_kling`

The script accepts `MagicClawDomain` and `MagicClawAuthorization`. It also accepts uppercase aliases `MAGIC_CLAW_DOMAIN` and `MAGIC_CLAW_AUTHORIZATION`.

## When To Use

- The user wants MagicClaw video generation
- The request should use either the `bytedance_seedance` or `duomi_kling` payload shape
- The workflow needs a provider task ID that can be queried later for final clip status

Do not use this skill for still image generation.

## Workflow

1. Confirm `MagicClawDomain` and `MagicClawAuthorization` exist.
2. Choose the right `model_type`.
3. Collect the required inputs for that mode.
4. Run the script.
5. By default, return immediately after task creation and persist the returned provider `task_id`.
6. Return only the minimal task result fields needed by downstream orchestration.

## Commands

Generate a `bytedance_seedance` video:

```bash
python3 "$SKILL_DIR/scripts/generate_video.py" \
  --model-type bytedance_seedance \
  --image-url "https://example.com/ref-1.png" \
  --image-url "https://example.com/ref-2.png" \
  --text "画面中的天使和魔鬼慢慢注视着对方" \
  --ratio "16:9" \
  --duration 12 \
  --resolution "1080p" \
  --fps 24 \
  --generate-audio true \
  --seed 123456 \
  --watermark false
```

Generate a `duomi_kling` video:

```bash
python3 "$SKILL_DIR/scripts/generate_video.py" \
  --model-type duomi_kling \
  --img-url "https://example.com/ref.png" \
  --prompt "女鬼慢慢蜕化，最后变成女神"
```

Query an existing task once:

```bash
python3 "$SKILL_DIR/scripts/generate_video.py" \
  --task-id "019e1529-1f7d-7c13-9bbf-156e49961c64"
```

## Inputs

- Required for create:
  - `--model-type`
- Required for `bytedance_seedance`:
  - one or more `--image-url`
  - `--text`
- Required for `duomi_kling`:
  - `--img-url`
  - `--prompt`
- Optional:
  - `--model`
  - `--duration`
  - `--mode`
  - `--source`
  - `--no-wait`
  - `--wait`
  - `--poll-interval-seconds`
  - `--max-wait-seconds`
  - `--base-url`
  - `--timeout`
- Additional optional fields for `bytedance_seedance`:
  - `--ratio`
  - `--duration`
  - `--resolution`
  - `--fps`
  - `--generate-audio`: `true` or `false`
  - `--seed`
  - `--watermark`: `true` or `false`
  - These optional Seedance fields are passed through directly to the request payload and are not range-validated locally by this skill
- Existing-task mode:
  - `--task-id`

## Output

The script prints JSON with:

- `task_id`
- `status`
- `video_url`
- `source_url`
- `query_attempts`
- `elapsed_seconds`
- `trace_id`

Do not depend on provider raw responses, `input_params`, or `task_result` in this skill's stdout. The script may parse provider internals to extract `source_url`, but it intentionally emits only the minimal stable contract.

## Common Mistakes

- Mixing `bytedance_seedance` and `duomi_kling` fields in the same request
- Forgetting `--text` for `bytedance_seedance`
- Forgetting `--img-url` or `--prompt` for `duomi_kling`
