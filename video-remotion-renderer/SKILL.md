---
name: video-remotion-renderer
description: Use when the user asks to render an AI video with Remotion, create render-input.json, assemble final.mp4, compile a final timeline from edit-plan.json and asset-manifest.json, or produce render-report.json.
version: 1.1.0
metadata:
  hermes:
    tags: [creative, video, remotion, render, export]
    related_skills: [video-production-planner, video-editor, video-asset-executor, video-subtitle-alignment, video-qa]
---

# AI Video Remotion Renderer

Use this role skill to compile Remotion input and render the final video from protocol files.

If this skill is loaded by `video-production-planner`, follow the planner's `video_spec` and protocol contracts.

## Execution Modes

### Direct invocation

When the user invokes `video-remotion-renderer` directly, return only render artifacts and stop.

### Planner-orchestrated invocation

When `video-production-planner` loads this skill with `orchestration_mode: planner_orchestrated`, the output rules below constrain only render artifacts. After render artifacts are complete, follow the planner's remaining stages. Continue to `video-qa` unless the user explicitly requested render input only.

## Role Boundary

The Remotion renderer owns render compilation truth: `render-input.json`, render execution when available, `render-report.json`, and `final.mp4`. It resolves timeline truth against persisted asset truth and subtitle truth. It does not reinterpret the story, change scene order, change prompts, regenerate media, or alter `edit-plan.json`.

## Inputs

Required:

- `edit-plan.json`
- `asset-manifest.json`

Optional:

- `subtitle-alignment.json`
- concrete Remotion render command or tool
- existing `render-input.json`

Use each input for a different truth:

- `edit-plan.json` provides scene order, scene duration, subtitle rules, transitions, and audio strategy.
- `asset-manifest.json` provides the concrete media assets and metadata that can actually be rendered.
- `subtitle-alignment.json` provides native dialogue subtitle timing truth when required.

## Outputs

Return:

- `render-input.json`
- `render-report.json`
- `final.mp4` when rendering is requested and tooling is available

`render-input.json` shape:

```json
{
  "project_meta": {},
  "timeline": [
    {
      "scene_id": "S_01",
      "order": 1,
      "duration_sec": 2,
      "duration_frames": 60,
      "visual_asset_id": "",
      "audio_asset_ids": [],
      "subtitle_mode": "audio_content | dialogue_alignment | none",
      "subtitle_ref": "",
      "transition_in": {},
      "transition_out": {}
    }
  ],
  "assets": [
    {
      "asset_id": "",
      "type": "image | video | voice | sfx | bgm | reference",
      "role": "",
      "path": "",
      "scene_id": "",
      "duration_sec": null
    }
  ],
  "subtitles": [
    {
      "scene_id": "S_01",
      "source": "audio_content | dialogue_alignment",
      "cues": []
    }
  ],
  "audio_mix": {
    "scene_audio": [],
    "bgm": {},
    "ducking": {}
  },
  "export": {
    "aspect_ratio": "9:16",
    "fps": 30
  }
}
```

`render-report.json` shape:

```json
{
  "project_id": "",
  "status": "success | blocked | failed | not_requested",
  "output": {
    "path": "final.mp4",
    "duration_sec": 0,
    "width": 0,
    "height": 0
  },
  "blockers": []
}
```

## Source Of Truth

- `edit-plan.json` is the timeline truth.
- `asset-manifest.json` is the asset truth.
- `subtitle-alignment.json` is the dialogue subtitle timing truth when present.

## Asset Resolution Rules

- Resolve each timeline scene to the concrete render asset using `asset-manifest.json`, not by re-inferring from prompts.
- Prefer visual assets in this order:
  - scene-level `video` assets with `role = dialogue_video` or `scene_video`
  - scene-level `image` assets with `role = keyframe`
  - other scene-bound assets only when the edit plan explicitly supports them
- Use asset `status = generated` or `provided` as renderable truth. Do not treat `failed`, `blocked`, or `not_requested` assets as renderable.
- If a required scene has no renderable visual asset, record a render blocker instead of silently omitting the scene.

## Subtitle Rules

- If `subtitle-alignment.json` exists, use it for dialogue scenes that require `dialogue_alignment`.
- Do not fall back to scene-average dialogue subtitles when alignment exists.
- If a dialogue scene requires `dialogue_alignment` and `subtitle-alignment.json` reports that scene as `blocked` or missing, rendering should normally be `blocked` unless the user explicitly accepts a subtitle-free export.
- For `narration_only`, voiceover subtitles can follow text and TTS timing.
- For `mixed`, process voiceover and dialogue separately.
- `render-input.json.subtitles` should preserve the source of truth per scene: `audio_content` for narration-style cues and `dialogue_alignment` for native dialogue cues.

## Audio Rules

- BGM may span the full video.
- BGM must duck under voiceover and native dialogue according to `edit-plan.json.global_audio_plan`.
- Native dialogue audio from generated video must remain attached to the dialogue scene unless the edit plan says otherwise.
- `render-input.json.audio_mix` should separate scene-attached audio, narration audio, SFX, and BGM well enough for downstream composition or inspection.
- When `asset-manifest.json` contains scene-specific SFX or narration assets, connect them to the matching scene rather than flattening them into a global unlabeled pool.

## Render Compilation Rules

- `render-input.json.timeline` should preserve every scene from `edit-plan.json` exactly once.
- `visual_asset_id` should identify the concrete render asset for that scene.
- `audio_asset_ids` should list all scene-relevant audio assets that actually participate in the mix for that scene.
- `subtitle_ref` should point to the matching subtitle scene entry or cue source when subtitles are enabled.
- `transition_in` and `transition_out` should compile from the scene transition strategy in `edit-plan.json`.
- `assets` should include only the concrete assets needed for the current render pass, not every historical artifact in the manifest.

## Render Rules

- If Remotion tooling is unavailable or the user requested specs only, write `render-input.json` and return `render-report.json` with `status = blocked` or `not_requested`.
- Do not modify upstream JSON to make render easier; report blockers instead.
- If render-critical assets or required subtitle alignment are missing, return `render-report.json` with `status = blocked` and explicit blocker entries.
- `render-report.json.blockers` should identify missing or unusable scene assets, blocked subtitle alignment, or inconsistent timing truth in a way QA can route back upstream.
- `final.mp4` must match duration and aspect ratio from `edit-plan.json` and `video_spec`.

## Quality Checks

Before returning, check:

- every timeline scene references an available asset
- every renderable scene resolves to a concrete `visual_asset_id`
- dialogue scenes use alignment when required
- subtitles do not exceed scene windows
- audio ducking is represented
- partial or blocked subtitle truth is reflected as a render blocker when required
- render report records success, blocker, or failure clearly
