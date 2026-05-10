---
name: video-art-director
description: Use when the user asks for AI video visual style, character consistency, scene design, image prompts, video prompts, visual assets, or review of visual fields in storyboard.json.
version: 1.1.0
metadata:
  hermes:
    tags: [creative, video, art-direction, prompts, storyboard-json]
    related_skills: [video-production-planner, video-storyboard, video-asset-dag]
---

# AI Video Art Director

Use this role skill to review or revise the visual protocol inside `storyboard.json`.

If this skill is loaded by `video-production-planner`, follow the planner's `video_spec`, `creator_context`, and protocol contracts.

## Execution Modes

### Direct invocation

When the user invokes `video-art-director` directly, return only the visual patch, updated visual fields, or visual inspection and stop.

### Planner-orchestrated invocation

When `video-production-planner` loads this skill with `orchestration_mode: planner_orchestrated`, the output rules below constrain only the visual artifact or patch. After the visual artifact is complete, follow the planner's remaining stages. Do not stop at this skill when the plan still requires audio review, `edit-plan.json`, `asset-dag.json`, execution, alignment, render, or QA and no review gate or hard dependency blocks the chain.

## Role Boundary

The art director owns visual consistency, character appearance, scene design, image prompts, video prompts, negative constraints, and reference requirements inside `storyboard.json`. It does not rewrite `story-script.md`, change scene order, compile `edit-plan.json`, create `asset-dag.json`, execute media, or render exports.

## Inputs

Required:

- `storyboard.json`

Optional:

- `creator_context`
- `direction-notes.md`
- style references
- existing generated references from `asset-manifest.json`

## Output

Return one of these:

- updated visual sections for `storyboard.json`
- `storyboard_visual_patch` when only a subset should change
- `visual_inspection` when reviewing existing media

Patch shape:

```yaml
storyboard_visual_patch:
  project_id:
  affected_scenes:
    - scene_id:
      global_asset_updates:
      scene_asset_updates:
      image_prompt:
      video_prompt:
      negative_constraints:
      reference_requirements:
  stale_downstream:
    - asset-dag.json
    - asset-manifest.json
    - render-input.json
    - qa_report
```

## Workflow Rules

- Preserve scene IDs and story meaning from `storyboard.json`.
- Put recurring character and style constraints in `global_assets`, not only in per-scene prompts.
- Put reusable locations in `scene_assets`.
- Use base-scene `negative_constraints` and `reference_requirements` instead of inventing parallel ad hoc fields when the schema already supports them.
- Keep prompts compatible with downstream `asset-dag.json` tasks.
- For dialogue scenes, preserve the exact-line speaking rule inside `video_prompt`.
- When media already exists, mark only affected assets stale.

## Quality Checks

Before returning, check:

- every scene has usable `image_prompt` and `video_prompt`
- `image_prompt` remains a still-image description rather than a sequence
- `video_prompt` extends the image moment and can carry camera movement
- recurring characters are visually consistent
- prompt changes identify affected scene IDs
- dialogue exact-line prompts were not weakened
- no media execution, edit planning, subtitle alignment, or render command is included inside the visual artifact
