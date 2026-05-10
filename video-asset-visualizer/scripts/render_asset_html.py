#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render asset-manifest.json and asset-dag.json into an HTML viewer."
    )
    parser.add_argument("--asset-dag", required=True, help="Path to asset-dag.json")
    parser.add_argument(
        "--asset-manifest", required=True, help="Path to asset-manifest.json"
    )
    parser.add_argument("--output", required=True, help="Path to output HTML file")
    parser.add_argument(
        "--title",
        default="Video Asset Overview",
        help="Optional HTML page title.",
    )
    return parser.parse_args()


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def scene_sort_key(scene_id: str) -> tuple[int, str]:
    match = re.search(r"(\d+)", scene_id or "")
    if match:
        return (int(match.group(1)), scene_id)
    return (10**9, scene_id or "")


def asset_card(asset: dict[str, Any], media_html: str) -> str:
    return f"""
    <div class="asset-card">
      <div class="asset-meta">
        <div class="asset-id">{esc(asset.get("id", ""))}</div>
        <div class="asset-type">{esc(asset.get("type", ""))}</div>
      </div>
      {media_html}
      <a class="asset-link" href="{esc(asset.get("url", ""))}" target="_blank" rel="noreferrer">open asset</a>
    </div>
    """


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def build_media_html(asset: dict[str, Any]) -> str:
    url = asset.get("url", "")
    asset_type = str(asset.get("type", "") or "")
    if not url:
        return '<div class="missing">missing url</div>'
    if asset_type in {"reference_image", "keyframe_image", "image"}:
        return f'<img class="preview-image" src="{esc(url)}" alt="{esc(asset.get("id", ""))}">'
    if asset_type in {"narration_audio", "dialogue_audio", "sfx", "bgm", "audio"}:
        return f'<audio class="preview-audio" controls preload="none" src="{esc(url)}"></audio>'
    if asset_type in {"video_clip", "video"}:
        return f'<video class="preview-video" controls preload="metadata" src="{esc(url)}"></video>'
    return f'<div class="unknown-media">{esc(url)}</div>'


def classify_manifest_asset(asset: dict[str, Any]) -> str:
    asset_id = str(asset.get("id", "") or "")
    asset_type = str(asset.get("type", "") or "")
    task_id = str(asset.get("task_id", "") or "")

    if asset_type in {"reference_image", "keyframe_image", "narration_audio", "dialogue_audio", "video_clip", "sfx", "bgm"}:
        return asset_type

    if asset_type == "image":
        if asset_id.startswith("REF_") or task_id.startswith("T_CHAR_") or task_id.startswith("T_PROP_"):
            return "reference_image"
        return "keyframe_image"

    if asset_type == "audio":
        if asset_id.startswith("VO_") or task_id.startswith("T_VO_"):
            return "narration_audio"
        return "audio"

    if asset_type == "video":
        return "video_clip"

    return asset_type


def build_task_output_map(dag: dict[str, Any]) -> dict[str, str]:
    task_output_map: dict[str, str] = {}
    for task in dag.get("tasks", []) or []:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id", "") or "")
        outputs = [str(x) for x in (task.get("expected_outputs", []) or []) if x]
        if len(outputs) == 1 and task_id:
            task_output_map[task_id] = outputs[0]
    return task_output_map


def extract_scene_text(task: dict[str, Any]) -> dict[str, str] | None:
    params = task.get("params", {}) or {}
    task_type = task.get("task_type", "")
    speaker = params.get("speaker") or ""
    if task_type == "voiceover_tts" and params.get("text"):
        return {
            "kind": "旁白",
            "speaker": speaker or "narrator",
            "text": str(params["text"]),
        }

    for key in ("dialogue_text", "line", "spoken_line", "text"):
        value = params.get(key)
        if task_type != "voiceover_tts" and value:
            return {
                "kind": "对话",
                "speaker": speaker or "character",
                "text": str(value),
            }

    prompt = str(params.get("prompt", "") or "")
    match = re.search(r"exactly this line in Chinese:\s*「(.+?)」", prompt)
    if match:
        return {
            "kind": "对话",
            "speaker": speaker or "character",
            "text": match.group(1),
        }
    return None


