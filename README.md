# magic-skills-public

Public Studio skills used by Magic Agent Studio cloud bootstrap.

## Cloud Node config

Recommended value in `magic-agent-node`:

```env
STUDIO_SKILL_SOURCE_BASE_URL=https://github.com/WindyYch/magic-skills-public/archive/refs/heads/main.zip
```

This installs each skill from the repository archive, so `scripts/`, `references/`, `agents/`, and tests stay with the skill directory.

Raw `SKILL.md` mode is also supported, but only for single-file skills:

```text
https://raw.githubusercontent.com/WindyYch/magic-skills-public/main/${skill}/SKILL.md
```

Example:

```text
https://raw.githubusercontent.com/WindyYch/magic-skills-public/main/video-writer/SKILL.md
```

## Included Studio skills

- `studio-world-runtime-protocol`
- `kanban-worker`
- `kanban-orchestrator`
- `video-production-planner`
- `video-multi-agent-orchestrator`
- `video-writer`
- `video-storyboard`
- `video-editor`
- `video-asset-dag`
- `video-asset-executor`
- `generate-tts`
- `generate-img`
- `imgs-to-img`
- `generate-video`
