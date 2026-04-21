from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FAMILY_SCHEMAS_DIR = REPO_ROOT / "docs" / "family_schemas"
BASELINE_PATH = REPO_ROOT / "docs" / "nr_official_source_baseline.json"
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "nr_official_watch"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _iter_family_schema_paths() -> list[Path]:
    paths: list[Path] = []
    for path in sorted(FAMILY_SCHEMAS_DIR.glob("nr*.json")):
        name = path.name
        if name.endswith(".laudo_output_exemplo.json") or name.endswith(".laudo_output_seed.json") or name.endswith(
            ".template_master_seed.json"
        ):
            continue
        paths.append(path)
    return paths


def _official_source_map() -> dict[str, dict[str, Any]]:
    source_map: dict[str, dict[str, Any]] = {}
    for path in _iter_family_schema_paths():
        payload = _load_json(path)
        family_key = str(payload.get("family_key") or path.stem).strip()
        basis = payload.get("normative_basis")
        if not isinstance(basis, dict):
            continue
        sources = basis.get("sources")
        if not isinstance(sources, list):
            continue
        for source in sources:
            if not isinstance(source, dict):
                continue
            url = str(source.get("url") or "").strip()
            if not url:
                continue
            entry = source_map.setdefault(
                url,
                {
                    "url": url,
                    "title": str(source.get("title") or "").strip() or url,
                    "authority": str(source.get("authority") or "").strip() or None,
                    "families": [],
                },
            )
            if family_key not in entry["families"]:
                entry["families"].append(family_key)
    return source_map


def _fetch_url(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "tariel-nr-official-watch/1.0 (+https://github.com/gstarielio-hash/tariel-web)"
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
        headers = response.headers
        content_type = headers.get("Content-Type")
        sha256, hash_mode = _content_hash(body=body, content_type=content_type)
        return {
            "url": url,
            "status_code": getattr(response, "status", None),
            "content_length": len(body),
            "content_type": content_type,
            "etag": headers.get("ETag"),
            "last_modified": headers.get("Last-Modified"),
            "sha256": sha256,
            "hash_mode": hash_mode,
            "checked_at": datetime.now(UTC).isoformat(),
        }


def _content_hash(*, body: bytes, content_type: str | None) -> tuple[str, str]:
    normalized_type = str(content_type or "").lower()
    if "html" not in normalized_type:
        return hashlib.sha256(body).hexdigest(), "raw_bytes"

    text = body.decode("utf-8", errors="ignore")
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<!--.*?-->", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), "normalized_html_text"


def _build_snapshot() -> dict[str, Any]:
    source_map = _official_source_map()
    results: list[dict[str, Any]] = []
    for url, source in sorted(source_map.items()):
        fetched = _fetch_url(url)
        fetched["title"] = source.get("title")
        fetched["authority"] = source.get("authority")
        fetched["families"] = sorted(source.get("families") or [])
        results.append(fetched)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "monitoring_mode": "manual_admin_review",
        "source_count": len(results),
        "sources": results,
    }


