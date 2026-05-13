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
    - video-orchestrator-param.json
    - compose-video-result.json
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
- A stage should not be marked runnable merely because its nominal input file exists; the planner should consider status-bearing artifacts such as `run-report.json`, `subtitle-alignment.json`, and `compose-video-result.json`.

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
- For `magicclaw-imgs-to-img` tasks, `input_refs` must identify the concrete reference assets that execution should feed into generation, `reference_bindings` must define how each ref maps to an upstream produced image asset, and `wait_for` must name the producer tasks that materialize those refs.
- Do not treat `input_refs` as decorative metadata. They are executable reference inputs for downstream asset execution.
- For `magicclaw-imgs-to-img` tasks, `reference_bindings` is required and should provide `ref_id`, `producer_task_id`, `expected_output_id` when available, `asset_type`, `usage_role`, and `required`.
- Use these fixed tool assignments for the standard concrete execution path:
  - `P1` `voiceover_tts` -> `tool: magicclaw-generate-tts`
  - `P0` `character_reference` -> `tool: magicclaw-generate-img`
  - `P2` `keyframe_image` with reusable character or key-prop refs -> `tool: magicclaw-imgs-to-img`
  - `P2` `keyframe_image` without those refs -> `tool: magicclaw-generate-img`
  - `P3` `image_to_video` -> `tool: magicclaw-generate-video`
  - `P3` `native_dialogue_video` -> `tool: magicclaw-generate-video`
  - `P4` `bgm` -> `tool: magicclaw-generate-music` when generated BGM/music is requested

## `asset-manifest.json`

Asset executor output.

```json
{
  "assets": [
    {
      "id": "",
      "url": "",
      "type": "reference_image | keyframe_image | narration_audio | dialogue_audio | video_clip | sfx | bgm",
      "task_id": ""
    }
  ]
}
```

## `run-report.json`

Asset executor status output.

