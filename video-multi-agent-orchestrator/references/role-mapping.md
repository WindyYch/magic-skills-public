# Role Mapping

Use this reference when the workflow should run as:

- one main agent
- one director child
- one asset generation child
- one editor child

## 1. Role Matrix

| Agent | Required skills | Optional skills | Main responsibility |
|---|---|---|---|
| Main agent | `video-production-planner` | `video-qa`, `video-asset-visualizer` | global planning, dispatch, blocker handling, final acceptance |
| Director child | `video-writer`, `video-storyboard` | `video-director`, `video-art-director`, `video-sound-designer` | story, scene intent, cinematic guidance, storyboard truth |
| Asset generation child | `video-asset-dag`, `video-asset-executor` | `generate-tts`, `generate-img`, `imgs-to-img`, `generate-video` | execution planning and concrete media generation |
| Editor child | `video-editor` | `video-subtitle-alignment`, `video-remotion-renderer` | edit truth, subtitle alignment, render assembly |

## 2. Why These Optional Skills Belong Here

### Main agent optional skills

- `video-qa`
  - QA is cross-stage and should stay above all child roles.
  - QA should route revisions back to the owning child instead of mutating artifacts directly.
- `video-asset-visualizer`
  - This is an inspection utility over `asset-dag.json` and `asset-manifest.json`.
  - It is best used by the main agent for review and acceptance rather than by a child role as part of core production.

### Director child optional skills

- `video-director`
  - belongs here because it owns cinematic intent, pacing emphasis, and continuity guidance before storyboard compile
- `video-art-director`
  - belongs here because it adjusts visual language, not execution truth
- `video-sound-designer`
  - belongs here because it shapes audio intent and scene sound design before edit planning

### Asset generation child optional skills

- `generate-tts`
  - concrete helper for `voiceover_tts`
- `generate-img`
  - concrete helper for plain references and stills
- `imgs-to-img`
  - concrete helper for ref-conditioned keyframes
- `generate-video`
  - concrete helper for scene motion assets

These helpers belong under the asset generation child because they are execution tools, not planning tools.

### Editor child optional skills

- `video-subtitle-alignment`
  - belongs here because it refines timing truth for dialogue scenes
- `video-remotion-renderer`
  - belongs here because it assembles final render input and export from edit truth plus asset truth

## 3. File Write Ownership

| File or artifact | Owning agent |
|---|---|
| `production_plan`, `video_spec`, dispatch state | Main agent |
| `story-script.md` | Director child |
| `direction-notes.md` | Director child |
| `storyboard.json` | Director child |
| `edit-plan.json` | Editor child |
| `asset-dag.json` | Asset generation child |
| `asset-manifest.json` | Asset generation child |
| `run-report.json` | Asset generation child |
| `subtitle-alignment.json` | Editor child |
| `render-input.json` | Editor child |
| `render-report.json` | Editor child |
| `final.mp4` | Editor child |
| `qa_report` | Main agent |

## 4. Read Permissions

| Agent | Read access |
|---|---|
| Main agent | all protocol files |
| Director child | `brief`, `video_spec`, `creator_context`, `story-script.md`, `direction-notes.md`, `storyboard.json` |
| Asset generation child | `storyboard.json`, `edit-plan.json`, existing `asset-dag.json`, existing `asset-manifest.json`, existing `run-report.json` |
| Editor child | `storyboard.json`, `edit-plan.json`, `asset-manifest.json`, `run-report.json`, `subtitle-alignment.json` when revising render |

## 5. Dispatch Order

### Standard path

1. Main agent:
   - load `video-production-planner`
   - produce `production_plan`
2. Director child:
   - `video-writer`
   - optional `video-director`
   - `video-storyboard`
   - optional `video-art-director`
   - optional `video-sound-designer`
3. Editor child:
   - `video-editor`
4. Asset generation child:
   - `video-asset-dag`
   - `video-asset-executor`
   - optional concrete helper skills during execution
5. Main agent:
   - inspect `asset-manifest.json` and `run-report.json`
   - optional `video-asset-visualizer`
6. Editor child:
   - `video-subtitle-alignment` when required
   - `video-remotion-renderer` when render is requested
7. Main agent:
   - `video-qa`
   - decide accept, revise, or retry

## 6. Revision Routing

| Problem type | Route back to |
|---|---|
| story tone, scene intent, prompt framing | Director child |
| visual continuity or sound intent before edit | Director child |
| scene duration, source strategy, subtitle strategy, render hints | Editor child |
| missing refs, bad keyframes, failed TTS, failed generated clips, manifest truth | Asset generation child |
| subtitle timing, render assembly, final export | Editor child |
| cross-stage inconsistency or unclear ownership | Main agent |

## 7. Guardrails

- The director child must not write `edit-plan.json`, `asset-dag.json`, or `asset-manifest.json`.
- The asset generation child must not rewrite `story-script.md`, `storyboard.json`, or `edit-plan.json`.
- The editor child must not rewrite story or execution artifacts.
- Child agents should report cross-role problems to the main agent instead of silently patching another role's file.
- If a revision changes upstream meaning, the main agent should mark downstream artifacts stale and redispatch the owning role.

## 8. Suggested Main-Agent Dispatch Prompt Shape

Use compact dispatch instructions like:

```yaml
dispatch:
  target_agent: director | asset_generation | editor
  reason:
  required_inputs:
    - path:
  required_skills:
    - name:
  writable_outputs:
    - path:
  stop_condition:
  return_to_main_agent_with:
    - path:
```

Recommended examples:

```yaml
dispatch:
  target_agent: director
  reason: produce story and storyboard truth
  required_inputs:
    - brief
    - video_spec
  required_skills:
    - video-writer
    - video-storyboard
  writable_outputs:
    - story-script.md
    - storyboard.json
  stop_condition: storyboard is complete
  return_to_main_agent_with:
    - story-script.md
    - storyboard.json
```

```yaml
dispatch:
  target_agent: asset_generation
  reason: compile and execute media tasks
  required_inputs:
    - storyboard.json
    - edit-plan.json
  required_skills:
    - video-asset-dag
    - video-asset-executor
  writable_outputs:
    - asset-dag.json
    - asset-manifest.json
    - run-report.json
  stop_condition: execution is success, partial, or blocked with explicit report
  return_to_main_agent_with:
    - asset-dag.json
    - asset-manifest.json
    - run-report.json
```

For ready-to-copy prompts with stronger wording, role-specific instructions, and revision scenarios, read `dispatch-prompts.md`.
