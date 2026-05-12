# Convert report.md to a single self-contained HTML file that renders
# the Mermaid sequence diagram via the official Mermaid CDN.
# Open the resulting report.html in Chrome/Edge, then Ctrl+P -> Save as PDF.

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MD = HERE.parent / "report" / "report.md"
OUT = HERE.parent / "report" / "report.html"

try:
    import markdown  # type: ignore
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
    import markdown  # type: ignore


def main() -> None:
    src = MD.read_text(encoding="utf-8")

    # Pull mermaid fenced blocks out before markdown sees them, so the
    # markdown library does not escape the diagram source.
    mermaid_blocks: list[str] = []

    def stash(m: re.Match[str]) -> str:
        mermaid_blocks.append(m.group(1))
        return f"@@MERMAID_{len(mermaid_blocks) - 1}@@"

    src = re.sub(r"```mermaid\n(.*?)```", stash, src, flags=re.DOTALL)

    html_body = markdown.markdown(
        src,
        extensions=["tables", "fenced_code", "toc"],
    )

    # Put the mermaid diagrams back as <div class="mermaid">...</div>
    def restore(m: re.Match[str]) -> str:
        idx = int(m.group(1))
        return f'<div class="mermaid">{mermaid_blocks[idx]}</div>'

    html_body = re.sub(r"@@MERMAID_(\d+)@@", restore, html_body)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>StudySync - PDC Assignment 2 Report</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{ startOnLoad: true, theme: "default" }});</script>
<style>
  @page {{ size: A4; margin: 10mm 12mm; }}
  html, body {{ font-family: "Times New Roman", Georgia, serif; color: #111; }}
  body {{ max-width: 100%; margin: 0; line-height: 1.22; font-size: 9.5pt; }}
  h1 {{ font-size: 13pt; margin: 0 0 .1em 0; }}
  h2 {{ font-size: 11pt; margin: .55em 0 .2em 0; border-bottom: 1px solid #ccc; padding-bottom: 1px; }}
  h3 {{ font-size: 10pt; margin: .45em 0 .15em 0; }}
  h4 {{ font-size: 9.8pt; margin: .35em 0 .1em 0; }}
  p {{ margin: .18em 0; }}
  ul, ol {{ margin: .2em 0 .2em 1.1em; padding: 0; }}
  li {{ margin: 0; }}
  p, li {{ font-size: 9.5pt; }}
  code {{ font-family: Consolas, "Courier New", monospace; font-size: 8.8pt;
          background: #f3f3f3; padding: 0 3px; border-radius: 3px; }}
  pre {{ margin: .3em 0; }}
  pre code {{ display: block; padding: 4px 7px; background: #f6f6f6;
              border: 1px solid #e2e2e2; border-radius: 4px; overflow: auto;
              line-height: 1.18; font-size: 8.8pt; }}
  table {{ border-collapse: collapse; margin: 4px 0; font-size: 8.5pt; width: 100%; }}
  th, td {{ border: 1px solid #bbb; padding: 2px 5px; vertical-align: top; }}
  th {{ background: #efefef; }}
  hr {{ display: none; }}
  .mermaid {{ background: #fff; padding: 0; page-break-inside: avoid;
              zoom: 0.75; }}
  .mermaid svg {{ max-width: 100% !important; height: auto !important; }}
  @media print {{
    a {{ color: inherit; text-decoration: none; }}
    h2, h3 {{ page-break-after: avoid; }}
    pre, table {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>
{html_body}
</body>
</html>
"""

    OUT.write_text(page, encoding="utf-8")
    print(f"Wrote {OUT}")
    print("Now open it in Chrome/Edge and Ctrl+P -> Save as PDF (A4, default margins).")


if __name__ == "__main__":
    main()
