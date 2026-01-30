# -*- coding: utf-8 -*-
"""
Created on Tue Dec 23 16:28:59 2025

@author: c_piazzese
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML
import re


# Where your HTML templates live
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"


# Ensure the templates directory exists
if not TEMPLATE_DIR.exists():
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Created templates folder at {TEMPLATE_DIR}")


# Ensure a default results.html exists
default_template_path = TEMPLATE_DIR / "results.html"
if not default_template_path.exists():
    default_template_content = """<!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>{{ title }}</title>
            </head>
            <body>
                <h1>{{ title }}</h1>
                <p>Total patients: {{ total_patients }}</p>
                <h2>Gender Counts</h2>
                <ul>{% for g in genderCounts %}<li>{{ g.gender }}: {{ g.count }}</li>{% endfor %}</ul>
                <h2>Age Groups</h2>
                <ul>{% for a in ageGroups %}<li>{{ a.range }}: {{ a.count }}</li>{% endfor %}</ul>
                <h2>Ethnicity Counts</h2>
                <ul>{% for e in ethnicityCounts %}<li>{{ e.ethnicity }}: {{ e.count }}</li>{% endfor %}</ul>
            </body>
            </html>"""
    default_template_path.write_text(default_template_content, encoding="utf-8")
    print(f"Created default template at {default_template_path}")
    

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def _safe_filename(value: str) -> str:
    """
    Make a string safe to use as a filename.
    """
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "_", value)
    return value


def generate_report(results: dict, filename_pdf: str | Path) -> tuple[str, Path]:
    """
    Generates:
      - HTML report (string) for email body
      - PDF report (Path) for attachment

    Args:
        results: dictionary with cohort results
        filename_pdf: path (string or Path) where the PDF will be saved

    Returns:
        (html_string, pdf_path)
    """

    template = env.get_template("results.html")

    html = template.render(
        title=results.get("title", "Untitled cohort"),
        total_patients=results.get("total_patients", 0),
        genderCounts=results.get("genderCounts", []),
        ageGroups=results.get("ageGroups", []),
        ethnicityCounts=results.get("ethnicityCounts", []),
    )

    pdf_path = Path(filename_pdf)  # use the provided PDF path

    # Uncomment below if you want to generate the PDF
    HTML(string=html).write_pdf(pdf_path)

    return html, pdf_path
