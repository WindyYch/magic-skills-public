---
name: video-production-planner
description: Use when the user asks to create, produce, plan, revise, storyboard, or generate an AI video, short film, music video, narrative video, or says phrases like help me create a video, generate a video, make a short film, 帮我创建一个视频, 生成视频, or 做一个短片.
version: 1.2.0
metadata:
  hermes:
    tags: [creative, video, ai-video, production, planner]
    related_skills:
      - video-writer
      - video-director
      - video-storyboard
      - video-art-director
      - video-sound-designer
      - video-editor
      - video-asset-dag
      - video-asset-executor
      - magicclaw-generate-tts
      - magicclaw-generate-img
      - magicclaw-imgs-to-img
      - magicclaw-generate-video
      - magicclaw-generate-music
      - video-subtitle-alignment
      - magicclaw-compose-video
      - video-qa
---

# AI Video Production Planner

Use this as the entry skill for AI video production tasks. It is a conversation-loaded planner, not a runtime DAG engine. The production core is the fixed Claw-style file protocol.

## Core Rule

The planner is the only dispatcher. Role skills do not call each other. Role skills return protocol artifacts to the planner, and the planner decides which role skill is needed afterward.

When the user asks for a full video, load role skills only when their stage is reached. When the user asks for one stage, load only the required role skill.

Do not perform writer, director, storyboard, art, sound, editor, asset DAG, asset execution, subtitle alignment, video composition submit/poll, or QA work until the corresponding role skill has been loaded. If a stage needs external media generation but no concrete tool is available, produce the protocol artifact and stop before the external action.

Concrete media helpers do not replace protocol stages. When execution reaches concrete media generation and Hermes has the relevant helper skills installed, route that work through `video-asset-executor`, which may use `magicclaw-generate-tts` for `voiceover_tts` assets, `magicclaw-generate-img` for plain still/reference images, `magicclaw-imgs-to-img` for reference-conditioned keyframes that must visibly preserve character or key-prop refs, `magicclaw-generate-video` for motion clips, and `magicclaw-generate-music` for generated BGM/music.

The planner must respect persisted stage truth, not optimistic assumptions:

- `asset-manifest.json` is the asset truth for anything downstream of `asset-dag.json`. It must exist immediately after the DAG handoff, before concrete media tools finish, with asset entries for declared outputs, but no top-level task list and no task status fields.
- `run-report.json` is the execution truth for whether each task is pending, running, succeeded, partially succeeded, blocked, failed, or skipped.
- `subtitle-alignment.json` is the subtitle timing truth for dialogue scenes that require alignment.
- `compose-video-result.json` is the composition truth; do not infer composition success from the existence of `video-orchestrator-param.json` alone.

## Orchestration Modes

Use one of these modes in every plan:

```yaml
orchestration_mode: direct_stage | planner_orchestrated
```

### `direct_stage`

Use when the user directly invokes a role skill or asks for only one file. The selected role skill returns its file and stops.

### `planner_orchestrated`

Use when the user invokes `video-production-planner` for a full chain or asks to continue through multiple files.

In `planner_orchestrated` mode:

- Role skill output rules constrain only that role's artifact block.
- A role skill saying "return only valid JSON" means the JSON artifact must be valid; it does not mean the whole planner response must stop there.
- After each artifact, immediately continue to the next required stage when no review gate or hard dependency blocks it.
- Do not stop after `story-script.md`, `storyboard.json`, `edit-plan.json`, or `asset-dag.json` just because that role artifact is complete.
- Stop only when a planned review gate is active, a hard dependency is missing, a concrete execution tool is unavailable, or the requested deliverable has been reached.
- If the user says "不暂停确认", "no review", "continue", or "specs only", set review gates to `skipped` for story and storyboard/edit unless safety or missing inputs block the chain.

## Production Protocol

Use these fixed files as the production truth:

```text
story-script.md
storyboard.json
edit-plan.json
asset-dag.json
asset-manifest.json
run-report.json
subtitle-alignment.json
video-orchestrator-param.json
compose-video-result.json
```

The middle chain must stay stable:

```text
brief
-> story-script.md
-> storyboard.json
-> edit-plan.json
-> asset-dag.json
-> asset-manifest.json + run-report.json
-> subtitle-alignment.json when dialogue alignment is required
-> video-orchestrator-param.json + compose-video-result.json
-> qa_report
```

Do not rename protocol files. If a file is not produced because the user requested specs only, mark it as `not_requested` or `blocked`, rather than inventing a substitute file.

## Supporting References

Load only the reference needed for the current decision:

- `references/claw-production-protocol.md`: fixed file chain, workflow modes, and hard production rules.
- `references/capabilities.md`: abstract capability names and role permissions.
- `references/workflow-variants.md`: full video, direct-stage, revision, and audio-driven flows.
- `references/artifact-contracts.md`: output schemas, missing-input report, stale artifact rules.
- `references/memory-policy.md`: creator memory read/write rules and templates.
- `references/test-cases.md`: pressure scenarios for validating these skills.

## Role Skills

