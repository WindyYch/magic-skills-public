---
name: magicclaw-generate-music
description: Use when a user wants MagicClaw music generation through the async task API, defaulting to task creation and later status querying by task ID.
required_environment_variables:
  - name: MagicClawDomain
    prompt: MagicClaw API domain or base URL
    required_for: MagicClaw music generation
  - name: MagicClawAuthorization
    prompt: MagicClaw Authorization header value
    required_for: MagicClaw music generation
---

# MagicClaw Generate Music

## Overview

Use this skill to submit MagicClaw music tasks to `/taskapi/v1/task/gen/music`. By default, the script returns immediately with a provider `task_id`; pass `--wait` only when you explicitly need to poll `/taskapi/v1/task/batch/get` until the final audio URL is ready.

The script accepts `MagicClawDomain` and `MagicClawAuthorization`. It also accepts uppercase aliases `MAGIC_CLAW_DOMAIN` and `MAGIC_CLAW_AUTHORIZATION`.

## When To Use

- The user wants music generation through the MagicClaw task API
- The request should send lyrics or prompt text plus `title` and `style`
- The workflow should return a stable provider task ID first, then query final music status later

Do not use this skill for speech synthesis.

## Workflow

1. Confirm `MagicClawDomain` and `MagicClawAuthorization` exist.
2. Collect `prompt`, `title`, and `style`.
3. Run the script.
4. By default, return immediately after task creation and persist the returned provider `task_id`.
5. Return only the minimal task result fields needed by downstream orchestration.

## Commands

Submit music and return `task_id`:

```bash
python3 "$SKILL_DIR/scripts/generate_music.py" \
  --title "Chasing Stars" \
  --style "pop, inspirational, female vocal" \
  --prompt "[Verse]\n风吹过 没有声音"
```

Generate music and wait for completion:

```bash
python3 "$SKILL_DIR/scripts/generate_music.py" \
  --title "Chasing Stars" \
  --style "pop, inspirational, female vocal" \
  --prompt "[Verse]\n风吹过 没有声音" \
  --wait
```

Query an existing task once:

```bash
python3 "$SKILL_DIR/scripts/generate_music.py" \
  --task-id "019e10a5-8017-7e05-b14c-4cadeb2ee1ee"
```

## Inputs

- Required for create:
  - `--prompt`
  - `--title`
  - `--style`
- Optional:
  - `--custom-mode`
  - `--make-instrumental`
  - `--mv`
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
- `audio_url`
- `source_url`
- `query_attempts`
- `elapsed_seconds`
- `trace_id`

Do not depend on provider raw responses, `input_params`, or `task_result` in this skill's stdout. The script may parse provider internals to extract `source_url`, but it intentionally emits only the minimal stable contract.

## Common Mistakes

- Forgetting `--title` or `--style`
- Using this skill for plain TTS instead of music
- Forgetting `--wait` when the user explicitly needs the final audio URL in the same command
