#!/usr/bin/env python3
"""
run_all.py
==========
Master pipeline: builds the static site, runs all analysis scripts,
then exports every markdown report in adherence_results/ to PDF.

Usage:
    python run_all.py              # full pipeline
    python run_all.py --skip-build # skip build.py (faster if site is current)
    python run_all.py --pdf-only   # only re-export PDFs from existing .md files
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

import markdown
from xhtml2pdf import pisa

ROOT       = Path(__file__).resolve().parent
REPORTS    = ROOT / "adherence_results"
PDF_DIR    = ROOT / "adherence_results" / "pdf"

# ── scripts to run in order ───────────────────────────────────────────────────
PIPELINE = [
    ("Build static site",        ["python", "build.py"]),
    ("Syntax adherence (all)",   ["python", "syntax_adherence.py", "--all"]),
    ("Response length (all)",    ["python", "length_analysis.py",  "--all"]),
    ("Decimal GT accuracy",      ["python", "decimal_accuracy.py"]),
    ("Edge case analysis",       ["python", "edge_case_analysis.py"]),
    ("Uncertain cards",          ["python", "uncertain_cards.py"]),
    ("Hard vs standard",         ["python", "hard_vs_standard.py"]),
]

# ── PDF styling ───────────────────────────────────────────────────────────────
PDF_CSS = """
    body {
        font-family: Arial, sans-serif;
        font-size: 10pt;
        line-height: 1.5;
        color: #1a1a1a;
    }
    h1 { font-size: 18pt; border-bottom: 2px solid #333; padding-bottom: 4px; }
    h2 { font-size: 14pt; border-bottom: 1px solid #aaa; padding-bottom: 2px; margin-top: 1.5em; }
    h3 { font-size: 11pt; margin-top: 1.2em; }
    table {
        border-collapse: collapse;
        width: 100%;
        font-size: 7pt;
        margin: 0.8em 0;
        table-layout: fixed;
        word-wrap: break-word;
    }
    th, td {
        border: 1px solid #ccc;
        padding: 2px 4px;
        text-align: left;
        word-break: break-word;
    }
    th { background: #f0f0f0; font-weight: bold; }
    code, pre {
        font-family: Courier, monospace;
        font-size: 8pt;
        background: #f4f4f4;
        padding: 1px 4px;
    }
    blockquote {
        border-left: 3px solid #888;
        margin: 0.5em 0 0.5em 1em;
        padding: 0.2em 0.8em;
        color: #555;
    }
    hr { border-top: 1px solid #ddd; margin: 1em 0; }
"""


# ── helpers ───────────────────────────────────────────────────────────────────

def run_step(label: str, cmd: list[str]) -> bool:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    t0 = time.time()
    result = subprocess.run(cmd, cwd=ROOT)
    elapsed = time.time() - t0
    if result.returncode != 0:
        print(f"  [FAILED] exit code {result.returncode}  ({elapsed:.1f}s)")
        return False
    print(f"  [OK] {elapsed:.1f}s")
    return True


def md_to_pdf(md_path: Path, pdf_path: Path):
    text = md_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "nl2br"],
    )
    # Use landscape for reports with wide tables
    page_size = "landscape" if md_path.stem == "report" else "portrait"
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{md_path.stem}</title>
<style>
@page {{ margin: 1.5cm; size: A4 {page_size}; }}
{PDF_CSS}
</style>
</head><body>
{html_body}
</body></html>"""
    with open(pdf_path, "wb") as f:
        result = pisa.CreatePDF(html.encode("utf-8"), dest=f)
    if result.err:
        raise RuntimeError(f"xhtml2pdf error code {result.err}")
    print(f"  {pdf_path.name}")


def export_pdfs():
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    md_files = sorted(REPORTS.glob("*.md"))
    if not md_files:
        print("  No .md files found in adherence_results/")
        return
    print(f"\n{'='*60}")
    print(f"  Exporting {len(md_files)} reports to PDF")
    print(f"{'='*60}")
    for md_path in md_files:
        pdf_path = PDF_DIR / (md_path.stem + ".pdf")
        try:
            md_to_pdf(md_path, pdf_path)
        except Exception as e:
            print(f"  [FAILED] {md_path.name}: {e}")
    print(f"\n  PDFs written to: {PDF_DIR}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Full analysis pipeline")
    parser.add_argument("--skip-build", action="store_true",
                        help="Skip build.py (use when site is already current)")
    parser.add_argument("--pdf-only",   action="store_true",
                        help="Only export PDFs from existing .md reports")
    args = parser.parse_args()

    if args.pdf_only:
        export_pdfs()
        return

    failures = []
    total_t0 = time.time()

    for label, cmd in PIPELINE:
        if args.skip_build and cmd[1] == "build.py":
            print(f"  [SKIPPED] {label}")
            continue
        ok = run_step(label, cmd)
        if not ok:
            failures.append(label)

    export_pdfs()

    elapsed = time.time() - total_t0
    print(f"\n{'='*60}")
    if failures:
        print(f"  Pipeline finished with {len(failures)} failure(s) in {elapsed:.1f}s:")
        for f in failures:
            print(f"    - {f}")
        sys.exit(1)
    else:
        print(f"  All steps completed successfully in {elapsed:.1f}s")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
