---
name: generate-img
description: Use when a user wants MagicLight text-to-image or image-to-image generation from a prompt and optional source image URL
required_environment_variables:
  - name: MAGIC_SVC_KEY
    prompt: MagicLight service key
    required_for: MagicLight image generation
  - name: MAGIC_SVC_AUTH
    prompt: MagicLight service auth
    required_for: MagicLight image generation
  - name: MAGIC_USER_ID
    prompt: MagicLight user id
    required_for: MagicLight image generation
---

# Generate Img

## Overview

Use this skill to generate images with the MagicLight open task API. It handles both text-to-image (`t2i`) and image-to-image (`i2i`) requests through a stable Python script instead of ad hoc `curl` commands.

## When To Use

- The user wants to create an image from a text prompt
- The user wants to transform an existing image while preserving some visual identity
- The user explicitly wants the MagicLight image API instead of a local model or another provider
- The task needs a reproducible command that returns a final image URL in structured JSON

Do not use this skill for video generation. Use `generate-video` for image-to-video workflows.

## Workflow

1. Confirm the required environment variables exist:
   - `MAGIC_SVC_KEY`
   - `MAGIC_SVC_AUTH`
   - `MAGIC_USER_ID`
2. Choose mode:
   - If the user provides only `prompt`, use `t2i`
   - If the user provides `prompt` and a source image URL, use `i2i`
3. Invoke `scripts/generate_image.py` from this skill directory.
4. Return the `primary_image_url` and any relevant task metadata to the user.

Always use the script. Do not handcraft JSON payloads in the model response unless the user specifically asks to see them.

## Commands

Text-to-image:

```bash
python3 /Users/zengqi/projects/magic-skills/generate-img/scripts/generate_image.py \
  --prompt "A cinematic toy astronaut walking on a strawberry planet, ultra detailed, soft lighting" \
  --aspect-ratio "9:16"
```

Image-to-image:

```bash
python3 /Users/zengqi/projects/magic-skills/generate-img/scripts/generate_image.py \
  --prompt "Keep the character identity, change the outfit to a white space suit, sunset background, more cinematic" \
  --image-url "https://as1.ftcdn.net/v2/jpg/06/13/78/30/1000_F_613783000_JU3rYvelgdaRtcCskB24cOGCzxFJnDp3.jpg" \
  --image-mime-type "image/jpg" \
  --aspect-ratio "16:9"
```

## Inputs

- Required:
  - `--prompt`
- Optional:
  - `--image-url` switches the request to `i2i`
  - `--image-mime-type`
  - `--aspect-ratio`
  - `--model`
  - `--task-id`
  - `--base-url`
  - `--user-id`
  - `--timeout`

## Output

The script prints JSON with:

- `type`
- `task_id`
- `status`
- `need_query`
- `primary_image_url`
- `images`
- `text`
- `raw_response`

If the API response is malformed or unsuccessful, the script exits non-zero and prints a clear error message.

## Reference

Read `references/api.md` if you need to inspect the exact payload shapes or response contracts.

## Common Mistakes

- Missing environment variables: fail fast and tell the user which variable is absent
- Using `generate-img` for video requests: route those to `generate-video`
- Forgetting `--image-url` for image-to-image edits: without it the script will submit `t2i`
