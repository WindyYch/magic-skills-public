# AI Video Production Skill Test Cases

Use these cases to validate the skill set after edits. Each case checks whether the agent loads the right role skills, respects protocol files, honors hard dependencies, and avoids doing work outside role boundaries.

## Case 1: Full Video Specs-Only

Prompt:

```text
Use video-production-planner to make a 45 second 9:16 AI short about a repair robot finding an old Earth voice message. Warm sci-fi, light suspense. Produce specs only, do not generate images, audio, video, or render.
```

Expected:

- Loads `video-production-planner`.
- Presents `production_plan` with fixed outputs.
- Uses `workflow_mode: narration_only` unless the user asks for dialogue.
- After approval or explicit skip, routes through `video-writer`, `video-storyboard`, `video-editor`, `video-asset-dag`, and `video-qa`.
- Produces enriched `story-script.md` scenes with stable `story_role`, `duration_hint_sec`, `subject_refs`, `location_ref`, `speaker`, natural `visual` descriptions, and `SFX` limited to sound effects plus ambience.
- Produces `storyboard.json`, `edit-plan.json`, and `asset-dag.json`.
- Does not stop after `storyboard.json`; continues to `edit-plan.json` and `asset-dag.json` when no review gate blocks the chain.
- Marks `asset-manifest.json`, `run-report.json`, `subtitle-alignment.json`, `video-orchestrator-param.json`, and `compose-video-result.json` as `not_requested`.

## Case 2: Creation Phrase Routes To Planner

Prompt:

```text
帮我创建一个视频，主题是海底城市最后一次广播。
```

Expected:

- Triggers `video-production-planner`, not `video-storyboard` directly.
- Builds a minimal `video_spec`.
- Plans the fixed file chain.
- Does not jump to media generation before `asset-dag.json`.

## Case 3: `storyboard.json` From Existing Script

Prompt:

```text
Use video-storyboard. Convert this story-script.md into storyboard.json: [script text].
```

Expected:

- Loads only `video-storyboard` unless required context is missing.
- Outputs valid JSON only.
- Includes `project_meta`, `global_assets`, `scene_assets`, `global_audio_assets`, and `scenes`.
- Maps enriched script fields directly without falling back to a legacy minimal script shape.
- Registers recurring assets with stable IDs and uses those IDs inside scene refs.
- Sets per-scene `generation_mode`, `motion_intensity`, `sound_design`, `negative_constraints`, and `reference_requirements`.
- Writes `image_prompt` as a still-image description and `video_prompt` as its dynamic continuation.
- Does not load asset execution, render, or QA roles.

## Case 3B: Storyboard Strategy Hints Drive Downstream

Prompt:

```text
Use video-storyboard. Convert this story-script.md into storyboard.json for downstream editing and asset generation.
```

Expected:

- Still or tableau scenes may use `generation_mode = image_first`.
- Motion-heavy scenes may use `generation_mode = video_first`.
- Native dialogue scenes use `generation_mode = dialogue_native`.
- `sound_design.sfx_notes` and `sound_design.ambience_notes` preserve the script's sound intent without burying it in prompt text.
- `negative_constraints` and `reference_requirements` are present when relevant instead of being deferred to later patch-only roles.
- `image_prompt` does not describe multiple sequential actions.
- `video_prompt` extends the matching image moment and may include camera movement.

## Case 3C: Editor Compiles Storyboard Strategy Into Timeline Truth

Prompt:

```text
Use video-editor. Compile this storyboard.json into edit-plan.json for downstream asset generation and rendering.
```

Expected:

- Outputs valid JSON only.
- Preserves storyboard scene order unless the user explicitly asks for a re-edit.
- Compiles `generation_mode` into `video_strategy.generation_mode`, primary/fallback source type, and motion treatment.
- Compiles `shot_type` and `motion_intensity` into final duration decisions and `render_hints`.
- Uses `continuity_notes` to influence transitions and continuity-facing render hints instead of dropping them.
- Carries `sound_design` into scene audio treatment and `global_audio_plan`.
- Keeps `image_first` final cuts at `<= 2.0s` unless the planner explicitly overrides, and promotes the source strategy when speech or performance cannot plausibly fit that limit.
- Uses `render_hints.requested_source_window_sec` to express downstream source headroom, especially for `dialogue_native` scenes that need `5s` or `6s` source clips.
- Uses `subtitle_strategy.source = dialogue_alignment` for native dialogue scenes.

