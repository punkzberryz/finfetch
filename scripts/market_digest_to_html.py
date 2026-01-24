#!/usr/bin/env python3
import argparse
from pathlib import Path

HTML_TEMPLATE = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f7f4ef;
      --ink: #1c1a17;
      --muted: #5d5a54;
      --accent: #0f766e;
      --card: #ffffff;
      --rule: #e6e0d8;
    }}
    body {{
      margin: 0;
      background: linear-gradient(180deg, #f7f4ef 0%, #f0ebe2 100%);
      color: var(--ink);
      font-family: "Charter", "Iowan Old Style", "Times New Roman", serif;
      line-height: 1.6;
    }}
    .wrap {{
      max-width: 980px;
      margin: 0 auto;
      padding: 48px 20px 80px;
    }}
    header {{
      border-bottom: 2px solid var(--rule);
      margin-bottom: 24px;
      padding-bottom: 16px;
    }}
    h1, h2, h3 {{
      font-family: "Marion", "Palatino", serif;
      letter-spacing: 0.2px;
    }}
    h1 {{ font-size: 2.2rem; margin: 0 0 8px; }}
    h2 {{ font-size: 1.6rem; margin: 28px 0 8px; }}
    h3 {{ font-size: 1.2rem; margin: 18px 0 6px; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--rule);
      border-radius: 10px;
      padding: 16px 18px;
      box-shadow: 0 6px 20px rgba(0,0,0,0.04);
    }}
    ul {{ padding-left: 20px; }}
    code, pre {{ background: #f3efe8; }}
    pre {{ padding: 10px 12px; border-radius: 8px; overflow-x: auto; }}
    .muted {{ color: var(--muted); }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <header>
      <h1>{title}</h1>
      <div class=\"muted\">Generated from market_digest.md</div>
    </header>
    <main class=\"card\">
{body}
    </main>
  </div>
</body>
</html>
"""

def markdown_to_html(md: str) -> str:
    try:
        import markdown  # type: ignore
        return markdown.markdown(md, extensions=["fenced_code"])
    except Exception:
        # Minimal fallback: preserve line breaks and headings
        lines = []
        for line in md.splitlines():
            if line.startswith("# "):
                lines.append(f"<h1>{line[2:].strip()}</h1>")
            elif line.startswith("## "):
                lines.append(f"<h2>{line[3:].strip()}</h2>")
            elif line.startswith("### "):
                lines.append(f"<h3>{line[4:].strip()}</h3>")
            elif line.startswith("- "):
                lines.append(f"<li>{line[2:].strip()}</li>")
            elif line.strip() == "":
                lines.append("<br/>")
            else:
                lines.append(f"<p>{line.strip()}</p>")
        return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input markdown file")
    ap.add_argument("--out", required=True, help="Output HTML file")
    ap.add_argument("--title", default="Market Digest", help="Page title")
    args = ap.parse_args()

    md = Path(args.input).read_text(encoding="utf-8")
    body_html = markdown_to_html(md)
    html = HTML_TEMPLATE.format(title=args.title, body=indent(body_html, 6))
    Path(args.out).write_text(html, encoding="utf-8")


def indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in text.splitlines())


if __name__ == "__main__":
    main()
