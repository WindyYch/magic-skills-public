---
name: video-asset-dag
description: Use when the user asks to create asset-dag.json, compile video production assets into a dependency graph, plan image/video/audio generation tasks, or define media generation order from storyboard.json and edit-plan.json.
version: 1.1.0
metadata:
  hermes:
    tags: [creative, video, asset-dag, media-generation, dag]
    related_skills: [video-production-planner, video-storyboard, video-editor, video-asset-executor, generate-tts, generate-img, imgs-to-img, generate-video]
---

# AI Video Asset DAG Compiler

Use this role skill to compile `storyboard.json + edit-plan.json` into `asset-dag.json`.

If this skill is loaded by `video-production-planner`, follow the planner's `video_spec`, `creator_context`, and protocol contracts.

## Execution Modes

### Direct invocation

When the user invokes `video-asset-dag` directly, return only `asset-dag.json` and stop.

### Planner-orchestrated invocation

When `video-production-planner` loads this skill with `orchestration_mode: planner_orchestrated`, the JSON-only rule below applies only to the `asset-dag.json` artifact. After the artifact is complete, follow the planner's remaining stages. In specs-only mode, continue to QA. In execution mode, continue to `video-asset-executor` when concrete tools and required inputs are available.

## Role Boundary

The asset DAG compiler owns execution planning: task ordering, task dependencies, tool assignment, generation parameters, dynamic parameter wiring, and expected outputs. It compiles storyboard prompts together with edit-plan execution truth. It declares which tasks should use concrete tools such as `generate-img`, `imgs-to-img`, and `generate-video`, but it does not execute those tools, write actual media, align subtitles, edit the timeline, or render exports.

## Inputs

Required:

- `storyboard.json`
- `edit-plan.json`

Optional:

- `video_spec`
- existing `asset-dag.json` to revise

Use both upstream artifacts as sources of truth:

- `storyboard.json` provides scene prompts, asset references, voice intent, sound intent, and reference requirements.
- `edit-plan.json` provides execution truth for source choice, motion treatment, source-window headroom, subtitle alignment requirements, and scene audio usage.

Pay special attention to:

- `timeline[].video_strategy.primary_source_type`
- `timeline[].video_strategy.fallback_source_type`
- `timeline[].video_strategy.motion_treatment`
- `timeline[].audio_strategy`
- `timeline[].subtitle_strategy`
- `timeline[].render_hints.requested_source_window_sec`
- `timeline[].render_hints.source_override_reason`
- `global_audio_plan.bgm_strategy`
- `global_audio_plan.scene_sound_bed_policy`
- `global_audio_plan.alignment_required_scene_ids`

## Output

For direct invocation, return only valid JSON for `asset-dag.json` and do not wrap it in Markdown. For planner-orchestrated invocation, the `asset-dag.json` artifact itself must be valid JSON; the planner may continue with later artifact sections afterward.

Required shape:

```json
{
  "project_id": "",
  "execution_stages": ["P0", "P1", "P2", "P3", "P4"],
  "tasks": [
    {
      "task_id": "",
      "stage": "P0",
      "task_type": "",
      "tool": "",
      "input_refs": [],
      "reference_bindings": [],
      "wait_for": [],
      "params": {},
      "dynamic_params": {},
      "expected_outputs": []
    }
  ]
}
```

## Stage Rules

| Stage | Meaning | Common tasks |
|---|---|---|
| `P0` | Global Anchors | conditional character references, reusable location or screen references when needed, `voice_profile_create`; character reference image tasks use `tool: generate-img` |
| `P1` | Scene Audio | voiceover TTS, dialogue voice preparation when needed |
| `P2` | Scene Keyframes | scene keyframes and reference-conditioned stills; scene keyframe image tasks use `tool: imgs-to-img` when recurring character or key-prop refs must be visibly preserved, otherwise `tool: generate-img` |
| `P3` | Motion Assets | image-to-video or native dialogue scene clips; scene video tasks use `tool: generate-video` |
| `P4` | Supplemental Audio | SFX and BGM |

