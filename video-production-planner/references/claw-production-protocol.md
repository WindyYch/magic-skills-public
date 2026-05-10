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
-> render-input.json + render-report.json + final.mp4
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
| `asset-manifest.json` | `video-asset-executor` | persisted asset truth: complete generated/provided image, audio, and video assets with primary remote `url` fields plus any needed recoverable metadata or dynamic values |
| `run-report.json` | `video-asset-executor` | persisted execution truth: task status, blocked reasons, retries, and recoverable dynamic state |
| `subtitle-alignment.json` | `video-subtitle-alignment` | dialogue timing truth aligned to actual executed scene media, including blocked scene reasons when alignment cannot yet run |
| `render-input.json` | `video-remotion-renderer` | scene-resolved Remotion composition input compiled from timeline truth, asset truth, and subtitle truth |
| `render-report.json` | `video-remotion-renderer` | render status, output metadata, and explicit blockers when asset or subtitle truth is insufficient |
| `final.mp4` | `video-remotion-renderer` | exported video |

## Hard Rules

- Separate narration and dialogue. Voiceover uses `remotion_tts`; native dialogue video uses `kling_native` or another explicit dialogue audio path.
- In concrete execution workflows, `voiceover_tts` asset tasks may be materialized by `generate-tts` while still belonging to the voiceover TTS path.
- Reference-conditioned keyframes that must visibly preserve recurring character or key-prop refs should use `imgs-to-img`; plain stills may use `generate-img`.
- Dialogue video prompts must include the exact spoken line:
  - `The character says exactly this line in Chinese: 「...」`
  - `Do not say any other words and do not speak any other language.`
- When the execution path uses concrete helper generation, generated stills should come from `generate-img` or `imgs-to-img` before any dependent `generate-video` clip task.
- When providers return stable remote media URLs, `asset-manifest.json` should use those URLs as the primary runtime locator instead of path-only local file entries.
- Kling image-to-video duration must be an integer from `3` to `15`.
- Short dialogue scenes should usually generate `5s`; longer dialogue can use `6s`, then edit down.
- Image-first scenes must be `<= 2.0s`.
- Dialogue subtitles must not be averaged across a scene. Use speech windows from `subtitle-alignment.json`.
- `voice_id` and other dynamic non-file values must be persisted in `asset-manifest.json` or `run-report.json` so retries can recover them.
- `edit-plan.json` is the timeline truth for render. `asset-manifest.json` is the asset truth for render.

## Specs-Only Behavior

When the user asks for specs only:

- Produce `story-script.md`, `storyboard.json`, `edit-plan.json`, and `asset-dag.json`.
- Mark media execution, subtitle alignment, render, and export as `not_requested`.
- Do not call image, video, audio, subtitle alignment, or render tools, including `generate-tts`, `generate-img`, `imgs-to-img`, and `generate-video`.
