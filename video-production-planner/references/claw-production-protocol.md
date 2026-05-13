# Claw Video Production Protocol

Use this reference when planning or validating the video production chain. The protocol is file-first: every stage consumes named files and produces named files.

## Fixed Chain

```text
brief
-> story-script.md
-> storyboard.json
-> edit-plan.json
-> asset-dag.json
-> asset-manifest.json + run-report.json
-> subtitle-alignment.json when required
-> video-orchestrator-param.json + compose-video-result.json
```

Do not rename these files. Do not replace them with conversational summaries.

## Workflow Modes

| Mode | Use for | Audio truth | Subtitle rule |
|---|---|---|---|
| `narration_only` | explainers, history, mood shorts, voiceover stories | `remotion_tts` voiceover | no dialogue alignment needed |
| `dialogue_only` | normal drama, dialogue skits | `kling_native` or dialogue TTS | `subtitle-alignment.json` required |
| `mixed` | cinematic shorts with narration and dialogue | scene-level split | only dialogue scenes require alignment |

## Stage Ownership

| File | Primary skill | Meaning |
|---|---|---|
| `story-script.md` | `video-writer` | scene script with stable story metadata: `scene_id`, `story_role`, `duration_hint_sec`, `subject_refs`, `location_ref`, `audio_type`, `speaker`, natural-language `visual`, dialogue/voiceover, and `SFX` for sound effects plus ambience |
| `storyboard.json` | `video-storyboard` | structured story, stable asset registries, scene generation strategy, scene sound design, and scene prompts |
| `edit-plan.json` | `video-editor` | timeline truth: durations, source strategy, motion treatment, transitions, audio strategy, subtitle strategy, and render-facing continuity hints |
| `asset-dag.json` | `video-asset-dag` | execution truth for media generation tasks, dependencies, and source-branch decisions compiled from `storyboard.json` and `edit-plan.json` |
| `asset-manifest.json` | `video-asset-executor` | persisted asset truth: initialized immediately from `asset-dag.json` with asset entries for declared outputs, then updated with generated/provided image, audio, and video asset URLs; top-level task lists and task status belong outside the manifest |
| `run-report.json` | `video-asset-executor` | persisted execution truth: initialized immediately from `asset-dag.json` with every DAG `task_id` and current status, then updated with provider/API returned `provider_task_id`, attempts, output asset IDs, blocked reasons, retries, and recoverable dynamic state |
| `subtitle-alignment.json` | `video-subtitle-alignment` | dialogue timing truth aligned to actual executed scene media, including blocked scene reasons when alignment cannot yet run |
| `video-orchestrator-param.json` | `magicclaw-compose-video` | canonical `video-orchestrator` request object compiled from edit truth, asset truth, and subtitle truth for `/taskapi/v1/task/gen/video-orchestrator-v2` |
| `compose-video-result.json` | `magicclaw-compose-video` | composition status truth from mc-task-api: `task_id`, semantic `status`, optional `video_url`, and error details |

## Hard Rules

- Separate narration and dialogue. Voiceover uses `remotion_tts`; native dialogue video uses `kling_native` or another explicit dialogue audio path.
- In concrete execution workflows, `voiceover_tts` asset tasks may be materialized by `magicclaw-generate-tts` while still belonging to the voiceover TTS path.
- Reference-conditioned keyframes that must visibly preserve recurring character or key-prop refs should use `magicclaw-imgs-to-img`; plain stills may use `magicclaw-generate-img`.
- Generated BGM/music tasks may be materialized by `magicclaw-generate-music` while still belonging to the supplemental audio path.
- Concrete MagicClaw generation calls are asynchronous by default. Initial submit calls should not pass `--wait` unless the user explicitly requests blocking execution for that task.
- After an async submit succeeds, write the provider/API returned task ID into `run-report.json.tasks[].provider_task_id`, mark the task `running`, and query that provider task ID later for final status and media URL.
- Do not write final asset URLs or `success` status based only on task creation. `asset-manifest.json` receives the final URL only after a later provider status query succeeds.
- Dialogue video prompts must include the exact spoken line:
  - `The character says exactly this line in Chinese: 「...」`
  - `Do not say any other words and do not speak any other language.`
- When the execution path uses concrete helper generation, generated stills should come from `magicclaw-generate-img` or `magicclaw-imgs-to-img` before any dependent `magicclaw-generate-video` clip task.
- When providers return stable remote media URLs, `asset-manifest.json` should use those URLs as the primary runtime locator instead of path-only local file entries.
- Immediately after `asset-dag.json` is produced and handed to execution, both `asset-manifest.json` and `run-report.json` must be created before concrete helper calls. The manifest should contain asset entries only, using DAG `expected_outputs` as asset IDs and optionally preserving producing `task_id` on each asset entry for lineage; it must not contain a top-level `tasks` array. The run report should record every DAG task with current `status`, initially `pending`, and `provider_task_id: null`, then write the provider/API returned task ID into `provider_task_id` as soon as the create/submit call succeeds and use it for later status queries.
- Kling image-to-video duration must be an integer from `3` to `15`.
- Short dialogue scenes should usually generate `5s`; longer dialogue can use `6s`, then edit down.
- Image-first scenes must be `<= 2.0s`.
- Dialogue subtitles must not be averaged across a scene. Use speech windows from `subtitle-alignment.json`.
- `voice_id` and other dynamic non-file values must be persisted in `asset-manifest.json` or `run-report.json` so retries can recover them.
- `edit-plan.json` is the timeline truth for final composition. `asset-manifest.json` is the asset truth for final composition.
- Even after replacing the local render stage with `magicclaw-compose-video`, the canonical compose payload currently still expects `input_protocol = video_remotion_renderer` and `input_protocol_version = v1`. Treat those as API payload fields, not as a signal to route back to the old role skill.

## Specs-Only Behavior

When the user asks for specs only:

- Produce `story-script.md`, `storyboard.json`, `edit-plan.json`, and `asset-dag.json`.
- Mark media execution, subtitle alignment, final composition, and export as `not_requested`.
- Do not call image, video, audio, subtitle alignment, or composition tools, including `magicclaw-generate-tts`, `magicclaw-generate-img`, `magicclaw-imgs-to-img`, `magicclaw-generate-video`, `magicclaw-generate-music`, and `magicclaw-compose-video`.