```json
{
  "project_id": "",
  "status": "initialized | running | success | partial | blocked | failed | not_requested",
  "tasks": [
    {
      "task_id": "",
      "stage": "",
      "task_type": "",
      "tool": "",
      "status": "pending | running | success | blocked | failed | skipped",
      "expected_outputs": [],
      "provider_task_id": null,
      "attempts": 0,
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

- `asset-manifest.json` is the persisted asset and lineage truth for downstream subtitle alignment and rendering. It must be initialized from `asset-dag.json` immediately after DAG handoff, before concrete media generation finishes.
- `asset-manifest.json` must not include a top-level `tasks` array. Task lists belong in `asset-dag.json` and `run-report.json`.
- `asset-manifest.json.assets[]` should contain one placeholder or materialized asset entry for every DAG `expected_outputs` item, carrying the final output asset ID and optionally the producing `task_id`, but must not record task status.
- `asset-manifest.json` should be complete for the executed scope. If the DAG declares reference images, keyframe images, narration audio, video clips, or other audio assets, each declared output should appear as its own asset record even before it has a final URL.
- Forbidden manifest fields: top-level `status`, top-level `tasks`, `assets[].status`, and `assets[].task_status`. If any of these appear, the manifest is invalid and must be rewritten.
- When providers return usable media URLs, the manifest should preserve a primary remote media `url` for each generated asset.
- In lightweight runtime manifests, prefer `id` / `url` / `type` records over path-only local file records.
- Do not emit path-only entries when a stable remote `url` exists for the same asset.
- Manifest asset IDs should be the concrete output asset IDs declared by DAG `expected_outputs`, not producer task IDs. For example, use `VID_S01`, not `T_VID_S01`, as the manifest video asset ID.
- For `magicclaw-imgs-to-img` execution, downstream stages should be able to recover which reference images were actually consumed, either from persisted lineage metadata or from `run-report.json`.
- Task status must live only in `run-report.json`. Do not write top-level `status`, task `task_status`, or asset `task_status` into `asset-manifest.json`.
- `run-report.json` is the persisted execution truth, so current task status, blocked tasks, and retry-relevant state should be explicit rather than inferred from missing files.
- `run-report.json` must be initialized from `asset-dag.json` at the same handoff moment as `asset-manifest.json`, before concrete helper calls.
- `run-report.json.tasks[]` should mirror every DAG task and record `task_id`, `stage`, `task_type`, `tool`, current `status`, `expected_outputs`, `provider_task_id`, `attempts`, `output_asset_ids`, error/blocker fields, and emitted dynamic values.
- `task_id` in `run-report.json.tasks[]` is the internal DAG task ID. `provider_task_id` is the concrete generation API's returned task ID, such as the `task_id` printed by a MagicClaw helper. Use `provider_task_id` for later provider status queries.
- Initialize `provider_task_id` as `null` before the provider task is submitted. As soon as the create/submit call succeeds, persist the returned provider task ID before polling or waiting.
- MagicClaw helper calls default to asynchronous submit mode. The initial helper call should return quickly with a provider `task_id`, set the corresponding run-report task to `running`, and keep `output_asset_ids` empty until a later query by `provider_task_id` returns a usable media URL.
- Do not mark a task `success` merely because the async create/submit call succeeded. `success` means the provider status query has produced the final asset URL and the matching manifest asset entry has been updated.
- During execution, a task should move through `pending -> running -> success | blocked | failed | skipped`; a helper call should not be in progress while the corresponding run-report task still says `pending`.

Paired example:

The full gold files live at:

- `references/gold-asset-dag.json`
- `references/gold-asset-manifest.json`
- `references/gold-run-report.json`

Use them as a matched pair. The manifest materializes the asset IDs declared in DAG `expected_outputs` without a top-level task list or status fields, while the run report mirrors the DAG task IDs and exposes each task's current execution status and eventual `output_asset_ids`.

Minimal initialized `asset-manifest.json` fragment immediately after DAG handoff, before concrete helper calls:

```json
{
  "assets": [
    {
      "id": "IMG_S04",
      "type": "keyframe_image",
      "task_id": "T_IMG_S04"
    }
  ]
}
```

Minimal initialized `run-report.json` fragment at the same moment:

```json
{
  "project_id": "tennis-kids-anime",
  "status": "initialized",
  "tasks": [
    {
      "task_id": "T_IMG_S04",
      "stage": "P2",
      "task_type": "keyframe_image",
      "tool": "magicclaw-imgs-to-img",
      "status": "pending",
      "expected_outputs": ["IMG_S04"],
      "provider_task_id": null,
      "attempts": 0,
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

Representative `magicclaw-imgs-to-img` DAG fragment:

```json
{
  "task_id": "T_IMG_S04",
  "stage": "P2",
  "task_type": "keyframe_image",
  "tool": "magicclaw-imgs-to-img",
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

Corresponding runtime `asset-manifest.json` fragment after successful execution:

```json
{
  "assets": [
    {
      "id": "CHAR_XZ_REF",
      "url": "https://images.magiclight.ai/open-task/1888000000001001/0.png",
      "type": "reference_image",
      "task_id": "T_CHAR_XZ"
    },
    {
      "id": "CHAR_XY_REF",
      "url": "https://images.magiclight.ai/open-task/1888000000001002/0.png",
      "type": "reference_image",
      "task_id": "T_CHAR_XY"
    },
    {
      "id": "PROP_BALL_REF",
      "url": "https://images.magiclight.ai/open-task/1888000000001003/0.png",
      "type": "reference_image",
      "task_id": "T_PROP_BALL"
    },
    {
      "id": "IMG_S04",
      "url": "https://images.magiclight.ai/open-task/1888000000002004/0.png",
      "type": "keyframe_image",
      "task_id": "T_IMG_S04"
    }
  ]
}
```

Mapping rules shown by this pair:

- `asset-manifest.json` should not contain top-level `tasks`; execution state and task coverage should be read from `run-report.json.tasks[]`.
- DAG `expected_outputs` should become concrete manifest asset IDs immediately as placeholders, then keep the same IDs when execution succeeds.
- `reference_bindings[].expected_output_id` should resolve to upstream manifest assets before `magicclaw-imgs-to-img` runs.
- The `magicclaw-imgs-to-img` scene output such as `IMG_S04` should appear as its own manifest asset, not be merged into a reference asset record.
- A complete matched sample also includes narration audio, motion clips, and BGM. See the full gold files for the end-to-end version.

Representative `run-report.json` fragment for the same execution:

```json
{
  "project_id": "tennis-kids-anime",
  "status": "success",
  "tasks": [
    {
      "task_id": "T_IMG_S04",
      "stage": "P2",
      "task_type": "keyframe_image",
      "tool": "magicclaw-imgs-to-img",
      "status": "success",
      "expected_outputs": ["IMG_S04"],
      "provider_task_id": "1888000000002004",
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

- `run-report.json.tasks[]` should be created before execution starts, then updated in place as each task becomes `running`, `success`, `blocked`, `failed`, or `skipped`.
- `provider_task_id` should store the provider/API returned task ID used for subsequent status queries; do not overwrite the internal DAG `task_id`.
- `tasks[].output_asset_ids` should match the asset IDs materialized into `asset-manifest.json` after a task succeeds; pending/running/blocked tasks may keep it empty while preserving `expected_outputs`.
- For reference-conditioned `magicclaw-imgs-to-img`, `run-report.json` should preserve enough execution truth to show which upstream reference assets were actually consumed.
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

## `video-orchestrator-param.json`

Canonical MagicClaw video composition request payload.

```json
{
  "job_kind": "render_from_edit_assets",
  "schema_version": "v1",
  "trace_id": "",
  "input_protocol": "video_remotion_renderer",
  "input_protocol_version": "v1",
  "project": {
    "project_id": "",
    "title": "",
    "aspect_ratio": "9:16",
    "language": "zh",
    "fps": 30
  },
  "timeline": {
    "scenes": [
      {
        "scene_id": "S_01",
        "order": 1,
        "duration_sec": 2,
        "duration_frames": 60,
        "video_strategy": {
          "primary_source_type": "video | image",
          "fallback_source_type": "image | none"
        }
      }
    ]
  },
  "assets": {
    "items": [
      {
        "asset_id": "VID_S01",
        "asset_type": "video",
        "source_url": "https://example.com/scene-01.mp4",
        "scene_id": "S_01",
        "role": "scene_video"
      }
    ]
  },
  "subtitles": {
    "alignment": {
      "S_01": [
        {
          "start_sec": 0.2,
          "end_sec": 1.3,
          "text": ""
        }
      ]
    }
  },
  "render_options": {
    "output_format": "mp4",
    "fps": 30,
    "resolution": {
      "width": 1080,
      "height": 1920
    }
  }
}
```

## `compose-video-result.json`

Persisted output from `magicclaw-compose-video`.

```json
{
  "ok": true,
  "mode": "submit_and_wait | submit_only | query | unknown",
  "task_id": "",
  "status": "submitted | running | succeeded | failed | unknown",
  "status_code": 0,
  "video_url": "",
  "source_url": "",
  "trace_id": "",
  "elapsed_seconds": 0,
  "query_attempts": 0,
  "error": null,
  "debug": {}
}
```

Notes:

- `video-orchestrator-param.json` should compile `edit-plan.json` scene truth against `asset-manifest.json` asset truth rather than re-inferring media from prompts or story text.
- If dialogue scenes require `dialogue_alignment`, `subtitle-alignment.json` is the subtitle timing truth; blocked or partial alignment should become an explicit composition blocker when those scenes cannot be exported correctly with captions.
- Keep `input_protocol = video_remotion_renderer` and `input_protocol_version = v1` unless the compose API contract itself changes. Those are API payload values required by the current `magicclaw-compose-video` interface.
- Normal orchestration should rely on top-level `task_id`, `status`, and `video_url`, not on fields inside `debug`.

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
| `story-script.md` meaning | `storyboard.json`, `edit-plan.json`, `asset-dag.json`, generated assets, subtitle alignment, composition param, composition result, QA |
| `storyboard.json` scene | affected `edit-plan.json` scene, affected DAG tasks, affected media assets, subtitle alignment when dialogue changed, composition param, composition result, QA |
| `edit-plan.json` timing | `asset-dag.json`, subtitle alignment when dialogue windows change, composition param, composition result, QA |
| `asset-dag.json` task | affected `asset-manifest.json`, `run-report.json`, composition param, composition result, QA |
| `asset-manifest.json` asset | subtitle alignment when video/audio changed, composition param, composition result, QA |
| `subtitle-alignment.json` | composition param, composition result, QA |
| `video-orchestrator-param.json` | compose-video result, QA |

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
