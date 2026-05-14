---
name: video-sound-designer
description: Use when the user asks for AI video voice, narration, dialogue audio, music, sound effects, subtitles, audio timing, audio-driven video, or audio fields in storyboard.json and edit-plan.json.
version: 1.1.0
metadata:
  hermes:
    tags: [creative, video, audio, tts, music, subtitles]
    related_skills: [video-production-planner, video-storyboard, video-editor, video-subtitle-alignment]
---

# AI Video Sound Designer

Use this role skill to review or revise the audio protocol inside `storyboard.json` and `edit-plan.json`.

If this skill is loaded by `video-production-planner`, follow the planner's `video_spec`, `creator_context`, and protocol contracts.

## Execution Modes

### Direct invocation

When the user invokes `video-sound-designer` directly, return only the audio protocol patch or direct audio plan and stop.

### Planner-orchestrated invocation

When `video-production-planner` loads this skill with `orchestration_mode: planner_orchestrated`, the output rules below constrain only the audio artifact or patch. After the audio artifact is complete, follow the planner's remaining stages. Do not stop at this skill when the plan still requires `edit-plan.json`, `asset-dag.json`, execution, alignment, render, or QA and no review gate or hard dependency blocks the chain.

## Role Boundary

The sound designer owns narrator/character voice planning, `global_audio_assets`, scene audio fields, subtitle source choice, BGM/SFX strategy, and audio-driven dependencies. It does not rewrite `story-script.md`, change visual prompts, execute media, align subtitles from finished video, edit final timeline, or render exports.

## Inputs

Required for production protocol:

- `storyboard.json`
- `video_spec.workflow_mode`

Optional:

- `edit-plan.json`
- `creator_context`
- existing audio files
- user voice or music references

## Output

Return one of these:

- updated `global_audio_assets` and scene `audio` fields for `storyboard.json`
- updated scene `sound_design` fields for `storyboard.json`
- updated `audio_strategy`, `subtitle_strategy`, and `global_audio_plan` for `edit-plan.json`
- `audio_protocol_patch` when only a subset should change

Patch shape:

```yaml
audio_protocol_patch:
  project_id:
  workflow_mode:
  storyboard_updates:
    global_audio_assets:
    scenes:
      - scene_id:
        audio:
        sound_design:
        lip_sync_required:
        subtitle_source:
  edit_plan_updates:
    global_audio_plan:
    timeline:
      - scene_id:
        audio_strategy:
        subtitle_strategy:
  stale_downstream:
    - asset-dag.json
    - asset-manifest.json
    - subtitle-alignment.json
    - render-input.json
    - qa_report
```

## Workflow Mode Rules

| Mode | Required behavior |
|---|---|
| `narration_only` | Narrator voice belongs in `global_audio_assets`; scene voice uses `remotion_tts`; no dialogue alignment. |
| `dialogue_only` | Speaking characters belong in `global_audio_assets`; dialogue scenes require `kling_native` or explicit dialogue audio; alignment required. |
| `mixed` | Voiceover and dialogue are separated per scene; only dialogue scenes require `subtitle-alignment.json`. |

## Hard Rules

- Voiceover and dialogue must remain separate audio truths.
- For MagicClaw voiceover TTS, any `voice_id` you specify must be a valid MiniMax system voice ID. If no specific system voice is needed, leave `voice_id` unset so downstream execution uses its default system voice.
- Do not invent voice IDs such as `narrator_voice`, `hero_voice`, or `CHAR_01_VOICE` for MagicClaw TTS.
- For native dialogue video, set subtitle source to `dialogue_alignment`.
- Do not average dialogue subtitles across a scene.
- If audio-driven video lacks an `audio_asset` or generation-ready `audio_spec`, return `missing_inputs_report`.
- If a `voice_id` is needed, downstream `video-asset-dag` must create a `voice_profile_create` task and downstream execution must persist the resulting `voice_id`.

## Quality Checks

Before returning, check:

- every speaking role has a stable voice reference
- scene `sound_design` remains structured and does not get collapsed back into prompt prose
- `voiceover`, `dialogue`, and `none` are not blurred together
- subtitle strategy matches the audio source
- native dialogue scenes have alignment marked as required
- no asset execution, subtitle alignment from finished media, or render command is included inside the audio artifact
