# AI Video Production Capabilities

Abstract capabilities are role permissions. They are stable names for planning and skill boundaries, not concrete Hermes tool names.

If a concrete Hermes tool for a capability is unavailable, create the required protocol file or task spec and stop before the external action. Do not invent tool names.

## Capability Glossary

| Capability | Meaning |
|---|---|
| `story_script_generation` | Expand a brief into `story-script.md` scenes |
| `story_direction` | Optional cinematic treatment and continuity guidance |
| `storyboard_compile` | Compile `story-script.md` into `storyboard.json` |
| `visual_protocol_review` | Validate or revise visual fields inside `storyboard.json` |
| `audio_protocol_review` | Validate or revise `global_audio_assets`, scene audio, and audio strategy |
| `edit_plan_compile` | Compile `storyboard.json` into `edit-plan.json` |
| `asset_dag_compile` | Compile `storyboard.json + edit-plan.json` into `asset-dag.json` |
| `asset_execution` | Execute `asset-dag.json` and write persisted asset truth in `asset-manifest.json` plus persisted execution truth in `run-report.json`; may call concrete helpers such as `generate-tts`, `generate-img`, `imgs-to-img`, and `generate-video` |
| `subtitle_alignment` | Align native dialogue subtitles into `subtitle-alignment.json` using asset truth from executed media |
| `remotion_render` | Compile `render-input.json` from timeline truth, asset truth, and subtitle truth; render `final.mp4`; write `render-report.json` |
| `media_inspection` | Inspect generated/imported media for duration, sync, readability, and consistency |
| `file_workspace` | Save or reference protocol files |
| `user_review` | Pause for user approval or requested changes |
| `creator_memory` | Use compact creator history and preferences from memory |

## Role Permissions

| Role skill | Allowed capabilities |
|---|---|
| `video-production-planner` | `creator_memory`, `file_workspace`, `user_review` |
| `video-writer` | `story_script_generation`, `file_workspace`, `user_review` |
| `video-director` | `story_direction`, `file_workspace`, `user_review` |
| `video-storyboard` | `storyboard_compile`, `file_workspace`, `user_review` |
| `video-art-director` | `visual_protocol_review`, `media_inspection`, `file_workspace`, `user_review` |
| `video-sound-designer` | `audio_protocol_review`, `media_inspection`, `file_workspace`, `user_review` |
| `video-editor` | `edit_plan_compile`, `file_workspace`, `user_review` |
| `video-asset-dag` | `asset_dag_compile`, `file_workspace`, `user_review` |
| `video-asset-executor` | `asset_execution`, `media_inspection`, `file_workspace`, `user_review` |
| `video-subtitle-alignment` | `subtitle_alignment`, `media_inspection`, `file_workspace`, `user_review` |
| `video-remotion-renderer` | `remotion_render`, `media_inspection`, `file_workspace`, `user_review` |
| `video-qa` | `media_inspection`, `file_workspace`, `user_review` |

## Guardrails

- A role may prepare the file it owns, but it must not perform another role's core work.
- `video-art-director` and `video-sound-designer` review sections of `storyboard.json` and `edit-plan.json`; they do not create extra core protocol files unless the planner asks for an explanatory note.
- The planner routes any revision to the smallest affected role.
- The planner may only execute media after `asset-dag.json` exists.
- The planner may only continue to render after execution truth and any required subtitle truth are sufficient.
- `generate-tts`, `generate-img`, `imgs-to-img`, and `generate-video` are concrete execution helpers inside `asset_execution`; they do not replace `video-asset-dag` or `video-asset-executor`.
- Concrete tools are implementation details. Keep the production plan in abstract capability terms unless a concrete tool already exists and the user asks for execution.
