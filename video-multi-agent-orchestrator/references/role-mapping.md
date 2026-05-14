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
| Asset generation child | `video-asset-dag`, `video-asset-executor` | `magicclaw-generate-tts`, `magicclaw-generate-img`, `magicclaw-imgs-to-img`, `magicclaw-generate-video`, `magicclaw-generate-music` for production presets | execution planning and concrete media generation |
| Editor child | `video-editor` | `magicclaw-compose-video` for production presets; `video-subtitle-alignment` when subtitle timing is required | edit truth, subtitle alignment, cloud composition assembly |

Production preset rule: if the product promise is real generated assets plus a final composed video, treat the MagicClaw concrete helpers and `magicclaw-compose-video` as required profile skills during profile bootstrap. They are optional only for planning-only or bring-your-own-assets workflows.

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

### Asset generation child production skills

- `magicclaw-generate-tts`
  - concrete helper for `voiceover_tts`
- `magicclaw-generate-img`
  - concrete helper for plain references and stills
- `magicclaw-imgs-to-img`
  - concrete helper for ref-conditioned keyframes
- `magicclaw-generate-video`
  - concrete helper for scene motion assets
- `magicclaw-generate-music`
  - concrete helper for generated BGM/music assets

These helpers belong under the asset generation child because they are execution tools, not planning tools.

### Editor child production and optional skills

- `video-subtitle-alignment`
  - belongs here because it refines timing truth for dialogue scenes, and remains optional because some final compositions do not need dialogue subtitle timing
- `magicclaw-compose-video`
  - belongs here because it assembles the canonical `video-orchestrator` payload and submits the final cloud composition task from edit truth plus asset truth

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
| `video-orchestrator-param.json` | Editor child |
| `compose-video-result.json` | Editor child |
| `qa_report` | Main agent |

## 4. Read Permissions

| Agent | Read access |
|---|---|
| Main agent | all protocol files |
| Director child | `brief`, `video_spec`, `creator_context`, `story-script.md`, `direction-notes.md`, `storyboard.json` |
| Asset generation child | `storyboard.json`, `edit-plan.json`, existing `asset-dag.json`, existing `asset-manifest.json`, existing `run-report.json` |
| Editor child | `storyboard.json`, `edit-plan.json`, `asset-manifest.json`, `run-report.json`, `subtitle-alignment.json` when revising composition |

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
   - MagicClaw concrete helper skills during production execution
5. Main agent:
   - inspect `asset-manifest.json` and `run-report.json`
   - optional `video-asset-visualizer`
6. Editor child:
   - `video-subtitle-alignment` when required
   - `magicclaw-compose-video` when final composition is requested
7. Main agent:
   - `video-qa`
   - decide accept, revise, or retry

## 6. Revision Routing

| Problem type | Route back to |
|---|---|
| story tone, scene intent, prompt framing | Director child |
| visual continuity or sound intent before edit | Director child |
| scene duration, source strategy, subtitle strategy, composition hints | Editor child |
| missing refs, bad keyframes, failed TTS, failed generated clips, manifest truth | Asset generation child |
| subtitle timing, compose payload assembly, final video submission | Editor child |
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
