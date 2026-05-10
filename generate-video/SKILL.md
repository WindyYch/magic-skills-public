---
name: generate-video
description: Use when a user wants MagicLight image-to-video generation that may require polling for the final video URL
required_environment_variables:
  - name: MAGIC_SVC_KEY
    prompt: MagicLight service key
    required_for: MagicLight video generation
  - name: MAGIC_SVC_AUTH
    prompt: MagicLight service auth
    required_for: MagicLight video generation
  - name: MAGIC_USER_ID
    prompt: MagicLight user id
    required_for: MagicLight video generation
---

# Generate Video

## Overview

Use this skill to generate videos through the MagicLight image-to-video API. It wraps both task creation and task polling in a single Python script so the agent can reliably return the final `video_url`.

## When To Use

- The user wants to animate an image into a short video clip
- The request should go through the MagicLight `i2v` API
- The task may need polling before the final asset URL is available
- The workflow should return a stable JSON result instead of a manual `curl` transcript

Do not use this skill for still image generation. Use `generate-img` when the user wants `t2i` or `i2i`.

## Workflow

1. Confirm the required environment variables exist:
   - `MAGIC_SVC_KEY`
   - `MAGIC_SVC_AUTH`
   - `MAGIC_USER_ID`
2. Collect the required inputs:
   - `prompt`
   - source `img_url`
3. Run `scripts/generate_video.py`.
4. If the create response sets `need_query=true`, let the script poll until it returns `status=2` or times out.
5. Return the final `video_url` and task metadata to the user.

Always use the script. Do not manually poll the API in the model response unless the user explicitly asks for raw request examples.

## Command

```bash
python3 /Users/zengqi/projects/magic-skills/generate-video/scripts/generate_video.py \
  --prompt "图中的人物在游泳池自由泳，保持人物面部细节不变" \
  --img-url "https://as1.ftcdn.net/v2/jpg/05/98/80/90/1000_F_598809067_KSuZtTsrFSRyRMTbBAJEn0wWAsEnJSIa.jpg" \
  --ratio 1 \
  --definition 720 \
  --duration 5 \
  --image2video-pro-type seedance2_0 \
  --enable-audio
```

## Inputs

- Required:
  - `--prompt`
  - `--img-url`
- Optional:
  - `--ratio`
  - `--definition`
  - `--duration`
  - `--image2video-pro-type`
  - `--enable-audio` or `--disable-audio`
  - `--poll-interval-seconds`
  - `--max-wait-seconds`
  - `--no-wait`
  - `--base-url`
  - `--user-id`
  - `--timeout`

## Output

The script prints JSON with:

- `task_id`
- `status`
- `need_query`
- `video_url`
- `query_attempts`
- `elapsed_seconds`
- `raw_create_response`
- `raw_query_response`

## Reference

Read `references/api.md` when you need the exact API contract.

## Common Mistakes

- Forgetting `--img-url`: video generation always requires a source image
- Stopping after create when `need_query=true`: the script should keep polling unless `--no-wait` is set
- Treating `status=1` as failure: it means the task is still running
