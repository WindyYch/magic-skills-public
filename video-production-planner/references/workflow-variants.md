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
                               P1 voiceover_tts -> generate-tts
                               P0 character_reference -> generate-img
                               P2 keyframe_image with reusable character/key-prop refs -> imgs-to-img
                               P2 keyframe_image without reusable refs -> generate-img
                               P3 image_to_video -> generate-video
                               P3 native_dialogue_video -> generate-video
-> video-asset-executor      => asset-manifest.json + run-report.json
                               asset-manifest.json is the asset truth
                               run-report.json is the execution truth
                               uses generate-tts for voiceover_tts assets when needed
                               uses imgs-to-img for reference-conditioned keyframes when needed
                               uses generate-img for still/reference assets when needed
                               uses generate-video for image-to-video clips when needed
-> video-subtitle-alignment  => subtitle-alignment.json when required
                               subtitle-alignment.json is the dialogue subtitle truth
-> video-remotion-renderer   => render-input.json + render-report.json + final.mp4
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
| Render final video | `video-subtitle-alignment` when required -> `video-remotion-renderer` -> `video-qa` |
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
-> render-input.json
-> final.mp4
```

Rules:

- `global_audio_assets` primarily contains narrator voice.
- `lip_sync_required = false`.
- `subtitle-alignment.json` is normally skipped.
- Voiceover subtitle timing can follow TTS duration and text.
- When concrete voiceover audio is executed, `voiceover_tts` tasks should normally use `generate-tts`.
- `P2` scene keyframes with reusable character or key-prop refs should use `imgs-to-img`; other `P2` scene keyframes may use `generate-img` before any `P3` `generate-video` clip task starts.

### `dialogue_only`

```text
story-script.md dialogue scenes
-> storyboard.json with character voices in global_audio_assets
-> edit-plan.json with voice_render_mode=kling_native
-> asset-dag.json with voice_profile_create tasks
-> asset-manifest.json with voice_id values
-> subtitle-alignment.json
-> render-input.json
-> final.mp4
```

Rules:

- Repeated speaking characters must be in `global_audio_assets`.
- Dialogue scenes require exact-line video prompts.
- Dialogue subtitles must use `subtitle-alignment.json`.
- If required subtitle alignment is `blocked`, render is also blocked unless the user explicitly accepts a subtitle-free export.
- If dialogue clips are image-to-video, the source still must already exist from user media or a `P2` `generate-img` / `imgs-to-img` task.

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
- A blocked required dialogue-alignment scene blocks final render unless the user approves an exception.

## Execution Truth Gates

After `video-asset-executor`:

- Continue only if `asset-manifest.json` contains the assets required by the next stage.
- Treat `run-report.json status = blocked` as a planner blocker, not a soft warning.
- `status = partial` may continue only if the missing outputs are irrelevant to the requested deliverable.

After `video-subtitle-alignment`:

- `status = success` means render may continue.
- `status = partial` may continue only when blocked scenes do not require rendered subtitles.
- `status = blocked` prevents render when dialogue-alignment scenes still require subtitles.

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
-> video-remotion-renderer
-> video-qa
```

Video generation must not start without:

- `audio_asset` or generation-ready `audio_spec`
- `storyboard.json`
- `edit-plan.json`
- `asset-dag.json`
- any required source still for `generate-video`

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
That includes `generate-tts`, `generate-img`, `imgs-to-img`, and `generate-video`.

## Revision Mode

Route revisions to the smallest affected artifact:

| User change | Revision role | Mark stale |
|---|---|---|
| Story meaning changes | `video-writer` | storyboard, edit plan, DAG, assets, subtitle alignment, render, QA |
| One scene action changes | `video-storyboard` | affected edit-plan scene, DAG tasks, media assets, subtitle alignment if dialogue changed, render, QA |
| Character, scene, visual style, or prompt changes | `video-art-director` | affected storyboard visual fields, DAG tasks, generated visuals, render, QA |
| Voice, dialogue usage, music, or SFX changes | `video-sound-designer` | storyboard audio fields, edit-plan audio strategy, DAG, audio assets, subtitle alignment, render, QA |
| Duration, primary/fallback source, subtitle source, or transition changes | `video-editor` | DAG, render, QA |
| Asset task changes | `video-asset-dag` | manifest, report, render, QA |
| Generated media changes | `video-asset-executor` | subtitle alignment when needed, render, QA |
| Dialogue alignment changes | `video-subtitle-alignment` | render, QA |
| Render settings change | `video-remotion-renderer` | render report, final video, QA |
| QA blocker only | target role from `qa_report.revision_tasks` | affected downstream artifacts |

Do not restart the full project when a scene-level revision is enough.