| Stage | Skill | Main output |
|---|---|---|
| Planning | `video-production-planner` | `production_plan`, `video_spec`, `creator_context` |
| Writing | `video-writer` | `story-script.md` |
| Direction | `video-director` | optional `direction-notes.md` for storyboard guidance |
| Storyboard and AV compile | `video-storyboard` | `storyboard.json` |
| Visual protocol review | `video-art-director` | `storyboard.json` visual sections or visual patch |
| Sound protocol review | `video-sound-designer` | `global_audio_assets`, scene audio fields, audio strategy patch |
| Edit planning | `video-editor` | `edit-plan.json` |
| Asset DAG | `video-asset-dag` | `asset-dag.json` |
| Asset execution | `video-asset-executor` | `asset-manifest.json`, `run-report.json`, complete media assets; may use `magicclaw-generate-tts`, `magicclaw-generate-img`, `magicclaw-imgs-to-img`, `magicclaw-generate-video`, and `magicclaw-generate-music` when concrete helpers are available |
| Subtitle alignment | `video-subtitle-alignment` | `subtitle-alignment.json` |
| Video composition | `magicclaw-compose-video` | `video-orchestrator-param.json`, `compose-video-result.json` |
| QA | `video-qa` | `qa_report`, `revision_tasks` |

## Standard Full Video Flow

For a full AI short film:

1. Create `creator_context` from memory when available.
2. Create `video_spec`: duration, aspect ratio, language, workflow mode, target deliverables, generation policy.
3. Present `production_plan` for user review unless the user explicitly asked to skip planning confirmation.
4. **REQUIRED ROLE SKILL:** load `video-writer` for `story-script.md`.
5. Pause for story review unless the user explicitly said no review and no missing-input risk exists.
6. **OPTIONAL ROLE SKILL:** load `video-director` when cinematic treatment, continuity, or performance notes are needed before compile.
7. **REQUIRED ROLE SKILL:** load `video-storyboard` to compile `story-script.md` into `storyboard.json`.
8. **OPTIONAL ROLE SKILL:** load `video-art-director` to review or revise visual fields in `storyboard.json`.
9. **OPTIONAL ROLE SKILL:** load `video-sound-designer` to review or revise `global_audio_assets`, scene audio, and subtitle strategy.
10. **REQUIRED ROLE SKILL:** load `video-editor` to compile `storyboard.json` into `edit-plan.json`.
11. Pause for storyboard/edit review unless the user explicitly said no review and no missing-input risk exists.
12. **REQUIRED ROLE SKILL:** load `video-asset-dag` to compile `storyboard.json + edit-plan.json` into `asset-dag.json`.
13. If media generation is requested, treat completed `asset-dag.json` as the execution handoff point: the DAG should declare concrete execution tasks such as `voiceover_tts`, still/keyframe generation, dependent motion clips, and generated BGM when requested. Immediately after this handoff, before any concrete media helper is called, `video-asset-executor` must initialize both `asset-manifest.json` and `run-report.json` from the DAG. The manifest records only asset entries for declared outputs, optionally including producing `task_id` as lineage, but never a top-level `tasks` array; the run report records each DAG `task_id`, `tool`, `expected_outputs`, `status: pending`, `attempts: 0`, and `provider_task_id: null`. When MagicClaw TTS is the concrete voice helper, `voiceover_tts` should route through `magicclaw-generate-tts`. When a `keyframe_image` must visibly preserve recurring character or key-prop refs, it should route through `magicclaw-imgs-to-img` instead of plain `magicclaw-generate-img`.
14. **REQUIRED ROLE SKILL WHEN EXECUTING MEDIA:** load `video-asset-executor` to read `asset-dag.json`, initialize `asset-manifest.json + run-report.json`, execute those tasks, update asset facts in the manifest, and update task status only in the run report. `asset-manifest.json` should default to a complete runtime asset list with final asset IDs, optional producing `task_id`, and first-class remote `url` fields for generated images, audio, and video whenever providers return stable URLs. `run-report.json` should default to a complete runtime task list with current per-task `status`, `attempts`, provider/API returned `provider_task_id`, `output_asset_ids`, blocker/error fields, and retry state. In concrete execution paths, this may call `magicclaw-generate-tts`, `magicclaw-generate-img`, `magicclaw-imgs-to-img`, `magicclaw-generate-video`, and `magicclaw-generate-music`.
15. After asset execution, inspect `run-report.json` and `asset-manifest.json`. If execution is `blocked` or composition-critical outputs are missing, do not continue to subtitle alignment or final composition as if media exists; route to QA or return the blocker state.
16. **CONDITIONAL ROLE SKILL:** load `video-subtitle-alignment` when `edit-plan.json` marks one or more scenes with `subtitle_strategy.source = dialogue_alignment` or lists them in `global_audio_plan.alignment_required_scene_ids`.
17. If `subtitle-alignment.json` is required but returns `blocked` or blocks any required dialogue scene, do not continue to final composition unless the user explicitly accepts a subtitle-free export.
18. **REQUIRED ROLE SKILL WHEN COMPOSING FINAL VIDEO:** load `magicclaw-compose-video` only when final composition is requested and the available asset truth plus required subtitle truth are sufficient to build a valid `video-orchestrator` submission. The caller must first prepare canonical `video-orchestrator-param.json` with `job_kind = render_from_edit_assets`, `schema_version`, `project`, `timeline.scenes`, `assets.items`, optional subtitle alignment payload, and `render_options`. Keep `input_protocol = video_remotion_renderer` and `input_protocol_version = v1` inside the canonical param unless the compose API contract changes, because those are payload fields expected by the current `magicclaw-compose-video` interface, not a signal to route back to any older local-render stage. Persist the submit/query result as `compose-video-result.json` and treat its top-level `task_id`, `status`, and `video_url` as the composition truth.
19. **REQUIRED ROLE SKILL:** load `video-qa` before final approval.