## Case 3D: Planner Integrates Concrete TTS Helper

Prompt:

```text
Use video-production-planner. Make a narration-only short and execute assets when concrete helpers are available.
```

Expected:

- Keeps narration scenes on the voiceover TTS path instead of misclassifying them as dialogue.
- Plans `voiceover_tts` execution through `video-asset-executor`.
- Treats `magicclaw-generate-tts` as the concrete helper for `voiceover_tts` when available.
- Continues to final composition only after narration audio assets exist in `asset-manifest.json` or are explicitly blocked.

## Case 4: Dialogue Subtitle Alignment Required

Prompt:

```text
Use video-production-planner. Make a dialogue-only short where two characters speak through kling_native video.
```

Expected:

- Uses `workflow_mode: dialogue_only`.
- `storyboard.json` scenes have `audio.audio_type = dialogue`, `lip_sync_required = true`, exact-line `video_prompt`, and character voices in `global_audio_assets`.
- `edit-plan.json` uses `voice_render_mode = kling_native` and `subtitle_strategy.source = dialogue_alignment`.
- The plan includes `video-subtitle-alignment` after `video-asset-executor` and before `magicclaw-compose-video`.

## Case 4B: Subtitle Alignment Uses Asset Truth

Prompt:

```text
Use video-subtitle-alignment. Align subtitles for a mixed workflow where only S_02 and S_05 use native dialogue video, and asset-manifest.json contains one dialogue_video asset plus one blocked scene video.
```

Expected:

- Selects only scenes that actually require `dialogue_alignment` from `edit-plan.json`.
- Uses `asset-manifest.json` to resolve the concrete scene media being aligned instead of assuming every dialogue scene succeeded.
- Returns aligned cues for the available dialogue asset.
- Marks the blocked dialogue scene explicitly rather than inventing approximate cue timing from the script alone.
- Preserves enough scene-level status for downstream composition and QA to know whether the alignment artifact is `partial` or `blocked`.

## Case 4C: Compose Stage Blocks On Required Subtitle Truth

Prompt:

```text
Use magicclaw-compose-video. Prepare video-orchestrator-param.json from edit-plan.json, asset-manifest.json, and subtitle-alignment.json where one dialogue scene requires dialogue_alignment but subtitle-alignment.json marks that scene blocked.
```

Expected:

- Resolves composition-ready scene media from `asset-manifest.json` instead of guessing from scene prompts.
- Detects that the required dialogue subtitle truth is blocked for that scene.
- Does not submit a success-looking composition task when the required subtitle truth is blocked.
- Returns a blocked planner or stage state that makes the subtitle blocker explicit before `compose-video-result.json` could claim success.

## Case 4D: Planner Respects Execution And Subtitle Truth Gates

Prompt:

```text
Use video-production-planner. Continue this project from existing edit-plan.json, asset-manifest.json, run-report.json, and subtitle-alignment.json where media execution is partial and one required dialogue subtitle scene is blocked.
```

Expected:

- Does not continue to `magicclaw-compose-video` as if all composition prerequisites are satisfied.
- Uses `run-report.json` and `subtitle-alignment.json` status-bearing truth, not just file existence, to decide the next stage.
- Routes to the smallest blocked role or QA instead of claiming the chain is composition-ready.
- Makes the blocker explicit in the plan or returned status.

## Case 5: Audio-Driven Missing Audio

Prompt:

```text
Use video-production-planner. Make an audio-driven lip-sync music video from this storyboard, but I do not have the song yet.
```

Expected:

- Loads workflow variant rules for audio-driven video.
- Blocks media execution.
- Returns `missing_inputs_report` with `audio_asset` or generation-ready `audio_spec` as missing.
- Recommends `video-sound-designer` or asks user to provide audio.

## Case 6: Memory-Aware Planning

Prompt:

```text
Use video-production-planner. Make another short in my usual style, but avoid repeating previous story ideas.
```

Expected:

- Uses memory entries only if already present.
- Creates `creator_context`.
- Does not invent past projects when memory has no video history.
- Tells writer and storyboard compiler to use `creator_context` without copying old story premises.

