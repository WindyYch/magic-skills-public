---
name: video-asset-executor
description: Use when the user asks to execute asset-dag.json, generate video production media assets, resume failed asset tasks, produce asset-manifest.json, or write run-report.json.
version: 1.1.0
metadata:
  hermes:
    tags: [creative, video, assets, media-generation, execution]
    related_skills: [video-production-planner, video-asset-dag, magicclaw-generate-tts, magicclaw-generate-img, magicclaw-imgs-to-img, magicclaw-generate-video, magicclaw-generate-music, video-subtitle-alignment, video-remotion-renderer, video-qa]
---

# AI Video Asset Executor

Use this role skill to execute `asset-dag.json` and produce `asset-manifest.json`, `run-report.json`, and media assets when concrete tools are available. The first executor action after reading `asset-dag.json` is always to initialize or refresh both files before calling any concrete media helper: `asset-manifest.json` records asset IDs and lineage, while `run-report.json` records task status.

If this skill is loaded by `video-production-planner`, follow the planner's `video_spec`, project workspace, and protocol contracts.

## Execution Modes

### Direct invocation

When the user invokes `video-asset-executor` directly, return only `asset-manifest.json`, `run-report.json`, and execution status.

### Planner-orchestrated invocation

When `video-production-planner` loads this skill with `orchestration_mode: planner_orchestrated`, the output rules below constrain only execution artifacts. After execution status is complete, follow the planner's remaining stages. Continue to `video-subtitle-alignment` when native dialogue alignment is required; continue to `video-remotion-renderer` when render is requested and no alignment is required; continue to QA when execution is blocked or specs-only has been requested.

## Role Boundary

The asset executor owns DAG execution truth in practice: dependency checks, tool calls when available, remote media URLs, optional local cache paths, task status, expected output materialization, retry state, and dynamic values such as `voice_id`. It does not change story, prompts, edit timing, subtitle alignment, render input, or final video.

## Inputs

Required:

- `asset-dag.json`

Optional:

- existing `asset-manifest.json`
- existing `run-report.json`
- concrete media generation tools or skills such as `magicclaw-generate-img`, `magicclaw-imgs-to-img`, and `magicclaw-generate-video`
- project workspace path

Use `asset-dag.json` task fields as execution truth, especially:

- `task_type`
- `tool`
- `input_refs`
- `wait_for`
- `params`
- `dynamic_params`
- `expected_outputs`

## Outputs

Return:

- `asset-manifest.json`
- `run-report.json`
- generated or provided media assets

Treat `asset-manifest.json` as the persisted asset/lineage truth and `run-report.json` as the persisted execution/status truth.

Recommended directory shape:

```text
project_runs/<project_id>/
  04_assets/
    references/
    images/
    videos/
    audio/
    sfx/
    bgm/
  asset-manifest.json
  run-report.json
```

## Execution Rules

