# MiniMax Synchronous TTS HTTP Notes

Source: MiniMax official synchronous speech synthesis documentation for `POST /v1/t2a_v2`.

## Request

- Method: `POST`
- Endpoint: `https://api.minimax.io/v1/t2a_v2`
- Optional query parameter in some official examples: `GroupId=<group-id>`
- Auth header: `Authorization: Bearer <api-key>`
- Content type: `application/json`

### Core body fields used by this skill

- `model`
- `text`
- `stream`
- `output_format`
- `voice_setting`
- `audio_setting`
- `subtitle_enable`
- `language_boost`
- `aigc_watermark`

### Voice setting fields exposed directly

- `voice_id`
- `speed`
- `vol`
- `pitch`
- `emotion`

The script also supports `--voice-setting-json` to merge additional documented fields into `voice_setting`.

### Audio setting fields exposed directly

- `sample_rate`
- `bitrate`
- `format`
- `channel`

The script also supports `--audio-setting-json` to merge additional documented fields into `audio_setting`.

## Response

For non-stream mode, the script expects:

- `base_resp.status_code == 0` for success
- `data.audio` containing either:
  - inline audio hex when `output_format=hex`
  - a temporary audio URL when `output_format=url`
- `trace_id`
- `extra_info`

## Skill-specific behavior

- default `stream=false`
- default `output_format=url`
- default endpoint is `https://api.minimax.io/v1/t2a_v2`
- if local certificate verification fails because of a self-signed certificate chain, the script retries once with a compatible SSL context
- local file output is only supported in `hex` mode because URL mode does not return inline bytes
