# Skill Installation

## Install the Skill

To install a packaged skill on another machine:

```
mkdir -p ~/.codex/skills
unzip -o docs/skills/digest-from-links.skill -d ~/.codex/skills
```

This creates:

```
~/.codex/skills/digest-from-links/
```

## Dependencies

For best extraction quality, install:

```
pip install trafilatura readability-lxml
```

For HTML conversion, install:

```
pip install markdown
```

## Use the Repo Helpers

The skill references helper scripts that live in this repository:

```
python scripts/fetch_links.py --input <links.csv> --out <digest.md> --cache-dir <cache_dir>
python scripts/market_digest_to_html.py --input <digest.md> --out <digest.html> --title "Market Digest"
```
