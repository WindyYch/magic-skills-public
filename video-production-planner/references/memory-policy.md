# AI Video Production Memory Policy

Use memory for durable creator preferences and compact project history. Do not store full protocol files, raw scripts, prompt packs, or media assets in memory.

## Read Before Planning

Inspect memory already present in context for:

- `video_creator_profile`
- `recent_video_projects_digest`
- `recurring_series_context`

Build a compact `creator_context` artifact:

```yaml
creator_context:
  memory_found: true | false
  preferences:
    duration_sec:
    aspect_ratio:
    tones:
    review_style:
    dislikes:
  recent_projects:
    - project_id:
      title:
      genre:
      story_core:
      visual_style:
      workflow_mode:
      protocol_outputs:
        - story-script.md
        - storyboard.json
        - edit-plan.json
      user_feedback:
  avoid_repeating:
  reusable_series_context:
```

If no relevant memory exists, set `memory_found: false` and continue from the current brief.

## Write After Approval Or Export

Write memory only after final approval, export, or explicit user request. Store stable project references to protocol files, not the protocol files themselves.

Use `replace` when a matching memory entry is visible. Use `add` when there is no matching entry.

## `video_creator_profile` Template

```yaml
video_creator_profile:
  preferred_duration_sec:
  preferred_aspect_ratio:
  preferred_tones:
  preferred_formats:
  review_style:
  dislikes:
  recurring_constraints:
```

## `recent_video_projects_digest` Template

```yaml
recent_video_projects_digest:
  projects:
    - project_id:
      title:
      genre:
      duration_sec:
      aspect_ratio:
      workflow_mode:
      story_core:
      visual_style:
      user_feedback:
      project_ref:
      protocol_ref:
  avoid_repeating:
```

## Rules

- Store project IDs, workspace paths, or stable references, not raw media or full protocol JSON.
- Keep summaries short enough to fit memory budgets.
- Do not claim a user preference from one project unless it appears durable or the user says it is a preference.
- Do not reuse characters, worlds, or series continuity unless the current request implies a series or the user asks for reuse.
- Do not invent project history.
