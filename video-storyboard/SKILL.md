---
name: video-storyboard
description: Use when the user asks for storyboard.json, a storyboard, shot list, scene breakdown, camera plan, or conversion from story-script.md into a structured video protocol.
version: 1.7.0
metadata:
  hermes:
    tags: [creative, video, storyboard, shots, storyboard-json]
    related_skills: [video-production-planner, video-director, video-art-director, video-sound-designer, video-editor]
---

# AI Video Storyboard Compiler

Use this role skill to compile `story-script.md` into `storyboard.json`.

If this skill is loaded by `video-production-planner`, follow the planner's `video_spec`, optional `direction-notes.md`, `creator_context`, and protocol contracts.

## Execution Modes

### Direct invocation

When the user invokes `video-storyboard` directly, return only `storyboard.json` and stop.

### Planner-orchestrated invocation

When `video-production-planner` loads this skill with `orchestration_mode: planner_orchestrated`, the JSON-only rule below applies only to the `storyboard.json` artifact. After the artifact is complete, follow the planner's remaining stages. Do not stop at `storyboard.json` when the plan still requires `video-editor`, `video-asset-dag`, QA, execution, alignment, or render work and no review gate or hard dependency blocks the chain.

## Role Boundary

The storyboard compiler owns structured scene protocol: global assets, scene assets, global audio assets, image prompts, video prompts, scene audio, sound design intent, generation strategy hints, lip-sync flags, and subtitle source. It does not execute assets, create `edit-plan.json`, align subtitles, or render exports.

Its output must be generation-ready. In execution workflows, `storyboard.json` supplies the scene `image_prompt` and `video_prompt` fields that later stages compile into `asset-dag.json` tasks.

## Inputs

Required:

- `story-script.md`
- `video_spec.workflow_mode`

Optional:

- `direction-notes.md`
- `creator_context`
- existing `storyboard.json` to revise

`story-script.md` must use the enriched writer format with `story_role`, `duration_hint_sec`, `subject_refs`, `location_ref`, `speaker`, `visual`, and `SFX`.

## Reference

Use [references/gold-storyboard.json](/Users/yangel/Documents/code/magic-skills/video-storyboard/references/gold-storyboard.json) as the style anchor for asset registration, scene field completeness, and prompt-to-structure balance.

- Follow its registry discipline, scene density, and cross-field consistency.
- Do not reuse its premise, character names, locations, or dialogue unless the user explicitly asks for that story.

## Output

For direct invocation, return only valid JSON for `storyboard.json` and do not wrap it in Markdown. For planner-orchestrated invocation, the `storyboard.json` artifact itself must be valid JSON; the planner may continue with later artifact sections afterward.

Required top-level fields:

```json
{
  "project_meta": {},
  "global_assets": [],
  "scene_assets": [],
  "global_audio_assets": [],
  "scenes": []
}
```

`global_assets` items must use this shape:

```json
{
  "asset_id": "CHAR_01",
  "name": "",
  "type": "character | creature | prop | vehicle | environment_anchor",
  "description": "",
  "reference_strategy": "generate_reference | scene_only | user_provided"
}
```

`scene_assets` items must use this shape:

```json
{
  "asset_id": "LOC_01",
  "name": "",
  "type": "location | setpiece | screen_content | prop_cluster",
  "description": ""
}
```

`global_audio_assets` items must use this shape:

```json
{
  "audio_asset_id": "VOICE_01",
  "name": "",
  "type": "narrator_voice | character_voice",
  "speaker_ref": "",
  "usage_mode": "remotion_tts | kling_voice",
  "voice_traits": []
}
```

Each scene must include:

```json
{
  "scene_id": "S_01",
  "story_role": "",
  "summary": "",
  "duration_hint_sec": 0,
  "subject_refs": [],
  "scene_asset_refs": [],
  "continuity_notes": [],
  "shot_type": "",
  "motion_intensity": "static | subtle | active | performance",
  "generation_mode": "image_first | video_first | dialogue_native",
  "image_prompt": "",
  "video_prompt": "",
  "negative_constraints": [],
  "reference_requirements": [],
  "audio": {
    "audio_type": "voiceover | dialogue | none",
    "speaker_ref": "",
    "text": "",
    "usage_mode": "remotion_tts | kling_voice | none"
  },
  "sound_design": {
    "sfx_notes": "",
    "ambience_notes": ""
  },
  "lip_sync_required": false,
  "subtitle_source": "audio_content | dialogue_alignment | none"
}
```

## Asset Rules

- Recurring characters must be registered in `global_assets` with stable `asset_id` values, and scene `subject_refs` must reference those IDs.
- Reused locations or spatial containers must be registered in `scene_assets` with stable `asset_id` values, and scene `scene_asset_refs` must reference those IDs.
- Repeated speaking characters or narrators must be registered in `global_audio_assets` with stable `audio_asset_id` values.
- Narrators use `type = narrator_voice` and `usage_mode = remotion_tts`.
- Dialogue characters use `type = character_voice` and usually `usage_mode = kling_voice`.
- One-off scene details should not be promoted into global assets unless downstream continuity benefits from it.

