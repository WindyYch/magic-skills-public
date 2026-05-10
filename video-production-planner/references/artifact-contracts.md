# AI Video Production Artifact Contracts

Use these contracts for planner handoffs and role results. The protocol favors named files over free-form role summaries.

## `video_spec`

```yaml
video_spec:
  project_id:
  title:
  duration_sec:
  aspect_ratio:
  language:
  target_platform:
  workflow_mode: narration_only | dialogue_only | mixed
  generation_policy: specs_only | execute_assets | render_final
  review_gates:
    story: required | skipped
    storyboard_edit: required | skipped
    final: required | skipped
  deliverables:
    - story-script.md
    - storyboard.json
    - edit-plan.json
    - asset-dag.json
```

## `production_plan`

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
    - render-input.json
    - render-report.json
    - final.mp4
  stages:
    - stage:
      skill:
      inputs:
      outputs:
      review_gate:
      status: pending | skipped | blocked | done | not_requested
  hard_dependencies:
    - target:
      requires:
      when:
      if_missing:
  skipped_stages:
    - stage:
      reason:
```

Notes:

- `production_plan` is orchestration truth. It should reflect not only which artifacts exist, but also which later stages are blocked by execution truth or subtitle truth.
- A stage should not be marked runnable merely because its nominal input file exists; the planner should consider status-bearing artifacts such as `run-report.json`, `subtitle-alignment.json`, and `render-report.json`.

## `story-script.md`

Writer output. It is Markdown, not JSON.

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
[台词/旁白]：...
[SFX]：统一写关键音效和环境声；无则写“无”。
```

Notes:

- `subject_refs` and `location_ref` are the continuity anchors that help `storyboard.json` register reusable assets consistently.
- `visual` is a natural scene description that still makes the must-see visual information explicit; it is not camera direction.
- `SFX` contains only sound effects and ambience, not music mood.
- `video-storyboard` expects this enriched format and should not be given legacy minimal scripts.

## `storyboard.json`

Storyboard compiler output. It must be valid JSON only.

```json
{
  "project_meta": {
    "project_id": "",
    "title": "",
    "workflow_mode": "narration_only",
    "duration_target_sec": 0,
    "aspect_ratio": "",
    "language": "zh"
  },
  "global_assets": [],
  "scene_assets": [],
  "global_audio_assets": [],
  "scenes": [
    {
      "scene_id": "S_01",
      "story_role": "",
      "summary": "",
      "duration_hint_sec": 0,
      "subject_refs": [],
      "scene_asset_refs": [],
      "continuity_notes": [],
      "shot_type": "",
      "motion_intensity": "static",
      "generation_mode": "image_first",
      "image_prompt": "",
      "video_prompt": "",
      "negative_constraints": [],
      "reference_requirements": [],
      "audio": {
        "audio_type": "voiceover",
        "speaker_ref": "",
        "text": "",
        "usage_mode": "remotion_tts"
      },
      "sound_design": {
        "sfx_notes": "",
        "ambience_notes": ""
      },
      "lip_sync_required": false,
      "subtitle_source": "audio_content"
    }
  ]
}
```

Supporting object shapes:

```json
{
  "global_assets": [
    {
      "asset_id": "CHAR_01",
      "name": "",
      "type": "character | creature | prop | vehicle | environment_anchor",
      "description": "",
      "reference_strategy": "generate_reference | scene_only | user_provided"
    }
  ],
  "scene_assets": [
    {
      "asset_id": "LOC_01",
      "name": "",
      "type": "location | setpiece | screen_content | prop_cluster",
      "description": ""
    }
  ],
  "global_audio_assets": [
    {
      "audio_asset_id": "VOICE_01",
      "name": "",
      "type": "narrator_voice | character_voice",
      "speaker_ref": "",
      "usage_mode": "remotion_tts | kling_voice",
      "voice_traits": []
    }
  ]
}
```

Notes:

- `subject_refs` should reference `global_assets[].asset_id`, not raw free-text names.
- `scene_asset_refs` should reference `scene_assets[].asset_id`, not raw free-text names.
- continuity-defining traits should be written into `description` in natural language instead of split into a `continuity_traits` array.
- `generation_mode` tells downstream stages whether a scene is image-first, motion-first, or native dialogue video.
- `motion_intensity` helps downstream editing and generation interpret how active the scene should feel.
- `negative_constraints` and `reference_requirements` are base storyboard fields, not art-director-only patch data.
- `sound_design` keeps SFX and ambience structured instead of leaking them into prompt prose.
- `image_prompt` should describe a single still-image moment.
- `video_prompt` should describe the motion continuation of that same image moment, including camera movement when needed.

