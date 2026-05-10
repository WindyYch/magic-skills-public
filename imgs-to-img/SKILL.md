---
name: imgs-to-img
description: Use when a user wants to combine multiple image URLs into one generated image through the Duomi Gemini Nano Banana API
required_environment_variables:
  - name: DUOMI_API_AUTHORIZATION
    prompt: Duomi API Authorization header value
    required_for: Duomi multi-image reference generation
---

# Imgs To Img

## Overview

Use this skill to preview the effective Duomi generation parameters first, confirm them with the user, then submit a prompt plus multiple remote image URLs to the Duomi Nano Banana edit API, reply immediately with the created `task_id`, and continue polling until the final composed image is ready.

## When To Use

- The user wants to merge or compose multiple image URLs into one generated image
- The user or upstream planner wants to build a `keyframe_image` from recurring character refs or key-prop refs that must be visibly preserved
- The request should go through the Duomi Gemini Nano Banana API
- The request should not block the conversation while the image task is running
- The caller can provide only remote image URLs, not local files

Do not use this skill when the caller has only local file paths and no reusable remote image URLs.

## Planner Integration

When `imgs-to-img` is invoked as a concrete helper inside `video-asset-executor` for a predeclared `asset-dag.json` task:

- treat the task's `model`, `aspect_ratio`, and `image_size` params as already confirmed unless the user explicitly asks to tune them
- skip the extra user confirmation loop
- still require one or more reusable remote image URLs; local file paths alone are not enough
- do not silently downgrade the task to `generate-img` just because reusable remote URLs are missing

## Workflow

1. When you are ready to submit, confirm `DUOMI_API_AUTHORIZATION` exists.
2. Collect `prompt` and one or more image URLs.
3. Run `scripts/imgs_to_img.py --preview-params` with any candidate `model`, `aspect_ratio`, and `image_size` flags.
4. Show the effective `model`, `aspect_ratio`, and `image_size` values to the user.
5. Ask whether the parameters are OK and state clearly that only `model`, `aspect_ratio`, and `image_size` may be modified.
6. If the user changes parameters, rerun preview mode with the updated flags and show the new values again.
7. After the user confirms, start the Duomi task with `scripts/imgs_to_img.py --no-wait`.
8. Reply immediately with:
   - the generated `task_id`
   - the execution steps:
     1. task submitted
     2. background polling started
     3. final result will be returned when ready
9. Continue polling the task in the background with `scripts/imgs_to_img.py --task-id <task_id>`, using a background worker, subagent, or equivalent non-blocking task runner when the environment supports it. The default polling interval is 10 seconds.
10. When polling reaches `state=succeeded`, return the final `primary_image_url`, `images`, and task metadata.

If the user explicitly wants to wait in the foreground, run the script without `--no-wait`. If the environment cannot send a proactive follow-up message later, tell the user that limitation and give them the exact `--task-id` command needed to resume the task.

## Command Notes

- Preview the effective parameters before creating the task:
  - `python3 imgs-to-img/scripts/imgs_to_img.py --preview-params`
- Preview again after changing only `model`, `aspect_ratio`, or `image_size`:
  - `python3 imgs-to-img/scripts/imgs_to_img.py --preview-params --model "nano-banana-pro" --aspect-ratio "1:1" --image-size "1K"`
- Create after confirmation and return immediately:
  - `python3 imgs-to-img/scripts/imgs_to_img.py --prompt "..." --image-url "..." --image-url "..." --no-wait`
- Reattach to an existing task and keep polling:
  - `python3 imgs-to-img/scripts/imgs_to_img.py --task-id "<task_id>"`
- Reattach to an existing task and inspect its current state once:
  - `python3 imgs-to-img/scripts/imgs_to_img.py --task-id "<task_id>" --no-wait`
