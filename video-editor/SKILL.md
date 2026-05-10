---
name: video-editor
description: Use when the user asks for AI video editing, edit-plan.json, timeline assembly, clip order, source strategy, transitions, subtitle strategy, audio strategy, render settings, or final composition planning.
version: 1.2.0
metadata:
  hermes:
    tags: [creative, video, editing, timeline, edit-plan]
    related_skills: [video-production-planner, video-storyboard, video-sound-designer, video-asset-dag, video-remotion-renderer, video-qa]
---

# AI Video Edit Plan Compiler

Use this role skill to compile `storyboard.json` into `edit-plan.json`.

If this skill is loaded by `video-production-planner`, follow the planner's `video_spec`, `creator_context`, and protocol contracts.

## Execution Modes

### Direct invocation

When the user invokes `video-editor` directly, return only `edit-plan.json` and stop.

### Planner-orchestrated invocation

When `video-production-planner` loads this skill with `orchestration_mode: planner_orchestrated`, the JSON-only rule below applies only to the `edit-plan.json` artifact. After the artifact is complete, follow the planner's remaining stages. Do not stop at `edit-plan.json` when the plan still requires `video-asset-dag`, execution, alignment, render, or QA and no review gate or hard dependency blocks the chain.

## Role Boundary

The editor owns scene order, final scene duration, source selection, motion treatment, subtitle strategy, audio strategy, BGM strategy, transitions, and render-facing timeline hints. It compiles `storyboard.json` strategy into edit truth. It does not rewrite story, change prompts, create `asset-dag.json`, execute media, align subtitles from finished video, or render exports.

## Inputs

Required:

- `storyboard.json`

Optional:

- `video_spec`
- `creator_context`
- existing `edit-plan.json` to revise

Use storyboard scene metadata as edit inputs, especially:

- `generation_mode`
- `shot_type`
- `motion_intensity`
- `continuity_notes`
- `sound_design`
- `audio`
- `lip_sync_required`
- `subtitle_source`

## Output

For direct invocation, return only valid JSON for `edit-plan.json` and do not wrap it in Markdown. For planner-orchestrated invocation, the `edit-plan.json` artifact itself must be valid JSON; the planner may continue with later artifact sections afterward.

Required top-level fields:

```json
{
  "project_meta": {
    "project_id": "",
    "title": "",
    "workflow_mode": "narration_only",
    "aspect_ratio": "9:16",
    "fps": 30
  },
  "timeline": [],
  "global_audio_plan": {
    "bgm_strategy": {},
    "scene_sound_bed_policy": {},
    "alignment_required_scene_ids": []
  }
}
```

Each timeline item must include:

```json
{
  "scene_id": "S_01",
  "order": 1,
  "duration_sec": 2,
  "duration_frames": 60,
  "narrative_role": "",
  "video_strategy": {
    "generation_mode": "image_first | video_first | dialogue_native",
    "primary_source_type": "generated_image | generated_video | user_image | user_video | none",
    "fallback_source_type": "generated_video | generated_image | user_video | user_image | none",
    "motion_treatment": "still_hold | subtle_motion | full_motion | native_dialogue"
  },
  "audio_strategy": {
    "audio_type": "voiceover | dialogue | none",
    "voice_render_mode": "remotion_tts | kling_native | none",
    "speaker_ref": "",
    "needs_lip_sync": false,
    "use_scene_sound_design": true
  },
  "subtitle_strategy": {
    "enabled": true,
    "source": "audio_content | dialogue_alignment | none",
    "placement": "open_captions | none"
  },
  "transitions": {
    "in_type": "cut | dissolve | none",
    "out_type": "cut | dissolve | none",
    "reason": ""
  },
  "render_hints": {
    "shot_type": "",
    "motion_intensity": "static | subtle | active | performance",
    "continuity_direction": "",
    "requested_source_window_sec": 2,
    "source_override_reason": "",
    "audio_ducking_target": "voiceover | dialogue | both | none"
  }
}
```

## Scene Compilation Rules

- Preserve storyboard scene order unless the user explicitly asks for a re-edit.
- `narrative_role` should mirror scene `story_role`.
- `video_strategy.generation_mode` should mirror the scene `generation_mode`; the editor may override only the actual source choice when timing or speech constraints make the storyboard hint non-viable.

## Source Strategy Rules

- Use `storyboard.json` scene `generation_mode` as the first source-strategy hint.
- `generation_mode = image_first` should normally map to `primary_source_type = generated_image`, `fallback_source_type = generated_video`, and `motion_treatment = still_hold` or `subtle_motion`.
- `generation_mode = video_first` should normally map to `primary_source_type = generated_video`, `fallback_source_type = generated_image`, and a motion treatment that matches scene activity.
- `generation_mode = dialogue_native` should normally map to `primary_source_type = generated_video`, `fallback_source_type = none`, and `motion_treatment = native_dialogue`.
- Do not silently assign a native dialogue scene to an image source as if lip-synced speech can survive that downgrade.
- If an `image_first` scene contains speech, performance, or action that clearly cannot fit a short still-led cut, promote `primary_source_type` to `generated_video` and record the reason in `render_hints.source_override_reason`.

