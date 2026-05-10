---
name: video-qa
description: Use when the user asks to review, validate, inspect, approve, or troubleshoot an AI video protocol chain, storyboard.json, edit-plan.json, asset-dag.json, media assets, subtitle alignment, render input, or final video.
version: 1.2.0
metadata:
  hermes:
    tags: [creative, video, qa, review, validation, protocol]
    related_skills: [video-production-planner, video-writer, video-storyboard, video-editor, video-asset-dag, video-asset-executor, video-subtitle-alignment, video-remotion-renderer]
---

# AI Video QA

Use this role skill to evaluate AI video protocol files and produce targeted revision tasks.

If this skill is loaded by `video-production-planner`, follow the planner's `video_spec`, `creator_context`, and protocol contracts.

## Execution Modes

### Direct invocation

When the user invokes `video-qa` directly, return only `qa_report`.

### Planner-orchestrated invocation

When `video-production-planner` loads this skill with `orchestration_mode: planner_orchestrated`, return `qa_report` as the final quality artifact for the current plan, unless the planner has a user-facing final summary requirement after QA.

## Role Boundary

QA owns checks, blockers, risk labels, and revision tasks. QA does not silently fix artifacts, rewrite scripts, regenerate media, edit timelines, align subtitles, or render exports. The planner decides which role handles each revision.

## Inputs

Use whichever protocol files exist for the current stage:

- `story-script.md`
- `storyboard.json`
- `edit-plan.json`
- `asset-dag.json`
- `asset-manifest.json`
- `run-report.json`
- `subtitle-alignment.json`
- `render-input.json`
- `render-report.json`
- `final.mp4`

Optional:

- `video_spec`
- `creator_context`
- user acceptance criteria

## Output

Return `qa_report`:

```yaml
qa_report:
  passed: true | false
  summary:
  protocol_files:
    - name:
      status: present | missing | not_requested | stale
  checks:
    - name:
      status: pass | fail | warning | not_applicable
      evidence:
      affected_artifacts:
  blockers:
    - issue:
      required_revision_role:
      suggested_action:
  revision_tasks:
    - role:
      input_refs:
      expected_output:
      reason:
```

## Protocol Checklist

Evaluate what exists:

- fixed filenames are present or explicitly `not_requested`
- `story-script.md` scenes have `scene_id`, `story_role`, `duration_hint_sec`, `subject_refs`, `location_ref`, `audio_type`, `speaker`, `visual`, dialogue/voiceover, and `SFX`
- `storyboard.json` has required top-level fields
- recurring characters, locations, and voices are registered globally with stable IDs
- `storyboard.json` scene refs point to registered asset IDs rather than raw free-text names
- `storyboard.json` scenes include explicit `generation_mode`, `motion_intensity`, `sound_design`, `negative_constraints`, and `reference_requirements`
- `image_prompt` is a still-image description rather than a sequence
- `video_prompt` continues from the `image_prompt` moment and carries motion/camera information when needed
- dialogue prompts include exact spoken Chinese lines when native dialogue video is used
- `edit-plan.json` timeline includes every scene once
- `edit-plan.json` source strategy follows scene `generation_mode`
- image-first scenes are `<= 2.0s`
- dialogue scenes use `dialogue_alignment`
- `asset-dag.json` dependencies are valid
- `asset-dag.json` task selection respects scene `generation_mode`
- Kling durations are integers from `3` to `15`
- `asset-manifest.json` preserves expected asset IDs, media metadata, and recoverable dynamic values
- `run-report.json` preserves task status, blocked reasons, and retry state
- `subtitle-alignment.json` references real aligned scene assets and preserves blocked reasons when required scenes could not be aligned
- dialogue subtitles are aligned by speaking windows, not scene averages
- `render-input.json` follows `edit-plan.json`, `asset-manifest.json`, and `subtitle-alignment.json` when required
- `render-report.json` exposes explicit blockers when render-critical assets or subtitle truth are missing
- `final.mp4` matches duration, aspect ratio, subtitle, and audio requirements when present

## Workflow Rules

- Use `not_applicable` when a check belongs to a later stage.
- Produce revision tasks with the smallest affected role.
- If one scene fails, target that scene instead of restarting the full project.
- If story meaning changes, mark downstream protocol files stale.
- Do not approve final export when blockers remain.

## Quality Checks

Before returning, check:

- every blocker maps to a role and protocol artifact
- warnings are separate from blocking failures
- no hidden changes were made to project artifacts
- the report gives the planner enough information to route revisions