## Case 7: Scene-Level Revision

Prompt:

```text
Change only S_03 so the robot sees the message on a cracked glass panel.
```

Expected:

- Routes to `video-storyboard` or `video-art-director` depending on whether action or visual prompt changes.
- Marks only affected downstream protocol files stale.
- Does not restart the full video workflow.

## Case 8: Asset Executor Retry

Prompt:

```text
Use video-asset-executor. Continue this failed asset-dag.json run. The previous run created a voice_id but failed on scene video.
```

Expected:

- Reads `run-report.json` or `asset-manifest.json` state when available.
- Restores `voice_id` and other dynamic non-file values.
- Does not regenerate completed references unless dependencies changed.

## Case 8B: Executor Preserves Expected Outputs And Blockers

Prompt:

```text
Use video-asset-executor. Execute this asset-dag.json where a native_dialogue_video task depends on a voice_id and a magicclaw-generate-video tool that is currently unavailable.
```

Expected:

- Does not invent a substitute tool or silently downgrade the task.
- Marks the affected task as `blocked` rather than `failed` when the missing tool or dependency is the real problem.
- Preserves any already completed upstream outputs in `asset-manifest.json`.
- Writes explicit blocked reasons and retry-relevant dynamic values into `run-report.json`.
- If a task already declared `expected_outputs`, the manifest either contains matching asset IDs for completed outputs or the missing outputs are explained by blocker state.

## Case 8C: Executor Blocks Ref-Composed Keyframes Without Reusable URLs

Prompt:

```text
Use video-asset-executor. Execute this asset-dag.json where a keyframe_image task uses magicclaw-imgs-to-img and waits on two upstream reference assets, but asset-manifest.json only contains local file paths and no reusable remote image URLs for those refs.
```

Expected:

- Does not silently downgrade the task to `magicclaw-generate-img`.
- Marks the `magicclaw-imgs-to-img` keyframe task as `blocked`.
- Explains that reusable remote image URLs are missing for one or more required refs.
- Preserves any completed upstream reference assets and retry-relevant state in `asset-manifest.json` and `run-report.json`.

## Case 8D: Executor Persists TTS Audio URL In Asset Truth

Prompt:

```text
Use video-asset-executor. Execute this asset-dag.json where a voiceover_tts task succeeds through magicclaw-generate-tts and the provider returns an audio_url plus local materialized audio output.
```

Expected:

- `asset-manifest.json` contains the narration audio asset with a first-class `url` field and stable duration metadata when available.
- The executor does not demote the provider audio URL into cache-only metadata just because a local file was also materialized.
- Any optional local cache path does not replace the asset's primary remote `url`.
- `run-report.json` still records normal task success and any retry-relevant metadata.

## Case 8E: Executor Persists All Materialized Asset Classes

Prompt:

```text
Use video-asset-executor. Execute this asset-dag.json where the run successfully produces one reference image, six keyframe images, six narration audio assets, and four scene video clips.
```

Expected:

- `asset-manifest.json` includes every materialized asset instead of only final video clips or only one asset per scene.
- Reference images, keyframe images, narration audio assets, and video clips each appear as separate asset records.
- The manifest remains usable as downstream asset truth for subtitle alignment, rendering, retry, and QA because no produced asset class is silently omitted.

## Case 8F: Executor Prefers Remote URLs Over Local Paths

Prompt:

```text
Use video-asset-executor. Execute this asset-dag.json where generated images, TTS audio, and video clips all succeed and each provider returns a stable remote URL, while the executor also materializes local cache files.
```

Expected:

- `asset-manifest.json` stores those assets with first-class `url` fields.
- The executor does not emit path-only asset entries when stable remote URLs are already available.
- Local cache files may still exist, but they do not replace remote URLs as the primary manifest locator.

## Case 9: Character Reference Tasks Are Conditional

Prompt:

```text
Use video-asset-dag. Build asset-dag.json from storyboard.json and edit-plan.json where global_assets defines two recurring characters and scenes reference them through subject_refs.
```

Expected:

- `asset-dag.json` includes `P0` `character_reference` tasks for those recurring characters.
- Scene keyframe tasks wait for the relevant character reference outputs.
- If the same storyboard is revised to remove recurring character definitions, those `character_reference` tasks are omitted rather than replaced with invented placeholders.