- Immediately after loading `asset-dag.json`, write initial `asset-manifest.json` and `run-report.json` before invoking any concrete media generation helper. The manifest must include placeholder asset entries for each declared output and must not include a top-level `tasks` array. The run report must include one task record per DAG task with `task_id`, `stage`, `task_type`, `tool`, `expected_outputs`, `status: pending`, `attempts: 0`, `provider_task_id: null`, empty `output_asset_ids`, and empty `error` / `blocked_reason`.
- The initial manifest and run report are not optional. If no media helper can run because credentials, tools, refs, or user approval are missing, the manifest still records the declared asset outputs and the run report marks affected task statuses as `blocked`.
- During execution, update task status only in the existing run report: `pending -> running -> success | blocked | failed | skipped`. Update the manifest only with asset facts such as `url`, `path`, dimensions, duration, provider IDs, and lineage. Do not wait until all assets finish before creating either `asset-manifest.json` or `run-report.json`.
- When constructing or repairing `asset-manifest.json`, never copy task records or status-bearing fields from `run-report.json` or old manifests. Drop forbidden manifest fields including top-level `status`, top-level `tasks`, `assets[].status`, and `assets[].task_status`.
- Execute tasks only when every `wait_for` dependency is complete.
- Persist stable provider URLs into `asset-manifest.json` whenever they exist. Local file materialization may exist as cache or support data, but should not replace remote URLs as the primary manifest locator.
- Do not persist redacted provider URLs. If a returned URL contains `***` or `Signature=***`, that value is display-only and invalid. Re-run through a helper mode that writes raw output to a file before terminal redaction, or materialize a local file and persist `path` instead.
- Record every task status in `run-report.json` as `success`, `failed`, `blocked`, or `skipped`.
- If a concrete tool is unavailable, mark the task as `blocked` in `run-report.json` and do not invent a tool.
- If execution pauses for human approval, budget/resource control, or batch-size confirmation, write the partial `asset-manifest.json` and `run-report.json`, then call `kanban_comment()` and `kanban_block(reason=...)`. Do not call `kanban_complete()` for a run that still needs human approval.
- Preserve task IDs from `asset-dag.json`.
- Do not overwrite the DAG `task_id` with the task ID returned by a concrete provider. Store the provider/API returned task ID in `run-report.json.tasks[].provider_task_id`.
- For MagicClaw helpers, the helper stdout field `task_id` is the provider task ID used for later status queries. Copy it into `provider_task_id`, and keep the DAG task ID in `task_id`.
- MagicClaw concrete helper creation should default to asynchronous submit mode. Do not pass `--wait` during the initial create/submit call unless the user explicitly requested blocking synchronous execution for that single task.
- After an async submit succeeds, set the run-report task to `running`, persist `provider_task_id`, and leave `output_asset_ids` empty until a later query returns a final URL.
- When a task uses `magicclaw-imgs-to-img`, verify that every required reference image resolves to a reusable remote URL from user inputs or upstream asset metadata before execution.
- When a task uses `magicclaw-imgs-to-img`, resolve `reference_bindings` into the concrete ordered list of upstream reference image URLs and pass each resolved URL into the helper as a real image input. Use `input_refs` as the compact order check, not as the only resolution source.
- For `magicclaw-imgs-to-img`, `wait_for` means the producer tasks must finish first; `input_refs` means those produced reference assets must actually be consumed during generation.
- When a task uses `magicclaw-generate-video`, verify that its source image already exists in user inputs or prior task outputs before execution.
- Respect `expected_outputs` as the materialization contract for each task. If a task succeeds, `asset-manifest.json` should contain matching asset entries for those outputs.
- Respect `params.duration_sec` as the requested generation duration. Do not silently collapse it down to the edited cut length when the DAG intentionally requested source headroom.
- If a task carries override or continuity parameters from upstream planning, pass them through to the concrete tool instead of dropping them during execution.

## Task-Type Rules

- `character_reference` and `keyframe_image` tasks should persist image asset URLs in the manifest and may additionally materialize local cache files in `references/` or `images/` when needed.
- `keyframe_image` tasks using `magicclaw-imgs-to-img` should preserve which remote reference URLs were used, and should persist any returned remote image URL alongside the local materialized file when available.
- `keyframe_image` tasks using `magicclaw-imgs-to-img` should call the helper with the scene prompt plus one image input per resolved ref URL. If any required binding or required ref URL is missing, mark the task `blocked` rather than silently generating from prompt only.
- `voice_profile_create` should persist any produced `voice_id` or equivalent speaker handle into `asset-manifest.json` or `run-report.json`.
- `voiceover_tts` should write an audio asset with stable duration metadata so downstream render timing can rely on it, and should persist the provider audio URL as the primary manifest locator when available.
- For `voiceover_tts`, persist the `audio_url` returned by `magicclaw-generate-tts` as the primary manifest locator when it is a usable provider URL. If the observed URL is redacted or missing, query the MagicClaw task again by `provider_task_id` from `run-report.json` and persist the unredacted provider result; otherwise mark the task `blocked` rather than storing an invalid URL.
- `image_to_video` should preserve the requested motion duration from task params and persist the resulting video URL plus actual returned video duration.
- `native_dialogue_video` should preserve exact-line speech constraints from the DAG prompt package and any required `voice_id` dynamic param.
- `sfx` and `bgm` tasks should write audio assets whose usage is clear enough for downstream mix and render stages.

## Manifest Rules

