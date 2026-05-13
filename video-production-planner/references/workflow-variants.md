# AI Video Production Workflow Variants

Use this file when the task is not the standard full-video path or when dependencies are unclear.

## Full Protocol Chain

```text
creator_context
-> video_spec
-> production_plan_review
-> video-writer              => story-script.md
-> story_review
-> video-director            => direction-notes.md when needed
-> video-storyboard          => storyboard.json
-> video-art-director        => visual review or patch for storyboard.json
-> video-sound-designer      => audio review or patch for storyboard.json/edit-plan.json
-> video-editor              => edit-plan.json
-> storyboard_edit_review
-> video-asset-dag           => asset-dag.json
                               asset-dag.json is the handoff point that declares:
                               P1 voiceover_tts -> magicclaw-generate-tts
                               P0 character_reference -> magicclaw-generate-img
                               P2 keyframe_image with reusable character/key-prop refs -> magicclaw-imgs-to-img
                               P2 keyframe_image without reusable refs -> magicclaw-generate-img
                               P3 image_to_video -> magicclaw-generate-video
                               P3 native_dialogue_video -> magicclaw-generate-video
                               P4 generated bgm/music -> magicclaw-generate-music
-> video-asset-executor      => asset-manifest.json + run-report.json
                               asset-manifest.json is the asset truth
                               run-report.json is the execution truth
                               uses magicclaw-generate-tts for voiceover_tts assets when needed
                               uses magicclaw-imgs-to-img for reference-conditioned keyframes when needed
                               uses magicclaw-generate-img for still/reference assets when needed
                               uses magicclaw-generate-video for image-to-video clips when needed
                               uses magicclaw-generate-music for generated BGM/music when needed
-> video-subtitle-alignment  => subtitle-alignment.json when required
                               subtitle-alignment.json is the dialogue subtitle truth
-> magicclaw-compose-video   => video-orchestrator-param.json + compose-video-result.json
                               compose-video-result.json is the final composition truth
-> video-qa
-> final_review
```

## Direct Stage

| User intent | Minimum chain |
|---|---|
| Script only | `video-writer` |
| `storyboard.json` from brief | `video-writer` -> `video-storyboard` |
| `storyboard.json` from existing `story-script.md` | `video-storyboard` |
| Generate scene media from completed `storyboard.json` | `video-storyboard` -> `video-editor` -> `video-asset-dag` -> `video-asset-executor` |
| Visual protocol review | `video-art-director` |
| Voice, music, subtitles, or sound strategy only | `video-sound-designer` |
| `edit-plan.json` from `storyboard.json` | `video-editor` |
| `asset-dag.json` only | `video-asset-dag` |
| Execute assets from DAG | `video-asset-executor` |
| Align native dialogue subtitles | `video-subtitle-alignment` |
| Compose final video | `video-subtitle-alignment` when required -> `magicclaw-compose-video` -> `video-qa` |
| Review existing plan or export | `video-qa` |

For direct-stage tasks, do not load unrelated role skills.

## Workflow Modes

### `narration_only`

```text
story-script.md voiceover scenes
-> storyboard.json with narrator in global_audio_assets
-> edit-plan.json with voice_render_mode=remotion_tts
-> asset-dag.json
-> asset-manifest.json with narration audio materialized by `voiceover_tts` execution
-> video-orchestrator-param.json
-> compose-video-result.json
```

Rules:

- `global_audio_assets` primarily contains narrator voice.
- `lip_sync_required = false`.
- `subtitle-alignment.json` is normally skipped.
- Voiceover subtitle timing can follow TTS duration and text.
- When concrete voiceover audio is executed, `voiceover_tts` tasks should normally use `magicclaw-generate-tts`.
- `P2` scene keyframes with reusable character or key-prop refs should use `magicclaw-imgs-to-img`; other `P2` scene keyframes may use `magicclaw-generate-img` before any `P3` `magicclaw-generate-video` clip task starts. Generated BGM/music tasks should use `magicclaw-generate-music` when requested.

### `dialogue_only`

```text
story-script.md dialogue scenes
-> storyboard.json with character voices in global_audio_assets
-> edit-plan.json with voice_render_mode=kling_native
-> asset-dag.json with voice_profile_create tasks
-> asset-manifest.json with voice_id values
-> subtitle-alignment.json
-> video-orchestrator-param.json
-> compose-video-result.json
```