## `edit-plan.json`

Editor output. It must be valid JSON only.

```json
{
  "project_meta": {
    "project_id": "",
    "title": "",
    "workflow_mode": "narration_only",
    "aspect_ratio": "9:16",
    "fps": 30
  },
  "timeline": [
    {
      "scene_id": "S_01",
      "order": 1,
      "duration_sec": 2,
      "duration_frames": 60,
      "narrative_role": "",
      "video_strategy": {
        "generation_mode": "image_first",
        "primary_source_type": "generated_image",
        "fallback_source_type": "generated_video",
        "motion_treatment": "still_hold"
      },
      "audio_strategy": {
        "audio_type": "voiceover",
        "voice_render_mode": "remotion_tts",
        "speaker_ref": "VOICE_01",
        "needs_lip_sync": false,
        "use_scene_sound_design": true
      },
      "subtitle_strategy": {
        "enabled": true,
        "source": "audio_content",
        "placement": "open_captions"
      },
      "transitions": {
        "in_type": "cut",
        "out_type": "cut",
        "reason": "continuous visual beat"
      },
      "render_hints": {
        "shot_type": "close_up",
        "motion_intensity": "subtle",
        "continuity_direction": "carry the same lantern glow and wet jacket state from the previous beat",
        "requested_source_window_sec": 2,
        "source_override_reason": "",
        "audio_ducking_target": "voiceover"
      }
    }
  ],
  "global_audio_plan": {
    "bgm_strategy": {
      "enabled": true,
      "duck_under": ["voiceover", "dialogue"]
    },
    "scene_sound_bed_policy": {
      "preserve_ambience": true,
      "preserve_sfx_hits": true
    },
    "alignment_required_scene_ids": []
  }
}
```

Notes:

- `duration_sec` is the final timeline truth; `render_hints.requested_source_window_sec` is the downstream generation headroom hint when a source clip should be longer than the final cut.
- `video_strategy` should compile scene `generation_mode` into real source choice and motion treatment instead of leaving downstream stages to infer them from prompts.
- `shot_type`, `motion_intensity`, `continuity_notes`, and `sound_design` should influence duration, transitions, scene sound treatment, and render hints rather than being dropped after storyboard compilation.

## `asset-dag.json`

Asset DAG compiler output. It must be valid JSON only.

```json
{
  "project_id": "",
  "execution_stages": ["P0", "P1", "P2", "P3", "P4"],
  "tasks": [
    {
      "task_id": "",
      "stage": "P0",
      "task_type": "character_reference | voice_profile_create | voiceover_tts | keyframe_image | image_to_video | native_dialogue_video | sfx | bgm",
      "tool": "",
      "input_refs": [],
      "reference_bindings": [],
      "wait_for": [],
      "params": {},
      "dynamic_params": {},
      "expected_outputs": []
    }
  ]
}
```

Rules:

- Add `character_reference` tasks only when `storyboard.json` defines recurring characters in `global_assets` and those characters are actually referenced by scenes.
- If no recurring character identity is defined in `storyboard.json`, omit `character_reference` tasks instead of inventing placeholder characters.
- Use `edit-plan.json` as execution truth for `primary_source_type`, `motion_treatment`, `requested_source_window_sec`, native dialogue handling, and scene audio usage when it differs from raw storyboard hints.
- `fallback_source_type` is not an automatic second branch by default; only materialize fallback generation tasks when the workflow explicitly requires them.
- `params.duration_sec` for motion tasks should usually follow `render_hints.requested_source_window_sec`, not only the final scene cut length.
- `native_dialogue_video` tasks should preserve exact-line speech constraints and any required `voice_id` dependency.
- For `imgs-to-img` tasks, `input_refs` must identify the concrete reference assets that execution should feed into generation, `reference_bindings` must define how each ref maps to an upstream produced image asset, and `wait_for` must name the producer tasks that materialize those refs.
- Do not treat `input_refs` as decorative metadata. They are executable reference inputs for downstream asset execution.
- For `imgs-to-img` tasks, `reference_bindings` is required and should provide `ref_id`, `producer_task_id`, `expected_output_id` when available, `asset_type`, `usage_role`, and `required`.
- Use these fixed tool assignments for the standard concrete execution path:
  - `P1` `voiceover_tts` -> `tool: generate-tts`
  - `P0` `character_reference` -> `tool: generate-img`
  - `P2` `keyframe_image` with reusable character or key-prop refs -> `tool: imgs-to-img`
  - `P2` `keyframe_image` without those refs -> `tool: generate-img`
  - `P3` `image_to_video` -> `tool: generate-video`
  - `P3` `native_dialogue_video` -> `tool: generate-video`