## Duration Rules

- Start from the storyboard scene `duration_hint_sec`, then refine it using `shot_type`, `motion_intensity`, `audio.text`, and `workflow_mode`.
- `duration_frames` must match `duration_sec` and the project FPS.
- `image_first` scenes should stay `<= 2.0s` in the final timeline unless the planner explicitly overrides; if that limit breaks the scene, prefer a source-strategy override over silently stretching the still-image scene.
- `shot_type` should influence pacing:
  - detail, insert, and cutaway shots are usually compact
  - wide or establishing beats may breathe slightly longer
  - close or medium performance coverage should preserve enough uninterrupted time for acting or speech
- `motion_intensity` should influence pacing:
  - `static` favors short, direct holds and clean cuts
  - `subtle` allows a gentle hold or small motion window
  - `active` needs enough time for visible motion completion
  - `performance` needs enough time for delivery, reaction, and lip sync
- If `audio.text` is present, the final cut must plausibly fit the spoken content. Do not strand a full sentence inside a `1s` or `2s` shot just because the storyboard hint started as `image_first`.
- `render_hints.requested_source_window_sec` is the downstream generation headroom hint:
  - for `image_first`, it usually matches `duration_sec`
  - for normal motion scenes, it may slightly exceed `duration_sec`
  - for `dialogue_native`, it should usually be `5` or `6` so downstream video generation can trim from a full spoken performance window

## Audio and Subtitle Rules

- Map scene audio directly from `storyboard.json` instead of re-inferring it from prose.
- `voiceover` scenes use `audio_type = voiceover`, `voice_render_mode = remotion_tts`, `needs_lip_sync = false`, and `subtitle_strategy.source = audio_content`.
- `dialogue` scenes using native video speech use `audio_type = dialogue`, `voice_render_mode = kling_native`, `needs_lip_sync = true`, and `subtitle_strategy.source = dialogue_alignment`.
- `none` scenes use `audio_type = none`, `voice_render_mode = none`, and `subtitle_strategy.enabled = false` unless the user explicitly wants subtitles for on-screen text only.
- `narration_only` projects do not require `subtitle-alignment.json`.
- `dialogue_only` and `mixed` projects require alignment for native dialogue scenes.
- `sound_design.sfx_notes` and `sound_design.ambience_notes` should survive into edit planning through `audio_strategy.use_scene_sound_design` and `global_audio_plan.scene_sound_bed_policy`.
- BGM must duck under voiceover and dialogue.
- Do not invent music mood inside `edit-plan.json`; keep music treatment structural.

## Continuity and Transition Rules

- `continuity_notes` are edit-relevant continuity truth, not storyboard-only decoration.
- Use `continuity_notes` to decide whether adjacent scenes should hard cut for continuity, soften the entry, or preserve a carry-over state such as wet clothing, broken props, screen content, or lighting change.
- When adjacent scenes continue the same location, action axis, or emotional beat, prefer simple `cut` transitions and note the continuity need in `render_hints.continuity_direction`.
- When a scene marks a reveal, memory shift, or time reset, a dissolve or softer transition may be justified, but do not add flashy transitions without a story reason.

## Shot And Motion Compilation

- `shot_type` should be carried into `render_hints.shot_type`.
- `motion_intensity` should be carried into both `video_strategy.motion_treatment` and `render_hints.motion_intensity`.
- `sound_design` should influence whether the cut expects scene ambience, emphasized SFX hits, or a cleaner music-led bed.

## Global Audio Plan Rules

- `global_audio_plan.bgm_strategy` should state whether BGM is enabled and that it ducks under `voiceover` and `dialogue`.
- `global_audio_plan.scene_sound_bed_policy` should preserve storyboard ambience and SFX intent instead of flattening every scene into narration plus music.
- `global_audio_plan.alignment_required_scene_ids` should list every scene whose subtitles depend on native dialogue alignment.

## Quality Checks

Before returning, check:

- output is valid JSON only
- every `storyboard.json` scene appears once in `timeline`
- `generation_mode`, `shot_type`, `motion_intensity`, `continuity_notes`, and `sound_design` were all compiled into edit decisions rather than dropped
- source strategy reflects scene `generation_mode` or documents a justified override
- image-first scenes are no longer than `2.0s` unless the planner explicitly overrides them
- `duration_sec` plausibly fits the spoken content
- dialogue subtitle strategy uses `dialogue_alignment`
- `global_audio_plan` preserves ducking and scene sound-bed intent
- no asset DAG, asset execution, subtitle alignment, or render work is attempted inside the `edit-plan.json` artifact