Rules:

- Repeated speaking characters must be in `global_audio_assets`.
- Dialogue scenes require exact-line video prompts.
- Dialogue subtitles must use `subtitle-alignment.json`.
- If required subtitle alignment is `blocked`, final composition is also blocked unless the user explicitly accepts a subtitle-free export.
- If dialogue clips are image-to-video, the source still must already exist from user media or a `P2` `magicclaw-generate-img` / `magicclaw-imgs-to-img` task.

### `mixed`

```text
voiceover scenes use remotion_tts
dialogue scenes use kling_native or explicit dialogue audio
all generated clips begin from storyboard-driven stills or provided source images
only dialogue scenes enter subtitle alignment
```

Rules:

- Scene audio type must be explicit: `voiceover`, `dialogue`, or `none`.
- Voiceover and dialogue must not compete in the same scene unless the user explicitly asks for overlap.
- BGM must duck under voiceover and native dialogue.
- Only scenes whose subtitle source is `dialogue_alignment` enter subtitle alignment.
- A blocked required dialogue-alignment scene blocks final composition unless the user approves an exception.

## Execution Truth Gates

After `video-asset-executor`:

- Continue only if `asset-manifest.json` contains the assets required by the next stage.
- Treat `run-report.json status = blocked` as a planner blocker, not a soft warning.
- `status = partial` may continue only if the missing outputs are irrelevant to the requested deliverable.

After `video-subtitle-alignment`:

- `status = success` means final composition may continue.
- `status = partial` may continue only when blocked scenes do not require composed subtitles.
- `status = blocked` prevents final composition when dialogue-alignment scenes still require subtitles.

## Audio-Driven Video

Audio-driven video has a hard dependency:

```text
script_or_audio_direction
-> video-sound-designer
-> audio_asset_or_generation_ready_audio_spec
-> video-storyboard
-> video-editor
-> video-asset-dag
-> video-asset-executor
-> video-subtitle-alignment when native dialogue exists
-> magicclaw-compose-video
-> video-qa
```

Video generation must not start without:

- `audio_asset` or generation-ready `audio_spec`
- `storyboard.json`
- `edit-plan.json`
- `asset-dag.json`
- any required source still for `magicclaw-generate-video`

If audio is missing, return `missing_inputs_report` from `artifact-contracts.md`.

## Specs-Only Mode

When the user says not to generate media, produce protocol specs only:

```text
story-script.md
storyboard.json
edit-plan.json
asset-dag.json
qa_report
```

Mark later outputs as `not_requested`. Do not call image, video, audio, subtitle alignment, render, or export tools.
That includes `magicclaw-generate-tts`, `magicclaw-generate-img`, `magicclaw-imgs-to-img`, `magicclaw-generate-video`, and `magicclaw-generate-music`.

## Revision Mode

Route revisions to the smallest affected artifact:

| User change | Revision role | Mark stale |
|---|---|---|
| Story meaning changes | `video-writer` | storyboard, edit plan, DAG, assets, subtitle alignment, composition, QA |
| One scene action changes | `video-storyboard` | affected edit-plan scene, DAG tasks, media assets, subtitle alignment if dialogue changed, composition, QA |
| Character, scene, visual style, or prompt changes | `video-art-director` | affected storyboard visual fields, DAG tasks, generated visuals, composition, QA |
| Voice, dialogue usage, music, or SFX changes | `video-sound-designer` | storyboard audio fields, edit-plan audio strategy, DAG, audio assets, subtitle alignment, composition, QA |
| Duration, primary/fallback source, subtitle source, or transition changes | `video-editor` | DAG, composition, QA |
| Asset task changes | `video-asset-dag` | manifest, report, composition, QA |
| Generated media changes | `video-asset-executor` | subtitle alignment when needed, composition, QA |
| Dialogue alignment changes | `video-subtitle-alignment` | composition, QA |
| Composition settings change | `magicclaw-compose-video` | compose param, compose result, QA |
| QA blocker only | target role from `qa_report.revision_tasks` | affected downstream artifacts |

Do not restart the full project when a scene-level revision is enough.