- `asset-manifest.json` should persist one asset entry per declared output asset as soon as the DAG is handed to the executor, whether the asset is not yet generated, generated, or user-provided.
- `asset-manifest.json` must not include a top-level task index such as `tasks`. Task lists belong in `asset-dag.json` and `run-report.json`; the manifest should expose assets only.
- If a generated manifest contains `status` or `task_status` anywhere, treat it as invalid and rewrite the manifest before continuing. Do not leave invalid status fields in place for compatibility.
- `asset-manifest.json` must be complete for the executed scope. Do not keep only final scene videos or only one representative asset per scene when reference images, keyframes, narration audio, dialogue audio, SFX, or BGM were also materialized.
- If execution produced multiple asset classes for the same scene, persist each class as its own asset entry rather than collapsing them together.
- In normal runtime manifests, prefer a lightweight `id` / `url` / `type` style entry whenever that is sufficient for downstream stages.
- Do not emit path-only asset entries when the provider returned a stable remote URL for the same asset.
- Each asset entry should preserve the `asset_id` expected by downstream stages rather than inventing a fresh transient identifier on retry.
- Manifest asset IDs must use the final output asset ID from `expected_outputs`, not the producing `task_id`. For example, a video task `T_VID_S07` should materialize a manifest asset ID such as `VID_S07`.
- Each manifest asset entry may preserve the producing `task_id` for lineage. Do not store task status in manifest asset entries; use `run-report.json` for that.
- When available, persist:
  - `task_id`
  - `scene_id`
  - asset `type`
  - remote `url`
  - local `path` only when a local cache copy is intentionally materialized
  - `mime_type`
  - `duration_sec`
  - `width`
  - `height`
  - tool or provider metadata
  - source-task lineage
  - dynamic values such as `voice_id` and provider job IDs
- When a provider returns a reusable remote media URL, persist it as the primary manifest `url`.
- A manifest URL containing `***` is not a valid media locator and fails quality checks.
- For image or reference assets, preserve reusable source URLs so downstream `magicclaw-imgs-to-img` tasks can consume them directly.
- When a `magicclaw-imgs-to-img` task succeeds, preserve enough lineage in the manifest or run report to show which upstream refs were actually consumed, so retries do not lose the ref-to-image mapping.
- For TTS audio assets, preserve the provider audio URL in the manifest entry itself rather than only in local-cache-oriented metadata.
- If a task is blocked before producing a file, keep the manifest placeholder asset entries intact and write the blocked state only into `run-report.json`.

For normal video production runs, the manifest should usually include all materialized asset classes that exist for the requested deliverable, such as:

- `reference_image`
- `keyframe_image`
- `narration_audio`
- `dialogue_audio` when applicable
- `video_clip`
- `sfx`
- `bgm`

## Run Report Rules

- `run-report.json` should clearly separate `success`, `partial`, `blocked`, `failed`, and `not_requested` at the top level.
- `run-report.json` should be initialized immediately after DAG handoff with one task record per DAG task, initially `status: pending` unless the task is already known to be blocked or skipped.
- The top-level `run-report.json.status` should move through `initialized` or `running` before settling on `success`, `partial`, `blocked`, `failed`, or `not_requested`.
- Each task record should preserve `task_id`, `stage`, `task_type`, `tool`, `expected_outputs`, current `status`, attempts, provider task ID, output asset IDs, failures, blocked reasons, and any emitted dynamic values needed for retry.
- `provider_task_id` is required for every concrete generation task once the provider create/submit call succeeds. It is the API-returned task ID used to query provider status, such as calling the same MagicClaw helper with `--task-id <provider_task_id>`.
- If a task has not yet been submitted, keep `provider_task_id: null`. If a provider call succeeds but `provider_task_id` is missing, mark the task `blocked` or `failed` because the task cannot be queried or resumed safely.
- When a concrete helper submit call begins, set the task `status` to `running` and increment `attempts` before or at the call boundary so a crash or pause still leaves inspectable progress.
- For default async execution, do not mark a task `success` immediately after submit. Mark it `success` only after querying by `provider_task_id` and receiving the final usable media URL.
- Blocked execution is not the same as failed execution. Use `blocked` when an input, dependency, credential, or concrete tool is missing.
- If one task fails or blocks after earlier tasks succeeded, keep the successful outputs in `asset-manifest.json` and mark the overall run `partial` or `blocked` instead of wiping progress.

## Retry Rules

- Retry should start from existing `asset-manifest.json` and `run-report.json` state when present.
- Retry must restore non-file dynamic values, including `voice_id`.
- `voice_id`, provider job IDs, and other dynamic values must be written to `asset-manifest.json` or `run-report.json`.
- Do not regenerate completed dependencies unless the producing task or its inputs changed.
- A failed downstream scene video should reuse existing references, keyframes, and voices when still valid.
- If a task's expected outputs already exist locally and still match the current task inputs, mark that task `skipped` or reuse the prior success state instead of regenerating it.
- Retry should restore dynamic params from prior producer tasks before re-running dependent tasks.

