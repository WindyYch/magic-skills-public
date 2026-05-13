---
name: magicclaw-generate-img
description: Use when a user wants MagicClaw image generation through the async task API, defaulting to task creation and later status querying by task ID.
required_environment_variables:
  - name: MagicClawDomain
    prompt: MagicClaw API domain or base URL
    required_for: MagicClaw image generation
  - name: MagicClawAuthorization
    prompt: MagicClaw Authorization header value
    required_for: MagicClaw image generation
---

# MagicClaw Generate Img

## Overview

Use this skill to submit MagicClaw image generation tasks to `/taskapi/v1/task/gen/img`. By default, the script returns immediately with a provider `task_id`; pass `--wait` only when you explicitly need to poll `/taskapi/v1/task/batch/get` until the final asset URL is ready.

The script accepts `MagicClawDomain` and `MagicClawAuthorization`. It also accepts uppercase aliases `MAGIC_CLAW_DOMAIN` and `MAGIC_CLAW_AUTHORIZATION`.

## When To Use

- The user wants text-to-image generation through the MagicClaw task API
- The request should return a `task_id` immediately or poll to a final image result
- The workflow needs a stable CLI instead of hand-written `curl`

Do not use this skill for multi-image composition. Use `magicclaw-imgs-to-img` for `img_list` workflows.

## Workflow

1. Confirm `MagicClawDomain` and `MagicClawAuthorization` exist.
2. Collect `prompt` and any optional reference `image` URLs.
3. Run the script.
4. By default, return immediately after task creation and persist the returned provider `task_id`.
5. Return only the minimal task result fields needed by downstream orchestration.

Always use the script. Do not handcraft MagicClaw request payloads in the model response unless the user explicitly asks for raw examples.

## Commands

Submit an image task and return `task_id`:

```bash
python3 "$SKILL_DIR/scripts/generate_image.py" \
  --prompt "阳光下的神圣天使，电影感，超细节"
```

Generate with reference images:

```bash
python3 "$SKILL_DIR/scripts/generate_image.py" \
  --prompt "保持人物身份一致，背景改成圣洁的云海" \
  --image-url "https://example.com/ref-1.png" \
  --image-url "https://example.com/ref-2.png"
```

Generate an image and wait for completion:

```bash
python3 "$SKILL_DIR/scripts/generate_image.py" \
  --prompt "阳光下的神圣天使，电影感，超细节" \
  --wait
```

Query an existing task once:

```bash
python3 "$SKILL_DIR/scripts/generate_image.py" \
  --task-id "019e0cf7-edef-711f-a0c2-12748224d9e8"
```

## Inputs

- Required for create:
  - `--prompt`
- Optional:
  - `--image-url`
  - `--model`
  - `--model-type`
  - `--quality`
  - `--size`
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

- Forgetting `MagicClawAuthorization`: every request requires the `Authorization` header
- Using this skill for `img_list` composition: route that to `magicclaw-imgs-to-img`
- Forgetting `--wait` when the user explicitly needs the final image URL in the same command