## Compilation Rules

- Join scenes by `scene_id` across `storyboard.json.scenes` and `edit-plan.json.timeline`; if a scene exists in one file but not the other, treat that as a protocol error rather than inventing a task.
- When `storyboard.json` and `edit-plan.json` disagree, use `edit-plan.json` as execution truth for source type, motion treatment, clip duration request, audio path, and subtitle dependency.
- Do not treat `fallback_source_type` as an automatic parallel-generation instruction. Only add explicit fallback tasks when the user asks for redundancy or when the workflow contract explicitly requires both branches.
- Carry `render_hints.source_override_reason` into the relevant task params when the editor promoted a scene away from the storyboard default, so downstream execution can preserve the reason for the override.

## Character Reference Rule

Use `storyboard.json` as the source of truth:

- If `global_assets` contains one or more recurring characters that scenes reference through `subject_refs`, `asset-dag.json` should include `P0` character reference tasks for those characters.
- If `storyboard.json` has no characters in `global_assets`, or scenes do not reference any recurring character identities, do not invent character reference tasks.
- Character reference tasks should be `task_type: character_reference` and use `tool: generate-img`.
- Scene keyframes that depend on recurring characters should wait for the relevant character reference tasks before generating scene images.

## Tool Assignment Rules

For the standard concrete execution path, use these fixed assignments:

- `P1` `voiceover_tts` tasks: `tool: generate-tts`
- `P0` `character_reference` tasks: `tool: generate-img`
- `P2` `keyframe_image` tasks with reusable character or key-prop refs: `tool: imgs-to-img`
- `P2` `keyframe_image` tasks without those refs: `tool: generate-img`
- `P3` `image_to_video` tasks: `tool: generate-video`
- `P3` `native_dialogue_video` tasks: `tool: generate-video`

Do not drift these fixed task types to other tool names unless the user explicitly changes the execution backend or the workflow is not using the standard concrete execution path.

## Source Strategy Rules

- `primary_source_type` determines the main executable branch for each scene:
  - `generated_image` means the scene's deliverable asset is normally the `P2` keyframe result
  - `generated_video` means the scene must produce a `P3` motion asset
  - `user_image` means use provided still media as the scene source and do not invent a `generate-img` task unless a derived keyframe is explicitly required
  - `user_video` means use provided video as the scene source and do not invent a generation task for that scene unless a derived asset is explicitly required
  - `none` means no scene media generation task should be created
- `motion_treatment` refines the branch choice:
  - `still_hold` usually stops at `P2`
  - `subtle_motion` usually still stops at `P2` unless the primary source is `generated_video` or the user explicitly wants a generated motion clip
  - `full_motion` should produce a `P3` motion asset
  - `native_dialogue` should produce a `P3` native dialogue video asset
- In the standard concrete execution path, scenes whose primary source is generated video still usually need a `P2` keyframe or equivalent source image unless the user already provided the source image/video.

## Dependency Rules

- A scene keyframe that uses character and scene references must wait for both references.
- If a `keyframe_image` must visibly preserve recurring character refs from `subject_refs` or key-prop refs from `scene_asset_refs` / `reference_requirements`, compile it as a reference-conditioned keyframe and use `tool: imgs-to-img` instead of plain `generate-img`.
- For `imgs-to-img` keyframes, `input_refs` is executable input, not commentary. It should list the exact reference asset refs that downstream execution must feed into the generation call.
- For `imgs-to-img` keyframes, also emit structured `reference_bindings` entries so execution does not need to infer how refs map to upstream assets.
- For `imgs-to-img` keyframes, `wait_for` should include the producer tasks that materialize those refs, so execution can resolve each declared ref to a real upstream image asset before generation starts.
- A dialogue scene using `kling_native` must wait for required `voice_id` creation.
- Scenes whose final source is `generated_image` may stop at keyframe/image outputs unless the edit plan explicitly requires motion.
- Scenes whose final source is `generated_video` should generate motion assets even if the original storyboard began as `image_first`.
- `generation_mode = dialogue_native` scenes should generate motion assets with native speech handling.
- Motion assets must wait for keyframes when the video task uses generated or user-supplied images as the source.
- `render_hints.requested_source_window_sec` should be copied into motion task params so downstream generation requests the right source clip length instead of the final edited cut length.
- SFX and BGM can run after the timing source exists, unless the planner marks stricter dependencies.
- A `generate-video` task must wait for a source image from user media or a prior `generate-img` or `imgs-to-img` task.
- `P2` scene keyframes with reusable character or key-prop refs must use `tool: imgs-to-img`.
- Other `P2` scene keyframes must use `tool: generate-img`.
- `P3` scene videos must use `tool: generate-video`.
- Do not create `character_reference` tasks for one-off scenes that have no recurring character identity in `storyboard.json`.