## Tool Names

Use concrete tool names only when they exist in the running environment. Claw-style examples include:

- `magicclaw-generate-tts`
- `magicclaw-generate-img`
- `magicclaw-imgs-to-img`
- `magicclaw-generate-video`
- `magicclaw-generate-music`
- `tts_engine`
- `nano_image`
- `image_generation_with_reference`
- `veo_i2v`
- `audio_sfx`
- `bgm_generator`
- `kling_create_voice`

When concrete helpers are available in Hermes, prefer `magicclaw-generate-tts` for MagicClaw voiceover TTS, `magicclaw-imgs-to-img` for reference-conditioned keyframes that must visibly preserve character or key-prop refs, `magicclaw-generate-img` for plain still/reference creation, `magicclaw-generate-video` for image-to-video clips, and `magicclaw-generate-music` for generated BGM/music tasks. If these tools are unavailable in Hermes, return a blocked report with the required task names and parameters.

For `magicclaw-imgs-to-img`, the concrete helper call should behave like:

- one scene prompt
- one `image-url` argument per resolved reference image URL
- no prompt-only fallback when the DAG declared required refs

## Native Dialogue And Duration Rules

- `native_dialogue_video` tasks must preserve any exact spoken Chinese line constraints already compiled by the DAG. Do not paraphrase or shorten them during execution.
- If a native dialogue task depends on `voice_id`, verify that the value is available from prior task results before execution; otherwise mark the task `blocked`.
- For Kling-style dialogue video, enforce an integer duration from `3` to `15`. If the requested duration falls outside that range, report the task as blocked or failed according to whether the issue is recoverable without rewriting the DAG.
- For motion tasks, keep both truths when possible:
  - requested duration from task params
  - actual returned asset duration from the provider

## Blocked-State Rules

- If execution cannot proceed because a tool is unavailable, credentials are missing, a user-provided input is absent, or a dependency did not materialize, mark the task `blocked`.
- A blocked task should record what is missing and which downstream tasks remain blocked because of it.
- If execution cannot proceed because more user approval is needed for cost, quota, or resource usage, block the Kanban task with `kanban_block(reason=...)` instead of completing a partial run. The UI can only surface approval/retry actions while the Kanban task remains blocked.
- Do not invent substitute assets just to keep the pipeline moving. Persist the blocker cleanly so the planner, QA, or the user can resolve it.

## Quality Checks

Before returning, check:

- every generated/provided asset has a first-class remote `url` when the provider returned one
- `asset-manifest.json` exists immediately after `asset-dag.json` handoff, even before media generation completes
- `run-report.json` exists immediately after `asset-dag.json` handoff, even before media generation completes
- `asset-manifest.json` has no top-level `tasks` array
- every DAG task appears in `run-report.json.tasks` with current `status`, including `pending` and `running` states
- every submitted concrete generation task in `run-report.json.tasks` preserves the provider/API returned `provider_task_id` for later status queries
- default MagicClaw helper calls use async submit behavior; final URLs are populated only after follow-up provider status queries succeed
- every declared `expected_outputs` item appears as a manifest asset entry with its producing `task_id`
- `asset-manifest.json` does not contain top-level `tasks` or any status fields: no top-level `status`, no `assets[].status`, and no `assets[].task_status`
- no generated/provided asset has a redacted URL containing `***`
- every materialized image, audio, and video asset is represented in `asset-manifest.json`, not just a subset
- every satisfied `expected_outputs` entry is represented in `asset-manifest.json`, or the blocker/failure is explicit in `run-report.json`
- manifest asset IDs use final output IDs such as `VID_S01` or `VO_S01`, not task IDs such as `T_VID_S01`
- `run-report.json` records failures, blocked reasons, and retry state
- `voice_id` and other dynamic values are recoverable
- generated motion assets preserve requested-duration intent and actual duration metadata
- `magicclaw-imgs-to-img` tasks do not silently proceed without reusable remote reference URLs
- `magicclaw-imgs-to-img` tasks actually consume the ref URLs declared by `reference_bindings` and `input_refs`, not just their dependency completion state
- native dialogue tasks preserve exact-line constraints and dynamic dependencies
- no subtitle alignment or render work is attempted inside the asset execution artifact
