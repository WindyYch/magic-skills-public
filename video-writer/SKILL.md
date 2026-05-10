---
name: video-writer
description: Use when the user asks to write or revise an AI video concept, synopsis, narration, dialogue, story beats, scene script, or story-script.md for a video production workflow.
version: 1.2.0
metadata:
  hermes:
    tags: [creative, video, writing, script, story-script]
    related_skills: [video-production-planner, video-director, video-storyboard]
---

# AI Video Writer

Use this role skill to produce `story-script.md`, the first fixed protocol file for an AI video project.

If this skill is loaded by `video-production-planner`, follow the planner's `video_spec`, `creator_context`, and protocol contracts.

## Execution Modes

### Direct invocation

When the user invokes `video-writer` directly, return only `story-script.md` and stop.

### Planner-orchestrated invocation

When `video-production-planner` loads this skill with `orchestration_mode: planner_orchestrated`, the output rules below constrain only the `story-script.md` artifact. After the script artifact is complete, follow the planner's remaining stages. Do not stop at this skill unless a story review gate is active, a hard dependency is missing, or the requested deliverable is script only.

## Role Boundary

The writer owns story, scene script, narration, dialogue, pacing estimate, natural visual scene writing, and `SFX` notes for sound effects plus ambient sound. The writer does not create `storyboard.json`, image prompts, video prompts, `edit-plan.json`, asset DAGs, media files, or render commands.

## Inputs

Required:

- user brief, title, story idea, or existing draft
- `video_spec.workflow_mode`

Optional:

- `creator_context`
- reference text
- existing `story-script.md` to revise

## Reference

Use [references/gold-story-script.md](/Users/yangel/Documents/code/magic-skills/video-writer/references/gold-story-script.md) as the style anchor for field completeness, naming stability, and sentence density.

- Follow its compactness and clarity.
- Do not reuse its premise, character names, locations, or lines unless the user explicitly asks for that story.

## Output

Return `story-script.md`. It is Markdown, not JSON.

Use this enriched format exactly:

```text
【场景 1】
[scene_id]：S_01
[story_role]：hook | setup | build | turn | reveal | payoff | ending | transition
[duration_hint_sec]：3
[subject_refs]：角色A, 道具B
[location_ref]：地点名
[audio_type]：voiceover | dialogue | none
[speaker]：旁白 | 角色名 | 无
[visual]：用自然的画面描述写清人物、动作、地点、环境，以及需要被看见的核心视觉信息。
[台词/旁白]：具体文本，无则写“无”。
[SFX]：统一写关键音效和环境声；无则写“无”。
```

## Scene Rules

- Prefer `8-20` scenes for short-form automation unless the planner specifies another count.
- Each scene must include visual action, dialogue or voiceover text, integrated `SFX`, and enough structured metadata for downstream storyboard compilation.
- Every scene must explicitly set `audio_type` to `dialogue`, `voiceover`, or `none`.
- `story_role` must describe the scene's narrative function, not camera language.
- `duration_hint_sec` should be a realistic integer estimate for that beat, usually `2-6` for shorts unless the planner specifies otherwise.
- `subject_refs` must list the recurring characters, creatures, props, or entities that are visually central in this scene. Reuse the exact same names across scenes.
- `location_ref` must use a stable location label when the place is reusable; do not rename the same place scene to scene.
- `speaker` must identify who is speaking when `audio_type` is `voiceover` or `dialogue`; otherwise write `无`.
- `visual` must read like a natural scene description, while still making the core visual information explicit. It should cover who is present, what is happening, where it happens, what the environment feels like, and what absolutely must be seen.
- `SFX` should include only key sound effects and ambient sound. Do not write music mood, score direction, or BGM notes in this field.
- Keep dialogue short enough for video generation and subtitle readability.
- Keep sentence structure compact so downstream JSON compilation is stable.
- Do not include shot types, camera moves, image prompts, video prompts, edit commands, or rendering instructions.

## Downstream Intent

Write `story-script.md` so `video-storyboard` does not need to guess the following:

- what this scene is doing in the story
- roughly how long the beat should last
- which characters or objects must be tracked across scenes
- whether a location should be treated as reusable
- who is speaking
- what the scene must show visually
- what sound cues and ambient texture belong to the scene

The gold sample demonstrates the target level of specificity: enough detail to compile stable assets and prompts downstream, but still written as story scenes rather than shot instructions.

## Workflow Mode Rules

| Mode | Writing behavior |
|---|---|
| `narration_only` | Use voiceover to carry story; minimize direct character speech. |
| `dialogue_only` | Use short spoken lines to drive action; avoid long monologues. |
| `mixed` | Use voiceover for setup or transition, dialogue for key dramatic moments; avoid both competing in the same scene. |

## Quality Checks

Before returning, check:

- scene IDs are stable and ordered as `S_01`, `S_02`, ...
- every scene includes `story_role`, `duration_hint_sec`, `subject_refs`, `location_ref`, `speaker`, `visual`, and `SFX`
- every scene has exactly one `audio_type`
- recurring characters, props, and locations keep the exact same names across scenes
- the output matches the field discipline and compact sentence style of the gold sample without copying its story content
- `visual` reads naturally instead of as a checklist, while still containing人物、动作、地点、环境和核心视觉信息
- `SFX` does not contain music mood or BGM instructions
- no scene mixes narration and dialogue into an ambiguous field
- the script can be compiled into `storyboard.json`
- no JSON, image prompt, video prompt, asset task, edit instruction, or render command leaked into this artifact
