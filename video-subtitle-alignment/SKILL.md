---
name: video-subtitle-alignment
description: Use when the user asks to align dialogue subtitles, create subtitle-alignment.json, sync captions to native video speech, or prepare subtitles for dialogue_only or mixed AI video renders.
version: 1.1.0
metadata:
  hermes:
    tags: [creative, video, subtitles, alignment, dialogue]
    related_skills: [video-production-planner, video-sound-designer, video-asset-executor, video-remotion-renderer, video-qa]
---

# AI Video Subtitle Alignment

Use this role skill between asset execution and Remotion render when native dialogue video needs subtitle timing.

If this skill is loaded by `video-production-planner`, follow the planner's `video_spec` and protocol contracts.

## Execution Modes

### Direct invocation

When the user invokes `video-subtitle-alignment` directly, return only `subtitle-alignment.json` and stop.

### Planner-orchestrated invocation

When `video-production-planner` loads this skill with `orchestration_mode: planner_orchestrated`, the JSON-only rule below applies only to the `subtitle-alignment.json` artifact. After the artifact is complete, follow the planner's remaining stages. Continue to `video-remotion-renderer` when render is requested; continue to QA when render is not requested or a render dependency is missing.

## Role Boundary

Subtitle alignment owns mapping dialogue text to actual speaking windows in the executed scene media. It compiles script truth, edit truth, and asset truth into subtitle timing truth. It does not rewrite dialogue, change scene order, regenerate video, change edit duration, or render exports.

## Inputs

Required:

- `storyboard.json`
- `edit-plan.json`
- `asset-manifest.json`

Optional:

- `run-report.json`
- existing `subtitle-alignment.json`
- extracted audio tracks
- forced alignment or ASR tooling

Use each input for a different truth:

- `storyboard.json` provides dialogue text and speaker truth.
- `edit-plan.json` provides which scenes actually require `dialogue_alignment`.
- `asset-manifest.json` provides the actual media asset path, duration, and asset identity to align against.
- `run-report.json` explains whether a required dialogue asset is blocked, failed, or missing.

## Output

For direct invocation, return only valid JSON for `subtitle-alignment.json` and do not wrap it in Markdown. For planner-orchestrated invocation, the `subtitle-alignment.json` artifact itself must be valid JSON; the planner may continue with later artifact sections afterward.

Required shape:

```json
{
  "project_id": "",
  "status": "success | partial | blocked | not_requested",
  "version": 1,
  "generated_at": "",
  "alignment_method": "silence_detection | forced_alignment | asr_alignment | not_run",
  "scenes": [
    {
      "scene_id": "S_01",
      "status": "aligned | blocked | skipped",
      "source_asset_id": "",
      "source_audio_asset_id": "",
      "mode": "dialogue",
      "speaker_ref": "",
      "source_text": "",
      "confidence": 0.0,
      "blocked_reason": "",
      "cues": [
        {
          "start_sec": 0,
          "end_sec": 0,
          "text": ""
        }
      ]
    }
  ]
}
```

## When To Use

Enable when:

- workflow mode is `dialogue_only`
- workflow mode is `mixed` and a scene has `audio.audio_type = dialogue`
- `edit-plan.json` uses `voice_render_mode = kling_native`
- scene `subtitle_strategy.source = dialogue_alignment`
- scene `scene_id` appears in `global_audio_plan.alignment_required_scene_ids`

Skip when:

- workflow mode is `narration_only`
- all voice is `remotion_tts`
- subtitles are not requested and the planner marked them `not_requested`

## Scene Selection Rules

- Determine required dialogue-alignment scenes from `edit-plan.json`, not from workflow mode alone.
- A scene should normally be aligned only when both are true:
  - the scene uses native dialogue media
  - `subtitle_strategy.source = dialogue_alignment` or the scene appears in `global_audio_plan.alignment_required_scene_ids`
- If no scene requires dialogue alignment, return `subtitle-alignment.json` with `status = not_requested` rather than inventing empty dialogue cues.

## Asset Resolution Rules

- Use `asset-manifest.json` as the media truth for alignment.
- Prefer scene assets with:
  - matching `scene_id`
  - `type = video`
  - `role = dialogue_video` first, then `scene_video`
  - `status = generated` or `provided`
- If a separate extracted dialogue audio asset exists, it may be used as `source_audio_asset_id`, but the cue timing still belongs to the scene media that render will use.
- Do not align against hypothetical media that never materialized. If the required scene asset is blocked, failed, or missing, record that explicitly instead of guessing timings from script length.

## Alignment Rules

- Do not average subtitle timing across a scene.
- Text truth comes from `storyboard.json` dialogue text.
- Timing truth comes from the executed scene asset in `asset-manifest.json` or its extracted audio.
- Minimum usable method: extract audio, detect speaking/silence windows, map script text to those windows.
- Better methods such as forced alignment or ASR alignment may replace the minimum method when available.
- `speaker_ref` should mirror the speaking role from `storyboard.json` or `edit-plan.json` audio strategy when available.
- If the scene asset duration is longer than the final scene duration from `edit-plan.json`, the alignment output should represent the portion intended for final use. If that trim window cannot be inferred reliably, mark the scene `blocked` instead of emitting misleading cue times.

## Blocked And Partial Rules

- If some required dialogue scenes can be aligned and others cannot, return `subtitle-alignment.json` with `status = partial`.
- If no required dialogue scene has a usable asset truth, return `missing_inputs_report` when the absence is a hard dependency problem, or `subtitle-alignment.json` with `status = blocked` when the scene-level blocker is the meaningful persisted truth.
- Use `run-report.json` to explain blocked upstream media generation when available.
- A blocked scene entry should preserve `scene_id`, `source_text`, and `blocked_reason` even when no cues can be emitted.

## Quality Checks

Before returning, check:

- every required native dialogue scene is either aligned or explicitly blocked/skipped
- aligned scenes have at least one cue
- cue windows stay within the usable scene window from `edit-plan.json`
- source text matches the dialogue text from `storyboard.json`
- asset IDs point to real entries from `asset-manifest.json`
- confidence is recorded
- no render input or final video is produced inside the `subtitle-alignment.json` artifact