## Direct Mode

If the user asks for only one output, choose the smallest valid chain:

| User request | Minimum chain |
|---|---|
| Script only | `video-writer` |
| Storyboard JSON from brief | `video-writer` then `video-storyboard` |
| Storyboard from existing script | `video-storyboard` |
| Storyboard to generated scene images and clips | `video-storyboard` then `video-editor` then `video-asset-dag` then `video-asset-executor` |
| Visual prompt review from storyboard | `video-art-director` |
| Music, voice, subtitle, or audio strategy only | `video-sound-designer` |
| Edit plan only | `video-editor` |
| Asset DAG only | `video-asset-dag` |
| Execute assets from DAG | `video-asset-executor` |
| Generate a still reference or keyframe only | `magicclaw-generate-img` or `magicclaw-imgs-to-img` depending on reference needs |
| Animate an existing still into a clip | `magicclaw-generate-video` |
| Align dialogue subtitles | `video-subtitle-alignment` |
| Compose final video from manifest and edit plan | `video-subtitle-alignment` when required, then `magicclaw-compose-video`, then `video-qa` |
| QA an existing plan or export | `video-qa` |

## Hard Dependencies

Do not start a stage when its required input is missing. Load `references/artifact-contracts.md` for the missing-input report shape.

For `dialogue_only` or `mixed` projects using native dialogue video, subtitle alignment is required after asset execution and before final composition. Do not let downstream composition average dialogue subtitles across a scene.

For final composition:

- `edit-plan.json` is necessary but not sufficient.
- `asset-manifest.json` must contain composition-ready scene assets for every required timeline scene.
- `run-report.json` must not leave required composition assets in a blocked or failed state.
- when a scene requires `dialogue_alignment`, `subtitle-alignment.json` must provide usable subtitle truth for that scene or an explicit user-approved exception must exist.
- `video-orchestrator-param.json` must be assembled from current edit truth, asset truth, and subtitle truth before `magicclaw-compose-video` is called.

For audio-driven video, audio must be prepared before video generation. Load `references/workflow-variants.md` for the audio-driven flow.

For image-to-video execution, `magicclaw-generate-video` requires a source image. The source may come from user-provided art or from a prior `magicclaw-generate-img` or `magicclaw-imgs-to-img` output referenced in `asset-manifest.json`.

## Plan Output

Start production tasks with this compact shape:

```yaml
production_plan:
  mode: full_video | direct_stage | revision
  workflow_mode: narration_only | dialogue_only | mixed
  orchestration_mode: direct_stage | planner_orchestrated
  creator_context_used: true | false
  user_confirmation_required: true | false
  fixed_outputs:
    - story-script.md
    - storyboard.json
    - edit-plan.json
    - asset-dag.json
    - asset-manifest.json
    - run-report.json
    - subtitle-alignment.json
    - video-orchestrator-param.json
    - compose-video-result.json
  stages:
    - stage: story_script
      skill: video-writer
      inputs: [brief, video_spec, creator_context]
      outputs: [story-script.md]
      review_gate: story_review
      status: pending
  hard_dependencies:
    - target: asset-dag.json
      requires: [storyboard.json, edit-plan.json]
      if_missing: return missing_inputs_report
    - target: subtitle-alignment.json
      requires: [storyboard.json, edit-plan.json, asset-manifest.json]
      when: one or more scenes require subtitle_strategy.source = dialogue_alignment
      if_missing: return missing_inputs_report
    - target: video-orchestrator-param.json
      requires: [edit-plan.json, asset-manifest.json]
      when: generation_policy is render_final
      if_missing: return missing_inputs_report
    - target: video-orchestrator-param.json
      requires: [edit-plan.json, asset-manifest.json, subtitle-alignment.json]
      when: generation_policy is render_final and one or more scenes require subtitle_strategy.source = dialogue_alignment
      if_missing: return missing_inputs_report
    - target: compose-video-result.json
      requires: [video-orchestrator-param.json]
      when: generation_policy is render_final
      if_missing: return missing_inputs_report
  skipped_stages:
    - stage: asset_execution
      reason: user requested specs only
```

Use this plan as the working contract for the rest of the conversation.