## `asset-manifest.json`

Asset executor output.

```json
{
  "assets": [
    {
      "id": "",
      "url": "",
      "type": "reference_image | keyframe_image | narration_audio | dialogue_audio | video_clip | sfx | bgm"
    }
  ]
}
```

## `run-report.json`

Asset executor status output.

```json
{
  "project_id": "",
  "status": "success | partial | blocked | failed | not_requested",
  "tasks": [
    {
      "task_id": "",
      "status": "success | failed | blocked | skipped",
      "attempts": 1,
      "error": "",
      "blocked_reason": "",
      "output_asset_ids": [],
      "emitted_dynamic_values": {}
    }
  ],
  "retry_state": {
    "dynamic_values": {},
    "completed_task_ids": [],
    "blocked_task_ids": []
  }
}
```

Notes:

- `asset-manifest.json` is the persisted asset truth for downstream subtitle alignment and rendering, so it should preserve a primary remote media `url` for each generated asset whenever the provider returns one.
- `asset-manifest.json` should be complete for the executed scope. If the run produced reference images, keyframe images, narration audio, video clips, or other audio assets, each materialized asset should appear as its own asset record.
- In lightweight runtime manifests, prefer `id` / `url` / `type` records over path-only local file records.
- Do not emit path-only entries when a stable remote `url` exists for the same asset.
- Manifest asset IDs should be the concrete output asset IDs declared by DAG `expected_outputs`, not producer task IDs. For example, use `VID_S01`, not `T_VID_S01`, as the manifest video asset ID.
- For `imgs-to-img` execution, downstream stages should be able to recover which reference images were actually consumed, either from persisted lineage metadata or from `run-report.json`.
- `run-report.json` is the persisted execution truth, so blocked tasks and retry-relevant state should be explicit rather than inferred from missing files.

Paired example:

The full gold files live at:

- `references/gold-asset-dag.json`
- `references/gold-asset-manifest.json`
- `references/gold-run-report.json`

Use them as a matched pair. The manifest should materialize the same asset IDs declared in the DAG task `expected_outputs`.

Representative `imgs-to-img` DAG fragment:

```json
{
  "task_id": "T_IMG_S04",
  "stage": "P2",
  "task_type": "keyframe_image",
  "tool": "imgs-to-img",
  "input_refs": ["REF_XZ", "REF_XY", "REF_BALL"],
  "reference_bindings": [
    {
      "ref_id": "REF_XZ",
      "producer_task_id": "T_CHAR_XZ",
      "expected_output_id": "CHAR_XZ_REF",
      "asset_type": "reference_image",
      "usage_role": "character",
      "required": true
    },
    {
      "ref_id": "REF_XY",
      "producer_task_id": "T_CHAR_XY",
      "expected_output_id": "CHAR_XY_REF",
      "asset_type": "reference_image",
      "usage_role": "character",
      "required": true
    },
    {
      "ref_id": "REF_BALL",
      "producer_task_id": "T_PROP_BALL",
      "expected_output_id": "PROP_BALL_REF",
      "asset_type": "reference_image",
      "usage_role": "prop",
      "required": true
    }
  ],
  "wait_for": ["T_CHAR_XZ", "T_CHAR_XY", "T_PROP_BALL"],
  "params": {
    "scene_id": "S_04",
    "prompt": "3D anime split-screen rally composition...",
    "aspect_ratio": "16:9",
    "subject_refs": ["REF_XZ", "REF_XY", "REF_BALL"]
  },
  "dynamic_params": {},
  "expected_outputs": ["IMG_S04"]
}
```

Corresponding runtime `asset-manifest.json` fragment:

```json
{
  "assets": [
    {
      "id": "CHAR_XZ_REF",
      "url": "https://images.magiclight.ai/open-task/1888000000001001/0.png",
      "type": "reference_image"
    },
    {
      "id": "CHAR_XY_REF",
      "url": "https://images.magiclight.ai/open-task/1888000000001002/0.png",
      "type": "reference_image"
    },
    {
      "id": "PROP_BALL_REF",
      "url": "https://images.magiclight.ai/open-task/1888000000001003/0.png",
      "type": "reference_image"
    },
    {
      "id": "IMG_S04",
      "url": "https://images.magiclight.ai/open-task/1888000000002004/0.png",
      "type": "keyframe_image"
    }
  ]
}
```

Mapping rules shown by this pair:

- `expected_outputs` should become concrete manifest asset IDs when execution succeeds.
- `reference_bindings[].expected_output_id` should resolve to upstream manifest assets before `imgs-to-img` runs.
- The `imgs-to-img` scene output such as `IMG_S04` should appear as its own manifest asset, not be merged into a reference asset record.
- A complete matched sample also includes narration audio, motion clips, and BGM. See the full gold files for the end-to-end version.

Representative `run-report.json` fragment for the same execution:

```json
{
  "project_id": "tennis-kids-anime",
  "status": "success",
  "tasks": [
    {
      "task_id": "T_IMG_S04",
      "status": "success",
      "attempts": 1,
      "error": "",
      "blocked_reason": "",
      "output_asset_ids": ["IMG_S04"],
      "emitted_dynamic_values": {
        "consumed_reference_asset_ids": ["CHAR_XZ_REF", "CHAR_XY_REF", "PROP_BALL_REF"]
      }
    }
  ],
  "retry_state": {
    "dynamic_values": {},
    "completed_task_ids": ["T_CHAR_XZ", "T_CHAR_XY", "T_PROP_BALL", "T_IMG_S04"],
    "blocked_task_ids": []
  }
}
```

Mapping rules shown by the run report example:

- `tasks[].output_asset_ids` should match the asset IDs materialized into `asset-manifest.json`.
- For reference-conditioned `imgs-to-img`, `run-report.json` should preserve enough execution truth to show which upstream reference assets were actually consumed.
- `retry_state.completed_task_ids` should let a retry resume from already materialized upstream refs and scene assets instead of regenerating them by default.
- The full gold run report includes the same task coverage as the gold DAG and gold manifest. Use `references/gold-run-report.json` for the end-to-end paired sample.

## `subtitle-alignment.json`

Subtitle alignment output.

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

Notes:

- `edit-plan.json` decides which scenes require `dialogue_alignment`; `asset-manifest.json` decides which concrete media asset those cues belong to.
- Partial alignment is valid when some required scenes aligned successfully and others are explicitly blocked with reasons.
- Do not infer subtitle timing from script length alone when the dialogue media asset is missing or blocked.

## `render-input.json`

Remotion renderer input.

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

## `render-report.json`

Remotion renderer status output.

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

Notes:

- `render-input.json` should compile `edit-plan.json` scene truth against `asset-manifest.json` asset truth rather than re-inferring media from prompts or story text.
- If dialogue scenes require `dialogue_alignment`, `subtitle-alignment.json` is the subtitle timing truth; blocked or partial alignment should become an explicit render blocker when those scenes cannot be rendered correctly without captions.

## `missing_inputs_report`

Return this instead of proceeding when a hard dependency is absent:

```yaml
missing_inputs_report:
  blocked_stage:
  missing_inputs:
    - name:
      required_by:
      why_required:
  available_inputs:
  recommended_next_skill:
  user_question:
```

## Stale Artifact Rule

When an upstream artifact changes, mark only affected downstream artifacts stale:

| Changed artifact | Mark stale |
|---|---|
| `story-script.md` meaning | `storyboard.json`, `edit-plan.json`, `asset-dag.json`, generated assets, subtitle alignment, render, QA |
| `storyboard.json` scene | affected `edit-plan.json` scene, affected DAG tasks, affected media assets, subtitle alignment when dialogue changed, render, QA |
| `edit-plan.json` timing | `asset-dag.json`, subtitle alignment when dialogue windows change, render, QA |
| `asset-dag.json` task | affected `asset-manifest.json`, `run-report.json`, render, QA |
| `asset-manifest.json` asset | subtitle alignment when video/audio changed, render, QA |
| `subtitle-alignment.json` | render, QA |
| `render-input.json` | render report, final export, QA |

## QA Report

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
