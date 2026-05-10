---
name: generate-tts
description: Use when a user wants MiniMax synchronous text-to-speech generation with configurable voice or audio settings, returning an audio URL by default and optionally saving a local audio file
required_environment_variables:
  - name: MINIMAX_API_KEY
    prompt: MiniMax API key
    required_for: MiniMax text-to-speech generation
  - name: MINIMAX_GROUP_ID
    prompt: MiniMax group id
    required_for: MiniMax accounts that require GroupId
---

# Generate TTS

## Overview

Use this skill to generate speech through the MiniMax synchronous HTTP TTS API. It wraps a stable Python script around `POST /v1/t2a_v2` so the agent can return structured JSON. The default skill behavior is to request and return an `audio_url`; local audio file output is opt-in.

The script defaults to the official `https://api.minimax.io/v1/t2a_v2` endpoint and automatically retries once with a compatible SSL context when local certificate verification fails because of a self-signed certificate chain.

## When To Use

- The user wants text-to-speech from MiniMax
- The request should stay in synchronous single-request mode
- The user needs to tune `voice_setting` or `audio_setting`
- The workflow should return an `audio_url` by default
- The workflow may optionally save the returned audio bytes to a local file when the user explicitly asks for it

Do not use this skill for streaming TTS or long-text async speech generation.

## Workflow

1. Confirm the required environment variable exists:
   - `MINIMAX_API_KEY`
2. Optionally read `MINIMAX_GROUP_ID` if the account requires a `GroupId` query parameter.
3. Collect the required inputs:
   - `text`
   - `voice_id`
4. By default, run `scripts/generate_tts.py --output-format url`.
5. For asset pipeline usage, add `--output-json <path>` and let downstream code read that file directly when writing manifests. Hermes terminal output redacts sensitive URL query parameters such as `Signature`; do not copy a signed URL from stdout into a persisted manifest.
6. Return the generated audio metadata and `audio_url`.
7. Only switch to local file output when the user explicitly asks for a saved file or when a redacted signed URL would otherwise corrupt a manifest; in that case use `hex` mode together with `--output-file`.

Always use the script. Do not handcraft HTTP payloads in the model response unless the user explicitly asks for raw request examples.

## Commands

Basic synthesis:

```bash
python3 generate-tts/scripts/generate_tts.py \
  --text "欢迎使用 MiniMax 语音合成服务。" \
  --voice-id "male-qn-qingse" \
  --output-format url
```

Synthesis for asset manifests, preserving the raw provider URL in a file before terminal redaction:

```bash
python3 generate-tts/scripts/generate_tts.py \
  --text "欢迎使用 MiniMax 语音合成服务。" \
  --voice-id "male-qn-qingse" \
  --output-format url \
  --output-json "$HERMES_KANBAN_WORKSPACE/tts-result.json"
```

Synthesis with tuned voice and returned audio URL:

```bash
python3 generate-tts/scripts/generate_tts.py \
  --text "欢迎使用 MiniMax 语音合成服务。" \
  --voice-id "male-qn-qingse" \
  --output-format url \
  --speed 1.1 \
  --vol 1.2 \
  --pitch 0 \
  --emotion "happy" \
  --sample-rate 32000 \
  --bitrate 128000 \
  --format "mp3" \
  --channel 1
```

Synthesis with tuned voice and saved local audio file:

```bash
python3 generate-tts/scripts/generate_tts.py \
  --text "欢迎使用 MiniMax 语音合成服务。" \
  --voice-id "male-qn-qingse" \
  --output-format hex \
  --speed 1.1 \
  --vol 1.2 \
  --pitch 0 \
  --emotion "happy" \
  --sample-rate 32000 \
  --bitrate 128000 \
  --format "mp3" \
  --channel 1 \
  --output-file "/tmp/minimax-tts.mp3"
```

Advanced override example:

```bash
python3 generate-tts/scripts/generate_tts.py \
  --text "欢迎使用 MiniMax 语音合成服务。" \
  --voice-id "male-qn-qingse" \
  --output-format url \
  --voice-setting-json '{"english_normalization": true}' \
  --audio-setting-json '{"sample_rate": 44100}'
```

## Inputs

- Required:
  - `--text`
  - `--voice-id`
- Optional:
  - `--model`
  - `--group-id`
  - `--output-format`
  - `--subtitle-enable` or `--subtitle-disable`
  - `--language-boost`
  - `--aigc-watermark`
  - `--speed`
  - `--vol`
  - `--pitch`
  - `--emotion`
  - `--voice-setting-json`
  - `--sample-rate`
  - `--bitrate`
  - `--format`
  - `--channel`
- `--audio-setting-json`
- `--output-file`
- `--output-json`
- `--base-url`
- `--timeout`

## Output

The script prints JSON with:

- `status`
- `trace_id`
- `audio_format`
- `audio_url`
- `audio_hex`
- `audio_bytes`
- `output_path`
- `extra_info`
- `raw_response`

In normal skill usage, prefer `--output-format url`, so `audio_url` is the default returned asset and `output_path` is usually empty.

When `--output-json` is set, the same JSON result is written to that file before Hermes terminal redaction is applied to stdout. Use this file as the source of truth for downstream `asset-manifest.json` writes. Never persist `audio_url` values containing `Signature=***`.

If `--output-file` is set in `hex` mode, the file is written locally and `output_path` is populated. If `--output-format url` is used, the script returns `audio_url` and does not write a file.

## Reference

Read `references/api.md` when you need the exact API contract.

## Common Mistakes

- Forgetting `--voice-id`: MiniMax needs a concrete voice selection
- Forgetting that this skill defaults to URL output: only use `--output-file` when the user explicitly wants a local file
- Using `--output-file` with `--output-format url`: URL mode does not return inline audio bytes
- Copying an `audio_url` containing `Signature=***` from terminal output into a manifest: use `--output-json` and have code read the raw JSON file, or generate a local audio file with `--output-format hex --output-file`
- Overriding `--base-url` back to an old domain: the script now defaults to the official `api.minimax.io` endpoint
- Passing malformed JSON to `--voice-setting-json` or `--audio-setting-json`: the script rejects invalid JSON before making the HTTP request