def collect_scene_rows(
    dag: dict[str, Any], manifest: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    task_output_map = build_task_output_map(dag)
    raw_assets = manifest.get("assets", [])
    if isinstance(raw_assets, dict):
        assets_list = []
        for aid, data in raw_assets.items():
            if isinstance(data, dict):
                item = dict(data)
                if "id" not in item:
                    resolved_id = task_output_map.get(str(aid), "")
                    if not resolved_id:
                        task_id = str(item.get("task_id", "") or "")
                        resolved_id = task_output_map.get(task_id, "")
                    item["id"] = resolved_id or aid
                assets_list.append(item)
    else:
        assets_list = list(raw_assets)

    assets_by_id = {}
    for asset in assets_list:
        if not isinstance(asset, dict):
            continue
        if not asset.get("id"):
            task_id = str(asset.get("task_id", "") or "")
            asset["id"] = task_output_map.get(task_id, task_id or "")
        if "normalized_type" not in asset:
            asset["normalized_type"] = classify_manifest_asset(asset)
        assets_by_id[asset.get("id")] = asset
    reference_assets = [
        asset
        for asset in assets_list
        if isinstance(asset, dict) and asset.get("normalized_type") == "reference_image"
    ]

    scenes: dict[str, dict[str, Any]] = {}
    tasks = dag.get("tasks", [])
    for task in tasks:
        params = task.get("params", {}) or {}
        # Try to find scene_id in params or infer from task_id (e.g. T_IMG_S01 -> S01)
        scene_id = params.get("scene_id")
        if not scene_id:
            task_id = task.get("task_id", "")
            match = re.search(r"S_?(\d+)", task_id)
            if match:
                scene_id = f"S_{match.group(1)}"
        
        if not scene_id:
            continue
        scene = scenes.setdefault(
            scene_id,
            {
                "scene_id": scene_id,
                "texts": [],
                "keyframes": [],
                "audios": [],
                "videos": [],
                "expected_keyframes": [],
                "expected_audios": [],
                "expected_videos": [],
                "missing_outputs": [],
            },
        )

        text_entry = extract_scene_text(task)
        if text_entry:
            scene["texts"].append(text_entry)

        task_type = task.get("task_type")
        expected_outputs = task.get("expected_outputs", []) or []
        if task_type == "voiceover_tts":
            scene["expected_audios"].extend(expected_outputs)
        elif task_type in {"image_to_video", "native_dialogue_video"}:
            scene["expected_videos"].extend(expected_outputs)
        elif task_type == "keyframe_image":
            scene["expected_keyframes"].extend(expected_outputs)

        for output_id in expected_outputs:
            asset = assets_by_id.get(output_id)
            if not asset:
                scene["missing_outputs"].append(output_id)
                continue
            asset_type = asset.get("normalized_type") or asset.get("type")
            if asset_type == "keyframe_image":
                scene["keyframes"].append(asset)
            elif asset_type in {"narration_audio", "dialogue_audio", "sfx", "bgm", "audio"}:
                scene["audios"].append(asset)
            elif asset_type == "video_clip":
                scene["videos"].append(asset)

    ordered_scenes = [scenes[k] for k in sorted(scenes.keys(), key=scene_sort_key)]
    return reference_assets, ordered_scenes


def render_text_entries(entries: list[dict[str, str]]) -> str:
    if not entries:
        return '<div class="empty">No text found for this scene.</div>'
    parts = []
    for entry in entries:
        parts.append(
            f"""
            <div class="text-entry">
              <div class="text-label">{esc(entry["kind"])} · {esc(entry["speaker"])}</div>
              <div class="text-body">{esc(entry["text"])}</div>
            </div>
            """
        )
    return "\n".join(parts)


def render_scene_summary(scene: dict[str, Any]) -> str:
    def join_or_none(values: list[dict[str, Any]]) -> str:
        if not values:
            return "none"
        return ", ".join(str(item.get("id", "")) for item in values if item.get("id"))

    return f"""
    <div class="scene-summary">
      <div><strong>Resolved keyframes:</strong> {esc(join_or_none(scene["keyframes"]))}</div>
      <div><strong>Resolved audios:</strong> {esc(join_or_none(scene["audios"]))}</div>
      <div><strong>Resolved videos:</strong> {esc(join_or_none(scene["videos"]))}</div>
    </div>
    """


def render_expected_keys(expected_ids: list[str]) -> str:
    if not expected_ids:
        return '<div class="expected-line muted-line">Expected keys: none planned</div>'
    return (
        '<div class="expected-line">Expected keys: '
        + esc(", ".join(expected_ids))
        + "</div>"
    )


def render_asset_list(
    assets: list[dict[str, Any]], empty_label: str, expected_ids: list[str]
) -> str:
    if not assets:
        return render_expected_keys(expected_ids) + f'<div class="empty">{esc(empty_label)}</div>'
    return render_expected_keys(expected_ids) + "\n".join(
        asset_card(asset, build_media_html(asset)) for asset in assets
    )


def render_scene(scene: dict[str, Any]) -> str:
    missing_html = ""
    if scene["missing_outputs"]:
        missing_html = f"""
        <div class="missing-box">
          Missing outputs: {esc(", ".join(scene["missing_outputs"]))}
        </div>
        """
    return f"""
    <section class="scene-section" id="{esc(scene["scene_id"])}">
      <div class="scene-header">
        <h2>{esc(scene["scene_id"])}</h2>
      </div>
      {render_scene_summary(scene)}
      {missing_html}
      <div class="scene-grid">
        <div class="scene-block">
          <h3>Text</h3>
          {render_text_entries(scene["texts"])}
        </div>
        <div class="scene-block scene-media-block scene-media-primary">
          <h3>Keyframe</h3>
          <div class="asset-grid">
            {render_asset_list(scene["keyframes"], "No planned keyframe for this scene.", scene["expected_keyframes"])}
          </div>
        </div>
        <div class="scene-block">
          <h3>Audio</h3>
          <div class="asset-grid">
            {render_asset_list(scene["audios"], "No planned audio for this scene.", scene["expected_audios"])}
          </div>
        </div>
        <div class="scene-block scene-media-block scene-media-primary">
          <h3>Video</h3>
          <div class="asset-grid">
            {render_asset_list(scene["videos"], "No planned video for this scene.", scene["expected_videos"])}
          </div>
        </div>
      </div>
    </section>
    """


def render_html(
    title: str,
    project_id: str,
    reference_assets: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
) -> str:
    refs_html = render_asset_list(
        reference_assets,
        "No reference assets found.",
        [str(asset.get("id", "")) for asset in reference_assets if asset.get("id")],
    )
    scenes_html = "\n".join(render_scene(scene) for scene in scenes)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <style>
    :root {{
      --bg: #f6f1e8;
      --paper: #fffaf2;
      --ink: #1b1b1b;
      --muted: #6e655b;
      --line: #d8cdbf;
      --accent: #c14f2e;
      --accent-soft: #f0d8c9;
      --shadow: 0 18px 40px rgba(62, 38, 17, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(193,79,46,0.10), transparent 28%),
        linear-gradient(180deg, #f9f4eb 0%, var(--bg) 100%);
      line-height: 1.55;
    }}
    .page {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 40px 20px 80px;
    }}
    .hero {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 28px 30px;
      box-shadow: var(--shadow);
      margin-bottom: 28px;
    }}
    .hero h1 {{
      margin: 0 0 8px;
      font-size: 38px;
      line-height: 1.1;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
    }}
    .section {{
      margin-top: 28px;
      background: rgba(255, 250, 242, 0.78);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(5px);
    }}
    .section h2 {{
      margin: 0 0 16px;
      font-size: 28px;
    }}
    .asset-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
    }}
    .asset-card {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .asset-id {{
      font-weight: 700;
      font-size: 14px;
      word-break: break-word;
    }}
    .asset-type {{
      color: var(--muted);
      font-size: 13px;
    }}
    .asset-link {{
      color: var(--accent);
      text-decoration: none;
      font-size: 13px;
    }}
    .preview-image,
    .preview-video {{
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #f0ebe2;
      display: block;
    }}
    .preview-image {{
      min-height: 220px;
      object-fit: contain;
    }}
    .preview-video {{
      min-height: 280px;
      object-fit: contain;
    }}
    .preview-audio {{
      width: 100%;
    }}
    .scene-section {{
      padding-top: 8px;
      border-top: 1px solid rgba(216, 205, 191, 0.7);
      margin-top: 24px;
    }}
    .scene-section:first-of-type {{
      border-top: 0;
      margin-top: 0;
      padding-top: 0;
    }}
    .scene-header h2 {{
      margin: 0 0 12px;
      font-size: 24px;
    }}
    .scene-grid {{
      display: grid;
      grid-template-columns: minmax(260px, 0.8fr) minmax(360px, 1.2fr) minmax(260px, 0.8fr) minmax(360px, 1.2fr);
      gap: 18px;
    }}
    .scene-summary {{
      margin-bottom: 12px;
      padding: 12px 14px;
      border-radius: 14px;
      background: #fff7ee;
      border: 1px solid #ecd9c6;
      display: grid;
      gap: 6px;
      font-size: 14px;
    }}
    .scene-block {{
      background: rgba(255,255,255,0.82);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
    }}
    .scene-media-block .asset-grid {{
      grid-template-columns: 1fr;
    }}
    .scene-media-block .asset-card {{
      padding: 18px;
    }}
    .scene-media-primary {{
      min-width: 0;
    }}
    .scene-block h3 {{
      margin: 0 0 12px;
      font-size: 18px;
    }}
    .text-entry {{
      padding: 12px 14px;
      border-radius: 14px;
      background: var(--accent-soft);
      border: 1px solid rgba(193,79,46,0.16);
      margin-bottom: 10px;
    }}
    .text-entry:last-child {{
      margin-bottom: 0;
    }}
    .text-label {{
      font-size: 12px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 6px;
      font-weight: 700;
    }}
    .text-body {{
      white-space: pre-wrap;
    }}
    .empty,
    .missing,
    .unknown-media,
    .missing-box {{
      color: var(--muted);
      font-size: 14px;
    }}
    .expected-line {{
      grid-column: 1 / -1;
      margin-bottom: 10px;
      padding: 10px 12px;
      border-radius: 12px;
      background: #f5eee4;
      border: 1px solid var(--line);
      font-size: 13px;
      color: var(--ink);
      word-break: break-word;
    }}
    .muted-line {{
      color: var(--muted);
    }}
    .missing-box {{
      margin-bottom: 12px;
      padding: 10px 12px;
      border-radius: 12px;
      background: #fff1e8;
      border: 1px solid #efc8b3;
    }}
    @media (max-width: 720px) {{
      .hero h1 {{
        font-size: 30px;
      }}
      .page {{
        padding: 18px 12px 40px;
      }}
      .section,
      .hero {{
        padding: 18px;
        border-radius: 18px;
      }}
      .scene-grid {{
        grid-template-columns: 1fr;
      }}
      .preview-image,
      .preview-video {{
        min-height: 0;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header class="hero">
      <h1>{esc(title)}</h1>
      <p>Project: {esc(project_id or "unknown")} · Reference assets first, then scene-by-scene text, keyframe, audio, and video.</p>
    </header>

    <section class="section">
      <h2>Reference Assets</h2>
      <div class="asset-grid">
        {refs_html}
      </div>
    </section>

    <section class="section">
      <h2>Scenes</h2>
      {scenes_html}
    </section>
  </div>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    dag = load_json(args.asset_dag)
    manifest = load_json(args.asset_manifest)
    reference_assets, scenes = collect_scene_rows(dag, manifest)
    html_text = render_html(
        title=args.title,
        project_id=str(dag.get("project_id", "") or ""),
        reference_assets=reference_assets,
        scenes=scenes,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")
    print(str(output_path))


if __name__ == "__main__":
    main()
