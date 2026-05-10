---
name: video-asset-visualizer
description: Use when the user wants to turn asset-manifest.json and asset-dag.json into an HTML viewer that first shows reference assets, then groups each scene's text, keyframe, audio, and video by scene index.
version: 1.0.0
metadata:
  hermes:
    tags: [creative, video, assets, visualization, html]
    related_skills: [video-production-planner, video-asset-dag, video-asset-executor]
---

# Video Asset Visualizer

Use this skill to render `asset-manifest.json` and `asset-dag.json` into a browsable HTML page.

The HTML should follow this structure:

1. show reference assets first
2. then show scene sections indexed by `scene_id`
3. each scene should include:
   - text from `asset-dag.json`, such as narration or dialogue
   - keyframe image
   - audio asset
   - video asset

## When To Use

- The user wants to inspect executed video assets in a browser-friendly layout
- The user has `asset-manifest.json` and `asset-dag.json`
- The user wants scene-by-scene traceability from planned task outputs to materialized media URLs

## Workflow

1. Read `asset-dag.json` and `asset-manifest.json`.
2. Resolve `expected_outputs` from DAG tasks against `assets[].id` in the manifest.
3. Collect reference assets first:
   - manifest assets with `type = reference_image`
   - show ID and image preview
4. Build scene groups using `params.scene_id` from DAG tasks.
5. For each scene, collect:
   - text from TTS or dialogue-related task params
   - keyframe image assets
   - audio assets
   - video assets
6. Render a single HTML file with remote media previews where possible.

## Commands

Basic usage:

```bash
python3 video-asset-visualizer/scripts/render_asset_html.py \
  --asset-dag /abs/path/asset-dag.json \
  --asset-manifest /abs/path/asset-manifest.json \
  --output /abs/path/assets-overview.html
```

Use the gold references:

```bash
python3 video-asset-visualizer/scripts/render_asset_html.py \
  --asset-dag video-production-planner/references/gold-asset-dag.json \
  --asset-manifest video-production-planner/references/gold-asset-manifest.json \
  --output /tmp/gold-assets-overview.html
```

## Output

The script writes one HTML file that:

- shows reference assets in a top section
- shows scenes in ascending scene order
- embeds image, audio, and video URLs when they exist
- prints fallback text when a scene has text but not every media type

## Notes

- Prefer remote `url` values from `asset-manifest.json`.
- Do not require `run-report.json` for the first version of the visualizer.
- If a scene has multiple text/audio/video entries, render all of them in order.
- If a task output ID is missing from the manifest, keep the scene row visible and mark that asset as missing instead of dropping the scene.
