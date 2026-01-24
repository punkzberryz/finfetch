#!/usr/bin/env python3
import argparse
import csv
import hashlib
import html
import os
import re
import time
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import List, Dict, Optional

try:
    import trafilatura
except Exception:
    trafilatura = None

CAPTURE_TAGS = {"p", "h1", "h2", "h3", "h4", "li"}
IGNORE_TAGS = {"script", "style", "noscript"}

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._texts: List[str] = []
        self._ignore_depth = 0
        self._capture_depth = 0
        self._in_title = False
        self.title = ""

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in IGNORE_TAGS:
            self._ignore_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in CAPTURE_TAGS:
            self._capture_depth += 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in IGNORE_TAGS and self._ignore_depth > 0:
            self._ignore_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in CAPTURE_TAGS and self._capture_depth > 0:
            self._capture_depth -= 1

    def handle_data(self, data):
        if self._ignore_depth > 0:
            return
        if self._in_title:
            self.title += data.strip()
        if self._capture_depth > 0:
            text = data.strip()
            if text:
                self._texts.append(text)

    def get_text(self) -> str:
        return "\n".join(self._texts)


def read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def fetch_url(url: str, timeout: int, user_agent: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def cache_path(cache_dir: str, url: str) -> str:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return os.path.join(cache_dir, f"{h}.html")


def extract_text(html_text: str, max_chars: int) -> Dict[str, str]:
    if trafilatura is not None:
        try:
            extracted = trafilatura.extract(html_text, include_links=False, include_images=False)
            if extracted:
                text = extracted.strip()
                if max_chars > 0 and len(text) > max_chars:
                    text = text[:max_chars]
                return {"text": text, "title": ""}
        except Exception:
            pass
    parser = TextExtractor()
    parser.feed(html_text)
    text = parser.get_text().strip()
    if not text:
        text = " ".join(html_text.split())
    text = html.unescape(text)
    if max_chars > 0 and len(text) > max_chars:
        text = text[:max_chars]
    return {"text": text, "title": parser.title.strip()}


def extract_canonical_url(html_text: str) -> Optional[str]:
    for pat in (
        r'rel="canonical" href="([^"]+)"',
        r'property="og:url" content="([^"]+)"',
        r'name="og:url" content="([^"]+)"'
    ):
        m = re.search(pat, html_text)
        if m:
            return m.group(1).strip()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV with news links")
    ap.add_argument("--out", default="digest.md", help="Output markdown path")
    ap.add_argument("--cache-dir", default=".link_cache", help="HTML cache directory")
    ap.add_argument("--limit", type=int, default=0, help="Limit number of URLs")
    ap.add_argument("--sleep", type=float, default=0.5, help="Delay between requests")
    ap.add_argument("--timeout", type=int, default=15, help="Request timeout in seconds")
    ap.add_argument("--user-agent", default="Mozilla/5.0 (Codex Digest Bot)", help="User agent")
    ap.add_argument("--max-chars", type=int, default=12000, help="Max chars of extracted text")
    ap.add_argument("--snippet-chars", type=int, default=1200, help="Snippet length to embed in markdown")
    args = ap.parse_args()

    os.makedirs(args.cache_dir, exist_ok=True)

    rows = read_csv(args.input)
    seen = set()
    output = []

    for row in rows:
        url = (row.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        if args.limit and len(output) >= args.limit:
            break

        record = {
            "url": url,
            "title": row.get("title", "").strip(),
            "source": row.get("source", "").strip(),
            "published_at": row.get("published_at", "").strip(),
            "scope": row.get("scope", "").strip(),
            "ticker": row.get("ticker", "").strip(),
            "provider": row.get("provider", "").strip(),
            "status": "ok",
            "error": "",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "text": ""
        }

        try:
            path = cache_path(args.cache_dir, url)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    html_text = f.read()
            else:
                html_text = fetch_url(url, args.timeout, args.user_agent)
                with open(path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(html_text)
                time.sleep(args.sleep)

            extracted = extract_text(html_text, args.max_chars)
            canonical = extract_canonical_url(html_text)
            if canonical and canonical != url:
                record["resolved_url"] = canonical
                try:
                    cpath = cache_path(args.cache_dir, canonical)
                    if os.path.exists(cpath):
                        with open(cpath, "r", encoding="utf-8", errors="replace") as f:
                            html_text = f.read()
                    else:
                        html_text = fetch_url(canonical, args.timeout, args.user_agent)
                        with open(cpath, "w", encoding="utf-8", errors="replace") as f:
                            f.write(html_text)
                        time.sleep(args.sleep)
                    extracted = extract_text(html_text, args.max_chars)
                except Exception:
                    pass
            if extracted.get("title") and not record["title"]:
                record["title"] = extracted["title"]
            record["text"] = extracted.get("text", "")
        except Exception as e:
            record["status"] = "error"
            record["error"] = str(e)

        output.append(record)

    output.sort(key=lambda x: x.get("published_at") or "", reverse=True)

    lines = []
    today = datetime.now(timezone.utc).date().isoformat()
    lines.append(f"# Market Digest ({today})")
    lines.append("")
    lines.append("## TL;DR")
    lines.append("- [Add top market summary with citation](SOURCE_URL)")
    lines.append("- [Add second summary with citation](SOURCE_URL)")
    lines.append("- [Add third summary with citation](SOURCE_URL)")
    lines.append("")
    lines.append("## Key Takeaways")
    lines.append("- [Add cross-source takeaway with citations]")
    lines.append("- [Optional second takeaway]")
    lines.append("")
    lines.append("## In-Depth")
    lines.append("")

    for item in output:
        title = item.get("title") or item.get("url")
        source = item.get("source") or "Unknown"
        url = item.get("resolved_url") or item.get("url") or ""
        scope = item.get("scope") or ""
        ticker = item.get("ticker") or ""
        text = (item.get("text") or "").strip()
        if args.snippet_chars > 0 and len(text) > args.snippet_chars:
            text = text[:args.snippet_chars]
        lines.append(f"### {title} — {source}")
        lines.append(f"- **Link**: {url}")
        lines.append(f"- **Scope**: {scope}  **Ticker**: {ticker}")
        lines.append("- **Summary (120-200 words)**: [Write summary with citations]")
        if text:
            lines.append("")
            lines.append("**Extracted Text (truncated)**")
            lines.append("```")
            lines.append(text)
            lines.append("```")
        lines.append("")

    lines.append("## Sources")
    for item in output:
        url = item.get("resolved_url") or item.get("url") or ""
        if url:
            lines.append(f"- {url}")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
