---
name: studio-world-runtime-protocol
description: Runtime presence protocol for Magic Studio Kanban workers. Use when a Hermes Kanban task belongs to a Studio run and the UI needs short, in-character progress comments, human-readable blockers, and structured handoff metadata.
version: 1.0.0
metadata:
  hermes:
    tags: [studio, kanban, runtime, presence, multi-agent]
    related_skills: [kanban-worker]
---

# Studio World Runtime Protocol

You are working inside a Magic Studio world. The Studio UI renders official
Hermes Kanban comments and completion metadata as character speech bubbles,
handoff animations, blocker cards, and runtime logs.

Do real work first. Presence updates are small signals around the work, not a
replacement for the deliverable.

## Required lifecycle

1. Start by calling `kanban_show()` for your current task.
2. Immediately after orientation, call `kanban_comment()` once with a short
   in-character sentence about what you are starting.
3. If the task has multiple major phases or runs for a while, call
   `kanban_comment()` at most one more time with concrete progress.
4. If you are blocked, call `kanban_comment()` with one sentence of context,
   then call `kanban_block(reason=...)` with a human-readable blocker.
5. Before completion, make sure all promised artifact files exist in
   `$HERMES_KANBAN_WORKSPACE`.
6. Complete with `kanban_complete(summary=..., metadata=...)`.

## Comment style

Comments are shown directly to users as speech bubbles.

Good:

- `我先把主角动机和三幕结构扣住，避免后面分镜失焦。`
- `分镜已经拆到中段转折，我在检查每个镜头的时长是否压得住。`
- `素材表快好了，我在把角色、场景和镜头依赖对齐。`

Bad:

- `Working on task t_123.`
- `I will now execute the requested operation according to the task body.`
- Long transcripts, full JSON dumps, stack traces, or generic status spam.

Keep each comment to one short sentence. Do not invent facts. Do not mention
internal IDs unless the human must act on them.

## Completion metadata

When you produce files, include stable artifact file names in metadata:

```python
kanban_complete(
    summary="剧本完成，后续可以按 8 个场景进入分镜。",
    metadata={
        "artifactKeys": ["story-script.json"],
        "studioWorld": {
            "handoffText": "剧本好了，分镜同学可以按 8 个场景接上。"
        }
    },
)
```

Rules:

- `artifactKeys` contains file names only, not absolute paths.
- `studioWorld.handoffText` is one short in-character handoff sentence.
- The summary should be a compact handoff, not a transcript.

## Blockers

If you need approval, missing input, credentials, or a human decision:

```python
kanban_comment(
    task_id=os.environ["HERMES_KANBAN_TASK"],
    body="我能看到上游任务完成了，但当前工作区还没有拿到 storyboard.json。"
)
kanban_block(reason="缺少 storyboard.json，无法继续生成剪辑计划。")
```

The block reason must be readable by a non-engineer. Put deeper context in the
comment, not in the reason.
