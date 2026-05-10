---
name: video-multi-agent-orchestrator
description: Use when the user wants to run AI video production with a main agent plus three child agents, where the main agent owns planning and dispatch, and the child agents own directing, asset generation, and editing.
version: 1.0.0
metadata:
  hermes:
    tags: [creative, video, orchestration, multi-agent, planner]
    related_skills:
      - video-production-planner
      - video-writer
      - video-director
      - video-storyboard
      - video-art-director
      - video-sound-designer
      - video-editor
      - video-asset-dag
      - video-asset-executor
      - generate-tts
      - generate-img
      - imgs-to-img
      - generate-video
      - video-subtitle-alignment
      - video-remotion-renderer
      - video-qa
      - video-asset-visualizer
---

# Video Multi-Agent Orchestrator

Use this skill when the video workflow should run as:

- one main agent
- three reusable child agents:
  - director
  - asset generation
  - editor

The main agent always owns planning, dispatch, stage truth, blocker handling, and final acceptance.

## Core Rule

Keep the `video-production-planner` rule intact:

- the main agent is the only dispatcher
- child agents do not call each other directly
- child agents return protocol artifacts to the main agent
- the main agent decides the next stage

Do not let the director child directly trigger asset execution.
Do not let the asset child directly rewrite story or edit truth.
Do not let the editor child directly rewrite story or asset truth.

## Agent Topology

- Main agent:
  - required core: `video-production-planner`
  - optional oversight: `video-qa`, `video-asset-visualizer`
- Director child:
  - required core: `video-writer`, `video-storyboard`
  - optional craft: `video-director`, `video-art-director`, `video-sound-designer`
- Asset generation child:
  - required core: `video-asset-dag`, `video-asset-executor`
  - optional concrete helpers: `generate-tts`, `generate-img`, `imgs-to-img`, `generate-video`
- Editor child:
  - required core: `video-editor`
  - optional finishing: `video-subtitle-alignment`, `video-remotion-renderer`

For the full ownership matrix, file write permissions, and dispatch templates, read:

- `references/role-mapping.md`
- `references/dispatch-prompts.md`

## Workflow

1. Main agent loads `video-production-planner` and builds the stage plan.
2. Main agent dispatches the director child to produce story and storyboard artifacts.
3. Main agent dispatches the editor child to produce `edit-plan.json`.
4. Main agent dispatches the asset generation child to produce `asset-dag.json`, then execute it into `asset-manifest.json + run-report.json`.
5. Main agent checks blockers and decides whether to retry, pause, or continue.
6. When rendering is requested, main agent dispatches the editor child again for subtitle alignment and Remotion render stages.
7. Main agent runs final QA or inspection before returning results to the user.

## Ownership Rules

- The main agent owns the state machine.
- Every protocol file should have exactly one owning child role.
- Shared read access is allowed.
- Shared write access is not allowed unless the main agent explicitly requests a revision from the owning role.
- If one child detects a problem in another child's artifact, it should report the issue back to the main agent instead of patching cross-role output silently.

## When To Use

- The user explicitly wants main-agent plus child-agent collaboration
- The user wants stable role separation across story, asset generation, and editing
- The workflow may revisit the same child role multiple times during revision

## Final Checks

Before using this orchestration mode, check:

- the main agent still owns `video-production-planner`
- the director child owns story and storyboard only
- the asset generation child owns DAG plus execution only
- the editor child owns timeline, alignment, and render only
- optional skills are attached to exactly one role in the role matrix
- no protocol file has ambiguous write ownership
