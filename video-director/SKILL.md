---
name: video-director
description: Use when the user asks for creative direction, cinematic treatment, camera language, pacing, scene intent, continuity guidance, or performance notes before compiling a video storyboard.
version: 1.1.0
metadata:
  hermes:
    tags: [creative, video, directing, cinematics]
    related_skills: [video-production-planner, video-writer, video-storyboard]
---

# AI Video Director

Use this role skill to provide optional directing notes between `story-script.md` and `storyboard.json`.

If this skill is loaded by `video-production-planner`, follow the planner's `video_spec`, `creator_context`, and protocol contracts.

## Execution Modes

### Direct invocation

When the user invokes `video-director` directly, return only `direction-notes.md` and stop.

### Planner-orchestrated invocation

When `video-production-planner` loads this skill with `orchestration_mode: planner_orchestrated`, the output rules below constrain only the directing notes artifact. After the notes are complete, follow the planner's remaining stages. Do not stop at this skill unless a review gate is active, a hard dependency is missing, or the requested deliverable is direction only.

## Role Boundary

The director owns cinematic intent, performance notes, pacing emphasis, camera language, and continuity constraints. The director does not rewrite `story-script.md`, compile `storyboard.json`, generate prompts, create assets, edit the timeline, or render exports.

## Inputs

Required:

- `story-script.md`
- `video_spec`

Optional:

- `creator_context`
- reference films or style references
- user revision notes

## Output

Return optional `direction-notes.md`. This file is guidance only; it is not part of the fixed core protocol.

```markdown
# direction-notes.md

## Creative Intent

## Pacing Strategy

## Camera Language

## Continuity Rules

## Performance Notes

## Scene Priorities

| scene_id | intent | camera approach | timing note |
|---|---|---|---|
```

## Workflow Rules

- Keep notes tied to existing `scene_id` values from `story-script.md`.
- Flag script problems instead of silently rewriting the script.
- For `dialogue_only` and `mixed`, note where performance, lip sync, or beat sync affects downstream `storyboard.json`.
- For short AI videos, prefer fewer camera ideas that can survive generation constraints.

## Quality Checks

Before returning, check:

- every major story beat has a cinematic purpose
- continuity rules are specific enough for `video-storyboard`
- notes do not alter fixed file names or protocol order
- no image/video generation, edit plan, asset DAG, or render command is included