## Audio Task Rules

- If `audio_strategy.voice_render_mode = remotion_tts` and scene `audio.text` is non-empty, create a `P1` `voiceover_tts` task.
- When `voiceover_tts` is used in the standard synchronous TTS path, prefer `tool: generate-tts`.
- If `audio_strategy.voice_render_mode = kling_native` and the workflow needs a reusable speaker profile, create `P0` `voice_profile_create` before the scene's native dialogue video task.
- Use `global_audio_plan.alignment_required_scene_ids` to identify which scenes must preserve native dialogue timing for later subtitle alignment. Do not create `subtitle-alignment.json` tasks here; create the media prerequisites for those scenes.
- If `audio_strategy.use_scene_sound_design = true` and the scene has non-empty `sound_design.sfx_notes` or `sound_design.ambience_notes`, create `P4` `sfx` tasks only when the workflow expects generated supplemental sound instead of relying purely on in-video sound.
- If `global_audio_plan.bgm_strategy.enabled = true`, create a project-level `P4` `bgm` task unless the user supplied BGM already.

## Prompt And Param Rules

- `keyframe_image` tasks should use the scene `image_prompt` plus relevant character, location, and reference constraints.
- When `keyframe_image` uses `imgs-to-img`, keep the same image moment as the composition target and carry the required upstream reference asset IDs or refs in `input_refs` / task params so execution can resolve reusable remote image URLs.
- For `imgs-to-img`, preserve enough linkage that execution can map each `input_refs` item to one concrete upstream reference image. Do not leave the task in a state where refs exist only in prose inside the prompt.
- If the scene depends on multiple character or prop refs, keep all of them in `input_refs` so the executor can pass multiple reference images into one composed generation call.
- For `imgs-to-img`, `reference_bindings` should be the machine-readable source of truth for ref resolution. Each binding should include:
  - `ref_id`: the storyboard/global asset ref such as `REF_XZ`
  - `producer_task_id`: the upstream task expected to materialize that ref such as `T_CHAR_XZ`
  - `expected_output_id`: the expected output asset id such as `CHAR_XZ_REF` or `PROP_BALL_REF` when available
  - `asset_type`: usually `reference_image`
  - `usage_role`: `character | prop | location | style_anchor | other`
  - `required`: `true | false`
- Keep `input_refs` as the ordered compact list used by humans and quick checks, but do not rely on it alone when `tool: imgs-to-img`.
- `image_to_video` and `native_dialogue_video` tasks should use the scene `video_prompt` as the prompt base, not the still-image prompt alone.
- Carry scene `negative_constraints`, `reference_requirements`, `subject_refs`, `scene_asset_refs`, and relevant continuity conditions into task params so execution does not lose asset consistency.
- If `render_hints.continuity_direction` carries forward a state such as damage, wetness, props in hand, or screen content, preserve that state in the task params or prompt package for the affected scene.
- `params.duration_sec` for generated motion tasks should normally come from `render_hints.requested_source_window_sec`, not the final `timeline.duration_sec`, because the source clip may need extra headroom for trimming.

## `imgs-to-img` Task Schema

When a task uses `tool: imgs-to-img`, tighten the task shape as follows:

- `input_refs` is required and should preserve the intended reference order for generation input.
- `reference_bindings` is required and should contain one entry per required ref.
- `wait_for` must include every `producer_task_id` referenced by `reference_bindings`.
- `params.subject_refs` should mirror the scene continuity refs, but `reference_bindings` remains the executable ref-resolution truth.
- Do not emit an `imgs-to-img` task with only prompt text plus loose prose about refs.

Recommended shape:

```json
{
  "task_id": "T_IMG_S04",
  "stage": "P2",
  "task_type": "keyframe_image",
  "tool": "imgs-to-img",
  "input_refs": ["REF_XZ", "REF_XY", "REF_BALL"],
  "reference_bindings": [
    {
      "ref_id": "REF_XZ",
      "producer_task_id": "T_CHAR_XZ",
      "expected_output_id": "CHAR_XZ_REF",
      "asset_type": "reference_image",
      "usage_role": "character",
      "required": true
    },
    {
      "ref_id": "REF_XY",
      "producer_task_id": "T_CHAR_XY",
      "expected_output_id": "CHAR_XY_REF",
      "asset_type": "reference_image",
      "usage_role": "character",
      "required": true
    },
    {
      "ref_id": "REF_BALL",
      "producer_task_id": "T_PROP_BALL",
      "expected_output_id": "PROP_BALL_REF",
      "asset_type": "reference_image",
      "usage_role": "prop",
      "required": true
    }
  ],
  "wait_for": ["T_CHAR_XZ", "T_CHAR_XY", "T_PROP_BALL"],
  "params": {
    "prompt": "",
    "aspect_ratio": "16:9",
    "subject_refs": ["REF_XZ", "REF_XY", "REF_BALL"]
  },
  "dynamic_params": {},
  "expected_outputs": ["IMG_S04"]
}
```

## Dialogue and Kling Rules

- For `kling_native` dialogue, use `task_type: native_dialogue_video`.
- For `kling_native` dialogue, the motion task prompt must include the exact spoken Chinese line.
- Include: `The character says exactly this line in Chinese: 「...」`.
- Include: `Do not say any other words and do not speak any other language.`
- Kling duration must be an integer from `3` to `15`.
- Short dialogue scenes should usually request `5s`; longer dialogue can use `6s`.
- If `render_hints.requested_source_window_sec` is present for a dialogue scene, use that value as the requested motion duration and keep it integer-safe for Kling.

## Quality Checks

Before returning, check:

- output is valid JSON only
- all tasks have stable `task_id`, `stage`, `task_type`, `tool`, and `wait_for`
- every dynamic value such as `voice_id` has a producing task and consuming task reference
- if `storyboard.json` defines referenced recurring characters, `P0` includes matching `character_reference` tasks
- if `storyboard.json` does not define referenced recurring characters, no unnecessary `character_reference` task was invented
- task selection respects scene `generation_mode` and the editor's final `primary_source_type`
- `motion_treatment` and `requested_source_window_sec` were compiled into task choice and params rather than dropped
- fallback source types were not expanded into unnecessary duplicate generation by default
- `P0` `character_reference` tasks use `tool: generate-img`
- `P1` `voiceover_tts` tasks use `tool: generate-tts` when the standard synchronous TTS path is selected
- `P2` `keyframe_image` tasks with reusable character or key-prop refs use `tool: imgs-to-img`
- `P2` `imgs-to-img` tasks declare concrete `input_refs`, structured `reference_bindings`, and matching producer dependencies rather than only a textual prompt
- other `P2` `keyframe_image` tasks use `tool: generate-img`
- `P3` `image_to_video` and `native_dialogue_video` tasks use `tool: generate-video`
- native dialogue tasks preserve exact-line speech constraints and alignment prerequisites
- `P4` audio tasks reflect scene sound design and project BGM policy when those are enabled
- no generation tool is executed inside the `asset-dag.json` artifact
- no `asset-manifest.json`, subtitle alignment, render input, or final video is produced inside the `asset-dag.json` artifact