## Case 9B: Edit Plan Drives DAG Branch Choice

Prompt:

```text
Use video-asset-dag. Compile storyboard.json and edit-plan.json where one scene started as image_first in storyboard.json but edit-plan.json promotes it to generated_video with requested_source_window_sec = 5.
```

Expected:

- `asset-dag.json` follows `edit-plan.json` as execution truth for that scene instead of stopping at the storyboard's original image-first hint.
- The scene gets the required `P2` keyframe dependency plus a `P3` motion task.
- The motion task duration request follows `render_hints.requested_source_window_sec`, not only the final cut duration.
- `fallback_source_type` does not automatically produce a duplicate branch unless the workflow explicitly asks for it.

## Case 9C: Ref-Composed Keyframes Use `magicclaw-imgs-to-img`

Prompt:

```text
Use video-asset-dag. Compile storyboard.json and edit-plan.json where S_04 is a generated_image keyframe and the scene must visibly preserve one recurring character ref plus one key prop ref.
```

Expected:

- The `P2` `keyframe_image` task for `S_04` uses `tool: magicclaw-imgs-to-img` rather than `magicclaw-generate-img`.
- The keyframe task preserves the scene's `image_prompt` as the composition target rather than replacing it with a generic prompt.
- The task declares dependencies on the required upstream reference assets instead of treating them as free text only.
- The task keeps those required refs in `input_refs`, so downstream execution can pass them as concrete image inputs rather than only mentioning them in prose.
- The task includes one `reference_bindings` entry per required ref, including the upstream producer task mapping.
- The DAG does not silently downgrade this ref-conditioned keyframe to plain text-to-image generation.

## Case 9D: Executor Must Consume Declared Ref Images

Prompt:

```text
Use video-asset-executor. Execute a magicclaw-imgs-to-img keyframe task where input_refs=["REF_XZ","REF_XY","REF_BALL"], reference_bindings map those refs to T_CHAR_XZ, T_CHAR_XY, and T_PROP_BALL, wait_for=["T_CHAR_XZ","T_CHAR_XY","T_PROP_BALL"], and asset-manifest.json already contains reusable remote URLs for those three upstream reference images.
```

Expected:

- The executor resolves each declared ref to a concrete remote image URL before calling `magicclaw-imgs-to-img`.
- The executor uses `reference_bindings` as the primary ref-resolution map instead of guessing from prompt text.
- The helper call uses the scene prompt plus one image input per resolved reference URL.
- The executor does not treat satisfied `wait_for` dependencies as enough if the actual reference URLs were never passed into generation.
- If one declared ref cannot be resolved to a reusable remote URL, the task is marked `blocked` rather than silently falling back to prompt-only generation.

## Case 9E: `magicclaw-imgs-to-img` Tasks Must Not Omit Structured Ref Bindings

Prompt:

```text
Use video-asset-dag. Compile asset-dag.json for a ref-conditioned keyframe where S_04 must preserve two recurring characters and one tennis ball prop.
```

Expected:

- The `magicclaw-imgs-to-img` task does not stop at `input_refs` alone.
- The task includes `reference_bindings` entries for both characters and the prop.
- `wait_for` matches the producer task IDs declared in `reference_bindings`.
- The task remains valid for downstream execution without requiring the executor to infer ref-to-task mapping from prose.

## Case 10: Role Boundary Pressure

Prompt:

```text
Use video-writer and also give me storyboard.json, asset-dag.json, and a compose-video submission command.
```

Expected:

- `video-writer` produces only `story-script.md`.
- It defers `storyboard.json`, `asset-dag.json`, and video composition work to the planner and corresponding role skills.

## Case 11: Planner-Orchestrated Role Continuation

Prompt:

```text
/video-production-planner 帮我创建一个视频，主题是海底城市最后一次广播。走完整 specs-only 协议链，不需要暂停确认，不生成真实素材，不渲染。
```

Expected:

- Sets `orchestration_mode: planner_orchestrated`.
- Sets story and storyboard/edit review gates to `skipped`.
- Produces or plans `story-script.md`, `storyboard.json`, `edit-plan.json`, `asset-dag.json`, and `qa_report`.
- Does not treat `video-storyboard`'s JSON-only rule as permission to end the whole planner run at `storyboard.json`.
