import hashlib
import re
from pathlib import Path
from typing import Any, Dict

from . import json_export, md_export


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    slug = slug.strip("-")
    return slug or "transcript"


def _infer_date(transcript: Dict[str, Any]) -> str:
    for key in ("event_date", "published_at"):
        value = transcript.get(key)
        if value:
            return str(value)[:10]
    return "undated"


def _article_id(url: str) -> str:
    m = re.search(r"-([0-9]+)\.html", url or "")
    if m:
        return m.group(1)
    return hashlib.md5((url or "").encode("utf-8")).hexdigest()[:8]


def build_transcript_basename(transcript: Dict[str, Any]) -> str:
    date_part = _infer_date(transcript)
    quarter = transcript.get("quarter") or ""
    title = transcript.get("title") or transcript.get("symbol") or "transcript"
    descriptor = _slugify(quarter) if quarter else _slugify(str(title))[:40]
    identifier = _article_id(transcript.get("url", ""))
    return "-".join([part for part in (date_part, descriptor, identifier) if part])


def export_transcript(transcript: Dict[str, Any], out_root: str = "./exports") -> Dict[str, str]:
    symbol = (transcript.get("symbol") or "UNKNOWN").upper()
    export_dir = Path(out_root) / "transcripts" / symbol
    export_dir.mkdir(parents=True, exist_ok=True)

    base = build_transcript_basename(transcript)
    json_path = export_dir / f"{base}.json"
    md_path = export_dir / f"{base}.md"

    json_export.export_json(transcript, json_path)
    md_export.export_transcript_md(transcript, md_path)

    return {"json": str(json_path), "markdown": str(md_path)}
