---
name: magicclaw-imgs-to-img
description: Use when a user wants MagicClaw multi-image composition through the async task API, defaulting to task creation and later status querying by task ID.
required_environment_variables:
  - name: MagicClawDomain
    prompt: MagicClaw API domain or base URL
    required_for: MagicClaw multi-image composition
  - name: MagicClawAuthorization
    prompt: MagicClaw Authorization header value
    required_for: MagicClaw multi-image composition
---

# MagicClaw Imgs To Img

## Overview

Use this skill to submit MagicClaw image composition tasks to `/taskapi/v1/task/gen/img` with `model_type=minimax_imgs2img`. By default, the script returns immediately with a provider `task_id`; pass `--wait` only when you explicitly need to poll `/taskapi/v1/task/batch/get` until the final image URL is ready.

The script accepts `MagicClawDomain` and `MagicClawAuthorization`. It also accepts uppercase aliases `MAGIC_CLAW_DOMAIN` and `MAGIC_CLAW_AUTHORIZATION`.

## When To Use

- The user wants to combine multiple images into one generated image
- The request should send `img_list` plus a composition prompt
- The workflow should return a stable JSON result instead of a manual `curl` transcript

Do not use this skill for plain text-to-image generation. Use `magicclaw-generate-img` for that.

## Workflow

1. Confirm `MagicClawDomain` and `MagicClawAuthorization` exist.
2. Collect `prompt` and one or more `image` URLs.
3. Run the script.
4. By default, return immediately after task creation and persist the returned provider `task_id`.
5. Return only the minimal task result fields needed by downstream orchestration.

## Commands

Submit a multi-image composition task and return `task_id`:

```bash
python3 "$SKILL_DIR/scripts/imgs_to_img.py" \
  --prompt "天使与女鬼手牵着手，气氛神圣而诡异" \
  --image-url "https://example.com/ref-1.png" \
  --image-url "https://example.com/ref-2.png"
```

Compose multiple images and wait for completion:

```bash
python3 "$SKILL_DIR/scripts/imgs_to_img.py" \
  --prompt "天使与女鬼手牵着手，气氛神圣而诡异" \
  --image-url "https://example.com/ref-1.png" \
  --image-url "https://example.com/ref-2.png" \
  --wait
```

Query an existing task once:

```bash
python3 "$SKILL_DIR/scripts/imgs_to_img.py" \
  --task-id "019e109a-1a03-7f24-b7fe-921a86702470"
```

## Inputs

- Required for create:
  - `--prompt`
  - one or more `--image-url`
- Optional:
  - `--model`
  - `--model-type`
  - `--aspect-ratio`
  - `--image-size`
  - `--source`
  - `--no-wait`
  - `--wait`
  - `--poll-interval-seconds`
  - `--max-wait-seconds`
  - `--base-url`
  - `--timeout`
- Existing-task mode:
  - `--task-id`

## Output

The script prints JSON with:

- `task_id`
- `status`
- `primary_image_url`
- `source_url`
- `query_attempts`
- `elapsed_seconds`
- `trace_id`

Do not depend on provider raw responses, `input_params`, or `task_result` in this skill's stdout. The script may parse provider internals to extract `source_url`, but it intentionally emits only the minimal stable contract.

## Common Mistakes

- Forgetting to pass at least one `--image-url`
- Using `image` instead of `img_list` semantics for this workflow
- Using this skill for a plain text-only image request