def _baseline_by_url(baseline: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(baseline, dict):
        return {}
    sources = baseline.get("sources")
    if not isinstance(sources, list):
        return {}
    return {
        str(item.get("url") or "").strip(): item
        for item in sources
        if isinstance(item, dict) and str(item.get("url") or "").strip()
    }


def _compare_snapshots(current: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any]:
    baseline_map = _baseline_by_url(baseline)
    added: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []

    current_map = {str(item.get("url") or "").strip(): item for item in current.get("sources", []) if isinstance(item, dict)}
    for url, item in current_map.items():
        previous = baseline_map.get(url)
        if previous is None:
            added.append(item)
            continue
        if (
            item.get("sha256") != previous.get("sha256")
            or item.get("etag") != previous.get("etag")
            or item.get("last_modified") != previous.get("last_modified")
        ):
            changed.append(
                {
                    "url": url,
                    "title": item.get("title"),
                    "families": item.get("families"),
                    "previous": {
                        "sha256": previous.get("sha256"),
                        "etag": previous.get("etag"),
                        "last_modified": previous.get("last_modified"),
                    },
                    "current": {
                        "sha256": item.get("sha256"),
                        "etag": item.get("etag"),
                        "last_modified": item.get("last_modified"),
                    },
                }
            )

    for url, item in baseline_map.items():
        if url not in current_map:
            removed.append(item)

    impacted_families: dict[str, set[str]] = defaultdict(set)
    for item in added + removed:
        for family in item.get("families") or []:
            impacted_families[family].add(item.get("url") or "")
    for item in changed:
        for family in item.get("families") or []:
            impacted_families[family].add(item.get("url") or "")

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "monitoring_mode": "manual_admin_review",
        "has_changes": bool(added or removed or changed),
        "added": added,
        "removed": removed,
        "changed": changed,
        "impacted_families": {family: sorted(urls) for family, urls in sorted(impacted_families.items())},
    }


def _build_markdown_report(diff: dict[str, Any]) -> str:
    lines = [
        "# NR Official Watch Report",
        "",
        f"- generated_at: `{diff.get('generated_at')}`",
        f"- monitoring_mode: `{diff.get('monitoring_mode')}`",
        f"- has_changes: `{diff.get('has_changes')}`",
        f"- changed_sources: `{len(diff.get('changed') or [])}`",
        f"- added_sources: `{len(diff.get('added') or [])}`",
        f"- removed_sources: `{len(diff.get('removed') or [])}`",
        "- action_policy: `monitorar e revisar manualmente; nao atualizar templates automaticamente`",
        "",
    ]
    if diff.get("changed"):
        lines.extend(["## Changed sources", ""])
        for item in diff["changed"]:
            lines.append(f"- `{item['title']}`")
            lines.append(f"  - url: `{item['url']}`")
            lines.append(f"  - families: `{', '.join(item.get('families') or [])}`")
            lines.append(f"  - previous_sha256: `{item['previous'].get('sha256')}`")
            lines.append(f"  - current_sha256: `{item['current'].get('sha256')}`")
        lines.append("")
    if diff.get("added"):
        lines.extend(["## Added sources", ""])
        for item in diff["added"]:
            lines.append(f"- `{item['title']}` -> `{item['url']}`")
        lines.append("")
    if diff.get("removed"):
        lines.extend(["## Removed sources", ""])
        for item in diff["removed"]:
            lines.append(f"- `{item.get('title')}` -> `{item.get('url')}`")
        lines.append("")
    if diff.get("impacted_families"):
        lines.extend(["## Impacted families", ""])
        for family, urls in diff["impacted_families"].items():
            lines.append(f"- `{family}`")
            for url in urls:
                lines.append(f"  - `{url}`")
        lines.append("")
    if not diff.get("has_changes"):
        lines.extend(["## Status", "", "- Nenhuma mudanca detectada nas fontes oficiais monitoradas.", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--report-dir", default=str(ARTIFACTS_DIR))
    args = parser.parse_args()

    current = _build_snapshot()
    report_dir = Path(args.report_dir)
    _dump_json(report_dir / "latest_snapshot.json", current)

    if args.write_baseline:
        _dump_json(BASELINE_PATH, current)
        print(json.dumps({"baseline_written": str(BASELINE_PATH), "source_count": current["source_count"]}, ensure_ascii=False, indent=2))
        return

    baseline = _load_json(BASELINE_PATH) if BASELINE_PATH.exists() else None
    diff = _compare_snapshots(current, baseline)
    _dump_json(report_dir / "latest_diff.json", diff)
    (report_dir / "latest_report.md").write_text(_build_markdown_report(diff), encoding="utf-8")
    print(json.dumps(diff, ensure_ascii=False, indent=2))
    if diff.get("has_changes"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
