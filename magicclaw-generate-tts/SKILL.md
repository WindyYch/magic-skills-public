---
name: magicclaw-generate-tts
description: Use when a user wants MagicClaw text-to-speech generation through the async task API, defaulting to task creation and later status querying by task ID.
required_environment_variables:
  - name: MagicClawDomain
    prompt: MagicClaw API domain or base URL
    required_for: MagicClaw text-to-speech generation
  - name: MagicClawAuthorization
    prompt: MagicClaw Authorization header value
    required_for: MagicClaw text-to-speech generation
---

# MagicClaw Generate TTS

## Overview

Use this skill to submit MagicClaw TTS tasks to `/taskapi/v1/task/gen/tts`. By default, the script returns immediately with a provider `task_id`; pass `--wait` only when you explicitly need to poll `/taskapi/v1/task/batch/get` until the final audio URL is ready.

The script accepts `MagicClawDomain` and `MagicClawAuthorization`. It also accepts uppercase aliases `MAGIC_CLAW_DOMAIN` and `MAGIC_CLAW_AUTHORIZATION`.

## When To Use

- The user wants TTS through the MagicClaw task API
- The request should use the documented nested `audio_setting` and `voice_setting` structure
- The workflow should return a stable provider task ID first, then query final audio status later

Do not use this skill for music generation.

## Workflow

1. Confirm `MagicClawDomain` and `MagicClawAuthorization` exist.
2. Collect `text` and `voice_id`.
3. Run the script.
4. By default, return immediately after task creation and persist the returned provider `task_id`.
5. Return only the minimal task result fields needed by downstream orchestration.

## Commands

Submit TTS and return `task_id`:

```bash
python3 "$SKILL_DIR/scripts/generate_tts.py" \
  --text "哈哈哈哈哈，今天天气正好" \
  --voice-id "female-yujie"
```

Generate TTS and wait for completion:

```bash
python3 "$SKILL_DIR/scripts/generate_tts.py" \
  --text "哈哈哈哈哈，今天天气正好" \
  --voice-id "female-yujie" \
  --wait
```

Query an existing task once:

```bash
python3 "$SKILL_DIR/scripts/generate_tts.py" \
  --task-id "019e10a0-6d0f-7854-bb40-6e02a82da7a8"
```

## Inputs

- Required for create:
  - `--text`
  - `--voice-id`
- Optional:
  - `--model`
  - `--output-format`
  - `--source`
  - `--stream`
  - `--speed`
  - `--vol`
  - `--pitch`
  - `--format`
  - `--sample-rate`
  - `--bitrate`
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

- Forgetting `--voice-id`
- Using this skill for music generation instead of TTS
- Expecting synchronous inline audio bytes instead of an async task result