## Script-To-Storyboard Mapping

Map the script fields directly:

- `story_role` -> scene `story_role`
- `duration_hint_sec` -> scene `duration_hint_sec`
- `subject_refs` -> recurring asset registration plus scene `subject_refs` as stable asset IDs
- `location_ref` -> reusable `scene_assets` entry plus scene `scene_asset_refs` as stable asset IDs
- `speaker` -> `audio.speaker_ref` and recurring `global_audio_assets`
- `visual` -> scene `summary`, the decisive still-image moment inside `image_prompt`, and the dynamic continuation inside `video_prompt`
- `台词/旁白` -> `audio.text`
- `SFX` -> scene sound cues, ambience, and downstream sound interpretation context

Use the writer's stable labels as the source of truth unless `direction-notes.md` explicitly revises them.

## Compilation Guidance

- Preserve subject and location naming exactly as written in `story-script.md` when creating asset names and IDs; do not alias the same entity into multiple names.
- If `subject_refs` contains a recurring entity, register it once in `global_assets` and reference it by `asset_id` from every scene.
- If `subject_refs` contains a one-off object that does not recur, it may remain scene-local and does not need a `global_assets` entry.
- If `location_ref` appears in multiple scenes, register it once in `scene_assets` and reference it consistently by `asset_id`.
- If `speaker` is `旁白`, use a narrator voice asset. If `speaker` is a character name, use that stable name in `audio.speaker_ref`.
- Parse `visual` as a natural scene description: identify人物、动作、地点、环境和核心视觉信息, then build `image_prompt` around one decisive visual moment from that scene.
- Treat `SFX` as sound-effects-and-ambience only. Do not infer music mood from it.
- `image_prompt` must be a still-image description. Do not write multiple sequential actions, time progression, or before/after changes into it.
- `video_prompt` must describe what happens after the `image_prompt` moment, including subject motion, environment motion, and camera movement when motion is required.
- Set `generation_mode` deliberately instead of letting downstream stages infer it from prompt prose:
  - `image_first` for still or tableau scenes that can render from an image source
  - `video_first` for motion-led scenes that should generate a clip
  - `dialogue_native` for native speaking video scenes
- Set `motion_intensity` to help downstream editing and generation decide how much motion the clip should show.
- Use `continuity_notes` for carry-over state that a prompt alone may hide, such as damage, lighting change, wet clothing, or object possession.
- Use `negative_constraints` for things that must not appear in generation outputs.
- Use `reference_requirements` to tell downstream stages whether a scene depends on a character reference, location reference, screen insert, or user-supplied source.
- Split `SFX` into `sound_design.sfx_notes` and `sound_design.ambience_notes` so sound intent stays structured instead of falling into free-form hints.

## Workflow Mode Rules

| Mode | Required behavior |
|---|---|
| `narration_only` | Most scenes use `audio.audio_type = voiceover`; `lip_sync_required = false`; `subtitle_source = audio_content`; prefer `image_first` or `video_first` based on motion needs. |
| `dialogue_only` | Dialogue scenes use `audio.audio_type = dialogue`; `lip_sync_required = true`; `subtitle_source = dialogue_alignment`; usually use `generation_mode = dialogue_native`. |
| `mixed` | Scene-level split between `voiceover`, `dialogue`, and `none`; only dialogue scenes require alignment; use `generation_mode` per scene. |

## Dialogue Prompt Rule

If a scene is `dialogue` and may use native video speech such as `kling_native`, the `video_prompt` must include the exact line:

```text
The character says exactly this line in Chinese: 「具体中文台词」. Do not say any other words and do not speak any other language.
```

Do not write vague prompts like `speaking`, `mouth moving`, or only a voice token.

## Quality Checks

Before returning, check:

- output is valid JSON only
- every scene from `story-script.md` is represented
- enriched script fields are mapped directly instead of being reinterpreted
- recurring characters, locations, and voices are registered globally with stable IDs
- scene refs point to registered asset IDs instead of free-floating names
- every scene has explicit `generation_mode` and `motion_intensity`
- every scene has structured `sound_design`, `negative_constraints`, and `reference_requirements`
- the output matches the structural density of the gold sample without copying its story content
- `image_prompt` reads as a still-image description rather than a sequence
- `video_prompt` is the dynamic continuation of `image_prompt` and includes camera movement when motion is required
- every scene that should generate media has a usable `image_prompt` and `video_prompt` for downstream asset-DAG compilation
- dialogue scenes contain exact-line video prompts
- no `edit-plan.json`, `asset-dag.json`, media execution, subtitle alignment, or render work is attempted inside the `storyboard.json` artifact
